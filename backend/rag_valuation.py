"""
PSDS — RAG Tabanlı Değerleme Motoru

Akış:
  1. RETRIEVE  — şehir/araç bilgisine göre bilgi tabanından veri çek
  2. AUGMENT   — bağlam (context) oluştur
  3. GENERATE  — Claude API ile güncel piyasa tahmini yap

Fallback: API key yoksa mevcut statik valuation.py devreye girer.
"""

import os
import json
import re
import datetime

# ─── Bilgi Tabanı (Knowledge Base) ────────────────────────────────────────────
# Güncel Türkiye gayrimenkul verileri (2024-2025 ortalama)
PROPERTY_KNOWLEDGE = [
    # İstanbul ilçeleri
    {"city": "istanbul", "district": "besiktas",    "avg_m2": 110_000, "trend": "rising",  "notes": "Yüksek talep, merkezi konum"},
    {"city": "istanbul", "district": "kadiköy",     "avg_m2": 95_000,  "trend": "rising",  "notes": "Yaşam kalitesi yüksek, ulaşım avantajı"},
    {"city": "istanbul", "district": "sisli",       "avg_m2": 90_000,  "trend": "stable",  "notes": "İş merkezi yakını"},
    {"city": "istanbul", "district": "atasehir",    "avg_m2": 75_000,  "trend": "rising",  "notes": "Finans merkezi yakını"},
    {"city": "istanbul", "district": "ümraniye",    "avg_m2": 60_000,  "trend": "rising",  "notes": "Gelişen bölge"},
    {"city": "istanbul", "district": "bagilar",     "avg_m2": 45_000,  "trend": "stable",  "notes": "Yoğun nüfuslu bölge"},
    {"city": "istanbul", "district": "pendik",      "avg_m2": 50_000,  "trend": "rising",  "notes": "Ulaşım hatları genişliyor"},
    {"city": "istanbul", "district": "maltepe",     "avg_m2": 70_000,  "trend": "stable",  "notes": "Sahil bölgesi"},
    {"city": "istanbul", "district": "sariyer",     "avg_m2": 100_000, "trend": "rising",  "notes": "Boğaz manzarası"},
    {"city": "istanbul", "district": "beylikduzu",  "avg_m2": 45_000,  "trend": "rising",  "notes": "Yeni gelişen bölge"},
    {"city": "istanbul", "district": "esenyurt",    "avg_m2": 35_000,  "trend": "stable",  "notes": "Göç alan kalabalık bölge"},
    {"city": "istanbul", "district": "fatih",       "avg_m2": 80_000,  "trend": "stable",  "notes": "Tarihi yarımada"},
    # Diğer büyük şehirler
    {"city": "ankara",   "district": "cankaya",     "avg_m2": 50_000,  "trend": "rising",  "notes": "Başkentin en prestijli ilçesi"},
    {"city": "ankara",   "district": "kecioren",    "avg_m2": 28_000,  "trend": "stable",  "notes": "Orta gelir bölgesi"},
    {"city": "ankara",   "district": "yenimahalle", "avg_m2": 30_000,  "trend": "stable",  "notes": "Gelişen konut bölgesi"},
    {"city": "izmir",    "district": "karsiyaka",   "avg_m2": 70_000,  "trend": "rising",  "notes": "Körfez manzarası"},
    {"city": "izmir",    "district": "bornova",     "avg_m2": 55_000,  "trend": "stable",  "notes": "Üniversite yakını"},
    {"city": "izmir",    "district": "konak",       "avg_m2": 60_000,  "trend": "stable",  "notes": "Merkezi konuşlanma"},
    {"city": "antalya",  "district": "muratpasa",   "avg_m2": 55_000,  "trend": "rising",  "notes": "Turistik merkez"},
    {"city": "antalya",  "district": "kepez",       "avg_m2": 35_000,  "trend": "stable",  "notes": "Orta kesim konut bölgesi"},
    {"city": "bursa",    "district": "nilufer",     "avg_m2": 45_000,  "trend": "rising",  "notes": "Prestijli bölge"},
    {"city": "bursa",    "district": "osmangazi",   "avg_m2": 32_000,  "trend": "stable",  "notes": "Merkez ilçe"},
    # Şehir genel
    {"city": "istanbul", "district": None,          "avg_m2": 85_000,  "trend": "rising",  "notes": "İstanbul geneli ortalama"},
    {"city": "ankara",   "district": None,          "avg_m2": 40_000,  "trend": "rising",  "notes": "Ankara geneli ortalama"},
    {"city": "izmir",    "district": None,          "avg_m2": 58_000,  "trend": "rising",  "notes": "İzmir geneli ortalama"},
    {"city": "antalya",  "district": None,          "avg_m2": 45_000,  "trend": "rising",  "notes": "Antalya geneli ortalama"},
    {"city": "bursa",    "district": None,          "avg_m2": 35_000,  "trend": "stable",  "notes": "Bursa geneli ortalama"},
    {"city": "kocaeli",  "district": None,          "avg_m2": 32_000,  "trend": "rising",  "notes": "Sanayi kenti"},
    {"city": "eskisehir","district": None,          "avg_m2": 28_000,  "trend": "stable",  "notes": "Öğrenci kenti"},
    {"city": "mersin",   "district": None,          "avg_m2": 28_000,  "trend": "stable",  "notes": "Liman kenti"},
    {"city": "adana",    "district": None,          "avg_m2": 25_000,  "trend": "stable",  "notes": "Güney Türkiye merkezi"},
    {"city": "gaziantep","district": None,          "avg_m2": 22_000,  "trend": "stable",  "notes": "Sanayi ve ticaret kenti"},
    {"city": "konya",    "district": None,          "avg_m2": 22_000,  "trend": "stable",  "notes": "İç Anadolu merkezi"},
    {"city": "trabzon",  "district": None,          "avg_m2": 25_000,  "trend": "rising",  "notes": "Karadeniz kıyısı"},
    {"city": "mugla",    "district": None,          "avg_m2": 55_000,  "trend": "rising",  "notes": "Tatil bölgesi, yüksek talep"},
    {"city": "bodrum",   "district": None,          "avg_m2": 120_000, "trend": "rising",  "notes": "Lüks tatil destinasyonu"},
]

