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
"disability_report":   "Sağlık Kurulu / Engel Raporu",
}


# ── PDF → Base64 JPEG ─────────────────────────────────────────────────────────
def pdf_to_base64(file_path: str, max_pages: int = 1) -> list[str]:
    """PDF sayfalarını base64 JPEG listesine çevirir. PyMuPDF kullanır.

    96 DPI: belge okunabilirliğini korurken ~3x daha az RAM kullanır.
    150 DPI → ~6MB/sayfa  |  96 DPI → ~2.5MB/sayfa (Render free 512MB için kritik)
    """
    result = []
    try:
        import fitz
        doc = fitz.open(file_path)
        for i in range(min(max_pages, len(doc))):
            pix = doc[i].get_pixmap(matrix=fitz.Matrix(96/72, 96/72), colorspace=fitz.csRGB)
            jpeg_bytes = pix.tobytes("jpeg", jpg_quality=75)
            result.append(base64.standard_b64encode(jpeg_bytes).decode())
            del pix          # RAM'i hemen serbest bırak
            del jpeg_bytes
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
            for b64 in images_b64[:1]   # RAM tasarrufu: 1 sayfa yeterli
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

ÖNEMLİ ALAN AYRIMI:
- "Yüz Ölçümü" / "Yüzölçümü" = ARSA/PARSEL alanı (toplam taşınmaz), bağımsız bölüm m² DEĞİL
- Bağımsız bölüm m²'si (daire/dükkan/ofis) çoğunlukla tapuda YAZILMAZ
- "Arsa Payı" (örn: 10/100) = kişinin tüm arsa üzerindeki hisse oranı
- "Bağımsız Bölüm" niteliği: Mesken/Dükkan/Ofis/Depo vb.
- "Kat": Bodrum/Zemin/1/2/3 vb.

ŞEHİR TESPİTİ — ZORUNLU KURALLAR:
- "İl" alanı BOŞSA veya okunamıyorsa: İlçe, mahalle, sokak, kadastro müdürlüğü adından şehri çıkar
- Eski tapularda (2010 öncesi) "İlçesi" alanında il adı yazabilir (örn. İlçesi=İSTANBUL → il=İstanbul)
  Bu durumda gerçek ilçeyi "Mahallesi" veya "Sokağı" alanından bul (örn. Mahalle=Büyükçekmece → ilce=Büyükçekmece)
- Büyükçekmece, Esenyurt, Beşiktaş, Kadıköy vb. → hepsi İstanbul ilçesidir
- il asla null döndürme, bağlamdan mutlaka çıkar

NİTELİK TESPİTİ:
- "Dükkan", "Dükkân", "DÜKKAN" → nitelik="Dükkan"
- "Mesken", "Konut", "Daire" → nitelik="Mesken"
- "Büro", "Ofis" → nitelik="Ofis"
- "Depo", "Ambar" → nitelik="Depo"

{_MARKET}

