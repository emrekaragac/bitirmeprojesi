import os
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from backend.scoring import compute_scores
from backend.reporting import generate_report
from backend.valuation import estimate_property_value, estimate_car_value
from backend.ocr import parse_ruhsat, parse_tapu
from backend.db import init_db, save_application, get_all_applications, get_application
from typing import Optional

app = FastAPI(title="BursIQ API")

# CORS — tum originlere izin ver (public frontend)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

os.makedirs("uploads", exist_ok=True)
os.makedirs("reports", exist_ok=True)

@app.on_event("startup")
def startup():
    init_db()


@app.get("/")
def root():
    return {"message": "BursIQ API calisiyor", "version": "2.0"}


@app.post("/analyze")
async def analyze(
    # Kisisel
    gender: str = Form(...),
    # Aile
    parents_divorced: str = Form(...),
    father_working:   str = Form(...),
    mother_working:   str = Form(...),
    everyone_healthy: str = Form(...),
    siblings_count:   str = Form("0"),
    family_size:      str = Form("1"),
    # Finansal
    monthly_income:    str = Form(""),
    is_renting:        str = Form("no"),
    monthly_rent:      str = Form("0"),
    other_scholarship: str = Form("no"),
    works_part_time:   str = Form("no"),
    # Arac
    has_car:   str = Form(...),
    car_brand: str = Form(""),
    car_model: str = Form(""),
    car_year:  str = Form(""),
    car_damage: str = Form("no"),
    car_owner:  str = Form(""),
    # Konut
    has_house:     str = Form(...),
    city:          str = Form(""),
    district:      str = Form(""),
    square_meters: str = Form(""),
    # Dosyalar
    car_file:   Optional[UploadFile] = File(None),
    house_file: Optional[UploadFile] = File(None),
):
    saved_files = {}
    ruhsat_data = None
    tapu_data   = None

    # --- Ruhsat OCR ---
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

    # --- Tapu OCR ---
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

    # --- Arac Degeri ---
    estimated_car_value  = None
    car_valuation_result = None
    if has_car == "yes" and car_brand and car_year:
        try:
            car_valuation_result = estimate_car_value(
                marka=car_brand, model=car_model,
                yil=int(car_year), has_damage=(car_damage == "yes"),
            )
            estimated_car_value = car_valuation_result.get("estimated_car_value")
        except Exception:
            pass

    # --- Mulk Degeri ---
    property_estimated_value = None
    avg_m2_price             = None
    if has_house == "yes" and city and square_meters:
        try:
            val = estimate_property_value(city=city, district=district, square_meters=float(square_meters))
            property_estimated_value = val.get("property_estimated_value")
            avg_m2_price             = val.get("avg_m2_price")
        except Exception:
            pass

    # --- Skor ---
    form_data = {
        "gender": gender,
        "parents_divorced": parents_divorced,
        "father_working":   father_working,
        "mother_working":   mother_working,
        "everyone_healthy": everyone_healthy,
        "siblings_count":   siblings_count,
        "family_size":      family_size,
        "monthly_income":   monthly_income,
        "is_renting":       is_renting,
        "monthly_rent":     monthly_rent,
        "other_scholarship": other_scholarship,
        "works_part_time":  works_part_time,
        "has_car":          has_car,
        "car_brand":        car_brand,
        "car_model":        car_model,
        "car_year":         car_year,
        "car_damage":       car_damage,
        "car_owner":        car_owner,
        "estimated_car_value": estimated_car_value,
        "has_house":        has_house,
        "city":             city,
        "district":         district,
        "square_meters":    square_meters,
        "property_estimated_value": property_estimated_value,
        "avg_m2_price":     avg_m2_price,
    }

    scores = compute_scores(form_data)

    # --- PDF Rapor ---
    report_path = None
    try:
        report_filename = f"reports/report_{scores.get('total_score',0)}.pdf"
        generate_report(report_filename, form_data, scores)
        report_path = report_filename
    except Exception:
        pass

    # --- DB'ye kaydet ---
    app_id = None
    try:
        app_id = save_application(form_data, scores)
    except Exception:
        pass

    return {
        "application_id": app_id,
        "score":          scores.get("total_score"),
        "priority":       scores.get("priority"),
        "decision":       scores.get("decision"),
        "reasons":        scores.get("reasons"),
        "breakdown":      scores.get("breakdown"),
        "report":         report_path,
        "uploaded_files": saved_files,
        "city":           city,
        "district":       district,
        "square_meters":  square_meters,
        "avg_m2_price":   avg_m2_price,
        "property_estimated_value": property_estimated_value,
        "estimated_car_value":      estimated_car_value,
        "car_valuation":  car_valuation_result,
        "ruhsat_ocr":     ruhsat_data,
        "tapu_ocr":       tapu_data,
    }


# ─── Admin Endpoints ──────────────────────────────────────────────────────────

ADMIN_KEY = os.getenv("ADMIN_KEY", "bursiq2024")


@app.get("/admin/applications")
def admin_applications(key: str = ""):
    if key != ADMIN_KEY:
        from fastapi import HTTPException
        raise HTTPException(status_code=401, detail="Unauthorized")
    return get_all_applications()


@app.get("/admin/applications/{app_id}")
def admin_application_detail(app_id: int, key: str = ""):
    if key != ADMIN_KEY:
        from fastapi import HTTPException
        raise HTTPException(status_code=401, detail="Unauthorized")
    data = get_application(app_id)
    if not data:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Not found")
    return data


@app.get("/reports/{filename}")
def get_report(filename: str):
    return FileResponse(f"reports/{filename}")
