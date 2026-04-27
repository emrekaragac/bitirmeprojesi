import os
import re
from typing import Optional

# ── Belge imzaları — anahtar kelime tabanlı doğrulama ─────────
DOC_SIGNATURES: dict = {
    "car_file": {
        "name": "Araç Ruhsatı",
        # required_any: belgede kesinlikle bunlardan biri olmalı
        # Gerçek ruhsattan kontrol edildi: ŞASE NO (ŞASİ değil!), PLAKA, MOTOR NO
        "required_any": [
            "PLAKA", "ŞASE NO", "ŞASE NUMARASI", "ŞASI NO", "MOTOR NO",
            "TESCİL SIRA NO", "MODEL YILI", "TRAFİK TESCİL", "RUHSAT",
        ],
        "keywords": [
            # Gerçek ruhsat alanları (PHOTO-2026... belgesiyle doğrulandı)
            "PLAKA", "MARKASI", "MARKA", "TESCİL", "MODEL YILI",
            "ŞASE NO", "ŞASE NUMARASI", "ŞASI NO",  # her iki yazım
            "MOTOR NO", "SİLİNDİR HACMİ", "MOTOR GÜCÜ",
            "YAKIT CİNSİ", "RENK", "CİNS", "TİP", "ARAÇ SINIFI",
            "TESCİL SIRA NO", "KULLANIM AMACI", "NET AĞIRLIĞI",
        ],
        "min_hits": 3,
    },
    "house_file": {
        "name": "Tapu Senedi",
        "required_any": ["TAPU", "TKGM", "TAPU VE KADASTRO", "KADASTRO MÜDÜRLÜĞÜ", "MALİK", "PARSEL"],
        "keywords": [
            "TAPU", "MALİK", "PARSEL", "ADA", "YÜZÖLÇÜM", "KADASTRO",
            "MÜLKİYET", "TKGM", "TAPU VE KADASTRO", "GAYRİMENKUL",
            "BAĞIMSIZ BÖLÜM", "ARSA PAYI",
        ],
        "min_hits": 3,
    },
    "transcript_file": {
        "name": "Transkript / Not Dökümü",
        "required_any": ["TRANSKRİPT", "NOT DÖKÜM", "GNO", "GPA", "GRADE", "DERS KODU", "SINAV NOTU"],
        "keywords": [
            "TRANSKRİPT", "NOT DÖKÜM", "GNO", "DÖNEM", "DERS KODU",
            "GPA", "GRADE", "ORTALAMA", "KREDİ", "SINAV NOTU",
            "ÜNİVERSİTE", "FAKÜLTE", "BÖLÜM",
        ],
        "min_hits": 4,
    },
    "income_file": {
        "name": "Gelir / Maaş Belgesi",
        "required_any": ["BORDRO", "MAAŞ BORDROSU", "SGK", "NET ÜCRET", "BRÜT ÜCRET", "GELİR VERGİSİ", "AYLIK ÜCRETİ"],
        "keywords": [
            "BORDRO", "MAAŞ", "SGK", "NET ÜCRET", "BRÜT", "GELİR VERGİSİ",
            "AYLIK ÜCRETİ", "SOSYAL GÜVENLİK", "PRİM", "KESİNTİ",
            "ÖDEME TUTARI", "ÇALIŞAN",
        ],
        "min_hits": 3,
    },
    "student_certificate": {
        "name": "Öğrenci Belgesi",
        "required_any": ["ÖĞRENCİ BELGESİ", "ÖĞRENCİ NUMARASI", "AKTİF ÖĞRENCİ", "ÖĞRENCİ İŞLERİ", "ÖĞRENCININ"],
        "keywords": [
            "ÖĞRENCİ BELGESİ", "ÖĞRENCİ", "KAYITLI", "ÜNİVERSİTE",
            "BÖLÜM", "SINIF", "ÖĞRENCİ NUMARASI", "FAKÜLTE",
            "AKTİF ÖĞRENCİ", "ÖĞRENCİ İŞLERİ",
        ],
        "min_hits": 3,
    },
    "family_registry": {
        "name": "Nüfus / Aile Kayıt Örneği",
        "required_any": ["NÜFUS", "VUKUATLI", "NÜFUS MÜDÜRLÜĞÜ", "MERNİS", "KÜTÜKLERİ", "AİLE KÜTÜKLERİ"],
        "keywords": [
            "NÜFUS", "AİLE", "KÜTÜKLERİ", "VUKUATLI", "NÜFUS MÜDÜRLÜĞÜ",
            "TC KİMLİK", "DOĞUM YERİ", "ANA ADI", "BABA ADI",
            "MERNİS", "E-DEVLET",
        ],
        "min_hits": 3,
    },
    "disability_report": {
        "name": "Sağlık / Engel Raporu",
        "required_any": ["SAĞLIK KURULU", "ENGELLİLİK", "HEYET RAPORU", "ENGELLİLİK ORANI", "SAĞLIK KURULU RAPORU"],
        "keywords": [
            "RAPOR", "SAĞLIK KURULU", "ENGELLİLİK", "HASTANE",
            "HEYET RAPORU", "TANI", "HASTALIK", "ENGELLİLİK ORANI",
            "SAĞLIK KURUMU", "DOKTOR", "HEKİM",
        ],
        "min_hits": 3,
    },
}


