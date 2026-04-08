"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"

const API = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:9001"

// ── Types ────────────────────────────────────────────────────
type DocType =
  | "car_file" | "house_file" | "transcript_file" | "income_file"
  | "student_certificate" | "family_registry" | "disability_report"

type Question = {
  id: string
  label: string
  type: "yesno" | "text" | "number" | "select"
  options?: string[]
  required: boolean
}

type ScholarshipConfig = {
  name: string
  description: string
  slots: number
  deadline: string
  type: "financial" | "academic" | "both"
  financial_weight: number
  academic_weight: number
  documents: DocType[]
  questions: Question[]
}

const STEPS = ["Type & Info", "Criteria", "Documents", "Review & Create"]

const DOC_OPTIONS: { id: DocType; label: string; icon: string; desc: string }[] = [
  { id: "car_file",            label: "Vehicle Registration (Ruhsat)", icon: "🚗", desc: "For vehicle valuation via OCR" },
  { id: "house_file",          label: "Title Deed (Tapu)",             icon: "🏠", desc: "For property valuation via OCR" },
  { id: "transcript_file",     label: "Transcript / GPA",              icon: "📋", desc: "Academic grade report" },
  { id: "income_file",         label: "Income Statement",              icon: "💰", desc: "Family income document" },
  { id: "student_certificate", label: "Student Certificate",           icon: "🎓", desc: "Proof of enrollment" },
  { id: "family_registry",     label: "Family Registry (Nüfus)",       icon: "👨‍👩‍👧", desc: "Family size & structure" },
  { id: "disability_report",   label: "Disability/Health Report",      icon: "❤️", desc: "If health criteria applies" },
]

const FINANCIAL_QUESTIONS: Question[] = [
  { id: "monthly_income",    label: "Monthly Household Income",   type: "select", options: ["under_5000","5000_10000","10000_20000","20000_40000","over_40000"], required: true },
  { id: "family_size",       label: "Family Size",                type: "number", required: true },
  { id: "has_car",           label: "Does the family own a car?", type: "yesno",  required: true },
  { id: "has_house",         label: "Does the family own a house?", type: "yesno", required: true },
  { id: "is_renting",        label: "Currently renting?",         type: "yesno",  required: false },
  { id: "parents_divorced",  label: "Are parents divorced?",       type: "yesno",  required: false },
  { id: "father_working",    label: "Is father employed?",         type: "yesno",  required: false },
  { id: "mother_working",    label: "Is mother employed?",         type: "yesno",  required: false },
  { id: "everyone_healthy",  label: "Any chronic illness in family?", type: "yesno", required: false },
  { id: "siblings_count",    label: "Number of siblings",          type: "number", required: false },
  { id: "other_scholarship", label: "Already receiving a scholarship?", type: "yesno", required: false },
  { id: "works_part_time",   label: "Works part-time?",            type: "yesno",  required: false },
]

const ACADEMIC_QUESTIONS: Question[] = [
  { id: "gpa",            label: "GPA",                      type: "number",  required: true },
  { id: "gpa_system",     label: "GPA System (4 or 100)",    type: "select",  options: ["4","100"], required: true },
  { id: "has_research",   label: "Involved in research?",    type: "yesno",   required: false },
  { id: "has_award",      label: "Has academic award?",      type: "yesno",   required: false },
  { id: "language_level", label: "Foreign language level",   type: "select",  options: ["none","A1","A2","B1","B2","C1","C2"], required: false },
  { id: "has_activity",   label: "Active in student clubs?", type: "yesno",   required: false },
]

