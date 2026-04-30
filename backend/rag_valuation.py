"""
PSDS — Araç ve Konut Değerleme

Akış:
  1. Serper.dev (SERPER_API_KEY varsa) → Google snippet'lerinden TL fiyat listesi
  2. Claude web_search (ANTHROPIC_API_KEY) → fallback arama + expert tahmin
  3. IQR ile outlier filtresi → trimmed median
  4. Yetersiz veri varsa marka/şehir bazlı formül

Tüm adımlar trace listesine yazılır.
"""

from __future__ import annotations

import os
import re
import json
import logging
import datetime
import statistics
import time

# ── Basit in-memory cache (process ömrü boyunca, ~30 dk TTL) ─────────────────
_CACHE: dict[str, tuple[dict, float]] = {}
_CACHE_TTL = 1800  # 30 dakika


def _cache_get(key: str) -> dict | None:
    if key in _CACHE:
        result, ts = _CACHE[key]
        if time.time() - ts < _CACHE_TTL:
            log.info(f"Cache hit: {key}")
            return result
        del _CACHE[key]
    return None


def _cache_set(key: str, value: dict) -> None:
    _CACHE[key] = (value, time.time())

log = logging.getLogger("psds.rag")
if not log.handlers:
    h = logging.StreamHandler()
    h.setFormatter(logging.Formatter("[%(asctime)s] [RAG] %(message)s", datefmt="%H:%M:%S"))
    log.addHandler(h)
    log.setLevel(logging.INFO)


# ── Sabitler ──────────────────────────────────────────────────────────────────
_BRAND_BASE: dict[str, int] = {
    "fiat": 1_050_000, "dacia": 1_100_000, "renault": 1_300_000,
    "volkswagen": 1_950_000, "toyota": 1_800_000, "ford": 1_600_000,
    "hyundai": 1_550_000, "kia": 1_550_000, "opel": 1_400_000,
    "peugeot": 1_500_000, "citroen": 1_350_000, "skoda": 1_650_000,
    "seat": 1_600_000, "honda": 1_750_000, "nissan": 1_700_000,
    "bmw": 4_000_000, "mercedes": 4_500_000, "mercedes-benz": 4_500_000,
    "audi": 3_800_000, "volvo": 3_500_000, "suzuki": 1_450_000,
    "jeep": 2_800_000, "land rover": 6_000_000, "porsche": 9_000_000,
    "mitsubishi": 2_200_000, "mazda": 2_000_000, "subaru": 2_500_000,
    "mini": 1_800_000, "togg": 1_700_000, "default": 1_600_000,
}

_CITY_M2: dict[str, int] = {
    "istanbul": 120_000, "ankara": 50_000, "izmir": 70_000,
    "bursa": 42_000, "antalya": 50_000, "kocaeli": 38_000,
    "mersin": 28_000, "konya": 25_000, "adana": 22_000,
    "samsun": 22_000, "trabzon": 25_000, "kayseri": 22_000,
    "eskisehir": 28_000, "gaziantep": 20_000, "diyarbakir": 16_000,
    "default": 20_000,
}

# NOT: allowed_domains kısıtı KALDIRILDI çünkü sahibinden/arabam anti-bot
# nedeniyle crawler snippet'inde fiyat dönmüyor. Open web'e bırakıldığında
# Claude Google'ın aggregator snippet'lerinden fiyatları görebiliyor.
# Yine de prompt içinde "tercih edilen kaynaklar" olarak listeleniyor.
_CAR_PREFERRED_SITES = (
    "sahibinden.com, arabam.com, letgo.com, dod.com.tr, "
    "otokocikincieli.com.tr, borusanoto.com, otomobilcim.com"
)

_PROPERTY_PREFERRED_SITES = (
    "sahibinden.com, hepsiemlak.com, emlakjet.com, "
    "zingat.com, milliyetemlak.com, endeksa.com"
)

_PRICE_RE = [
    r'(\d{1,3}(?:\.\d{3})+)\s*(?:TL|₺)',
    r'(?:TL|₺)\s*(\d{1,3}(?:\.\d{3})+)',
    r'(\d{1,3}(?:,\d{3})+)\s*(?:TL|₺)',
    r'(\d{6,9})\s*(?:TL|₺)',
]

# m² birim fiyatı pattern'leri — toplam fiyat yerine m²/TL çekmek için
_M2_PRICE_RE = [
    r'(\d{1,3}(?:\.\d{3})+)\s*(?:TL|₺)\s*/\s*m[²2]',
    r'(\d{1,3}(?:\.\d{3})+)\s*(?:TL|₺)\s*(?:per|başına)\s*m[²2]',
    r'm[²2]\s*(?:fiyat[ıi]?|birim\s*fiyat[ıi]?)[ıi]?\s*:?\s*(\d{1,3}(?:\.\d{3})+)',
    r'ortalama\s+m[²2]\s+fiyat[ıi]?\s*:?\s*(\d{1,3}(?:\.\d{3})+)',
    r'(\d{2,3}(?:\.\d{3})?)\s*(?:TL|₺)\s*/\s*m[²2]',
]