CAR_KNOWLEDGE = [
    # Volkswagen
    {"brand": "volkswagen", "model": "polo",     "year_range": "2018-2021", "avg_price": 650_000,  "notes": "Şehir içi popüler model"},
    {"brand": "volkswagen", "model": "golf",     "year_range": "2018-2021", "avg_price": 950_000,  "notes": "Klasik hatchback"},
    {"brand": "volkswagen", "model": "passat",   "year_range": "2018-2021", "avg_price": 1_100_000,"notes": "Üst segment sedan"},
    {"brand": "volkswagen", "model": "tiguan",   "year_range": "2018-2021", "avg_price": 1_400_000,"notes": "Kompakt SUV"},
    # Toyota
    {"brand": "toyota", "model": "corolla",      "year_range": "2018-2022", "avg_price": 800_000,  "notes": "Güvenilir orta segment"},
    {"brand": "toyota", "model": "yaris",        "year_range": "2018-2022", "avg_price": 550_000,  "notes": "Şehir aracı"},
    {"brand": "toyota", "model": "rav4",         "year_range": "2018-2022", "avg_price": 1_600_000,"notes": "Popüler SUV"},
    # Renault
    {"brand": "renault", "model": "clio",        "year_range": "2018-2022", "avg_price": 500_000,  "notes": "Şehir içi"},
    {"brand": "renault", "model": "megane",      "year_range": "2018-2022", "avg_price": 700_000,  "notes": "Hatchback orta segment"},
    {"brand": "renault", "model": "duster",      "year_range": "2018-2022", "avg_price": 800_000,  "notes": "Uygun fiyatlı SUV"},
    # Fiat / Tofas
    {"brand": "fiat",    "model": "egea",        "year_range": "2017-2022", "avg_price": 550_000,  "notes": "Türkiye'nin en çok satan"},
    {"brand": "fiat",    "model": "doblo",       "year_range": "2017-2022", "avg_price": 600_000,  "notes": "Ticari araç"},
    # Hyundai
    {"brand": "hyundai", "model": "i20",         "year_range": "2018-2022", "avg_price": 600_000,  "notes": "Kompakt"},
    {"brand": "hyundai", "model": "tucson",      "year_range": "2018-2022", "avg_price": 1_200_000,"notes": "Orta segment SUV"},
    # Lüks
    {"brand": "bmw",     "model": "3 serisi",    "year_range": "2018-2022", "avg_price": 2_500_000,"notes": "Premium sedan"},
    {"brand": "mercedes","model": "c serisi",    "year_range": "2018-2022", "avg_price": 2_800_000,"notes": "Premium sedan"},
    {"brand": "audi",    "model": "a4",          "year_range": "2018-2022", "avg_price": 2_400_000,"notes": "Premium sedan"},
]

