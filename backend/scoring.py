"""
Burs Karar Destek Sistemi - Skorlama Motoru
0-100 arasi puan: 100 = en cok ihtiyac sahibi (en kotu maddi durum)

Varlik degerlendirmesi: Fiyat arttikca puan dususu artar.
Ev veya araba sahibi olmak puani onemli olcude dusurebilir.
"""


def compute_scores(form_data: dict) -> dict:
    score = 0
    reasons = []
    breakdown = {}

    # ─────────────────────────────────────────────
    # 1. Aylik Gelir (max 35 puan) — en kritik faktor
    # ─────────────────────────────────────────────
    monthly_income = form_data.get("monthly_income", "")
    family_size = _safe_int(form_data.get("family_size", 0))

    income_score = _income_score(monthly_income, family_size)
    score += income_score
    breakdown["income"] = income_score
    if income_score >= 28:
        reasons.append("Very low family income — highest financial need")
    elif income_score >= 20:
        reasons.append("Low family income")
    elif income_score >= 12:
        reasons.append("Moderate family income")
    elif income_score > 0:
        reasons.append("Above-average family income — lower financial need")

    # ─────────────────────────────────────────────
    # 2. Konut Durumu (aralik: -15 ile +20 puan)
    #    2025 Turkiye piyasa fiyatlarina gore guncel esikler.
    #    Pahali ev sahipligi sert negatif puan getirir.
    # ─────────────────────────────────────────────
    has_house = form_data.get("has_house", "no")
    property_value = _safe_float(form_data.get("property_estimated_value"))
    is_renting = form_data.get("is_renting", "no")
    monthly_rent = _safe_float(form_data.get("monthly_rent", 0))

    if has_house == "no":
        if is_renting == "yes":
            housing_score = 20
            reasons.append("No house ownership — currently renting")
        else:
            housing_score = 14
            reasons.append("No house ownership")
    else:
        if property_value is not None:
            if property_value < 3_000_000:
                # Kucuk sehir / eski yapı — cok dusuk deger
                housing_score = 8
                reasons.append("Low-value property (< 3M TL)")
            elif property_value < 8_000_000:
                # Orta buyukluk sehir standart konut
                housing_score = 2
                reasons.append("Moderate-value property (3-8M TL)")
            elif property_value < 20_000_000:
                # Buyuk sehir / iyi semt
                housing_score = -5
                reasons.append("High-value property (8-20M TL) — asset deduction applied")
            elif property_value < 40_000_000:
                # Istanbul / Ankara premium
                housing_score = -10
                reasons.append("Premium property (20-40M TL) — significant asset deduction")
            else:
                # Luks / çok degerli mulk
                housing_score = -15
                reasons.append("Luxury property (> 40M TL) — major asset deduction")
        else:
            # Deger bilinmiyor — orta ihtiyatli puan
            housing_score = 4
            reasons.append("House ownership — value not determined")

    score += housing_score
    breakdown["housing"] = housing_score

    # Kira yuku bonusu (max 5 puan)
    if is_renting == "yes" and monthly_rent and monthly_rent > 0:
        rent_score = min(5, int(monthly_rent / 8_000))
        score += rent_score
        breakdown["rent_burden"] = rent_score
        if rent_score > 0:
            reasons.append("Monthly rent burden: {:,} TL".format(int(monthly_rent)))
    else:
        breakdown["rent_burden"] = 0

    # ─────────────────────────────────────────────
    # 3. Arac Durumu (aralik: -10 ile +15 puan)
    #    2025 Turkiye otomobil piyasasina gore guncel esikler.
    #    Lüks / pahali arac sahipligi ciddi kesinti getirir.
    # ─────────────────────────────────────────────
    has_car = form_data.get("has_car", "no")
    car_value = _safe_float(form_data.get("estimated_car_value"))

    if has_car == "no":
        car_score = 15
        reasons.append("No vehicle ownership")
    else:
        if car_value is not None:
            if car_value < 500_000:
                # Cok eski / hurda siniri arac
                car_score = 8
                reasons.append("Old/very low-value vehicle (< 500K TL)")
            elif car_value < 1_500_000:
                # Normal ikinci el arac
                car_score = 3
                reasons.append("Standard used vehicle (500K-1.5M TL)")
            elif car_value < 3_000_000:
                # Yeni / gorece pahali arac
                car_score = -3
                reasons.append("Expensive vehicle (1.5M-3M TL) — asset deduction applied")
            else:
                # Luks / spor arac
                car_score = -10
                reasons.append("Luxury/sports vehicle (> 3M TL) — major asset deduction")
        else:
            # Deger bilinmiyor — ihtiyatli orta puan
            car_score = 2
            reasons.append("Vehicle ownership — value not determined")

    score += car_score
    breakdown["vehicle"] = car_score

    # ─────────────────────────────────────────────
    # 4. Aile Durumu (max 28 puan)
    # ─────────────────────────────────────────────
    family_score = 0

    if form_data.get("parents_divorced", "no") == "yes":
        family_score += 5
        reasons.append("Parents are divorced")

    if form_data.get("father_working", "yes") == "no":
        family_score += 8
        reasons.append("Father is not working")

    if form_data.get("mother_working", "yes") == "no":
        family_score += 5
        reasons.append("Mother is not working")

    if form_data.get("everyone_healthy", "yes") == "no":
        family_score += 8
        reasons.append("Chronic illness / health issue in the family")

    siblings = _safe_int(form_data.get("siblings_count", 0))
    sibling_score = _sibling_score(siblings)
    family_score += sibling_score
    if sibling_score > 0:
        reasons.append("{} sibling(s) — larger family burden".format(siblings))

    score += family_score
    breakdown["family_situation"] = family_score

    # ─────────────────────────────────────────────
    # 5. Cinsiyet Onceligi (max 5 puan)
    # ─────────────────────────────────────────────
    gender = form_data.get("gender", "")
    if gender.lower() in ["female", "kadin"]:
        score += 5
        breakdown["gender"] = 5
        reasons.append("Female applicant — gender priority applied")
    else:
        breakdown["gender"] = 0

    # ─────────────────────────────────────────────
    # 6. Baska Burs / Part-Time (kesinti)
    # ─────────────────────────────────────────────
    if form_data.get("other_scholarship", "no") == "yes":
        score -= 5
        breakdown["other_scholarship"] = -5
        reasons.append("Already receiving another scholarship — deduction applied")
    else:
        breakdown["other_scholarship"] = 0

    if form_data.get("works_part_time", "no") == "yes":
        score -= 3
        breakdown["part_time_work"] = -3
        reasons.append("Part-time employment — slight deduction")
    else:
        breakdown["part_time_work"] = 0

    # Skoru 0-100 arasina kisitla
    score = max(0, min(score, 100))

    # Oncelik siniflandirmasi
    if score >= 75:
        priority = "High Priority"
        decision = "Accepted"
    elif score >= 50:
        priority = "Medium Priority"
        decision = "Under Review"
    else:
        priority = "Low Priority"
        decision = "Rejected"

    return {
        "total_score": score,
        "priority": priority,
        "decision": decision,
        "reasons": reasons,
        "breakdown": breakdown,
    }


