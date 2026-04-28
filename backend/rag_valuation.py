"""
PSDS — Araç ve Konut Değerleme
1. Claude (training knowledge) ile fiyat tahmini
2. Fallback: marka/şehir bazlı formül
"""

import os
import re
import datetime

# ── Türkiye ikinci el araç referans fiyatları (2025 ortalama, TL) ─────────────
# Bu fiyatlar fallback için — her zaman önce Claude'a sorulur
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


def _ask_claude(prompt: str) -> str:
    """
    Claude'a direkt sor — web_search tool kullanma, training knowledge'dan cevap ver.
    Model sırası: haiku-4-5 → 3-5-haiku → sonnet-4-5
    """
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return ""
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)

        models = [
            "claude-haiku-4-5-20251001",
            "claude-3-5-haiku-20241022",
            "claude-sonnet-4-5-20251001",
        ]
        for model_name in models:
            try:
                resp = client.messages.create(
                    model=model_name,
                    max_tokens=60,
                    messages=[{"role": "user", "content": prompt}],
                )
                text = ""
                for block in resp.content:
                    if hasattr(block, "text"):
                        text += block.text
                if text.strip():
                    print(f"[RAG] Model={model_name} | Yanıt: {text[:200]}")
                    return text
            except Exception as model_err:
                print(f"[RAG] Model {model_name} hata: {model_err}")
                continue
    except Exception as e:
        print(f"[RAG] Claude API error: {e}")
    return ""


# ── ARAÇ fiyat tahmini ────────────────────────────────────────────────────────

def _live_search_price(brand: str, model: str, year: int, has_damage: bool) -> dict | None:
    """Claude'un bilgisinden Türkiye ikinci el araç fiyatı."""
    hasar = "Hasar kaydı var, %15-20 değer düşüklüğünü fiyata yansıt." if has_damage else "Hasar yok."
    prompt = (
        f"Türkiye ikinci el araç piyasasında {year} model {brand} {model} aracının "
        f"2025-2026 yılı gerçekçi ortalama ikinci el satış fiyatı nedir? "
        f"{hasar} "
        f"Türkiye'deki yüksek enflasyon, döviz kuru ve arz-talep dengesini göz önünde bulundur. "
        f"SADECE şu formatta yaz, başka hiçbir şey yazma:\n"
        f"FIYAT: 1.250.000 TL"
    )

    text = _ask_claude(prompt)
    if not text:
        return None

    m = re.search(r'FIYAT[:\s]+(\d[\d.,]+)\s*(?:TL|₺)?', text, re.IGNORECASE)
    if not m:
        return None

    try:
        val = int(m.group(1).replace(".", "").replace(",", ""))
    except ValueError:
        return None

    if not (100_000 <= val <= 100_000_000):
        return None

    return {
        "rag_used": True,
        "estimated_car_value": val,
        "confidence": "medium",
        "reasoning": f"{year} {brand} {model} Claude bilgi tahmini.",
        "source": "Claude AI",
    }


# ── KONUT fiyat tahmini ───────────────────────────────────────────────────────

def _live_search_property(city: str, district: str, square_meters: float) -> dict | None:
    """Claude'un bilgisinden Türkiye konut fiyatı."""
    loc = f"{city} {district}".strip()
    prompt = (
        f"Türkiye'de {loc} bölgesinde {square_meters} m² dairenin "
        f"2025-2026 yılı gerçekçi ortalama satış fiyatı nedir? "
        f"Türkiye'deki yüksek enflasyon ve bölgesel fiyat farklarını göz önünde bulundur. "
        f"SADECE şu formatta yaz, başka hiçbir şey yazma:\n"
        f"FIYAT: 4.500.000 TL"
    )

    text = _ask_claude(prompt)
    if not text:
        return None

    m = re.search(r'FIYAT[:\s]+(\d[\d.,]+)\s*(?:TL|₺)?', text, re.IGNORECASE)
    if not m:
        return None

    try:
        val = int(m.group(1).replace(".", "").replace(",", ""))
    except ValueError:
        return None

    if not (200_000 <= val <= 500_000_000):
        return None

    m2p = round(val / max(square_meters, 1))
    return {
        "rag_used": True,
        "property_estimated_value": val,
        "avg_m2_price": m2p,
        "confidence": "medium",
        "reasoning": f"{loc} {square_meters}m² Claude bilgi tahmini.",
        "source": "Claude AI",
    }


# ── ARAÇ TAHMİNİ (public) ────────────────────────────────────────────────────
def rag_estimate_car(
    brand: str, model: str, year: int,
    has_damage: bool = False, ocr_text: str = "",
) -> dict:
    damage_factor = 0.82 if has_damage else 1.0

    # 1. Claude bilgisinden fiyat
    live = _live_search_price(brand, model, year, has_damage)
    if live:
        return live

    # 2. Marka bazlı formül (fallback)
    # Türkiye'de yüksek enflasyon nedeniyle eski araçlar daha az değer kaybeder
    # Min %40 taban değer, yıllık %8 değer kaybı
    age = max(0, datetime.datetime.now().year - int(year))
    base = _BRAND_BASE.get(brand.lower(), _BRAND_BASE["default"])
    dep = max(0.40, (1 - 0.08) ** age)
    val = round(base * dep * damage_factor)
    return {
        "rag_used": False,
        "estimated_car_value": val,
        "confidence": "low",
        "reasoning": f"{brand} marka bazlı formül ({age} yıl, dep={dep:.2f}).",
        "source": "marka bazlı formül",
    }


# ── EMLAK TAHMİNİ (public) ───────────────────────────────────────────────────
def rag_estimate_property(
    city: str, district: str, square_meters: float, ocr_text: str = "",
) -> dict:
    # 1. Claude bilgisinden fiyat
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