MARKET_CONTEXT = """
Türkiye Gayrimenkul Piyasası Genel Durum (2024-2025):
- Enflasyon nedeniyle TL bazlı fiyatlar son 2 yılda %200-400 artmıştır
- İstanbul'da ortalama m² fiyatı 85,000-120,000 TL arasında değişmektedir
- Kıyı şehirleri (Muğla, Antalya) yabancı talep nedeniyle premium fiyatlıdır
- Ankara fiyatları İstanbul'un yaklaşık %40-50'si düzeyindedir

Türkiye İkinci El Araç Piyasası Genel Durum (2024):
- Yeni araç fiyatları 2020'ye göre 5-8 kat artmış, ikinci el piyasası da etkilenmiştir
- 2018-2021 model araçlar için değer kaybı düşüktür (%10-15/yıl)
- Lüks araçlar daha yavaş değer kaybeder
- Hasar kaydı değeri %20-30 düşürür
"""


# ─── Retrieval ─────────────────────────────────────────────────────────────────

def _normalize(text: str) -> str:
    if not text:
        return ""
    tr_map = {"ı":"i","İ":"I","ğ":"g","Ğ":"G","ü":"u","Ü":"U",
              "ş":"s","Ş":"S","ö":"o","Ö":"O","ç":"c","Ç":"C"}
    for k, v in tr_map.items():
        text = text.replace(k, v)
    return text.strip().lower()


def _retrieve_property(city: str, district: str) -> list[dict]:
    """En alakalı property knowledge parçalarını getir."""
    city_n     = _normalize(city)
    district_n = _normalize(district) if district else ""
    results = []

    for entry in PROPERTY_KNOWLEDGE:
        entry_city = _normalize(entry["city"])
        entry_dist = _normalize(entry["district"] or "")

        # Kesin district eşleşmesi
        if entry_city == city_n and entry_dist and district_n and entry_dist in district_n:
            results.insert(0, entry)  # öne al
        # Şehir eşleşmesi (district yok)
        elif entry_city == city_n and not entry["district"]:
            results.append(entry)
        # Kısmi şehir eşleşmesi
        elif city_n and city_n in entry_city:
            results.append(entry)

    return results[:5]  # en fazla 5 sonuç


def _retrieve_car(brand: str, model: str, year: int) -> list[dict]:
    """En alakalı car knowledge parçalarını getir."""
    brand_n = _normalize(brand)
    model_n = _normalize(model or "")
    results = []

    for entry in CAR_KNOWLEDGE:
        entry_brand = _normalize(entry["brand"])
        entry_model = _normalize(entry["model"])

        if entry_brand == brand_n:
            if model_n and model_n in entry_model:
                results.insert(0, entry)  # model eşleşirse öne al
            else:
                results.append(entry)

    return results[:4]


# ─── Generation (Claude API) ──────────────────────────────────────────────────

def _call_claude(prompt: str) -> str | None:
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return None
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        message = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=400,
            messages=[{"role": "user", "content": prompt}]
        )
        return message.content[0].text
    except Exception as e:
        print(f"[RAG] Claude API error: {e}")
        return None


def _parse_json_from_text(text: str) -> dict | None:
    """Claude'un cevabından JSON bloğunu çıkar."""
    try:
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            return json.loads(match.group())
    except Exception:
        pass
    return None


# ─── Public API ───────────────────────────────────────────────────────────────

