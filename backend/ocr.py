import os
import re
from typing import Optional

# ── Belge imzaları — anahtar kelime tabanlı doğrulama ─────────
DOC_SIGNATURES: dict = {
    "car_file": {
        "name": "Araç Ruhsatı",
        "keywords": [
            "RUHSAT", "TESCİL", "PLAKA", "ARAÇ", "ŞASI NO", "ŞASI NUMARASI",
            "MOTOR NO", "MOTOR NUMARASI", "TRAFİK TESCİL", "MOTORLU TAŞIT",
            "CİNS", "MARKA", "TİP", "RENK", "MODEL YILI",
        ],
        "min_hits": 2,
    },
    "house_file": {
        "name": "Tapu Senedi",
        "keywords": [
            "TAPU", "MALİK", "PARSEL", "ADA", "YÜZÖLÇÜM", "KADASTRO",
            "MÜLKİYET", "TKGM", "TAPU VE KADASTRO", "GAYRİMENKUL",
            "BAĞIMSIZ BÖLÜM", "ARSA PAYI",
        ],
        "min_hits": 2,
    },
    "transcript_file": {
        "name": "Transkript / Not Dökümü",
        "keywords": [
            "TRANSKRİPT", "NOT DÖKÜM", "GNO", "DÖNEM", "DERS KODU",
            "GPA", "GRADE", "ORTALAMA", "KREDİ", "SINAV NOTU",
            "ÜNİVERSİTE", "FAKÜLTE", "BÖLÜM",
        ],
        "min_hits": 3,
    },
    "income_file": {
        "name": "Gelir / Maaş Belgesi",
        "keywords": [
            "BORDRO", "MAAŞ", "SGK", "NET ÜCRET", "BRÜT", "GELİR VERGİSİ",
            "AYLIK ÜCRETİ", "SOSYAL GÜVENLİK", "PRİM", "KESİNTİ",
            "ÖDEME TUTARI", "ÇALIŞAN",
        ],
        "min_hits": 2,
    },
    "student_certificate": {
        "name": "Öğrenci Belgesi",
        "keywords": [
            "ÖĞRENCİ BELGESİ", "ÖĞRENCİ", "KAYITLI", "ÜNİVERSİTE",
            "BÖLÜM", "SINIF", "ÖĞRENCİ NUMARASI", "FAKÜLTE",
            "AKTİF ÖĞRENCİ", "ÖĞRENCİ İŞLERİ",
        ],
        "min_hits": 2,
    },
    "family_registry": {
        "name": "Nüfus / Aile Kayıt Örneği",
        "keywords": [
            "NÜFUS", "AİLE", "KÜTÜKLERİ", "VUKUATLI", "NÜFUS MÜDÜRLÜĞÜ",
            "TC KİMLİK", "DOĞUM YERİ", "ANA ADI", "BABA ADI",
            "MERNİS", "E-DEVLET",
        ],
        "min_hits": 2,
    },
    "disability_report": {
        "name": "Sağlık / Engel Raporu",
        "keywords": [
            "RAPOR", "SAĞLIK KURULU", "ENGELLİLİK", "HASTANE",
            "HEYET RAPORU", "TANI", "HASTALIK", "ENGELLİLİK ORANI",
            "SAĞLIK KURUMU", "DOKTOR", "HEKİM",
        ],
        "min_hits": 2,
    },
}