# ── Yardımcılar ───────────────────────────────────────────────────────────────
def _extract_prices(text: str, min_val: int, max_val: int) -> list[int]:
    found: set[int] = set()
    for pat in _PRICE_RE:
        for tok in re.findall(pat, text, re.IGNORECASE):
            clean = tok.replace(".", "").replace(",", "")
            try:
                v = int(clean)
                if min_val <= v <= max_val:
                    found.add(v)
            except ValueError:
                pass
    return sorted(found)


def _extract_m2_unit_prices(text: str, min_m2: int = 8_000, max_m2: int = 400_000) -> list[int]:
    """
    Metin içinden m² birim fiyatlarını çeker.
    Örn: "45.000 TL/m²" → 45000
    min_m2/max_m2: Türkiye 2025 makul m² aralığı.
    """
    found: set[int] = set()
    for pat in _M2_PRICE_RE:
        for tok in re.findall(pat, text, re.IGNORECASE):
            clean = tok.replace(".", "").replace(",", "")
            try:
                v = int(clean)
                if min_m2 <= v <= max_m2:
                    found.add(v)
            except ValueError:
                pass
    return sorted(found)


def _serper_search(query: str, num: int = 10) -> str:
    """
    Serper.dev Google Search API — IP yasağı yok, temiz snippet'ler.
    SERPER_API_KEY env yoksa boş döner, Claude web_search devreye girer.
    """
    api_key = os.getenv("SERPER_API_KEY")
    if not api_key:
        return ""
    try:
        import httpx
        resp = httpx.post(
            "https://google.serper.dev/search",
            headers={"X-API-KEY": api_key, "Content-Type": "application/json"},
            json={"q": query, "gl": "tr", "hl": "tr", "num": num},
            timeout=12,
        )
        data = resp.json()
        parts: list[str] = []
        for r in data.get("organic", []):
            parts.append(r.get("title", "") + " " + r.get("snippet", ""))
        for r in data.get("answerBox", {}).get("snippets", []):
            parts.append(r)
        return "\n".join(parts)
    except Exception as e:
        log.warning(f"Serper hata: {e}")
        return ""


def _serper_prices(
    queries: list[str], min_val: int, max_val: int, trace: list | None = None
) -> list[int]:
    """Birden fazla sorgu yapıp fiyatları birleştir."""
    all_prices: list[int] = []
    for q in queries:
        text = _serper_search(q)
        if not text:
            break  # API key yok — devam etme
        prices = _extract_prices(text, min_val, max_val)
        log.info(f"Serper '{q[:50]}' → {len(prices)} fiyat: {prices[:5]}")
        if trace is not None:
            trace.append({"step": "serper", "query": q, "prices": prices})
        all_prices.extend(prices)
        if len(set(all_prices)) >= 5:
            break
    return sorted(set(all_prices))


def _remove_outliers_iqr(prices: list[int]) -> list[int]:
    """Q1-1.5*IQR / Q3+1.5*IQR dışını at. n<4 ise dokunma."""
    if len(prices) < 4:
        return prices
    qs = statistics.quantiles(prices, n=4)
    q1, q3 = qs[0], qs[2]
    iqr = q3 - q1
    lo = q1 - 1.5 * iqr
    hi = q3 + 1.5 * iqr
    return [p for p in prices if lo <= p <= hi]


def _parse_json_block(text: str) -> dict | None:
    try:
        m = re.search(r'\{[^{}]*"prices"[^{}]*\}', text, re.DOTALL)
        if not m:
            m = re.search(r'\{.*\}', text, re.DOTALL)
        return json.loads(m.group()) if m else None
    except Exception:
        return None


# ── Web search çekirdeği ──────────────────────────────────────────────────────
def _run_web_search(
    client,
    model: str,
    prompt: str,
    allowed_domains: list[str] | None = None,
    max_turns: int = 3,
    max_uses: int = 5,
    trace: list | None = None,
) -> str:
    """
    Anthropic'in server-side managed `web_search_20250305` tool'unu kullanır.
    Aramayı Anthropic sunucusu çalıştırır; istemci tool_result yollamaz.
    stop_reason 'pause_turn' ise aynı mesajla devam et.
    """
    tool: dict = {
        "type": "web_search_20250305",
        "name": "web_search",
        "max_uses": max_uses,
        "user_location": {
            "type": "approximate",
            "country": "TR",
            "timezone": "Europe/Istanbul",
        },
    }
    if allowed_domains:
        tool["allowed_domains"] = allowed_domains

    messages = [{"role": "user", "content": prompt}]
    full_text = ""
    queries: list[str] = []
    domains_hit: set[str] = set()

    for turn in range(max_turns):
        resp = client.messages.create(
            model=model,
            max_tokens=2048,
            tools=[tool],
            messages=messages,
        )

        for block in resp.content:
            btype = getattr(block, "type", None)
            text = getattr(block, "text", None)
            if text:
                full_text += text
            if btype == "server_tool_use":
                q = getattr(getattr(block, "input", None), "get", lambda _k, _d=None: None)("query", None) \
                    if not isinstance(getattr(block, "input", None), dict) \
                    else block.input.get("query")
                if q:
                    queries.append(q)
            if btype == "web_search_tool_result":
                content = getattr(block, "content", None) or []
                for r in content:
                    url = getattr(r, "url", None) or (r.get("url") if isinstance(r, dict) else None)
                    if url:
                        m = re.search(r"https?://(?:www\.)?([^/]+)", url)
                        if m:
                            domains_hit.add(m.group(1))

        log.info(f"turn {turn+1}: stop_reason={resp.stop_reason} chars={len(full_text)}")

        if resp.stop_reason == "pause_turn":
            messages.append({"role": "assistant", "content": resp.content})
            continue
        break

    if trace is not None:
        trace.append({
            "step": "web_search",
            "queries": queries,
            "domains_hit": sorted(domains_hit),
            "raw_chars": len(full_text),
            "raw_preview": full_text[:1500],
        })
    return full_text


