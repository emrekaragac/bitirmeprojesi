"use client"

import React, { useState } from "react"

const API = process.env.NEXT_PUBLIC_API_URL || "https://bitirmeprojesi-gza2.onrender.com"

const INCOME_LABELS: Record<string, string> = {
  under_5000:   "< ₺5K",
  "5000_10000": "₺5K–10K",
  "10000_20000":"₺10K–20K",
  "20000_40000":"₺20K–40K",
  over_40000:   "> ₺40K",
}

function fmt(v?: number | null) {
  if (v == null) return "—"
  return new Intl.NumberFormat("tr-TR", { style: "currency", currency: "TRY", maximumFractionDigits: 0 }).format(v)
}

type Scholarship = {
  id: string
  name: string
  description: string
  deadline: string
  type: string
  financial_weight: number
  academic_weight: number
  created_at: string
}

type App = {
  id: number
  scholarship_id: string
  submitted_at: string
  total_score: number
  priority: string
  decision: string
  first_name: string
  last_name: string
  university: string
  department: string
  gender: string
  reasons: string[]
  breakdown: Record<string, number>
  form_data: Record<string, string | number | null>
  needs_review?: boolean
  trust_score?: number
}

type VerificationFlag = {
  code: string
  severity: "high" | "medium"
  message: string
}

type Verification = {
  tc_valid: boolean | null
  tc_error: string | null
  trust_score: number
  trust_level: string
  needs_review: boolean
  flags: VerificationFlag[]
  notes: string[]
  passed_checks: string[]
  qr_car?: { found: boolean; is_official: boolean; data?: string } | null
  qr_house?: { found: boolean; is_official: boolean; data?: string } | null
}

type Detail = {
  id: number
  scholarship_id: string
  submitted_at: string
  total_score: number
  priority: string
  decision: string
  form_data: Record<string, string | number | null>
  scores: { reasons: string[]; breakdown: Record<string, number> }
  verification?: Verification
}

const PRIORITY_STYLE: Record<string, string> = {
  "High Priority":   "bg-red-100 text-red-700 border-red-200",
  "Medium Priority": "bg-amber-100 text-amber-700 border-amber-200",
  "Low Priority":    "bg-green-100 text-green-700 border-green-200",
}
const DECISION_STYLE: Record<string, string> = {
  "Accepted":     "bg-emerald-100 text-emerald-700",
  "Under Review": "bg-amber-100 text-amber-700",
  "Rejected":     "bg-red-100 text-red-600",
}
const TYPE_STYLE: Record<string, string> = {
  financial: "bg-blue-100 text-blue-700",
  academic:  "bg-violet-100 text-violet-700",
  both:      "bg-indigo-100 text-indigo-700",
}

