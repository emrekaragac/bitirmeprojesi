"use client"

import { useMemo, useState } from "react"

// ─── Types ───────────────────────────────────────────────────────────────────
type OcrRuhsat = {
  plaka?: string | null; marka?: string | null; model?: string | null
  yil?: number | null; yakit_tipi?: string | null; sahip_adi?: string | null
  ocr_success?: boolean
}
type OcrTapu = {
  il?: string | null; ilce?: string | null; yuzolcumu?: number | null
  nitelik?: string | null; malik?: string | null; ocr_success?: boolean
}
type CarValuation = {
  estimated_car_value?: number | null; marka?: string; model?: string
  yil?: number; age?: number; has_damage?: boolean
}
type AnalyzeResult = {
  score: number; priority: string; decision: string; reasons: string[]
  breakdown?: Record<string, number>; report?: string
  city?: string; district?: string; square_meters?: string
  avg_m2_price?: number | null; property_estimated_value?: number | null
  estimated_car_value?: number | null; car_valuation?: CarValuation | null
  ruhsat_ocr?: OcrRuhsat | null; tapu_ocr?: OcrTapu | null
}

// ─── Data ────────────────────────────────────────────────────────────────────
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

// ─── Helpers ──────────────────────────────────────────────────────────────────
function fmt(v?: number | null) {
  if (v == null || Number.isNaN(v)) return "—"
  return new Intl.NumberFormat("tr-TR", { style: "currency", currency: "TRY", maximumFractionDigits: 0 }).format(v)
}

// ─── Logo SVG ─────────────────────────────────────────────────────────────────
function BursIQLogo({ size = 40 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg">
      {/* Graduation cap base */}
      <path d="M24 8L4 18L24 28L44 18L24 8Z" fill="url(#grad1)" opacity="0.95"/>
      {/* Cap top highlight */}
      <path d="M24 8L44 18L24 28L4 18L24 8Z" stroke="white" strokeWidth="0.5" strokeOpacity="0.3" fill="none"/>
      {/* Tassel string */}
      <line x1="44" y1="18" x2="44" y2="30" stroke="white" strokeWidth="2" strokeLinecap="round" strokeOpacity="0.8"/>
      <circle cx="44" cy="32" r="2.5" fill="white" fillOpacity="0.9"/>
      {/* IQ bars inside cap — financial bars */}
      <rect x="16" y="35" width="4" height="8" rx="2" fill="url(#grad2)" opacity="0.9"/>
      <rect x="22" y="31" width="4" height="12" rx="2" fill="url(#grad2)" opacity="0.95"/>
      <rect x="28" y="33" width="4" height="10" rx="2" fill="url(#grad2)"/>
      <defs>
        <linearGradient id="grad1" x1="4" y1="8" x2="44" y2="28" gradientUnits="userSpaceOnUse">
          <stop offset="0%" stopColor="#818cf8"/>
          <stop offset="100%" stopColor="#6366f1"/>
        </linearGradient>
        <linearGradient id="grad2" x1="0" y1="0" x2="0" y2="1" gradientUnits="objectBoundingBox">
          <stop offset="0%" stopColor="#a5b4fc"/>
          <stop offset="100%" stopColor="#818cf8"/>
        </linearGradient>
      </defs>
    </svg>
  )
}

