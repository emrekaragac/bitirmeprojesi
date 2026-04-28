"""
PSDS — Parametrik Skorlama Motoru

Her sorunun ağırlığı (weight) ve her cevabın puanı (answer_scores)
burs veren tarafından yapılandırılır.

Formül:
  total = Σ (question.weight / 100) × answer_scores[submitted_answer]
"""


def compute_parametric_score(form_data: dict, questions: list) -> dict:
    """
    questions: scholarship config içindeki sorular listesi
               Her soruda: id, label, type, weight, answer_scores
    form_data: adayın gönderdiği form verileri
    """
    total = 0.0
    breakdown = {}
    reasons = []

    weighted_questions = [q for q in questions if q.get("weight", 0) > 0]

    if not weighted_questions:
        return {
            "total_score": 0,
            "priority": "Low Priority",
            "decision": "Rejected",
            "reasons": ["No weighted questions configured."],
            "breakdown": {},
        }

    for q in weighted_questions:
        q_id          = q.get("id", "")
        label         = q.get("label", q_id)
        weight        = float(q.get("weight", 0))
        answer_scores = q.get("answer_scores", {})
        q_type        = q.get("type", "text")

        raw_answer = form_data.get(q_id, "")
        answer_key = str(raw_answer).strip().lower() if raw_answer is not None else ""

        # Score lookup — try direct match, then case-insensitive
        score = 0.0
        if answer_key in answer_scores:
            score = float(answer_scores[answer_key])
        else:
            for k, v in answer_scores.items():
                if k.lower() == answer_key:
                    score = float(v)
                    break

        # Number type: range scoring
        if q_type == "number" and answer_scores:
            try:
                num_val = float(str(raw_answer).replace(",", "."))
                score = _range_score(num_val, answer_scores)
            except Exception:
                score = 0.0

        # Araç değeri bazlı özel skor — has_car=yes ise car value'ya göre ayarla
        if q_id == "has_car" and answer_key == "yes":
            car_val = _safe_float(form_data.get("estimated_car_value"))
            if car_val is not None:
                # "no" cevabının skoru maksimum kabul et
                no_score = float(answer_scores.get("no", 100))
                score = _car_value_score(car_val, no_score)

        weighted_points = (weight / 100.0) * score
        total += weighted_points

        breakdown[label] = {
            "weight": weight,
            "answer": str(raw_answer),
            "score": round(score, 1),
            "points": round(weighted_points, 2),
        }

        if score >= 80:
            reasons.append(f"✅ {label}: strong score ({score:.0f}/100, weight {weight:.0f}%)")
        elif score >= 50:
            reasons.append(f"➡️ {label}: moderate score ({score:.0f}/100, weight {weight:.0f}%)")
        elif score > 0:
            reasons.append(f"⚠️ {label}: low score ({score:.0f}/100, weight {weight:.0f}%)")
        else:
            reasons.append(f"❌ {label}: no points (weight {weight:.0f}%)")

    total = round(min(max(total, 0), 100))

    if total >= 75:
        priority, decision = "High Priority", "Accepted"
    elif total >= 50:
        priority, decision = "Medium Priority", "Under Review"
    else:
        priority, decision = "Low Priority", "Rejected"

    return {
        "total_score": total,
        "priority": priority,
        "decision": decision,
        "reasons": reasons,
        "breakdown": breakdown,
    }


def _safe_float(val) -> float | None:
    try:
        if val is None or str(val).strip().lower() in ("", "none"):
            return None
        return float(str(val).replace(",", "."))
    except Exception:
        return None


def _car_value_score(car_value: float, max_score: float) -> float:
    """
    Araç piyasa değerine göre 0–max_score arası puan döner.
    2025-2026 Türkiye fiyat seviyeleri:
      < 700K TL   → %80 (çok eski/ucuz araç)
      700K–1.5M   → %50 (ekonomik segment)
      1.5M–3M     → %25 (orta segment)
      3M–7M       → %5  (üst segment)
      > 7M        → 0   (lüks — puan yok)
    """
    if car_value < 700_000:
        ratio = 0.80
    elif car_value < 1_500_000:
        ratio = 0.50
    elif car_value < 3_000_000:
        ratio = 0.25
    elif car_value < 7_000_000:
        ratio = 0.05
    else:
        ratio = 0.0
    return round(max_score * ratio, 1)


def _range_score(value: float, answer_scores: dict) -> float:
    """
    answer_scores formatı: {"0-2": 100, "3-4": 70, "5+": 40}
    ya da {"lte_5000": 100, "gt_40000": 5} gibi provider tanımlı etiketler.
    En yakın range'i seç.
    """
    best = 0.0
    for key, score in answer_scores.items():
        key = str(key).strip()
        try:
            if "+" in key:
                low = float(key.replace("+", "").strip())
                if value >= low:
                    best = float(score)
            elif "-" in key:
                parts = key.split("-")
                low, high = float(parts[0]), float(parts[1])
                if low <= value <= high:
                    best = float(score)
            else:
                # Exact numeric match
                if float(key) == value:
                    best = float(score)
        except Exception:
            pass
    return best
