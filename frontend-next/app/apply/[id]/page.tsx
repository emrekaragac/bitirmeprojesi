"use client"

import { useState, useEffect, useCallback, use } from "react"

const API = process.env.NEXT_PUBLIC_API_URL || "https://bitirmeprojesi-gza2.onrender.com"

// ── Types ────────────────────────────────────────────────────
type Question = {
  id: string
  label: string
  type: "yesno" | "text" | "number" | "select"
  options?: string[]
  required: boolean
}

type Scholarship = {
  id: string
  name: string
  description: string
  deadline: string
  type: "financial" | "academic" | "both"
  financial_weight: number
  academic_weight: number
  config: {
    questions: Question[]
    documents: string[]
  }
}

type BreakdownEntry = number | { weight: number; answer: string; score: number; points: number }

type Result = {
  application_id: number
  score: number
  priority: string
  decision: string
  reasons: string[]
  breakdown: Record<string, BreakdownEntry>
  property_estimated_value?: number
  avg_m2_price?: number
  estimated_car_value?: number
}

const INCOME_OPTIONS = [
  { val: "under_22000",   label: "Below ₺22,000 — below minimum wage" },
  { val: "22000_40000",   label: "₺22,000 – ₺40,000" },
  { val: "40000_75000",   label: "₺40,000 – ₺75,000" },
  { val: "75000_150000",  label: "₺75,000 – ₺150,000" },
  { val: "over_150000",   label: "Above ₺150,000" },
]

const GPA_SYSTEM_OPTIONS = [
  { val: "4",   label: "4.0 Scale" },
  { val: "100", label: "100 Scale" },
]

const LANG_OPTIONS = [
  { val: "none", label: "None" },
  { val: "A1", label: "A1 – Beginner" },
  { val: "A2", label: "A2 – Elementary" },
  { val: "B1", label: "B1 – Intermediate" },
  { val: "B2", label: "B2 – Upper Intermediate" },
  { val: "C1", label: "C1 – Advanced" },
  { val: "C2", label: "C2 – Proficient" },
]

// ── KVKK Metni ──────────────────────────────────────────────
const KVKK_TEXT = `BursIQ — Data Processing Consent

Data Controller: Parametric Scholarship Distribution System (BursIQ)
Scope: All personal data processed within the scope of the scholarship application
Legal Basis: Personal data protection regulations applicable to academic research systems

1. PERSONAL DATA COLLECTED

a) Identity & Contact Information
First name, last name, date of birth, email address, phone number, residential address.

b) Financial Data
Household income level, real estate ownership, vehicle ownership, debt obligations, number of family members and their income status. Declared vehicle and/or property details (brand, model, year, location) are processed alongside current market price data collected from public listing platforms for the purpose of asset valuation.

c) Academic Data
GPA, student transcript, scholarship and achievement certificates, language certificates, research activities.

d) Leadership & Social Impact Data
Association/club memberships, volunteer activities, entrepreneurship experience.

e) Uploaded Documents — OCR-Processed Data
Uploaded documents are processed via optical character recognition (OCR). The extracted data is used for cross-validation against form declarations; a trust score between 0–100 is calculated for each application.

2. PURPOSES OF DATA PROCESSING

• Receiving, evaluating, and concluding scholarship applications
• Verifying declared financial assets against current market data
• Auditing consistency between uploaded documents and form declarations
• Scoring applications according to the scholarship's weighted formula
• Displaying the ranked applicant list to system administrators

3. DATA RECIPIENTS

System Administration: Your application and score breakdown can only be viewed by BursIQ system administrators. Your data is not shared with any scholarship provider, foundation, or third-party institution.

Anthropic Inc. (International Transfer): During the financial asset valuation process, declared vehicle or property attributes (brand, model, year, location) are sent alongside public market data to the AI API (Claude) operated by Anthropic Inc., a company based in the United States. This transfer is solely for the purpose of market value estimation; your name, ID number, and contact details are not included.

Infrastructure Providers: Vercel (frontend hosting) and Render (backend hosting) act as technical data processors and cannot independently access your personal data.

4. RETENTION PERIOD

Your personal data will be retained for the period required by applicable regulations following the completion of the scholarship evaluation process, after which it will be securely deleted or anonymised.

5. YOUR RIGHTS

You have the right to: learn whether your personal data is being processed, request information about processed data, learn the purposes of processing, learn third parties to whom data is transferred, request correction of incomplete or inaccurate data, request deletion or destruction of data, object to outcomes arising from automated processing, and request compensation for damages arising from unlawful processing.

6. WITHDRAWAL OF CONSENT

You may withdraw your consent at any time. Withdrawal does not affect the lawfulness of prior data processing activities.

BursIQ — Management Information Systems, 2025–2026`

const CAR_BRANDS: Record<string, string[]> = {
  "Toyota":       ["Corolla", "Yaris", "Camry", "C-HR", "RAV4", "Land Cruiser", "Hilux", "Auris", "Prius", "Verso"],
  "Volkswagen":   ["Polo", "Golf", "Passat", "Tiguan", "T-Roc", "T-Cross", "Caddy", "Transporter", "Arteon"],
  "Renault":      ["Clio", "Megane", "Symbol", "Fluence", "Kadjar", "Captur", "Duster", "Taliant", "Zoe", "Talisman"],
  "Fiat":         ["Egea", "500", "Doblo", "Panda", "Tipo", "Fiorino", "Ducato"],
  "Ford":         ["Fiesta", "Focus", "Mondeo", "Kuga", "EcoSport", "Puma", "Ranger", "Transit", "Transit Connect"],
  "Hyundai":      ["i10", "i20", "i30", "Elantra", "Tucson", "Santa Fe", "Kona", "Bayon"],
  "Kia":          ["Picanto", "Rio", "Ceed", "Sportage", "Sorento", "Stonic", "Niro"],
  "BMW":          ["1 Serisi", "2 Serisi", "3 Serisi", "4 Serisi", "5 Serisi", "7 Serisi", "X1", "X2", "X3", "X5", "X6"],
  "Mercedes-Benz":["A Serisi", "B Serisi", "C Serisi", "E Serisi", "S Serisi", "GLA", "GLB", "GLC", "GLE", "GLS", "Vito"],
  "Audi":         ["A1", "A3", "A4", "A5", "A6", "A7", "A8", "Q2", "Q3", "Q5", "Q7", "Q8"],
  "Opel":         ["Corsa", "Astra", "Insignia", "Mokka", "Crossland", "Grandland", "Combo"],
  "Peugeot":      ["108", "208", "308", "408", "508", "2008", "3008", "5008", "Partner", "Expert"],
  "Citroen":      ["C1", "C3", "C4", "C5 Aircross", "Berlingo", "Jumpy"],
  "Dacia":        ["Sandero", "Logan", "Duster", "Jogger", "Spring", "Dokker"],
  "SEAT":         ["Ibiza", "Leon", "Arona", "Ateca", "Tarraco"],
  "Skoda":        ["Fabia", "Scala", "Octavia", "Superb", "Kamiq", "Karoq", "Kodiaq"],
  "Honda":        ["Jazz", "Civic", "Accord", "HR-V", "CR-V"],
  "Nissan":       ["Micra", "Note", "Juke", "Qashqai", "X-Trail", "Navara"],
  "Mazda":        ["Mazda2", "Mazda3", "Mazda6", "CX-3", "CX-5", "CX-30"],
  "Volvo":        ["V40", "V60", "V90", "S60", "S90", "XC40", "XC60", "XC90"],
  "Mitsubishi":   ["Colt", "Lancer", "Outlander", "Eclipse Cross", "ASX", "L200"],
  "Suzuki":       ["Alto", "Swift", "Baleno", "Vitara", "S-Cross", "Ignis"],
  "Subaru":       ["Impreza", "Forester", "Outback", "XV", "Legacy"],
  "Jeep":         ["Renegade", "Compass", "Cherokee", "Grand Cherokee", "Wrangler"],
  "Land Rover":   ["Defender", "Discovery", "Discovery Sport", "Range Rover", "Range Rover Sport", "Range Rover Evoque"],
  "Porsche":      ["911", "718 Boxster", "718 Cayman", "Cayenne", "Macan", "Panamera", "Taycan"],
  "TOGG":         ["T10X", "T10F"],
  "Tofaş":        ["Şahin", "Kartal", "Doğan", "Tempra"],
}

