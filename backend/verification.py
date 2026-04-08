"""
PSDS — Belge Doğrulama Modülü
1. TC Kimlik No mod-11 doğrulama
2. QR Kod okuma (pyzbar)
3. Form vs OCR cross-check + güven skoru
"""

import re
import os
from typing import Optional


# ─────────────────────────────────────────────────────────────
# 1. TC KİMLİK NO DOĞRULAMA (Mod-11 algoritması)
# ─────────────────────────────────────────────────────────────

def validate_tc_no(tc: str) -> dict:
    """
    TC Kimlik No Türk standardı:
    - 11 hane
    - İlk hane 0 olamaz
    - 1-9. hanelerin toplamının mod-10'u = 10. hane
    - (1+3+5+7+9)*7 - (2+4+6+8) mod 10 = 10. hane  (alternatif kural)
    - Tüm hanelerin toplamının mod-10'u = 11. hane
    """
    if not tc:
        return {"valid": False, "error": "TC kimlik no girilmedi"}

    tc = str(tc).strip().replace(" ", "")

    if not tc.isdigit():
        return {"valid": False, "error": "TC sadece rakam içermelidir"}

    if len(tc) != 11:
        return {"valid": False, "error": f"TC 11 hane olmalı, {len(tc)} hane girildi"}

    if tc[0] == "0":
        return {"valid": False, "error": "TC ilk hanesi 0 olamaz"}

    digits = [int(d) for d in tc]

    # Kural 1: (d1+d3+d5+d7+d9)*7 - (d2+d4+d6+d8) mod 10 = d10
    odd_sum  = digits[0] + digits[2] + digits[4] + digits[6] + digits[8]
    even_sum = digits[1] + digits[3] + digits[5] + digits[7]
    check10  = (odd_sum * 7 - even_sum) % 10
    if check10 != digits[9]:
        return {"valid": False, "error": "TC geçersiz (10. hane kontrolü başarısız)"}

    # Kural 2: İlk 10 hanenin toplamının mod-10'u = 11. hane
    check11 = sum(digits[:10]) % 10
    if check11 != digits[10]:
        return {"valid": False, "error": "TC geçersiz (11. hane kontrolü başarısız)"}

    return {"valid": True, "error": None}


# ─────────────────────────────────────────────────────────────
# 2. QR KOD OKUMA
# ─────────────────────────────────────────────────────────────

# Bilinen resmi QR URL pattern'leri
OFFICIAL_QR_PATTERNS = [
    r"tapusorgu\.tkgm\.gov\.tr",        # Tapu
    r"egm\.gov\.tr",                    # Trafik / Ruhsat
    r"edevlet\.gov\.tr",                # e-Devlet
    r"turkiye\.gov\.tr",                # e-Devlet yeni
    r"meb\.gov\.tr",                    # MEB belgeleri
    r"yok\.gov\.tr",                    # YÖK transkript
    r"sgk\.gov\.tr",                    # SGK
    r"nvi\.gov\.tr",                    # Nüfus müdürlüğü
    r"obs\.\w+\.edu\.tr",               # Üniversite OBS
    r"ubs\.\w+\.edu\.tr",               # Üniversite UBS
]


