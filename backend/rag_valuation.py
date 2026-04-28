"""
PSDS — Araç ve Konut Değerleme Motoru

Akış:
  1. LIVE SEARCH  — Claude web_search tool ile arabam.com/sahibinden.com canlı fiyat
  2. FALLBACK     — Claude API yok veya search başarısız → model fiyat tablosu
  3. LAST RESORT  — Tablo yok → marka bazlı formül
"""

import os
import datetime

# ── Model-bazlı referans tablosu (sadece fallback) ────────────────────────────
_MODEL_PRICES: dict[str, dict[int, int]] = {
    "fiat|egea":          {2015: 430_000, 2017: 530_000, 2019: 680_000, 2021: 870_000, 2023: 1_050_000, 2025: 1_250_000},
    "dacia|sandero":      {2015: 370_000, 2017: 460_000, 2019: 590_000, 2021: 780_000, 2023: 980_000,   2025: 1_150_000},
    "dacia|duster":       {2015: 500_000, 2017: 620_000, 2019: 780_000, 2021: 980_000, 2023: 1_250_000, 2025: 1_500_000},
    "renault|clio":       {2015: 420_000, 2017: 530_000, 2019: 670_000, 2021: 870_000, 2023: 1_100_000, 2025: 1_350_000},
    "renault|megane":     {2015: 500_000, 2017: 630_000, 2019: 800_000, 2021: 1_050_000, 2023: 1_300_000, 2025: 1_600_000},
    "renault|kadjar":     {2016: 650_000, 2018: 820_000, 2020: 1_050_000, 2022: 1_350_000, 2024: 1_700_000},
    "volkswagen|polo":    {2015: 520_000, 2017: 660_000, 2019: 850_000, 2021: 1_100_000, 2023: 1_450_000, 2025: 1_800_000},
    "volkswagen|golf":    {2015: 650_000, 2017: 830_000, 2019: 1_050_000, 2021: 1_400_000, 2023: 1_850_000, 2025: 2_300_000},
    "volkswagen|passat":  {2015: 750_000, 2017: 950_000, 2019: 1_200_000, 2021: 1_600_000, 2023: 2_100_000, 2025: 2_700_000},
    "volkswagen|tiguan":  {2016: 900_000, 2018: 1_150_000, 2020: 1_500_000, 2022: 2_000_000, 2024: 2_700_000},
    "toyota|yaris":       {2015: 480_000, 2017: 600_000, 2019: 780_000, 2021: 1_000_000, 2023: 1_300_000, 2025: 1_600_000},
    "toyota|corolla":     {2015: 600_000, 2017: 780_000, 2019: 1_000_000, 2021: 1_350_000, 2023: 1_750_000, 2025: 2_200_000},
    "toyota|c-hr":        {2017: 900_000, 2019: 1_200_000, 2021: 1_600_000, 2023: 2_200_000, 2025: 2_800_000},
    "toyota|rav4":        {2015: 950_000, 2017: 1_200_000, 2019: 1_600_000, 2021: 2_100_000, 2023: 2_900_000, 2025: 3_700_000},
    "ford|focus":         {2015: 530_000, 2017: 670_000, 2019: 860_000, 2021: 1_150_000, 2023: 1_500_000, 2025: 1_850_000},
    "ford|kuga":          {2015: 680_000, 2017: 870_000, 2019: 1_100_000, 2021: 1_500_000, 2023: 2_000_000, 2025: 2_600_000},
    "hyundai|i20":        {2015: 420_000, 2017: 530_000, 2019: 680_000, 2021: 900_000, 2023: 1_150_000, 2025: 1_450_000},
    "hyundai|i30":        {2015: 530_000, 2017: 670_000, 2019: 860_000, 2021: 1_150_000, 2023: 1_500_000, 2025: 1_850_000},
    "hyundai|tucson":     {2015: 700_000, 2017: 900_000, 2019: 1_150_000, 2021: 1_550_000, 2023: 2_100_000, 2025: 2_700_000},
    "kia|ceed":           {2015: 520_000, 2017: 660_000, 2019: 850_000, 2021: 1_130_000, 2023: 1_480_000, 2025: 1_850_000},
    "kia|sportage":       {2015: 680_000, 2017: 870_000, 2019: 1_100_000, 2021: 1_500_000, 2023: 2_050_000, 2025: 2_650_000},
    "opel|corsa":         {2015: 420_000, 2017: 530_000, 2019: 680_000, 2021: 900_000, 2023: 1_150_000, 2025: 1_450_000},
    "opel|astra":         {2015: 520_000, 2017: 660_000, 2019: 840_000, 2021: 1_100_000, 2023: 1_450_000, 2025: 1_800_000},
    "honda|civic":        {2015: 570_000, 2017: 720_000, 2019: 920_000, 2021: 1_250_000, 2023: 1_700_000, 2025: 2_200_000},
    "bmw|3 serisi":       {2015: 950_000, 2017: 1_250_000, 2019: 1_650_000, 2021: 2_300_000, 2023: 3_300_000, 2025: 4_500_000},
    "bmw|5 serisi":       {2015: 1_300_000, 2017: 1_700_000, 2019: 2_200_000, 2021: 3_100_000, 2023: 4_500_000, 2025: 6_200_000},
    "bmw|7 serisi":       {2015: 2_000_000, 2017: 2_700_000, 2019: 3_800_000, 2021: 5_500_000, 2023: 8_500_000, 2025: 12_000_000},
    "bmw|x3":             {2015: 1_100_000, 2017: 1_400_000, 2019: 1_850_000, 2021: 2_600_000, 2023: 3_800_000, 2025: 5_100_000},
    "bmw|x5":             {2015: 1_800_000, 2017: 2_300_000, 2019: 3_200_000, 2021: 4_800_000, 2023: 7_000_000, 2025: 9_500_000},
    "mercedes-benz|c serisi": {2015: 1_050_000, 2017: 1_380_000, 2019: 1_850_000, 2021: 2_600_000, 2023: 3_800_000, 2025: 5_200_000},
    "mercedes-benz|e serisi": {2015: 1_450_000, 2017: 1_900_000, 2019: 2_550_000, 2021: 3_600_000, 2023: 5_200_000, 2025: 7_200_000},
    "mercedes-benz|s serisi": {2018: 3_000_000, 2019: 4_000_000, 2020: 6_000_000, 2021: 8_500_000, 2022: 12_500_000, 2023: 16_000_000, 2025: 22_000_000},
    "mercedes-benz|gle":  {2016: 1_800_000, 2018: 2_500_000, 2020: 4_000_000, 2022: 6_500_000, 2024: 9_000_000},
    "mercedes-benz|gls":  {2018: 3_500_000, 2020: 5_500_000, 2022: 9_000_000, 2024: 13_000_000},
    "audi|a3":            {2015: 750_000, 2017: 970_000, 2019: 1_280_000, 2021: 1_800_000, 2023: 2_600_000, 2025: 3_500_000},
    "audi|a4":            {2015: 950_000, 2017: 1_250_000, 2019: 1_650_000, 2021: 2_350_000, 2023: 3_400_000, 2025: 4_600_000},
    "audi|a6":            {2015: 1_300_000, 2017: 1_700_000, 2019: 2_300_000, 2021: 3_300_000, 2023: 5_000_000, 2025: 7_000_000},
    "audi|q5":            {2016: 1_400_000, 2018: 1_900_000, 2020: 2_800_000, 2022: 4_200_000, 2024: 6_000_000},
    "suzuki|swift":       {2015: 380_000, 2017: 480_000, 2019: 620_000, 2021: 830_000, 2023: 1_100_000, 2025: 1_400_000},
    "suzuki|vitara":      {2015: 560_000, 2017: 720_000, 2019: 930_000, 2021: 1_250_000, 2023: 1_700_000, 2025: 2_200_000},
    "land rover|defender":{2019: 3_000_000, 2020: 4_500_000, 2021: 6_000_000, 2022: 8_000_000, 2023: 10_000_000, 2025: 13_000_000},
    "land rover|discovery":{2018: 2_500_000, 2020: 3_800_000, 2022: 6_500_000, 2024: 9_000_000},
    "land rover|range rover":{2018: 3_500_000, 2020: 6_000_000, 2022: 10_000_000, 2024: 15_000_000},
    "porsche|cayenne":    {2016: 2_000_000, 2018: 3_000_000, 2020: 5_000_000, 2022: 8_000_000, 2024: 12_000_000},
    "porsche|macan":      {2016: 1_500_000, 2018: 2_200_000, 2020: 3_500_000, 2022: 5_500_000, 2024: 8_000_000},
    "togg|t10x":          {2023: 1_350_000, 2024: 1_600_000, 2025: 1_850_000},
}

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
    "togg": 1_700_000, "default": 1_600_000,
}

