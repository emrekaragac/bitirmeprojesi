"use client"

import { useState } from "react"

const API = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:9001"

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
  slots: number
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
          <h1 className="text-2xl font-black text-slate-800">BursIQ Admin</h1>
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
          <h1 className="text-xl font-black">BursIQ Admin Panel</h1>
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
                      <span>{s.slots > 0 ? `${s.slots} slots` : "Unlimited"}</span>
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
                        {["#ID","Name","University","Date","Score","Priority","Decision","Gender","Trust","İşlem"].map(h => (
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
      {detail && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4" onClick={() => setDetail(null)}>
          <div className="bg-white rounded-2xl shadow-2xl max-w-lg w-full max-h-[85vh] overflow-y-auto" onClick={e => e.stopPropagation()}>
            <div className="sticky top-0 bg-gradient-to-r from-indigo-600 to-violet-600 text-white px-6 py-4 rounded-t-2xl flex items-center justify-between">
              <div>
                <h2 className="font-black text-lg">
                  {detail.form_data?.first_name || detail.form_data?.last_name
                    ? `${detail.form_data.first_name ?? ""} ${detail.form_data.last_name ?? ""}`.trim()
                    : `Application #${detail.id}`}
                </h2>
                <p className="text-indigo-200 text-xs">
                  {detail.form_data?.university ? `${detail.form_data.university} · ` : ""}
                  #{detail.id} · {detail.submitted_at.slice(0,16)}
                </p>
              </div>
              <div className="text-right">
                <div className="text-4xl font-black">{detail.total_score}</div>
                <div className="text-indigo-200 text-xs">score / 100</div>
              </div>
            </div>

            <div className="p-6 space-y-4">
              <div className={`rounded-xl px-4 py-3 text-sm font-bold text-center border ${PRIORITY_STYLE[detail.priority] || ""}`}>
                {detail.priority} — {detail.decision}
              </div>

              <div>
                <h3 className="font-bold text-slate-700 text-sm mb-3">Form Data</h3>
                <div className="space-y-1.5">
                  {Object.entries(detail.form_data).map(([k, v]) => (
                    v !== null && v !== "" && (
                      <div key={k} className="flex justify-between text-xs">
                        <span className="text-slate-400 capitalize">{k.replace(/_/g, " ")}</span>
                        <span className="text-slate-700 font-medium text-right max-w-[55%]">{String(v)}</span>
                      </div>
                    )
                  ))}
                </div>
              </div>

              <div>
                <h3 className="font-bold text-slate-700 text-sm mb-3">Score Breakdown</h3>
                <div className="space-y-1.5">
                  {Object.entries(detail.scores.breakdown || {}).map(([k, v]) => (
                    <div key={k} className="flex justify-between text-xs">
                      <span className="text-slate-400 capitalize">{k.replace(/_/g, " ")}</span>
                      <span className={`font-bold ${Number(v) < 0 ? "text-red-500" : "text-indigo-700"}`}>
                        {Number(v) > 0 ? `+${v}` : v}
                      </span>
                    </div>
                  ))}
                </div>
              </div>

              <div>
                <h3 className="font-bold text-slate-700 text-sm mb-3">Evaluation Notes</h3>
                <ul className="space-y-1">
                  {(detail.scores.reasons || []).map((r, i) => (
                    <li key={i} className="text-xs text-slate-600 flex gap-2">
                      <span className="text-indigo-400 shrink-0">•</span>{r}
                    </li>
                  ))}
                </ul>
              </div>

              {/* ── Verification Panel ── */}
              {detail.verification && (
                <div>
                  <h3 className="font-bold text-slate-700 text-sm mb-3">🛡️ Document Verification</h3>

                  {/* Trust score */}
                  <div className={`rounded-xl px-4 py-3 mb-3 flex items-center justify-between
                    ${(detail.verification.trust_score ?? 100) >= 80
                      ? "bg-emerald-50 border border-emerald-200"
                      : (detail.verification.trust_score ?? 100) >= 50
                      ? "bg-amber-50 border border-amber-200"
                      : "bg-red-50 border border-red-200"}`}>
                    <div>
                      <div className="text-xs font-semibold text-slate-600">Trust Score</div>
                      <div className="text-xs text-slate-500">{detail.verification.trust_level}</div>
                    </div>
                    <div className={`text-2xl font-black
                      ${(detail.verification.trust_score ?? 100) >= 80 ? "text-emerald-600"
                        : (detail.verification.trust_score ?? 100) >= 50 ? "text-amber-600"
                        : "text-red-600"}`}>
                      {detail.verification.trust_score ?? "—"}
                    </div>
                  </div>

                  {/* TC Kimlik */}
                  <div className={`flex items-center gap-2 text-xs px-3 py-2 rounded-lg mb-2
                    ${detail.verification.tc_valid ? "bg-emerald-50 text-emerald-700" : "bg-red-50 text-red-700"}`}>
                    <span>{detail.verification.tc_valid ? "✅" : "❌"}</span>
                    <span className="font-semibold">TC Kimlik No:</span>
                    <span>{detail.verification.tc_valid ? "Valid" : (detail.verification.tc_error || "Invalid")}</span>
                  </div>

                  {/* QR Codes */}
                  {detail.verification.qr_car && (
                    <div className={`flex items-center gap-2 text-xs px-3 py-2 rounded-lg mb-2
                      ${detail.verification.qr_car.is_official ? "bg-emerald-50 text-emerald-700" : detail.verification.qr_car.found ? "bg-amber-50 text-amber-700" : "bg-slate-100 text-slate-500"}`}>
                      <span>{detail.verification.qr_car.is_official ? "✅" : detail.verification.qr_car.found ? "⚠️" : "—"}</span>
                      <span className="font-semibold">Ruhsat QR:</span>
                      <span>{detail.verification.qr_car.is_official ? "Official domain verified" : detail.verification.qr_car.found ? "QR found but domain unrecognized" : "No QR found"}</span>
                    </div>
                  )}
                  {detail.verification.qr_house && (
                    <div className={`flex items-center gap-2 text-xs px-3 py-2 rounded-lg mb-2
                      ${detail.verification.qr_house.is_official ? "bg-emerald-50 text-emerald-700" : detail.verification.qr_house.found ? "bg-amber-50 text-amber-700" : "bg-slate-100 text-slate-500"}`}>
                      <span>{detail.verification.qr_house.is_official ? "✅" : detail.verification.qr_house.found ? "⚠️" : "—"}</span>
                      <span className="font-semibold">Tapu QR:</span>
                      <span>{detail.verification.qr_house.is_official ? "Official domain verified" : detail.verification.qr_house.found ? "QR found but domain unrecognized" : "No QR found"}</span>
                    </div>
                  )}

                  {/* Flags */}
                  {(detail.verification.flags || []).length > 0 && (
                    <div className="mt-3">
                      <div className="text-xs font-semibold text-slate-500 mb-2">⚠️ Flags ({detail.verification.flags.length})</div>
                      <div className="space-y-1.5">
                        {detail.verification.flags.map((f, i) => (
                          <div key={i} className={`text-xs px-3 py-2 rounded-lg flex gap-2
                            ${f.severity === "high" ? "bg-red-50 text-red-700 border border-red-200" : "bg-amber-50 text-amber-700 border border-amber-200"}`}>
                            <span className="shrink-0">{f.severity === "high" ? "🔴" : "🟡"}</span>
                            <span>{f.message}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Passed checks */}
                  {(detail.verification.passed_checks || []).length > 0 && (
                    <div className="mt-3">
                      <div className="text-xs font-semibold text-slate-500 mb-2">✅ Passed ({detail.verification.passed_checks.length})</div>
                      <div className="space-y-1">
                        {detail.verification.passed_checks.map((p, i) => (
                          <div key={i} className="text-xs text-emerald-700 flex gap-2">
                            <span className="shrink-0">✓</span><span>{p}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Notes */}
                  {(detail.verification.notes || []).length > 0 && (
                    <div className="mt-2 space-y-1">
                      {detail.verification.notes.map((n, i) => (
                        <div key={i} className="text-xs text-slate-500 flex gap-2">
                          <span className="shrink-0">ℹ️</span><span>{n}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}

              <button
                onClick={() => setDetail(null)}
                className="w-full rounded-xl bg-slate-100 text-slate-700 font-semibold py-2.5 text-sm hover:bg-slate-200 transition"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
