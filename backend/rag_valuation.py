"""
PSDS — RAG Tabanlı Değerleme Motoru

Akış:
  1. RETRIEVE  — Arabam.com / Hepsiemlak.com / Sahibinden.com'dan canlı fiyat çek
  2. AUGMENT   — Çekilen veya bilinen fiyatları Claude prompt'una ekle
  3. GENERATE  — Claude Haiku ile gerekçeli tahmin yap
  4. FALLBACK  — Claude yoksa şehir/marka bazlı istatistiksel formül
"""

import os
import re
import json
import datetime

from backend.web_retrieval import (
    fetch_car_prices,
    fetch_car_prices_sahibinden,
    fetch_property_prices,
    fetch_property_prices_sahibinden,
)

# ── Güncel Türkiye piyasa bağlamı (2024-2025) ──────────────────────────────────
MARKET_CONTEXT = """
Türkiye 2024-2025 araç ve konut piyasası:

ARAÇ FİYATLARI (ortalama ikinci el, TL, Kasım 2024):
- 2020 model segment B (Fiat Egea, Renault Clio, VW Polo): 800K–1.2M TL
- 2020 model segment C (Toyota Corolla, VW Golf, Honda Civic): 1.1M–1.7M TL
- 2020 model segment D (Toyota Camry, VW Passat, BMW 3): 1.5M–2.5M TL
- 2020 model SUV orta (Toyota C-HR, Renault Kadjar): 1.3M–2.0M TL
- 2020 model SUV büyük (Toyota RAV4, BMW X3, Mercedes GLC): 2.0M–3.5M TL
- Her model yılı için yaklaşık %10-15 yıllık değer kaybı
- Hasar kaydı olan araçlar %15-25 iskontolu değerlenir
- Lüks markalar (BMW, Mercedes, Audi, Porsche) fiyatları 2-4x yüksek

KONUT FİYATLARI (m² satış fiyatı, TL, Kasım 2024):
- İstanbul Avrupa merkez (Beşiktaş, Şişli, Sarıyer): 120K–250K TL/m²
- İstanbul Anadolu merkez (Kadıköy, Üsküdar, Maltepe): 80K–160K TL/m²
- İstanbul çevre ilçeler (Esenyurt, Pendik, Tuzla): 40K–80K TL/m²
- Ankara merkez (Çankaya, Keçiören): 35K–70K TL/m²
- İzmir merkez (Konak, Bornova, Karşıyaka): 50K–100K TL/m²
- Büyük şehirler (Bursa, Antalya, Kayseri): 25K–55K TL/m²
- Orta ölçekli şehirler: 15K–35K TL/m²
- Küçük şehir/ilçe merkezi: 8K–20K TL/m²
"""

# ── Şehir bazlı m² fiyatı tahmini (Claude yoksa fallback için) ─────────────────
_CITY_M2: dict[str, int] = {
    "istanbul": 110_000,
    "ankara": 45_000,
    "izmir": 65_000,
    "bursa": 38_000,
    "antalya": 45_000,
    "kocaeli": 35_000,
    "mersin": 25_000,
    "konya": 22_000,
    "adana": 20_000,
    "samsun": 20_000,
    "trabzon": 22_000,
    "kayseri": 20_000,
    "eskisehir": 25_000,
    "gaziantep": 18_000,
    "diyarbakir": 15_000,
    "default": 18_000,
}

# ── Segment bazlı araç fallback fiyatları (2024 yılı baz, 2020 model) ──────────
_BRAND_SEGMENT: dict[str, tuple[int, str]] = {
    # (baz_fiyat_2020, segment_ismi)
    "volkswagen": (1_500_000, "C"),
    "toyota":     (1_400_000, "C"),
    "mercedes":   (2_800_000, "D-Luxury"),
    "bmw":        (2_800_000, "D-Luxury"),
    "audi":       (2_500_000, "D-Luxury"),
    "ford":       (1_100_000, "B-C"),
    "renault":    (1_000_000, "B"),
    "fiat":       (  900_000, "B"),
    "opel":       (1_000_000, "B-C"),
    "hyundai":    (1_200_000, "C"),
    "kia":        (1_200_000, "C"),
    "honda":      (1_300_000, "C"),
    "peugeot":    (1_100_000, "B-C"),
    "citroen":    (1_000_000, "B"),
    "skoda":      (1_200_000, "C"),
    "dacia":      (  850_000, "B"),
    "seat":       (1_100_000, "B-C"),
    "volvo":      (2_500_000, "D"),
    "mitsubishi": (1_300_000, "C"),
    "nissan":     (1_200_000, "C"),
    "default":    (1_200_000, "C"),
}


