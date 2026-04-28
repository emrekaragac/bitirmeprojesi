"""
PSDS — Araç ve Konut Değerleme
1. Claude web_search ile güncel piyasa fiyatı
2. Fallback: marka/şehir bazlı formül
"""

import os
import re
import datetime
import statistics

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

_PRICE_RE = [
    r'(\d{1,3}(?:\.\d{3})+)\s*(?:TL|₺)',
    r'(?:TL|₺)\s*(\d{1,3}(?:\.\d{3})+)',
    r'(\d{1,3}(?:,\d{3})+)\s*(?:TL|₺)',
]


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


def _run_web_search(client, model: str, prompt: str, max_turns: int = 5) -> str:
    tools = [{"type": "web_search_20250305", "name": "web_search"}]
    messages = [{"role": "user", "content": prompt}]
    full_text = ""
    for _ in range(max_turns):
        resp = client.messages.create(model=model, max_tokens=512, tools=tools, messages=messages)
        for block in resp.content:
            if hasattr(block, "text"):
                full_text += block.text
        if resp.stop_reason == "end_turn":
            break
        if resp.stop_reason == "tool_use":
            tool_results = [
                {"type": "tool_result", "tool_use_id": b.id, "content": ""}
                for b in resp.content if hasattr(b, "type") and b.type == "tool_use"
            ]
            messages.append({"role": "assistant", "content": resp.content})
            if tool_results:
                messages.append({"role": "user", "content": tool_results})
            else:
                break
        else:
            break
    return full_text


def _live_search_price(brand: str, model: str, year: int, has_damage: bool) -> dict | None:
    """
    Claude web_search ile güncel Türkiye ikinci el piyasa fiyatı.
    Claude hem web araması yapar hem bilgisiyle değerlendirir.
    """
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return None
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)

        hasar = "Hasar kaydı var, fiyata yansıt." if has_damage else ""
        prompt = (
            f"'{year} {brand} {model} ikinci el türkiye' diye ara. "
            f"Arama sonuçları ve bilgine dayanarak bu aracın 2025 Türkiye "
            f"ikinci el ortalama piyasa değerini ver. {hasar} "
            f"Sadece şunu yaz, başka hiçbir şey yazma:\n"
            f"FIYAT: 1.250.000 TL"
        )

        full_text = _run_web_search(client, "claude-haiku-4-5-20251001", prompt)
        print(f"[RAG] Claude yanıtı: {full_text[:300]}")

        m = re.search(r'FIYAT[:\s]+(\d[\d.]+)\s*TL', full_text, re.IGNORECASE)
        if m:
            val = int(m.group(1).replace(".", ""))
        else:
            prices = _extract_prices(full_text, 50_000, 100_000_000)
            if not prices:
                return None
            val = prices[len(prices) // 2]

        if not (50_000 <= val <= 100_000_000):
            return None

        return {
            "rag_used": True,
            "estimated_car_value": val,
            "confidence": "medium",
            "reasoning": f"{year} {brand} {model} güncel piyasa değeri.",
            "source": "Claude web_search",
        }
    except Exception as e:
        print(f"[RAG] Live search error: {e}")
    return None


def _live_search_property(city: str, district: str, square_meters: float) -> dict | None:
    """Claude web_search ile güncel Türkiye konut piyasa fiyatı."""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return None
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)

        loc = f"{city} {district}".strip()
        prompt = (
            f"'{loc} satılık daire' diye ara. "
            f"Arama sonuçları ve bilgine dayanarak {loc} bölgesinde "
            f"{square_meters} m² dairenin 2025 Türkiye ortalama piyasa değerini ver. "
            f"Sadece şunu yaz, başka hiçbir şey yazma:\n"
            f"FIYAT: 4.500.000 TL"
        )

        full_text = _run_web_search(client, "claude-haiku-4-5-20251001", prompt)
        print(f"[RAG] Konut Claude yanıtı: {full_text[:300]}")

        m = re.search(r'FIYAT[:\s]+(\d[\d.]+)\s*TL', full_text, re.IGNORECASE)
        if m:
            val = int(m.group(1).replace(".", ""))
        else:
            prices = _extract_prices(full_text, 200_000, 500_000_000)
            if not prices:
                return None
            val = prices[len(prices) // 2]

        if not (200_000 <= val <= 500_000_000):
            return None

        m2p = round(val / max(square_meters, 1))
        return {
            "rag_used": True,
            "property_estimated_value": val,
            "avg_m2_price": m2p,
            "confidence": "medium",
            "reasoning": f"{loc} {square_meters}m² güncel piyasa değeri.",
            "source": "Claude web_search",
        }
    except Exception as e:
        print(f"[RAG] Live property search error: {e}")
    return None


# ── ARAÇ TAHMİNİ ─────────────────────────────────────────────────────────────
def rag_estimate_car(
    brand: str, model: str, year: int,
    has_damage: bool = False, ocr_text: str = "",
) -> dict:
    damage_factor = 0.82 if has_damage else 1.0

    # 1. Claude web_search
    live = _live_search_price(brand, model, year, has_damage)
    if live:
        return live

    # 2. Marka bazlı formül (fallback)
    age = max(0, datetime.datetime.now().year - int(year))
    base = _BRAND_BASE.get(brand.lower(), _BRAND_BASE["default"])
    dep = max(0.25, (1 - 0.10) ** age)
    val = round(base * dep * damage_factor)
    return {
        "rag_used": False,
        "estimated_car_value": val,
        "confidence": "low",
        "reasoning": f"{brand} marka bazlı formül ({age} yıl).",
        "source": "marka bazlı formül",
    }


# ── EMLAK TAHMİNİ ─────────────────────────────────────────────────────────────
def rag_estimate_property(
    city: str, district: str, square_meters: float, ocr_text: str = "",
) -> dict:
    # 1. Claude web_search
    live = _live_search_property(city, district, square_meters)
    if live:
        return live

    # 2. Şehir bazlı formül (fallback)
    city_norm = city.lower()
    for tr, en in zip("çğışöüÇĞİŞÖÜ", "cgisouCGISOu"):
        city_norm = city_norm.replace(tr, en)
    m2 = _CITY_M2.get(city_norm, _CITY_M2["default"])
    val = round(m2 * square_meters)
    return {
        "rag_used": False,
        "property_estimated_value": val,
        "avg_m2_price": m2,
        "confidence": "low",
        "reasoning": f"{city} için ₺{m2:,}/m² × {square_meters}m².",
        "source": "şehir bazlı formül",
    }
