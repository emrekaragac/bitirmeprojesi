from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from datetime import datetime


def _fmt_currency(val):
    try:
        return f"{float(val):,.0f} TL"
    except Exception:
        return str(val) if val else "—"


def _yn(val):
    if val in ("yes", "Yes", True):  return "Yes"
    if val in ("no",  "No",  False): return "No"
    return str(val) if val else "—"


INCOME_LABELS = {
    "under_5000":    "Under ₺5,000",
    "5000_10000":    "₺5,000 – ₺10,000",
    "10000_20000":   "₺10,000 – ₺20,000",
    "20000_40000":   "₺20,000 – ₺40,000",
    "over_40000":    "Over ₺40,000",
}

BREAKDOWN_LABELS = {
    "income":           "Monthly Income",
    "housing":          "Housing Situation",
    "rent_burden":      "Rent Burden",
    "vehicle":          "Vehicle",
    "family_situation": "Family Situation",
    "gender":           "Gender Priority",
    "other_scholarship":"Other Scholarship",
    "part_time_work":   "Part-Time Work",
}


def generate_report(output_path: str, form_data: dict, scores: dict):
    W, H = A4
    c = canvas.Canvas(output_path, pagesize=A4)

    # ── HEADER ──────────────────────────────────────────────────────────────
    c.setFillColor(colors.HexColor("#4f46e5"))
    c.rect(0, H - 90, W, 90, fill=True, stroke=False)

    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 22)
    c.drawString(40, H - 45, "BursIQ")
    c.setFont("Helvetica", 10)
    c.drawString(40, H - 65, "Scholarship Intelligence System — Financial Need Report")

    c.setFont("Helvetica", 9)
    c.drawRightString(W - 40, H - 50, datetime.utcnow().strftime("%d %B %Y, %H:%M UTC"))

    # ── SCORE BANNER ────────────────────────────────────────────────────────
    score    = scores.get("total_score", 0)
    priority = scores.get("priority", "—")
    decision = scores.get("decision", "—")

    # Decision color
    dec_color = {
        "Accepted":     colors.HexColor("#16a34a"),
        "Under Review": colors.HexColor("#d97706"),
        "Rejected":     colors.HexColor("#dc2626"),
    }.get(decision, colors.grey)

    banner_y = H - 160
    c.setFillColor(colors.HexColor("#f8fafc"))
    c.roundRect(30, banner_y, W - 60, 55, 8, fill=True, stroke=False)

    # Score number
    c.setFillColor(colors.HexColor("#4f46e5"))
    c.setFont("Helvetica-Bold", 34)
    c.drawString(50, banner_y + 12, str(score))
    c.setFont("Helvetica", 9)
    c.setFillColor(colors.HexColor("#94a3b8"))
    c.drawString(50, banner_y + 4, "/ 100")

    # Priority + Decision
    c.setFillColor(colors.HexColor("#1e293b"))
    c.setFont("Helvetica-Bold", 13)
    c.drawString(130, banner_y + 28, priority)
    c.setFont("Helvetica", 10)
    c.setFillColor(dec_color)
    c.drawString(130, banner_y + 12, f"Decision: {decision}")

    # Score bar
    bar_x, bar_y, bar_w, bar_h = 320, banner_y + 20, 230, 12
    c.setFillColor(colors.HexColor("#e2e8f0"))
    c.roundRect(bar_x, bar_y, bar_w, bar_h, 4, fill=True, stroke=False)
    fill_w = int(bar_w * score / 100)
    if fill_w > 0:
        bar_color = colors.HexColor("#ef4444") if score >= 75 else (
            colors.HexColor("#f59e0b") if score >= 50 else colors.HexColor("#22c55e"))
        c.setFillColor(bar_color)
        c.roundRect(bar_x, bar_y, fill_w, bar_h, 4, fill=True, stroke=False)
    c.setFillColor(colors.HexColor("#64748b"))
    c.setFont("Helvetica", 7)
    c.drawString(bar_x, bar_y - 9, "0 = No need          100 = Highest need")

    y = banner_y - 20

    # ── SECTION HELPER ──────────────────────────────────────────────────────
    def section(title, icon=""):
        nonlocal y
        if y < 120:
            c.showPage()
            y = H - 60
        c.setFillColor(colors.HexColor("#eef2ff"))
        c.rect(30, y - 4, W - 60, 20, fill=True, stroke=False)
        c.setFillColor(colors.HexColor("#4f46e5"))
        c.setFont("Helvetica-Bold", 10)
        c.drawString(38, y + 3, f"{icon}  {title}".strip())
        y -= 26

    def row(label, value, indent=0):
        nonlocal y
        if y < 60:
            c.showPage()
            y = H - 60
        c.setFillColor(colors.HexColor("#64748b"))
        c.setFont("Helvetica", 9)
        c.drawString(40 + indent, y, label)
        c.setFillColor(colors.HexColor("#1e293b"))
        c.setFont("Helvetica-Bold", 9)
        c.drawString(250, y, str(value) if value is not None else "—")
        y -= 16

    # ── PERSONAL & FAMILY ───────────────────────────────────────────────────
    section("Personal & Family Information", "👤")
    row("Gender",             form_data.get("gender", "—").capitalize())
    row("Parents divorced",   _yn(form_data.get("parents_divorced")))
    row("Father working",     form_data.get("father_working", "—").capitalize())
    row("Mother working",     form_data.get("mother_working", "—").capitalize())
    row("Everyone healthy",   _yn(form_data.get("everyone_healthy")))
    row("Number of siblings", form_data.get("siblings_count", "0"))
    row("Total family members", form_data.get("family_size", "1"))

    y -= 6
    # ── FINANCIAL ───────────────────────────────────────────────────────────
    section("Financial Situation", "💰")
    income_key = form_data.get("monthly_income", "")
    row("Monthly family income",   INCOME_LABELS.get(income_key, income_key or "—"))
    row("Currently renting",       _yn(form_data.get("is_renting")))
    if form_data.get("is_renting") == "yes":
        row("Monthly rent",        _fmt_currency(form_data.get("monthly_rent")), indent=15)
    row("Other scholarship",       _yn(form_data.get("other_scholarship")))
    row("Part-time work",          _yn(form_data.get("works_part_time")))

    y -= 6
    # ── VEHICLE ─────────────────────────────────────────────────────────────
    section("Vehicle", "🚗")
    row("Owns a vehicle",   _yn(form_data.get("has_car")))
    if form_data.get("has_car") == "yes":
        row("Brand / Model",     f"{form_data.get('car_brand','—')} {form_data.get('car_model','')}")
        row("Year",              form_data.get("car_year", "—"))
        row("Damage record",     _yn(form_data.get("car_damage")))
        row("Registered to",     form_data.get("car_owner", "—").replace("_", " ").capitalize())
        if form_data.get("estimated_car_value"):
            row("Estimated value", _fmt_currency(form_data.get("estimated_car_value")))

    y -= 6
    # ── PROPERTY ────────────────────────────────────────────────────────────
    section("Property / House", "🏠")
    row("Owns a house",   _yn(form_data.get("has_house")))
    if form_data.get("has_house") == "yes":
        row("City",             form_data.get("city", "—"))
        if form_data.get("district"):
            row("District",     form_data.get("district"))
        row("House size",       f"{form_data.get('square_meters','—')} m²")
        if form_data.get("avg_m2_price"):
            row("Avg m² price", _fmt_currency(form_data.get("avg_m2_price")))
        if form_data.get("property_estimated_value"):
            row("Estimated value", _fmt_currency(form_data.get("property_estimated_value")))

    y -= 6
    # ── SCORE BREAKDOWN ─────────────────────────────────────────────────────
    section("Score Breakdown", "📊")
    breakdown = scores.get("breakdown", {})
    for key, val in breakdown.items():
        label = BREAKDOWN_LABELS.get(key, key.replace("_", " ").capitalize())
        sign  = f"+{val}" if val > 0 else str(val)
        row(label, sign)

    total_possible = 93
    row("─" * 30, "")
    row("TOTAL SCORE", f"{scores.get('total_score',0)} / 100 (max possible ~{total_possible})")

    y -= 6
    # ── REASONS ─────────────────────────────────────────────────────────────
    section("Evaluation Notes", "📝")
    reasons = scores.get("reasons", [])
    for reason in reasons:
        if y < 60:
            c.showPage()
            y = H - 60
        c.setFillColor(colors.HexColor("#4f46e5"))
        c.setFont("Helvetica-Bold", 9)
        c.drawString(44, y, "•")
        c.setFillColor(colors.HexColor("#1e293b"))
        c.setFont("Helvetica", 9)
        c.drawString(54, y, reason[:90])
        y -= 15

    # ── FOOTER ──────────────────────────────────────────────────────────────
    c.setFillColor(colors.HexColor("#94a3b8"))
    c.setFont("Helvetica", 8)
    c.drawString(40, 30, "This report is generated automatically by BursIQ — Scholarship Intelligence System.")
    c.drawRightString(W - 40, 30, f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")

    c.save()