# ─── Yardimci Fonksiyonlar ────────────────────────────────────

def _safe_float(val):
    try:
        if val is None or val == "" or str(val).lower() == "none":
            return None
        return float(val)
    except Exception:
        return None


def _safe_int(val):
    try:
        if val is None or val == "":
            return 0
        return int(float(val))
    except Exception:
        return 0


def _income_score(monthly_income_bracket, family_size):
    # 2025 asgari ücret: ~22.104 TL net
    bracket_mid = {
        # Eski anahtarlar — geriye dönük uyumluluk
        "under_5000":   10_000,
        "5000_10000":   15_000,
        "10000_20000":  20_000,
        "20000_40000":  30_000,
        "over_40000":   60_000,
        # Yeni anahtarlar
        "under_22000":   15_000,
        "22000_40000":   30_000,
        "40000_75000":   55_000,
        "75000_150000": 110_000,
        "over_150000":  200_000,
    }

    if not monthly_income_bracket or monthly_income_bracket not in bracket_mid:
        return 14  # bilinmiyor → orta puan

    mid = bracket_mid[monthly_income_bracket]
    size = max(1, family_size)
    per_person = mid / size

    # Kişi başı aylık gelir eşikleri (2025 fiyat seviyesi)
    if per_person < 10_000:
        return 35
    elif per_person < 18_000:
        return 28
    elif per_person < 30_000:
        return 18
    elif per_person < 55_000:
        return 8
    else:
        return 2


def _sibling_score(count):
    if count == 0:
        return 0
    elif count == 1:
        return 2
    elif count == 2:
        return 4
    elif count == 3:
        return 6
    else:
        return 8
