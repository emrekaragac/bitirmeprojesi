import pandas as pd
import datetime


def normalize_turkish(text: str) -> str:
    if not text:
        return ""
    replacements = {
        "ı": "i", "İ": "I", "ğ": "g", "Ğ": "G",
        "ü": "u", "Ü": "U", "ş": "s", "Ş": "S",
        "ö": "o", "Ö": "O", "ç": "c", "Ç": "C",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text.strip().lower()


# Marka başlangıç fiyatları (2024 Türkiye ortalama, TL)
CAR_BASE_PRICES = {
    "bmw": 3_500_000,
    "mercedes": 4_000_000,
    "audi": 3_200_000,
    "porsche": 8_000_000,
    "volvo": 2_500_000,
    "land rover": 5_000_000,
    "volkswagen": 1_800_000,
    "toyota": 1_600_000,
    "honda": 1_400_000,
    "hyundai": 1_300_000,
    "kia": 1_200_000,
    "skoda": 1_300_000,
    "seat": 1_200_000,
    "ford": 1_300_000,
    "opel": 1_200_000,
    "peugeot": 1_200_000,
    "citroen": 1_100_000,
    "renault": 1_100_000,
    "nissan": 1_200_000,
    "mitsubishi": 1_300_000,
    "suzuki": 900_000,
    "dacia": 900_000,
    "fiat": 950_000,
    "tofas": 800_000,
    "subaru": 1_500_000,
    "jeep": 2_200_000,
}

# Şehir bazlı ortalama m² fiyatları (2024, TL) - Türkiye geneli
CITY_M2_PRICES = {
    "istanbul": 85_000,
    "ankara": 40_000,
    "izmir": 55_000,
    "antalya": 45_000,
    "bursa": 35_000,
    "kocaeli": 32_000,
    "eskisehir": 28_000,
    "mersin": 28_000,
    "adana": 25_000,
    "gaziantep": 22_000,
    "konya": 22_000,
    "kayseri": 20_000,
    "trabzon": 25_000,
    "samsun": 22_000,
    "diyarbakir": 18_000,
    "malatya": 18_000,
    "balikesir": 25_000,
    "mugla": 50_000,
    "aydin": 30_000,
    "denizli": 25_000,
}


def estimate_car_value(marka: str, model: str, yil: int, has_damage: bool = False) -> dict:
    """Araç değeri tahmini: marka, model, yıl, hasar kaydına göre"""
    current_year = datetime.datetime.now().year
    age = max(0, current_year - int(yil)) if yil else 7

    marka_key = normalize_turkish(marka or "")
    base_price = CAR_BASE_PRICES.get(marka_key, 1_000_000)

    # Yıllık %18 değer kaybı, minimum baz fiyatın %15'i
    depreciation_factor = max(0.15, (1 - 0.18) ** age)
    estimated_value = base_price * depreciation_factor

    # Hasar kaydı %25 değer düşürür
    if has_damage:
        estimated_value *= 0.75

    return {
        "estimated_car_value": round(estimated_value),
        "marka": marka,
        "model": model,
        "yil": yil,
        "age": age,
        "has_damage": has_damage,
    }


def estimate_property_value(city: str, district: str, square_meters: float) -> dict:
    """Mülk değeri tahmini: şehir, ilçe, m² bilgisine göre"""
    avg_m2_price = None
    district_found = False

    # Önce CSV'den ilçe bazlı fiyat dene (İstanbul detaylı)
    if district:
        for csv_path in ["backend/istanbul_property_reference.csv",
                         "backend/turkiye_property_reference.csv"]:
            try:
                df = pd.read_csv(csv_path)
                district_normalized = normalize_turkish(district)
                df["district_normalized"] = df["district"].apply(normalize_turkish)
                match = df[df["district_normalized"] == district_normalized]
                if not match.empty:
                    avg_m2_price = float(match.iloc[0]["avg_m2_price"])
                    district_found = True
                    break
            except Exception:
                continue

    # İlçe bulunamazsa şehir bazlı fiyat kullan
    if avg_m2_price is None and city:
        city_key = normalize_turkish(city)
        avg_m2_price = CITY_M2_PRICES.get(city_key, 20_000)

    # Her ikisi de yoksa ulusal ortalama
    if avg_m2_price is None:
        avg_m2_price = 22_000

    estimated_value = avg_m2_price * float(square_meters)

    return {
        "property_estimated_value": round(estimated_value),
        "avg_m2_price": avg_m2_price,
        "district_found": district_found,
    }
