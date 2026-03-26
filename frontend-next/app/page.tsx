"use client"

import { useMemo, useState } from "react"

// ─── Types ──────────────────────────────────────────────────────────────────
type OcrRuhsat = {
  plaka?: string | null
  marka?: string | null
  model?: string | null
  yil?: number | null
  yakit_tipi?: string | null
  sahip_adi?: string | null
  ocr_success?: boolean
}

type OcrTapu = {
  il?: string | null
  ilce?: string | null
  yuzolcumu?: number | null
  nitelik?: string | null
  malik?: string | null
  ocr_success?: boolean
}

type CarValuation = {
  estimated_car_value?: number | null
  marka?: string
  model?: string
  yil?: number
  age?: number
  has_damage?: boolean
}

type AnalyzeResult = {
  score: number
  priority: string
  decision: string
  reasons: string[]
  breakdown?: Record<string, number>
  report?: string
  city?: string
  district?: string
  square_meters?: string
  avg_m2_price?: number | null
  property_estimated_value?: number | null
  estimated_car_value?: number | null
  car_valuation?: CarValuation | null
  ruhsat_ocr?: OcrRuhsat | null
  tapu_ocr?: OcrTapu | null
}

// ─── City / District Data ────────────────────────────────────────────────────
const istanbulDistricts = [
  "Adalar","Arnavutkoy","Atasehir","Avcilar","Bagcilar","Bahcelievler",
  "Bakirkoy","Basaksehir","Bayrampasa","Besiktas","Beykoz","Beylikduzu",
  "Beyoglu","Buyukcekmece","Catalca","Cekmekoy","Esenler","Esenyurt",
  "Eyupsultan","Fatih","Gaziosmanpasa","Gungoren","Kadikoy","Kagithane",
  "Kartal","Kucukcekmece","Maltepe","Pendik","Sancaktepe","Sariyer",
  "Silivri","Sisli","Sultanbeyli","Sultangazi","Tuzla","Umraniye",
  "Uskudar","Zeytinburnu",
]

const cities = [
  "Adana","Adiyaman","Afyonkarahisar","Agri","Amasya","Ankara","Antalya",
  "Artvin","Aydin","Balikesir","Bilecik","Bingol","Bitlis","Bolu","Burdur",
  "Bursa","Canakkale","Cankiri","Corum","Denizli","Diyarbakir","Edirne",
  "Elazig","Erzincan","Erzurum","Eskisehir","Gaziantep","Giresun","Gumushane",
  "Hakkari","Hatay","Isparta","Mersin","Istanbul","Izmir","Kars","Kastamonu",
  "Kayseri","Kirklareli","Kirsehir","Kocaeli","Konya","Kutahya","Malatya",
  "Manisa","Kahramanmaras","Mardin","Mugla","Mus","Nevsehir","Nigde","Ordu",
  "Rize","Sakarya","Samsun","Siirt","Sinop","Sivas","Tekirdag","Tokat",
  "Trabzon","Tunceli","Sanliurfa","Usak","Van","Yozgat","Zonguldak",
  "Aksaray","Bayburt","Karaman","Kirikkale","Batman","Sirnak","Bartin",
  "Ardahan","Igdir","Yalova","Karabuk","Kilis","Osmaniye","Duzce",
]

const carBrands = [
  "Audi","BMW","Citroen","Dacia","Fiat","Ford","Honda","Hyundai","Jeep",
  "Kia","Land Rover","Mercedes","Mitsubishi","Nissan","Opel","Peugeot",
  "Porsche","Renault","Seat","Skoda","Subaru","Suzuki","Tofas","Toyota",
  "Volkswagen","Volvo","Diger",
]

// ─── Helpers ─────────────────────────────────────────────────────────────────
function formatCurrency(value?: number | null) {
  if (value == null || Number.isNaN(value)) return "-"
  return new Intl.NumberFormat("tr-TR", {
    style: "currency",
    currency: "TRY",
    maximumFractionDigits: 0,
  }).format(value)
}

function SectionTitle({ children }: { children: React.ReactNode }) {
  return (
    <div className="border-b border-slate-200 pb-2 mb-5">
      <h2 className="text-sm font-bold text-slate-500 uppercase tracking-widest">
        {children}
      </h2>
    </div>
  )
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <label className="block text-sm font-semibold text-slate-700 mb-1.5">
        {label}
      </label>
      {children}
    </div>
  )
}

