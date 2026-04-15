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

type Result = {
  application_id: number
  score: number
  priority: string
  decision: string
  reasons: string[]
  breakdown: Record<string, number>
  property_estimated_value?: number
  avg_m2_price?: number
  estimated_car_value?: number
}

const INCOME_OPTIONS = [
  { val: "under_5000",   label: "Under ₺5,000" },
  { val: "5000_10000",  label: "₺5,000 – ₺10,000" },
  { val: "10000_20000", label: "₺10,000 – ₺20,000" },
  { val: "20000_40000", label: "₺20,000 – ₺40,000" },
  { val: "over_40000",  label: "Over ₺40,000" },
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

const DOC_LABELS: Record<string, { label: string; icon: string }> = {
  car_file:            { label: "Vehicle Registration (Ruhsat)", icon: "🚗" },
  house_file:          { label: "Title Deed (Tapu)",             icon: "🏠" },
  transcript_file:     { label: "Transcript",                    icon: "📋" },
  income_file:         { label: "Income Statement",              icon: "💰" },
  student_certificate: { label: "Student Certificate",           icon: "🎓" },
  family_registry:     { label: "Family Registry",               icon: "👨‍👩‍👧" },
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
  const [result, setResult]  = useState<Result | null>(null)
  const [savedAt, setSavedAt] = useState<string | null>(null)

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

  function setFile(key: string, f: File | null) {
    setFiles(prev => {
      if (!f) { const n = { ...prev }; delete n[key]; return n }
      return { ...prev, [key]: f }
    })
  }

  async function handleSubmit() {
    if (!scholarship) return
    setLoading(true)
    try {
      const fd = new FormData()
      // identity
      ;["first_name","last_name","tc_no","birth_date","phone","email",
        "university","department","grade","gender"].forEach(k => {
        fd.append(k, values[k] || "")
      })
      // scholarship questions
      scholarship.config.questions.forEach(q => {
        fd.append(q.id, values[q.id] || (q.type === "yesno" ? "no" : ""))
      })
      // car/house sub-fields if needed
      ;["car_brand","car_model","car_year","car_damage",
        "city","district","square_meters"].forEach(k => {
        fd.append(k, values[k] || "")
      })
      // files
      scholarship.config.documents.forEach(docId => {
        if (files[docId]) fd.append(docId, files[docId])
      })

      const res = await fetch(`${API}/scholarship/${id}/apply`, { method: "POST", body: fd })
      if (!res.ok) throw new Error(await res.text())
      const data = await res.json()
      setResult(data)
      setStep(3)
      // Clear draft after successful submission
      try { localStorage.removeItem(DRAFT_KEY) } catch {}
    } catch (e) {
      alert("Submission error: " + e)
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
        <div className="max-w-2xl mx-auto">
          <div className="flex items-center justify-between mb-1">
            <a href="/" className="text-indigo-200 hover:text-white text-sm">← Home</a>
            <div className="flex items-center gap-3">
              {savedAt && (
                <span className="text-indigo-300 text-xs flex items-center gap-1">
                  <span>💾</span> Draft saved {savedAt}
                </span>
              )}
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

      <div className="max-w-2xl mx-auto px-4 py-8">

        {/* ── Step 0: Identity ── */}
        {step === 0 && (
          <div className="space-y-6">
            <div className="bg-white rounded-2xl border border-slate-100 shadow-sm p-6 space-y-4">
              <h2 className="font-black text-slate-800 text-lg">Your Information</h2>
              <div className="grid grid-cols-2 gap-4">
                {[
                  { id: "first_name", label: "First Name", req: true },
                  { id: "last_name",  label: "Last Name",  req: true },
                ].map(f => (
                  <div key={f.id}>
                    <label className="block text-xs font-semibold text-slate-600 mb-1">{f.label}{f.req && " *"}</label>
                    <input value={values[f.id] || ""} onChange={e => setVal(f.id, e.target.value)}
                      className="w-full border border-slate-200 rounded-xl px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-indigo-400" />
                  </div>
                ))}
              </div>
              {[
                { id: "tc_no",     label: "TC Identity No",  type: "text" },
                { id: "birth_date",label: "Date of Birth",   type: "date" },
                { id: "phone",     label: "Phone",           type: "tel" },
                { id: "email",     label: "Email",           type: "email" },
                { id: "university",label: "University",      type: "text" },
                { id: "department",label: "Department",      type: "text" },
              ].map(f => (
                <div key={f.id}>
                  <label className="block text-xs font-semibold text-slate-600 mb-1">{f.label}</label>
                  <input type={f.type} value={values[f.id] || ""} onChange={e => setVal(f.id, e.target.value)}
                    className="w-full border border-slate-200 rounded-xl px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-indigo-400" />
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

            <button
              onClick={() => goStep(1)}
              disabled={!values.first_name || !values.last_name}
              className="w-full rounded-xl bg-gradient-to-r from-indigo-600 to-violet-600 text-white font-bold py-3 disabled:opacity-50"
            >
              Next →
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
                    {q.label}{q.required && <span className="text-red-400 ml-1">*</span>}
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

                  {(q.type === "text" || q.type === "number") && (
                    <input
                      type={q.type === "number" ? "number" : "text"}
                      value={values[q.id] || ""}
                      onChange={e => setVal(q.id, e.target.value)}
                      placeholder={q.type === "number" ? "0" : ""}
                      className="w-full border border-slate-200 rounded-xl px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-indigo-400"
                    />
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

            <div className="flex gap-3">
              <button onClick={() => goStep(0)} className="flex-1 rounded-xl bg-slate-100 text-slate-700 font-semibold py-3 text-sm">← Back</button>
              <button onClick={() => goStep(2)} className="flex-1 rounded-xl bg-gradient-to-r from-indigo-600 to-violet-600 text-white font-bold py-3 text-sm">
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
                const meta = DOC_LABELS[docId] || { label: docId, icon: "📄" }
                const file = files[docId]
                return (
                  <div key={docId} className={`p-4 rounded-xl border-2 transition ${file ? "border-emerald-300 bg-emerald-50" : "border-slate-200"}`}>
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <span className="text-xl">{meta.icon}</span>
                        <span className="text-sm font-semibold text-slate-800">{meta.label}</span>
                      </div>
                      {file && <span className="text-xs text-emerald-600 font-semibold">✓ Uploaded</span>}
                    </div>
                    <label className="block cursor-pointer">
                      <div className={`border-2 border-dashed rounded-xl p-3 text-center text-xs transition
                        ${file ? "border-emerald-300 text-emerald-600" : "border-slate-300 text-slate-400 hover:border-indigo-300 hover:text-indigo-500"}`}>
                        {file ? file.name : "Click to select file (PDF or image)"}
                      </div>
                      <input type="file" accept=".pdf,.jpg,.jpeg,.png"
                        onChange={e => setFile(docId, e.target.files?.[0] || null)}
                        className="hidden" />
                    </label>
                  </div>
                )
              })}
            </div>

            <div className="flex gap-3">
              <button onClick={() => goStep(1)} className="flex-1 rounded-xl bg-slate-100 text-slate-700 font-semibold py-3 text-sm">← Back</button>
              <button
                onClick={handleSubmit}
                disabled={loading}
                className="flex-1 rounded-xl bg-gradient-to-r from-emerald-500 to-teal-500 text-white font-bold py-3 text-sm disabled:opacity-50"
              >
                {loading ? (
                  <span className="flex items-center justify-center gap-2">
                    <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                    Analyzing…
                  </span>
                ) : "Submit Application →"}
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
                {Object.entries(result.breakdown || {}).map(([key, val]) => (
                  <div key={key}>
                    <div className="flex justify-between text-xs mb-1">
                      <span className="text-slate-500 capitalize">{key.replace(/_/g, " ")}</span>
                      <span className={`font-bold ${Number(val) < 0 ? "text-red-500" : "text-indigo-600"}`}>
                        {Number(val) > 0 ? `+${val}` : val}
                      </span>
                    </div>
                    <div className="w-full bg-slate-100 rounded-full h-1.5">
                      <div
                        className={`h-1.5 rounded-full ${Number(val) < 0 ? "bg-red-400" : "bg-indigo-500"}`}
                        style={{ width: `${Math.min(Math.abs(Number(val)) * 3, 100)}%` }}
                      />
                    </div>
                  </div>
                ))}
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