// ─── Step Indicator ───────────────────────────────────────────────────────────
const STEPS = ["Personal", "Family", "Financial", "Vehicle", "Property"]
function StepBar({ active }: { active: number }) {
  return (
    <div className="flex items-center gap-1 mb-8">
      {STEPS.map((label, i) => (
        <div key={i} className="flex items-center gap-1 flex-1">
          <div className="flex flex-col items-center flex-1">
            <div className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold border-2 transition-all
              ${i < active ? "bg-indigo-600 border-indigo-600 text-white"
              : i === active ? "bg-white border-indigo-600 text-indigo-600"
              : "bg-white border-slate-200 text-slate-400"}`}>
              {i < active ? "✓" : i + 1}
            </div>
            <span className={`text-[10px] mt-0.5 hidden sm:block font-medium ${i === active ? "text-indigo-600" : "text-slate-400"}`}>
              {label}
            </span>
          </div>
          {i < STEPS.length - 1 && (
            <div className={`h-0.5 flex-1 mb-4 transition-all ${i < active ? "bg-indigo-600" : "bg-slate-200"}`} />
          )}
        </div>
      ))}
    </div>
  )
}

// ─── Reusable Field ───────────────────────────────────────────────────────────
function Field({ label, hint, children }: { label: string; hint?: string; children: React.ReactNode }) {
  return (
    <div>
      <label className="block text-sm font-semibold text-slate-700 mb-1.5">{label}</label>
      {children}
      {hint && <p className="mt-1 text-xs text-slate-400">{hint}</p>}
    </div>
  )
}

const sel = "w-full rounded-xl border border-slate-200 px-4 py-3 outline-none focus:ring-2 focus:ring-indigo-400 focus:border-indigo-400 bg-white text-slate-800 text-sm transition"
const inp = "w-full rounded-xl border border-slate-200 px-4 py-3 outline-none focus:ring-2 focus:ring-indigo-400 focus:border-indigo-400 bg-white text-slate-800 text-sm transition"
const fileInp = "w-full rounded-xl border-2 border-dashed border-slate-200 px-4 py-3 bg-white text-slate-700 cursor-pointer text-sm hover:border-indigo-400 transition file:mr-3 file:rounded-lg file:border-0 file:bg-indigo-50 file:px-3 file:py-1 file:text-xs file:font-semibold file:text-indigo-700"

// ─── Card ─────────────────────────────────────────────────────────────────────
function Card({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return (
    <div className={`rounded-2xl bg-white shadow-sm border border-slate-100 px-7 py-6 ${className}`}>
      {children}
    </div>
  )
}

function SectionTitle({ icon, children }: { icon: string; children: React.ReactNode }) {
  return (
    <div className="flex items-center gap-2 mb-5 pb-3 border-b border-slate-100">
      <span className="text-lg">{icon}</span>
      <h2 className="text-sm font-bold text-slate-600 uppercase tracking-wider">{children}</h2>
    </div>
  )
}

// ─── Page ─────────────────────────────────────────────────────────────────────
export default function Page() {
  const [step, setStep] = useState(1)

  // Personal
  const [gender, setGender] = useState("")
  // Family
  const [parentsDivorced, setParentsDivorced] = useState("")
  const [fatherWorking, setFatherWorking] = useState("")
  const [motherWorking, setMotherWorking] = useState("")
  const [everyoneHealthy, setEveryoneHealthy] = useState("")
  const [siblingsCount, setSiblingsCount] = useState("0")
  const [familySize, setFamilySize] = useState("1")
  // Financial
  const [monthlyIncome, setMonthlyIncome] = useState("")
  const [isRenting, setIsRenting] = useState("")
  const [monthlyRent, setMonthlyRent] = useState("")
  const [otherScholarship, setOtherScholarship] = useState("")
  const [worksPartTime, setWorksPartTime] = useState("")
  // Car
  const [hasCar, setHasCar] = useState("")
  const [carBrand, setCarBrand] = useState("")
  const [carModel, setCarModel] = useState("")
  const [carYear, setCarYear] = useState("")
  const [carDamage, setCarDamage] = useState("")
  const [carOwner, setCarOwner] = useState("")
  const [carFile, setCarFile] = useState<File | null>(null)
  // House
  const [hasHouse, setHasHouse] = useState("")
  const [city, setCity] = useState("")
  const [district, setDistrict] = useState("")
  const [squareMeters, setSquareMeters] = useState("")
  const [houseFile, setHouseFile] = useState<File | null>(null)
  // UI
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<AnalyzeResult | null>(null)
  const [error, setError] = useState("")

  const showDistrict = city === "Istanbul"
  const currentDistricts = useMemo(() => (city === "Istanbul" ? istanbulDistricts : []), [city])

  const handleSubmit = async () => {
    setLoading(true); setError(""); setResult(null)
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
      const res = await fetch(`${apiUrl}/analyze`, { method: "POST", body: fd })
      if (!res.ok) throw new Error((await res.text()) || "Request failed")
      setResult(await res.json())
      setStep(5)
    } catch (e) {
      console.error(e); setError("Something went wrong. Please try again.")
    } finally {
      setLoading(false)
    }
  }

  // Score color
  const sc = result?.score ?? 0
  const scoreGradient = sc >= 75 ? "from-red-500 to-rose-600"
    : sc >= 50 ? "from-amber-400 to-orange-500"
    : "from-emerald-400 to-green-500"
  const decisionColor = result?.decision === "Accepted" ? "text-emerald-600 bg-emerald-50 border-emerald-200"
    : result?.decision === "Under Review" ? "text-amber-600 bg-amber-50 border-amber-200"
    : "text-red-600 bg-red-50 border-red-200"

  const canSubmit = gender && parentsDivorced && fatherWorking && motherWorking &&
    everyoneHealthy && monthlyIncome && otherScholarship && worksPartTime &&
    isRenting && hasCar && hasHouse

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-indigo-50/30 to-violet-50/20">

      {/* ── NAVBAR ─────────────────────────────────────────────────── */}
      <nav className="sticky top-0 z-30 backdrop-blur-md bg-white/80 border-b border-slate-100 shadow-sm">
        <div className="max-w-3xl mx-auto px-6 h-16 flex items-center gap-3">
          <BursIQLogo size={36} />
          <div>
            <span className="text-xl font-black tracking-tight bg-gradient-to-r from-indigo-600 to-violet-600 bg-clip-text text-transparent">
              BursIQ
            </span>
            <span className="ml-2 text-xs font-medium text-slate-400 hidden sm:inline">
              Scholarship Intelligence System
            </span>
          </div>
          <div className="ml-auto">
            <span className="text-xs bg-indigo-100 text-indigo-700 font-semibold px-3 py-1 rounded-full">
              Beta
            </span>
          </div>
        </div>
      </nav>

      <main className="max-w-3xl mx-auto px-4 py-8 space-y-5">

        {/* ── FORM STEPS ─────────────────────────────────────────────── */}
        {step >= 1 && step <= 4 && (
          <>
            <StepBar active={step - 1} />

            {/* Step 1: Personal */}
            {step === 1 && (
              <Card>
                <SectionTitle icon="👤">Personal Information</SectionTitle>
                <Field label="Gender">
                  <select value={gender} onChange={e => setGender(e.target.value)} className={sel}>
                    <option value="">Select gender</option>
                    <option value="female">Female</option>
                    <option value="male">Male</option>
                  </select>
                </Field>
              </Card>
            )}

            {/* Step 2: Family */}
            {step === 2 && (
              <Card>
                <SectionTitle icon="👨‍👩‍👧‍👦">Family Situation</SectionTitle>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <Field label="Are your parents divorced?">
                    <select value={parentsDivorced} onChange={e => setParentsDivorced(e.target.value)} className={sel}>
                      <option value="">Select</option>
                      <option value="yes">Yes</option>
                      <option value="no">No</option>
                    </select>
                  </Field>
                  <Field label="Is your father working?">
                    <select value={fatherWorking} onChange={e => setFatherWorking(e.target.value)} className={sel}>
                      <option value="">Select</option>
                      <option value="yes">Yes</option>
                      <option value="no">No</option>
                      <option value="deceased">Deceased</option>
                    </select>
                  </Field>
                  <Field label="Is your mother working?">
                    <select value={motherWorking} onChange={e => setMotherWorking(e.target.value)} className={sel}>
                      <option value="">Select</option>
                      <option value="yes">Yes</option>
                      <option value="no">No</option>
                      <option value="deceased">Deceased</option>
                    </select>
                  </Field>
                  <Field label="Is everyone in the family healthy?">
                    <select value={everyoneHealthy} onChange={e => setEveryoneHealthy(e.target.value)} className={sel}>
                      <option value="">Select</option>
                      <option value="yes">Yes — no chronic illness</option>
                      <option value="no">No — chronic / serious illness</option>
                    </select>
                  </Field>
                  <Field label="Number of siblings">
                    <input type="number" min="0" max="20" value={siblingsCount} onChange={e => setSiblingsCount(e.target.value)} className={inp} />
                  </Field>
                  <Field label="Total family members (incl. yourself)">
                    <input type="number" min="1" max="30" value={familySize} onChange={e => setFamilySize(e.target.value)} className={inp} />
                  </Field>
                </div>
              </Card>
            )}

            {/* Step 3: Financial */}
            {step === 3 && (
              <Card>
                <SectionTitle icon="💰">Financial Situation</SectionTitle>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <Field label="Family monthly income (total)">
                    <select value={monthlyIncome} onChange={e => setMonthlyIncome(e.target.value)} className={sel}>
                      <option value="">Select range</option>
                      <option value="under_5000">Under ₺5,000</option>
                      <option value="5000_10000">₺5,000 – ₺10,000</option>
                      <option value="10000_20000">₺10,000 – ₺20,000</option>
                      <option value="20000_40000">₺20,000 – ₺40,000</option>
                      <option value="over_40000">Over ₺40,000</option>
                    </select>
                  </Field>
                  <Field label="Do you receive any other scholarship?">
                    <select value={otherScholarship} onChange={e => setOtherScholarship(e.target.value)} className={sel}>
                      <option value="">Select</option>
                      <option value="yes">Yes</option>
                      <option value="no">No</option>
                    </select>
                  </Field>
                  <Field label="Do you work part-time?">
                    <select value={worksPartTime} onChange={e => setWorksPartTime(e.target.value)} className={sel}>
                      <option value="">Select</option>
                      <option value="yes">Yes</option>
                      <option value="no">No</option>
                    </select>
                  </Field>
                  <Field label="Is your family currently paying rent?">
                    <select value={isRenting} onChange={e => setIsRenting(e.target.value)} className={sel}>
                      <option value="">Select</option>
                      <option value="yes">Yes</option>
                      <option value="no">No</option>
                    </select>
                  </Field>
                  {isRenting === "yes" && (
                    <Field label="Monthly rent amount (TL)" hint="Enter approximate monthly rent">
                      <input type="number" min="0" value={monthlyRent} onChange={e => setMonthlyRent(e.target.value)} className={inp} placeholder="e.g. 15000" />
                    </Field>
                  )}
                </div>
              </Card>
            )}

            {/* Step 4: Vehicle */}
            {step === 4 && (
              <div className="space-y-5">
                <Card>
                  <SectionTitle icon="🚗">Vehicle</SectionTitle>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <Field label="Does your family own a car?">
                      <select value={hasCar} onChange={e => setHasCar(e.target.value)} className={sel}>
                        <option value="">Select</option>
                        <option value="yes">Yes</option>
                        <option value="no">No</option>
                      </select>
                    </Field>
                    {hasCar === "yes" && (
                      <>
                        <Field label="Car brand">
                          <select value={carBrand} onChange={e => setCarBrand(e.target.value)} className={sel}>
                            <option value="">Select brand</option>
                            {carBrands.map(b => <option key={b} value={b}>{b}</option>)}
                          </select>
                        </Field>
                        <Field label="Car model">
                          <input type="text" value={carModel} onChange={e => setCarModel(e.target.value)} className={inp} placeholder="e.g. Corolla, Polo" />
                        </Field>
                        <Field label="Year of manufacture">
                          <input type="number" min="1990" max={new Date().getFullYear()} value={carYear} onChange={e => setCarYear(e.target.value)} className={inp} placeholder="e.g. 2015" />
                        </Field>
                        <Field label="Damage record (hasar kaydı)?">
                          <select value={carDamage} onChange={e => setCarDamage(e.target.value)} className={sel}>
                            <option value="">Select</option>
                            <option value="yes">Yes</option>
                            <option value="no">No</option>
                          </select>
                        </Field>
                        <Field label="Registered to whom?">
                          <select value={carOwner} onChange={e => setCarOwner(e.target.value)} className={sel}>
                            <option value="">Select</option>
                            <option value="self">Myself</option>
                            <option value="mother">Mother</option>
                            <option value="father">Father</option>
                            <option value="sibling">Sibling</option>
                            <option value="other_family">Other family member</option>
                          </select>
                        </Field>
                        <div className="sm:col-span-2">
                          <Field label="Upload vehicle registration (ruhsat)" hint="OCR will auto-extract brand, model and year — PDF, JPG or PNG">
                            <input type="file" accept=".pdf,.jpg,.jpeg,.png" onChange={e => setCarFile(e.target.files?.[0] || null)} className={fileInp} />
                          </Field>
                        </div>
                      </>
                    )}
                  </div>
                </Card>

                <Card>
                  <SectionTitle icon="🏠">Property / House</SectionTitle>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <Field label="Does your family own a house?">
                      <select value={hasHouse} onChange={e => setHasHouse(e.target.value)} className={sel}>
                        <option value="">Select</option>
                        <option value="yes">Yes</option>
                        <option value="no">No</option>
                      </select>
                    </Field>
                    {hasHouse === "yes" && (
                      <>
                        <div className="sm:col-span-2">
                          <Field label="Upload title deed (tapu)" hint="OCR will auto-extract city and area — PDF, JPG or PNG">
                            <input type="file" accept=".pdf,.jpg,.jpeg,.png" onChange={e => setHouseFile(e.target.files?.[0] || null)} className={fileInp} />
                          </Field>
                        </div>
                        <Field label="City">
                          <select value={city} onChange={e => { setCity(e.target.value); setDistrict("") }} className={sel}>
                            <option value="">Select city</option>
                            {cities.map(c => <option key={c} value={c}>{c}</option>)}
                          </select>
                        </Field>
                        {showDistrict && (
                          <Field label="District (ilçe)">
                            <select value={district} onChange={e => setDistrict(e.target.value)} className={sel}>
                              <option value="">Select district</option>
                              {currentDistricts.map(d => <option key={d} value={d}>{d}</option>)}
                            </select>
                          </Field>
                        )}
                        <Field label="House size (m²)">
                          <input type="number" min="1" value={squareMeters} onChange={e => setSquareMeters(e.target.value)} className={inp} placeholder="e.g. 90" />
                        </Field>
                      </>
                    )}
                  </div>
                </Card>
              </div>
            )}

            {/* Error */}
            {error && (
              <div className="rounded-xl bg-red-50 border border-red-200 px-5 py-4 text-red-700 text-sm flex items-center gap-2">
                <span>⚠️</span> {error}
              </div>
            )}

            {/* Nav Buttons */}
            <div className="flex gap-3">
              {step > 1 && (
                <button
                  onClick={() => setStep(s => s - 1)}
                  className="flex-1 rounded-xl border-2 border-slate-200 text-slate-600 font-semibold py-3 hover:border-slate-300 transition text-sm"
                >
                  ← Back
                </button>
              )}
              {step < 4 ? (
                <button
                  onClick={() => setStep(s => s + 1)}
                  className="flex-1 rounded-xl bg-gradient-to-r from-indigo-600 to-violet-600 text-white font-bold py-3 hover:shadow-lg hover:shadow-indigo-200 transition-all text-sm"
                >
                  Continue →
                </button>
              ) : (
                <button
                  onClick={handleSubmit}
                  disabled={loading || !canSubmit}
                  className="flex-1 rounded-xl bg-gradient-to-r from-indigo-600 to-violet-600 text-white font-bold py-3 hover:shadow-lg hover:shadow-indigo-200 transition-all text-sm disabled:opacity-50"
                >
                  {loading ? (
                    <span className="flex items-center justify-center gap-2">
                      <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z"/>
                      </svg>
                      Analyzing…
                    </span>
                  ) : "Analyze Application ✓"}
                </button>
              )}
            </div>
          </>
        )}

        {/* ── RESULTS ────────────────────────────────────────────────── */}
        {result && step === 5 && (
          <div className="space-y-5 pb-12">

            {/* Big Score Hero */}
            <div className={`rounded-3xl overflow-hidden shadow-lg bg-gradient-to-br ${scoreGradient}`}>
              <div className="px-8 py-8 text-white">
                <div className="flex items-start justify-between">
                  <div>
                    <p className="text-white/70 text-sm font-medium mb-1">Financial Need Score</p>
                    <div className="text-8xl font-black tracking-tight leading-none">{result.score}</div>
                    <p className="text-white/70 text-sm mt-1">out of 100</p>
                  </div>
                  <div className={`text-right`}>
                    <div className={`inline-block border rounded-xl px-4 py-2 text-sm font-bold ${decisionColor}`}>
                      {result.decision}
                    </div>
                    <p className="text-white/80 text-sm mt-3 font-semibold">{result.priority}</p>
                  </div>
                </div>
                {/* Score bar */}
                <div className="mt-6 bg-white/20 rounded-full h-3 overflow-hidden">
                  <div className="h-3 bg-white rounded-full transition-all" style={{ width: `${result.score}%` }} />
                </div>
                <p className="mt-2 text-white/60 text-xs">100 = highest financial need (most eligible)</p>
              </div>
            </div>

            {/* Breakdown */}
            {result.breakdown && Object.keys(result.breakdown).length > 0 && (
              <Card>
                <SectionTitle icon="📊">Score Breakdown</SectionTitle>
                <div className="space-y-3">
                  {Object.entries(result.breakdown).map(([key, val]) => (
                    <div key={key} className="flex items-center gap-3">
                      <span className="w-44 text-xs text-slate-500 font-medium capitalize shrink-0">
                        {key.replace(/_/g, " ")}
                      </span>
                      <div className="flex-1 bg-slate-100 rounded-full h-2 overflow-hidden">
                        <div
                          className={`h-2 rounded-full transition-all ${val < 0 ? "bg-emerald-400" : val >= 20 ? "bg-indigo-500" : "bg-indigo-400"}`}
                          style={{ width: `${Math.min(100, Math.abs(val) * 3.5)}%` }}
                        />
                      </div>
                      <span className={`text-xs font-bold w-10 text-right shrink-0 ${val < 0 ? "text-emerald-600" : "text-indigo-700"}`}>
                        {val > 0 ? `+${val}` : val}
                      </span>
                    </div>
                  ))}
                </div>
              </Card>
            )}

            {/* Asset Cards */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {/* Property */}
              <Card>
                <div className="flex items-center gap-2 mb-4">
                  <span className="text-2xl">🏠</span>
                  <h3 className="font-bold text-slate-700 text-sm">Property Valuation</h3>
                </div>
                <div className="space-y-2 text-sm text-slate-600">
                  <div className="flex justify-between"><span className="text-slate-400">City</span><span className="font-medium">{result.city || "—"}</span></div>
                  <div className="flex justify-between"><span className="text-slate-400">District</span><span className="font-medium">{result.district || "—"}</span></div>
                  <div className="flex justify-between"><span className="text-slate-400">Size</span><span className="font-medium">{result.square_meters ? `${result.square_meters} m²` : "—"}</span></div>
                  <div className="flex justify-between"><span className="text-slate-400">Avg m²</span><span className="font-medium">{fmt(result.avg_m2_price)}</span></div>
                  <div className="mt-3 pt-3 border-t border-slate-100 flex justify-between items-center">
                    <span className="text-slate-400 text-xs">Estimated value</span>
                    <span className="font-black text-indigo-600">{fmt(result.property_estimated_value)}</span>
                  </div>
                </div>
              </Card>

              {/* Vehicle */}
              <Card>
                <div className="flex items-center gap-2 mb-4">
                  <span className="text-2xl">🚗</span>
                  <h3 className="font-bold text-slate-700 text-sm">Vehicle Valuation</h3>
                </div>
                {result.car_valuation ? (
                  <div className="space-y-2 text-sm text-slate-600">
                    <div className="flex justify-between"><span className="text-slate-400">Brand</span><span className="font-medium">{result.car_valuation.marka || "—"}</span></div>
                    <div className="flex justify-between"><span className="text-slate-400">Model</span><span className="font-medium">{result.car_valuation.model || "—"}</span></div>
                    <div className="flex justify-between"><span className="text-slate-400">Year</span><span className="font-medium">{result.car_valuation.yil || "—"}</span></div>
                    <div className="flex justify-between"><span className="text-slate-400">Age</span><span className="font-medium">{result.car_valuation.age} yrs</span></div>
                    <div className="flex justify-between"><span className="text-slate-400">Damage</span>
                      <span className={`font-medium text-xs px-2 py-0.5 rounded-full ${result.car_valuation.has_damage ? "bg-red-100 text-red-600" : "bg-emerald-100 text-emerald-600"}`}>
                        {result.car_valuation.has_damage ? "Yes" : "No"}
                      </span>
                    </div>
                    <div className="mt-3 pt-3 border-t border-slate-100 flex justify-between items-center">
                      <span className="text-slate-400 text-xs">Estimated value</span>
                      <span className="font-black text-indigo-600">{fmt(result.car_valuation.estimated_car_value)}</span>
                    </div>
                  </div>
                ) : (
                  <div className="text-center py-6 text-slate-300">
                    <div className="text-4xl mb-2">🚫</div>
                    <p className="text-sm">No vehicle</p>
                  </div>
                )}
              </Card>
            </div>

            {/* OCR Results */}
            {(result.ruhsat_ocr?.ocr_success || result.tapu_ocr?.ocr_success) && (
              <Card>
                <SectionTitle icon="🔍">OCR Extraction Results</SectionTitle>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  {result.ruhsat_ocr?.ocr_success && (
                    <div className="rounded-xl bg-blue-50 border border-blue-100 p-4">
                      <p className="text-xs font-bold text-blue-600 uppercase tracking-wide mb-3 flex items-center gap-1.5">
                        <span>📋</span> Ruhsat (Vehicle Reg.)
                      </p>
                      <div className="space-y-1.5 text-xs text-slate-600">
                        {[["Plate", result.ruhsat_ocr.plaka],["Brand", result.ruhsat_ocr.marka],
                          ["Year", result.ruhsat_ocr.yil],["Fuel", result.ruhsat_ocr.yakit_tipi],
                          ["Owner", result.ruhsat_ocr.sahip_adi]].map(([k, v]) => (
                          <div key={String(k)} className="flex justify-between">
                            <span className="text-slate-400">{String(k)}</span>
                            <span className="font-semibold">{v ? String(v) : "—"}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                  {result.tapu_ocr?.ocr_success && (
                    <div className="rounded-xl bg-emerald-50 border border-emerald-100 p-4">
                      <p className="text-xs font-bold text-emerald-600 uppercase tracking-wide mb-3 flex items-center gap-1.5">
                        <span>📄</span> Tapu (Title Deed)
                      </p>
                      <div className="space-y-1.5 text-xs text-slate-600">
                        {[["Province", result.tapu_ocr.il],["District", result.tapu_ocr.ilce],
                          ["Area", result.tapu_ocr.yuzolcumu ? `${result.tapu_ocr.yuzolcumu} m²` : null],
                          ["Type", result.tapu_ocr.nitelik],["Owner", result.tapu_ocr.malik]].map(([k, v]) => (
                          <div key={String(k)} className="flex justify-between">
                            <span className="text-slate-400">{String(k)}</span>
                            <span className="font-semibold">{v ? String(v) : "—"}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </Card>
            )}

            {/* Reasons */}
            <Card>
              <SectionTitle icon="📝">Scoring Reasons</SectionTitle>
              {result.reasons?.length > 0 ? (
                <ul className="space-y-2">
                  {result.reasons.map((r, i) => (
                    <li key={i} className="flex items-start gap-2 text-sm text-slate-700">
                      <span className="mt-0.5 text-indigo-400 shrink-0">•</span>
                      {r}
                    </li>
                  ))}
                </ul>
              ) : <p className="text-slate-400 text-sm">No reasons returned.</p>}
            </Card>

            {/* Report + New Analysis */}
            <div className="flex flex-col sm:flex-row gap-3">
              {result.report && (
                <a
                  href={`${process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:9001"}/${result.report}`}
                  target="_blank" rel="noreferrer"
                  className="flex-1 rounded-xl bg-gradient-to-r from-indigo-600 to-violet-600 text-white font-bold py-3.5 text-center hover:shadow-lg hover:shadow-indigo-200 transition-all text-sm"
                >
                  📄 Open PDF Report
                </a>
              )}
              <button
                onClick={() => { setResult(null); setStep(1) }}
                className="flex-1 rounded-xl border-2 border-slate-200 text-slate-600 font-semibold py-3.5 hover:border-slate-300 transition text-sm"
              >
                ← New Analysis
              </button>
            </div>
          </div>
        )}

      </main>

      {/* Footer */}
      <footer className="text-center py-6 text-xs text-slate-400 border-t border-slate-100 mt-4">
        <div className="flex items-center justify-center gap-2 mb-1">
          <BursIQLogo size={16} />
          <span className="font-semibold text-slate-500">BursIQ</span>
        </div>
        Scholarship Intelligence System · All decisions are advisory only.
      </footer>
    </div>
  )
}
