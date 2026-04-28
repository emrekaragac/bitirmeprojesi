"""
PSDS — Araç ve Konut Değerleme

Akış:
  1. Claude web_search → güvenilir Türk satış sitelerinden TL fiyat listesi
  2. IQR ile outlier filtresi → trimmed median
  3. Yetersiz veri varsa fallback formül (marka/şehir bazlı)

Tüm adımlar `_RAG_TRACE` listesine yazılır → API response'una gömülür → tarayıcı console'unda görünür.
"""

import os
import re
import json
import logging
import datetime
import statistics

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

_CAR_DOMAINS = [
    "sahibinden.com", "arabam.com", "letgo.com", "ikinciel.com",
    "dod.com.tr", "otokocikincieli.com.tr", "borusanoto.com",
    "otomobilcim.com", "gardiyan.com.tr",
]

_PROPERTY_DOMAINS = [
    "sahibinden.com", "hepsiemlak.com", "emlakjet.com",
    "zingat.com", "milliyetemlak.com", "endeksa.com",
]

_PRICE_RE = [
    r'(\d{1,3}(?:\.\d{3})+)\s*(?:TL|₺)',
    r'(?:TL|₺)\s*(\d{1,3}(?:\.\d{3})+)',
    r'(\d{1,3}(?:,\d{3})+)\s*(?:TL|₺)',
    r'(\d{6,9})\s*(?:TL|₺)',
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
            "raw_preview": full_text[:400],
        })
    return full_text


# ── Live search: araç ─────────────────────────────────────────────────────────
def _live_search_price(
    brand: str, model: str, year: int, has_damage: bool,
    trace: list | None = None,
) -> dict | None:
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        log.warning("ANTHROPIC_API_KEY yok — web search atlandı")
        return None
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)

        prompt = (
            f"Türkiye 2. el otomobil ilanlarını ara: \"{year} {brand} {model}\".\n"
            f"SADECE arama snippet'lerinde DOĞRUDAN gördüğün TL fiyatları topla. "
            f"Tahmin yapma, training data kullanma, hesaplama yapma — sadece SERP'te yazan rakamlar.\n"
            f"Atla: yedek parça, kiralama, 0 km yeni model, hasar kayıtlı, ağır hasarlı.\n\n"
            f"Şu JSON formatında yanıt ver, başka metin yazma:\n"
            f'{{"prices": [425000, 480000, 510000], "skipped": 2, "note": "kısa not"}}'
        )

        full_text = _run_web_search(
            client, "claude-haiku-4-5-20251001", prompt,
            allowed_domains=_CAR_DOMAINS, max_uses=5, trace=trace,
        )
        log.info(f"car raw: {full_text[:200]}")

        # Tercihen JSON parse et
        prices: list[int] = []
        data = _parse_json_block(full_text)
        if data and isinstance(data.get("prices"), list):
            for p in data["prices"]:
                try:
                    v = int(str(p).replace(".", "").replace(",", ""))
                    if 50_000 <= v <= 100_000_000:
                        prices.append(v)
                except (ValueError, TypeError):
                    pass

        # JSON yoksa serbest metinden çek
        if len(prices) < 3:
            extra = _extract_prices(full_text, 50_000, 100_000_000)
            for p in extra:
                if p not in prices:
                    prices.append(p)

        if len(prices) < 3:
            log.warning(f"yetersiz fiyat (n={len(prices)}) — fallback'e düşülüyor")
            if trace is not None:
                trace.append({
                    "step": "aggregate_car",
                    "result": "insufficient_data",
                    "raw_prices": prices,
                })
            return None

        cleaned = _remove_outliers_iqr(prices)
        if len(cleaned) < 3:
            cleaned = prices  # IQR çok agresifse geri al

        median = statistics.median(cleaned)
        if has_damage:
            median = round(median * 0.82)

        confidence = "high" if len(cleaned) >= 6 else "medium" if len(cleaned) >= 3 else "low"
        log.info(f"car: n={len(cleaned)} median=₺{int(median):,} confidence={confidence}")

        if trace is not None:
            trace.append({
                "step": "aggregate_car",
                "raw_prices": prices,
                "after_iqr": cleaned,
                "median": int(median),
                "has_damage_discount": has_damage,
                "confidence": confidence,
            })

        return {
            "rag_used": True,
            "estimated_car_value": int(median),
            "confidence": confidence,
            "price_count": len(cleaned),
            "raw_prices": prices,
            "filtered_prices": cleaned,
            "reasoning": f"{year} {brand} {model} — {len(cleaned)} ilanın medyanı.",
            "source": f"Claude web_search ({len(cleaned)} ilan)",
        }
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
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        log.warning("ANTHROPIC_API_KEY yok — konut web search atlandı")
        return None
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)

        loc = f"{city} {district}".strip()
        prompt = (
            f"Türkiye 2. el konut satılık ilanlarını ara: \"{loc}\" bölgesinde "
            f"yaklaşık {square_meters:.0f} m² daire.\n"
            f"SADECE arama snippet'lerinde DOĞRUDAN gördüğün TL fiyatları topla. "
            f"Tahmin yapma, training data kullanma. Kiralık ilanları atla.\n\n"
            f"Şu JSON formatında yanıt ver, başka metin yazma:\n"
            f'{{"prices": [4500000, 5200000, 6100000], "note": "kısa not"}}'
        )

        full_text = _run_web_search(
            client, "claude-haiku-4-5-20251001", prompt,
            allowed_domains=_PROPERTY_DOMAINS, max_uses=5, trace=trace,
        )
        log.info(f"property raw: {full_text[:200]}")

        prices: list[int] = []
        data = _parse_json_block(full_text)
        if data and isinstance(data.get("prices"), list):
            for p in data["prices"]:
                try:
                    v = int(str(p).replace(".", "").replace(",", ""))
                    if 200_000 <= v <= 500_000_000:
                        prices.append(v)
                except (ValueError, TypeError):
                    pass

        if len(prices) < 3:
            extra = _extract_prices(full_text, 200_000, 500_000_000)
            for p in extra:
                if p not in prices:
                    prices.append(p)

        if len(prices) < 3:
            log.warning(f"konut yetersiz fiyat (n={len(prices)}) — fallback")
            if trace is not None:
                trace.append({
                    "step": "aggregate_property",
                    "result": "insufficient_data",
                    "raw_prices": prices,
                })
            return None

        cleaned = _remove_outliers_iqr(prices)
        if len(cleaned) < 3:
            cleaned = prices

        median = statistics.median(cleaned)
        m2p = round(median / max(square_meters, 1))
        confidence = "high" if len(cleaned) >= 6 else "medium" if len(cleaned) >= 3 else "low"
        log.info(f"property: n={len(cleaned)} median=₺{int(median):,} m2p=₺{m2p:,} confidence={confidence}")

        if trace is not None:
            trace.append({
                "step": "aggregate_property",
                "raw_prices": prices,
                "after_iqr": cleaned,
                "median": int(median),
                "m2_price": m2p,
                "confidence": confidence,
            })

        return {
            "rag_used": True,
            "property_estimated_value": int(median),
            "avg_m2_price": m2p,
            "confidence": confidence,
            "price_count": len(cleaned),
            "raw_prices": prices,
            "filtered_prices": cleaned,
            "reasoning": f"{loc} {square_meters:.0f}m² — {len(cleaned)} ilanın medyanı.",
            "source": f"Claude web_search ({len(cleaned)} ilan)",
        }
    except Exception as e:
        log.error(f"property live search hata: {e}")
        if trace is not None:
            trace.append({"step": "web_search", "error": str(e)[:200]})
    return None