def scan_qr(file_path: str) -> dict:
    """
    Dosyadan QR kod okur.
    PDF → her sayfayı image'a çevirir (pdf2image varsa)
    Image → direkt pyzbar ile okur
    """
    result = {
        "found": False,
        "data": None,
        "is_official": False,
        "matched_domain": None,
        "error": None,
    }

    ext = os.path.splitext(file_path)[1].lower()

    images = []

    if ext == ".pdf":
        try:
            from pdf2image import convert_from_path
            images = convert_from_path(file_path, dpi=200, first_page=1, last_page=3)
        except ImportError:
            result["error"] = "pdf2image kurulu değil, QR tarama PDF için devre dışı"
            return result
        except Exception as e:
            result["error"] = f"PDF açılamadı: {str(e)}"
            return result
    elif ext in [".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".webp"]:
        try:
            from PIL import Image
            images = [Image.open(file_path)]
        except Exception as e:
            result["error"] = f"Görüntü açılamadı: {str(e)}"
            return result
    else:
        result["error"] = "Desteklenmeyen dosya formatı"
        return result

    try:
        from pyzbar.pyzbar import decode as qr_decode
    except ImportError:
        result["error"] = "pyzbar kurulu değil"
        return result

    for img in images:
        try:
            decoded = qr_decode(img)
            if decoded:
                qr_data = decoded[0].data.decode("utf-8", errors="ignore")
                result["found"] = True
                result["data"] = qr_data

                # Resmi domain kontrolü
                for pattern in OFFICIAL_QR_PATTERNS:
                    if re.search(pattern, qr_data, re.IGNORECASE):
                        result["is_official"] = True
                        result["matched_domain"] = re.search(pattern, qr_data, re.IGNORECASE).group()
                        break
                return result
        except Exception:
            continue

    return result


# ─────────────────────────────────────────────────────────────
# 3. CROSS-CHECK: Form Verisi vs OCR Verisi
# ─────────────────────────────────────────────────────────────

def cross_check(form_data: dict, ruhsat_data: Optional[dict], tapu_data: Optional[dict]) -> dict:
    """
    Form ile OCR verilerini karşılaştırır.
    Her uyumsuzluk için flag ekler ve güven skoru hesaplar.
    """
    flags  = []     # şüpheli durumlar
    notes  = []     # bilgi amaçlı notlar
    passed = []     # geçen kontroller

    # ── Araç kontrolleri ──────────────────────────────────────

    has_car    = form_data.get("has_car", "no")
    car_brand  = (form_data.get("car_brand") or "").strip().upper()
    car_year   = _safe_int(form_data.get("car_year"))
    car_damage = form_data.get("car_damage", "no")

    if ruhsat_data and ruhsat_data.get("ocr_success"):

        # Araç yok dedi ama ruhsat yükledi
        if has_car == "no":
            flags.append({
                "code": "CAR_CONTRADICTION",
                "severity": "high",
                "message": "Araç yok seçildi ama araç ruhsatı yüklendi.",
            })
        else:
            passed.append("Araç sahibi olduğu ruhsat ile uyumlu")

            # Marka uyumsuzluğu
            ocr_brand = (ruhsat_data.get("marka") or "").upper()
            if ocr_brand and car_brand and ocr_brand not in car_brand and car_brand not in ocr_brand:
                flags.append({
                    "code": "CAR_BRAND_MISMATCH",
                    "severity": "medium",
                    "message": f"Form markası '{car_brand}', ruhsatta '{ocr_brand}' yazıyor.",
                })
            elif ocr_brand and car_brand:
                passed.append(f"Araç markası uyumlu: {ocr_brand}")

            # Yıl uyumsuzluğu (3 yıldan fazla fark şüpheli)
            ocr_year = ruhsat_data.get("yil")
            if ocr_year and car_year and abs(ocr_year - car_year) > 3:
                flags.append({
                    "code": "CAR_YEAR_MISMATCH",
                    "severity": "medium",
                    "message": f"Form yılı {car_year}, ruhsatta {ocr_year} yazıyor.",
                })
            elif ocr_year and car_year:
                passed.append(f"Araç yılı uyumlu: {ocr_year}")

            # İsim uyumsuzluğu (ruhsatta sahip adı okunabiliyorsa)
            ocr_name  = (ruhsat_data.get("sahip_adi") or "").upper()
            form_name = f"{form_data.get('first_name','')} {form_data.get('last_name','')}".upper().strip()
            if ocr_name and form_name and len(ocr_name) > 3:
                if not _name_match(form_name, ocr_name):
                    flags.append({
                        "code": "CAR_OWNER_NAME_MISMATCH",
                        "severity": "high",
                        "message": f"Başvuran adı '{form_name}', ruhsatta '{ocr_name}' yazıyor. Araç başkasına ait olabilir.",
                    })
                else:
                    passed.append("Ruhsat sahibi adı başvuranla uyumlu")

    elif has_car == "yes" and not ruhsat_data:
        notes.append("Araç sahibi olduğu belirtildi ancak ruhsat yüklenmedi")

    # ── Konut kontrolleri ─────────────────────────────────────

    has_house     = form_data.get("has_house", "no")
    form_city     = (form_data.get("city") or "").strip().upper()
    form_sqm      = _safe_float(form_data.get("square_meters"))

    if tapu_data and tapu_data.get("ocr_success"):

        # Ev yok dedi ama tapu yükledi
        if has_house == "no":
            flags.append({
                "code": "HOUSE_CONTRADICTION",
                "severity": "high",
                "message": "Ev sahibi değil seçildi ama tapu yüklendi.",
            })
        else:
            passed.append("Ev sahibi olduğu tapu ile uyumlu")

            # Şehir uyumsuzluğu
            ocr_city = (tapu_data.get("il") or "").upper()
            if ocr_city and form_city:
                if not _city_match(form_city, ocr_city):
                    flags.append({
                        "code": "HOUSE_CITY_MISMATCH",
                        "severity": "medium",
                        "message": f"Form şehri '{form_city}', tapuda '{ocr_city}' yazıyor.",
                    })
                else:
                    passed.append(f"Mülk şehri uyumlu: {ocr_city}")

            # Alan uyumsuzluğu (20% den fazla fark şüpheli)
            ocr_sqm = tapu_data.get("yuzolcumu")
            if ocr_sqm and form_sqm and form_sqm > 0:
                diff_pct = abs(ocr_sqm - form_sqm) / form_sqm
                if diff_pct > 0.20:
                    flags.append({
                        "code": "HOUSE_AREA_MISMATCH",
                        "severity": "medium",
                        "message": f"Form m²: {form_sqm:.0f}, tapuda: {ocr_sqm:.0f} (fark: %{diff_pct*100:.0f})",
                    })
                else:
                    passed.append(f"Mülk alanı uyumlu: {ocr_sqm:.0f} m²")

            # Malik uyumsuzluğu
            ocr_malik = (tapu_data.get("malik") or "").upper()
            form_name = f"{form_data.get('first_name','')} {form_data.get('last_name','')}".upper().strip()
            if ocr_malik and form_name and len(ocr_malik) > 3:
                if not _name_match(form_name, ocr_malik):
                    flags.append({
                        "code": "HOUSE_OWNER_NAME_MISMATCH",
                        "severity": "high",
                        "message": f"Başvuran adı '{form_name}', tapuda malik '{ocr_malik}'. Mülk başkasına ait olabilir.",
                    })
                else:
                    passed.append("Tapu maliki başvuranla uyumlu")

    elif has_house == "yes" and not tapu_data:
        notes.append("Ev sahibi olduğu belirtildi ancak tapu yüklenmedi")

    # ── Gelir / Varlık tutarsızlığı (finansal mantık kontrolü) ─

    income_bracket = form_data.get("monthly_income", "")
    prop_value     = _safe_float(form_data.get("property_estimated_value"))
    car_value      = _safe_float(form_data.get("estimated_car_value"))

    if income_bracket == "under_5000":
        if prop_value and prop_value > 10_000_000:
            flags.append({
                "code": "INCOME_ASSET_CONTRADICTION",
                "severity": "medium",
                "message": f"Gelir < ₺5K beyan edildi ancak mülk değeri {prop_value:,.0f} TL — tutarsız.",
            })
        if car_value and car_value > 2_000_000:
            flags.append({
                "code": "INCOME_CAR_CONTRADICTION",
                "severity": "medium",
                "message": f"Gelir < ₺5K beyan edildi ancak araç değeri {car_value:,.0f} TL — tutarsız.",
            })

    if income_bracket == "over_40000":
        notes.append("Yüksek gelir beyan edildi — otomatik öncelik düşük")

    # ── Güven skoru hesapla ───────────────────────────────────

    high_flags   = [f for f in flags if f["severity"] == "high"]
    medium_flags = [f for f in flags if f["severity"] == "medium"]

    trust_score = 100
    trust_score -= len(high_flags)   * 30
    trust_score -= len(medium_flags) * 10
    trust_score += len(passed)       * 5
    trust_score = max(0, min(trust_score, 100))

    if trust_score >= 80:
        trust_level = "High"
    elif trust_score >= 50:
        trust_level = "Medium"
    else:
        trust_level = "Low — Manual Review Required"

    needs_review = trust_score < 70 or len(high_flags) > 0

    return {
        "trust_score":   trust_score,
        "trust_level":   trust_level,
        "needs_review":  needs_review,
        "flags":         flags,
        "notes":         notes,
        "passed_checks": passed,
        "flag_count":    len(flags),
        "high_flag_count": len(high_flags),
    }


# ─────────────────────────────────────────────────────────────
# Yardımcı Fonksiyonlar
# ─────────────────────────────────────────────────────────────

def _safe_int(val) -> int:
    try:
        return int(float(str(val).replace(",", ".")))
    except Exception:
        return 0


def _safe_float(val) -> Optional[float]:
    try:
        if val is None or val == "":
            return None
        return float(str(val).replace(",", "."))
    except Exception:
        return None


def _name_match(name1: str, name2: str) -> bool:
    """İki ismin en az bir kelimesi örtüşüyor mu?"""
    words1 = set(name1.upper().split())
    words2 = set(name2.upper().split())
    # 3 karakterden kısa kelimeleri çıkar (AŞ, VE gibi)
    words1 = {w for w in words1 if len(w) >= 3}
    words2 = {w for w in words2 if len(w) >= 3}
    return bool(words1 & words2)


def _city_match(city1: str, city2: str) -> bool:
    """İstanbul / Istanbul gibi varyasyonları tolere et"""
    normalize_map = {
        "İSTANBUL": "ISTANBUL",
        "İZMİR": "IZMIR",
        "GAZİANTEP": "GAZIANTEP",
        "KAYSERİ": "KAYSERI",
        "MERSİN": "MERSIN",
        "ESKİŞEHİR": "ESKISEHIR",
        "DİYARBAKIR": "DIYARBAKIR",
        "KOCAELİ": "KOCAELI",
    }
    c1 = normalize_map.get(city1.upper(), city1.upper())
    c2 = normalize_map.get(city2.upper(), city2.upper())
    return c1 in c2 or c2 in c1
