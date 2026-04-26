"""
PSDS — Claude Vision ile Belge Analizi

Akış (Hoca onaylı):
  PDF/Resim → PyMuPDF ile görüntüye çevir → Claude Vision API'ye gönder
  → Belge doğrula + alanları çıkar + piyasa değeri tahmin et

Avantaj: Tesseract binary kurulumu gerektirmez, Türkçe belgelerde çok daha güvenilir.
"""

import os
import re
import json
import base64
from typing import Optional


# ── PDF/Resim → Base64 ────────────────────────────────────────────────────────
def file_to_base64_images(file_path: str, max_pages: int = 2) -> list[str]:
    """
    PDF veya resim dosyasını base64 JPEG listesine çevirir.
    PDF → PyMuPDF ile her sayfa 150 DPI'de render edilir.
    Resim → direkt JPEG base64'e çevrilir.
    """
    ext = os.path.splitext(file_path)[1].lower()
    images_b64 = []

    if ext == ".pdf":
        try:
            import fitz  # PyMuPDF
            doc = fitz.open(file_path)
            for i, page in enumerate(doc):
                if i >= max_pages:
                    break
                mat = fitz.Matrix(150 / 72, 150 / 72)   # 150 DPI — kalite/hız dengesi
                pix = page.get_pixmap(matrix=mat, colorspace=fitz.csRGB)
                img_bytes = pix.tobytes("jpeg", jpg_quality=85)
                images_b64.append(base64.standard_b64encode(img_bytes).decode("utf-8"))
            doc.close()
        except Exception as e:
            print(f"[Vision] PDF→image error: {e}")

    elif ext in [".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".webp"]:
        try:
            from PIL import Image
            import io
            img = Image.open(file_path).convert("RGB")
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=85)
            images_b64.append(base64.standard_b64encode(buf.getvalue()).decode("utf-8"))
        except Exception as e:
            print(f"[Vision] Image→base64 error: {e}")

    return images_b64


# ── Claude Vision API çağrısı ─────────────────────────────────────────────────
def _call_claude_vision(images_b64: list[str], prompt: str) -> Optional[str]:
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return None
    if not images_b64:
        return None
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)

        content = []
        for img_b64 in images_b64[:2]:   # max 2 sayfa
            content.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/jpeg",
                    "data": img_b64,
                },
            })
        content.append({"type": "text", "text": prompt})

        message = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=768,
            messages=[{"role": "user", "content": content}],
        )
        return message.content[0].text
    except Exception as e:
        print(f"[Vision] Claude API error: {e}")
        return None


def _parse_json(text: str) -> Optional[dict]:
    try:
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            return json.loads(match.group())
    except Exception:
        pass
    return None


# ── DOC_NAMES — belge tür adları ─────────────────────────────────────────────
DOC_NAMES = {
    "car_file":            "Araç Ruhsatı (vehicle registration)",
    "house_file":          "Tapu Senedi (property title deed)",
    "transcript_file":     "Transkript / Not Dökümü",
    "income_file":         "Maaş Bordrosu / Gelir Belgesi",
    "student_certificate": "Öğrenci Belgesi",
    "family_registry":     "Nüfus / Aile Kayıt Örneği",
    "disability_report":   "Sağlık Kurulu / Engel Raporu",
}