# ── Public API ────────────────────────────────────────────────────────────────
def rag_estimate_car(
    brand: str, model: str, year: int,
    has_damage: bool = False, ocr_text: str = "",
) -> dict:
    trace: list = []
    log.info(f"rag_estimate_car: {year} {brand} {model} damage={has_damage}")

    live = _live_search_price(brand, model, year, has_damage, trace=trace)
    if live:
        live["debug_trace"] = trace
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
    return {
        "rag_used": False,
        "estimated_car_value": val,
        "confidence": "low",
        "reasoning": f"{brand} marka bazlı formül ({age} yıl).",
        "source": "marka bazlı formül",
        "debug_trace": trace,
    }


def rag_estimate_property(
    city: str, district: str, square_meters: float, ocr_text: str = "",
) -> dict:
    trace: list = []
    log.info(f"rag_estimate_property: {city} {district} {square_meters}m²")

    live = _live_search_property(city, district, square_meters, trace=trace)
    if live:
        live["debug_trace"] = trace
        return live

    # Fallback: şehir bazlı formül
    city_norm = (city or "").lower().translate(str.maketrans(
        "çğışöüâîû", "cgisouaiu"
    ))
    m2 = _CITY_M2.get(city_norm, _CITY_M2["default"])
    val = round(m2 * square_meters)
    log.info(f"property fallback: city={city} m2p=₺{m2:,} → ₺{val:,}")
    trace.append({
        "step": "fallback_formula",
        "city_normalized": city_norm,
        "m2_price": m2,
        "square_meters": square_meters,
        "result": val,
    })
    return {
        "rag_used": False,
        "property_estimated_value": val,
        "avg_m2_price": m2,
        "confidence": "low",
        "reasoning": f"{city} için ₺{m2:,}/m² × {square_meters}m².",
        "source": "şehir bazlı formül",
        "debug_trace": trace,
    }