# ── Live search: araç ─────────────────────────────────────────────────────────
def _live_search_price(
    brand: str, model: str, year: int, has_damage: bool,
    trace: list | None = None,
) -> dict | None:
    _CAR_MIN = 400_000
    _CAR_MAX = 100_000_000

    # ── ADIM 1: Serper.dev ile canlı Google snippet fiyatları ─────────────────
    serper_queries = [
        f"{year} {brand} {model} ikinci el fiyat sahibinden",
        f"{year} {brand} {model} arabam ikinci el TL",
        f"{brand} {model} {year} satılık fiyat türkiye",
    ]
    serper_prices = _serper_prices(serper_queries, _CAR_MIN, _CAR_MAX, trace)
    if len(serper_prices) >= 3:
        cleaned = _remove_outliers_iqr(serper_prices)
        if len(cleaned) < 2:
            cleaned = serper_prices
        median = int(statistics.median(cleaned))
        if has_damage:
            median = round(median * 0.82)
        log.info(f"Serper tier1: n={len(cleaned)} median=₺{median:,}")
        if trace is not None:
            trace.append({"step": "aggregate_car", "source": "serper", "tier": 1,
                          "raw": serper_prices, "cleaned": cleaned, "median": median})
        return {
            "rag_used": True, "tier": 1,
            "estimated_car_value": median,
            "confidence": "high" if len(cleaned) >= 5 else "medium",
            "price_count": len(cleaned),
            "raw_prices": serper_prices,
            "filtered_prices": cleaned,
            "reasoning": f"{year} {brand} {model} — Serper/Google'dan {len(cleaned)} ilan medyanı.",
            "source": "Serper.dev (Google)",
        }

    # ── ADIM 2: Claude web_search (Anthropic sunucuları, IP yasağı yok) ───────
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        log.warning("ANTHROPIC_API_KEY yok — web search atlandı")
        return None
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)

        damage_note = "ARAÇ HASAR KAYITLI — bunu fiyata yansıt (%15-20 düşük)." if has_damage else ""
        age = max(0, datetime.datetime.now().year - int(year))
        # Segment tahmini için bağlam — Claude'un expert tahminini gerçekçi tutar
        segment_hint = (
            "BMW, Mercedes-Benz, Audi, Porsche, Land Rover, Volvo gibi premium/lüks markalar "
            "Türkiye'de 2026 yılında 3M–20M TL aralığındadır."
            if brand.lower() in {"bmw","mercedes","mercedes-benz","audi","porsche","land rover","volvo","lexus"}
            else
            "Volkswagen, Toyota, Ford, Hyundai, Renault, Fiat gibi ana segment araçlar "
            "Türkiye'de 2026 yılında 800K–4M TL aralığındadır."
        )
        prompt = (
            f"Türkiye 2. el otomobil piyasasında {year} {brand} {model} fiyatını araştır.\n\n"
            f"ADIM 1 — Arama yap:\n"
            f"  • \"{year} {brand} {model} ikinci el fiyat\"\n"
            f"  • \"{year} {brand} {model} sahibinden\"\n"
            f"  • \"{year} {brand} {model} arabam\"\n\n"
            f"ADIM 2 — Fiyat topla (KRİTİK KURALLAR):\n"
            f"  ✅ 'TL' veya '₺' sembolüyle birlikte yazılan SATIŞ fiyatları\n"
            f"  ❌ Kilometre değerleri (50.000 km, 120.000 km) — FIYAT DEĞİL\n"
            f"  ❌ Model yılı rakamları (2010, 2022 vb.) — FIYAT DEĞİL\n"
            f"  ❌ Yedek parça, kira, 0 km yeni araç, ağır hasarlı ilanlar\n\n"
            f"ADIM 3 — Expert tahmin yap (ZORUNLU):\n"
            f"  Araç: {year} {brand} {model}, yaşı {age} yıl.\n"
            f"  {segment_hint}\n"
            f"  Türkiye yüksek enflasyon ekonomisi — fiyatlar her yıl büyük artıyor.\n"
            f"  Bulduğun gerçek ilanlarla + segment bilginle expert_low/high/estimate belirle.\n"
            f"  {damage_note}\n\n"
            f"SADECE şu JSON formatında yanıt ver, başka hiçbir metin yazma:\n"
            f"{{\n"
            f"  \"listings\": [13200000, 14500000],\n"
            f"  \"expert_low\": 12000000,\n"
            f"  \"expert_high\": 15000000,\n"
            f"  \"expert_estimate\": 13500000,\n"
            f"  \"segment\": \"lüks sedan, 4 yıllık, 330 BG dizel\",\n"
            f"  \"note\": \"1 gerçek ilan + segment bilgisiyle tahmin\"\n"
            f"}}"
        )

        full_text = _run_web_search(
            client, "claude-haiku-4-5-20251001", prompt,
            allowed_domains=None, max_uses=5, trace=trace,
        )
        log.info(f"car raw: {full_text[:200]}")

        data = _parse_json_block(full_text) or {}

        def _to_int(v) -> int | None:
            try:
                n = int(str(v).replace(".", "").replace(",", ""))
                return n if _CAR_MIN <= n <= _CAR_MAX else None
            except (ValueError, TypeError):
                return None

        listings: list[int] = []
        for p in (data.get("listings") or []):
            n = _to_int(p)
            if n is not None:
                listings.append(n)

        # JSON yoksa serbest metinden çekmeyi de dene
        if len(listings) < 3:
            for p in _extract_prices(full_text, _CAR_MIN, _CAR_MAX):
                if p not in listings:
                    listings.append(p)

        # ── Tier 1: gerçek listings yeterli mi? ───────────────────────────
        if len(listings) >= 3:
            cleaned = _remove_outliers_iqr(listings)
            if len(cleaned) < 3:
                cleaned = listings
            median = statistics.median(cleaned)
            if has_damage:
                median = round(median * 0.82)
            confidence = "high" if len(cleaned) >= 6 else "medium"
            log.info(f"car tier1: n={len(cleaned)} median=₺{int(median):,} confidence={confidence}")
            if trace is not None:
                trace.append({
                    "step": "aggregate_car",
                    "tier": 1,
                    "raw_prices": listings,
                    "after_iqr": cleaned,
                    "median": int(median),
                    "confidence": confidence,
                })
            return {
                "rag_used": True,
                "tier": 1,
                "estimated_car_value": int(median),
                "confidence": confidence,
                "price_count": len(cleaned),
                "raw_prices": listings,
                "filtered_prices": cleaned,
                "reasoning": f"{year} {brand} {model} — {len(cleaned)} gerçek ilanın medyanı.",
                "source": f"Claude web_search ({len(cleaned)} ilan)",
            }

        # ── Tier 2: Claude'un segment-bazlı tahmini ───────────────────────
        expert = _to_int(data.get("expert_estimate"))
        elow   = _to_int(data.get("expert_low"))
        ehigh  = _to_int(data.get("expert_high"))

        # Expert tahmin de mantıklı aralıkta olmalı
        if expert is not None and expert < _CAR_MIN:
            log.warning(f"expert_estimate {expert} < minimum {_CAR_MIN}, Tier2 atlanıyor")
            expert = None

        if expert is not None and elow is not None and ehigh is not None and elow <= ehigh:
            # has_damage zaten prompt'ta verildi, bu yüzden %82 indirimi tekrar uygulamıyoruz
            log.info(f"car tier2: ₺{elow:,}–₺{ehigh:,} mid=₺{expert:,} (segment={data.get('segment')})")
            if trace is not None:
                trace.append({
                    "step": "aggregate_car",
                    "tier": 2,
                    "result": "insufficient_listings_used_expert_estimate",
                    "listings_found": listings,
                    "expert_low": elow,
                    "expert_high": ehigh,
                    "expert_estimate": expert,
                    "segment": data.get("segment"),
                    "note": data.get("note"),
                })
            return {
                "rag_used": True,
                "tier": 2,
                "estimated_car_value": expert,
                "confidence": "medium",
                "price_count": len(listings),
                "raw_prices": listings,
                "expert_range": [elow, ehigh],
                "segment": data.get("segment"),
                "reasoning": (
                    f"{year} {brand} {model}: SERP'te yeterli ilan yok ({len(listings)}). "
                    f"Segment-bazlı uzman tahmin: ₺{elow:,}–₺{ehigh:,}. "
                    f"{data.get('note', '')}"
                ),
                "source": "Claude segment estimate",
            }

        # ── Hiçbir şey çıkmadı → fallback formüle bırak ────────────────────
        log.warning(f"yetersiz tier1+tier2 (listings={len(listings)}, expert={expert})")
        if trace is not None:
            trace.append({
                "step": "aggregate_car",
                "result": "insufficient_data",
                "listings": listings,
                "raw_data": data,
            })
        return None

    except Exception as e:
        log.error(f"car live search hata: {e}")
        if trace is not None:
            trace.append({"step": "web_search", "error": str(e)[:200]})
    return None


