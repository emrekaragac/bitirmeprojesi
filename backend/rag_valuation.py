"""
PSDS — RAG Tabanlı Değerleme Motoru (Gerçek Zamanlı Web Verisi)

Akış:
  1. RETRIEVE  — Arabam.com / Hepsiemlak.com / Sahibinden.com'dan canlı fiyat çek
  2. AUGMENT   — Çekilen fiyatları Claude prompt'una ekle
  3. GENERATE  — Claude Haiku ile gerekçeli tahmin yap

Fallback zinciri:
  arabam.com → sahibinden.com → statik hesaplama (Claude API yoksa)
  hepsiemlak.com → sahibinden.com → statik hesaplama
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

MARKET_CONTEXT = """
Türkiye'de yüksek enflasyon nedeniyle TL bazlı fiyatlar son 2 yılda dramatik artış gösterdi.
2024-2025 döneminde İstanbul merkezi ilçelerde m² fiyatları 80.000-150.000 TL aralığında,
Anadolu yakasında 50.000-100.000 TL aralığındadır.
Araç fiyatları ise OTV artışları ve kur etkisiyle %40-80 yükselmiştir.
"""

# ─── Claude API çağrısı ───────────────────────────────────────────────────────

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


def _parse_json(text: str) -> dict | None:
    try:
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            return json.loads(match.group())
    except Exception:
        pass
    return None


# ─── ARAÇ TAHMİNİ ─────────────────────────────────────────────────────────────

def rag_estimate_car(brand: str, model: str, year: int, has_damage: bool = False) -> dict:
    """
    1. Arabam.com'dan canlı fiyat çek
    2. Bulamazsa Sahibinden.com'u dene
    3. Verileri Claude'a ver, gerekçeli tahmin al
    4. Claude yoksa istatistiksel fallback
    """
    current_year = datetime.datetime.now().year
    age = max(0, current_year - int(year))

    # ── Retrieve ──
    data = fetch_car_prices(brand, model, year)
    source = "arabam.com"

    if not data["found"]:
        data = fetch_car_prices_sahibinden(brand, model, year)
        source = "sahibinden.com"

    if data["found"] and data["count"] >= 3:
        prices_str = ", ".join(f"{p:,}" for p in data["prices"][:10])
        context = (
            f"Kaynak: {source}\n"
            f"Toplam ilan: {data['count']}\n"
            f"Ortalama fiyat: {data['avg']:,} TL\n"
            f"Medyan fiyat: {data['median']:,} TL\n"
            f"Örnek fiyatlar (TL): {prices_str}\n"
            f"Kaynak URL: {data['url']}"
        )
        base_price = data["median"]
    else:
        # Web verisi yok → Claude'a genel bilgiyle git
        context = "Web kaynaklarından veri çekilemedi. Genel Türkiye piyasa bilgisine göre tahmin yap."
        base_price = None

    # ── Augment + Generate ──
    prompt = f"""Sen deneyimli bir Türkiye ikinci el araç değerleme uzmanısın.
Aşağıdaki gerçek ilan verilerini kullanarak araç piyasa değerini tahmin et.

{MARKET_CONTEXT}

Güncel ilan verisi:
{context}

Değerlendirilecek araç:
- Marka: {brand}
- Model: {model or "belirtilmedi"}
- Yıl: {year} ({age} yaşında)
- Hasar kaydı: {"Evet" if has_damage else "Hayır"}
- Değerleme tarihi: {current_year}