const selectCls =
  "w-full rounded-xl border border-slate-300 px-4 py-3 outline-none focus:ring-2 focus:ring-slate-400 bg-white text-slate-800"
const inputCls =
  "w-full rounded-xl border border-slate-300 px-4 py-3 outline-none focus:ring-2 focus:ring-slate-400 bg-white text-slate-800"
const fileCls =
  "w-full rounded-xl border border-slate-300 px-4 py-3 bg-white text-slate-700 cursor-pointer file:mr-3 file:rounded-lg file:border-0 file:bg-slate-100 file:px-3 file:py-1.5 file:text-sm file:font-medium"

// ─── Page ────────────────────────────────────────────────────────────────────
export default function Page() {
  const [gender, setGender] = useState("")
  const [parentsDivorced, setParentsDivorced] = useState("")
  const [fatherWorking, setFatherWorking] = useState("")
  const [motherWorking, setMotherWorking] = useState("")
  const [everyoneHealthy, setEveryoneHealthy] = useState("")
  const [siblingsCount, setSiblingsCount] = useState("0")
  const [familySize, setFamilySize] = useState("1")
  const [monthlyIncome, setMonthlyIncome] = useState("")
  const [isRenting, setIsRenting] = useState("")
  const [monthlyRent, setMonthlyRent] = useState("")
  const [otherScholarship, setOtherScholarship] = useState("")
  const [worksPartTime, setWorksPartTime] = useState("")
  const [hasCar, setHasCar] = useState("")
  const [carBrand, setCarBrand] = useState("")
  const [carModel, setCarModel] = useState("")
  const [carYear, setCarYear] = useState("")
  const [carDamage, setCarDamage] = useState("")
  const [carOwner, setCarOwner] = useState("")
  const [carFile, setCarFile] = useState<File | null>(null)
  const [hasHouse, setHasHouse] = useState("")
  const [city, setCity] = useState("")
  const [district, setDistrict] = useState("")
  const [squareMeters, setSquareMeters] = useState("")
  const [houseFile, setHouseFile] = useState<File | null>(null)
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<AnalyzeResult | null>(null)
  const [error, setError] = useState("")

  const showDistrict = city === "Istanbul"
  const currentDistricts = useMemo(
    () => (city === "Istanbul" ? istanbulDistricts : []),
    [city]
  )

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    setLoading(true)
    setError("")
    setResult(null)
    try {
      const fd = new FormData()
      fd.append("gender", gender)
      fd.append("parents_divorced", parentsDivorced)
      fd.append("father_working", fatherWorking)
      fd.append("mother_working", motherWorking)
      fd.append("everyone_healthy", everyoneHealthy)
      fd.append("siblings_count", siblingsCount)
      fd.append("family_size", familySize)
      fd.append("monthly_income", monthlyIncome)
      fd.append("is_renting", isRenting)
      fd.append("monthly_rent", monthlyRent || "0")
      fd.append("other_scholarship", otherScholarship)
      fd.append("works_part_time", worksPartTime)
      fd.append("has_car", hasCar)
      fd.append("car_brand", carBrand)
      fd.append("car_model", carModel)
      fd.append("car_year", carYear)
      fd.append("car_damage", carDamage)
      fd.append("car_owner", carOwner)
      fd.append("has_house", hasHouse)
      fd.append("city", city)
      fd.append("district", district)
      fd.append("square_meters", squareMeters)
      if (carFile) fd.append("car_file", carFile)
      if (houseFile) fd.append("house_file", houseFile)

      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:9001"
      const response = await fetch(`${apiUrl}/analyze`, { method: "POST", body: fd })
      if (!response.ok) throw new Error((await response.text()) || "Request failed")
      setResult(await response.json())
    } catch (err) {
      console.error(err)
      setError("Something went wrong while analyzing the application.")
    } finally {
      setLoading(false)
    }
  }

  const scoreColor =
    (result?.score ?? 0) >= 75 ? "bg-red-500"
    : (result?.score ?? 0) >= 50 ? "bg-yellow-500"
    : "bg-green-500"

  return (
    <main className="min-h-screen bg-slate-100 py-10 px-4">
      <div className="mx-auto max-w-3xl space-y-6">

        {/* Header */}
        <div className="rounded-2xl bg-slate-900 px-8 py-7 shadow-lg">
          <h1 className="text-3xl font-bold text-white">Scholarship Decision Support System</h1>
          <p className="mt-2 text-slate-300">
            Complete all sections. Ruhsat &amp; tapu documents are read via OCR to estimate asset values.
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-6">

          {/* ── 1 Personal ───────────────────────────────────────────── */}
          <div className="rounded-2xl bg-white shadow border border-slate-200 px-8 py-7">
            <SectionTitle>1 · Personal Information</SectionTitle>
            <Field label="Gender">
              <select value={gender} onChange={(e) => setGender(e.target.value)} className={selectCls} required>
                <option value="">Select gender</option>
                <option value="female">Female</option>
                <option value="male">Male</option>
              </select>
            </Field>
          </div>

          {/* ── 2 Family ─────────────────────────────────────────────── */}
          <div className="rounded-2xl bg-white shadow border border-slate-200 px-8 py-7">
            <SectionTitle>2 · Family Situation</SectionTitle>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
              <Field label="Are your parents divorced?">
                <select value={parentsDivorced} onChange={(e) => setParentsDivorced(e.target.value)} className={selectCls} required>
                  <option value="">Select</option>
                  <option value="yes">Yes</option>
                  <option value="no">No</option>
                </select>
              </Field>
              <Field label="Is your father working?">
                <select value={fatherWorking} onChange={(e) => setFatherWorking(e.target.value)} className={selectCls} required>
                  <option value="">Select</option>
                  <option value="yes">Yes</option>
                  <option value="no">No</option>
                  <option value="deceased">Deceased</option>
                </select>
              </Field>
              <Field label="Is your mother working?">
                <select value={motherWorking} onChange={(e) => setMotherWorking(e.target.value)} className={selectCls} required>
                  <option value="">Select</option>
                  <option value="yes">Yes</option>
                  <option value="no">No</option>
                  <option value="deceased">Deceased</option>
                </select>
              </Field>
              <Field label="Is everyone in the family healthy?">
                <select value={everyoneHealthy} onChange={(e) => setEveryoneHealthy(e.target.value)} className={selectCls} required>
                  <option value="">Select</option>
                  <option value="yes">Yes</option>
                  <option value="no">No — chronic / serious illness</option>
                </select>
              </Field>
              <Field label="Number of siblings">
                <input type="number" min="0" max="20" value={siblingsCount} onChange={(e) => setSiblingsCount(e.target.value)} className={inputCls} required />
              </Field>
              <Field label="Total family members (incl. yourself)">
                <input type="number" min="1" max="30" value={familySize} onChange={(e) => setFamilySize(e.target.value)} className={inputCls} required />
              </Field>
            </div>
          </div>

          {/* ── 3 Financial ──────────────────────────────────────────── */}
          <div className="rounded-2xl bg-white shadow border border-slate-200 px-8 py-7">
            <SectionTitle>3 · Financial Situation</SectionTitle>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
              <Field label="Family monthly income (total, TL)">
                <select value={monthlyIncome} onChange={(e) => setMonthlyIncome(e.target.value)} className={selectCls} required>
                  <option value="">Select range</option>
                  <option value="under_5000">Under ₺5,000</option>
                  <option value="5000_10000">₺5,000 – ₺10,000</option>
                  <option value="10000_20000">₺10,000 – ₺20,000</option>
                  <option value="20000_40000">₺20,000 – ₺40,000</option>
                  <option value="over_40000">Over ₺40,000</option>
                </select>
              </Field>
              <Field label="Do you receive any other scholarship?">
                <select value={otherScholarship} onChange={(e) => setOtherScholarship(e.target.value)} className={selectCls} required>
                  <option value="">Select</option>
                  <option value="yes">Yes</option>
                  <option value="no">No</option>
                </select>
              </Field>
              <Field label="Do you work part-time?">
                <select value={worksPartTime} onChange={(e) => setWorksPartTime(e.target.value)} className={selectCls} required>
                  <option value="">Select</option>
                  <option value="yes">Yes</option>
                  <option value="no">No</option>
                </select>
              </Field>
              <Field label="Is your family currently paying rent?">
                <select value={isRenting} onChange={(e) => setIsRenting(e.target.value)} className={selectCls} required>
                  <option value="">Select</option>
                  <option value="yes">Yes</option>
                  <option value="no">No</option>
                </select>
              </Field>
              {isRenting === "yes" && (
                <Field label="Monthly rent amount (TL)">
                  <input type="number" min="0" value={monthlyRent} onChange={(e) => setMonthlyRent(e.target.value)} className={inputCls} placeholder="e.g. 15000" />
                </Field>
              )}
            </div>
          </div>

          {/* ── 4 Vehicle ────────────────────────────────────────────── */}
          <div className="rounded-2xl bg-white shadow border border-slate-200 px-8 py-7">
            <SectionTitle>4 · Vehicle</SectionTitle>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
              <Field label="Do you have a car?">
                <select value={hasCar} onChange={(e) => setHasCar(e.target.value)} className={selectCls} required>
                  <option value="">Select</option>
                  <option value="yes">Yes</option>
                  <option value="no">No</option>
                </select>
              </Field>

              {hasCar === "yes" && (
                <>
                  <Field label="Car brand">
                    <select value={carBrand} onChange={(e) => setCarBrand(e.target.value)} className={selectCls}>
                      <option value="">Select brand</option>
                      {carBrands.map((b) => <option key={b} value={b}>{b}</option>)}
                    </select>
                  </Field>
                  <Field label="Car model (e.g. Corolla, Polo)">
                    <input type="text" value={carModel} onChange={(e) => setCarModel(e.target.value)} className={inputCls} placeholder="Model name" />
                  </Field>
                  <Field label="Year of manufacture">
                    <input type="number" min="1990" max={new Date().getFullYear()} value={carYear} onChange={(e) => setCarYear(e.target.value)} className={inputCls} placeholder="e.g. 2015" />
                  </Field>
                  <Field label="Is there a damage record (hasar kaydı)?">
                    <select value={carDamage} onChange={(e) => setCarDamage(e.target.value)} className={selectCls}>
                      <option value="">Select</option>
                      <option value="yes">Yes</option>
                      <option value="no">No</option>
                    </select>
                  </Field>
                  <Field label="Registered to whom?">
                    <select value={carOwner} onChange={(e) => setCarOwner(e.target.value)} className={selectCls}>
                      <option value="">Select</option>
                      <option value="self">Myself</option>
                      <option value="mother">Mother</option>
                      <option value="father">Father</option>
                      <option value="sibling">Sibling</option>
                      <option value="other_family">Other family member</option>
                    </select>
                  </Field>
                  <div className="sm:col-span-2">
                    <Field label="Upload vehicle registration / ruhsat (PDF, JPG, PNG)">
                      <input type="file" accept=".pdf,.jpg,.jpeg,.png" onChange={(e) => setCarFile(e.target.files?.[0] || null)} className={fileCls} />
                      <p className="mt-1 text-xs text-slate-400">OCR will auto-extract brand, model and year.</p>
                    </Field>
                  </div>
                </>
              )}
            </div>
          </div>

          {/* ── 5 Property ───────────────────────────────────────────── */}
          <div className="rounded-2xl bg-white shadow border border-slate-200 px-8 py-7">
            <SectionTitle>5 · Property / House</SectionTitle>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
              <Field label="Do you own a house?">
                <select value={hasHouse} onChange={(e) => setHasHouse(e.target.value)} className={selectCls} required>
                  <option value="">Select</option>
                  <option value="yes">Yes</option>
                  <option value="no">No</option>
                </select>
              </Field>

              {hasHouse === "yes" && (
                <>
                  <div className="sm:col-span-2">
                    <Field label="Upload title deed / tapu (PDF, JPG, PNG)">
                      <input type="file" accept=".pdf,.jpg,.jpeg,.png" onChange={(e) => setHouseFile(e.target.files?.[0] || null)} className={fileCls} />
                      <p className="mt-1 text-xs text-slate-400">OCR will auto-extract city and area (m²).</p>
                    </Field>
                  </div>
                  <Field label="City">
                    <select value={city} onChange={(e) => { setCity(e.target.value); setDistrict("") }} className={selectCls}>
                      <option value="">Select city</option>
                      {cities.map((c) => <option key={c} value={c}>{c}</option>)}
                    </select>
                  </Field>
                  {showDistrict && (
                    <Field label="District (ilçe)">
                      <select value={district} onChange={(e) => setDistrict(e.target.value)} className={selectCls}>
                        <option value="">Select district</option>
                        {currentDistricts.map((d) => <option key={d} value={d}>{d}</option>)}
                      </select>
                    </Field>
                  )}
                  <Field label="House size (m²)">
                    <input type="number" min="1" value={squareMeters} onChange={(e) => setSquareMeters(e.target.value)} className={inputCls} placeholder="e.g. 90" />
                  </Field>
                </>
              )}
            </div>
          </div>

          {error && (
            <div className="rounded-xl bg-red-50 border border-red-200 px-5 py-4 text-red-700">
              {error}
            </div>
          )}

          <button type="submit" disabled={loading}
            className="w-full rounded-xl bg-slate-900 text-white font-bold py-4 text-lg hover:bg-slate-800 transition disabled:opacity-50">
            {loading ? "Analyzing…" : "Analyze Application"}
          </button>
        </form>

        {/* ── RESULTS ───────────────────────────────────────────────── */}
        {result && (
          <div className="space-y-5 pb-10">

            {/* Score Card */}
            <div className="rounded-2xl bg-white border border-slate-200 shadow px-8 py-7">
              <h2 className="text-2xl font-bold text-slate-900 mb-6">Analysis Result</h2>
              <div className="flex items-center gap-6 mb-6">
                <div className="text-center min-w-[90px]">
                  <div className="text-6xl font-black text-slate-900">{result.score}</div>
                  <div className="text-sm text-slate-500 mt-1">/ 100</div>
                </div>
                <div className="flex-1">
                  <div className="w-full bg-slate-100 rounded-full h-4 overflow-hidden">
                    <div className={`h-4 rounded-full transition-all ${scoreColor}`} style={{ width: `${result.score}%` }} />
                  </div>
                  <p className="mt-2 text-slate-400 text-xs">100 = highest financial need</p>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="rounded-xl bg-slate-50 border border-slate-200 p-4">
                  <p className="text-xs text-slate-500 uppercase tracking-wide">Priority</p>
                  <p className="text-lg font-bold text-slate-900 mt-1">{result.priority}</p>
                </div>
                <div className="rounded-xl bg-slate-50 border border-slate-200 p-4">
                  <p className="text-xs text-slate-500 uppercase tracking-wide">Decision</p>
                  <p className={`text-lg font-bold mt-1 ${result.decision === "Accepted" ? "text-green-600" : result.decision === "Under Review" ? "text-yellow-600" : "text-red-600"}`}>
                    {result.decision}
                  </p>
                </div>
              </div>
            </div>

            {/* Breakdown */}
            {result.breakdown && Object.keys(result.breakdown).length > 0 && (
              <div className="rounded-2xl bg-white border border-slate-200 shadow px-8 py-7">
                <h3 className="text-lg font-bold text-slate-900 mb-4">Score Breakdown</h3>
                <div className="space-y-3">
                  {Object.entries(result.breakdown).map(([key, val]) => (
                    <div key={key} className="flex items-center gap-3">
                      <span className="w-48 text-sm text-slate-600 capitalize shrink-0">{key.replace(/_/g, " ")}</span>
                      <div className="flex-1 bg-slate-100 rounded-full h-2.5 overflow-hidden">
                        <div className={`h-2.5 rounded-full ${val < 0 ? "bg-green-400" : "bg-slate-700"}`}
                          style={{ width: `${Math.min(100, Math.abs(val) * 3.5)}%` }} />
                      </div>
                      <span className={`text-sm font-bold w-10 text-right shrink-0 ${val < 0 ? "text-green-600" : "text-slate-800"}`}>
                        {val > 0 ? `+${val}` : val}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Asset Valuations */}
            <div className="rounded-2xl bg-white border border-slate-200 shadow px-8 py-7">
              <h3 className="text-lg font-bold text-slate-900 mb-4">Asset Valuations</h3>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="rounded-xl bg-slate-50 border border-slate-200 p-4">
                  <p className="text-xs font-bold text-slate-500 uppercase tracking-wide mb-2">Property</p>
                  <div className="space-y-1 text-sm text-slate-700">
                    <div><span className="font-medium">City:</span> {result.city || "-"}</div>
                    <div><span className="font-medium">District:</span> {result.district || "-"}</div>
                    <div><span className="font-medium">Size:</span> {result.square_meters ? `${result.square_meters} m²` : "-"}</div>
                    <div><span className="font-medium">Avg m² price:</span> {formatCurrency(result.avg_m2_price)}</div>
                    <div className="text-base font-bold text-slate-900 pt-1">Est. Value: {formatCurrency(result.property_estimated_value)}</div>
                  </div>
                </div>
                <div className="rounded-xl bg-slate-50 border border-slate-200 p-4">
                  <p className="text-xs font-bold text-slate-500 uppercase tracking-wide mb-2">Vehicle</p>
                  {result.car_valuation ? (
                    <div className="space-y-1 text-sm text-slate-700">
                      <div><span className="font-medium">Brand:</span> {result.car_valuation.marka || "-"}</div>
                      <div><span className="font-medium">Model:</span> {result.car_valuation.model || "-"}</div>
                      <div><span className="font-medium">Year:</span> {result.car_valuation.yil || "-"}</div>
                      <div><span className="font-medium">Age:</span> {result.car_valuation.age} years</div>
                      <div><span className="font-medium">Damage record:</span> {result.car_valuation.has_damage ? "Yes" : "No"}</div>
                      <div className="text-base font-bold text-slate-900 pt-1">Est. Value: {formatCurrency(result.car_valuation.estimated_car_value)}</div>
                    </div>
                  ) : (
                    <p className="text-sm text-slate-400">No vehicle</p>
                  )}
                </div>
              </div>
            </div>

            {/* OCR Results */}
            {(result.ruhsat_ocr?.ocr_success || result.tapu_ocr?.ocr_success) && (
              <div className="rounded-2xl bg-white border border-slate-200 shadow px-8 py-7">
                <h3 className="text-lg font-bold text-slate-900 mb-4">OCR Extraction Results</h3>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  {result.ruhsat_ocr?.ocr_success && (
                    <div className="rounded-xl bg-blue-50 border border-blue-200 p-4">
                      <p className="text-xs font-bold text-blue-700 uppercase tracking-wide mb-2">Ruhsat (Vehicle Reg.)</p>
                      <div className="space-y-1 text-sm text-slate-700">
                        <div><span className="font-medium">Plate:</span> {result.ruhsat_ocr.plaka || "-"}</div>
                        <div><span className="font-medium">Brand:</span> {result.ruhsat_ocr.marka || "-"}</div>
                        <div><span className="font-medium">Year:</span> {result.ruhsat_ocr.yil || "-"}</div>
                        <div><span className="font-medium">Fuel:</span> {result.ruhsat_ocr.yakit_tipi || "-"}</div>
                        <div><span className="font-medium">Owner:</span> {result.ruhsat_ocr.sahip_adi || "-"}</div>
                      </div>
                    </div>
                  )}
                  {result.tapu_ocr?.ocr_success && (
                    <div className="rounded-xl bg-emerald-50 border border-emerald-200 p-4">
                      <p className="text-xs font-bold text-emerald-700 uppercase tracking-wide mb-2">Tapu (Title Deed)</p>
                      <div className="space-y-1 text-sm text-slate-700">
                        <div><span className="font-medium">Province:</span> {result.tapu_ocr.il || "-"}</div>
                        <div><span className="font-medium">District:</span> {result.tapu_ocr.ilce || "-"}</div>
                        <div><span className="font-medium">Area:</span> {result.tapu_ocr.yuzolcumu ? `${result.tapu_ocr.yuzolcumu} m²` : "-"}</div>
                        <div><span className="font-medium">Type:</span> {result.tapu_ocr.nitelik || "-"}</div>
                        <div><span className="font-medium">Owner:</span> {result.tapu_ocr.malik || "-"}</div>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Reasons */}
            <div className="rounded-2xl bg-white border border-slate-200 shadow px-8 py-7">
              <h3 className="text-lg font-bold text-slate-900 mb-4">Scoring Reasons</h3>
              {result.reasons?.length > 0 ? (
                <ul className="list-disc pl-5 space-y-2 text-slate-700">
                  {result.reasons.map((r, i) => <li key={i}>{r}</li>)}
                </ul>
              ) : (
                <p className="text-slate-400">No reasons returned.</p>
              )}
            </div>

            {/* Report */}
            {result.report && (
              <div className="rounded-2xl bg-white border border-slate-200 shadow px-8 py-7">
                <h3 className="text-lg font-bold text-slate-900 mb-3">Generated Report</h3>
                <a
                  href={`${process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:9001"}/${result.report}`}
                  target="_blank" rel="noreferrer"
                  className="inline-flex items-center rounded-xl bg-slate-900 px-5 py-2.5 text-white font-semibold hover:bg-slate-700 transition"
                >
                  Open PDF Report
                </a>
              </div>
            )}
          </div>
        )}
      </div>
    </main>
  )
}