_CITY_M2: dict[str, int] = {
    "istanbul": 120_000, "ankara": 50_000, "izmir": 70_000,
    "bursa": 42_000, "antalya": 50_000, "kocaeli": 38_000,
    "mersin": 28_000, "konya": 25_000, "adana": 22_000,
    "samsun": 22_000, "trabzon": 25_000, "kayseri": 22_000,
    "eskisehir": 28_000, "gaziantep": 20_000, "diyarbakir": 16_000,
    "default": 20_000,
}


def _lookup_model_price(brand: str, model: str, year: int) -> int | None:
    brand_l = brand.lower().replace("_", "-")
    model_l = model.lower().strip()

    # Tam eşleşme
    key = f"{brand_l}|{model_l}"
    table = _MODEL_PRICES.get(key)

    if not table:
        for k, v in _MODEL_PRICES.items():
            kb, km = k.split("|", 1)
            # Marka kontrolü (mercedes-benz, mercedes her ikisi de eşleşsin)
            brand_match = (
                brand_l == kb
                or brand_l.startswith(kb)
                or kb.startswith(brand_l.split("-")[0])
            )
            if not brand_match:
                continue
            # Model kontrolü: model'in ilk harfi/kelimesi tablo anahtarıyla örtüşüyor mu?
            model_first = model_l.split()[0] if model_l else ""
            km_first = km.split()[0] if km else ""
            if (
                model_l in km
                or km in model_l
                or model_first == km_first
                or (len(model_first) >= 1 and model_first[0] == km_first[0] and len(km_first) >= 1)
            ):
                table = v
                break

    if not table:
        return None
    years = sorted(table.keys())
    if year <= years[0]:  return table[years[0]]
    if year >= years[-1]: return table[years[-1]]
    for i in range(len(years) - 1):
        y0, y1 = years[i], years[i + 1]
        if y0 <= year <= y1:
            ratio = (year - y0) / (y1 - y0)
            return round(table[y0] + (table[y1] - table[y0]) * ratio)
    return None


