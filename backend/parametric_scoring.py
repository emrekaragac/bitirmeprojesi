"""
PSDS — Parametrik Skorlama Motoru

Her sorunun ağırlığı (weight) ve her cevabın puanı (answer_scores)
burs veren tarafından yapılandırılır.

Formül (normalize edilmiş):
  raw    = Σ (question.weight / 100) × answer_scores[submitted_answer]
  max    = Σ (question.weight / 100) × max(answer_scores.values())
  total  = round((raw / max) * 100)   → her zaman 0-100 arası sonuç

Normalizasyon sayesinde answer_scores 0-30 arasında da olsa
adayın mümkün olan en iyi profili = 100 puan alır.
"""

# GPA 4.0 skala aralıkları — 100'lük sistem için normalize ederek kullanılır
_GPA_RANGES_4 = {
    "0-2":     10,
    "2-2.99":  40,
    "3-3.49":  70,
    "3.5-3.79": 90,
    "3.8-4":   100,
}


def compute_parametric_score(form_data: dict, questions: list) -> dict:
    """
    questions: scholarship config içindeki sorular listesi
               Her soruda: id, label, type, weight, answer_scores
    form_data: adayın gönderdiği form verileri
    """
    total = 0.0
    max_possible = 0.0
    breakdown = {}
    reasons = []

    weighted_questions = [q for q in questions if q.get("weight", 0) > 0]

    if not weighted_questions:
        return {
            "total_score": 0,
            "priority": "Low Priority",
            "decision": "Rejected",
            "reasons": ["Ağırlıklı soru yapılandırılmamış."],
            "breakdown": {},
        }

    gpa_system = str(form_data.get("gpa_system", "4")).strip()

    for q in weighted_questions:
        q_id          = q.get("id", "")
        label         = q.get("label", q_id)
        weight        = float(q.get("weight", 0))
        answer_scores = q.get("answer_scores", {})
        q_type        = q.get("type", "text")

        raw_answer = form_data.get(q_id, "")
        answer_key = str(raw_answer).strip().lower() if raw_answer is not None else ""

        # ── Max possible için bu sorunun max answer_score'u ──────────
        q_max = max((float(v) for v in answer_scores.values()), default=0.0) if answer_scores else 100.0
        max_possible += (weight / 100.0) * q_max

        # ── Score hesapla ────────────────────────────────────────────
        score = 0.0

        # GPA: özel işleme (4.0 ve 100'lük skala desteği)
        if q_id == "gpa":
            score = _gpa_score(raw_answer, answer_scores, gpa_system)

        # Number type: range scoring
        elif q_type == "number" and answer_scores:
            try:
                num_val = float(str(raw_answer).replace(",", "."))
                score = _range_score(num_val, answer_scores)
            except Exception:
                score = 0.0

        # Select / yesno / text: direct key match
        else:
            if answer_key in answer_scores:
                score = float(answer_scores[answer_key])
            else:
                for k, v in answer_scores.items():
                    if str(k).lower() == answer_key:
                        score = float(v)
                        break

        weighted_points = (weight / 100.0) * score
        total += weighted_points

        breakdown[label] = {
            "weight": weight,
            "answer": str(raw_answer),
            "score": round(score, 1),
            "points": round(weighted_points, 2),
        }

        # Reason messages use score relative to q_max
        pct = (score / q_max * 100) if q_max > 0 else 0
        if pct >= 80:
            reasons.append(f"✅ {label}: güçlü cevap ({score:.0f} puan, ağırlık %{weight:.0f})")
        elif pct >= 50:
            reasons.append(f"➡️ {label}: orta cevap ({score:.0f} puan, ağırlık %{weight:.0f})")
        elif pct > 0:
            reasons.append(f"⚠️ {label}: zayıf cevap ({score:.0f} puan, ağırlık %{weight:.0f})")
        else:
            reasons.append(f"❌ {label}: puan alınamadı (ağırlık %{weight:.0f})")

    # ── Normalize: raw / max * 100 ───────────────────────────────
    if max_possible > 0:
        normalized = round((total / max_possible) * 100)
    else:
        # Tüm answer_scores sıfırsa (yanlış yapılandırma)
        normalized = 0
        reasons.insert(0, "⚠️ Burs yapılandırması hatalı: tüm cevap puanları sıfır.")

    normalized = max(0, min(normalized, 100))

    if normalized >= 75:
        priority, decision = "High Priority", "Accepted"
    elif normalized >= 50:
        priority, decision = "Medium Priority", "Under Review"
    else:
        priority, decision = "Low Priority", "Rejected"

    return {
        "total_score": normalized,
        "priority": priority,
        "decision": decision,
        "reasons": reasons,
        "breakdown": breakdown,
    }


# ── GPA özel işleme ──────────────────────────────────────────────────────────

def _gpa_score(raw_answer, answer_scores: dict, gpa_system: str) -> float:
    """
    GPA skorunu hesaplar. 100'lük sistemdeyse 4.0'a normalize eder.
    answer_scores hem 4.0 hem 100'lük aralıkları içerebilir.
    answer_scores boşsa varsayılan 4.0 tablosu kullanılır.
    """
    try:
        gpa_val = float(str(raw_answer).replace(",", "."))
    except Exception:
        return 0.0

    if gpa_val <= 0:
        return 0.0

    # 100'lük sistemden 4.0'a çevir (range tablosu 4.0 skalası için)
    if gpa_system == "100":
        gpa_val = gpa_val / 25.0  # 0-100 → 0-4

    # Kullanılacak aralık tablosu
    ranges = answer_scores if answer_scores else _GPA_RANGES_4
    return _range_score(gpa_val, ranges)


# ── Yardımcı: Aralık Puanlaması ─────────────────────────────────────────────

def _range_score(value: float, answer_scores: dict) -> float:
    """
    answer_scores formatı: {"0-2": 100, "3-4": 70, "5+": 40}
    ya da {"lte_5000": 100, "gt_40000": 5} gibi provider tanımlı etiketler.
    En iyi (en yüksek) eşleşen range puanı döner.
    """
    best = 0.0
    matched = False
    for key, score in answer_scores.items():
        key_s = str(key).strip()
        try:
            if "+" in key_s:
                low = float(key_s.replace("+", "").strip())
                if value >= low:
                    candidate = float(score)
                    if not matched or candidate > best:
                        best = candidate
                    matched = True
            elif "-" in key_s:
                parts = key_s.split("-")
                low, high = float(parts[0]), float(parts[1])
                if low <= value <= high:
                    candidate = float(score)
                    if not matched or candidate > best:
                        best = candidate
                    matched = True
            else:
                # Exact numeric match
                if abs(float(key_s) - value) < 1e-9:
                    candidate = float(score)
                    if not matched or candidate > best:
                        best = candidate
                    matched = True
        except Exception:
            pass
    return best