def validate_document(file_path: str, expected_doc_id: str) -> dict:
    """
    Yüklenen dosyanın beklenen belge türüne uygun olup olmadığını kontrol eder.
    Döndürür: {valid, expected_name, detected_name, message, confidence, hits}
    """
    sig = DOC_SIGNATURES.get(expected_doc_id)

    if not sig:
        return {
            "valid": True,
            "expected_name": expected_doc_id,
            "detected_name": expected_doc_id,
            "message": "Belge alındı.",
            "confidence": 1.0,
            "hits": 0,
        }

    text = extract_text(file_path)

    # PDF okunamıyor veya çok kısa — geçersiz say
    if not text or len(text.strip()) < 50:
        return {
            "valid": False,
            "expected_name": sig["name"],
            "detected_name": None,
            "message": (
                f"❌ Belge okunamadı veya boş. "
                f"Lütfen metin içeren geçerli bir {sig['name']} PDF'i yükleyin."
            ),
            "confidence": 0.0,
            "hits": 0,
        }

    text_upper = text.upper()

    # Beklenen türe kaç anahtar kelime eşleşti?
    hits = sum(1 for kw in sig["keywords"] if kw in text_upper)
    confidence = round(hits / len(sig["keywords"]), 2)
    valid = hits >= sig["min_hits"]

    # Başka bir tür mü daha çok eşleşiyor?
    best_other: Optional[str] = None
    best_other_hits = 0
    for doc_id, other_sig in DOC_SIGNATURES.items():
        if doc_id == expected_doc_id:
            continue
        other_hits = sum(1 for kw in other_sig["keywords"] if kw in text_upper)
        if other_hits >= other_sig["min_hits"] and other_hits > best_other_hits:
            best_other_hits = other_hits
            best_other = other_sig["name"]

    if valid:
        message = f"✅ Geçerli {sig['name']} tespit edildi."
        detected = sig["name"]
    elif best_other:
        message = (
            f"❌ Yüklenen dosya '{best_other}' gibi görünüyor. "
            f"Bu alana lütfen geçerli bir {sig['name']} yükleyin."
        )
        detected = best_other
    else:
        message = (
            f"❌ Bu PDF'in {sig['name']} olduğu doğrulanamadı. "
            f"Lütfen doğru belgeyi yükleyin."
        )
        detected = None

    return {
        "valid": valid,
        "expected_name": sig["name"],
        "detected_name": detected,
        "message": message,
        "confidence": confidence,
        "hits": hits,
    }


def _extract_text_from_pdf(file_path: str) -> str:
    try:
        import pdfplumber
        with pdfplumber.open(file_path) as pdf:
            text = ""
            for page in pdf.pages:
                t = page.extract_text()
                if t:
                    text += t + "\n"
        return text
    except Exception:
        return ""


def _extract_text_from_image(file_path: str) -> str:
    try:
        import pytesseract
        from PIL import Image
        img = Image.open(file_path)
        text = pytesseract.image_to_string(img, lang="tur+eng")
        return text
    except Exception:
        try:
            import pytesseract
            from PIL import Image
            img = Image.open(file_path)
            text = pytesseract.image_to_string(img, lang="eng")
            return text
        except Exception:
            return ""


