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
        "required_any": [
            # Bordro
            "BORDRO", "MAAŞ BORDROSU", "SGK", "NET ÜCRET", "BRÜT ÜCRET", "GELİR VERGİSİ",
            # Hesap ekstresi
            "HESAP HAREKETLERİ", "MAAŞ ÖDEMESİ",
        ],
        "keywords": [
            "BORDRO", "MAAŞ", "SGK", "NET ÜCRET", "BRÜT", "GELİR VERGİSİ",
            "AYLIK ÜCRETİ", "SOSYAL GÜVENLİK", "PRİM", "KESİNTİ",
            # Hesap ekstresi ek keyword'ler
            "HESAP HAREKETLERİ", "BAKIYE", "IBAN", "MAAŞ ÖDEMESİ",
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
    from backend.claude_vision import analyze_car, analyze_house, analyze_generic, analyze_transcript, analyze_income, analyze_health_report

    sig = DOC_SIGNATURES.get(expected_doc_id)
    if not sig:
        return {"valid": True, "message": "Belge alındı.", "vision_unavailable": False}

    def _tu(s: str) -> str:
        # Python upper(): 'i'→'I' (ASCII), 'İ' stays 'İ'. Normalize both to I.
        return s.upper().replace("İ", "I")  # İ → I

    # 1. Metin tabanlı kontrol (dijital PDF'ler için)
    text = extract_text(file_path)
    if text and len(text.strip()) >= 80:
        text_upper = _tu(text)
        required_any = sig.get("required_any", [])
        has_anchor = not required_any or any(_tu(kw) in text_upper for kw in required_any)
        hits = sum(1 for kw in sig["keywords"] if _tu(kw) in text_upper)
        valid = has_anchor and hits >= sig["min_hits"]

        if valid:
            extra: dict = {}
            if expected_doc_id == "transcript_file":
                pt = parse_transcript(file_path)
                extra = {k: pt[k] for k in ("gno", "sistem", "universite", "bolum", "ogrenci_adi") if pt.get(k) is not None}
            elif expected_doc_id == "income_file":
                pi = parse_income(file_path)
                extra = {k: pi[k] for k in ("net_aylik", "income_bracket", "kaynak") if pi.get(k) is not None}
            elif expected_doc_id == "disability_report":
                hr = analyze_health_report(file_path)
                if hr:
                    extra = {k: hr[k] for k in ("hasta_adi","tc_no","kurum","maluliyet_orani","ana_tani","icd_kodu","gecerlilik_bitis","suresi_dolmus") if hr.get(k) is not None}
                    if hr.get("suresi_dolmus"):
                        return {"valid": False, "message": "❌ Sağlık raporunun geçerlilik süresi dolmuş.", "confidence": 0.0, "hits": hits}
            elif expected_doc_id == "house_file":
                from backend.rag_valuation import _classify_property_category
                pt2 = parse_tapu(file_path)
                tapu_keys = ("il", "ilce", "mahalle", "yuzolcumu", "nitelik", "malik")
                extra = {k: pt2[k] for k in tapu_keys if pt2.get(k) is not None}
                extra["property_category"] = _classify_property_category(
                    pt2.get("tapu_turu") or "", pt2.get("nitelik") or ""
                )
            return {"valid": True, "message": f"✅ Geçerli {sig['name']} tespit edildi.",
                    "confidence": round(hits / len(sig["keywords"]), 2), "hits": hits, **extra}

        # Başka belge türü mü?
        best_other = None
        for doc_id, other_sig in DOC_SIGNATURES.items():
            if doc_id == expected_doc_id:
                continue
            if sum(1 for kw in other_sig["keywords"] if kw in text_upper) >= other_sig["min_hits"]:
                best_other = other_sig["name"]
                break

        if best_other:
            return {"valid": False,
                    "message": f"❌ Yüklenen dosya '{best_other}' gibi görünüyor. Lütfen geçerli bir {sig['name']} yükleyin.",
                    "confidence": 0.0, "hits": hits}

        # Keyword eşleşmedi ama başka belge de değil → bozuk OCR katmanı olabilir, Vision'a geç

    # 2. Metin yok veya keyword eşleşmedi → Claude Vision
    try:
        if expected_doc_id == "car_file":
            result = analyze_car(file_path)
        elif expected_doc_id == "house_file":
            result = analyze_house(file_path)
        elif expected_doc_id == "transcript_file":
            result = analyze_transcript(file_path)
        elif expected_doc_id == "income_file":
            result = analyze_income(file_path)
        elif expected_doc_id == "disability_report":
            result = analyze_health_report(file_path)
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
            **{k: result[k] for k in (
                # Araç
                "marka","model","yil","plaka","yakit","hasar","estimated_value_tl",
                # Tapu
                "il","ilce","mahalle","yuzolcumu","tapu_turu","nitelik","property_category","arsa_payi","kat","price_per_m2","reasoning",
                # Transkript
                "universite","bolum","sinif","gno","sistem","donem_sayisi","ogrenci_adi",
                # Gelir
                "net_aylik","income_bracket","kaynak",
                # Sağlık raporu
                "hasta_adi","tc_no","kurum","maluliyet_orani","ana_tani","icd_kodu","gecerlilik_bitis","suresi_dolmus",
            ) if k in result},
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


def parse_transcript(file_path: str) -> dict:
    """Transkript PDF'inden GNO ve notlama sistemini çek (text-based PDFs için)."""
    text = extract_text(file_path)
    result: dict = {
        "gno": None,
        "sistem": None,
        "universite": None,
        "bolum": None,
        "raw_text": text[:2000] if text else "",
        "ocr_success": bool(text and len(text) > 20),
    }

    if not text:
        return result

    # GNO / CGPA  — \w+ covers ı (dotless-i) in "Ortalaması"
    gno_match = re.search(
        r'(?:GNO|GENEL\s+NOT\s+ORTALAMA\w*|CGPA|GPA|GENEL\s+ORTALAMA)[:\s]*(\d+[.,]\d+)',
        text, re.IGNORECASE,
    )
    if gno_match:
        try:
            result["gno"] = float(gno_match.group(1).replace(",", "."))
        except Exception:
            pass

    # Notlama sistemi — çeşitli format kalıpları
    if (re.search(r'4[.,]00\s*\w*zerindendir', text, re.IGNORECASE)
            or re.search(r'4[`\'‘’]l[uü]k\s*not\s*sistem', text, re.IGNORECASE)
            or re.search(r'4[.,]0\s*scale', text, re.IGNORECASE)
            or re.search(r'not\s*sistem[i:]?\s*4', text, re.IGNORECASE)):
        result["sistem"] = "4"
    elif (re.search(r'100\s*\w*zerindendir', text, re.IGNORECASE)
            or re.search(r'100[`\'‘’]l[uü]k\s*not\s*sistem', text, re.IGNORECASE)
            or re.search(r'100\s*scale', text, re.IGNORECASE)):
        result["sistem"] = "100"

    # Üniversite adı — ilk birkaç satırda bulunur
    for line in text.strip().split('\n')[:8]:
        if any(kw in line.upper() for kw in ['ÜNİVERSİTE', 'UNIVERSITY', 'UNİVERSİTESİ']):
            result["universite"] = line.strip()
            break

    # Bölüm
    bolum_match = re.search(
        r'(?:BÖLÜM|BOLUM|PROGRAM|DEPARTMENT)[:\s]+([^\n]{5,60})',
        text, re.IGNORECASE,
    )
    if bolum_match:
        result["bolum"] = bolum_match.group(1).strip()

    # Öğrenci adı — birden fazla etiket formatını dene
    # Daha spesifik (etiket+iki nokta) pattern'lar önce gelir;
    # "AD SOYAD" tablo başlığı gibi belirsiz etiketler sona bırakılır.
    name_patterns = [
        r'(?:ÖĞRENCİN[İI]N\s+)?ADI?\s+SOYADI?\s*:\s*([A-ZÇĞİÖŞÜa-zçğışöşü ]{4,50})',
        r'(?:STUDENT\s+)?NAME\s*:\s*([A-ZÇĞİÖŞÜa-zçğışöşü ]{4,50})',
        r'ÖĞRENCİ\s*:\s*([A-ZÇĞİÖŞÜa-zçğışöşü ]{4,50})',
        r'AD\s+SOYAD\s*:\s*([A-ZÇĞİÖŞÜa-zçğışöşü ]{4,50})',
    ]
    # Transkript tablo başlıklarında geçen anahtar kelimeler — bunları içeren
    # capture'lar isim değil başlık/sütun metnidir, atla.
    _NON_NAME_KEYWORDS = {
        "KREDİ", "KREDI", "AKTS", "ECTS", "TÜRÜ", "TURU", "KOD", "NOT",
        "BÖLÜM", "BOLUM", "PROGRAM", "DÖNEM", "DONEM", "YIL", "SINIF",
        "TOPLAM", "ORTALAMA", "GNO", "GPA", "CGPA", "TRANSKRIPT",
    }
    for pat in name_patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            candidate = m.group(1).strip().split('\n')[0].strip()
            upper_words = {w.upper() for w in candidate.split()}
            if 3 < len(candidate) < 60 and not upper_words & _NON_NAME_KEYWORDS:
                result["ogrenci_adi"] = candidate
                break

    return result


def _parse_tr_amount(s: str) -> float:
    """'21.126,68' → 21126.68  (Türkçe binlik nokta, ondalık virgül)"""
    return float(s.replace(".", "").replace(",", "."))


def _amount_to_bracket(amount: float) -> str:
    if amount < 22_000:   return "under_22000"
    if amount < 40_000:   return "22000_40000"
    if amount < 75_000:   return "40000_75000"
    if amount < 150_000:  return "75000_150000"
    return "over_150000"


def parse_income(file_path: str) -> dict:
    """Bordro veya banka ekstresi PDF'inden aylık net geliri çıkar."""
    text = extract_text(file_path)
    result: dict = {
        "net_aylik": None,
        "income_bracket": None,
        "kaynak": None,
        "raw_text": text[:2000] if text else "",
        "ocr_success": bool(text and len(text) > 20),
    }

    if not text:
        return result

    # ── 1. BORDRO: NET ÖDENEN satırı ──────────────────────────────
    net_match = re.search(r'NET\s*ÖDENEN\s+([\d.]+,\d+)', text, re.IGNORECASE)
    if net_match:
        try:
            result["net_aylik"] = _parse_tr_amount(net_match.group(1))
            result["kaynak"] = "bordro"
        except Exception:
            pass

    # ── 2. BANKA EKSTRESİ: "Maaş" etiketli kredi satırları ───────
    if result["net_aylik"] is None:
        # Format: "<açıklama> Maaş +75.000,00 TL <bakiye>"
        all_lines = re.findall(r'([^\n]*?Maaş\s+\+([\d.]+,\d+)\s*TL)', text)
        monthly_salaries = []
        for line, amount_str in all_lines:
            if "AVANS" in line.upper():
                continue  # avans ayrı satır, aylık maaş değil
            try:
                monthly_salaries.append(_parse_tr_amount(amount_str))
            except Exception:
                pass
        if monthly_salaries:
            result["net_aylik"] = sum(monthly_salaries) / len(monthly_salaries)
            result["kaynak"] = "ekstre"

    if result["net_aylik"] is not None:
        result["income_bracket"] = _amount_to_bracket(result["net_aylik"])

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

    # Tüm 81 il — uzun isimler önce (kısmi eşleşmeyi önler)
    _PROVINCES = [
        ("AFYONKARAHISAR", "Afyonkarahisar"), ("KAHRAMANMARAŞ", "Kahramanmaraş"),
        ("KAHRAMAN MARAS", "Kahramanmaraş"), ("DİYARBAKIR", "Diyarbakır"),
        ("DIYARBAKIR", "Diyarbakır"), ("ESKİŞEHİR", "Eskişehir"),
        ("ESKISEHIR", "Eskişehir"), ("GAZİANTEP", "Gaziantep"),
        ("GAZIANTEP", "Gaziantep"), ("KAYSERİ", "Kayseri"), ("KAYSERI", "Kayseri"),
        ("KOCAELİ", "Kocaeli"), ("KOCAELI", "Kocaeli"), ("SAKARYA", "Sakarya"),
        ("İSTANBUL", "İstanbul"), ("ISTANBUL", "İstanbul"),
        ("İZMİR", "İzmir"), ("IZMIR", "İzmir"), ("ANKARA", "Ankara"),
        ("BURSA", "Bursa"), ("ANTALYA", "Antalya"), ("ADANA", "Adana"),
        ("KONYA", "Konya"), ("MERSİN", "Mersin"), ("MERSIN", "Mersin"),
        ("SAMSUN", "Samsun"), ("TRABZON", "Trabzon"), ("MALATYA", "Malatya"),
        ("BALIKESIR", "Balıkesir"), ("BALIKESİR", "Balıkesir"),
        ("MANISA", "Manisa"), ("MANİSA", "Manisa"),
        ("DENIZLI", "Denizli"), ("DENİZLİ", "Denizli"),
        ("HATAY", "Hatay"), ("MUĞLA", "Muğla"), ("MUGLA", "Muğla"),
        ("TEKIRDAĞ", "Tekirdağ"), ("TEKIRDAG", "Tekirdağ"),
        ("KÜTAHYA", "Kütahya"), ("KUTAHYA", "Kütahya"),
        ("GEBZE", "Kocaeli"),  # Gebze → Kocaeli
        ("ORDU", "Ordu"), ("ERZURUM", "Erzurum"), ("VAN", "Van"),
        ("ŞANLIURFA", "Şanlıurfa"), ("SANLIURFA", "Şanlıurfa"),
        ("ŞIRNAK", "Şırnak"), ("MARDIN", "Mardin"), ("BATMAN", "Batman"),
        ("SIIRT", "Siirt"), ("AĞRI", "Ağrı"), ("AGRI", "Ağrı"),
        ("ARDAHAN", "Ardahan"), ("IĞDIR", "Iğdır"), ("IGDIR", "Iğdır"),
        ("TUNCELI", "Tunceli"), ("BİNGÖL", "Bingöl"), ("BINGOL", "Bingöl"),
        ("MUŞ", "Muş"), ("MUS", "Muş"), ("BITLIS", "Bitlis"),
        ("HAKKARI", "Hakkari"), ("ELAZIĞ", "Elazığ"), ("ELAZIG", "Elazığ"),
        ("ADIYAMAN", "Adıyaman"), ("GAZIOSMANPASA", "İstanbul"),
        ("ÇANAKKALE", "Çanakkale"), ("CANAKKALE", "Çanakkale"),
        ("EDİRNE", "Edirne"), ("EDIRNE", "Edirne"),
        ("KIRKLARELİ", "Kırklareli"), ("KIRKLARELI", "Kırklareli"),
        ("ÇORLU", "Tekirdağ"), ("CORLU", "Tekirdağ"),
        ("ISPARTA", "Isparta"), ("BURDUR", "Burdur"),
        ("AFYON", "Afyonkarahisar"), ("KARS", "Kars"),
        ("KASTAMONU", "Kastamonu"), ("ÇORUM", "Çorum"), ("CORUM", "Çorum"),
        ("AMASYA", "Amasya"), ("TOKAT", "Tokat"), ("SİVAS", "Sivas"), ("SIVAS", "Sivas"),
        ("GİRESUN", "Giresun"), ("GIRESUN", "Giresun"),
        ("RIZE", "Rize"), ("ARTVİN", "Artvin"), ("ARTVIN", "Artvin"),
        ("GÜMÜŞHANE", "Gümüşhane"), ("BAYBURT", "Bayburt"),
        ("ERZINCAN", "Erzincan"), ("ERZİNCAN", "Erzincan"),
        ("NEVSEHIR", "Nevşehir"), ("NEVŞEHİR", "Nevşehir"),
        ("AKSARAY", "Aksaray"), ("KIRIKKALE", "Kırıkkale"),
        ("YOZGAT", "Yozgat"), ("CANKIRI", "Çankırı"), ("ÇANKIRI", "Çankırı"),
        ("BOLU", "Bolu"), ("DÜZCE", "Düzce"), ("DUZCE", "Düzce"),
        ("ZONGULDAK", "Zonguldak"), ("KARABÜK", "Karabük"), ("KARABUK", "Karabük"),
        ("BARTIN", "Bartın"), ("SINOP", "Sinop"), ("ANKARA", "Ankara"),
        ("NIGDE", "Niğde"), ("NİĞDE", "Niğde"),
        ("KARAMAN", "Karaman"), ("OSMANIYE", "Osmaniye"),
        ("KILIS", "Kilis"), ("GAZIANTEP", "Gaziantep"),
        ("AYDIN", "Aydın"), ("AYDIN", "Aydın"),
        ("USAK", "Uşak"), ("UŞAK", "Uşak"),
        ("BILECIK", "Bilecik"), ("BİLECİK", "Bilecik"),
        ("BOLU", "Bolu"), ("YALOVA", "Yalova"),
        ("KIRŞEHIR", "Kırşehir"), ("KIRŞEHİR", "Kırşehir"),
        ("ÇANKIRI", "Çankırı"),
    ]

    text_upper = text.upper()
    for keyword, display in _PROVINCES:
        if keyword in text_upper:
            result["il"] = display
            break

    # İlçe — "İlçe:" etiketinden sonra gelen kelime
    ilce_match = re.search(
        r'(?:İLÇE|ILCE|İLÇESİ)[:\s]+([A-ZÇĞİÖŞÜa-zçğışöüÇĞİÖŞÜ ]{3,30})',
        text, re.IGNORECASE
    )
    if ilce_match:
        result["ilce"] = ilce_match.group(1).strip().split('\n')[0].strip()

    # Mahalle / Bölge
    mahalle_match = re.search(
        r'(?:MAHALLE|MAHALLESİ)[:\s]+([A-ZÇĞİÖŞÜa-zçğışöüÇĞİÖŞÜ ]{3,40})',
        text, re.IGNORECASE
    )
    if mahalle_match:
        result["mahalle"] = mahalle_match.group(1).strip().split('\n')[0].strip()

    # Yüzölçümü / alan m²
    area_patterns = [
        r'(?:YÜZ\s*ÖLÇÜMÜ|YÜZÖLÇÜMÜ|YÜZÖLÇÜMü|ALAN)[:\s]*(\d+[.,]\d+)\s*(?:m[²2])?',
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

    # Nitelik (property type) — ticari tipler önce (daha spesifik)
    nitelik_map = [
        (["DÜKKAN", "DUKKAN", "DÜKKÂN"],             "Dükkan"),
        (["İŞYERİ", "ISYERI", "IS YERI"],            "İşyeri"),
        (["OFİS", "OFIS"],                            "Ofis"),
        (["MAĞAZA", "MAGAZA"],                        "Mağaza"),
        (["FABRİKA", "FABRIKA"],                      "Fabrika"),
        (["DEPO", "AMBAR"],                           "Depo"),
        (["ATÖLYE", "ATOLYE"],                        "Atölye"),
        (["TARLA"],                                   "Tarla"),
        (["ARSA"],                                    "Arsa"),
        (["BAHÇE", "BAHCE"],                          "Bahçe"),
        (["ZEYTİNLİK", "ZEYTINLIK"],                  "Zeytinlik"),
        (["VİLLA", "VILLA", "MÜSTAKIL", "MUSTAKIL"],  "Villa"),
        (["BAĞIMSIZ BÖLÜM", "BAGIMSIZ BOLUM"],        "Bağımsız Bölüm"),
        (["DAİRE", "DAIRE", "MESKEN", "APARTMAN"],    "Daire"),
        (["KONUT"],                                   "Konut"),
    ]
    for keywords, label in nitelik_map:
        if any(k in text_upper for k in keywords):
            result["nitelik"] = label
            break

    # Malik (sahip)
    malik_match = re.search(
        r'(?:MALİK|MALIK|SAHİP)[:\s]+([A-ZÇĞİÖŞÜa-zçğışöüÇĞİÖŞÜ ]{5,50})',
        text, re.IGNORECASE
    )
    if malik_match:
        result["malik"] = malik_match.group(1).strip()

    return result