# ── Live search: konut ────────────────────────────────────────────────────────
def _live_search_property(
    city: str, district: str, square_meters: float,
    trace: list | None = None,
) -> dict | None:
    _PROP_MIN = 500_000
    _PROP_MAX = 500_000_000

    loc = f"{city} {district}".strip()

    # ── ADIM 1: Serper.dev — önce m² birim fiyatı ara (daha doğru) ───────────
    serper_api_key = os.getenv("SERPER_API_KEY")
    if serper_api_key:
        # 1a. m²/birim fiyatı sorgula
        m2_unit_queries = [
            f"{loc} daire m2 satış fiyatı 2025",
            f"{city} {district} konut ortalama m2 fiyat",
            f"endeksa {loc} m2 fiyatı",
            f"hepsiemlak {loc} m2 fiyat 2025",
        ]
        all_m2_texts = ""
        for q in m2_unit_queries:
            t = _serper_search(q)
            if not t:
                break
            all_m2_texts += "\n" + t
            unit_prices_so_far = _extract_m2_unit_prices(all_m2_texts)
            log.info(f"Serper m² '{q[:50]}' → birim fiyatlar: {unit_prices_so_far[:5]}")
            if trace is not None:
                trace.append({"step": "serper_m2", "query": q,
                               "unit_prices": unit_prices_so_far})
            if len(unit_prices_so_far) >= 3:
                break

        m2_unit_prices = _extract_m2_unit_prices(all_m2_texts)
        if len(m2_unit_prices) >= 2:
            cleaned_m2 = _remove_outliers_iqr(m2_unit_prices)
            if len(cleaned_m2) < 2:
                cleaned_m2 = m2_unit_prices
            median_m2 = int(statistics.median(cleaned_m2))
            total = round(median_m2 * square_meters)
            if _PROP_MIN <= total <= _PROP_MAX:
                log.info(f"Serper m²-birim tier1: m2p=₺{median_m2:,} × {square_meters}m² = ₺{total:,}")
                if trace is not None:
                    trace.append({
                        "step": "aggregate_property", "source": "serper_m2_unit",
                        "tier": 1, "unit_prices": m2_unit_prices,
                        "cleaned_unit_prices": cleaned_m2,
                        "median_m2_price": median_m2,
                        "square_meters": square_meters,
                        "total": total,
                    })
                return {
                    "rag_used": True, "tier": 1,
                    "property_estimated_value": total,
                    "avg_m2_price": median_m2,
                    "confidence": "high" if len(cleaned_m2) >= 4 else "medium",
                    "price_count": len(cleaned_m2),
                    "reasoning": (
                        f"{loc}: ₺{median_m2:,}/m² × {square_meters:.0f}m² = ₺{total:,} "
                        f"({len(cleaned_m2)} Serper m² verisi)."
                    ),
                    "source": "Serper.dev — m² birim fiyatı",
                }

        # 1b. m² bulunamadı — toplam ilan fiyatlarını dene
        serper_total_queries = [
            f"{loc} satılık daire fiyat",
            f"{city} {district} satılık konut sahibinden hepsiemlak",
        ]
        serper_prices = _serper_prices(serper_total_queries, _PROP_MIN, _PROP_MAX, trace)
        if len(serper_prices) >= 3:
            cleaned = _remove_outliers_iqr(serper_prices)
            if len(cleaned) < 2:
                cleaned = serper_prices
            median = int(statistics.median(cleaned))
            m2p = round(median / max(square_meters, 1))
            log.info(f"Serper konut toplam-fiyat tier1: n={len(cleaned)} median=₺{median:,}")
            if trace is not None:
                trace.append({"step": "aggregate_property", "source": "serper_total",
                               "tier": 1, "raw": serper_prices, "cleaned": cleaned,
                               "median": median})
            return {
                "rag_used": True, "tier": 1,
                "property_estimated_value": median,
                "avg_m2_price": m2p,
                "confidence": "medium",
                "price_count": len(cleaned),
                "reasoning": f"{loc} {square_meters}m² — Serper/Google'dan {len(cleaned)} ilan toplam fiyatı medyanı.",
                "source": "Serper.dev (Google toplam fiyat)",
            }

    # ── ADIM 2: Claude web_search ──────────────────────────────────────────────
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        log.warning("ANTHROPIC_API_KEY yok — konut web search atlandı")
        return None
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        prompt = (
            f"Türkiye konut pazarında {loc} bölgesinde {square_meters:.0f} m² satılık daire değerini araştır.\n\n"
            f"ADIM 1 — ÖNCELİKLE m² birim fiyatı ara:\n"
            f"  • \"{loc} daire m2 satış fiyatı 2025\"\n"
            f"  • \"{city} {district} konut ortalama m2 fiyat\"\n"
            f"  • \"endeksa {loc} m2 fiyatı\"\n\n"
            f"ADIM 2 — Eğer m² birim fiyatı bulamazsan toplam ilan fiyatı ara:\n"
            f"  • \"{loc} {square_meters:.0f} m² daire sahibinden satılık\"\n"
            f"  • \"{loc} satılık daire fiyat\"\n\n"
            f"ADIM 3 — HESAPLAMA KURALLARI (ÇOK ÖNEMLİ):\n"
            f"  ✅ m² birim fiyatı bulduysan: birim_fiyat × {square_meters:.0f} = TOPLAM DEĞİL\n"
            f"     Bu hesabı yap, 'listing' listesine TOPLAM rakamı yaz\n"
            f"  ✅ Sadece SATIŞ fiyatları, 'TL' veya '₺' ile yazılmış\n"
            f"  ❌ KİRALIK fiyatlar — SATIŞ DEĞİL, atla\n"
            f"  ❌ 2024 öncesi eski fiyatlar\n"
            f"  ❌ Sıfır/proje aşaması fiyatları\n\n"
            f"ADIM 4 — Expert tahmin:\n"
            f"  2026 Türkiye'de {loc} bölgesinde {square_meters:.0f} m² daire makul fiyat aralığı nedir?\n"
            f"  Snippet'lerden bulunan m² birim fiyatıyla veya toplam ilanlarla destekle.\n\n"
            f"  Örnek: Esenyurt 2025 m² ~40.000-55.000 TL → 65m² = 2.6M-3.6M TL\n\n"
            f"Yanıtı SADECE şu JSON formatında ver, başka metin yazma:\n"
            f"{{\n"
            f"  \"m2_unit_prices\": [42000, 48000],\n"
            f"  \"listings\": [2730000, 3120000],\n"
            f"  \"expert_low\": 2500000,\n"
            f"  \"expert_high\": 3800000,\n"
            f"  \"expert_estimate\": 3100000,\n"
            f"  \"note\": \"Esenyurt 45.000 TL/m² medyanı × 65m² hesabıyla\"\n"
            f"}}"
        )

        full_text = _run_web_search(
            client, "claude-haiku-4-5-20251001", prompt,
            allowed_domains=None, max_uses=5, trace=trace,
        )
        log.info(f"property raw: {full_text[:200]}")

        data = _parse_json_block(full_text) or {}

        def _to_int(v) -> int | None:
            try:
                n = int(str(v).replace(".", "").replace(",", ""))
                return n if 200_000 <= n <= 500_000_000 else None
            except (ValueError, TypeError):
                return None

        # ── Önce Claude'un m²/birim fiyatlarını kontrol et ────────────────
        claude_m2_unit: list[int] = []
        for p in (data.get("m2_unit_prices") or []):
            try:
                v = int(str(p).replace(".", "").replace(",", ""))
                if 8_000 <= v <= 400_000:
                    claude_m2_unit.append(v)
            except (ValueError, TypeError):
                pass

        # Serbest metinden de m² birim fiyatlarını çek
        text_m2_units = _extract_m2_unit_prices(full_text)
        for v in text_m2_units:
            if v not in claude_m2_unit:
                claude_m2_unit.append(v)

        if len(claude_m2_unit) >= 2:
            cleaned_m2 = _remove_outliers_iqr(claude_m2_unit)
            if len(cleaned_m2) < 2:
                cleaned_m2 = claude_m2_unit
            median_m2 = int(statistics.median(cleaned_m2))
            total = round(median_m2 * square_meters)
            if _PROP_MIN <= total <= _PROP_MAX:
                log.info(f"prop web-search m²-birim tier1: m2p=₺{median_m2:,} × {square_meters}m² = ₺{total:,}")
                if trace is not None:
                    trace.append({
                        "step": "aggregate_property", "source": "claude_m2_unit",
                        "tier": 1, "unit_prices": claude_m2_unit,
                        "median_m2_price": median_m2,
                        "square_meters": square_meters,
                        "total": total,
                    })
                return {
                    "rag_used": True, "tier": 1,
                    "property_estimated_value": total,
                    "avg_m2_price": median_m2,
                    "confidence": "high" if len(cleaned_m2) >= 3 else "medium",
                    "price_count": len(cleaned_m2),
                    "reasoning": (
                        f"{loc}: ₺{median_m2:,}/m² × {square_meters:.0f}m² = ₺{total:,} "
                        f"(Claude web_search m² birim fiyatı)."
                    ),
                    "source": "Claude web_search — m² birim fiyatı",
                }

        listings: list[int] = []
        for p in (data.get("listings") or []):
            n = _to_int(p)
            if n is not None:
                listings.append(n)

        if len(listings) < 3:
            for p in _extract_prices(full_text, 200_000, 500_000_000):
                if p not in listings:
                    listings.append(p)

        # ── Tier 1: gerçek ilan yeterli mi ────────────────────────────────
        if len(listings) >= 3:
            cleaned = _remove_outliers_iqr(listings)
            if len(cleaned) < 3:
                cleaned = listings
            median = statistics.median(cleaned)
            m2p = round(median / max(square_meters, 1))
            confidence = "high" if len(cleaned) >= 6 else "medium"
            log.info(f"prop tier1: n={len(cleaned)} median=₺{int(median):,} confidence={confidence}")
            if trace is not None:
                trace.append({
                    "step": "aggregate_property",
                    "tier": 1,
                    "raw_prices": listings,
                    "after_iqr": cleaned,
                    "median": int(median),
                    "m2_price": m2p,
                    "confidence": confidence,
                })
            return {
                "rag_used": True,
                "tier": 1,
                "property_estimated_value": int(median),
                "avg_m2_price": m2p,
                "confidence": confidence,
                "price_count": len(cleaned),
                "raw_prices": listings,
                "filtered_prices": cleaned,
                "reasoning": f"{loc} {square_meters:.0f}m² — {len(cleaned)} gerçek ilanın medyanı.",
                "source": f"Claude web_search ({len(cleaned)} ilan)",
            }

        # ── Tier 2: segment-bazlı uzman tahmin ────────────────────────────
        expert = _to_int(data.get("expert_estimate"))
        elow   = _to_int(data.get("expert_low"))
        ehigh  = _to_int(data.get("expert_high"))

        if expert is not None and elow is not None and ehigh is not None and elow <= ehigh:
            m2p = round(expert / max(square_meters, 1))
            log.info(f"prop tier2: ₺{elow:,}–₺{ehigh:,} mid=₺{expert:,}")
            if trace is not None:
                trace.append({
                    "step": "aggregate_property",
                    "tier": 2,
                    "result": "insufficient_listings_used_expert_estimate",
                    "listings_found": listings,
                    "expert_low": elow,
                    "expert_high": ehigh,
                    "expert_estimate": expert,
                    "note": data.get("note"),
                })
            return {
                "rag_used": True,
                "tier": 2,
                "property_estimated_value": expert,
                "avg_m2_price": m2p,
                "confidence": "medium",
                "price_count": len(listings),
                "raw_prices": listings,
                "expert_range": [elow, ehigh],
                "reasoning": (
                    f"{loc} {square_meters:.0f}m²: SERP'te yeterli ilan yok ({len(listings)}). "
                    f"Bölge-bazlı uzman tahmin: ₺{elow:,}–₺{ehigh:,}. "
                    f"{data.get('note', '')}"
                ),
                "source": "Claude segment estimate",
            }

        log.warning(f"konut yetersiz tier1+tier2 (listings={len(listings)}, expert={expert})")
        if trace is not None:
            trace.append({
                "step": "aggregate_property",
                "result": "insufficient_data",
                "listings": listings,
                "raw_data": data,
            })
        return None

    except Exception as e:
        log.error(f"property live search hata: {e}")
        if trace is not None:
            trace.append({"step": "web_search", "error": str(e)[:200]})
    return None