# ── Claude API çağrısı ──────────────────────────────────────────────────────────

def _call_claude(prompt: str) -> str | None:
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("[RAG] ANTHROPIC_API_KEY yok, Claude atlanıyor")
        return None
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        message = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=512,
            messages=[{"role": "user", "content": prompt}]
        )
        return message.content[0].text
    except Exception as e:
        print(f"[RAG] Claude API error: {e}")
        return None


def _parse_json(text: str) -> dict | None:
    try:
        match = re.search(r'\{[^{}]*\}', text, re.DOTALL)
        if match:
            return json.loads(match.group())
    except Exception:
        pass
    return None


# ── ARAÇ TAHMİNİ ───────────────────────────────────────────────────────────────

def rag_estimate_car(brand: str, model: str, year: int, has_damage: bool = False) -> dict:
    current_year = datetime.datetime.now().year
    age = max(0, current_year - int(year))

    # 1. Web'den veri çekmeyi dene
    data = fetch_car_prices(brand, model, year)
    source = "arabam.com"

    if not data["found"]:
        data = fetch_car_prices_sahibinden(brand, model, year)
        source = "sahibinden.com"

    if data["found"] and data["count"] >= 3:
        prices_str = ", ".join(f"₺{p:,}" for p in data["prices"][:10])
        web_context = (
            f"Gerçek zamanlı ilan verisi ({source}):\n"
            f"  İlan sayısı: {data['count']}\n"
            f"  Ortalama: ₺{data['avg']:,}\n"
            f"  Medyan: ₺{data['median']:,}\n"
            f"  Örnek fiyatlar: {prices_str}"
        )
        base_price = data["median"]
    else:
        web_context = (
            "Web kaynaklarından güncel ilan verisi alınamadı "
            "(bot koruması veya bağlantı hatası). "
            "Yukarıdaki piyasa bağlamı ve uzmanlık bilginle tahmin yap."
        )
        base_price = None

    # 2. Claude ile tahmin
    prompt = f"""Sen Türkiye'nin önde gelen ikinci el araç değerleme uzmanısın.
Aşağıdaki araç için güncel Türkiye piyasa değerini tahmin et.

{MARKET_CONTEXT}

{web_context}

Araç bilgileri:
  Marka: {brand}
  Model: {model or "bilinmiyor"}
  Model yılı: {year} ({age} yıl eski)
  Hasar kaydı: {"Evet (değeri %15-25 düşürür)" if has_damage else "Hayır"}
  Değerleme tarihi: {current_year}

Talimatlar:
- Piyasa bağlamındaki güncel TL fiyat aralıklarını ve web verisini birlikte değerlendir
- Hasar varsa değerden %15-25 düş
- Yaş arttıkça %10-15/yıl amortisman uygula
- SADECE JSON yanıt ver, başka metin yazma

{{
  "estimated_value": <TL cinsinden tam sayı>,
  "confidence": "low" veya "medium" veya "high",
  "reasoning": "<1-2 cümle Türkçe gerekçe>"
}}"""

    response = _call_claude(prompt)
    if response:
        parsed = _parse_json(response)
        if parsed and "estimated_value" in parsed:
            val = int(parsed["estimated_value"])
            # Makul aralık kontrolü: 50K - 30M TL
            if 50_000 <= val <= 30_000_000:
                return {
                    "rag_used": True,
                    "estimated_car_value": val,
                    "confidence": parsed.get("confidence", "medium"),
                    "reasoning": parsed.get("reasoning", ""),
                    "source": source if data["found"] else "Claude piyasa bilgisi",
                    "live_data": data["found"],
                    "live_avg": data.get("avg"),
                    "live_median": data.get("median"),
                    "live_count": data.get("count"),
                }

    # 3. İstatistiksel fallback (Claude yoksa veya parse başarısız)
    if base_price:
        depreciation = max(0.20, (1 - 0.12) ** age)
        value = round(base_price * depreciation * (0.80 if has_damage else 1.0))
        reasoning = f"{source} medyanından (₺{base_price:,}) {age} yıllık amortisman uygulandı."
    else:
        brand_lower = brand.lower()
        base_2020, segment = _BRAND_SEGMENT.get(brand_lower, _BRAND_SEGMENT["default"])
        # 2024 baz → model yılına göre amortisman
        years_from_2020 = 2020 - min(year, 2020)
        depreciation = max(0.20, (1 - 0.12) ** (age))
        value = round(base_2020 * depreciation * (0.80 if has_damage else 1.0))
        reasoning = (
            f"{brand} {segment} segment baz fiyatından "
            f"(₺{base_2020:,}, 2020 model) {age} yıl amortismanla hesaplandı."
        )

    return {
        "rag_used": False,
        "estimated_car_value": value,
        "confidence": "low",
        "reasoning": reasoning,
        "source": source if data["found"] else "istatistiksel formül",
        "live_data": data["found"],
    }