def rag_estimate_property(city: str, district: str, square_meters: float) -> dict:
    """
    RAG tabanlı konut değer tahmini.
    Claude API yoksa statik hesaplama döner.
    """
    retrieved = _retrieve_property(city, district)

    if not retrieved:
        return {"rag_used": False, "error": "No matching data found"}

    # Context oluştur
    data_lines = []
    for r in retrieved:
        dist_str = f"({r['district']})" if r.get("district") else "(şehir geneli)"
        data_lines.append(
            f"- {r['city'].title()} {dist_str}: avg {r['avg_m2']:,} TL/m² | "
            f"Trend: {r['trend']} | {r['notes']}"
        )

    context = "\n".join(data_lines)
    current_year = datetime.datetime.now().year

    prompt = f"""You are a Turkish real estate valuation expert.
Estimate the current market value based on this data:

{MARKET_CONTEXT}

Retrieved price data:
{context}

Property to value:
- City: {city}
- District: {district or "not specified"}
- Size: {square_meters} m²
- Valuation year: {current_year}

Respond ONLY with a JSON object (no extra text):
{{
  "estimated_value": <integer in TRY>,
  "price_per_m2": <integer in TRY>,
  "confidence": "low" | "medium" | "high",
  "reasoning": "<1-2 sentence explanation in English>"
}}"""

    response = _call_claude(prompt)

    if not response:
        # Claude API yok → statik fallback
        best = retrieved[0]
        estimated = round(best["avg_m2"] * square_meters)
        return {
            "rag_used": False,
            "property_estimated_value": estimated,
            "avg_m2_price": best["avg_m2"],
            "confidence": "medium",
            "reasoning": "Calculated from static reference data (Claude API not configured).",
        }

    parsed = _parse_json_from_text(response)
    if parsed and "estimated_value" in parsed:
        return {
            "rag_used": True,
            "property_estimated_value": int(parsed["estimated_value"]),
            "avg_m2_price": int(parsed.get("price_per_m2", retrieved[0]["avg_m2"])),
            "confidence": parsed.get("confidence", "medium"),
            "reasoning": parsed.get("reasoning", ""),
            "retrieved_sources": len(retrieved),
        }

    # Parse başarısız → statik fallback
    best = retrieved[0]
    return {
        "rag_used": False,
        "property_estimated_value": round(best["avg_m2"] * square_meters),
        "avg_m2_price": best["avg_m2"],
        "confidence": "medium",
        "reasoning": "Parse error, used static reference.",
    }


def rag_estimate_car(brand: str, model: str, year: int, has_damage: bool = False) -> dict:
    """
    RAG tabanlı araç değer tahmini.
    Claude API yoksa statik hesaplama döner.
    """
    retrieved = _retrieve_car(brand, model, year)
    current_year = datetime.datetime.now().year
    age = max(0, current_year - int(year)) if year else 5

    if not retrieved:
        return {"rag_used": False, "error": "No matching car data found"}

    data_lines = []
    for r in retrieved:
        data_lines.append(
            f"- {r['brand'].title()} {r['model'].title()} "
            f"({r['year_range']}): avg {r['avg_price']:,} TL | {r['notes']}"
        )

    context = "\n".join(data_lines)

    prompt = f"""You are a Turkish used car valuation expert.
Estimate the current market value based on this data:

{MARKET_CONTEXT}

Retrieved car price data:
{context}

Car to value:
- Brand: {brand}
- Model: {model or "unknown"}
- Year: {year} (age: {age} years)
- Has damage record: {has_damage}
- Valuation year: {current_year}

Respond ONLY with a JSON object (no extra text):
{{
  "estimated_value": <integer in TRY>,
  "confidence": "low" | "medium" | "high",
  "reasoning": "<1-2 sentence explanation in English>"
}}"""

    response = _call_claude(prompt)

    if not response:
        # Statik fallback
        base = retrieved[0]["avg_price"]
        factor = max(0.15, (1 - 0.18) ** age)
        value = round(base * factor * (0.75 if has_damage else 1.0))
        return {
            "rag_used": False,
            "estimated_car_value": value,
            "confidence": "medium",
            "reasoning": "Calculated from static reference data (Claude API not configured).",
        }

    parsed = _parse_json_from_text(response)
    if parsed and "estimated_value" in parsed:
        return {
            "rag_used": True,
            "estimated_car_value": int(parsed["estimated_value"]),
            "confidence": parsed.get("confidence", "medium"),
            "reasoning": parsed.get("reasoning", ""),
            "retrieved_sources": len(retrieved),
        }

    base = retrieved[0]["avg_price"]
    factor = max(0.15, (1 - 0.18) ** age)
    value = round(base * factor * (0.75 if has_damage else 1.0))
    return {
        "rag_used": False,
        "estimated_car_value": value,
        "confidence": "medium",
        "reasoning": "Parse error, used static reference.",
    }