# ── Endeksa: tapu tipinden kategori ──────────────────────────────────────────
def _tr_lower(s: str) -> str:
    """Türkçe özel karakterleri ASCII eşdeğeriyle değiştirip küçük harf yapar."""
    _TR_MAP = str.maketrans("İIÇĞÖŞÜçğışöü", "iicgosucgisou")
    return s.translate(_TR_MAP).lower()


def _classify_property_category(tapu_turu: str, nitelik: str) -> str:
    """
    Tapu tür ve niteliğine göre Endeksa kategori kodu döner.
    Endeksa URL'leri:
      konut  → /tr/analiz/turkiye/endeks/satilik/konut
      arsa   → /tr/analiz/turkiye/endeks/satilik/arsa
      ticari → /tr/analiz/turkiye/endeks/satilik/ticari
    """
    combined = _tr_lower(f"{(tapu_turu or '')} {(nitelik or '')}")
    if any(k in combined for k in ["arsa", "tarla", "zeytinlik", "orman", "bosta"]):
        return "arsa"
    if any(k in combined for k in ["dukkan", "isyeri", "is yeri", "ofis", "depo", "ticari", "buro", "fabrika"]):
        return "ticari"
    return "konut"  # daire, mesken, villa, bagımsız bolum, kat irtifakı/mulkiyeti