# ── EMLAK TAHMİNİ ──────────────────────────────────────────────────────────────

def rag_estimate_property(city: str, district: str, square_meters: float) -> dict:
    current_year = datetime.datetime.now().year

    # 1. Web'den veri çekmeyi dene
    data = fetch_property_prices(city, district)
    source = "hepsiemlak.com"

    if not data["found"]:
        data = fetch_property_prices_sahibinden(city, district)
        source = "sahibinden.com"

    if data["found"] and data["count"] >= 3:
        prices_str = ", ".join(f"₺{p:,}" for p in data["prices"][:8])
        # İlan toplam fiyatından m² tahmini — daire büyüklüğünü 90m² baz al
        implied_m2 = int(data["median_total"] / 90)
        web_context = (
            f"Gerçek zamanlı ilan verisi ({source}, {city}/{district or 'merkez'}):\n"
            f"  İlan sayısı: {data['count']}\n"
            f"  Medyan toplam ilan fiyatı: ₺{data['median_total']:,}\n"
            f"  Tahmini m² fiyatı (~90m² baz): ₺{implied_m2:,}/m²\n"
            f"  Örnek ilan fiyatları: {prices_str}"
        )
        base_m2 = implied_m2
    else:
        web_context = (
            "Web kaynaklarından güncel ilan verisi alınamadı. "
            "Yukarıdaki piyasa bağlamı ve uzmanlık bilginle tahmin yap."
        )
        base_m2 = None

    # 2. Claude ile tahmin
    prompt = f"""Sen Türkiye'nin önde gelen gayrimenkul değerleme uzmanısın.
Aşağıdaki konut için güncel Türkiye piyasa değerini tahmin et.

{MARKET_CONTEXT}

{web_context}

Taşınmaz bilgileri:
  Şehir: {city}
  İlçe: {district or "belirtilmedi"}
  Büyüklük: {square_meters} m²
  Değerleme tarihi: {current_year}

Talimatlar:
- Şehir ve ilçeye özgü m² fiyatını doğru belirle (İstanbul merkez ile küçük şehir çok farklı!)
- Web ilan verisi varsa o bölgenin fiyatını baz al
- Yoksa piyasa bağlamındaki fiyat aralığının ortasını kullan
- Toplam değer = m² fiyatı × {square_meters}
- SADECE JSON yanıt ver

{{
  "estimated_value": <TL cinsinden toplam değer, tam sayı>,
  "price_per_m2": <TL cinsinden m² fiyatı, tam sayı>,
  "confidence": "low" veya "medium" veya "high",
  "reasoning": "<1-2 cümle Türkçe gerekçe>"
}}"""

    response = _call_claude(prompt)
    if response:
        parsed = _parse_json(response)
        if parsed and "estimated_value" in parsed:
            val = int(parsed["estimated_value"])
            m2_price = int(parsed.get("price_per_m2", val / max(square_meters, 1)))
            # Makul aralık: 500K - 500M TL
            if 500_000 <= val <= 500_000_000:
                return {
                    "rag_used": True,
                    "property_estimated_value": val,
                    "avg_m2_price": m2_price,
                    "confidence": parsed.get("confidence", "medium"),
                    "reasoning": parsed.get("reasoning", ""),
                    "source": source if data["found"] else "Claude piyasa bilgisi",
                    "live_data": data["found"],
                    "live_avg_total": data.get("avg_total"),
                    "live_median_total": data.get("median_total"),
                    "live_count": data.get("count"),
                }

    # 3. İstatistiksel fallback
    city_key = city.lower().translate(str.maketrans("çğıöşü", "cgiosu"))
    m2 = base_m2 or _CITY_M2.get(city_key, _CITY_M2["default"])
    value = round(m2 * square_meters)
    reasoning = (
        f"{city} için tahmini ₺{m2:,}/m² baz alınarak "
        f"{square_meters}m² değerlendi."
    ) if not base_m2 else (
        f"{source} ilan medyanından hesaplanan ₺{m2:,}/m² × {square_meters}m²."
    )

    return {
        "rag_used": False,
        "property_estimated_value": value,
        "avg_m2_price": m2,
        "confidence": "low",
        "reasoning": reasoning,
        "source": source if data["found"] else "şehir bazlı formül",
        "live_data": data["found"],
    }
