"use client"

import { useState } from "react"

const API = process.env.NEXT_PUBLIC_API_URL || "https://bitirmeprojesi-gza2.onrender.com"

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
  weight: number
  answer_scores: Record<string, number>
  source?: string   // referans platform
  custom?: boolean  // manuel eklenen soru
}

type ScholarshipConfig = {
  name: string
  description: string
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

const OPTION_LABELS: Record<string, string> = {
  under_5000: "Under ₺5,000", "5000_10000": "₺5K–₺10K",
  "10000_20000": "₺10K–₺20K", "20000_40000": "₺20K–₺40K", over_40000: "Over ₺40K",
  "4": "4.0 Scale", "100": "100 Scale",
  none: "None", A1: "A1", A2: "A2", B1: "B1", B2: "B2", C1: "C1", C2: "C2",
  yes: "Yes", no: "No",
  "0h": "0 hours", "1_10h": "1–10 hrs", "11_50h": "11–50 hrs", "50h_plus": "50+ hrs",
  academia: "Academia", public_sector: "Public Sector", private_sector: "Private Sector",
  ngo: "NGO / Civil Society", entrepreneurship: "Entrepreneurship",
  same_city: "Same City", diff_city: "Different City", abroad: "Abroad", undecided: "Undecided",
  big_city: "Metropolitan", town: "Town / District", village: "Village / Rural",
  none_grad: "Nobody", one_grad: "1 person", two_plus_grad: "2+ people",
  own_device: "Own device", shared: "Shared device", school_only: "School only",
}

function defaultScores(q: Omit<Question, "weight" | "answer_scores">): Record<string, number> {
  if (q.type === "yesno") return { yes: 0, no: 0 }
  if (q.type === "select" && q.options) return Object.fromEntries(q.options.map(o => [o, 0]))
  if (q.type === "number") return { "0-2": 0, "3-4": 0, "5+": 0 }
  return {}
}

// ── Soru Havuzu ──────────────────────────────────────────────

type QTemplate = Omit<Question, "weight" | "answer_scores">

const FINANCIAL_QUESTIONS: QTemplate[] = [
  { id: "monthly_income",   label: "Monthly Household Income",        type: "select", options: ["under_5000","5000_10000","10000_20000","20000_40000","over_40000"], required: true,  source: "FAFSA / SAI" },
  { id: "family_size",      label: "Family Size",                     type: "number", required: true,  source: "FAFSA / SAI" },
  { id: "has_car",          label: "Does the family own a car?",      type: "yesno",  required: true,  source: "YTB / TR Standard" },
  { id: "has_house",        label: "Does the family own a house?",    type: "yesno",  required: true,  source: "YTB / TR Standard" },
  { id: "is_renting",       label: "Currently renting?",             type: "yesno",  required: false, source: "FAFSA / SAI" },
  { id: "parents_divorced", label: "Are parents divorced?",           type: "yesno",  required: false, source: "YTB / TR Standard" },
  { id: "father_working",   label: "Is father employed?",             type: "yesno",  required: false, source: "YTB / TR Standard" },
  { id: "mother_working",   label: "Is mother employed?",             type: "yesno",  required: false, source: "YTB / TR Standard" },
  { id: "everyone_healthy", label: "Any chronic illness in family?",  type: "yesno",  required: false, source: "YTB / TR Standard" },
  { id: "siblings_count",   label: "Number of siblings",              type: "number", required: false, source: "FAFSA / SAI" },
  { id: "other_scholarship",label: "Already receiving a scholarship?",type: "yesno",  required: false, source: "DAAD / Erasmus+" },
  { id: "works_part_time",  label: "Works part-time?",                type: "yesno",  required: false, source: "FAFSA / SAI" },
  // Yeni finansal sorular
  { id: "has_debt",         label: "Has regular debt/loan payments?", type: "yesno",  required: false, source: "ABD SAI Metodolojisi" },
  { id: "siblings_in_uni",  label: "Siblings currently in university?",type: "yesno", required: false, source: "ABD SAI Metodolojisi" },
  { id: "family_retired",   label: "Any retired family member?",      type: "yesno",  required: false, source: "ABD SAI Metodolojisi" },
  { id: "family_supporting",label: "Financially supporting family members?", type: "yesno", required: false, source: "ABD SAI Metodolojisi" },
  { id: "sudden_income_loss",label: "Major income loss in last year? (death, job loss, disaster)", type: "yesno", required: false, source: "AB Finansal Yardım Standartları" },
  { id: "has_disability",   label: "Chronic illness or disability?",  type: "yesno",  required: false, source: "AB Finansal Yardım Standartları" },
  { id: "family_needs_care",label: "Family member needing care due to illness/disability?", type: "yesno", required: false, source: "AB Finansal Yardım Standartları" },
  { id: "first_gen_grad",   label: "University graduates in family?", type: "select", options: ["none_grad","one_grad","two_plus_grad"], required: false, source: "ABD FAFSA — First Generation" },
  { id: "highschool_location",label: "High school location",          type: "select", options: ["big_city","town","village"], required: false, source: "ABD FAFSA — Geographic Disadvantage" },
  { id: "device_access",    label: "Internet & device access?",       type: "select", options: ["own_device","shared","school_only"], required: false, source: "Dijital Eşitsizlik — UNESCO 2024" },
]

const ACADEMIC_QUESTIONS: QTemplate[] = [
  { id: "gpa",            label: "GPA",                             type: "number", required: true,  source: "Erasmus+ / DAAD" },
  { id: "gpa_system",     label: "GPA System (4 or 100)",           type: "select", options: ["4","100"], required: true, source: "Erasmus+ / DAAD" },
  { id: "has_research",   label: "Involved in research?",           type: "yesno",  required: false, source: "Fulbright / DAAD" },
  { id: "has_award",      label: "Has academic award?",             type: "yesno",  required: false, source: "Rhodes / Gates Cambridge" },
  { id: "language_level", label: "Foreign language level",          type: "select", options: ["none","A1","A2","B1","B2","C1","C2"], required: false, source: "DAAD / Erasmus+" },
  { id: "has_activity",   label: "Active in student clubs?",        type: "yesno",  required: false, source: "Chevening / Commonwealth" },
  // Yeni akademik sorular
  { id: "has_lang_cert",  label: "Has international language certificate? (IELTS, TOEFL, DELF…)", type: "yesno", required: false, source: "DAAD / Erasmus+" },
  { id: "has_intl_exp",   label: "International education/internship/exchange experience?", type: "yesno", required: false, source: "DAAD / Erasmus+" },
  { id: "has_patent",     label: "Registered product, patent or original software?", type: "yesno", required: false, source: "TÜBİTAK Ekosistemi" },
  { id: "has_tubitak",    label: "Participated in TÜBİTAK / TEKNOFEST or similar?", type: "yesno", required: false, source: "TÜBİTAK Ekosistemi" },
]

const LEADERSHIP_QUESTIONS: QTemplate[] = [
  { id: "has_leadership_role", label: "Leadership role in student club/association?", type: "yesno", required: false, source: "Chevening / Rhodes / Gates Cambridge" },
  { id: "volunteer_hours",     label: "Volunteer activity hours in last 2 years",    type: "select", options: ["0h","1_10h","11_50h","50h_plus"], required: false, source: "Chevening / Gates Cambridge" },
  { id: "has_social_project",  label: "Independently started a social project? (NGO, campaign, initiative)", type: "yesno", required: false, source: "Gates Cambridge / Rhodes" },
  { id: "has_youth_platform",  label: "Represented at national/international youth platform? (Model UN, Parliament…)", type: "yesno", required: false, source: "Chevening / Commonwealth" },
  { id: "has_startup",         label: "Active business venture? (sole proprietorship, startup…)", type: "yesno", required: false, source: "TÜBİTAK Ekosistemi / Fulbright" },
]

const CAREER_QUESTIONS: QTemplate[] = [
  { id: "career_field",       label: "Target career field",                          type: "select", options: ["academia","public_sector","private_sector","ngo","entrepreneurship"], required: false, source: "Fulbright / YTB / Commonwealth" },
  { id: "post_grad_location", label: "Where plan to work after graduation?",         type: "select", options: ["same_city","diff_city","abroad","undecided"], required: false, source: "YTB / Commonwealth — Beyin Göçü Riski" },
]

// ── Ana Component ────────────────────────────────────────────
export default function SetupPage() {
  const [step, setStep]     = useState(0)
  const [qPhase, setQPhase] = useState<0 | 1>(0)
  const [loading, setLoading] = useState(false)
  const [createdId, setCreatedId] = useState<string | null>(null)

  // Manuel soru oluşturma state'i
  const [customForm, setCustomForm] = useState({
    label: "",
    type: "yesno" as Question["type"],
    options: [""],   // select tipi için
  })
  const [showCustomForm, setShowCustomForm] = useState(false)
  const [customCounter, setCustomCounter] = useState(0)

  const [config, setConfig] = useState<ScholarshipConfig>({
    name: "", description: "", deadline: "",
    type: "financial", financial_weight: 100, academic_weight: 0,
    documents: [], questions: [],
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

  function toggleQuestion(q: QTemplate) {
    setConfig(prev => {
      const exists = prev.questions.find(x => x.id === q.id)
      return {
        ...prev,
        questions: exists
          ? prev.questions.filter(x => x.id !== q.id)
          : [...prev.questions, { ...q, weight: 0, answer_scores: defaultScores(q) }],
      }
    })
  }

  function setQuestionWeight(id: string, weight: number) {
    setConfig(prev => ({
      ...prev,
      questions: prev.questions.map(q => q.id === id ? { ...q, weight } : q),
    }))
  }

  function setAnswerScore(qId: string, answerKey: string, score: number) {
    setConfig(prev => ({
      ...prev,
      questions: prev.questions.map(q =>
        q.id === qId ? { ...q, answer_scores: { ...q.answer_scores, [answerKey]: score } } : q
      ),
    }))
  }

  // Manuel soru ekleme
  function addCustomQuestion() {
    if (!customForm.label.trim()) return
    const id = `custom_${customCounter}`
    const options = customForm.type === "select"
      ? customForm.options.filter(o => o.trim())
      : undefined
    const newQ: Question = {
      id,
      label: customForm.label.trim(),
      type: customForm.type,
      options,
      required: false,
      weight: 0,
      answer_scores: defaultScores({ id, label: customForm.label, type: customForm.type, options, required: false }),
      source: "Custom",
      custom: true,
    }
    setConfig(prev => ({ ...prev, questions: [...prev.questions, newQ] }))
    setCustomCounter(c => c + 1)
    setCustomForm({ label: "", type: "yesno", options: [""] })
    setShowCustomForm(false)
  }

  function removeQuestion(id: string) {
    setConfig(prev => ({ ...prev, questions: prev.questions.filter(q => q.id !== id) }))
  }

  const totalWeight = config.questions.reduce((s, q) => s + (q.weight || 0), 0)
  const weightOk = Math.abs(totalWeight - 100) < 1

  function handleTypeChange(t: "financial" | "academic" | "both") {
    set("type", t)
    if (t === "financial") { set("financial_weight", 100); set("academic_weight", 0) }
    if (t === "academic")  { set("financial_weight", 0);   set("academic_weight", 100) }
    if (t === "both")      { set("financial_weight", 60);  set("academic_weight", 40) }
  }

  async function handleCreate() {
    setLoading(true)
    try {
      const res = await fetch(`${API}/scholarship/create`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: config.name, description: config.description, deadline: config.deadline,
          type: config.type, financial_weight: config.financial_weight, academic_weight: config.academic_weight,
          config: { questions: config.questions, documents: config.documents },
        }),
      })
      if (!res.ok) { alert(`Error ${res.status}: ${await res.text()}`); return }
      const data = await res.json()
      setCreatedId(data.id)
    } catch (e) {
      alert(`Connection error: ${e}\n\nAPI: ${API}`)
    } finally {
      setLoading(false)
    }
  }

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
          <button onClick={() => navigator.clipboard.writeText(`${window.location.origin}/apply/${createdId}`)}
            className="flex-1 rounded-xl bg-indigo-600 text-white font-semibold py-3 text-sm">
            📋 Copy Link
          </button>
          <a href="/admin" className="flex-1 rounded-xl bg-slate-100 text-slate-700 font-semibold py-3 text-sm text-center">Admin →</a>
        </div>
        <button
          onClick={() => { setCreatedId(null); setStep(0); setConfig({ name:"",description:"",deadline:"",type:"financial",financial_weight:100,academic_weight:0,documents:[],questions:[] }) }}
          className="mt-3 text-xs text-slate-400 hover:text-slate-600">
          Create another scholarship
        </button>
      </div>
    </div>
  )

  const showFinancial = config.type === "financial" || config.type === "both"
  const showAcademic  = config.type === "academic"  || config.type === "both"

  // Soru listesi bölümleri
  const Q_SECTIONS = [
    ...(showFinancial ? [{ title: "💸 Financial Questions", emoji: "💸", items: FINANCIAL_QUESTIONS }] : []),
    ...(showAcademic  ? [{ title: "🎓 Academic Questions",  emoji: "🎓", items: ACADEMIC_QUESTIONS  }] : []),
    { title: "🏆 Leadership & Social Impact", emoji: "🏆", items: LEADERSHIP_QUESTIONS },
    { title: "🎯 Career & Goals",             emoji: "🎯", items: CAREER_QUESTIONS },
  ]

  return (
    <div className="min-h-screen bg-slate-50">
      {/* Header */}
      <div className="bg-gradient-to-r from-indigo-700 to-violet-700 text-white px-6 py-4 flex items-center gap-4">
        <a href="/" className="text-indigo-200 hover:text-white text-sm">← Home</a>
        <div className="flex-1 text-center"><h1 className="text-lg font-black">Create Scholarship</h1></div>
        <a href="/admin" className="text-indigo-200 hover:text-white text-sm">Admin →</a>
      </div>

      {/* Step bar */}
      <div className="flex justify-center bg-white border-b border-slate-100 px-4 py-3 overflow-x-auto">
        {STEPS.map((s, i) => (
          <div key={i} className="flex items-center">
            <div className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-semibold cursor-pointer
              ${i === step ? "bg-indigo-100 text-indigo-700" : i < step ? "text-emerald-600" : "text-slate-400"}`}
              onClick={() => i < step && setStep(i)}>
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
                <input value={config.name} onChange={e => set("name", e.target.value)}
                  placeholder="e.g. 2024 Financial Need Scholarship"
                  className="w-full border border-slate-200 rounded-xl px-4 py-2.5 text-sm outline-none focus:ring-2 focus:ring-indigo-400" />
              </div>
              <div>
                <label className="block text-sm font-semibold text-slate-700 mb-1.5">Description</label>
                <textarea value={config.description} onChange={e => set("description", e.target.value)}
                  placeholder="Who is eligible? What is the goal?" rows={3}
                  className="w-full border border-slate-200 rounded-xl px-4 py-2.5 text-sm outline-none focus:ring-2 focus:ring-indigo-400 resize-none" />
              </div>
              <div>
                <label className="block text-sm font-semibold text-slate-700 mb-1.5">Deadline</label>
                <input type="date" value={config.deadline} onChange={e => set("deadline", e.target.value)}
                  className="w-full border border-slate-200 rounded-xl px-4 py-2.5 text-sm outline-none focus:ring-2 focus:ring-indigo-400" />
              </div>
            </div>

            <div className="bg-white rounded-2xl border border-slate-100 shadow-sm p-6">
              <h3 className="font-bold text-slate-700 mb-4">Scholarship Type</h3>
              <div className="grid grid-cols-3 gap-3">
                {([
                  { val: "financial", icon: "💸", title: "Financial Need", desc: "Based on economic situation" },
                  { val: "academic",  icon: "🎓", title: "Academic Merit", desc: "Based on GPA & achievements" },
                  { val: "both",      icon: "⚖️", title: "Both",           desc: "Weighted combination" },
                ] as const).map(opt => (
                  <button key={opt.val} onClick={() => handleTypeChange(opt.val)}
                    className={`p-4 rounded-xl border-2 text-center transition ${config.type === opt.val ? "border-indigo-500 bg-indigo-50" : "border-slate-200 hover:border-indigo-300"}`}>
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
                  <input type="range" min={0} max={100} value={config.financial_weight}
                    onChange={e => { const v = Number(e.target.value); set("financial_weight", v); set("academic_weight", 100 - v) }}
                    className="w-full accent-indigo-600" />
                  <div className="flex justify-between text-xs text-slate-400 mt-1">
                    <span>100% Financial</span><span>100% Academic</span>
                  </div>
                </div>
              )}
            </div>

            <button onClick={() => setStep(1)} disabled={!config.name}
              className="w-full rounded-xl bg-gradient-to-r from-indigo-600 to-violet-600 text-white font-bold py-3 disabled:opacity-50">
              Next: Choose Criteria →
            </button>
          </div>
        )}

        {/* ── Step 1 Phase 0: Soru Seç ── */}
        {step === 1 && qPhase === 0 && (
          <div className="space-y-6">
            <div>
              <h2 className="text-xl font-black text-slate-800 mb-1">Select Questions</h2>
              <p className="text-slate-500 text-sm">Choose which questions applicants will answer — then set weights & scores</p>
            </div>

            {/* Standart soru bölümleri */}
            {Q_SECTIONS.map(section => (
              <div key={section.title} className="bg-white rounded-2xl border border-slate-100 shadow-sm p-6">
                <h3 className="font-bold text-slate-700 mb-4">{section.title}</h3>
                <div className="space-y-2">
                  {section.items.map(q => {
                    const checked = !!config.questions.find(x => x.id === q.id)
                    return (
                      <label key={q.id} className={`flex items-start gap-3 p-3 rounded-xl cursor-pointer transition
                        ${checked ? "bg-indigo-50 border border-indigo-200" : "hover:bg-slate-50 border border-transparent"}`}>
                        <input type="checkbox" checked={checked} onChange={() => toggleQuestion(q)} className="accent-indigo-600 w-4 h-4 mt-0.5" />
                        <div className="flex-1">
                          <div className="text-sm font-medium text-slate-800">{q.label}</div>
                          <div className="flex items-center gap-2 mt-0.5">
                            <span className="text-xs text-slate-400">{q.type === "yesno" ? "Yes/No" : q.type === "select" ? "Dropdown" : "Number"}</span>
                            {q.source && (
                              <span className="text-[10px] bg-violet-100 text-violet-600 px-1.5 py-0.5 rounded-full font-medium">
                                📚 {q.source}
                              </span>
                            )}
                          </div>
                        </div>
                      </label>
                    )
                  })}
                </div>
              </div>
            ))}

            {/* Manuel soru ekleme */}
            <div className="bg-white rounded-2xl border border-slate-100 shadow-sm p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="font-bold text-slate-700">✏️ Custom Questions</h3>
                <button onClick={() => setShowCustomForm(v => !v)}
                  className="text-xs bg-indigo-600 text-white px-3 py-1.5 rounded-lg font-semibold hover:bg-indigo-700 transition">
                  {showCustomForm ? "Cancel" : "+ Add Custom Question"}
                </button>
              </div>

              {/* Mevcut custom sorular */}
              {config.questions.filter(q => q.custom).length === 0 && !showCustomForm && (
                <p className="text-slate-400 text-sm italic">No custom questions yet. Add your own question above.</p>
              )}
              {config.questions.filter(q => q.custom).map(q => (
                <div key={q.id} className="flex items-center gap-3 p-3 bg-violet-50 border border-violet-200 rounded-xl mb-2">
                  <div className="flex-1">
                    <div className="text-sm font-medium text-slate-800">{q.label}</div>
                    <div className="flex items-center gap-2 mt-0.5">
                      <span className="text-xs text-slate-400">{q.type === "yesno" ? "Yes/No" : q.type === "select" ? `Dropdown (${q.options?.join(", ")})` : q.type}</span>
                      <span className="text-[10px] bg-violet-100 text-violet-600 px-1.5 py-0.5 rounded-full font-medium">✏️ Custom</span>
                    </div>
                  </div>
                  <button onClick={() => removeQuestion(q.id)} className="text-red-400 hover:text-red-600 text-lg">×</button>
                </div>
              ))}

              {/* Custom soru formu */}
              {showCustomForm && (
                <div className="border border-indigo-200 bg-indigo-50 rounded-xl p-4 space-y-3">
                  <div>
                    <label className="text-xs font-semibold text-slate-600 block mb-1">Question Text *</label>
                    <input value={customForm.label} onChange={e => setCustomForm(f => ({ ...f, label: e.target.value }))}
                      placeholder="e.g. Do you have siblings in high school?"
                      className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-indigo-400 bg-white" />
                  </div>
                  <div>
                    <label className="text-xs font-semibold text-slate-600 block mb-1">Answer Type</label>
                    <div className="grid grid-cols-4 gap-2">
                      {(["yesno","select","number","text"] as const).map(t => (
                        <button key={t} onClick={() => setCustomForm(f => ({ ...f, type: t, options: [""] }))}
                          className={`py-1.5 rounded-lg border text-xs font-semibold transition ${customForm.type === t ? "border-indigo-500 bg-white text-indigo-700" : "border-slate-200 text-slate-500 hover:border-indigo-300"}`}>
                          {t === "yesno" ? "Yes/No" : t === "select" ? "Dropdown" : t === "number" ? "Number" : "Text"}
                        </button>
                      ))}
                    </div>
                  </div>

                  {customForm.type === "select" && (
                    <div>
                      <label className="text-xs font-semibold text-slate-600 block mb-1">Answer Options</label>
                      <div className="space-y-2">
                        {customForm.options.map((opt, idx) => (
                          <div key={idx} className="flex gap-2">
                            <input value={opt}
                              onChange={e => setCustomForm(f => { const o = [...f.options]; o[idx] = e.target.value; return { ...f, options: o } })}
                              placeholder={`Option ${idx + 1}`}
                              className="flex-1 border border-slate-200 rounded-lg px-3 py-1.5 text-sm outline-none focus:ring-1 focus:ring-indigo-400 bg-white" />
                            {customForm.options.length > 1 && (
                              <button onClick={() => setCustomForm(f => ({ ...f, options: f.options.filter((_, i) => i !== idx) }))}
                                className="text-red-400 hover:text-red-600 px-2">×</button>
                            )}
                          </div>
                        ))}
                        <button onClick={() => setCustomForm(f => ({ ...f, options: [...f.options, ""] }))}
                          className="text-xs text-indigo-600 hover:underline">+ Add option</button>
                      </div>
                    </div>
                  )}

                  <button onClick={addCustomQuestion} disabled={!customForm.label.trim()}
                    className="w-full bg-indigo-600 text-white rounded-lg py-2 text-sm font-semibold disabled:opacity-50 hover:bg-indigo-700 transition">
                    Add Question
                  </button>
                </div>
              )}
            </div>

            {/* Seçilen özet */}
            {config.questions.length > 0 && (
              <div className="bg-indigo-50 border border-indigo-100 rounded-xl p-3 text-sm text-indigo-700">
                {config.questions.length} question{config.questions.length > 1 ? "s" : ""} selected
                {config.questions.filter(q => q.custom).length > 0 && ` (${config.questions.filter(q => q.custom).length} custom)`}
              </div>
            )}

            <div className="flex gap-3">
              <button onClick={() => setStep(0)} className="flex-1 rounded-xl bg-slate-100 text-slate-700 font-semibold py-3 text-sm">← Back</button>
              <button onClick={() => setQPhase(1)} disabled={config.questions.length === 0}
                className="flex-1 rounded-xl bg-gradient-to-r from-indigo-600 to-violet-600 text-white font-bold py-3 text-sm disabled:opacity-50">
                Set Weights & Scores → ({config.questions.length} selected)
              </button>
            </div>
          </div>
        )}

        {/* ── Step 1 Phase 1: Ağırlık + Cevap Puanları ── */}
        {step === 1 && qPhase === 1 && (
          <div className="space-y-5">
            <div>
              <h2 className="text-xl font-black text-slate-800 mb-1">Weights & Answer Scores</h2>
              <p className="text-slate-500 text-sm">Set each question's weight and score per answer</p>
            </div>

            <div className={`rounded-2xl p-4 border-2 ${weightOk ? "border-emerald-300 bg-emerald-50" : "border-amber-300 bg-amber-50"}`}>
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-bold text-slate-700">Total Weight</span>
                <span className={`text-lg font-black ${weightOk ? "text-emerald-600" : "text-amber-600"}`}>
                  {totalWeight}% {weightOk ? "✅" : `— need ${100 - totalWeight > 0 ? `+${100 - totalWeight}` : 100 - totalWeight}% more`}
                </span>
              </div>
              <div className="w-full bg-white/70 rounded-full h-2.5">
                <div className={`h-2.5 rounded-full transition-all ${weightOk ? "bg-emerald-500" : totalWeight > 100 ? "bg-red-500" : "bg-amber-500"}`}
                  style={{ width: `${Math.min(totalWeight, 100)}%` }} />
              </div>
              <p className="text-xs text-slate-500 mt-1.5">Total must equal exactly 100% to use parametric scoring</p>
            </div>

            {config.questions.map((q, idx) => {
              const optionKeys = q.type === "yesno" ? ["yes","no"]
                : q.type === "select" && q.options ? q.options
                : Object.keys(q.answer_scores)

              return (
                <div key={q.id} className="bg-white rounded-2xl border border-slate-100 shadow-sm p-5">
                  <div className="flex items-start justify-between mb-4">
                    <div className="flex-1">
                      <span className="text-xs text-slate-400 font-mono">Q{idx + 1}</span>
                      <h3 className="font-bold text-slate-800 text-sm">{q.label}</h3>
                      <div className="flex items-center gap-2 mt-0.5">
                        <span className="text-xs text-slate-400">{q.type === "yesno" ? "Yes/No" : q.type === "select" ? "Dropdown" : q.type}</span>
                        {q.source && (
                          <span className="text-[10px] bg-violet-100 text-violet-600 px-1.5 py-0.5 rounded-full">
                            {q.custom ? "✏️ Custom" : `📚 ${q.source}`}
                          </span>
                        )}
                      </div>
                    </div>
                    <div className="text-right ml-3">
                      <label className="text-xs text-slate-500 block mb-1">Weight (%)</label>
                      <input type="number" min={0} max={100} value={q.weight}
                        onChange={e => setQuestionWeight(q.id, Math.max(0, Math.min(100, Number(e.target.value))))}
                        className="w-20 border-2 border-indigo-200 rounded-xl px-2 py-1.5 text-center text-sm font-black text-indigo-700 outline-none focus:ring-2 focus:ring-indigo-400" />
                    </div>
                  </div>

                  <div className="border-t border-slate-100 pt-3">
                    <p className="text-xs font-semibold text-slate-500 mb-2">Answer Scores (0 = lowest, 100 = highest need)</p>
                    <div className="space-y-2">
                      {optionKeys.map(opt => (
                        <div key={opt} className="flex items-center gap-3">
                          <span className="text-xs text-slate-700 flex-1 font-medium">{OPTION_LABELS[opt] || opt}</span>
                          <div className="flex items-center gap-2">
                            <input type="range" min={0} max={100} step={5}
                              value={q.answer_scores[opt] ?? 0}
                              onChange={e => setAnswerScore(q.id, opt, Number(e.target.value))}
                              className="w-28 accent-indigo-500" />
                            <span className={`w-10 text-center text-xs font-black rounded-lg px-1 py-0.5
                              ${(q.answer_scores[opt] ?? 0) >= 75 ? "bg-emerald-100 text-emerald-700"
                                : (q.answer_scores[opt] ?? 0) >= 40 ? "bg-amber-100 text-amber-700"
                                : "bg-red-50 text-red-500"}`}>
                              {q.answer_scores[opt] ?? 0}
                            </span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              )
            })}

            <div className="flex gap-3">
              <button onClick={() => setQPhase(0)} className="flex-1 rounded-xl bg-slate-100 text-slate-700 font-semibold py-3 text-sm">← Back</button>
              <button onClick={() => setStep(2)} disabled={!weightOk}
                className="flex-1 rounded-xl bg-gradient-to-r from-indigo-600 to-violet-600 text-white font-bold py-3 text-sm disabled:opacity-50">
                {weightOk ? "Next: Documents →" : `Total must be 100% (now ${totalWeight}%)`}
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
                    <label key={doc.id} className={`flex items-center gap-4 p-3 rounded-xl cursor-pointer transition
                      ${checked ? "bg-indigo-50 border border-indigo-200" : "hover:bg-slate-50 border border-transparent"}`}>
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
              <button onClick={() => setStep(3)} className="flex-1 rounded-xl bg-gradient-to-r from-indigo-600 to-violet-600 text-white font-bold py-3 text-sm">Review →</button>
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
              <div className="flex justify-between"><span className="text-sm text-slate-500">Name</span><span className="text-sm font-semibold text-slate-800">{config.name}</span></div>
              <div className="flex justify-between"><span className="text-sm text-slate-500">Type</span><span className="text-sm font-semibold capitalize text-indigo-600">{config.type}</span></div>
              {config.type === "both" && (
                <div className="flex justify-between"><span className="text-sm text-slate-500">Weights</span><span className="text-sm font-semibold text-slate-700">💸 {config.financial_weight}% · 🎓 {config.academic_weight}%</span></div>
              )}
              {config.deadline && (
                <div className="flex justify-between"><span className="text-sm text-slate-500">Deadline</span><span className="text-sm font-semibold text-slate-800">{config.deadline}</span></div>
              )}
              <div className="flex justify-between"><span className="text-sm text-slate-500">Questions</span><span className="text-sm font-semibold text-slate-800">{config.questions.length} selected ({config.questions.filter(q=>q.custom).length} custom)</span></div>
              {config.questions.length > 0 && (
                <div>
                  <span className="text-sm text-slate-500 block mb-1.5">Question Weights & Sources</span>
                  <div className="space-y-1.5">
                    {config.questions.map(q => (
                      <div key={q.id} className="flex items-center justify-between text-xs bg-slate-50 rounded-lg px-3 py-1.5">
                        <span className="text-slate-600 flex-1">{q.label}</span>
                        <div className="flex items-center gap-2">
                          {q.source && <span className="text-[10px] text-violet-500">{q.custom ? "✏️ Custom" : `📚 ${q.source}`}</span>}
                          <span className="font-bold text-indigo-600 w-10 text-right">{q.weight}%</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
              <div className="flex justify-between"><span className="text-sm text-slate-500">Documents</span><span className="text-sm font-semibold text-slate-800">{config.documents.length} required</span></div>
              {config.description && (
                <div><span className="text-sm text-slate-500">Description</span><p className="text-sm text-slate-700 mt-1">{config.description}</p></div>
              )}
            </div>
            <div className="flex gap-3">
              <button onClick={() => setStep(2)} className="flex-1 rounded-xl bg-slate-100 text-slate-700 font-semibold py-3 text-sm">← Back</button>
              <button onClick={handleCreate} disabled={loading}
                className="flex-1 rounded-xl bg-gradient-to-r from-emerald-500 to-teal-500 text-white font-bold py-3 text-sm disabled:opacity-50">
                {loading ? "Creating…" : "✅ Create Scholarship"}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