_ENDEKSA_BASE = "https://www.endeksa.com/tr/analiz/turkiye/endeks/satilik"


def _endeksa_city_m2(
    city: str, district: str, category: str, trace: list | None = None
) -> int | None:
    """
    Serper ile Endeksa şehir/ilçe bazlı m² birim fiyatı çeker.
    Endeksa Angular SPA olduğundan doğrudan çekilemiyor;
    Google'ın Endeksa snippet'leri üzerinden fiyat alınıyor.
    Başarısız olursa None döner → üst katman fallback kaynaklara geçer.
    """
    cat_tr = {"konut": "konut", "arsa": "arsa", "ticari": "ticari işyeri"}.get(category, category)
    loc = f"{district} {city}".strip() if district else city

    queries = [
        f"endeksa {loc} {cat_tr} satılık m2 birim fiyat",
        f"endeksa {city} {category} ortalama metrekare fiyatı 2025",
        f"endeksa.com {loc} {category} satılık",
    ]

    all_text = ""
    for q in queries:
        text = _serper_search(q, num=5)
        if not text:
            break  # SERPER_API_KEY yok — devam etme
        all_text += "\n" + text
        prices = _extract_m2_unit_prices(all_text)
        log.info(f"Endeksa Serper '{q[:50]}' → m² fiyatlar: {prices[:5]}")
        if trace is not None:
            trace.append({"step": "endeksa_serper", "query": q, "unit_prices": prices,
                          "endeksa_ref": f"{_ENDEKSA_BASE}/{category}"})
        if len(prices) >= 2:
            break

    if not all_text:
        return None

    m2_prices = _extract_m2_unit_prices(all_text)
    if not m2_prices:
        log.info(f"Endeksa: {loc} {category} için m² fiyatı bulunamadı")
        return None

    cleaned = _remove_outliers_iqr(m2_prices)
    if not cleaned:
        cleaned = m2_prices
    median = int(statistics.median(cleaned))
    log.info(f"Endeksa tier0: {loc} {category} → ₺{median:,}/m²")
    return median


