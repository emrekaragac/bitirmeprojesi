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

# ── Güncel Türkiye piyasa bağlamı (2025) ─────────────────────────────────────
MARKET_CONTEXT = """
Türkiye 2025 ikinci el araç piyasası (Nisan 2025 güncel TL değerleri):

ARAÇ İKİNCİ EL SATIŞ FİYATLARI (yıla göre, TL):
Segment B — Fiat Egea, Renault Clio, Dacia Sandero, VW Polo:
  2024 model: 1.100K–1.500K TL
  2022 model: 950K–1.300K TL
  2020 model: 800K–1.100K TL
  2018 model: 650K–900K TL
  2015 model: 450K–650K TL

Segment C — Toyota Corolla, VW Golf, Hyundai i30, Honda Civic, Skoda Octavia:
  2024 model: 2.000K–2.800K TL
  2022 model: 1.700K–2.300K TL
  2020 model: 1.400K–1.900K TL
  2018 model: 1.100K–1.500K TL
  2015 model: 750K–1.100K TL

SUV Orta — Toyota C-HR, Hyundai Tucson, Kia Sportage, VW Tiguan:
  2024 model: 2.500K–3.500K TL
  2022 model: 2.000K–2.800K TL
  2020 model: 1.600K–2.300K TL
  2018 model: 1.200K–1.800K TL

SUV Büyük — Toyota RAV4, BMW X3, Mercedes GLC:
  2024 model: 3.500K–5.500K TL
  2022 model: 2.800K–4.500K TL
  2020 model: 2.200K–3.500K TL

Lüks Sedan — BMW 3/5 Serisi, Mercedes C/E Serisi, Audi A4/A6:
  2024 model: 4.000K–9.000K TL
  2022 model: 3.200K–7.000K TL
  2020 model: 2.500K–5.500K TL
  2018 model: 1.800K–3.500K TL

KONUT FİYATLARI (m² satış, TL, Nisan 2025):
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

# ── Segment bazlı araç baz fiyatları (fallback) ───────────────────────────────
# NOT: Bu değerler 2025 SIFIR araç fiyatlarıdır.
# Amortisman bu fiyat üzerinden yıla göre hesaplanır.
_BRAND_SEGMENT: dict[str, tuple[int, str]] = {
    "volkswagen":    (2_800_000, "C"),
    "toyota":        (2_500_000, "C"),
    "mercedes":      (7_000_000, "Lüks"),
    "mercedes-benz": (7_000_000, "Lüks"),
    "bmw":           (6_000_000, "Lüks"),
    "audi":          (5_500_000, "Lüks"),
    "ford":          (2_200_000, "B-C"),
    "renault":       (1_600_000, "B"),
    "fiat":          (1_200_000, "B"),
    "opel":          (1_700_000, "B-C"),
    "hyundai":       (2_100_000, "C"),
    "kia":           (2_100_000, "C"),
    "honda":         (2_400_000, "C"),
    "peugeot":       (1_900_000, "B-C"),
    "citroen":       (1_600_000, "B"),
    "skoda":         (2_000_000, "B-C"),
    "dacia":         (1_100_000, "B"),
    "seat":          (1_900_000, "B-C"),
    "volvo":         (5_000_000, "D"),
    "mitsubishi":    (2_600_000, "SUV Orta"),
    "nissan":        (2_200_000, "C-SUV"),
    "subaru":        (3_200_000, "C-SUV"),
    "jeep":          (4_500_000, "SUV"),
    "land rover":    (9_000_000, "SUV Lüks"),
    "porsche":       (12_000_000, "Spor"),
    "suzuki":        (1_700_000, "B"),
    "mazda":         (2_500_000, "C"),
    "togg":          (1_800_000, "B"),
    "default":       (2_000_000, "C"),
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
- Yukarıdaki yıl-bazlı fiyat tablosunu kullan, araca en yakın segmenti ve yılı bul
- İki yıl arası interpolasyon yap (ör. 2019 modeli → 2018 ile 2020 arası)
- Hasar varsa %15-25 ek iskonto uygula
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

    # Fallback: istatistiksel formül (2025 sıfır fiyatından amortisman)
    brand_lower = (brand or "").lower()
    base_new, segment = _BRAND_SEGMENT.get(brand_lower, _BRAND_SEGMENT["default"])
    depreciation = max(0.25, (1 - 0.10) ** age)   # %10/yıl, min %25 kalır
    value = round(base_new * depreciation * (0.80 if has_damage else 1.0))
    reasoning = (
        f"{brand or 'Bilinmeyen'} {segment} segment, 2025 sıfır baz ₺{base_new:,}, "
        f"{age} yıl %10 amortismanla hesaplandı."
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