export default function AdminPage() {
  const [key, setKey]       = useState("")
  const [authed, setAuthed] = useState(false)
  const [keyErr, setKeyErr] = useState(false)
  const [loading, setLoading] = useState(false)

  // Scholarship list
  const [scholarships, setScholarships] = useState<Scholarship[]>([])
  const [selectedScholarship, setSelectedScholarship] = useState<Scholarship | null>(null)

  // Applications for selected scholarship
  const [apps, setApps]     = useState<App[]>([])
  const [appsLoading, setAppsLoading] = useState(false)

  const [detail, setDetail] = useState<Detail | null>(null)
  const [search, setSearch] = useState("")

  async function login() {
    setLoading(true)
    setKeyErr(false)
    try {
      const r = await fetch(`${API}/admin/scholarships?key=${key}`)
      if (!r.ok) { setKeyErr(true); return }
      const data = await r.json()
      setScholarships(data)
      setAuthed(true)
    } catch {
      setKeyErr(true)
    } finally {
      setLoading(false)
    }
  }

  async function loadApps(s: Scholarship) {
    setSelectedScholarship(s)
    setAppsLoading(true)
    setApps([])
    setDetail(null)
    try {
      const r = await fetch(`${API}/admin/scholarships/${s.id}/applications?key=${key}`)
      if (r.ok) setApps(await r.json())
    } finally {
      setAppsLoading(false)
    }
  }

  async function loadDetail(id: number) {
    const r = await fetch(`${API}/admin/scholarship-applications/${id}?key=${key}`)
    if (r.ok) setDetail(await r.json())
  }

  const filtered = apps.filter(a =>
    !search ||
    a.id.toString().includes(search) ||
    (a.first_name || "").toLowerCase().includes(search.toLowerCase()) ||
    (a.last_name  || "").toLowerCase().includes(search.toLowerCase()) ||
    (a.university || "").toLowerCase().includes(search.toLowerCase())
  )

  // ── Login Screen ──
  if (!authed) return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 to-indigo-950 flex items-center justify-center p-4">
      <div className="w-full max-w-sm bg-white rounded-2xl shadow-2xl p-8">
        <div className="text-center mb-6">
          <div className="text-4xl mb-2">🔒</div>
          <h1 className="text-2xl font-black text-slate-800">PSDS Admin</h1>
          <p className="text-slate-400 text-sm mt-1">Enter admin password to continue</p>
        </div>
        <input
          type="password"
          placeholder="Admin key..."
          value={key}
          onChange={e => setKey(e.target.value)}
          onKeyDown={e => e.key === "Enter" && login()}
          className={`w-full rounded-xl border-2 ${keyErr ? "border-red-400" : "border-slate-200"} px-4 py-3 outline-none focus:ring-2 focus:ring-indigo-400 text-sm mb-3`}
        />
        {keyErr && <p className="text-red-500 text-xs mb-3 text-center">Wrong key. Try again.</p>}
        <button
          onClick={login}
          disabled={loading || !key}
          className="w-full rounded-xl bg-gradient-to-r from-indigo-600 to-violet-600 text-white font-bold py-3 text-sm disabled:opacity-50"
        >
          {loading ? "Connecting…" : "Enter"}
        </button>
        <a href="/" className="block text-center text-xs text-slate-400 mt-4 hover:text-slate-600">← Back to Home</a>
      </div>
    </div>
  )

  return (
    <div className="min-h-screen bg-slate-50">
      {/* Header */}
      <div className="bg-gradient-to-r from-indigo-700 to-violet-700 text-white px-6 py-4 flex items-center gap-4 shadow">
        <div>
          <h1 className="text-xl font-black">PSDS Admin Panel</h1>
          <p className="text-indigo-200 text-xs">{scholarships.length} scholarship(s) created</p>
        </div>
        <div className="ml-auto flex gap-3 items-center">
          <a href="/setup" className="text-xs bg-white/20 hover:bg-white/30 transition px-3 py-1.5 rounded-lg font-semibold">+ New Scholarship</a>
          <a href="/" className="text-xs text-indigo-200 hover:text-white transition">← Home</a>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 py-6">

        {/* ── Scholarship List ── */}
        {!selectedScholarship && (
          <div>
            <h2 className="text-lg font-black text-slate-800 mb-4">All Scholarships</h2>
            {scholarships.length === 0 ? (
              <div className="bg-white rounded-2xl border border-slate-100 shadow-sm p-12 text-center">
                <div className="text-4xl mb-3">📭</div>
                <p className="text-slate-400 text-sm">No scholarships yet.</p>
                <a href="/setup" className="inline-block mt-4 bg-indigo-600 text-white rounded-xl px-5 py-2.5 text-sm font-bold hover:bg-indigo-700 transition">
                  Create Your First Scholarship →
                </a>
              </div>
            ) : (
              <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
                {scholarships.map(s => (
                  <div key={s.id}
                    onClick={() => loadApps(s)}
                    className="bg-white rounded-2xl border border-slate-100 shadow-sm p-5 cursor-pointer hover:shadow-md hover:border-indigo-200 transition group"
                  >
                    <div className="flex items-start justify-between mb-3">
                      <div className={`text-xs font-semibold px-2 py-0.5 rounded-full capitalize ${TYPE_STYLE[s.type] || "bg-slate-100 text-slate-600"}`}>
                        {s.type === "both" ? `${s.financial_weight}% Fin · ${s.academic_weight}% Aca` : s.type}
                      </div>
                      <span className="font-mono text-xs text-slate-400 bg-slate-50 px-2 py-0.5 rounded">#{s.id}</span>
                    </div>
                    <h3 className="font-black text-slate-800 text-base mb-1 group-hover:text-indigo-700 transition">{s.name}</h3>
                    {s.description && <p className="text-slate-500 text-xs mb-3 line-clamp-2">{s.description}</p>}
                    <div className="flex items-center justify-between text-xs text-slate-400">
                      <span>{s.deadline || "No deadline"}</span>
                    </div>
                    <div className="mt-3 pt-3 border-t border-slate-100 flex items-center justify-between">
                      <span className="text-xs text-slate-400">{s.created_at.slice(0,10)}</span>
                      <span className="text-xs font-semibold text-indigo-600 group-hover:underline">View Applications →</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* ── Applications View ── */}
        {selectedScholarship && (
          <div>
            {/* Breadcrumb */}
            <div className="flex items-center gap-2 mb-5">
              <button onClick={() => { setSelectedScholarship(null); setApps([]) }}
                className="text-sm text-indigo-600 hover:underline font-semibold">
                ← All Scholarships
              </button>
              <span className="text-slate-400">/</span>
              <span className="text-sm font-semibold text-slate-800">{selectedScholarship.name}</span>
            </div>

            {/* Scholarship info */}
            <div className="bg-gradient-to-r from-indigo-50 to-violet-50 border border-indigo-100 rounded-2xl p-4 mb-5 flex flex-wrap gap-4 items-center justify-between">
              <div>
                <div className="font-black text-slate-800">{selectedScholarship.name}</div>
                <div className="text-xs text-slate-500 mt-0.5">
                  ID: <span className="font-mono font-semibold">{selectedScholarship.id}</span>
                  {selectedScholarship.deadline && ` · Deadline: ${selectedScholarship.deadline}`}
                </div>
              </div>
              <div className="flex gap-2 flex-wrap">
                <span className={`text-xs font-semibold px-2 py-1 rounded-full capitalize ${TYPE_STYLE[selectedScholarship.type] || ""}`}>
                  {selectedScholarship.type}
                </span>
                <button
                  onClick={() => navigator.clipboard.writeText(`${window.location.origin}/apply/${selectedScholarship.id}`)}
                  className="text-xs bg-white border border-indigo-200 text-indigo-600 px-3 py-1 rounded-full font-semibold hover:bg-indigo-50 transition"
                >
                  📋 Copy Apply Link
                </button>
              </div>
            </div>

            {/* Stats */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-5">
              {[
                { label: "Total",       val: apps.length,                                            color: "indigo" },
                { label: "Accepted",    val: apps.filter(a => a.decision === "Accepted").length,     color: "green"  },
                { label: "Under Review",val: apps.filter(a => a.decision === "Under Review").length, color: "amber"  },
                { label: "Avg Score",   val: apps.length ? Math.round(apps.reduce((s,a) => s + a.total_score, 0) / apps.length) : 0, color: "violet" },
              ].map(s => (
                <div key={s.label} className="bg-white rounded-2xl border border-slate-100 shadow-sm p-4 text-center">
                  <div className={`text-3xl font-black text-${s.color}-600`}>{s.val}</div>
                  <div className="text-xs text-slate-400 mt-1 font-medium">{s.label}</div>
                </div>
              ))}
            </div>

            {/* Search */}
            <div className="mb-4">
              <input
                type="text"
                placeholder="Search by name or university…"
                value={search}
                onChange={e => setSearch(e.target.value)}
                className="rounded-xl border border-slate-200 px-4 py-2 text-sm outline-none focus:ring-2 focus:ring-indigo-400 w-full sm:w-72"
              />
            </div>

            {/* Table */}
            {appsLoading ? (
              <div className="text-center py-16 text-slate-400 text-sm">Loading applications…</div>
            ) : (
              <div className="bg-white rounded-2xl border border-slate-100 shadow-sm overflow-hidden">
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="bg-slate-50 border-b border-slate-100">
                        {["#ID","Name","University","Date","Score","Priority","Decision","Gender","Trust","Action"].map(h => (
                          <th key={h} className="px-4 py-3 text-left text-xs font-bold text-slate-500 uppercase tracking-wide whitespace-nowrap">{h}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {filtered.map((a, i) => (
                        <tr key={a.id} className={`border-b border-slate-50 hover:bg-indigo-50/30 transition ${i % 2 === 0 ? "" : "bg-slate-50/30"}`}>
                          <td className="px-4 py-3 font-mono text-slate-400 text-xs">#{a.id}</td>
                          <td className="px-4 py-3">
                            <div className="font-semibold text-slate-800 text-sm whitespace-nowrap">
                              {a.first_name || a.last_name ? `${a.first_name} ${a.last_name}`.trim() : "—"}
                            </div>
                          </td>
                          <td className="px-4 py-3 text-slate-600 text-xs whitespace-nowrap">{a.university || "—"}</td>
                          <td className="px-4 py-3 text-slate-500 text-xs whitespace-nowrap">{a.submitted_at.slice(0,16)}</td>
                          <td className="px-4 py-3">
                            <span className={`text-xl font-black ${a.total_score >= 75 ? "text-red-600" : a.total_score >= 50 ? "text-amber-600" : "text-green-600"}`}>
                              {a.total_score}
                            </span>
                          </td>
                          <td className="px-4 py-3">
                            <span className={`text-xs font-semibold px-2 py-1 rounded-full border ${PRIORITY_STYLE[a.priority] || "bg-slate-100 text-slate-600"}`}>
                              {a.priority}
                            </span>
                          </td>
                          <td className="px-4 py-3">
                            <span className={`text-xs font-semibold px-2 py-1 rounded-full ${DECISION_STYLE[a.decision] || ""}`}>
                              {a.decision}
                            </span>
                          </td>
                          <td className="px-4 py-3 capitalize text-slate-700">{a.gender || "—"}</td>
                          <td className="px-4 py-3">
                            {a.needs_review
                              ? <span className="text-xs bg-red-100 text-red-600 font-semibold px-2 py-0.5 rounded-full">⚠️ Review</span>
                              : a.trust_score != null
                              ? <span className="text-xs bg-emerald-100 text-emerald-700 font-semibold px-2 py-0.5 rounded-full">✓ {a.trust_score}</span>
                              : <span className="text-xs text-slate-400">—</span>
                            }
                          </td>
                          <td className="px-4 py-3">
                            <button
                              onClick={() => loadDetail(a.id)}
                              className="text-xs text-indigo-600 font-semibold hover:underline whitespace-nowrap"
                            >
                              Details →
                            </button>
                          </td>
                        </tr>
                      ))}
                      {filtered.length === 0 && (
                        <tr><td colSpan={9} className="text-center text-slate-400 py-12 text-sm">No applications yet.</td></tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Detail Modal */}
      {detail && (() => {
        const fd = detail.form_data
        const v  = detail.verification
        const score = detail.total_score

        const INCOME_MAP: Record<string, string> = {
          under_5000:    "< ₺5,000",
          "5000_10000":  "₺5K – ₺10K",
          "10000_20000": "₺10K – ₺20K",
          "20000_40000": "₺20K – ₺40K",
          "40000_75000": "₺40K – ₺75K",
          over_40000:    "> ₺40,000",
          over_75000:    "> ₺75,000",
        }

        const PRIORITY_BADGE: Record<string, string> = {
          "High Priority":   "bg-red-500/20 text-red-200 border border-red-400/40",
          "Medium Priority": "bg-amber-400/20 text-amber-200 border border-amber-400/40",
          "Low Priority":    "bg-emerald-500/20 text-emerald-200 border border-emerald-400/40",
        }
        const DECISION_BADGE: Record<string, string> = {
          "Accepted":     "bg-emerald-100 text-emerald-700",
          "Under Review": "bg-amber-100 text-amber-700",
          "Rejected":     "bg-red-100 text-red-600",
        }

        const YesNo = ({ val }: { val: unknown }) => {
          const s = String(val ?? "").toLowerCase()
          if (s === "yes") return <span className="inline-flex items-center gap-1 text-xs bg-emerald-100 text-emerald-700 font-semibold px-2 py-0.5 rounded-full">✓ Yes</span>
          if (s === "no")  return <span className="inline-flex items-center gap-1 text-xs bg-slate-100 text-slate-400 font-semibold px-2 py-0.5 rounded-full">✗ No</span>
          return <span className="text-slate-600 text-sm font-medium">{String(val ?? "—")}</span>
        }

        const Row = ({ label, children }: { label: string; children: React.ReactNode }) => (
          <div className="flex items-center justify-between py-2.5 border-b border-slate-100 last:border-0">
            <span className="text-xs text-slate-400 font-medium shrink-0 mr-4">{label}</span>
            <div className="text-sm font-semibold text-slate-700 text-right">{children}</div>
          </div>
        )

        const Section = ({ title, children }: { title: string; children: React.ReactNode }) => (
          <div className="bg-slate-50 rounded-2xl p-4">
            <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-3">{title}</p>
            {children}
          </div>
        )

        const scoreColor = score >= 75 ? "text-red-500" : score >= 50 ? "text-amber-500" : "text-emerald-500"
        const scoreRing  = score >= 75 ? "border-red-400" : score >= 50 ? "border-amber-400" : "border-emerald-400"

        return (
          <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4" onClick={() => setDetail(null)}>
            <div className="bg-white rounded-3xl shadow-2xl w-full max-w-2xl max-h-[92vh] overflow-y-auto" onClick={e => e.stopPropagation()}>

              {/* ── Hero Header ── */}
              <div className="bg-gradient-to-br from-indigo-600 via-violet-600 to-purple-700 px-7 pt-7 pb-6 rounded-t-3xl text-white">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <p className="text-indigo-300 text-[10px] font-bold uppercase tracking-widest mb-1">Application #{detail.id}</p>
                    <h2 className="text-2xl font-black leading-tight truncate">
                      {`${fd.first_name ?? ""} ${fd.last_name ?? ""}`.trim() || "Unknown Applicant"}
                    </h2>
                    <p className="text-indigo-200 text-sm mt-0.5">
                      {[fd.university, fd.department].filter(Boolean).join(" · ")}
                    </p>
                    <p className="text-indigo-300 text-xs mt-0.5">{detail.submitted_at.slice(0, 16)}</p>
                  </div>
                  {/* Score circle */}
                  <div className={`shrink-0 w-20 h-20 rounded-full border-4 ${scoreRing} bg-white/10 backdrop-blur flex flex-col items-center justify-center`}>
                    <span className={`text-3xl font-black leading-none ${scoreColor}`}>{score}</span>
                    <span className="text-indigo-300 text-[9px] font-semibold mt-0.5">/ 100</span>
                  </div>
                </div>

                {/* Status badges */}
                <div className="flex flex-wrap gap-2 mt-5">
                  <span className={`text-xs font-bold px-3 py-1.5 rounded-full ${PRIORITY_BADGE[detail.priority] || "bg-white/20 text-white border border-white/30"}`}>
                    {detail.priority}
                  </span>
                  <span className={`text-xs font-bold px-3 py-1.5 rounded-full ${DECISION_BADGE[detail.decision] || "bg-white/20 text-white"}`}>
                    {detail.decision}
                  </span>
                  {v?.trust_score != null && (
                    <span className={`text-xs font-bold px-3 py-1.5 rounded-full ${v.trust_score >= 80 ? "bg-emerald-100 text-emerald-700" : v.trust_score >= 50 ? "bg-amber-100 text-amber-700" : "bg-red-100 text-red-600"}`}>
                      🛡 Trust {v.trust_score}
                    </span>
                  )}
                </div>
              </div>

              <div className="p-6 space-y-4">

                {/* ── Personal Info ── */}
                <Section title="👤 Personal Information">
                  <Row label="Full Name">{`${fd.first_name ?? ""} ${fd.last_name ?? ""}`.trim()}</Row>
                  <Row label="TC Identity No">
                    <span className="font-mono text-xs bg-slate-200 text-slate-600 px-2 py-0.5 rounded">{fd.tc_no ?? "—"}</span>
                  </Row>
                  <Row label="Date of Birth">{String(fd.birth_date ?? "—")}</Row>
                  <Row label="Email"><span className="text-indigo-600 text-xs">{String(fd.email ?? "—")}</span></Row>
                  <Row label="Gender"><span className="capitalize">{String(fd.gender ?? "—")}</span></Row>
                </Section>

                {/* ── Academic ── */}
                <Section title="🎓 Academic">
                  <Row label="University">{String(fd.university ?? "—")}</Row>
                  <Row label="Department">{String(fd.department ?? "—")}</Row>
                  <Row label="Year / Grade">Year {String(fd.grade ?? "—")}</Row>
                </Section>

                {/* ── Financial Profile ── */}
                <Section title="💰 Financial Profile">
                  <Row label="Monthly Household Income">
                    <span className="bg-indigo-100 text-indigo-700 text-xs font-bold px-2 py-0.5 rounded-full">
                      {INCOME_MAP[String(fd.monthly_income)] ?? String(fd.monthly_income ?? "—")}
                    </span>
                  </Row>
                  <Row label="Family Size">{String(fd.family_size ?? "—")} person(s)</Row>
                  <Row label="Siblings">{String(fd.siblings_count ?? 0)}</Row>
                  <Row label="Parents Divorced"><YesNo val={fd.parents_divorced} /></Row>
                  <Row label="Father Working"><YesNo val={fd.father_working} /></Row>
                  <Row label="Mother Working"><YesNo val={fd.mother_working} /></Row>
                  <Row label="Everyone Healthy"><YesNo val={fd.everyone_healthy} /></Row>
                  <Row label="Renting"><YesNo val={fd.is_renting} /></Row>
                  {fd.is_renting === "yes" && Number(fd.monthly_rent) > 0 && (
                    <Row label="Monthly Rent">{fmt(Number(fd.monthly_rent))}</Row>
                  )}
                  <Row label="Part-time Work"><YesNo val={fd.works_part_time} /></Row>
                  <Row label="Other Scholarship"><YesNo val={fd.other_scholarship} /></Row>
                </Section>

                {/* ── Assets ── */}
                {(fd.has_car === "yes" || fd.has_house === "yes") && (
                  <Section title="🏠 Declared Assets">
                    {fd.has_car === "yes" && (
                      <div className={fd.has_house === "yes" ? "mb-4 pb-4 border-b border-slate-200" : ""}>
                        <p className="text-xs font-bold text-slate-500 mb-2">🚗 Vehicle</p>
                        <Row label="Brand / Model">{`${fd.car_brand ?? ""} ${fd.car_model ?? ""}`.trim() || "—"}</Row>
                        <Row label="Year">{String(fd.car_year ?? "—")}</Row>
                        <Row label="Has Damage"><YesNo val={fd.car_damage} /></Row>
                        {fd.estimated_car_value != null && (
                          <Row label="Est. Market Value">
                            <span className="text-emerald-700 font-bold">{fmt(Number(fd.estimated_car_value))}</span>
                          </Row>
                        )}
                      </div>
                    )}
                    {fd.has_house === "yes" && (
                      <div>
                        <p className="text-xs font-bold text-slate-500 mb-2">🏠 Property</p>
                        {(fd.city || fd.district) && (
                          <Row label="Location">{[fd.city, fd.district].filter(Boolean).join(", ")}</Row>
                        )}
                        {fd.square_meters && <Row label="Size">{String(fd.square_meters)} m²</Row>}
                        {fd.property_estimated_value != null && (
                          <Row label="Est. Market Value">
                            <span className="text-emerald-700 font-bold">{fmt(Number(fd.property_estimated_value))}</span>
                          </Row>
                        )}
                      </div>
                    )}
                  </Section>
                )}

                {/* ── Score Breakdown ── */}
                {Object.keys(detail.scores?.breakdown || {}).length > 0 && (
                  <Section title="📊 Score Breakdown">
                    <div className="space-y-3">
                      {Object.entries(detail.scores.breakdown).map(([k, v]) => {
                        const isObj = typeof v === "object" && v !== null
                        const pts = isObj ? (v as {points?: number; score?: number}).points ?? (v as {score?: number}).score ?? 0 : Number(v)
                        const ans = isObj ? (v as {answer?: string}).answer : undefined
                        const w   = isObj ? (v as {weight?: number}).weight : undefined
                        const pct = Math.max(0, Math.min(100, pts))
                        const barColor = pts >= 60 ? "bg-emerald-400" : pts >= 30 ? "bg-amber-400" : "bg-red-400"
                        const ptColor  = pts >= 60 ? "text-emerald-600" : pts >= 30 ? "text-amber-600" : "text-red-500"
                        return (
                          <div key={k}>
                            <div className="flex justify-between items-center mb-1">
                              <span className="text-xs text-slate-500 capitalize font-medium">{k.replace(/_/g, " ")}</span>
                              <div className="flex items-center gap-2 shrink-0 ml-2">
                                {ans && <span className="text-xs text-slate-400 italic truncate max-w-[120px]">{ans}</span>}
                                {w !== undefined && <span className="text-xs text-slate-400 bg-slate-100 px-1.5 py-0.5 rounded">w:{w}%</span>}
                                <span className={`text-xs font-black min-w-[32px] text-right ${ptColor}`}>{pts}</span>
                              </div>
                            </div>
                            <div className="w-full bg-slate-100 rounded-full h-1.5">
                              <div className={`h-1.5 rounded-full transition-all ${barColor}`} style={{ width: `${pct}%` }} />
                            </div>
                          </div>
                        )
                      })}
                    </div>
                  </Section>
                )}

                {/* ── Evaluation Notes ── */}
                {(detail.scores?.reasons || []).length > 0 && (
                  <Section title="📝 Evaluation Notes">
                    <ul className="space-y-1.5">
                      {detail.scores.reasons.map((r, i) => (
                        <li key={i} className="text-xs text-slate-600 flex gap-2 items-start">
                          <span className="text-indigo-400 shrink-0 mt-0.5">›</span>{r}
                        </li>
                      ))}
                    </ul>
                  </Section>
                )}

                {/* ── Document Verification ── */}
                {v && (
                  <Section title="🛡️ Document Verification">
                    {/* Trust score bar */}
                    <div className={`rounded-xl px-4 py-3 mb-4 flex items-center justify-between
                      ${v.trust_score >= 80 ? "bg-emerald-50 border border-emerald-200"
                        : v.trust_score >= 50 ? "bg-amber-50 border border-amber-200"
                        : "bg-red-50 border border-red-200"}`}>
                      <div>
                        <p className="text-xs font-bold text-slate-600">Document Trust Score</p>
                        <p className="text-xs text-slate-400 mt-0.5">{v.trust_level}</p>
                      </div>
                      <div className={`text-4xl font-black ${v.trust_score >= 80 ? "text-emerald-600" : v.trust_score >= 50 ? "text-amber-600" : "text-red-600"}`}>
                        {v.trust_score ?? "—"}
                      </div>
                    </div>

                    <Row label="TC Identity">
                      {v.tc_valid
                        ? <span className="text-xs bg-emerald-100 text-emerald-700 font-semibold px-2 py-0.5 rounded-full">✅ Valid</span>
                        : <span className="text-xs bg-red-100 text-red-600 font-semibold px-2 py-0.5 rounded-full">❌ {v.tc_error || "Invalid"}</span>
                      }
                    </Row>
                    {v.qr_car && (
                      <Row label="Vehicle Reg. QR">
                        <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${v.qr_car.is_official ? "bg-emerald-100 text-emerald-700" : v.qr_car.found ? "bg-amber-100 text-amber-700" : "bg-slate-100 text-slate-500"}`}>
                          {v.qr_car.is_official ? "✅ Official" : v.qr_car.found ? "⚠️ Unverified" : "— Not found"}
                        </span>
                      </Row>
                    )}
                    {v.qr_house && (
                      <Row label="Title Deed QR">
                        <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${v.qr_house.is_official ? "bg-emerald-100 text-emerald-700" : v.qr_house.found ? "bg-amber-100 text-amber-700" : "bg-slate-100 text-slate-500"}`}>
                          {v.qr_house.is_official ? "✅ Official" : v.qr_house.found ? "⚠️ Unverified" : "— Not found"}
                        </span>
                      </Row>
                    )}

                    {(v.flags || []).length > 0 && (
                      <div className="mt-3 space-y-1.5">
                        <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Flags ({v.flags.length})</p>
                        {v.flags.map((f, i) => (
                          <div key={i} className={`text-xs px-3 py-2 rounded-xl flex gap-2 items-start
                            ${f.severity === "high" ? "bg-red-50 text-red-700 border border-red-200" : "bg-amber-50 text-amber-700 border border-amber-200"}`}>
                            <span className="shrink-0">{f.severity === "high" ? "🔴" : "🟡"}</span>
                            <span>{f.message}</span>
                          </div>
                        ))}
                      </div>
                    )}

                    {(v.passed_checks || []).length > 0 && (
                      <div className="mt-3">
                        <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-2">Passed Checks</p>
                        <div className="flex flex-wrap gap-1.5">
                          {v.passed_checks.map((p, i) => (
                            <span key={i} className="text-xs bg-emerald-50 text-emerald-700 border border-emerald-200 px-2 py-0.5 rounded-full">✓ {p}</span>
                          ))}
                        </div>
                      </div>
                    )}

                    {(v.notes || []).length > 0 && (
                      <div className="mt-2 space-y-1">
                        {v.notes.map((n, i) => (
                          <p key={i} className="text-xs text-slate-400 flex gap-2 items-start">
                            <span className="shrink-0">ℹ</span><span>{n}</span>
                          </p>
                        ))}
                      </div>
                    )}
                  </Section>
                )}

                <button
                  onClick={() => setDetail(null)}
                  className="w-full rounded-2xl bg-slate-100 hover:bg-slate-200 text-slate-600 font-bold py-3 text-sm transition"
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        )
      })()}
    </div>
  )
}