# ── Public API ────────────────────────────────────────────────────────────────
def rag_estimate_car(
    brand: str, model: str, year: int,
    has_damage: bool = False, ocr_text: str = "",
) -> dict:
    # Cache: aynı araç için 30 dk içinde tekrar sorulursa aynı sonucu dön
    cache_key = f"car:{brand.lower()}:{model.lower()}:{year}:{has_damage}"
    cached = _cache_get(cache_key)
    if cached:
        cached["from_cache"] = True
        return cached

    trace: list = []
    log.info(f"rag_estimate_car: {year} {brand} {model} damage={has_damage}")

    live = _live_search_price(brand, model, year, has_damage, trace=trace)
    if live:
        live["debug_trace"] = trace
        _cache_set(cache_key, live)
        return live

    # Fallback: marka formülü
    age = max(0, datetime.datetime.now().year - int(year))
    base = _BRAND_BASE.get(brand.lower(), _BRAND_BASE["default"])
    dep = max(0.25, (1 - 0.10) ** age)
    damage_factor = 0.82 if has_damage else 1.0
    val = round(base * dep * damage_factor)
    log.info(f"car fallback: brand={brand} age={age} → ₺{val:,}")
    trace.append({
        "step": "fallback_formula",
        "brand_base": base,
        "age": age,
        "depreciation": round(dep, 3),
        "damage_factor": damage_factor,
        "result": val,
    })
    result = {
        "rag_used": False,
        "estimated_car_value": val,
        "confidence": "low",
        "reasoning": f"{brand} marka bazlı formül ({age} yıl).",
        "source": "marka bazlı formül",
        "debug_trace": trace,
    }
    _cache_set(cache_key, result)
    return result