SADECE aşağıdaki JSON formatında yanıt ver (başka metin yazma):
{{
  "estimated_value": <TL cinsinden tam sayı>,
  "confidence": "low" veya "medium" veya "high",
  "reasoning": "<1-2 cümle Türkçe gerekçe>"
}}"""

    response = _call_claude(prompt)

    if response:
        parsed = _parse_json(response)
        if parsed and "estimated_value" in parsed:
            return {
                "rag_used": True,
                "estimated_car_value": int(parsed["estimated_value"]),
                "confidence": parsed.get("confidence", "medium"),
                "reasoning": parsed.get("reasoning", ""),
                "source": source if data["found"] else "Claude genel bilgi",
                "live_data": data["found"],
                "live_avg": data.get("avg"),
                "live_median": data.get("median"),
                "live_count": data.get("count"),
            }

    # ── Statik fallback (Claude yoksa) ──
    if base_price:
        depreciation = max(0.15, (1 - 0.15) ** age)
        value = round(base_price * depreciation * (0.75 if has_damage else 1.0))
        reasoning = f"{source} medyanından ({base_price:,} TL) {age} yıl amortisman uygulandı."
    else:
        # Ne web verisi ne Claude var
        fallback_base = 800_000 + (2020 - min(year, 2020)) * 50_000
        depreciation = max(0.15, (1 - 0.15) ** age)
        value = round(fallback_base * depreciation * (0.75 if has_damage else 1.0))
        reasoning = "Web verisi ve Claude API mevcut değil, genel formülle hesaplandı."

    return {
        "rag_used": False,
        "estimated_car_value": value,
        "confidence": "low",
        "reasoning": reasoning,
        "source": source if data["found"] else "statik formül",
        "live_data": data["found"],
    }


# ─── EMlAK TAHMİNİ ────────────────────────────────────────────────────────────

def rag_estimate_property(city: str, district: str, square_meters: float) -> dict:
    """
    1. Hepsiemlak.com'dan canlı fiyat çek
    2. Bulamazsa Sahibinden.com'u dene
    3. İlan fiyatlarından m² fiyatı hesapla + Claude'a ver
    4. Claude yoksa istatistiksel fallback
    """
    current_year = datetime.datetime.now().year

    # ── Retrieve ──
    data = fetch_property_prices(city, district)
    source = "hepsiemlak.com"

    if not data["found"]:
        data = fetch_property_prices_sahibinden(city, district)
        source = "sahibinden.com"

    if data["found"] and data["count"] >= 3:
        prices_str = ", ".join(f"{p:,}" for p in data["prices"][:10])
        # m² tahmini: medyan / ortalama daire büyüklüğü ~100m²
        implied_m2 = data["median_total"] // 100

        context = (
            f"Kaynak: {source}\n"
            f"Toplam ilan: {data['count']}\n"
            f"Ortalama ilan fiyatı: {data['avg_total']:,} TL\n"
            f"Medyan ilan fiyatı: {data['median_total']:,} TL\n"
            f"Tahmini m² fiyatı (~100m² baz alınarak): {implied_m2:,} TL/m²\n"
            f"Örnek ilan fiyatları (TL): {prices_str}\n"
            f"Kaynak URL: {data['url']}"
        )
        base_m2 = implied_m2
    else:
        context = "Web kaynaklarından veri çekilemedi. Genel Türkiye piyasa bilgisine göre tahmin yap."
        base_m2 = None

    # ── Augment + Generate ──
    prompt = f"""Sen deneyimli bir Türkiye gayrimenkul değerleme uzmanısın.
Aşağıdaki gerçek ilan verilerini kullanarak konut değerini tahmin et.

{MARKET_CONTEXT}

Güncel ilan verisi ({city} / {district or "merkez"}):
{context}

Değerlendirilecek taşınmaz:
- Şehir: {city}
- İlçe: {district or "belirtilmedi"}
- Büyüklük: {square_meters} m²
- Değerleme tarihi: {current_year}

SADECE aşağıdaki JSON formatında yanıt ver (başka metin yazma):
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
            return {
                "rag_used": True,
                "property_estimated_value": int(parsed["estimated_value"]),
                "avg_m2_price": int(parsed.get("price_per_m2", base_m2 or 50_000)),
                "confidence": parsed.get("confidence", "medium"),
                "reasoning": parsed.get("reasoning", ""),
                "source": source if data["found"] else "Claude genel bilgi",
                "live_data": data["found"],
                "live_avg_total": data.get("avg_total"),
                "live_median_total": data.get("median_total"),
                "live_count": data.get("count"),
            }

    # ── Statik fallback ──
    if base_m2:
        value = round(base_m2 * square_meters)
        reasoning = f"{source} medyanından hesaplanan ~{base_m2:,} TL/m² üzerinden {square_meters}m² değerlendi."
    else:
        base_m2 = 50_000  # genel fallback
        value = round(base_m2 * square_meters)
        reasoning = "Web verisi ve Claude API mevcut değil, genel m² fiyatıyla hesaplandı."

    return {
        "rag_used": False,
        "property_estimated_value": value,
        "avg_m2_price": base_m2,
        "confidence": "low",
        "reasoning": reasoning,
        "source": source if data["found"] else "statik formül",
        "live_data": data["found"],
    }