const DOC_LABELS: Record<string, { label: string; icon: string }> = {
  car_file:            { label: "Vehicle Registration (Ruhsat)", icon: "🚗" },
  house_file:          { label: "Title Deed (Tapu)",             icon: "🏠" },
  transcript_file:     { label: "Transcript",                    icon: "📋" },
  income_file:         { label: "Income Statement",              icon: "💰" },
disability_report:   { label: "Health/Disability Report",      icon: "❤️" },
}

const PRIORITY_STYLE: Record<string, string> = {
  "High Priority":   "bg-red-50 border-red-200 text-red-700",
  "Medium Priority": "bg-amber-50 border-amber-200 text-amber-700",
  "Low Priority":    "bg-emerald-50 border-emerald-200 text-emerald-700",
}
const DECISION_STYLE: Record<string, string> = {
  "Accepted":     "text-emerald-700 bg-emerald-100",
  "Under Review": "text-amber-700 bg-amber-100",
  "Rejected":     "text-red-700 bg-red-100",
}

function fmt(v?: number | null) {
  if (v == null) return "—"
  return new Intl.NumberFormat("tr-TR", { style: "currency", currency: "TRY", maximumFractionDigits: 0 }).format(v)
}

// ── Main Component ───────────────────────────────────────────
export default function ApplyPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params)
  const [scholarship, setScholarship] = useState<Scholarship | null>(null)
  const [notFound, setNotFound] = useState(false)
  const [step, setStep]   = useState(0)      // 0=identity, 1=questions, 2=docs, 3=result
  const [values, setValues] = useState<Record<string, string>>({})
  const [files, setFiles]   = useState<Record<string, File>>({})
  const [loading, setLoading] = useState(false)
  const [submitError, setSubmitError] = useState<string | null>(null)
  const [result, setResult]  = useState<Result | null>(null)
  const [savedAt, setSavedAt] = useState<string | null>(null)
  const [kvkkAccepted, setKvkkAccepted] = useState(false)
  const [kvkkOpen, setKvkkOpen] = useState(false)
  const [docValidation, setDocValidation] = useState<Record<string, {
    status: "checking" | "valid" | "invalid" | "unknown"
    message: string
    visionUnavailable?: boolean
    netAylik?: number
    nameMismatch?: boolean
    transcriptName?: string
  }>>({})


  const DRAFT_KEY = `psds_draft_${id}`

  // Load draft from localStorage on mount
  useEffect(() => {
    try {
      const raw = localStorage.getItem(DRAFT_KEY)
      if (raw) {
        const draft = JSON.parse(raw)
        if (draft.values) setValues(draft.values)
        if (typeof draft.step === "number" && draft.step < 3) setStep(draft.step)
        setSavedAt(draft.savedAt || null)
      }
    } catch {}
  }, [DRAFT_KEY])

  // Auto-save values + step to localStorage whenever they change
  const saveDraft = useCallback((vals: Record<string, string>, currentStep: number) => {
    try {
      const now = new Date().toLocaleTimeString("tr-TR", { hour: "2-digit", minute: "2-digit" })
      localStorage.setItem(DRAFT_KEY, JSON.stringify({ values: vals, step: currentStep, savedAt: now }))
      setSavedAt(now)
    } catch {}
  }, [DRAFT_KEY])

  useEffect(() => {
    fetch(`${API}/scholarship/${id}`)
      .then(r => { if (!r.ok) throw new Error(); return r.json() })
      .then(setScholarship)
      .catch(() => setNotFound(true))
  }, [id])

  function setVal(key: string, val: string) {
    setValues(prev => {
      const next = { ...prev, [key]: val }
      saveDraft(next, step)
      return next
    })
  }

  function goStep(s: number) {
    setStep(s)
    saveDraft(values, s)
  }

  async function setFile(key: string, f: File | null) {
    setFiles(prev => {
      if (!f) { const n = { ...prev }; delete n[key]; return n }
      return { ...prev, [key]: f }
    })
    if (!f) {
      setDocValidation(prev => { const n = { ...prev }; delete n[key]; return n })
      return
    }
    setDocValidation(prev => ({ ...prev, [key]: { status: "checking", message: "" } }))
    try {
      const fd = new FormData()
      fd.append("file", f)
      // Transkript için isim eşleşme kontrolü
      if (key === "transcript_file") {
        fd.append("first_name", values.first_name || "")
        fd.append("last_name",  values.last_name  || "")
      }
      const res = await fetch(`${API}/validate-document/${key}`, { method: "POST", body: fd })
      if (res.ok) {
        const data = await res.json()
        const isDefinitelyInvalid = data.valid === false && !data.vision_unavailable
        const visionUnavailable = !!data.vision_unavailable
        setDocValidation(prev => ({
          ...prev,
          [key]: {
            status: isDefinitelyInvalid ? "invalid" : data.valid ? "valid" : "unknown",
            message: data.message ?? "",
            visionUnavailable,
            ...(data.net_aylik != null ? { netAylik: data.net_aylik } : {}),
          },
        }))
        // Tapu için Vision'dan çıkarılan il/ilçe/m² bilgilerini otomatik doldur
        if (key === "house_file" && data.valid) {
          setValues(prev => ({
            ...prev,
            ...(data.il         && !prev.city          ? { city:          data.il }                : {}),
            ...(data.ilce       && !prev.district       ? { district:      data.ilce }              : {}),
            ...(data.yuzolcumu  && !prev.square_meters  ? { square_meters: String(data.yuzolcumu) } : {}),
          }))
        }
        // Transkript için Vision'dan çıkarılan GNO/sistem bilgilerini doldur — her yüklemede güncelle
        if (key === "transcript_file" && data.valid && data.gno != null) {
          setValues(prev => ({
            ...prev,
            gpa: String(data.gno),
            ...(data.sistem ? { gpa_system: String(data.sistem) } : {}),
          }))
        }
        // İsim uyumsuzluğunu state'e kaydet
        if (key === "transcript_file" && data.name_checked) {
          setDocValidation(prev => ({
            ...prev,
            [key]: {
              ...prev[key],
              nameMismatch:    data.name_match === false,
              transcriptName:  data.ogrenci_adi ?? undefined,
            },
          }))
        }
        if (key === "income_file" && data.valid && data.income_bracket) {
          setValues(prev => ({ ...prev, monthly_income: data.income_bracket }))
        }
      } else {
        setDocValidation(prev => ({
          ...prev,
          [key]: { status: "unknown", message: "⚠️ Validation service unavailable. Document accepted — will be reviewed manually.", visionUnavailable: true },
        }))
      }
    } catch {
      setDocValidation(prev => ({
        ...prev,
        [key]: { status: "unknown", message: "⚠️ Validation service unavailable. Document accepted — will be reviewed manually.", visionUnavailable: true },
      }))
    }
  }

  async function handleSubmit() {
    if (!scholarship) return
    setLoading(true)
    setSubmitError(null)
    try {
      const fd = new FormData()
      // identity
      ;["first_name","last_name","tc_no","birth_date","phone","email",
        "university","department","grade","gender"].forEach(k => {
        fd.append(k, values[k] || "")
      })
      // car/house sub-fields
      ;["car_brand","car_model","car_year","car_damage",
        "city","district","square_meters"].forEach(k => {
        fd.append(k, values[k] || "")
      })
      // financial/academic fields — always send even if not a scholarship question
      ;["monthly_income","gpa","gpa_system","family_size"].forEach(k => {
        fd.append(k, values[k] || "")
      })
      // scholarship questions — hem doğrudan ekle (eski alanlar için)
      // hem de extra_fields JSON olarak gönder (yeni/custom sorular backend'e ulaşsın)
      const extraFields: Record<string, string> = {}
      scholarship.config.questions.forEach(q => {
        const val = values[q.id] ?? (q.type === "yesno" ? "no" : "")
        fd.append(q.id, val)
        extraFields[q.id] = val
      })
      fd.append("extra_fields", JSON.stringify(extraFields))
      // Araç/tapu dosyası yüklendiyse has_car/has_house'u zorla "yes" yap
      // (scholarship'ta bu soru yoksa bile backend değer hesaplasın)
      if (files["car_file"])   fd.set("has_car",   "yes")
      if (files["house_file"]) fd.set("has_house", "yes")
      // files
      scholarship.config.documents.forEach(docId => {
        if (files[docId]) fd.append(docId, files[docId])
      })

      const res = await fetch(`${API}/scholarship/${id}/apply`, { method: "POST", body: fd })
      if (!res.ok) {
        const txt = await res.text().catch(() => `HTTP ${res.status}`)
        throw new Error(txt)
      }
      const data = await res.json()

      // ── RAG debug logları (browser console) ────────────────────────────
      // Sunucuda araç/konut değer tahmini nasıl yapıldı, hangi fiyatlar bulundu,
      // outlier filtresi sonrası ne kaldı, web_search mi yoksa fallback formül mü.
      try {
        console.log("[apply] full backend response:", data)
        const dbg = data?._rag_debug
        if (!dbg) {
          console.warn("[RAG] _rag_debug alanı yok — backend eski kod çalıştırıyor olabilir")
        }
        if (dbg) {
          console.groupCollapsed("%c[RAG] Değerleme debug", "color:#4f46e5;font-weight:bold")
          const tierLabel = (t: number | undefined) =>
            t === 1 ? "Tier 1: Gerçek ilanlar"
            : t === 2 ? "Tier 2: Claude segment tahmini"
            : "Tier 3: Marka/şehir formülü (fallback)"
          if (dbg.car) {
            console.groupCollapsed("ARAÇ")
            console.log("tier:", tierLabel(dbg.car.trace?.find((s: { tier?: number }) => s?.tier)?.tier))
            console.log("source:", dbg.car.source, "| confidence:", dbg.car.confidence)
            console.log("estimate:", dbg.car.estimate, "TL")
            console.log("raw_prices:", dbg.car.raw_prices)
            console.log("filtered_prices (IQR):", dbg.car.filtered_prices)
            console.log("reasoning:", dbg.car.reasoning)
            console.log("trace:", dbg.car.trace)
            if (dbg.car.error) console.error("error:", dbg.car.error)
            console.groupEnd()
          }
          if (dbg.property) {
            console.groupCollapsed("KONUT")
            console.log("tier:", tierLabel(dbg.property.trace?.find((s: { tier?: number }) => s?.tier)?.tier))
            console.log("source:", dbg.property.source, "| confidence:", dbg.property.confidence)
            console.log("estimate:", dbg.property.estimate, "TL  (m²:", dbg.property.m2_price, "TL)")
            console.log("raw_prices:", dbg.property.raw_prices)
            console.log("filtered_prices (IQR):", dbg.property.filtered_prices)
            console.log("reasoning:", dbg.property.reasoning)
            console.log("trace:", dbg.property.trace)
            if (dbg.property.error) console.error("error:", dbg.property.error)
            console.groupEnd()
          }
          console.groupEnd()
        }
      } catch {}

      setResult(data)
      setStep(3)
      try { localStorage.removeItem(DRAFT_KEY) } catch {}
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e)
      const isFetch = msg.toLowerCase().includes("fetch") || msg.toLowerCase().includes("network")
      setSubmitError(
        isFetch
          ? "Could not connect to the server. Please check your internet connection and try again."
          : `Submission error: ${msg.slice(0, 200)}`
      )
    } finally {
      setLoading(false)
    }
  }

  // ── Loading ──
  if (!scholarship && !notFound) return (
    <div className="min-h-screen flex items-center justify-center bg-slate-50">
      <div className="text-center">
        <div className="w-10 h-10 border-4 border-indigo-500 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
        <p className="text-slate-500 text-sm">Loading scholarship…</p>
      </div>
    </div>
  )

  // ── Not Found ──
  if (notFound) return (
    <div className="min-h-screen flex items-center justify-center bg-slate-50">
      <div className="text-center">
        <div className="text-5xl mb-4">❌</div>
        <h2 className="text-xl font-black text-slate-800 mb-2">Scholarship Not Found</h2>
        <p className="text-slate-500 text-sm mb-6">The ID <code className="bg-slate-100 px-2 py-0.5 rounded">{id}</code> does not exist.</p>
        <a href="/" className="text-indigo-600 text-sm font-semibold hover:underline">← Go Home</a>
      </div>
    </div>
  )

  const s = scholarship!
  const questions = s.config.questions || []
  const documents = s.config.documents || []
  const hasCarDoc   = documents.includes("car_file")
  const hasHouseDoc = documents.includes("house_file")

  // ── Steps ──
  const STEPS = ["Your Info", "Application", "Documents", "Result"]

  return (
    <div className="min-h-screen bg-slate-50">
      {/* Header */}
      <div className="bg-gradient-to-r from-indigo-700 to-violet-700 text-white px-6 py-4">
        <div className="max-w-5xl mx-auto">
          <div className="flex items-center justify-between mb-1">
            <a href="/" className="text-indigo-200 hover:text-white text-sm">← Home</a>
            <div className="flex items-center gap-3">
              {s.deadline && <span className="text-indigo-200 text-xs">Deadline: {s.deadline}</span>}
            </div>
          </div>
          <h1 className="text-xl font-black">{s.name}</h1>
          {s.description && <p className="text-indigo-200 text-sm mt-0.5">{s.description}</p>}
          <div className="flex gap-3 mt-2">
            <span className="bg-white/20 text-xs px-2 py-0.5 rounded-full capitalize">{s.type === "both" ? `${s.financial_weight}% Financial · ${s.academic_weight}% Academic` : s.type}</span>
          </div>
        </div>
      </div>

      {/* Step bar */}
      {step < 3 && (
        <div className="flex justify-center gap-0 bg-white border-b border-slate-100 px-4 py-3 overflow-x-auto">
          {STEPS.slice(0, 3).map((label, i) => (
            <div key={i} className="flex items-center">
              <div className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-semibold
                ${i === step ? "bg-indigo-100 text-indigo-700" : i < step ? "text-emerald-600" : "text-slate-400"}`}>
                <span className={`w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-black
                  ${i === step ? "bg-indigo-600 text-white" : i < step ? "bg-emerald-500 text-white" : "bg-slate-200 text-slate-500"}`}>
                  {i < step ? "✓" : i + 1}
                </span>
                {label}
              </div>
              {i < 2 && <div className="w-6 h-px bg-slate-200 mx-1" />}
            </div>
          ))}
        </div>
      )}

      <div className="max-w-5xl mx-auto px-6 py-8">

        {/* ── Step 0: Identity ── */}
        {step === 0 && (
          <div className="space-y-6">
            <div className="bg-white rounded-2xl border border-slate-100 shadow-sm p-6 space-y-4">
              <h2 className="font-black text-slate-800 text-lg">Personal Information</h2>

              {/* Ad / Soyad */}
              <div className="grid grid-cols-2 gap-4">
                {[
                  { id: "first_name", label: "First Name", req: true },
                  { id: "last_name",  label: "Last Name", req: true },
                ].map(f => (
                  <div key={f.id}>
                    <label className="block text-xs font-semibold text-slate-600 mb-1">{f.label}{f.req && " *"}</label>
                    <input value={values[f.id] || ""} onChange={e => setVal(f.id, e.target.value)}
                      className={`w-full border rounded-xl px-3 py-2 text-sm text-slate-900 outline-none focus:ring-2 focus:ring-indigo-400
                        ${values[f.id] ? "border-indigo-300" : "border-slate-200"}`} />
                  </div>
                ))}
              </div>

              {/* TC Kimlik */}
              <div>
                <label className="block text-xs font-semibold text-slate-600 mb-1">National ID No *</label>
                <input
                  type="text"
                  inputMode="numeric"
                  maxLength={11}
                  value={values["tc_no"] || ""}
                  onChange={e => setVal("tc_no", e.target.value.replace(/\D/g, "").slice(0, 11))}
                  className={`w-full border rounded-xl px-3 py-2 text-sm text-slate-900 outline-none focus:ring-2 focus:ring-indigo-400
                    ${values["tc_no"]
                      ? values["tc_no"].length === 11
                        ? "border-emerald-400"
                        : "border-red-300"
                      : "border-slate-200"}`}
                  placeholder="11-digit national ID number"
                />
                {values["tc_no"] && values["tc_no"].length !== 11 && (
                  <p className="text-xs text-red-500 font-medium mt-1">
                    ❌ National ID must be 11 digits ({values["tc_no"].length}/11)
                  </p>
                )}
              </div>

              {/* Diğer alanlar */}
              {[
                { id: "birth_date", label: "Date of Birth", type: "date" },
                { id: "phone",      label: "Phone",          type: "tel" },
              ].map(f => (
                <div key={f.id}>
                  <label className="block text-xs font-semibold text-slate-600 mb-1">{f.label}</label>
                  <input type={f.type} value={values[f.id] || ""} onChange={e => setVal(f.id, e.target.value)}
                    className={`w-full border rounded-xl px-3 py-2 text-sm text-slate-900 outline-none focus:ring-2 focus:ring-indigo-400
                      ${values[f.id] ? "border-indigo-300" : "border-slate-200"}`} />
                </div>
              ))}

              {/* Email — format kontrolü */}
              <div>
                <label className="block text-xs font-semibold text-slate-600 mb-1">Email *</label>
                <input
                  type="email"
                  value={values["email"] || ""}
                  onChange={e => setVal("email", e.target.value)}
                  placeholder="ornek@gmail.com"
                  className={`w-full border rounded-xl px-3 py-2 text-sm text-slate-900 outline-none focus:ring-2 focus:ring-indigo-400
                    ${values["email"]
                      ? /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(values["email"])
                        ? "border-emerald-400"
                        : "border-red-300"
                      : "border-slate-200"}`}
                />
                {values["email"] && !values["email"].includes("@") && (
                  <p className="text-xs text-red-500 font-medium mt-1">❌ @ symbol required (e.g. example@gmail.com)</p>
                )}
                {values["email"] && values["email"].includes("@") && !/^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(values["email"]) && (
                  <p className="text-xs text-red-500 font-medium mt-1">❌ Enter a valid domain (e.g. @gmail.com)</p>
                )}
              </div>

              {[
                { id: "university", label: "University", type: "text" },
                { id: "department", label: "Department", type: "text" },
              ].map(f => (
                <div key={f.id}>
                  <label className="block text-xs font-semibold text-slate-600 mb-1">{f.label}</label>
                  <input type={f.type} value={values[f.id] || ""} onChange={e => setVal(f.id, e.target.value)}
                    className={`w-full border rounded-xl px-3 py-2 text-sm text-slate-900 outline-none focus:ring-2 focus:ring-indigo-400
                      ${values[f.id] ? "border-indigo-300" : "border-slate-200"}`} />
                </div>
              ))}
              <div>
                <label className="block text-xs font-semibold text-slate-600 mb-1">Grade / Year</label>
                <select value={values.grade || ""} onChange={e => setVal("grade", e.target.value)}
                  className="w-full border border-slate-200 rounded-xl px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-indigo-400 bg-white">
                  <option value="">Select…</option>
                  {["1","2","3","4","5"].map(g => <option key={g} value={g}>Year {g}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-600 mb-2">Gender</label>
                <div className="flex gap-2">
                  {["male","female","other"].map(g => (
                    <button key={g} onClick={() => setVal("gender", g)}
                      className={`flex-1 py-2 rounded-xl border-2 text-sm font-semibold capitalize transition
                        ${values.gender === g ? "border-indigo-500 bg-indigo-50 text-indigo-700" : "border-slate-200 text-slate-600 hover:border-indigo-300"}`}>
                      {g}
                    </button>
                  ))}
                </div>
              </div>
            </div>

            {/* KVKK Açık Rıza */}
            <div className="bg-white rounded-2xl border border-slate-100 shadow-sm p-5 space-y-3">
              <div className="flex items-center justify-between">
                <h3 className="font-bold text-slate-700 text-sm flex items-center gap-2">
                  <span>🔒</span> Data Privacy Consent
                </h3>
                <button
                  type="button"
                  onClick={() => setKvkkOpen(v => !v)}
                  className="text-xs text-indigo-600 font-semibold hover:underline"
                >
                  {kvkkOpen ? "Hide ▲" : "Read Policy ▼"}
                </button>
              </div>

              {kvkkOpen && (
                <div className="bg-slate-50 border border-slate-200 rounded-xl p-4 max-h-64 overflow-y-auto text-xs text-slate-600 leading-relaxed whitespace-pre-wrap font-mono">
                  {KVKK_TEXT}
                </div>
              )}

              <label className="flex items-start gap-3 cursor-pointer select-none">
                <input
                  type="checkbox"
                  checked={kvkkAccepted}
                  onChange={e => setKvkkAccepted(e.target.checked)}
                  className="mt-0.5 w-4 h-4 accent-indigo-600 shrink-0"
                />
                <span className="text-xs text-slate-600 leading-snug">
                  I confirm that I have read and understood the above notice and freely consent to the processing of my personal data for the stated purposes,{" "}
                  <span className="font-semibold">including international transfer to Anthropic Inc.</span>
                </span>
              </label>

              {!kvkkAccepted && (
                <p className="text-xs text-amber-600 font-medium">
                  ⚠️ You must accept the data privacy notice to continue.
                </p>
              )}
            </div>

            <button
              onClick={() => goStep(1)}
              disabled={
                !values.first_name || !values.last_name || !kvkkAccepted ||
                (!!values["tc_no"] && values["tc_no"].length !== 11) ||
                (!!values["email"] && !/^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(values["email"]))
              }
              className="w-full rounded-xl bg-gradient-to-r from-indigo-600 to-violet-600 text-white font-bold py-3 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Continue →
            </button>
          </div>
        )}

        {/* ── Step 1: Questions ── */}
        {step === 1 && (
          <div className="space-y-6">
            <div className="bg-white rounded-2xl border border-slate-100 shadow-sm p-6 space-y-5">
              <h2 className="font-black text-slate-800 text-lg">Application Questions</h2>

              {questions.length === 0 && (
                <p className="text-slate-400 text-sm italic">No additional questions required for this scholarship.</p>
              )}

              {questions.map(q => (
                <div key={q.id}>
                  <label className="block text-sm font-semibold text-slate-700 mb-1.5">
                    {q.label}<span className="text-red-400 ml-1">*</span>
                  </label>

                  {q.type === "yesno" && (
                    <div className="flex gap-2">
                      {["yes","no"].map(v => (
                        <button key={v} onClick={() => setVal(q.id, v)}
                          className={`flex-1 py-2 rounded-xl border-2 text-sm font-semibold capitalize transition
                            ${values[q.id] === v ? "border-indigo-500 bg-indigo-50 text-indigo-700" : "border-slate-200 text-slate-600 hover:border-indigo-300"}`}>
                          {v === "yes" ? "✅ Yes" : "❌ No"}
                        </button>
                      ))}
                    </div>
                  )}

                  {q.type === "select" && (
                    <select value={values[q.id] || ""} onChange={e => setVal(q.id, e.target.value)}
                      className="w-full border border-slate-200 rounded-xl px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-indigo-400 bg-white">
                      <option value="">Select…</option>
                      {q.id === "monthly_income" && INCOME_OPTIONS.map(o => <option key={o.val} value={o.val}>{o.label}</option>)}
                      {q.id === "gpa_system" && GPA_SYSTEM_OPTIONS.map(o => <option key={o.val} value={o.val}>{o.label}</option>)}
                      {q.id === "language_level" && LANG_OPTIONS.map(o => <option key={o.val} value={o.val}>{o.label}</option>)}
                      {q.options && !["monthly_income","gpa_system","language_level"].includes(q.id) &&
                        q.options.map(o => <option key={o} value={o}>{o}</option>)}
                    </select>
                  )}

                  {(q.type === "text" || q.type === "number") && q.id !== "gpa" && (
                    <input
                      type={q.type === "number" ? "number" : "text"}
                      value={values[q.id] || ""}
                      onChange={e => setVal(q.id, e.target.value)}
                      placeholder={q.type === "number" ? "0" : ""}
                      className="w-full border border-slate-200 rounded-xl px-3 py-2 text-sm text-slate-900 outline-none focus:ring-2 focus:ring-indigo-400"
                    />
                  )}

                  {/* GPA — önce scale seç, sonra enforce'lu input */}
                  {q.id === "gpa" && (
                    <div className="space-y-2">
                      <div className="flex gap-2">
                        {GPA_SYSTEM_OPTIONS.map(o => (
                          <button
                            key={o.val}
                            type="button"
                            onClick={() => {
                              setVal("gpa_system", o.val)
                              setVal("gpa", "") // scale değişince değeri sıfırla
                            }}
                            className={`flex-1 py-2 text-xs font-semibold rounded-xl border-2 transition
                              ${values["gpa_system"] === o.val
                                ? "border-indigo-500 bg-indigo-50 text-indigo-700"
                                : "border-slate-200 bg-white text-slate-500 hover:border-indigo-300"}`}
                          >
                            {o.label}
                          </button>
                        ))}
                      </div>
                      <input
                        type="number"
                        value={values[q.id] || ""}
                        min={0}
                        max={values["gpa_system"] === "4" ? 4 : 100}
                        step={values["gpa_system"] === "4" ? 0.01 : 1}
                        placeholder={
                          !values["gpa_system"]
                            ? "Select scale first"
                            : values["gpa_system"] === "4"
                              ? "0.00 – 4.00"
                              : "0 – 100"
                        }
                        disabled={!values["gpa_system"]}
                        onChange={e => {
                          const raw = e.target.value
                          if (raw === "" || raw === "-") { setVal(q.id, raw); return }
                          const num = parseFloat(raw)
                          if (isNaN(num)) return
                          const maxVal = values["gpa_system"] === "4" ? 4 : 100
                          setVal(q.id, String(Math.min(Math.max(num, 0), maxVal)))
                        }}
                        className={`w-full border rounded-xl px-3 py-2 text-sm text-slate-900 outline-none focus:ring-2 focus:ring-indigo-400 disabled:opacity-40 disabled:cursor-not-allowed
                          ${values["gpa_system"] ? "border-indigo-300" : "border-slate-200"}`}
                      />
                      {values["gpa_system"] && values[q.id] && (
                        <p className="text-xs text-slate-400">
                          Max: <strong>{values["gpa_system"] === "4" ? "4.00" : "100"}</strong> — girilen: <strong className="text-indigo-600">{values[q.id]}</strong>
                        </p>
                      )}
                    </div>
                  )}

                  {/* Sub-fields for car */}
                  {q.id === "has_car" && values.has_car === "yes" && (
                    <div className="mt-3 grid grid-cols-3 gap-3 p-3 bg-slate-50 rounded-xl">
                      {[
                        { id: "car_brand", label: "Brand" },
                        { id: "car_model", label: "Model" },
                        { id: "car_year",  label: "Year" },
                      ].map(f => (
                        <div key={f.id}>
                          <label className="text-xs text-slate-500 block mb-1">{f.label}</label>
                          <input value={values[f.id] || ""} onChange={e => setVal(f.id, e.target.value)}
                            className="w-full border border-slate-200 rounded-lg px-2 py-1.5 text-xs outline-none focus:ring-1 focus:ring-indigo-400" />
                        </div>
                      ))}
                      <div className="col-span-3">
                        <label className="text-xs text-slate-500 block mb-1">Has damage?</label>
                        <div className="flex gap-2">
                          {["yes","no"].map(v => (
                            <button key={v} onClick={() => setVal("car_damage", v)}
                              className={`flex-1 py-1.5 rounded-lg border text-xs font-semibold transition
                                ${values.car_damage === v ? "border-indigo-400 bg-indigo-50 text-indigo-700" : "border-slate-200 text-slate-500"}`}>
                              {v === "yes" ? "Yes" : "No"}
                            </button>
                          ))}
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Sub-fields for house */}
                  {q.id === "has_house" && values.has_house === "yes" && (
                    <div className="mt-3 grid grid-cols-3 gap-3 p-3 bg-slate-50 rounded-xl">
                      {[
                        { id: "city",          label: "City" },
                        { id: "district",      label: "District" },
                        { id: "square_meters", label: "m²" },
                      ].map(f => (
                        <div key={f.id}>
                          <label className="text-xs text-slate-500 block mb-1">{f.label}</label>
                          <input value={values[f.id] || ""} onChange={e => setVal(f.id, e.target.value)}
                            className="w-full border border-slate-200 rounded-lg px-2 py-1.5 text-xs outline-none focus:ring-1 focus:ring-indigo-400" />
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>

            {/* Cevaplanmayan sorular uyarısı */}
            {questions.some(q => !values[q.id]) && (
              <p className="text-xs text-red-500 font-medium">
                ❗ Please answer all required questions.
              </p>
            )}

            <div className="flex gap-3">
              <button onClick={() => goStep(0)} className="flex-1 rounded-xl bg-slate-100 text-slate-700 font-semibold py-3 text-sm">← Back</button>
              <button
                onClick={() => goStep(2)}
                disabled={questions.some(q => !values[q.id])}
                className="flex-1 rounded-xl bg-gradient-to-r from-indigo-600 to-violet-600 text-white font-bold py-3 text-sm disabled:opacity-40 disabled:cursor-not-allowed"
              >
                Next: Documents →
              </button>
            </div>
          </div>
        )}

        {/* ── Step 2: Documents ── */}
        {step === 2 && (
          <div className="space-y-6">
            <div className="bg-white rounded-2xl border border-slate-100 shadow-sm p-6 space-y-4">
              <h2 className="font-black text-slate-800 text-lg">Upload Documents</h2>

              {documents.length === 0 && (
                <p className="text-slate-400 text-sm italic">No documents required for this scholarship.</p>
              )}

              {documents.map(docId => {
                // Engellilik raporu sadece "has_disability = yes" seçiliyse göster
                if (docId === "disability_report" && values["has_disability"] !== "yes") return null

                const meta   = DOC_LABELS[docId] || { label: docId, icon: "📄" }
                const file   = files[docId]
                const dv     = docValidation[docId]
                const status = dv?.status ?? "idle"

                const borderCls = !file ? "border-slate-200"
                  : status === "checking" ? "border-amber-300 bg-amber-50"
                  : status === "valid"    ? "border-emerald-300 bg-emerald-50"
                  : status === "invalid"  ? "border-red-300 bg-red-50"
                  : status === "unknown"  ? "border-amber-200 bg-amber-50"
                  : "border-slate-200"

                const fileCls = !file
                  ? "border-slate-300 text-slate-400 hover:border-indigo-300 hover:text-indigo-500"
                  : status === "checking" ? "border-amber-300 text-amber-600"
                  : status === "valid"    ? "border-emerald-300 text-emerald-600"
                  : status === "invalid"  ? "border-red-300 text-red-500"
                  : "border-amber-200 text-amber-600"

                return (
                  <div key={docId} className={`p-4 rounded-xl border-2 transition ${borderCls}`}>
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <span className="text-xl">{meta.icon}</span>
                        <span className="text-sm font-semibold text-slate-800">{meta.label}</span>
                      </div>
                      {file && (
                        status === "checking" ? (
                          <span className="flex items-center gap-1 text-xs text-amber-600 font-semibold">
                            <span className="w-3 h-3 border-2 border-amber-500 border-t-transparent rounded-full animate-spin" />
                            Verifying…
                          </span>
                        ) : status === "valid" ? (
                          <span className="text-xs text-emerald-600 font-semibold">✅ Valid</span>
                        ) : status === "invalid" ? (
                          <span className="text-xs text-red-600 font-semibold">❌ Invalid</span>
                        ) : (
                          <span className="text-xs text-amber-600 font-semibold">⚠️ Unverified</span>
                        )
                      )}
                    </div>
                    {/* Grading system selector for transcript — pick before uploading */}
                    {docId === "transcript_file" && (
                      <div className="mb-3 space-y-1">
                        <p className="text-xs font-semibold text-slate-600">Grading System (select first):</p>
                        <div className="flex gap-2">
                          {GPA_SYSTEM_OPTIONS.map(o => (
                            <button
                              key={o.val}
                              type="button"
                              onClick={() => setValues(p => ({ ...p, gpa_system: o.val }))}
                              className={`flex-1 py-1.5 text-xs font-semibold rounded-lg border-2 transition ${
                                values["gpa_system"] === o.val
                                  ? "border-indigo-500 bg-indigo-50 text-indigo-700"
                                  : "border-slate-200 bg-white text-slate-500 hover:border-indigo-300"
                              }`}
                            >
                              {o.label}
                            </button>
                          ))}
                        </div>
                      </div>
                    )}
                    {file ? (
                      <div className={`border-2 border-dashed rounded-xl px-3 py-2.5 flex items-center gap-2 ${fileCls}`}>
                        <span className="flex-1 text-xs text-slate-700 truncate min-w-0">{file.name}</span>
                        <label className="cursor-pointer shrink-0">
                          <span className="text-xs text-indigo-600 font-semibold hover:text-indigo-800 whitespace-nowrap px-2 py-1 rounded-lg hover:bg-indigo-50 transition">
                            🔄 Change
                          </span>
                          <input type="file" accept=".pdf"
                            onChange={e => setFile(docId, e.target.files?.[0] || null)}
                            className="hidden" />
                        </label>
                        <button
                          type="button"
                          onClick={() => setFile(docId, null)}
                          className="shrink-0 text-xs text-red-500 font-semibold hover:text-red-700 whitespace-nowrap px-2 py-1 rounded-lg hover:bg-red-50 transition"
                        >
                          🗑 Remove
                        </button>
                      </div>
                    ) : (
                      <label className="block cursor-pointer">
                        <div className={`border-2 border-dashed rounded-xl p-3 text-center text-xs transition ${fileCls}`}>
                          Click to select a PDF
                        </div>
                        <input type="file" accept=".pdf"
                          onChange={e => setFile(docId, e.target.files?.[0] || null)}
                          className="hidden" />
                      </label>
                    )}
                    {file && status !== "checking" && dv?.message && (
                      <p className={`mt-2 text-xs font-medium leading-snug
                        ${status === "valid" ? "text-emerald-700"
                        : status === "invalid" ? "text-red-600"
                        : "text-amber-700"}`}>
                        {dv.message}
                      </p>
                    )}

                    {/* Gelir belgesi — okunan net gelir göster */}
                    {file && status === "valid" && docId === "income_file" && docValidation[docId]?.netAylik && (
                      <p className="mt-2 text-xs font-semibold text-emerald-700">
                        💰 Detected monthly net: <strong>₺{Math.round(docValidation[docId].netAylik!).toLocaleString("en")}</strong>
                        {" "}— income bracket auto-selected
                      </p>
                    )}

                    {/* Transkript — okunan GNO göster */}
                    {file && status === "valid" && docId === "transcript_file" && values["gpa"] && (
                      <p className="mt-2 text-xs font-semibold text-emerald-700">
                        📊 Detected GPA: <strong>{values["gpa"]}</strong>
                        {values["gpa_system"] ? ` (${values["gpa_system"] === "4" ? "4.0 scale" : "100 scale"})` : ""}
                      </p>
                    )}

                    {/* Transkript — isim uyumsuzluğu uyarısı */}
                    {file && docId === "transcript_file" && docValidation[docId]?.nameMismatch === true && (
                      <div className="mt-2 bg-red-50 border border-red-200 rounded-xl p-3">
                        <p className="text-xs font-bold text-red-700 mb-0.5">
                          ⚠️ Name Mismatch
                        </p>
                        <p className="text-xs text-red-600 leading-snug">
                          The name on the transcript (<strong>{docValidation[docId].transcriptName}</strong>) does not match the name you entered.
                          Please upload your own transcript.
                        </p>
                      </div>
                    )}
                    {file && docId === "transcript_file" && docValidation[docId]?.nameMismatch === false && docValidation[docId]?.transcriptName && (
                      <p className="mt-1.5 text-xs text-emerald-700 font-medium">
                        ✅ Transcript owner verified: <strong>{docValidation[docId].transcriptName}</strong>
                      </p>
                    )}

                    {/* Manuel giriş — Vision okuyamadığında veya servis erişilemediğinde */}
                    {file && status !== "checking" && status !== "invalid" && (dv?.visionUnavailable || status === "unknown") && docId === "car_file" && (
                      <div className="mt-3 pt-3 border-t border-amber-200 space-y-2">
                        <p className="text-xs font-semibold text-amber-800">Enter vehicle details (for price estimation):</p>
                        <div className="grid grid-cols-2 gap-2">
                          {/* Marka */}
                          <select
                            className="col-span-1 px-2 py-1.5 text-xs border border-amber-300 rounded-lg bg-white focus:outline-none focus:ring-1 focus:ring-amber-400"
                            value={values["car_brand"] || ""}
                            onChange={e => setValues(p => ({ ...p, car_brand: e.target.value, car_model: "" }))}
                          >
                            <option value="">— Select brand —</option>
                            {Object.keys(CAR_BRANDS).sort().map(b => (
                              <option key={b} value={b}>{b}</option>
                            ))}
                          </select>
                          {/* Model — markaya göre dinamik */}
                          <select
                            className="col-span-1 px-2 py-1.5 text-xs border border-amber-300 rounded-lg bg-white focus:outline-none focus:ring-1 focus:ring-amber-400 disabled:opacity-40"
                            value={values["car_model"] || ""}
                            disabled={!values["car_brand"]}
                            onChange={e => setValues(p => ({ ...p, car_model: e.target.value }))}
                          >
                            <option value="">— Select model —</option>
                            {(CAR_BRANDS[values["car_brand"] || ""] || []).map(m => (
                              <option key={m} value={m}>{m}</option>
                            ))}
                          </select>
                          {/* Yıl */}
                          <select
                            className="col-span-1 px-2 py-1.5 text-xs border border-amber-300 rounded-lg bg-white focus:outline-none focus:ring-1 focus:ring-amber-400"
                            value={values["car_year"] || ""}
                            onChange={e => setValues(p => ({ ...p, car_year: e.target.value }))}
                          >
                            <option value="">— Year —</option>
                            {Array.from({ length: 30 }, (_, i) => 2025 - i).map(y => (
                              <option key={y} value={y}>{y}</option>
                            ))}
                          </select>
                          {/* Hasar */}
                          <select
                            className="col-span-1 px-2 py-1.5 text-xs border border-amber-300 rounded-lg bg-white focus:outline-none focus:ring-1 focus:ring-amber-400"
                            value={values["car_damage"] || "no"}
                            onChange={e => setValues(p => ({ ...p, car_damage: e.target.value }))}
                          >
                            <option value="no">No damage record</option>
                            <option value="yes">Has damage record</option>
                          </select>
                        </div>
                      </div>
                    )}

                    {file && status !== "checking" && status !== "invalid" && docId === "house_file" && (
                      <div className="mt-3 pt-3 border-t border-amber-200 space-y-2">
                        <p className="text-xs font-semibold text-amber-800">
                          {(dv?.visionUnavailable || status === "unknown")
                            ? "Enter property details manually:"
                            : "Details read from title deed (correct if needed):"}
                        </p>
                        <div className="grid grid-cols-2 gap-2">
                          <input
                            className="col-span-1 px-2 py-1.5 text-xs border border-amber-300 rounded-lg bg-white focus:outline-none focus:ring-1 focus:ring-amber-400"
                            placeholder="City (e.g. Istanbul)"
                            value={values["city"] || ""}
                            onChange={e => setValues(p => ({ ...p, city: e.target.value }))}
                          />
                          <input
                            className="col-span-1 px-2 py-1.5 text-xs border border-amber-300 rounded-lg bg-white focus:outline-none focus:ring-1 focus:ring-amber-400"
                            placeholder="District (e.g. Kadikoy)"
                            value={values["district"] || ""}
                            onChange={e => setValues(p => ({ ...p, district: e.target.value }))}
                          />
                          <input
                            className="col-span-2 px-2 py-1.5 text-xs border border-amber-300 rounded-lg bg-white focus:outline-none focus:ring-1 focus:ring-amber-400"
                            placeholder="Area (m²) e.g. 95"
                            type="number"
                            value={values["square_meters"] || ""}
                            onChange={e => setValues(p => ({ ...p, square_meters: e.target.value }))}
                          />
                        </div>
                      </div>
                    )}
                  </div>
                )
              })}
            </div>

            {/* Invalid document warning — blocks submission */}
            {Object.values(docValidation).some(v => v.status === "invalid") && (
              <div className="bg-red-50 border-2 border-red-300 rounded-xl p-4 text-sm text-red-700 space-y-1">
                <p className="font-bold">❌ Invalid document detected</p>
                <p>Please remove the documents marked in red and upload the correct ones. Submission is blocked until all documents are valid.</p>
              </div>
            )}

            {/* Submission error */}
            {submitError && (
              <div className="bg-red-50 border-2 border-red-300 rounded-xl p-4 space-y-2">
                <p className="text-sm font-bold text-red-700">❌ Submission failed</p>
                <p className="text-xs text-red-600">{submitError}</p>
                <button
                  onClick={handleSubmit}
                  className="mt-1 px-4 py-2 bg-red-600 hover:bg-red-700 text-white text-xs font-bold rounded-lg"
                >
                  Retry
                </button>
              </div>
            )}

            <div className="flex gap-3">
              <button onClick={() => goStep(1)} className="flex-1 rounded-xl bg-slate-100 text-slate-700 font-semibold py-3 text-sm">← Back</button>
              <button
                onClick={handleSubmit}
                disabled={
                  loading ||
                  Object.values(docValidation).some(v => v.status === "checking") ||
                  Object.values(docValidation).some(v => v.status === "invalid") ||
                  Object.values(docValidation).some(v => v.nameMismatch === true)
                }
                className="flex-1 rounded-xl bg-gradient-to-r from-emerald-500 to-teal-500 text-white font-bold py-3 text-sm disabled:opacity-40 disabled:cursor-not-allowed"
              >
                {loading ? (
                  <span className="flex items-center justify-center gap-2">
                    <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                    Analyzing…
                  </span>
                ) : Object.values(docValidation).some(v => v.status === "checking")
                  ? "Checking documents…"
                  : Object.values(docValidation).some(v => v.nameMismatch === true)
                  ? "Name mismatch — cannot submit"
                  : "Submit Application →"}
              </button>
            </div>
          </div>
        )}

        {/* ── Step 3: Result ── */}
        {step === 3 && result && (
          <div className="space-y-5">
            {/* Score hero */}
            <div className={`rounded-2xl border-2 p-6 ${PRIORITY_STYLE[result.priority] || "bg-slate-50 border-slate-200"}`}>
              <div className="flex items-center justify-between mb-4">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-widest opacity-70">Your Score</p>
                  <div className="text-6xl font-black">{result.score}<span className="text-2xl font-light opacity-50">/100</span></div>
                </div>
                <div className="text-right">
                  <div className={`px-4 py-2 rounded-xl text-sm font-black ${DECISION_STYLE[result.decision] || ""}`}>
                    {result.decision}
                  </div>
                  <p className="text-xs mt-1 opacity-70">{result.priority}</p>
                </div>
              </div>
              <div className="w-full bg-white/50 rounded-full h-3">
                <div
                  className={`h-3 rounded-full transition-all duration-700 ${
                    result.score >= 75 ? "bg-red-500" : result.score >= 50 ? "bg-amber-500" : "bg-emerald-500"
                  }`}
                  style={{ width: `${result.score}%` }}
                />
              </div>
            </div>

            {/* Score Breakdown */}
            <div className="bg-white rounded-2xl border border-slate-100 shadow-sm p-6">
              <h3 className="font-bold text-slate-700 mb-4">Score Breakdown</h3>
              <div className="space-y-3">
                {Object.entries(result.breakdown || {}).map(([key, val]) => {
                  // Parametric scoring returns objects; legacy scoring returns numbers
                  const isObj = typeof val === "object" && val !== null
                  const points = isObj ? (val as { points: number }).points : Number(val)
                  const score  = isObj ? (val as { score: number }).score  : Number(val)
                  const answer = isObj ? (val as { answer: string }).answer : undefined
                  const weight = isObj ? (val as { weight: number }).weight : undefined
                  const barPct = isObj
                    ? Math.min(Math.abs(score), 100)
                    : Math.min(Math.abs(points) * 3, 100)
                  return (
                    <div key={key}>
                      <div className="flex justify-between text-xs mb-1">
                        <span className="text-slate-500 capitalize">{key.replace(/_/g, " ")}</span>
                        <div className="text-right">
                          <span className={`font-bold ${points < 0 ? "text-red-500" : "text-indigo-600"}`}>
                            {points > 0 ? `+${points}` : points} pts
                          </span>
                          {answer !== undefined && (
                            <span className="ml-2 text-slate-400">({answer}{weight !== undefined ? `, w:${weight}%` : ""})</span>
                          )}
                        </div>
                      </div>
                      <div className="w-full bg-slate-100 rounded-full h-1.5">
                        <div
                          className={`h-1.5 rounded-full ${points < 0 ? "bg-red-400" : "bg-indigo-500"}`}
                          style={{ width: `${isNaN(barPct) ? 0 : barPct}%` }}
                        />
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>

            {/* Valuation Cards */}
            {(result.estimated_car_value || result.property_estimated_value) && (
              <div className="grid grid-cols-2 gap-4">
                {result.estimated_car_value && (
                  <div className="bg-white rounded-2xl border border-slate-100 shadow-sm p-4 text-center">
                    <div className="text-2xl mb-1">🚗</div>
                    <p className="text-xs text-slate-400 mb-1">Est. Car Value</p>
                    <p className="font-black text-indigo-700 text-sm">{fmt(result.estimated_car_value)}</p>
                  </div>
                )}
                {result.property_estimated_value && (
                  <div className="bg-white rounded-2xl border border-slate-100 shadow-sm p-4 text-center">
                    <div className="text-2xl mb-1">🏠</div>
                    <p className="text-xs text-slate-400 mb-1">Est. Property Value</p>
                    <p className="font-black text-indigo-700 text-sm">{fmt(result.property_estimated_value)}</p>
                  </div>
                )}
              </div>
            )}

            {/* Evaluation Notes */}
            <div className="bg-white rounded-2xl border border-slate-100 shadow-sm p-6">
              <h3 className="font-bold text-slate-700 mb-4">Evaluation Notes</h3>
              <ul className="space-y-2">
                {(result.reasons || []).map((r, i) => (
                  <li key={i} className="flex gap-2 text-sm text-slate-600">
                    <span className="text-indigo-400 shrink-0 mt-0.5">•</span>{r}
                  </li>
                ))}
              </ul>
            </div>

            <div className="bg-indigo-50 border border-indigo-100 rounded-xl p-4 text-center text-xs text-indigo-600">
              Application ID: <span className="font-bold">#{result.application_id}</span> — Keep this for your records
            </div>

            <a href="/" className="block text-center text-sm text-slate-400 hover:text-slate-600">← Back to Home</a>
          </div>
        )}
      </div>
    </div>
  )
}
