"""
PSDS — Belge Tabanlı Değerleme Motoru

Hoca onaylı akış:
  1. EXTRACT  — Ruhsat/Tapu belgesinden OCR ile bilgi çıkar (ocr.py)
  2. AUGMENT  — Çıkarılan bilgileri + ham belge metnini Claude prompt'una ekle
  3. GENERATE — Claude Haiku ile piyasa değeri tahmini yap
  4. FALLBACK — Claude yoksa şehir/marka bazlı istatistiksel formül

Web scraping KALDIRILDI (arabam.com/hepsiemlak.com bot koruması nedeniyle çalışmıyor).
"""

import os
import re
import json
import datetime

# ── Güncel Türkiye piyasa bağlamı (2024-2025) ────────────────────────────────
MARKET_CONTEXT = """
Türkiye 2024-2025 araç ve konut piyasası (güncel TL değerleri):

ARAÇ FİYATLARI (ikinci el, TL, 2025 başı):
- Segment B (Fiat Egea, Renault Clio, VW Polo, Dacia Sandero): 900K–1.3M TL (2020 model)
- Segment C (Toyota Corolla, VW Golf, Honda Civic, Hyundai i30): 1.2M–1.8M TL (2020 model)
- Segment D (Toyota Camry, VW Passat, BMW 3 Serisi): 1.8M–3.0M TL (2020 model)
- SUV Orta (Toyota C-HR, Renault Kadjar, Hyundai Tucson): 1.5M–2.3M TL (2020 model)
- SUV Büyük (Toyota RAV4, BMW X3, Mercedes GLC): 2.5M–4.5M TL (2020 model)
- Lüks (BMW 5, Mercedes E, Audi A6): 4M–8M TL (2020 model)
- Her model yılı: ~%12-15 yıllık değer kaybı
- Hasar kaydı var: %15-25 ek iskonto

KONUT FİYATLARI (m² satış, TL, 2025):
- İstanbul Avrupa merkez (Beşiktaş, Şişli, Sarıyer, Bakırköy): 130K–280K TL/m²
- İstanbul Anadolu merkez (Kadıköy, Üsküdar, Ataşehir): 90K–180K TL/m²
- İstanbul çevre (Esenyurt, Pendik, Tuzla, Silivri): 45K–90K TL/m²
- Ankara merkez (Çankaya, Keçiören, Mamak): 40K–80K TL/m²
- İzmir merkez (Konak, Bornova, Karşıyaka, Alsancak): 55K–110K TL/m²
- Büyük şehirler (Bursa, Antalya, Kocaeli): 30K–65K TL/m²
- Orta şehirler (Kayseri, Konya, Adana, Mersin): 20K–40K TL/m²
- Küçük şehir/ilçe: 10K–22K TL/m²
"""

# ── Şehir bazlı m² fiyatı (fallback) ──────────────────────────────────────────
_CITY_M2: dict[str, int] = {
    "istanbul": 120_000,
    "ankara":   50_000,
    "izmir":    70_000,
    "bursa":    42_000,
    "antalya":  50_000,
    "kocaeli":  38_000,
    "mersin":   28_000,
    "konya":    25_000,
    "adana":    22_000,
    "samsun":   22_000,
    "trabzon":  25_000,
    "kayseri":  22_000,
    "eskisehir":28_000,
    "gaziantep":20_000,
    "diyarbakir":16_000,
    "default":  20_000,
}

# ── Segment bazlı araç baz fiyatları (fallback, 2020 model baz) ───────────────
_BRAND_SEGMENT: dict[str, tuple[int, str]] = {
    "volkswagen": (1_500_000, "C"),
    "toyota":     (1_400_000, "C"),
    "mercedes":   (3_200_000, "Lüks"),
    "bmw":        (3_000_000, "Lüks"),
    "audi":       (2_800_000, "Lüks"),
    "ford":       (1_200_000, "B-C"),
    "renault":    (1_050_000, "B"),
    "fiat":       (  950_000, "B"),
    "opel":       (1_050_000, "B-C"),
    "hyundai":    (1_300_000, "C"),
    "kia":        (1_300_000, "C"),
    "honda":      (1_350_000, "C"),
    "peugeot":    (1_150_000, "B-C"),
    "citroen":    (1_050_000, "B"),
    "skoda":      (1_250_000, "C"),
    "dacia":      (  900_000, "B"),
    "seat":       (1_150_000, "B-C"),
    "volvo":      (2_800_000, "D"),
    "mitsubishi": (1_400_000, "C"),
    "nissan":     (1_300_000, "C"),
    "subaru":     (1_500_000, "C"),
    "jeep":       (2_000_000, "SUV"),
    "default":    (1_250_000, "C"),
}


# ── Claude API çağrısı ─────────────────────────────────────────────────────────
def _call_claude(prompt: str) -> str | None:
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
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