def validate_document(file_path: str, expected_doc_id: str) -> dict:
    """
    Strateji:
      1. pdfplumber ile metin çıkar → yeterli metin varsa keyword eşleştir
      2. Metin yoksa (fotoğraf PDF) → Claude Vision ile görsel analiz
      3. Vision yanıt vermezse → uyarıyla kabul et (bloke etme)
    """
    from backend.claude_vision import analyze_car, analyze_house, analyze_generic

    sig = DOC_SIGNATURES.get(expected_doc_id)
    if not sig:
        return {"valid": True, "message": "Belge alındı.", "vision_unavailable": False}

    # 1. Metin tabanlı kontrol (dijital PDF'ler için)
    text = extract_text(file_path)
    if text and len(text.strip()) >= 80:
        text_upper = text.upper()
        required_any = sig.get("required_any", [])
        has_anchor = not required_any or any(kw in text_upper for kw in required_any)
        hits = sum(1 for kw in sig["keywords"] if kw in text_upper)
        valid = has_anchor and hits >= sig["min_hits"]

        if valid:
            return {"valid": True, "message": f"✅ Geçerli {sig['name']} tespit edildi.",
                    "confidence": round(hits / len(sig["keywords"]), 2), "hits": hits}

        # Keyword eşleşmedi ama metin var → hangi belge olduğunu bul
        best_other = None
        for doc_id, other_sig in DOC_SIGNATURES.items():
            if doc_id == expected_doc_id:
                continue
            if sum(1 for kw in other_sig["keywords"] if kw in text_upper) >= other_sig["min_hits"]:
                best_other = other_sig["name"]
                break

        msg = (f"❌ Yüklenen dosya '{best_other}' gibi görünüyor. Lütfen geçerli bir {sig['name']} yükleyin."
               if best_other else f"❌ Bu belgenin {sig['name']} olduğu doğrulanamadı.")
        return {"valid": False, "message": msg, "confidence": 0.0, "hits": hits}

    # 2. Metin yok → Claude Vision
    try:
        if expected_doc_id == "car_file":
            result = analyze_car(file_path)
        elif expected_doc_id == "house_file":
            result = analyze_house(file_path)
        else:
            result = analyze_generic(file_path, expected_doc_id)

        if result is None:
            # Vision kullanılamadı → uyarıyla kabul et
            return {
                "valid": True,
                "message": "⚠️ Görsel doğrulama yapılamadı. Belge kabul edildi, manuel incelemeye alınacak.",
                "vision_unavailable": True,
            }

        return {
            "valid": result["valid"],
            "message": result["message"],
            "confidence": result.get("confidence", 0.5),
            "hits": 0,
            "vision_used": True,
            "vision_unavailable": False,
            # Araç/ev için çıkarılan alanlar (apply endpoint'i kullanır)
            **{k: result[k] for k in ("marka","model","yil","plaka","yakit","hasar",
                                       "estimated_value_tl","il","ilce","yuzolcumu",
                                       "price_per_m2","reasoning") if k in result},
        }

    except Exception as e:
        return {
            "valid": True,
            "message": f"⚠️ Doğrulama hatası ({str(e)[:60]}). Belge manuel incelemeye alınacak.",
            "vision_unavailable": True,
        }


def extract_text(file_path: str) -> str:
    """
    PDF'ten seçilebilir metin katmanını çıkar (pdfplumber).
    Fotoğraf PDF'leri için boş string döner — caller Claude Vision'a yönlendirir.
    Tesseract Render'da yüklü olmadığı için OCR denemesi yok.
    """
    ext = os.path.splitext(file_path)[1].lower()
    if ext != ".pdf":
        return ""
    try:
        import pdfplumber
        text = ""
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                t = page.extract_text()
                if t:
                    text += t + "\n"
        return text
    except Exception:
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
        "raw_text": text[:2000] if text else "",   # Claude'a verilecek ham metin
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
        "raw_text": text[:2000] if text else "",   # Claude'a verilecek ham metin
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
