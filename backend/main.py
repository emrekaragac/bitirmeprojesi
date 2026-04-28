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
from backend.ocr import parse_ruhsat, parse_tapu, validate_document, extract_text
from backend.claude_vision import analyze_car, analyze_house
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
    try:
        init_db()
    except Exception as e:
        print(f"[WARN] init_db failed: {e}")
    try:
        init_scholarship_db()
    except Exception as e:
        print(f"[WARN] init_scholarship_db failed: {e}")
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
# DEBUG — sistem bileşenlerini test et
# ─────────────────────────────────────────────────────────────

@app.get("/debug-system")
def debug_system():
    """PyMuPDF ve Anthropic API bağlantısını test eder."""
    result = {}

    # PyMuPDF
    try:
        import fitz
        result["pymupdf"] = f"✅ {fitz.__version__}"
    except Exception as e:
        result["pymupdf"] = f"❌ {e}"

    # Anthropic API key
    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    result["api_key"] = f"✅ set ({len(api_key)} chars)" if api_key else "❌ not set"

    # Anthropic API bağlantısı
    try:
        import anthropic
        resp = anthropic.Anthropic(api_key=api_key).messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=10,
            messages=[{"role": "user", "content": "ping"}],
        )
        result["anthropic_api"] = f"✅ OK ({resp.model})"
    except Exception as e:
        result["anthropic_api"] = f"❌ {str(e)[:120]}"

    # web_search tool testi
    try:
        import anthropic
        resp2 = anthropic.Anthropic(api_key=api_key).messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=50,
            tools=[{"type": "web_search_20250305", "name": "web_search"}],
            messages=[{"role": "user", "content": "test"}],
        )
        result["web_search_tool"] = "✅ available"
    except Exception as e:
        result["web_search_tool"] = f"❌ {str(e)[:120]}"

    # Veritabanı bağlantısı
    try:
        import psycopg2
        db_url = os.getenv("DATABASE_URL", "")
        if not db_url:
            result["database"] = "❌ DATABASE_URL not set"
        else:
            conn = psycopg2.connect(db_url)
            conn.close()
            result["database"] = "✅ PostgreSQL bağlantısı OK"
    except Exception as e:
        result["database"] = f"❌ {str(e)[:120]}"

    return result

# ─────────────────────────────────────────────────────────────
# DEBUG — araç fiyat pipeline testi
# ─────────────────────────────────────────────────────────────

@app.get("/debug-price")
def debug_price(brand: str = "mercedes-benz", model: str = "S400d", year: int = 2022):
    """Araç fiyat tahmin pipeline'ını adım adım test eder."""
    from backend.rag_valuation import (
        _live_search_price, rag_estimate_car,
        _run_web_search, _extract_prices,
    )
    import os, anthropic as _anthropic

    result: dict = {"brand": brand, "model": model, "year": year}

    # 1. Web search ham yanıt
    try:
        api_key = os.getenv("ANTHROPIC_API_KEY", "")
        client = _anthropic.Anthropic(api_key=api_key)
        prompt = (
            f"'{year} {brand} {model} ikinci el fiyat' diye Türkiye'de web araması yap. "
            f"Arama sonuçlarında gördüğün TL fiyatlarını SADECE listele, "
            f"yorum yapma, tahmin yapma. Her fiyat ayrı satırda."
        )
        raw_text = _run_web_search(client, "claude-haiku-4-5-20251001", prompt)
        prices = _extract_prices(raw_text, 50_000, 100_000_000)
        result["web_search_raw"] = raw_text[:600]
        result["web_search_prices"] = prices
    except Exception as e:
        result["web_search_raw"] = f"hata: {e}"
        result["web_search_prices"] = []

    # 2. Live search sonucu
    try:
        live = _live_search_price(brand, model, year, has_damage=False)
        result["live_search"] = live if live else "None döndü"
    except Exception as e:
        result["live_search"] = f"hata: {e}"

    # 3. Nihai sonuç
    try:
        final = rag_estimate_car(brand, model, year, has_damage=False)
        result["final_estimate"] = final
    except Exception as e:
        result["final_estimate"] = f"hata: {e}"

    return result


