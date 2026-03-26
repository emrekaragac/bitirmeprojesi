"""
Burs Karar Destek Sistemi - Skorlama Motoru
0-100 arasi puan: 100 = en cok ihtiyac sahibi (en kotu maddi durum)
"""


def compute_scores(form_data: dict) -> dict:
    score = 0
    reasons = []
    breakdown = {}

    # ─────────────────────────────────────────────
    # 1. Aylik Gelir (max 30 puan) — en kritik faktor
    # ─────────────────────────────────────────────
    monthly_income = form_data.get("monthly_income", "")
    family_size = _safe_int(form_data.get("family_size", 0))

    income_score = _income_score(monthly_income, family_size)
    score += income_score
    breakdown["income"] = income_score
    if income_score >= 25:
        reasons.append("Very low family income — highest financial need")
    elif income_score >= 18:
        reasons.append("Low family income")
    elif income_score >= 10:
        reasons.append("Moderate family income")
    elif income_score > 0:
        reasons.append("Above-average family income — lower financial need")

    # ─────────────────────────────────────────────
    # 2. Konut Durumu (max 15 puan)
    # ─────────────────────────────────────────────
    has_house = form_data.get("has_house", "no")
    property_value = _safe_float(form_data.get("property_estimated_value"))
    is_renting = form_data.get("is_renting", "no")
    monthly_rent = _safe_float(form_data.get("monthly_rent", 0))

    if has_house == "no":
        if is_renting == "yes":
            housing_score = 15
            reasons.append("No house ownership — currently renting")
        else:
            housing_score = 10
            reasons.append("No house ownership")
    else:
        if property_value is not None:
            if property_value < 2_000_000:
                housing_score = 8
                reasons.append("Low-value property (< 2M TL)")
            elif property_value < 5_000_000:
                housing_score = 5
                reasons.append("Moderate-value property (2-5M TL)")
            elif property_value < 10_000_000:
                housing_score = 2
                reasons.append("High-value property (5-10M TL)")
            else:
                housing_score = 0
                reasons.append("Very high-value property (> 10M TL) — lower priority")
        else:
            housing_score = 5

    score += housing_score
    breakdown["housing"] = housing_score

    # Kira yuku bonus
    if is_renting == "yes" and monthly_rent and monthly_rent > 0:
        rent_score = min(5, int(monthly_rent / 5000))
        score += rent_score
        breakdown["rent_burden"] = rent_score
        if rent_score > 0:
            reasons.append("Monthly rent burden: {:,} TL".format(int(monthly_rent)))

    # ─────────────────────────────────────────────
    # 3. Arac Durumu (max 10 puan)
    # ─────────────────────────────────────────────
    has_car = form_data.get("has_car", "no")
    car_value = _safe_float(form_data.get("estimated_car_value"))

    if has_car == "no":
        car_score = 10
        reasons.append("No vehicle ownership")
    else:
        if car_value is not None:
            if car_value < 300_000:
                car_score = 7
                reasons.append("Old/low-value vehicle (< 300K TL)")
            elif car_value < 800_000:
                car_score = 4
                reasons.append("Mid-value vehicle (300K-800K TL)")
            elif car_value < 2_000_000:
                car_score = 1
                reasons.append("High-value vehicle (800K-2M TL)")
            else:
                car_score = -3
                reasons.append("Luxury vehicle (> 2M TL) — lower priority")
        else:
            car_score = 3

    score += car_score
    breakdown["vehicle"] = car_score

    # ─────────────────────────────────────────────
    # 4. Aile Durumu (max 28 puan)
    # ─────────────────────────────────────────────
    family_score = 0

    if form_data.get("parents_divorced", "no") == "yes":
        family_score += 6
        reasons.append("Parents are divorced")

    if form_data.get("father_working", "yes") == "no":
        family_score += 8
        reasons.append("Father is not working")

    if form_data.get("mother_working", "yes") == "no":
        family_score += 5
        reasons.append("Mother is not working")

    if form_data.get("everyone_healthy", "yes") == "no":
        family_score += 7
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

    # Skoru 0-100 arasin a kisitla
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
    bracket_mid = {
        "under_5000": 4_000,
        "5000_10000": 7_500,
        "10000_20000": 15_000,
        "20000_40000": 30_000,
        "over_40000": 50_000,
    }

    if not monthly_income_bracket or monthly_income_bracket not in bracket_mid:
        return 12  # bilinmiyor -> orta puan

    mid = bracket_mid[monthly_income_bracket]
    size = max(1, family_size)
    per_person = mid / size

    if per_person < 3_000:
        return 30
    elif per_person < 5_000:
        return 24
    elif per_person < 8_000:
        return 16
    elif per_person < 15_000:
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