# ── ARAÇ TAHMİNİ ──────────────────────────────────────────────────────────────
def rag_estimate_car(
    brand: str,
    model: str,
    year: int,
    has_damage: bool = False,
    ocr_text: str = "",          # Ruhsattan çıkarılan ham belge metni
) -> dict:
    """
    Araç değeri tahmini.
    Akış: OCR metni + bilinen alanlar → Claude → TL değer tahmini
    """
    current_year = datetime.datetime.now().year
    age = max(0, current_year - int(year))

    # Ham belge metni varsa prompt'a ekle
    doc_section = ""
    if ocr_text and len(ocr_text.strip()) > 30:
        doc_section = f"""
Ruhsat belgesinden OCR ile çıkarılan ham metin:
---
{ocr_text[:1200]}
---
"""

    prompt = f"""Sen Türkiye'nin önde gelen ikinci el araç değerleme uzmanısın.
Aşağıdaki araç ruhsatı bilgilerine dayanarak güncel Türkiye ikinci el piyasa değerini TL cinsinden tahmin et.

{MARKET_CONTEXT}
{doc_section}
Çıkarılan araç bilgileri:
  Marka        : {brand or "bilinmiyor"}
  Model        : {model or "bilinmiyor"}
  Model yılı   : {year} ({age} yıllık)
  Hasar kaydı  : {"Evet — değerden %15-25 düş" if has_damage else "Hayır"}
  Değerleme    : {current_year} yılı Türkiye piyasası

Talimatlar:
- Piyasa bağlamındaki TL fiyat aralıklarını kullan
- Araç yaşına göre %12-15/yıl amortisman uygula
- Hasar varsa ek %15-25 iskonto ekle
- Varsa belge metninden ek bilgi (motor hacmi, yakıt tipi vb.) değerlemeye kat
- SADECE JSON formatında yanıt ver, başka metin yazma

{{
  "estimated_value": <TL cinsinden tam sayı, örn: 1250000>,
  "confidence": "low" veya "medium" veya "high",
  "reasoning": "<1-2 cümle Türkçe gerekçe>"
}}"""

    response = _call_claude(prompt)
    if response:
        parsed = _parse_json(response)
        if parsed and "estimated_value" in parsed:
            val = int(parsed["estimated_value"])
            if 50_000 <= val <= 30_000_000:
                return {
                    "rag_used": True,
                    "estimated_car_value": val,
                    "confidence": parsed.get("confidence", "medium"),
                    "reasoning": parsed.get("reasoning", ""),
                    "source": "Claude AI (belge OCR + piyasa bilgisi)",
                    "live_data": False,
                }

    # Fallback: istatistiksel formül
    brand_lower = (brand or "").lower()
    base_2020, segment = _BRAND_SEGMENT.get(brand_lower, _BRAND_SEGMENT["default"])
    depreciation = max(0.20, (1 - 0.12) ** age)
    value = round(base_2020 * depreciation * (0.80 if has_damage else 1.0))
    reasoning = (
        f"{brand or 'Bilinmeyen'} {segment} segment baz fiyatı (₺{base_2020:,}, 2020 model), "
        f"{age} yıl amortismanla hesaplandı."
    )
    return {
        "rag_used": False,
        "estimated_car_value": value,
        "confidence": "low",
        "reasoning": reasoning,
        "source": "istatistiksel formül",
        "live_data": False,
    }


# ── EMLAK TAHMİNİ ─────────────────────────────────────────────────────────────
def rag_estimate_property(
    city: str,
    district: str,
    square_meters: float,
    ocr_text: str = "",          # Tapu belgesinden çıkarılan ham metin
) -> dict:
    """
    Konut değeri tahmini.
    Akış: OCR metni + şehir/ilçe/m² → Claude → TL değer tahmini
    """
    current_year = datetime.datetime.now().year

    doc_section = ""
    if ocr_text and len(ocr_text.strip()) > 30:
        doc_section = f"""
Tapu belgesinden OCR ile çıkarılan ham metin:
---
{ocr_text[:1200]}
---
"""

    prompt = f"""Sen Türkiye'nin önde gelen gayrimenkul değerleme uzmanısın.
Aşağıdaki tapu bilgilerine dayanarak konutun güncel Türkiye piyasa değerini TL cinsinden tahmin et.

{MARKET_CONTEXT}
{doc_section}
Çıkarılan taşınmaz bilgileri:
  Şehir        : {city or "bilinmiyor"}
  İlçe         : {district or "belirtilmedi"}
  Alan         : {square_meters} m²
  Değerleme    : {current_year} yılı Türkiye piyasası

Talimatlar:
- Şehir ve ilçeye özgü güncel m² fiyatını belirle (İstanbul merkez ile küçük şehir çok farklı)
- Varsa belge metninden mahalle/nitelik bilgisini değerlemeye kat
- Toplam değer = m² fiyatı × {square_meters}
- SADECE JSON formatında yanıt ver

{{
  "estimated_value": <TL cinsinden toplam değer, tam sayı, örn: 8500000>,
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
            if 500_000 <= val <= 500_000_000:
                return {
                    "rag_used": True,
                    "property_estimated_value": val,
                    "avg_m2_price": m2_price,
                    "confidence": parsed.get("confidence", "medium"),
                    "reasoning": parsed.get("reasoning", ""),
                    "source": "Claude AI (belge OCR + piyasa bilgisi)",
                    "live_data": False,
                }

    # Fallback: şehir bazlı m² fiyatı
    city_key = (city or "").lower().translate(str.maketrans("çğıöşüÇĞİÖŞÜ", "cgiōsuCGIOSU"))
    # Basit normalize: ç→c, ğ→g, ı→i, ö→o, ş→s, ü→u
    for tr, en in zip("çğışöüÇĞİŞÖÜ", "cgisouCGISOu"):
        city_key = city_key.replace(tr, en)
    m2 = _CITY_M2.get(city_key, _CITY_M2["default"])
    value = round(m2 * square_meters)
    reasoning = (
        f"{city or 'Bilinmeyen şehir'} için tahmini ₺{m2:,}/m² × {square_meters}m² "
        f"= ₺{value:,} (şehir bazlı formül)."
    )
    return {
        "rag_used": False,
        "property_estimated_value": value,
        "avg_m2_price": m2,
        "confidence": "low",
        "reasoning": reasoning,
        "source": "şehir bazlı formül",
        "live_data": False,
    }
