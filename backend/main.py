import os
import json
from contextlib import asynccontextmanager
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional, Any

from backend.scoring import compute_scores
from backend.academic_scoring import compute_academic_score
from backend.parametric_scoring import compute_parametric_score
from backend.reporting import generate_report
from backend.rag_valuation import rag_estimate_property, rag_estimate_car
from backend.ocr import parse_ruhsat, parse_tapu, validate_document
from backend.verification import validate_tc_no, scan_qr, cross_check
from backend.db import init_db, save_application, get_all_applications, get_application
from backend.scholarship_db import (
    init_scholarship_db,
    create_scholarship,
    get_scholarship,
    get_all_scholarships,
    save_scholarship_application,
    get_scholarship_applications,
    get_scholarship_application,
)

os.makedirs("uploads", exist_ok=True)
os.makedirs("reports", exist_ok=True)

ADMIN_KEY = os.getenv("ADMIN_KEY", "psds2024")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    init_scholarship_db()
    yield


app = FastAPI(title="PSDS API — Parametric Scholarship Distribution System", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {"message": "PSDS API running", "version": "3.0"}


# ─────────────────────────────────────────────────────────────
# DOCUMENT VALIDATION  — anlık belge doğrulama
# ─────────────────────────────────────────────────────────────

@app.post("/validate-document/{doc_type}")
async def validate_doc_endpoint(
    doc_type: str,
    file: UploadFile = File(...),
):
    """
    Yüklenen dosyanın beklenen belge türüne uyup uymadığını kontrol eder.
    doc_type: car_file | house_file | transcript_file | income_file |
              student_certificate | family_registry | disability_report
    """
    import tempfile
    suffix = os.path.splitext(file.filename or "doc")[1] or ".pdf"
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(await file.read())
            tmp_path = tmp.name
        result = validate_document(tmp_path, doc_type)
    except Exception as exc:
        # Backend hatası → geçersiz say, 500 yerine 200 döndür
        result = {
            "valid": False,
            "expected_name": doc_type,
            "detected_name": None,
            "message": f"❌ Belge işlenirken hata oluştu: {str(exc)[:120]}",
            "confidence": 0.0,
            "hits": 0,
        }
    finally:
        if tmp_path:
            try:
                os.remove(tmp_path)
            except Exception:
                pass
    return result


# ─────────────────────────────────────────────────────────────
# SCHOLARSHIP CRUD
# ─────────────────────────────────────────────────────────────

class ScholarshipCreateRequest(BaseModel):
    name: str
    description: str = ""
    deadline: str = ""
    type: str = "financial"          # financial | academic | both
    financial_weight: int = 100
    academic_weight: int = 0
    config: dict                      # { questions: [...], documents: [...] }


@app.post("/scholarship/create")
def scholarship_create(body: ScholarshipCreateRequest):
    sid = create_scholarship(body.dict())
    return {"id": sid, "message": "Scholarship created"}


@app.get("/scholarships")
def scholarships_list():
    """Public endpoint — returns all scholarships (no admin key needed)"""
    all_s = get_all_scholarships()
    # Strip internal config details, return only what applicants need to see
    return [
        {
            "id": s["id"],
            "name": s["name"],
            "description": s["description"],
            "slots": s["slots"],
            "deadline": s["deadline"],
            "type": s["type"],
            "financial_weight": s["financial_weight"],
            "academic_weight": s["academic_weight"],
            "created_at": s["created_at"],
        }
        for s in all_s
    ]


@app.get("/scholarship/{sid}")
def scholarship_get(sid: str):
    s = get_scholarship(sid)
    if not s:
        raise HTTPException(status_code=404, detail="Scholarship not found")
    return s


# ─────────────────────────────────────────────────────────────
# DYNAMIC APPLY — supports files + form fields
# ─────────────────────────────────────────────────────────────

@app.post("/scholarship/{sid}/apply")
async def scholarship_apply(
    sid: str,
    # Identity
    first_name:  str = Form(""),
    last_name:   str = Form(""),
    tc_no:       str = Form(""),
    birth_date:  str = Form(""),
    phone:       str = Form(""),
    email:       str = Form(""),
    university:  str = Form(""),
    department:  str = Form(""),
    grade:       str = Form(""),
    gender:      str = Form(""),
    # Financial fields (optional, used when type=financial|both)
    monthly_income:    str = Form(""),
    family_size:       str = Form("1"),
    is_renting:        str = Form("no"),
    monthly_rent:      str = Form("0"),
    parents_divorced:  str = Form("no"),
    father_working:    str = Form("yes"),
    mother_working:    str = Form("yes"),
    everyone_healthy:  str = Form("yes"),
    siblings_count:    str = Form("0"),
    other_scholarship: str = Form("no"),
    works_part_time:   str = Form("no"),
    has_car:   str = Form("no"),
    car_brand: str = Form(""),
    car_model: str = Form(""),
    car_year:  str = Form(""),
    car_damage: str = Form("no"),
    has_house:     str = Form("no"),
    city:          str = Form(""),
    district:      str = Form(""),
    square_meters: str = Form(""),
    # Academic fields (optional, used when type=academic|both)
    gpa:            str = Form(""),
    gpa_system:     str = Form("4"),
    has_research:   str = Form("no"),
    has_award:      str = Form("no"),
    language_level: str = Form(""),
    has_activity:   str = Form("no"),
    # Extra dynamic fields as JSON string
    extra_fields:   str = Form("{}"),
    # Files
    car_file:       Optional[UploadFile] = File(None),
    house_file:     Optional[UploadFile] = File(None),
    transcript_file: Optional[UploadFile] = File(None),
    income_file:    Optional[UploadFile] = File(None),
):
    s = get_scholarship(sid)
    if not s:
        raise HTTPException(status_code=404, detail="Scholarship not found")

    saved_files = {}
    ruhsat_data = None
    tapu_data   = None

    # OCR — Car
    if car_file and car_file.filename:
        car_path = f"uploads/{car_file.filename}"
        with open(car_path, "wb") as buf:
            buf.write(await car_file.read())
        saved_files["car_file"] = car_path
        try:
            ruhsat_data = parse_ruhsat(car_path)
            if ruhsat_data.get("ocr_success"):
                if not car_brand and ruhsat_data.get("marka"):
                    car_brand = ruhsat_data["marka"]
                if not car_model and ruhsat_data.get("model"):
                    car_model = ruhsat_data["model"]
                if not car_year and ruhsat_data.get("yil"):
                    car_year = str(ruhsat_data["yil"])
        except Exception:
            pass

    # OCR — House
    if house_file and house_file.filename:
        house_path = f"uploads/{house_file.filename}"
        with open(house_path, "wb") as buf:
            buf.write(await house_file.read())
        saved_files["house_file"] = house_path
        try:
            tapu_data = parse_tapu(house_path)
            if tapu_data.get("ocr_success"):
                if not city and tapu_data.get("il"):
                    city = tapu_data["il"]
                if not square_meters and tapu_data.get("yuzolcumu"):
                    square_meters = str(tapu_data["yuzolcumu"])
        except Exception:
            pass

    # Transcript (save only)
    if transcript_file and transcript_file.filename:
        t_path = f"uploads/{transcript_file.filename}"
        with open(t_path, "wb") as buf:
            buf.write(await transcript_file.read())
        saved_files["transcript_file"] = t_path

    # Income doc (save only)
    if income_file and income_file.filename:
        i_path = f"uploads/{income_file.filename}"
        with open(i_path, "wb") as buf:
            buf.write(await income_file.read())
        saved_files["income_file"] = i_path

    # Valuations
    estimated_car_value = None
    car_rag_used = False
    car_confidence = None
    car_reasoning = None
    if has_car == "yes" and car_brand and car_year:
        try:
            res = rag_estimate_car(brand=car_brand, model=car_model,
                                   year=int(car_year), has_damage=(car_damage == "yes"))
            estimated_car_value = res.get("estimated_car_value")
            car_rag_used = res.get("rag_used", False)
            car_confidence = res.get("confidence")
            car_reasoning = res.get("reasoning")
        except Exception:
            pass

    property_estimated_value = None
    avg_m2_price = None
    property_rag_used = False
    property_confidence = None
    property_reasoning = None
    if has_house == "yes" and city and square_meters:
        try:
            val = rag_estimate_property(city=city, district=district, square_meters=float(square_meters))
            property_estimated_value = val.get("property_estimated_value")
            avg_m2_price = val.get("avg_m2_price")
            property_rag_used = val.get("rag_used", False)
            property_confidence = val.get("confidence")
            property_reasoning = val.get("reasoning")
        except Exception:
            pass

    # Parse extra fields
    try:
        extra = json.loads(extra_fields)
    except Exception:
        extra = {}

    form_data = {
        "first_name": first_name, "last_name": last_name, "tc_no": tc_no,
        "birth_date": birth_date, "phone": phone, "email": email,
        "university": university, "department": department, "grade": grade,
        "gender": gender,
        "monthly_income": monthly_income, "family_size": family_size,
        "is_renting": is_renting, "monthly_rent": monthly_rent,
        "parents_divorced": parents_divorced, "father_working": father_working,
        "mother_working": mother_working, "everyone_healthy": everyone_healthy,
        "siblings_count": siblings_count, "other_scholarship": other_scholarship,
        "works_part_time": works_part_time,
        "has_car": has_car, "car_brand": car_brand, "car_model": car_model,
        "car_year": car_year, "car_damage": car_damage,
        "estimated_car_value": estimated_car_value,
        "car_rag_used": car_rag_used, "car_confidence": car_confidence, "car_reasoning": car_reasoning,
        "has_house": has_house, "city": city, "district": district,
        "square_meters": square_meters,
        "property_estimated_value": property_estimated_value,
        "avg_m2_price": avg_m2_price,
        "property_rag_used": property_rag_used, "property_confidence": property_confidence, "property_reasoning": property_reasoning,
        "gpa": gpa, "gpa_system": gpa_system,
        "has_research": has_research, "has_award": has_award,
        "language_level": language_level, "has_activity": has_activity,
        **extra,
    }

    # Compute score — parametric if weights configured, else legacy
    scholarship_type = s.get("type", "financial")
    config_questions  = s.get("config", {}).get("questions", [])
    has_weights = any(q.get("weight", 0) > 0 for q in config_questions)

    if has_weights:
        # Fully parametric: use provider-defined weights and answer scores
        scores = compute_parametric_score(form_data, config_questions)
    else:
        # Legacy fallback
        fin_w = s.get("financial_weight", 100) / 100
        aca_w = s.get("academic_weight", 0) / 100
        if scholarship_type == "financial":
            scores = compute_scores(form_data)
        elif scholarship_type == "academic":
            scores = compute_academic_score(form_data)
        else:
            fin_scores = compute_scores(form_data)
            aca_scores = compute_academic_score(form_data)
            combined = round(fin_scores["total_score"] * fin_w + aca_scores["total_score"] * aca_w)
            combined = max(0, min(combined, 100))
            if combined >= 75:
                priority, decision = "High Priority", "Accepted"
            elif combined >= 50:
                priority, decision = "Medium Priority", "Under Review"
            else:
                priority, decision = "Low Priority", "Rejected"
            scores = {
                "total_score": combined,
                "priority": priority,
                "decision": decision,
                "reasons": fin_scores["reasons"] + aca_scores["reasons"],
                "breakdown": {**fin_scores["breakdown"], **aca_scores["breakdown"]},
            }

    # ── Doğrulama ──
    # TC Kimlik
    tc_validation = validate_tc_no(tc_no)

    # QR Kod tarama
    qr_car   = scan_qr(saved_files["car_file"])   if "car_file"   in saved_files else None
    qr_house = scan_qr(saved_files["house_file"])  if "house_file" in saved_files else None

    # Cross-check
    form_data_for_check = {
        **form_data,
        "estimated_car_value": estimated_car_value,
        "property_estimated_value": property_estimated_value,
    }
    verification = cross_check(form_data_for_check, ruhsat_data, tapu_data)

    # PDF
    report_path = None
    try:
        report_filename = f"reports/report_{sid}_{scores.get('total_score', 0)}.pdf"
        generate_report(report_filename, form_data, scores)
        report_path = report_filename
    except Exception:
        pass

    app_id = save_scholarship_application(sid, form_data, scores, verification)

    return {
        "application_id": app_id,
        "scholarship_id": sid,
        "score": scores.get("total_score"),
        "priority": scores.get("priority"),
        "decision": scores.get("decision"),
        "reasons": scores.get("reasons"),
        "breakdown": scores.get("breakdown"),
        "report": report_path,
        "uploaded_files": saved_files,
        "property_estimated_value": property_estimated_value,
        "avg_m2_price": avg_m2_price,
        "estimated_car_value": estimated_car_value,
        "ruhsat_ocr": ruhsat_data,
        "tapu_ocr": tapu_data,
        "verification": {
            "tc_valid":       tc_validation.get("valid"),
            "tc_error":       tc_validation.get("error"),
            "qr_car":         qr_car,
            "qr_house":       qr_house,
            "trust_score":    verification.get("trust_score"),
            "trust_level":    verification.get("trust_level"),
            "needs_review":   verification.get("needs_review"),
            "flags":          verification.get("flags"),
            "notes":          verification.get("notes"),
            "passed_checks":  verification.get("passed_checks"),
        },
    }


# ─────────────────────────────────────────────────────────────
# LEGACY /analyze  (kept for backward compatibility)
# ─────────────────────────────────────────────────────────────

@app.post("/analyze")
async def analyze(
    first_name:  str = Form(""),
    last_name:   str = Form(""),
    tc_no:       str = Form(""),
    birth_date:  str = Form(""),
    phone:       str = Form(""),
    email:       str = Form(""),
    university:  str = Form(""),
    department:  str = Form(""),
    grade:       str = Form(""),
    gender: str = Form(...),
    parents_divorced: str = Form(...),
    father_working:   str = Form(...),
    mother_working:   str = Form(...),
    everyone_healthy: str = Form(...),
    siblings_count:   str = Form("0"),
    family_size:      str = Form("1"),
    monthly_income:    str = Form(""),
    is_renting:        str = Form("no"),
    monthly_rent:      str = Form("0"),
    other_scholarship: str = Form("no"),
    works_part_time:   str = Form("no"),
    has_car:   str = Form(...),
    car_brand: str = Form(""),
    car_model: str = Form(""),
    car_year:  str = Form(""),
    car_damage: str = Form("no"),
    car_owner:  str = Form(""),
    has_house:     str = Form(...),
    city:          str = Form(""),
    district:      str = Form(""),
    square_meters: str = Form(""),
    car_file:   Optional[UploadFile] = File(None),
    house_file: Optional[UploadFile] = File(None),
):
    saved_files = {}
    ruhsat_data = None
    tapu_data   = None

    if car_file and car_file.filename:
        car_path = f"uploads/{car_file.filename}"
        with open(car_path, "wb") as buf:
            buf.write(await car_file.read())
        saved_files["car_file"] = car_path
        try:
            ruhsat_data = parse_ruhsat(car_path)
            if ruhsat_data.get("ocr_success"):
                if not car_brand and ruhsat_data.get("marka"):
                    car_brand = ruhsat_data["marka"]
                if not car_model and ruhsat_data.get("model"):
                    car_model = ruhsat_data["model"]
                if not car_year and ruhsat_data.get("yil"):
                    car_year = str(ruhsat_data["yil"])
        except Exception:
            pass

    if house_file and house_file.filename:
        house_path = f"uploads/{house_file.filename}"
        with open(house_path, "wb") as buf:
            buf.write(await house_file.read())
        saved_files["house_file"] = house_path
        try:
            tapu_data = parse_tapu(house_path)
            if tapu_data.get("ocr_success"):
                if not city and tapu_data.get("il"):
                    city = tapu_data["il"]
                if not square_meters and tapu_data.get("yuzolcumu"):
                    square_meters = str(tapu_data["yuzolcumu"])
        except Exception:
            pass

    estimated_car_value = None
    car_rag_used = False
    car_confidence = None
    car_reasoning = None
    if has_car == "yes" and car_brand and car_year:
        try:
            res = rag_estimate_car(brand=car_brand, model=car_model,
                                   year=int(car_year), has_damage=(car_damage == "yes"))
            estimated_car_value = res.get("estimated_car_value")
            car_rag_used = res.get("rag_used", False)
            car_confidence = res.get("confidence")
            car_reasoning = res.get("reasoning")
        except Exception:
            pass

    property_estimated_value = None
    avg_m2_price = None
    property_rag_used = False
    property_confidence = None
    property_reasoning = None
    if has_house == "yes" and city and square_meters:
        try:
            val = rag_estimate_property(city=city, district=district, square_meters=float(square_meters))
            property_estimated_value = val.get("property_estimated_value")
            avg_m2_price = val.get("avg_m2_price")
            property_rag_used = val.get("rag_used", False)
            property_confidence = val.get("confidence")
            property_reasoning = val.get("reasoning")
        except Exception:
            pass

    form_data = {
        "first_name": first_name, "last_name": last_name, "tc_no": tc_no,
        "birth_date": birth_date, "phone": phone, "email": email,
        "university": university, "department": department, "grade": grade,
        "gender": gender, "parents_divorced": parents_divorced,
        "father_working": father_working, "mother_working": mother_working,
        "everyone_healthy": everyone_healthy, "siblings_count": siblings_count,
        "family_size": family_size, "monthly_income": monthly_income,
        "is_renting": is_renting, "monthly_rent": monthly_rent,
        "other_scholarship": other_scholarship, "works_part_time": works_part_time,
        "has_car": has_car, "car_brand": car_brand, "car_model": car_model,
        "car_year": car_year, "car_damage": car_damage, "car_owner": car_owner,
        "estimated_car_value": estimated_car_value,
        "car_rag_used": car_rag_used, "car_confidence": car_confidence, "car_reasoning": car_reasoning,
        "has_house": has_house, "city": city, "district": district,
        "square_meters": square_meters,
        "property_estimated_value": property_estimated_value,
        "avg_m2_price": avg_m2_price,
        "property_rag_used": property_rag_used, "property_confidence": property_confidence, "property_reasoning": property_reasoning,
    }

    scores = compute_scores(form_data)

    report_path = None
    try:
        report_filename = f"reports/report_{scores.get('total_score', 0)}.pdf"
        generate_report(report_filename, form_data, scores)
        report_path = report_filename
    except Exception:
        pass

    app_id = None
    try:
        app_id = save_application(form_data, scores)
    except Exception:
        pass

    return {
        "application_id": app_id,
        "score": scores.get("total_score"),
        "priority": scores.get("priority"),
        "decision": scores.get("decision"),
        "reasons": scores.get("reasons"),
        "breakdown": scores.get("breakdown"),
        "report": report_path,
        "uploaded_files": saved_files,
        "city": city, "district": district, "square_meters": square_meters,
        "avg_m2_price": avg_m2_price,
        "property_estimated_value": property_estimated_value,
        "estimated_car_value": estimated_car_value,
        "ruhsat_ocr": ruhsat_data,
        "tapu_ocr": tapu_data,
    }


# ─────────────────────────────────────────────────────────────
# ADMIN ENDPOINTS
# ─────────────────────────────────────────────────────────────

@app.get("/admin/scholarships")
def admin_scholarships(key: str = ""):
    if key != ADMIN_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return get_all_scholarships()


@app.get("/admin/scholarships/{sid}/applications")
def admin_scholarship_applications(sid: str, key: str = ""):
    if key != ADMIN_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return get_scholarship_applications(sid)


@app.get("/admin/scholarship-applications/{app_id}")
def admin_scholarship_application_detail(app_id: int, key: str = ""):
    if key != ADMIN_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")
    data = get_scholarship_application(app_id)
    if not data:
        raise HTTPException(status_code=404, detail="Not found")
    return data


@app.get("/admin/applications")
def admin_applications(key: str = ""):
    if key != ADMIN_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return get_all_applications()


@app.get("/admin/applications/{app_id}")
def admin_application_detail(app_id: int, key: str = ""):
    if key != ADMIN_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")
    data = get_application(app_id)
    if not data:
        raise HTTPException(status_code=404, detail="Not found")
    return data


@app.get("/reports/{filename}")
def get_report(filename: str):
    return FileResponse(f"reports/{filename}")