# ── ARAÇ: doğrulama + değer tahmini ──────────────────────────────────────────
def analyze_car_document(file_path: str) -> dict:
    """
    Ruhsat görselini Claude'a gönder:
    - Belge türü doğrula (ruhsat mı?)
    - Marka/model/yıl/plaka çıkar
    - Tahmini ikinci el piyasa değerini hesapla (TL)
    """
    images_b64 = file_to_base64_images(file_path, max_pages=1)
    if not images_b64:
        return _car_fallback(valid=None, msg="⚠️ Belge görüntüye dönüştürülemedi, manuel incelemeye alınacak.")

    prompt = """Bu belgeyi incele ve aşağıdaki JSON formatında yanıt ver. Başka metin yazma.

Görevin:
1. Bu belgenin bir Türk araç ruhsatı (trafik tescil belgesi) olup olmadığını belirle.
2. Eğer ruhsatsa, araç bilgilerini çıkar.
3. 2025 yılı Türkiye ikinci el araç piyasasına göre tahmini değeri hesapla.

Türkiye 2025 ikinci el araç piyasa fiyat rehberi:
- Segment B (Fiat Egea, Renault Clio, VW Polo): 900K–1.3M TL (2020 model)
- Segment C (Toyota Corolla, Honda Civic, Hyundai i30): 1.2M–1.8M TL (2020 model)
- Segment D (BMW 3, Mercedes C, VW Passat): 2.0M–3.5M TL (2020 model)
- SUV (Toyota RAV4, BMW X3): 2.5M–4.5M TL (2020 model)
- Lüks (BMW 5, Mercedes E): 4M–8M TL (2020 model)
- Her yıl için ~%12 amortisman, hasar kaydı varsa %20 daha düşük

{
  "is_valid_doc": true veya false,
  "reason_if_invalid": "geçersizse neden (Türkçe)",
  "marka": "araç markası veya null",
  "model": "araç modeli veya null",
  "yil": yıl sayısı veya null,
  "plaka": "plaka veya null",
  "yakit": "Benzin/Dizel/Elektrik/LPG/Hibrit veya null",
  "hasar": true veya false,
  "estimated_value_tl": tahmini TL değeri (tam sayı) veya null,
  "confidence": "low" veya "medium" veya "high",
  "reasoning": "1-2 cümle Türkçe değerleme gerekçesi"
}"""

    response = _call_claude_vision(images_b64, prompt)
    if not response:
        return _car_fallback(valid=None, msg="⚠️ Vision servisi yanıt vermedi.")

    parsed = _parse_json(response)
    if not parsed:
        return _car_fallback(valid=None, msg="⚠️ Yanıt işlenemedi.")

    is_valid = bool(parsed.get("is_valid_doc"))

    if not is_valid:
        reason = parsed.get("reason_if_invalid", "Bu belge araç ruhsatı değil.")
        return {
            "valid": False,
            "message": f"❌ {reason}",
            "extracted": {},
            "estimated_value": None,
            "confidence": "high",
            "source": "Claude Vision",
        }

    extracted = {
        "marka":  parsed.get("marka"),
        "model":  parsed.get("model"),
        "yil":    parsed.get("yil"),
        "plaka":  parsed.get("plaka"),
        "yakit":  parsed.get("yakit"),
        "hasar":  parsed.get("hasar", False),
    }
    val = parsed.get("estimated_value_tl")
    if val and not (50_000 <= int(val) <= 30_000_000):
        val = None   # Makul aralık dışıysa iptal

    return {
        "valid": True,
        "message": "✅ Geçerli Araç Ruhsatı tespit edildi.",
        "extracted": extracted,
        "estimated_value": int(val) if val else None,
        "confidence": parsed.get("confidence", "medium"),
        "reasoning": parsed.get("reasoning", ""),
        "source": "Claude Vision",
    }


