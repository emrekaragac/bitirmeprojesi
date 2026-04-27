"""
PSDS — Claude Vision ile Belge Analizi (Temiz Versiyon)

Akış:
  PDF → PyMuPDF ile JPEG → Claude Vision API → doğrulama + alan çıkarma + değer tahmini

Tek sorumluluk: Belgeyi gör, ne olduğunu söyle, değerini tahmin et.
"""

import os
import re
import json
import base64
from typing import Optional


# ── Türkiye 2025 piyasa bağlamı ──────────────────────────────────────────────
_MARKET = """
Türkiye 2025 piyasası:
ARAÇ (ikinci el TL, 2020 model baz):
- Segment B (Fiat Egea, Renault Clio, Dacia): 900K–1.3M TL
- Segment C (Toyota Corolla, Honda Civic, Hyundai i30): 1.2M–1.8M TL
- Segment D (BMW 3, Mercedes C, VW Passat): 2.0M–3.5M TL
- SUV orta (Toyota C-HR, Hyundai Tucson): 1.5M–2.5M TL
- SUV büyük (Toyota RAV4, BMW X3): 2.5M–4.5M TL
- Lüks (BMW 5, Mercedes E, S Serisi): 4M–12M TL
- Her yıl ~%12 değer kaybı. Hasar kaydı: %20 ek iskonto.

KONUT (m² TL, 2025):
- İstanbul Avrupa merkez (Beşiktaş, Şişli): 130K–280K TL/m²
- İstanbul Anadolu merkez (Kadıköy, Üsküdar): 90K–180K TL/m²
- İstanbul çevre (Esenyurt, Pendik): 45K–90K TL/m²
- Ankara merkez (Çankaya): 40K–80K TL/m²
- İzmir merkez: 55K–110K TL/m²
- Büyük şehir (Bursa, Antalya, Kocaeli): 30K–65K TL/m²
- Orta şehir (Kayseri, Konya, Adana): 20K–40K TL/m²
- Küçük şehir/ilçe: 10K–22K TL/m²
"""

DOC_NAMES = {
    "car_file":            "Araç Ruhsatı",
    "house_file":          "Tapu Senedi",
    "transcript_file":     "Transkript / Not Dökümü",
    "income_file":         "Maaş Bordrosu / Gelir Belgesi",
    "student_certificate": "Öğrenci Belgesi",
    "family_registry":     "Nüfus / Aile Kayıt Örneği",
    "disability_report":   "Sağlık Kurulu / Engel Raporu",
}


# ── PDF → Base64 JPEG ─────────────────────────────────────────────────────────
def pdf_to_base64(file_path: str, max_pages: int = 1) -> list[str]:
    """PDF sayfalarını base64 JPEG listesine çevirir. PyMuPDF kullanır."""
    result = []
    try:
        import fitz
        doc = fitz.open(file_path)
        for i in range(min(max_pages, len(doc))):
            pix = doc[i].get_pixmap(matrix=fitz.Matrix(150/72, 150/72), colorspace=fitz.csRGB)
            result.append(base64.standard_b64encode(pix.tobytes("jpeg", jpg_quality=85)).decode())
        doc.close()
    except Exception as e:
        print(f"[Vision] pdf_to_base64 error: {e}")
    return result


# ── Claude Vision API ─────────────────────────────────────────────────────────
def _call_vision(images_b64: list[str], prompt: str) -> Optional[str]:
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key or not images_b64:
        return None
    try:
        import anthropic
        content = [
            {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": b64}}
            for b64 in images_b64[:2]
        ]
        content.append({"type": "text", "text": prompt})
        resp = anthropic.Anthropic(api_key=api_key).messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=768,
            messages=[{"role": "user", "content": content}],
        )
        return resp.content[0].text
    except Exception as e:
        print(f"[Vision] API error: {e}")
        return None


def _parse_json(text: str) -> Optional[dict]:
    try:
        m = re.search(r'\{.*\}', text, re.DOTALL)
        return json.loads(m.group()) if m else None
    except Exception:
        return None