export default function SetupPage() {
  const router = useRouter()
  const [step, setStep] = useState(0)
  const [adminKey, setAdminKey] = useState("")
  const [keyErr, setKeyErr] = useState(false)
  const [authed, setAuthed] = useState(false)
  const [loading, setLoading] = useState(false)
  const [createdId, setCreatedId] = useState<string | null>(null)

  const [config, setConfig] = useState<ScholarshipConfig>({
    name: "",
    description: "",
    slots: 10,
    deadline: "",
    type: "financial",
    financial_weight: 100,
    academic_weight: 0,
    documents: [],
    questions: [],
  })

  function set<K extends keyof ScholarshipConfig>(key: K, val: ScholarshipConfig[K]) {
    setConfig(prev => ({ ...prev, [key]: val }))
  }

  function toggleDoc(id: DocType) {
    setConfig(prev => ({
      ...prev,
      documents: prev.documents.includes(id)
        ? prev.documents.filter(d => d !== id)
        : [...prev.documents, id],
    }))
  }

  function toggleQuestion(q: Question) {
    setConfig(prev => {
      const exists = prev.questions.find(x => x.id === q.id)
      return {
        ...prev,
        questions: exists
          ? prev.questions.filter(x => x.id !== q.id)
          : [...prev.questions, q],
      }
    })
  }

  function handleTypeChange(t: "financial" | "academic" | "both") {
    set("type", t)
    if (t === "financial") { set("financial_weight", 100); set("academic_weight", 0) }
    if (t === "academic")  { set("financial_weight", 0);   set("academic_weight", 100) }
    if (t === "both")      { set("financial_weight", 60);  set("academic_weight", 40) }
  }

  async function handleCreate() {
    setLoading(true)
    try {
      const res = await fetch(`${API}/scholarship/create?key=${adminKey}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: config.name,
          description: config.description,
          slots: config.slots,
          deadline: config.deadline,
          type: config.type,
          financial_weight: config.financial_weight,
          academic_weight: config.academic_weight,
          config: {
            questions: config.questions,
            documents: config.documents,
          },
        }),
      })
      if (!res.ok) { setKeyErr(true); setStep(0); return }
      const data = await res.json()
      setCreatedId(data.id)
    } catch {
      alert("Connection error")
    } finally {
      setLoading(false)
    }
  }

  // ── Auth Screen ──
  if (!authed) return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 to-indigo-950 flex items-center justify-center p-4">
      <div className="w-full max-w-sm bg-white rounded-2xl shadow-2xl p-8">
        <div className="text-center mb-6">
          <div className="text-4xl mb-2">🔐</div>
          <h1 className="text-2xl font-black text-slate-800">Scholarship Setup</h1>
          <p className="text-slate-400 text-sm mt-1">Admin access required to create a scholarship</p>
        </div>
        <input
          type="password"
          placeholder="Admin key..."
          value={adminKey}
          onChange={e => setAdminKey(e.target.value)}
          onKeyDown={e => e.key === "Enter" && setAuthed(true)}
          className={`w-full rounded-xl border-2 ${keyErr ? "border-red-400" : "border-slate-200"} px-4 py-3 outline-none focus:ring-2 focus:ring-indigo-400 text-sm mb-3`}
        />
        {keyErr && <p className="text-red-500 text-xs mb-3 text-center">Wrong key. Try again.</p>}
        <button
          onClick={() => { setKeyErr(false); setAuthed(true) }}
          disabled={!adminKey}
          className="w-full rounded-xl bg-gradient-to-r from-indigo-600 to-violet-600 text-white font-bold py-3 text-sm disabled:opacity-50"
        >
          Continue →
        </button>
        <a href="/" className="block text-center text-xs text-slate-400 mt-4 hover:text-slate-600">← Back to Home</a>
      </div>
    </div>
  )

  // ── Success Screen ──
  if (createdId) return (
    <div className="min-h-screen bg-gradient-to-br from-emerald-50 to-teal-50 flex items-center justify-center p-4">
      <div className="w-full max-w-md bg-white rounded-2xl shadow-2xl p-8 text-center">
        <div className="text-6xl mb-4">🎉</div>
        <h2 className="text-2xl font-black text-slate-800 mb-2">Scholarship Created!</h2>
        <p className="text-slate-500 text-sm mb-6">Share this link with applicants:</p>
        <div className="bg-indigo-50 border border-indigo-200 rounded-xl px-4 py-3 mb-2 font-mono text-sm text-indigo-700 break-all">
          {typeof window !== "undefined" ? `${window.location.origin}/apply/${createdId}` : `/apply/${createdId}`}
        </div>
        <div className="bg-slate-100 rounded-xl px-4 py-2 mb-6 text-xs text-slate-500">
          Scholarship ID: <span className="font-bold text-slate-700">{createdId}</span>
        </div>
        <div className="flex gap-3">
          <button
            onClick={() => navigator.clipboard.writeText(`${window.location.origin}/apply/${createdId}`)}
            className="flex-1 rounded-xl bg-indigo-600 text-white font-semibold py-3 text-sm"
          >
            📋 Copy Link
          </button>
          <a
            href="/admin"
            className="flex-1 rounded-xl bg-slate-100 text-slate-700 font-semibold py-3 text-sm text-center"
          >
            Admin Panel →
          </a>
        </div>
        <button
          onClick={() => { setCreatedId(null); setStep(0); setConfig({ name:"",description:"",slots:10,deadline:"",type:"financial",financial_weight:100,academic_weight:0,documents:[],questions:[] }) }}
          className="mt-3 text-xs text-slate-400 hover:text-slate-600"
        >
          Create another scholarship
        </button>
      </div>
    </div>
  )

  const allFinancialQ = config.type === "financial" || config.type === "both"
  const allAcademicQ  = config.type === "academic"  || config.type === "both"

  return (
    <div className="min-h-screen bg-slate-50">
      {/* Header */}
      <div className="bg-gradient-to-r from-indigo-700 to-violet-700 text-white px-6 py-4 flex items-center gap-4">
        <a href="/" className="text-indigo-200 hover:text-white text-sm">← Home</a>
        <div className="flex-1 text-center">
          <h1 className="text-lg font-black">Create Scholarship</h1>
        </div>
        <a href="/admin" className="text-indigo-200 hover:text-white text-sm">Admin →</a>
      </div>

      {/* Step bar */}
      <div className="flex justify-center gap-0 bg-white border-b border-slate-100 px-4 py-3 overflow-x-auto">
        {STEPS.map((s, i) => (
          <div key={i} className="flex items-center">
            <div
              className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-semibold transition cursor-pointer
                ${i === step ? "bg-indigo-100 text-indigo-700" : i < step ? "text-emerald-600" : "text-slate-400"}`}
              onClick={() => i < step && setStep(i)}
            >
              <span className={`w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-black
                ${i === step ? "bg-indigo-600 text-white" : i < step ? "bg-emerald-500 text-white" : "bg-slate-200 text-slate-500"}`}>
                {i < step ? "✓" : i + 1}
              </span>
              {s}
            </div>
            {i < STEPS.length - 1 && <div className="w-6 h-px bg-slate-200 mx-1" />}
          </div>
        ))}
      </div>

      <div className="max-w-2xl mx-auto px-4 py-8">

        {/* ── Step 0: Type & Info ── */}
        {step === 0 && (
          <div className="space-y-6">
            <div>
              <h2 className="text-xl font-black text-slate-800 mb-1">Scholarship Type & Info</h2>
              <p className="text-slate-500 text-sm">Define what this scholarship is for</p>
            </div>

            <div className="bg-white rounded-2xl border border-slate-100 shadow-sm p-6 space-y-4">
              <div>
                <label className="block text-sm font-semibold text-slate-700 mb-1.5">Scholarship Name *</label>
                <input
                  value={config.name}
                  onChange={e => set("name", e.target.value)}
                  placeholder="e.g. 2024 Financial Need Scholarship"
                  className="w-full border border-slate-200 rounded-xl px-4 py-2.5 text-sm outline-none focus:ring-2 focus:ring-indigo-400"
                />
              </div>
              <div>
                <label className="block text-sm font-semibold text-slate-700 mb-1.5">Description</label>
                <textarea
                  value={config.description}
                  onChange={e => set("description", e.target.value)}
                  placeholder="Who is eligible? What is the goal?"
                  rows={3}
                  className="w-full border border-slate-200 rounded-xl px-4 py-2.5 text-sm outline-none focus:ring-2 focus:ring-indigo-400 resize-none"
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-semibold text-slate-700 mb-1.5">Number of Slots</label>
                  <input
                    type="number"
                    value={config.slots}
                    onChange={e => set("slots", Number(e.target.value))}
                    className="w-full border border-slate-200 rounded-xl px-4 py-2.5 text-sm outline-none focus:ring-2 focus:ring-indigo-400"
                  />
                </div>
                <div>
                  <label className="block text-sm font-semibold text-slate-700 mb-1.5">Deadline</label>
                  <input
                    type="date"
                    value={config.deadline}
                    onChange={e => set("deadline", e.target.value)}
                    className="w-full border border-slate-200 rounded-xl px-4 py-2.5 text-sm outline-none focus:ring-2 focus:ring-indigo-400"
                  />
                </div>
              </div>
            </div>

            {/* Scholarship type */}
            <div className="bg-white rounded-2xl border border-slate-100 shadow-sm p-6">
              <h3 className="font-bold text-slate-700 mb-4">Scholarship Type</h3>
              <div className="grid grid-cols-3 gap-3">
                {([
                  { val: "financial", icon: "💸", title: "Financial Need", desc: "Based on economic situation" },
                  { val: "academic",  icon: "🎓", title: "Academic Merit", desc: "Based on GPA & achievements" },
                  { val: "both",      icon: "⚖️", title: "Both",           desc: "Weighted combination" },
                ] as const).map(opt => (
                  <button
                    key={opt.val}
                    onClick={() => handleTypeChange(opt.val)}
                    className={`p-4 rounded-xl border-2 text-center transition ${
                      config.type === opt.val
                        ? "border-indigo-500 bg-indigo-50"
                        : "border-slate-200 hover:border-indigo-300"
                    }`}
                  >
                    <div className="text-2xl mb-1">{opt.icon}</div>
                    <div className="font-bold text-sm text-slate-800">{opt.title}</div>
                    <div className="text-xs text-slate-500 mt-0.5">{opt.desc}</div>
                  </button>
                ))}
              </div>

              {config.type === "both" && (
                <div className="mt-5 p-4 bg-slate-50 rounded-xl">
                  <div className="flex justify-between text-sm font-semibold text-slate-700 mb-2">
                    <span>💸 Financial: {config.financial_weight}%</span>
                    <span>🎓 Academic: {config.academic_weight}%</span>
                  </div>
                  <input
                    type="range" min={0} max={100}
                    value={config.financial_weight}
                    onChange={e => {
                      const v = Number(e.target.value)
                      set("financial_weight", v)
                      set("academic_weight", 100 - v)
                    }}
                    className="w-full accent-indigo-600"
                  />
                  <div className="flex justify-between text-xs text-slate-400 mt-1">
                    <span>100% Financial</span><span>100% Academic</span>
                  </div>
                </div>
              )}
            </div>

            <button
              onClick={() => setStep(1)}
              disabled={!config.name}
              className="w-full rounded-xl bg-gradient-to-r from-indigo-600 to-violet-600 text-white font-bold py-3 disabled:opacity-50"
            >
              Next: Choose Criteria →
            </button>
          </div>
        )}

        {/* ── Step 1: Criteria / Questions ── */}
        {step === 1 && (
          <div className="space-y-6">
            <div>
              <h2 className="text-xl font-black text-slate-800 mb-1">Application Questions</h2>
              <p className="text-slate-500 text-sm">Select which questions applicants must answer</p>
            </div>

            {allFinancialQ && (
              <div className="bg-white rounded-2xl border border-slate-100 shadow-sm p-6">
                <h3 className="font-bold text-slate-700 mb-4 flex items-center gap-2"><span>💸</span> Financial Questions</h3>
                <div className="space-y-2">
                  {FINANCIAL_QUESTIONS.map(q => {
                    const checked = !!config.questions.find(x => x.id === q.id)
                    return (
                      <label key={q.id} className={`flex items-center gap-3 p-3 rounded-xl cursor-pointer transition ${checked ? "bg-indigo-50 border border-indigo-200" : "hover:bg-slate-50 border border-transparent"}`}>
                        <input type="checkbox" checked={checked} onChange={() => toggleQuestion(q)} className="accent-indigo-600 w-4 h-4" />
                        <div>
                          <div className="text-sm font-medium text-slate-800">{q.label}</div>
                          <div className="text-xs text-slate-400">{q.type === "yesno" ? "Yes/No" : q.type === "select" ? "Dropdown" : "Number"}{q.required ? " · Required" : ""}</div>
                        </div>
                      </label>
                    )
                  })}
                </div>
              </div>
            )}

            {allAcademicQ && (
              <div className="bg-white rounded-2xl border border-slate-100 shadow-sm p-6">
                <h3 className="font-bold text-slate-700 mb-4 flex items-center gap-2"><span>🎓</span> Academic Questions</h3>
                <div className="space-y-2">
                  {ACADEMIC_QUESTIONS.map(q => {
                    const checked = !!config.questions.find(x => x.id === q.id)
                    return (
                      <label key={q.id} className={`flex items-center gap-3 p-3 rounded-xl cursor-pointer transition ${checked ? "bg-indigo-50 border border-indigo-200" : "hover:bg-slate-50 border border-transparent"}`}>
                        <input type="checkbox" checked={checked} onChange={() => toggleQuestion(q)} className="accent-indigo-600 w-4 h-4" />
                        <div>
                          <div className="text-sm font-medium text-slate-800">{q.label}</div>
                          <div className="text-xs text-slate-400">{q.type === "yesno" ? "Yes/No" : q.type === "select" ? "Dropdown" : "Number"}{q.required ? " · Required" : ""}</div>
                        </div>
                      </label>
                    )
                  })}
                </div>
              </div>
            )}

            <div className="flex gap-3">
              <button onClick={() => setStep(0)} className="flex-1 rounded-xl bg-slate-100 text-slate-700 font-semibold py-3 text-sm">← Back</button>
              <button onClick={() => setStep(2)} className="flex-1 rounded-xl bg-gradient-to-r from-indigo-600 to-violet-600 text-white font-bold py-3 text-sm">
                Next: Documents →
              </button>
            </div>
          </div>
        )}

        {/* ── Step 2: Documents ── */}
        {step === 2 && (
          <div className="space-y-6">
            <div>
              <h2 className="text-xl font-black text-slate-800 mb-1">Required Documents</h2>
              <p className="text-slate-500 text-sm">Select which files applicants must upload</p>
            </div>

            <div className="bg-white rounded-2xl border border-slate-100 shadow-sm p-6">
              <div className="space-y-2">
                {DOC_OPTIONS.map(doc => {
                  const checked = config.documents.includes(doc.id)
                  return (
                    <label key={doc.id} className={`flex items-center gap-4 p-3 rounded-xl cursor-pointer transition ${checked ? "bg-indigo-50 border border-indigo-200" : "hover:bg-slate-50 border border-transparent"}`}>
                      <input type="checkbox" checked={checked} onChange={() => toggleDoc(doc.id)} className="accent-indigo-600 w-4 h-4" />
                      <span className="text-xl">{doc.icon}</span>
                      <div>
                        <div className="text-sm font-semibold text-slate-800">{doc.label}</div>
                        <div className="text-xs text-slate-400">{doc.desc}</div>
                      </div>
                    </label>
                  )
                })}
              </div>
            </div>

            <div className="flex gap-3">
              <button onClick={() => setStep(1)} className="flex-1 rounded-xl bg-slate-100 text-slate-700 font-semibold py-3 text-sm">← Back</button>
              <button onClick={() => setStep(3)} className="flex-1 rounded-xl bg-gradient-to-r from-indigo-600 to-violet-600 text-white font-bold py-3 text-sm">
                Review →
              </button>
            </div>
          </div>
        )}

        {/* ── Step 3: Review ── */}
        {step === 3 && (
          <div className="space-y-6">
            <div>
              <h2 className="text-xl font-black text-slate-800 mb-1">Review & Create</h2>
              <p className="text-slate-500 text-sm">Everything looks good? Create the scholarship.</p>
            </div>

            <div className="bg-white rounded-2xl border border-slate-100 shadow-sm p-6 space-y-4">
              <div className="flex justify-between">
                <span className="text-sm text-slate-500">Name</span>
                <span className="text-sm font-semibold text-slate-800">{config.name}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-sm text-slate-500">Type</span>
                <span className="text-sm font-semibold capitalize text-indigo-600">{config.type}</span>
              </div>
              {config.type === "both" && (
                <div className="flex justify-between">
                  <span className="text-sm text-slate-500">Weights</span>
                  <span className="text-sm font-semibold text-slate-700">💸 {config.financial_weight}% · 🎓 {config.academic_weight}%</span>
                </div>
              )}
              <div className="flex justify-between">
                <span className="text-sm text-slate-500">Slots</span>
                <span className="text-sm font-semibold text-slate-800">{config.slots}</span>
              </div>
              {config.deadline && (
                <div className="flex justify-between">
                  <span className="text-sm text-slate-500">Deadline</span>
                  <span className="text-sm font-semibold text-slate-800">{config.deadline}</span>
                </div>
              )}
              <div className="flex justify-between">
                <span className="text-sm text-slate-500">Questions</span>
                <span className="text-sm font-semibold text-slate-800">{config.questions.length} selected</span>
              </div>
              <div className="flex justify-between">
                <span className="text-sm text-slate-500">Documents</span>
                <span className="text-sm font-semibold text-slate-800">{config.documents.length} required</span>
              </div>
              {config.description && (
                <div>
                  <span className="text-sm text-slate-500">Description</span>
                  <p className="text-sm text-slate-700 mt-1">{config.description}</p>
                </div>
              )}
            </div>

            <div className="flex gap-3">
              <button onClick={() => setStep(2)} className="flex-1 rounded-xl bg-slate-100 text-slate-700 font-semibold py-3 text-sm">← Back</button>
              <button
                onClick={handleCreate}
                disabled={loading}
                className="flex-1 rounded-xl bg-gradient-to-r from-emerald-500 to-teal-500 text-white font-bold py-3 text-sm disabled:opacity-50"
              >
                {loading ? "Creating…" : "✅ Create Scholarship"}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