# ── TAPU: doğrulama + değer tahmini ──────────────────────────────────────────
def analyze_house_document(file_path: str) -> dict:
    """
    Tapu görselini Claude'a gönder:
    - Tapu mu?
    - İl/ilçe/m²/nitelik çıkar
    - Tahmini piyasa değerini hesapla (TL)
    """
    images_b64 = file_to_base64_images(file_path, max_pages=1)
    if not images_b64:
        return _house_fallback(valid=None, msg="⚠️ Belge görüntüye dönüştürülemedi, manuel incelemeye alınacak.")

    prompt = """Bu belgeyi incele ve aşağıdaki JSON formatında yanıt ver. Başka metin yazma.

Görevin:
1. Bu belgenin bir Türk tapusu (tapu senedi / tapu belgesi) olup olmadığını belirle.
2. Eğer tapuysa, taşınmaz bilgilerini çıkar.
3. 2025 yılı Türkiye gayrimenkul piyasasına göre tahmini değeri hesapla.

Türkiye 2025 konut m² fiyat rehberi:
- İstanbul Avrupa merkez (Beşiktaş, Şişli): 130K–280K TL/m²
- İstanbul Anadolu merkez (Kadıköy, Üsküdar): 90K–180K TL/m²
- İstanbul çevre (Esenyurt, Pendik): 45K–90K TL/m²
- Ankara merkez (Çankaya): 40K–80K TL/m²
- İzmir merkez: 55K–110K TL/m²
- Büyük şehirler (Bursa, Antalya): 30K–65K TL/m²
- Orta şehirler (Kayseri, Konya): 20K–40K TL/m²
- Küçük şehir/ilçe: 10K–22K TL/m²

{
  "is_valid_doc": true veya false,
  "reason_if_invalid": "geçersizse neden (Türkçe)",
  "il": "şehir adı veya null",
  "ilce": "ilçe adı veya null",
  "mahalle": "mahalle adı veya null",
  "yuzolcumu_m2": alan m² (sayı) veya null,
  "nitelik": "Daire/Arsa/Villa/Tarla vb. veya null",
  "price_per_m2": tahmini m² fiyatı (TL, tam sayı) veya null,
  "estimated_value_tl": tahmini toplam değer (TL, tam sayı) veya null,
  "confidence": "low" veya "medium" veya "high",
  "reasoning": "1-2 cümle Türkçe değerleme gerekçesi"
}"""

    response = _call_claude_vision(images_b64, prompt)
    if not response:
        return _house_fallback(valid=None, msg="⚠️ Vision servisi yanıt vermedi.")

    parsed = _parse_json(response)
    if not parsed:
        return _house_fallback(valid=None, msg="⚠️ Yanıt işlenemedi.")

    is_valid = bool(parsed.get("is_valid_doc"))

    if not is_valid:
        reason = parsed.get("reason_if_invalid", "Bu belge tapu senedi değil.")
        return {
            "valid": False,
            "message": f"❌ {reason}",
            "extracted": {},
            "estimated_value": None,
            "price_per_m2": None,
            "confidence": "high",
            "source": "Claude Vision",
        }

    extracted = {
        "il":           parsed.get("il"),
        "ilce":         parsed.get("ilce"),
        "mahalle":      parsed.get("mahalle"),
        "yuzolcumu":    parsed.get("yuzolcumu_m2"),
        "nitelik":      parsed.get("nitelik"),
    }
    val = parsed.get("estimated_value_tl")
    m2p = parsed.get("price_per_m2")
    if val and not (500_000 <= int(val) <= 500_000_000):
        val = None

    return {
        "valid": True,
        "message": "✅ Geçerli Tapu Senedi tespit edildi.",
        "extracted": extracted,
        "estimated_value": int(val) if val else None,
        "price_per_m2": int(m2p) if m2p else None,
        "confidence": parsed.get("confidence", "medium"),
        "reasoning": parsed.get("reasoning", ""),
        "source": "Claude Vision",
    }


# ── DİĞER BELGELER: sadece doğrulama ──────────────────────────────────────────
def analyze_generic_document(file_path: str, doc_type: str) -> dict:
    """Transkript, bordro, öğrenci belgesi vb. için sadece doğrulama."""
    images_b64 = file_to_base64_images(file_path, max_pages=2)
    if not images_b64:
        return {"valid": None, "message": "⚠️ Belge görüntüye dönüştürülemedi.", "source": "Claude Vision"}

    doc_name = DOC_NAMES.get(doc_type, doc_type)
    prompt = f"""Bu belgeyi incele.

Soru: Bu belge bir "{doc_name}" midir?

Sadece JSON formatında yanıt ver:
{{
  "is_valid_doc": true veya false,
  "reason": "1 cümle Türkçe gerekçe"
}}"""

    response = _call_claude_vision(images_b64, prompt)
    if not response:
        return {"valid": None, "message": "⚠️ Vision servisi yanıt vermedi.", "source": "Claude Vision"}

    parsed = _parse_json(response)
    if not parsed:
        return {"valid": None, "message": "⚠️ Yanıt işlenemedi.", "source": "Claude Vision"}

    is_valid = bool(parsed.get("is_valid_doc"))
    reason = parsed.get("reason", "")

    return {
        "valid": is_valid,
        "message": f"✅ Geçerli {doc_name}." if is_valid else f"❌ {reason}",
        "source": "Claude Vision",
    }


# ── Fallback döndürücüler ─────────────────────────────────────────────────────
def _car_fallback(valid, msg: str) -> dict:
    return {
        "valid": valid,
        "message": msg,
        "extracted": {},
        "estimated_value": None,
        "confidence": "low",
        "source": "Claude Vision (hata)",
    }

def _house_fallback(valid, msg: str) -> dict:
    return {
        "valid": valid,
        "message": msg,
        "extracted": {},
        "estimated_value": None,
        "price_per_m2": None,
        "confidence": "low",
        "source": "Claude Vision (hata)",
    }