# ── ARAÇ RUHSATI ─────────────────────────────────────────────────────────────
def analyze_car(file_path: str) -> Optional[dict]:
    """
    Ruhsat PDF'ini Claude Vision ile analiz et.
    Döner: {valid, marka, model, yil, plaka, yakit, hasar, estimated_value_tl, confidence, reasoning, message}
    None döner → Vision kullanılamadı (bloke etme)
    """
    images = pdf_to_base64(file_path, max_pages=1)
    if not images:
        return None  # PyMuPDF çalışmadı → bloke etme

    prompt = f"""Bu belgeyi incele. Türk araç ruhsatı (trafik tescil belgesi) olup olmadığını belirle.

{_MARKET}

Sadece JSON döndür, başka metin yazma:
{{
  "is_ruhsat": true/false,
  "red_reason": "geçersizse kısa Türkçe neden, yoksa null",
  "marka": "marka adı veya null",
  "model": "model adı veya null",
  "yil": yıl sayısı veya null,
  "plaka": "plaka veya null",
  "yakit": "Benzin/Dizel/Elektrik/LPG/Hibrit veya null",
  "hasar": true/false,
  "estimated_value_tl": tahmini ikinci el TL değeri (tam sayı) veya null,
  "confidence": "low"/"medium"/"high",
  "reasoning": "1-2 cümle Türkçe değerleme gerekçesi"
}}"""

    raw = _call_vision(images, prompt)
    if not raw:
        return None  # API yanıt vermedi → bloke etme

    data = _parse_json(raw)
    if not data:
        return None  # JSON parse hatası → bloke etme

    is_valid = bool(data.get("is_ruhsat"))
    val = data.get("estimated_value_tl")
    if val and not (50_000 <= int(val) <= 30_000_000):
        val = None  # Mantıksız değer → iptal

    return {
        "valid": is_valid,
        "message": "✅ Geçerli Araç Ruhsatı." if is_valid else f"❌ {data.get('red_reason', 'Bu belge araç ruhsatı değil.')}",
        "marka":  data.get("marka"),
        "model":  data.get("model"),
        "yil":    data.get("yil"),
        "plaka":  data.get("plaka"),
        "yakit":  data.get("yakit"),
        "hasar":  bool(data.get("hasar")),
        "estimated_value_tl": int(val) if val else None,
        "confidence": data.get("confidence", "medium"),
        "reasoning":  data.get("reasoning", ""),
    }


# ── TAPU SENEDİ ───────────────────────────────────────────────────────────────
def analyze_house(file_path: str) -> Optional[dict]:
    """
    Tapu PDF'ini Claude Vision ile analiz et.
    Döner: {valid, il, ilce, mahalle, yuzolcumu, nitelik, estimated_value_tl, price_per_m2, ...}
    None → Vision kullanılamadı
    """
    images = pdf_to_base64(file_path, max_pages=1)
    if not images:
        return None

    prompt = f"""Bu belgeyi incele. Türk tapusu (tapu senedi) olup olmadığını belirle.

{_MARKET}

Sadece JSON döndür, başka metin yazma:
{{
  "is_tapu": true/false,
  "red_reason": "geçersizse kısa Türkçe neden, yoksa null",
  "il": "şehir adı veya null",
  "ilce": "ilçe adı veya null",
  "mahalle": "mahalle adı veya null",
  "yuzolcumu_m2": alan m² (sayı) veya null,
  "nitelik": "Daire/Arsa/Villa/Tarla vb veya null",
  "price_per_m2": tahmini m² fiyatı TL (tam sayı) veya null,
  "estimated_value_tl": tahmini toplam değer TL (tam sayı) veya null,
  "confidence": "low"/"medium"/"high",
  "reasoning": "1-2 cümle Türkçe değerleme gerekçesi"
}}"""

    raw = _call_vision(images, prompt)
    if not raw:
        return None

    data = _parse_json(raw)
    if not data:
        return None

    is_valid = bool(data.get("is_tapu"))
    val = data.get("estimated_value_tl")
    m2p = data.get("price_per_m2")
    if val and not (500_000 <= int(val) <= 500_000_000):
        val = None

    return {
        "valid": is_valid,
        "message": "✅ Geçerli Tapu Senedi." if is_valid else f"❌ {data.get('red_reason', 'Bu belge tapu senedi değil.')}",
        "il":         data.get("il"),
        "ilce":       data.get("ilce"),
        "mahalle":    data.get("mahalle"),
        "yuzolcumu":  data.get("yuzolcumu_m2"),
        "nitelik":    data.get("nitelik"),
        "price_per_m2":       int(m2p) if m2p else None,
        "estimated_value_tl": int(val) if val else None,
        "confidence": data.get("confidence", "medium"),
        "reasoning":  data.get("reasoning", ""),
    }


# ── DİĞER BELGELER ────────────────────────────────────────────────────────────
def analyze_generic(file_path: str, doc_type: str) -> Optional[dict]:
    """Transkript, bordro, öğrenci belgesi vb. için sadece doğrulama."""
    images = pdf_to_base64(file_path, max_pages=2)
    if not images:
        return None

    doc_name = DOC_NAMES.get(doc_type, doc_type)
    prompt = f"""Bu belgeyi incele. Bir "{doc_name}" olup olmadığını belirle.

Sadece JSON döndür:
{{"is_valid": true/false, "reason": "1 cümle Türkçe gerekçe"}}"""

    raw = _call_vision(images, prompt)
    if not raw:
        return None

    data = _parse_json(raw)
    if not data:
        return None

    is_valid = bool(data.get("is_valid"))
    return {
        "valid": is_valid,
        "message": f"✅ Geçerli {doc_name}." if is_valid else f"❌ {data.get('reason', 'Yanlış belge türü.')}",
    }
