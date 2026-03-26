import os
import re
from typing import Optional


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
