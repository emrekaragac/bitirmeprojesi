import os
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from backend.scoring import compute_scores
from backend.reporting import generate_report
from typing import Optional
from backend.valuation import estimate_property_value

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
    return {"message": "Burs DSS çalışıyor"}

@app.post("/analyze")
async def analyze(
    gender: str = Form(...),
    parents_divorced: str = Form(...),
    mother_working: str = Form(...),
    everyone_healthy: str = Form(...),
    has_car: str = Form(...),
    has_house: str = Form(...),
    city: str = Form(""),
    district: str = Form(""),
    square_meters: str = Form(""),
    car_file: Optional[UploadFile] = File(None),
    house_file: Optional[UploadFile] = File(None),
):
    saved_files = {}

    if car_file is not None:
        car_path = f"uploads/{car_file.filename}"
        with open(car_path, "wb") as buffer:
            buffer.write(await car_file.read())
        saved_files["car_file"] = car_path

    if house_file is not None:
        house_path = f"uploads/{house_file.filename}"
        with open(house_path, "wb") as buffer:
            buffer.write(await house_file.read())
        saved_files["house_file"] = house_path
    property_estimated_value = None
    avg_m2_price = None

    if has_house == "yes" and city and square_meters:
       try:
        valuation_result = estimate_property_value(city, district, float(square_meters))
        property_estimated_value = valuation_result.get("property_estimated_value")
        avg_m2_price = valuation_result.get("avg_m2_price")
       except Exception:
        property_estimated_value = None
        avg_m2_price = None

    form_data = {
    "gender": gender,
    "parents_divorced": parents_divorced,
    "mother_working": mother_working,
    "everyone_healthy": everyone_healthy,
    "has_car": has_car,
    "has_house": has_house,
    "city": city,
    "district": district,
    "square_meters": square_meters,
    "property_estimated_value": property_estimated_value,
    "avg_m2_price": avg_m2_price,
}

    scores = compute_scores(form_data)

    report_path = "reports/generated_report.pdf"
    generate_report(report_path, form_data, scores)

    return {
    "score": scores.get("total_score"),
    "priority": scores.get("priority"),
    "decision": scores.get("decision"),
    "reasons": scores.get("reasons"),
    "report": "reports/generated_report.pdf",
    "uploaded_files": saved_files,
    "city": city,
    "district": district,
    "square_meters": square_meters,
    "avg_m2_price": avg_m2_price,
    "property_estimated_value": property_estimated_value,
}


@app.get("/reports/{filename}")
def get_report(filename: str):
    return FileResponse(f"reports/{filename}")