# ─────────────────────────────────────────────────────────────
# DEBUG — belge metin çıkarma testi
# ─────────────────────────────────────────────────────────────

@app.post("/debug-document")
async def debug_document(file: UploadFile = File(...)):
    """Belgeden çıkarılan ham metni döndürür — keyword sorunlarını teşhis için."""
    import tempfile
    from backend.ocr import extract_text
    tmp_path = None
    try:
        suffix = os.path.splitext(file.filename or "doc")[1] or ".pdf"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(await file.read())
            tmp_path = tmp.name
        text = extract_text(tmp_path)
        text_upper = text.upper() if text else ""
        return {
            "filename": file.filename,
            "char_count": len(text) if text else 0,
            "text_preview": text[:1500] if text else "",
            "text_upper_preview": text_upper[:1500],
        }
    except Exception as exc:
        return {"error": str(exc)}
    finally:
        if tmp_path:
            try: os.remove(tmp_path)
            except: pass

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
        # Backend hatası → bloke ETME, uyarıyla kabul et
        result = {
            "valid": True,
            "expected_name": doc_type,
            "detected_name": None,
            "message": f"⚠️ Doğrulama sırasında hata oluştu. Belge manuel incelemeye alınacak. ({str(exc)[:80]})",
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

    # ── Dosyaları kaydet ─────────────────────────────────────────────────────
    car_path   = None
    house_path = None

    if car_file and car_file.filename:
        car_path = f"uploads/{car_file.filename}"
        with open(car_path, "wb") as buf:
            buf.write(await car_file.read())
        saved_files["car_file"] = car_path

    if house_file and house_file.filename:
        house_path = f"uploads/{house_file.filename}"
        with open(house_path, "wb") as buf:
            buf.write(await house_file.read())
        saved_files["house_file"] = house_path

    if transcript_file and transcript_file.filename:
        p = f"uploads/{transcript_file.filename}"
        with open(p, "wb") as buf:
            buf.write(await transcript_file.read())
        saved_files["transcript_file"] = p

    if income_file and income_file.filename:
        p = f"uploads/{income_file.filename}"
        with open(p, "wb") as buf:
            buf.write(await income_file.read())
        saved_files["income_file"] = p

    # ── Araç: belge oku → alan çıkar → değer tahmin ──────────────────────────
    ruhsat_data = None          # cross_check ve response'ta kullanılıyor
    estimated_car_value = None
    car_rag_used = False
    car_confidence = None
    car_reasoning = None

    if has_car == "yes" and car_path:
        try:
            text = extract_text(car_path)
            if text and len(text.strip()) > 20:
                ruhsat_data = parse_ruhsat(car_path)
                if not car_brand and ruhsat_data.get("marka"): car_brand = ruhsat_data["marka"]
                if not car_model and ruhsat_data.get("model"):  car_model = ruhsat_data["model"]
                if not car_year  and ruhsat_data.get("yil"):    car_year  = str(ruhsat_data["yil"])
            ocr_text = ruhsat_data.get("raw_text", "") if ruhsat_data else ""

            # Vision: marka/model/yıl/hasar çıkar — fiyat tahmini Vision'dan alınmaz
            if not (car_brand and car_year):
                vr = analyze_car(car_path)
                if vr:
                    if not car_brand and vr.get("marka"):  car_brand = vr["marka"]
                    if not car_model and vr.get("model"):  car_model = vr["model"]
                    if not car_year  and vr.get("yil"):    car_year  = str(vr["yil"])
                    if vr.get("hasar"):                     car_damage = "yes"

            if car_brand and car_year:
                try:
                    res_car = rag_estimate_car(
                        brand=car_brand, model=car_model,
                        year=int(car_year), has_damage=(car_damage == "yes"),
                        ocr_text=ocr_text,
                    )
                    estimated_car_value = res_car.get("estimated_car_value")
                    car_rag_used   = res_car.get("rag_used", False)
                    car_confidence = res_car.get("confidence")
                    car_reasoning  = res_car.get("reasoning")
                except Exception:
                    pass
        except Exception:
            pass

    # ── Tapu: belge oku → alan çıkar → değer tahmin ──────────────────────────
    tapu_data = None            # cross_check ve response'ta kullanılıyor
    property_estimated_value = None
    avg_m2_price = None
    property_rag_used = False
    property_confidence = None
    property_reasoning = None

    if has_house == "yes" and house_path:
        try:
            text = extract_text(house_path)
            if text and len(text.strip()) > 20:
                tapu_data = parse_tapu(house_path)
                if not city          and tapu_data.get("il"):        city          = tapu_data["il"]
                if not square_meters and tapu_data.get("yuzolcumu"): square_meters = str(tapu_data["yuzolcumu"])
            ocr_text = tapu_data.get("raw_text", "") if tapu_data else ""

            # Vision: il/ilçe/m² çıkar — fiyat tahmini Vision'dan alınmaz
            if not (city and square_meters):
                vh = analyze_house(house_path)
                if vh:
                    if not city          and vh.get("il"):        city          = vh["il"]
                    if not square_meters and vh.get("yuzolcumu"): square_meters = str(vh["yuzolcumu"])

            if city and square_meters:
                try:
                    val = rag_estimate_property(
                        city=city, district=district,
                        square_meters=float(square_meters),
                        ocr_text=ocr_text,
                    )
                    property_estimated_value = val.get("property_estimated_value")
                    avg_m2_price        = val.get("avg_m2_price")
                    property_rag_used   = val.get("rag_used", False)
                    property_confidence = val.get("confidence")
                    property_reasoning  = val.get("reasoning")
                except Exception:
                    pass
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

    vision_car_result = None
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
            else:
                vr = analyze_car(car_path)
                if vr:
                    if not car_brand and vr.get("marka"): car_brand = vr["marka"]
                    if not car_model and vr.get("model"): car_model = vr["model"]
                    if not car_year  and vr.get("yil"):   car_year  = str(vr["yil"])
                    if vr.get("hasar"):                    car_damage = "yes"
                    if vr.get("estimated_value_tl"):
                        vision_car_result = {"estimated_value": vr["estimated_value_tl"],
                                             "confidence": vr.get("confidence", "medium"),
                                             "reasoning": vr.get("reasoning", "")}
        except Exception:
            pass

    vision_house_result = None
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
            else:
                vh = analyze_house(house_path)
                if vh:
                    if not city          and vh.get("il"):        city          = vh["il"]
                    if not square_meters and vh.get("yuzolcumu"): square_meters = str(vh["yuzolcumu"])
                    if vh.get("estimated_value_tl"):
                        vision_house_result = {"estimated_value": vh["estimated_value_tl"],
                                               "price_per_m2": vh.get("price_per_m2"),
                                               "confidence": vh.get("confidence", "medium"),
                                               "reasoning": vh.get("reasoning", "")}
        except Exception:
            pass

    estimated_car_value = None
    car_rag_used = False
    car_confidence = None
    car_reasoning = None
    if has_car == "yes":
        try:
            if vision_car_result and vision_car_result.get("estimated_value"):
                estimated_car_value = vision_car_result["estimated_value"]
                car_rag_used = True
                car_confidence = vision_car_result.get("confidence", "medium")
                car_reasoning = vision_car_result.get("reasoning", "")
            elif car_brand and car_year:
                car_ocr_text = ruhsat_data.get("raw_text", "") if ruhsat_data else ""
                res = rag_estimate_car(
                    brand=car_brand, model=car_model,
                    year=int(car_year), has_damage=(car_damage == "yes"),
                    ocr_text=car_ocr_text,
                )
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
    if has_house == "yes":
        try:
            if vision_house_result and vision_house_result.get("estimated_value"):
                property_estimated_value = vision_house_result["estimated_value"]
                avg_m2_price = vision_house_result.get("price_per_m2")
                property_rag_used = True
                property_confidence = vision_house_result.get("confidence", "medium")
                property_reasoning = vision_house_result.get("reasoning", "")
            elif city and square_meters:
                house_ocr_text = tapu_data.get("raw_text", "") if tapu_data else ""
                val = rag_estimate_property(
                    city=city, district=district,
                    square_meters=float(square_meters),
                    ocr_text=house_ocr_text,
                )
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
