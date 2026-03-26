import os
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from backend.scoring import compute_scores
from backend.reporting import generate_report
from backend.valuation import estimate_property_value, estimate_car_value
from backend.ocr import parse_ruhsat, parse_tapu
from typing import Optional

app = FastAPI()

_local_origins = [
    "http://localhost:3000",
    "http://localhost:3001",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:3001",
]
_frontend_url = os.getenv("FRONTEND_URL", "")
allowed_origins = _local_origins + ([_frontend_url] if _frontend_url else [])

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

os.makedirs("uploads", exist_ok=True)
os.makedirs("reports", exist_ok=True)


@app.get("/")
def root():
    return {"message": "Burs DSS calisiyor"}


@app.post("/analyze")
async def analyze(
    # Kisisel
    gender: str = Form(...),

    # Aile durumu
    parents_divorced: str = Form(...),
    father_working: str = Form(...),
    mother_working: str = Form(...),
    everyone_healthy: str = Form(...),
    siblings_count: str = Form("0"),
    family_size: str = Form("1"),

    # Finansal durum
    monthly_income: str = Form(""),
    is_renting: str = Form("no"),
    monthly_rent: str = Form("0"),
    other_scholarship: str = Form("no"),
    works_part_time: str = Form("no"),

    # Arac
    has_car: str = Form(...),
    car_brand: str = Form(""),
    car_model: str = Form(""),
    car_year: str = Form(""),
    car_damage: str = Form("no"),
    car_owner: str = Form(""),

    # Konut
    has_house: str = Form(...),
    city: str = Form(""),
    district: str = Form(""),
    square_meters: str = Form(""),

    # Dosyalar
    car_file: Optional[UploadFile] = File(None),
    house_file: Optional[UploadFile] = File(None),
):
    saved_files = {}
    ruhsat_data = None
    tapu_data = None

    # -- Arac dosyasi (ruhsat) ------------------------------------------
    if car_file is not None and car_file.filename:
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

    # -- Ev dosyasi (tapu) -----------------------------------------------
    if house_file is not None and house_file.filename:
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

    # -- Arac Deger Tahmini -----------------------------------------------
    estimated_car_value = None
    car_valuation_result = None
    if has_car == "yes" and car_brand and car_year:
        try:
            car_valuation_result = estimate_car_value(
                marka=car_brand,
                model=car_model,
                yil=int(car_year),
                has_damage=(car_damage == "yes"),
            )
            estimated_car_value = car_valuation_result.get("estimated_car_value")
        except Exception:
            pass

    # -- Mulk Deger Tahmini -----------------------------------------------
    property_estimated_value = None
    avg_m2_price = None
    if has_house == "yes" and city and square_meters:
        try:
            val_result = estimate_property_value(
                city=city,
                district=district,
                square_meters=float(square_meters),
            )
            property_estimated_value = val_result.get("property_estimated_value")
            avg_m2_price = val_result.get("avg_m2_price")
        except Exception:
            pass

    # -- Skor Hesapla -----------------------------------------------------
    form_data = {
        "gender": gender,
        "parents_divorced": parents_divorced,
        "father_working": father_working,
        "mother_working": mother_working,
        "everyone_healthy": everyone_healthy,
        "siblings_count": siblings_count,
        "family_size": family_size,
        "monthly_income": monthly_income,
        "is_renting": is_renting,
        "monthly_rent": monthly_rent,
        "other_scholarship": other_scholarship,
        "works_part_time": works_part_time,
        "has_car": has_car,
        "estimated_car_value": estimated_car_value,
        "has_house": has_house,
        "city": city,
        "district": district,
        "square_meters": square_meters,
        "property_estimated_value": property_estimated_value,
    }

    scores = compute_scores(form_data)

    # -- Rapor ------------------------------------------------------------
    report_path = "reports/generated_report.pdf"
    try:
        generate_report(report_path, form_data, scores)
    except Exception:
        report_path = None

    return {
        "score": scores.get("total_score"),
        "priority": scores.get("priority"),
        "decision": scores.get("decision"),
        "reasons": scores.get("reasons"),
        "breakdown": scores.get("breakdown"),
        "report": report_path,
        "uploaded_files": saved_files,
        # Mulk
        "city": city,
        "district": district,
        "square_meters": square_meters,
        "avg_m2_price": avg_m2_price,
        "property_estimated_value": property_estimated_value,
        # Arac
        "estimated_car_value": estimated_car_value,
        "car_valuation": car_valuation_result,
        # OCR sonuclari
        "ruhsat_ocr": ruhsat_data,
        "tapu_ocr": tapu_data,
    }


@app.get("/reports/{filename}")
def get_report(filename: str):
    return FileResponse(f"reports/{filename}")