_PRICE_RE = [
    r'(\d{1,3}(?:\.\d{3})+)\s*(?:TL|₺)',      # 12.249.900 TL
    r'(?:TL|₺)\s*(\d{1,3}(?:\.\d{3})+)',      # ₺ 12.249.900
    r'(\d{1,3}(?:,\d{3})+)\s*(?:TL|₺)',       # 12,249,900 TL
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


def _remove_outliers(prices: list[int]) -> list[int]:
    if len(prices) < 4:
        return prices
    s = sorted(prices)
    n = len(s)
    q1, q3 = s[n // 4], s[(3 * n) // 4]
    iqr = q3 - q1
    if iqr == 0:
        return prices
    lo, hi = q1 - 1.5 * iqr, q3 + 1.5 * iqr
    filtered = [p for p in s if lo <= p <= hi]
    return filtered if len(filtered) >= 3 else s




# ── Canlı web araması ile fiyat çekme ────────────────────────────────────────
def _live_search_price(brand: str, model: str, year: int, has_damage: bool) -> dict | None:
    """
    Google/DuckDuckGo arama snippet HTML'inden TL fiyatlarını regex ile çeker.
    IQR uygular, ortalar. Siteye girme — sadece snippet metni kullanılır.
    """
    try:
        from backend.web_retrieval import fetch_car_prices
        result = fetch_car_prices(brand, model, year)
        if not result.get("found") or result["count"] < 2:
            return None

        avg = result["avg"]
        damage_factor = 0.82 if has_damage else 1.0
        val = round(avg * damage_factor)

        return {
            "rag_used": True,
            "estimated_car_value": val,
            "confidence": "high" if result["count"] >= 5 else "medium",
            "reasoning": f"{result['count']} ilan ortalaması (IQR temizlendi): ₺{avg:,}",
            "source": "sahibinden / arabam Google snippet",
        }
    except Exception as e:
        print(f"[RAG] Live search error: {e}")
    return None


def _live_search_property(city: str, district: str, square_meters: float) -> dict | None:
    """
    Google/DuckDuckGo arama snippet HTML'inden konut TL fiyatlarını regex ile çeker.
    IQR uygular, m² fiyatına böler.
    """
    try:
        from backend.web_retrieval import fetch_property_prices
        result = fetch_property_prices(city, district)
        if not result.get("found") or result["count"] < 2:
            return None

        avg_total = result["avg_total"]
        m2p = round(avg_total / max(square_meters, 1))
        val = round(avg_total)

        return {
            "rag_used": True,
            "property_estimated_value": val,
            "avg_m2_price": m2p,
            "confidence": "high" if result["count"] >= 5 else "medium",
            "reasoning": f"{result['count']} ilan ortalaması (IQR temizlendi): ₺{avg_total:,}",
            "source": "sahibinden / hepsiemlak Google snippet",
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

    # 1. Sahibinden snippet'lerinden canlı fiyat
    live = _live_search_price(brand, model, year, has_damage)
    if live:
        return live

    # 2. Model fiyat tablosu (fallback)
    ref_price = _lookup_model_price(brand, model, year)
    if ref_price:
        val = round(ref_price * damage_factor)
        return {
            "rag_used": True,
            "estimated_car_value": val,
            "confidence": "medium",
            "reasoning": f"{brand} {model} {year} referans tablo fiyatı.",
            "source": "model fiyat tablosu",
        }

    # 3. Marka bazlı formül (son çare)
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
    # 1. Claude web_search ile gerçek zamanlı fiyat (primary)
    live = _live_search_property(city, district, square_meters)
    if live:
        return live

    # 3. Şehir bazlı formül
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