def rag_estimate_property(
    city: str, district: str, square_meters: float, ocr_text: str = "",
    tapu_turu: str = "", nitelik: str = "",
) -> dict:
    category = _classify_property_category(tapu_turu, nitelik)
    endeksa_url = f"{_ENDEKSA_BASE}/{category}"

    # Cache: konum + m² + kategori için 30 dk TTL
    cache_key = f"prop:{(city or '').lower()}:{(district or '').lower()}:{int(square_meters)}:{category}"
    cached = _cache_get(cache_key)
    if cached:
        cached["from_cache"] = True
        return cached

    trace: list = []
    log.info(f"rag_estimate_property: {city} {district} {square_meters}m² category={category}")

    # ── Tier 0: Endeksa şehir/ilçe m² birim fiyatı ───────────────────────────
    _PROP_MIN, _PROP_MAX = 500_000, 500_000_000
    endeksa_m2 = _endeksa_city_m2(city, district, category, trace=trace)
    if endeksa_m2:
        total = round(endeksa_m2 * square_meters)
        if _PROP_MIN <= total <= _PROP_MAX:
            loc = f"{city} {district}".strip() if district else city
            result = {
                "rag_used": True,
                "tier": 0,
                "property_estimated_value": total,
                "avg_m2_price": endeksa_m2,
                "confidence": "high",
                "price_count": 1,
                "endeksa_category": category,
                "reasoning": (
                    f"{loc} [{category}]: Endeksa ₺{endeksa_m2:,}/m² × {square_meters:.0f}m² = ₺{total:,}."
                ),
                "source": f"Endeksa ({endeksa_url})",
                "debug_trace": trace,
            }
            _cache_set(cache_key, result)
            return result

    live = _live_search_property(city, district, square_meters, trace=trace)
    if live:
        live["debug_trace"] = trace
        _cache_set(cache_key, live)
        return live

    # Fallback: şehir bazlı formül
    city_norm = (city or "").lower().translate(str.maketrans(
        "çğışöüâîû", "cgisouaiu"
    ))
    m2 = _CITY_M2.get(city_norm, _CITY_M2["default"])
    val = round(m2 * square_meters)
    log.info(f"property fallback: city={city} category={category} m2p=₺{m2:,} → ₺{val:,}")
    trace.append({
        "step": "fallback_formula",
        "city_normalized": city_norm,
        "category": category,
        "m2_price": m2,
        "square_meters": square_meters,
        "result": val,
    })
    fallback_result = {
        "rag_used": False,
        "property_estimated_value": val,
        "avg_m2_price": m2,
        "confidence": "low",
        "endeksa_category": category,
        "reasoning": f"{city} {category} için ₺{m2:,}/m² × {square_meters}m².",
        "source": "şehir bazlı formül",
        "debug_trace": trace,
    }
    _cache_set(cache_key, fallback_result)
    return fallback_result
