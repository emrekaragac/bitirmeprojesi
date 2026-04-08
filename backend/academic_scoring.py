"""
Akademik Skorlama Motoru
GPA ve akademik başarı kriterlerine göre 0-100 puan
"""


def compute_academic_score(form_data: dict) -> dict:
    score = 0
    reasons = []
    breakdown = {}

    # GPA (max 50 puan)
    gpa_raw = form_data.get("gpa", "")
    gpa_system = form_data.get("gpa_system", "4")  # "4" or "100"
    gpa_score = _gpa_score(gpa_raw, gpa_system)
    score += gpa_score
    breakdown["gpa"] = gpa_score
    if gpa_score >= 45:
        reasons.append("Excellent academic performance (GPA ≥ 3.5 / 4.0)")
    elif gpa_score >= 35:
        reasons.append("Good academic performance")
    elif gpa_score >= 20:
        reasons.append("Average academic performance")
    elif gpa_score > 0:
        reasons.append("Below-average academic performance")

    # Yıl / Sınıf (max 10 puan) — yüksek sınıf biraz bonus
    grade = form_data.get("grade", "")
    grade_score = _grade_score(grade)
    score += grade_score
    breakdown["grade_year"] = grade_score
    if grade_score > 0:
        reasons.append("Advanced year student")

    # Proje / Araştırma (max 15 puan)
    if form_data.get("has_research", "no") == "yes":
        score += 15
        breakdown["research"] = 15
        reasons.append("Active in research / academic project")
    else:
        breakdown["research"] = 0

    # Ödül / Sertifika (max 10 puan)
    if form_data.get("has_award", "no") == "yes":
        score += 10
        breakdown["award"] = 10
        reasons.append("Has academic award or certificate")
    else:
        breakdown["award"] = 0

    # Yabancı dil (max 10 puan)
    lang_score = _language_score(form_data.get("language_level", ""))
    score += lang_score
    breakdown["language"] = lang_score
    if lang_score > 0:
        reasons.append("Foreign language proficiency")

    # Aktivite / Kulüp (max 5 puan)
    if form_data.get("has_activity", "no") == "yes":
        score += 5
        breakdown["activity"] = 5
        reasons.append("Active in student clubs / social activities")
    else:
        breakdown["activity"] = 0

    score = max(0, min(score, 100))

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


def _gpa_score(gpa_raw, system):
    try:
        gpa = float(str(gpa_raw).replace(",", "."))
    except Exception:
        return 0

    if system == "100":
        gpa = gpa / 25  # normalize to 4.0 scale

    if gpa >= 3.75:
        return 50
    elif gpa >= 3.50:
        return 45
    elif gpa >= 3.00:
        return 36
    elif gpa >= 2.50:
        return 25
    elif gpa >= 2.00:
        return 15
    else:
        return 5


def _grade_score(grade: str) -> int:
    grade_map = {
        "1": 0, "freshman": 0,
        "2": 3, "sophomore": 3,
        "3": 6, "junior": 6,
        "4": 10, "senior": 10,
        "5": 10, "graduate": 10,
    }
    return grade_map.get(str(grade).strip().lower(), 0)


def _language_score(level: str) -> int:
    level_map = {
        "none": 0, "": 0,
        "a1": 2, "a2": 3,
        "b1": 5, "b2": 7,
        "c1": 9, "c2": 10,
        "native": 10,
    }
    return level_map.get(str(level).strip().lower(), 0)