def extract_text(file_path: str) -> str:
    ext = os.path.splitext(file_path)[1].lower()
    if ext == ".pdf":
        return _extract_text_from_pdf(file_path)
    elif ext in [".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".webp"]:
        return _extract_text_from_image(file_path)
    return ""


def parse_ruhsat(file_path: str) -> dict:
    """Araç ruhsatından bilgileri çek (vehicle registration)"""
    text = extract_text(file_path)
    result = {
        "plaka": None,
        "marka": None,
        "model": None,
        "yil": None,
        "motor_hacmi": None,
        "yakit_tipi": None,
        "sahip_adi": None,
        "ocr_success": bool(text and len(text) > 20),
    }

    if not text:
        return result

    text_upper = text.upper()

    # Plaka: örn. 34ABC123 ya da 34 ABC 123
    plaka_match = re.search(r'\b(\d{2}\s?[A-Z]{1,3}\s?\d{2,5})\b', text_upper)
    if plaka_match:
        result["plaka"] = plaka_match.group(1).replace(" ", "")

    # Marka
    brands = [
        "VOLKSWAGEN", "TOYOTA", "MERCEDES", "BMW", "AUDI",
        "RENAULT", "FIAT", "OPEL", "FORD", "HYUNDAI", "KIA",
        "HONDA", "NISSAN", "PEUGEOT", "CITROEN", "DACIA",
        "SEAT", "SKODA", "VOLVO", "TOFAS", "MITSUBISHI",
        "SUZUKI", "SUBARU", "JEEP", "LAND ROVER", "PORSCHE",
    ]
    for brand in brands:
        if brand in text_upper:
            result["marka"] = brand.title()
            break

    # Model yılı (1990–2026)
    year_match = re.search(r'\b(19[9]\d|20[0-2]\d)\b', text)
    if year_match:
        result["yil"] = int(year_match.group(1))

    # Motor hacmi
    motor_match = re.search(r'(\d{3,5})\s*cc', text, re.IGNORECASE)
    if not motor_match:
        motor_match = re.search(r'(\d[.,]\d{1,2})\s*(?:lt|litre|liter|l\b)', text, re.IGNORECASE)
    if motor_match:
        result["motor_hacmi"] = motor_match.group(1)

    # Yakıt tipi
    fuel_map = {
        "Dizel": ["DİZEL", "DIESEL", "GAZOIL", "MAZOT"],
        "Benzin": ["BENZİN", "BENZIN", "GASOLINE", "PETROL"],
        "Elektrik": ["ELEKTRİK", "ELEKTRIK", "ELECTRIC", "BEV"],
        "Hibrit": ["HİBRİT", "HIBRIT", "HYBRID"],
        "LPG": ["LPG", "AUTOGAS"],
    }
    for fuel_name, keywords in fuel_map.items():
        if any(k in text_upper for k in keywords):
            result["yakit_tipi"] = fuel_name
            break

    # Tescil sahibi adı (genellikle "TESCİL SAHİBİ" veya "AD SOYAD" satırından sonra)
    name_match = re.search(
        r'(?:TESCİL SAHİBİ|SAHIP ADI|AD SOYAD)[:\s]+([A-ZÇĞİÖŞÜa-zçğışöüÇĞİÖŞÜ ]{5,40})',
        text, re.IGNORECASE
    )
    if name_match:
        result["sahip_adi"] = name_match.group(1).strip()

    return result


def parse_tapu(file_path: str) -> dict:
    """Tapu senedinden bilgileri çek (property deed)"""
    text = extract_text(file_path)
    result = {
        "il": None,
        "ilce": None,
        "mahalle": None,
        "yuzolcumu": None,
        "nitelik": None,
        "malik": None,
        "ocr_success": bool(text and len(text) > 20),
    }

    if not text:
        return result

    text_upper = text.upper()

    # İl / Şehir
    provinces = [
        "İSTANBUL", "ISTANBUL", "ANKARA", "İZMİR", "IZMIR", "BURSA",
        "ANTALYA", "ADANA", "KONYA", "GAZİANTEP", "GAZIANTEP",
        "KAYSERİ", "KAYSERI", "MERSİN", "MERSIN", "ESKİŞEHİR", "ESKISEHIR",
        "DİYARBAKIR", "DIYARBAKIR", "SAMSUN", "TRABZON", "MALATYA",
        "GEBZe", "KOCAELI", "KOCAELİ",
    ]
    for province in provinces:
        norm = province.upper()
        if norm in text_upper:
            display = province.replace("İ", "İ").title()
            result["il"] = display
            break

    # Yüzölçümü / alan m²
    area_patterns = [
        r'(?:YÜZÖLÇÜMü|YÜZÖLÇÜMÜ|ALAN)[:\s]*(\d+[.,]\d+)\s*(?:m[²2])?',
        r'(\d+[.,]\d+)\s*m[²2]',
        r'(\d{2,5}[.,]\d{2})\s*m',
    ]
    for pattern in area_patterns:
        area_match = re.search(pattern, text, re.IGNORECASE)
        if area_match:
            area_str = area_match.group(1).replace(",", ".")
            try:
                result["yuzolcumu"] = float(area_str)
                break
            except Exception:
                pass

    # Nitelik (property type)
    if any(k in text_upper for k in ["DAİRE", "DAIRE", "APARTMAN"]):
        result["nitelik"] = "Daire"
    elif "ARSA" in text_upper:
        result["nitelik"] = "Arsa"
    elif "TARLA" in text_upper:
        result["nitelik"] = "Tarla"
    elif any(k in text_upper for k in ["BAĞIMSIZ BÖLÜM", "BAGIMSIZ BOLUM"]):
        result["nitelik"] = "Bağımsız Bölüm"
    elif "VİLLA" in text_upper or "VILLA" in text_upper:
        result["nitelik"] = "Villa"

    # Malik (sahip)
    malik_match = re.search(
        r'(?:MALİK|MALIK|SAHİP)[:\s]+([A-ZÇĞİÖŞÜa-zçğışöüÇĞİÖŞÜ ]{5,50})',
        text, re.IGNORECASE
    )
    if malik_match:
        result["malik"] = malik_match.group(1).strip()

    return result