Sadece JSON döndür, başka metin yazma:
{{
  "is_tapu": true/false,
  "red_reason": "geçersizse kısa Türkçe neden, yoksa null",
  "il": "şehir adı (bağlamdan çıkar, asla null bırakma)",
  "ilce": "gerçek ilçe adı veya null",
  "mahalle": "mahalle adı veya null",
  "tapu_turu": "Kat İrtifakı / Kat Mülkiyeti / Müstakil / Arsa / Tarla veya null",
  "arsa_yuzolcumu_m2": TAPU'daki Yüz Ölçümü alanındaki rakam (sayı) veya null,
  "arsa_payi": "10/100 gibi pay/payda string veya null",
  "daire_m2": sadece belgede açıkça yazıyorsa bağımsız bölüm net m² (sayı), yoksa null,
  "kat": "Bodrum/Zemin/1/2/3 vb veya null",
  "nitelik": "Daire/Mesken/Dükkan/Ofis/Depo/Arsa/Villa/Tarla veya null",
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

    # ── Bağımsız bölüm m²'sini hesapla ──────────────────────────────────────
    # Öncelik: belgede açık daire_m2 > arsa payı tahmini > None
    daire_m2 = data.get("daire_m2")
    arsa_m2  = data.get("arsa_yuzolcumu_m2")
    arsa_payi_str = data.get("arsa_payi")  # "10/100"
    tapu_turu = data.get("tapu_turu", "")
    nitelik_raw = data.get("nitelik", "") or ""
    kat = data.get("kat", "")

    # Ticari/dükkan tapularda m² nadiren yazılır — arsa payından tahmin et
    is_ticari = any(k in nitelik_raw.lower() for k in ["dükkan", "dukkan", "ofis", "depo", "büro", "buro"])

    if not daire_m2 and arsa_m2 and arsa_payi_str:
        try:
            pay, payda = arsa_payi_str.replace(" ", "").split("/")
            oran = int(pay) / int(payda)
            hesap = round(arsa_m2 * oran)
            if is_ticari:
                # Dükkan için makul alt sınır yok — hesabı doğrudan kullan (min 10 m²)
                daire_m2 = max(hesap, 10)
            else:
                # Konut için 40 m² alt sınır (küçük hesaplar genellikle yanlış)
                daire_m2 = max(hesap, 40) if hesap < 40 else hesap
        except Exception:
            daire_m2 = None

    bodrum_notu = ""
    if kat and "bodrum" in str(kat).lower():
        bodrum_notu = " (Bodrum kat — değer düşük olabilir)"

    return {
        "valid": is_valid,
        "message": "✅ Geçerli Tapu Senedi." if is_valid else f"❌ {data.get('red_reason', 'Bu belge tapu senedi değil.')}",
        "il":           data.get("il"),
        "ilce":         data.get("ilce"),
        "mahalle":      data.get("mahalle"),
        "yuzolcumu":    daire_m2,          # Artık daire m²'si (arsa değil)
        "arsa_yuzolcumu": arsa_m2,         # Ham arsa alanı (referans)
        "arsa_payi":    arsa_payi_str,
        "tapu_turu":    tapu_turu,
        "kat":          kat,
        "nitelik":      data.get("nitelik"),
        "price_per_m2":       int(m2p) if m2p else None,
        "estimated_value_tl": int(val) if val else None,
        "confidence":   data.get("confidence", "medium"),
        "reasoning":    data.get("reasoning", "") + bodrum_notu,
    }


# ── TRANSKRİPT ───────────────────────────────────────────────────────────────
def analyze_transcript(file_path: str) -> Optional[dict]:
    """
    Transkript PDF'ini Vision ile analiz et.
    Döner: {valid, universite, bolum, gno, sistem, sinif, message}
    None → Vision kullanılamadı
    """
    images = pdf_to_base64(file_path, max_pages=2)
    if not images:
        return None

    prompt = """Bu belgeyi incele. Öğrencinin not dökümü (transkript) olup olmadığını belirle.

TRANSKRİPT TANIMI: Üniversite/yükseköğretim kurumunun resmi not belgesi. Ders listesi, notlar ve genel not ortalaması (GNO/GPA/CGPA) içerir.

NOT ORTALAMASI TESPİTİ — ZORUNLU KURALLAR:
- "GNO", "Genel Not Ortalaması", "CGPA", "GPA", "Overall GPA", "Kümülatif Ortalama" → genel ortalama
- 4.00'lık sistemde: 0.00–4.00 arası bir sayı (örn. 3.14, 2.87, 3.50)
- 100'lük sistemde: 0–100 arası bir sayı (örn. 72.4, 85.0)
- Eğer her iki sistem de varsa 4.00'lık sistemi tercih et
- Son yarıyıl/dönem GNO'su değil, GENEL (kümülatif) ortalamayı al
- Sayfa başlığında veya en alt satırda yazar
- Ders bazlı notları (AA, BB, 85 gibi) ALMA — sadece genel ortalamayı al

Sadece JSON döndür, başka metin yazma:
{
  "is_transcript": true/false,
  "red_reason": "geçersizse kısa Türkçe neden, yoksa null",
  "universite": "üniversite adı veya null",
  "bolum": "bölüm/program adı veya null",
  "sinif": "1/2/3/4/Yüksek Lisans veya null",
  "gno": genel not ortalaması sayı olarak (örn. 3.14 veya 78.5) veya null,
  "sistem": "4" veya "100" (GNO hangi sistemde?) veya null,
  "donem_sayisi": tamamlanan dönem sayısı (tam sayı) veya null
}"""

    raw = _call_vision(images, prompt)
    if not raw:
        return None

    data = _parse_json(raw)
    if not data:
        return None

    is_valid = bool(data.get("is_transcript"))
    gno = data.get("gno")

    # Makul aralık kontrolü
    sistem = str(data.get("sistem") or "4")
    if gno is not None:
        try:
            gno = float(gno)
            if sistem == "4" and not (0.0 <= gno <= 4.0):
                gno = None
            elif sistem == "100" and not (0.0 <= gno <= 100.0):
                gno = None
        except (TypeError, ValueError):
            gno = None

    return {
        "valid":      is_valid,
        "message":    "✅ Geçerli Transkript." if is_valid else f"❌ {data.get('red_reason', 'Bu belge transkript değil.')}",
        "universite": data.get("universite"),
        "bolum":      data.get("bolum"),
        "sinif":      data.get("sinif"),
        "gno":        round(gno, 2) if gno is not None else None,
        "sistem":     sistem if gno is not None else None,
        "donem_sayisi": data.get("donem_sayisi"),
    }


def analyze_income(file_path: str) -> Optional[dict]:
    """
    Bordro veya banka ekstresi PDF'ini Vision ile analiz et.
    Döner: {valid, net_aylik, income_bracket, kaynak, message}
    """
    images = pdf_to_base64(file_path, max_pages=2)
    if not images:
        return None

    prompt = """Bu belgeyi incele. Maaş bordrosu veya banka hesap ekstresi olup olmadığını belirle.

GELİR TESPİTİ KURALLARI:
- BORDRO: "NET ÖDENEN" veya "NET ÜCRET" satırındaki tutarı al (brüt değil)
- HESAP EKSTRESİ: "Maaş" etiketli kredi girişlerini bul, AVANS olanları hariç tut, kalanların ortalamasını al
- Tutar Türk lirası (TL) cinsinden olmalı
- Başka ülke para birimi veya çok eski tarih → geçersiz

Sadece JSON döndür:
{
  "is_income_doc": true/false,
  "red_reason": "geçersizse kısa Türkçe neden, yoksa null",
  "net_aylik": aylık net gelir sayı olarak (örn. 21126.68) veya null,
  "kaynak": "bordro" veya "ekstre" veya null
}"""

    raw = _call_vision(images, prompt)
    if not raw:
        return None
    data = _parse_json(raw)
    if not data:
        return None

    is_valid = bool(data.get("is_income_doc"))
    net_aylik = None
    income_bracket = None
    try:
        val = data.get("net_aylik")
        if val is not None:
            net_aylik = float(val)
            if net_aylik < 22_000:     income_bracket = "under_22000"
            elif net_aylik < 40_000:   income_bracket = "22000_40000"
            elif net_aylik < 75_000:   income_bracket = "40000_75000"
            elif net_aylik < 150_000:  income_bracket = "75000_150000"
            else:                       income_bracket = "over_150000"
    except (TypeError, ValueError):
        pass

    return {
        "valid":          is_valid,
        "message":        "✅ Geçerli Gelir Belgesi." if is_valid else f"❌ {data.get('red_reason', 'Bu belge gelir belgesi değil.')}",
        "net_aylik":      net_aylik,
        "income_bracket": income_bracket,
        "kaynak":         data.get("kaynak"),
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
