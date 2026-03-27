"use client"

import { useState } from "react"

const API = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:9001"

const INCOME_LABELS: Record<string, string> = {
  under_5000:  "< ₺5K",
  "5000_10000": "₺5K–10K",
  "10000_20000":"₺10K–20K",
  "20000_40000":"₺20K–40K",
  over_40000:  "> ₺40K",
}

function fmt(v?: number | null) {
  if (v == null) return "—"
  return new Intl.NumberFormat("tr-TR", { style: "currency", currency: "TRY", maximumFractionDigits: 0 }).format(v)
}

type App = {
  id: number
  submitted_at: string
  total_score: number
  priority: string
  decision: string
  first_name: string
  last_name: string
  university: string
  department: string
  gender: string
  monthly_income: string
  has_car: string
  has_house: string
  city: string
  siblings_count: string
  family_size: string
  property_value?: number | null
  car_value?: number | null
  reasons: string[]
  breakdown: Record<string, number>
  form_data: Record<string, string | number | null>
}

type Detail = {
  id: number
  submitted_at: string
  total_score: number
  priority: string
  decision: string
  form_data: Record<string, string | number | null>
  scores: { reasons: string[]; breakdown: Record<string, number> }
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

export default function AdminPage() {
  const [key, setKey]     = useState("")
  const [authed, setAuthed] = useState(false)
  const [keyErr, setKeyErr] = useState(false)
  const [apps, setApps]   = useState<App[]>([])
  const [loading, setLoading] = useState(false)
  const [detail, setDetail] = useState<Detail | null>(null)
  const [search, setSearch] = useState("")

  async function login() {
    setLoading(true)
    setKeyErr(false)
    try {
      const r = await fetch(`${API}/admin/applications?key=${key}`)
      if (!r.ok) { setKeyErr(true); return }
      const data = await r.json()
      setApps(data)
      setAuthed(true)
    } catch {
      setKeyErr(true)
    } finally {
      setLoading(false)
    }
  }

  async function loadDetail(id: number) {
    const r = await fetch(`${API}/admin/applications/${id}?key=${key}`)
    if (r.ok) setDetail(await r.json())
  }

  const filtered = apps.filter(a =>
    !search ||
    a.id.toString().includes(search) ||
    (a.first_name || "").toLowerCase().includes(search.toLowerCase()) ||
    (a.last_name  || "").toLowerCase().includes(search.toLowerCase()) ||
    (a.university || "").toLowerCase().includes(search.toLowerCase()) ||
    (a.city       || "").toLowerCase().includes(search.toLowerCase()) ||
    (a.gender     || "").toLowerCase().includes(search.toLowerCase())
  )

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
      </div>
    </div>
  )

  return (
    <div className="min-h-screen bg-slate-50">
      {/* Header */}
      <div className="bg-gradient-to-r from-indigo-700 to-violet-700 text-white px-6 py-4 flex items-center gap-4 shadow">
        <div>
          <h1 className="text-xl font-black">BursIQ Admin Panel</h1>
          <p className="text-indigo-200 text-xs">{apps.length} total applications</p>
        </div>
        <div className="ml-auto flex gap-3 items-center">
          <input
            type="text"
            placeholder="Search by name, city, university…"
            value={search}
            onChange={e => setSearch(e.target.value)}
            className="rounded-xl px-4 py-2 text-sm text-slate-800 bg-white/90 outline-none w-56"
          />
          <a href="/" className="text-xs text-indigo-200 hover:text-white transition">← Back to Form</a>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 py-6">
        {/* Stats */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-6">
          {[
            { label: "Total",      val: apps.length,                                             color: "indigo" },
            { label: "Accepted",   val: apps.filter(a => a.decision === "Accepted").length,      color: "green"  },
            { label: "Under Review",val:apps.filter(a => a.decision === "Under Review").length,  color: "amber"  },
            { label: "Avg Score",  val: apps.length ? Math.round(apps.reduce((s,a) => s + a.total_score, 0) / apps.length) : 0, color: "violet" },
          ].map(s => (
            <div key={s.label} className="bg-white rounded-2xl border border-slate-100 shadow-sm p-5 text-center">
              <div className={`text-3xl font-black text-${s.color}-600`}>{s.val}</div>
              <div className="text-xs text-slate-400 mt-1 font-medium">{s.label}</div>
            </div>
          ))}
        </div>

        {/* Table */}
        <div className="bg-white rounded-2xl border border-slate-100 shadow-sm overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-slate-50 border-b border-slate-100">
                  {["#ID","Ad Soyad","Üniversite","Tarih","Skor","Öncelik","Karar","Cinsiyet","Gelir","Araba","Ev","Şehir","İşlem"].map(h => (
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
                    <td className="px-4 py-3 text-slate-700 text-xs">{INCOME_LABELS[a.monthly_income] || a.monthly_income || "—"}</td>
                    <td className="px-4 py-3 text-center">{a.has_car === "yes" ? "✅" : "❌"}</td>
                    <td className="px-4 py-3 text-center">{a.has_house === "yes" ? "✅" : "❌"}</td>
                    <td className="px-4 py-3 text-slate-700 text-xs">{a.city || "—"}</td>
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
                  <tr><td colSpan={13} className="text-center text-slate-400 py-12 text-sm">Henüz başvuru yok.</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
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
                    : `Başvuru #${detail.id}`}
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
              {/* Decision */}
              <div className={`rounded-xl px-4 py-3 text-sm font-bold text-center border ${PRIORITY_STYLE[detail.priority] || ""}`}>
                {detail.priority} — {detail.decision}
              </div>

              {/* Form data */}
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

              {/* Breakdown */}
              <div>
                <h3 className="font-bold text-slate-700 text-sm mb-3">Score Breakdown</h3>
                <div className="space-y-1.5">
                  {Object.entries(detail.scores.breakdown || {}).map(([k, v]) => (
                    <div key={k} className="flex justify-between text-xs">
                      <span className="text-slate-400 capitalize">{k.replace(/_/g, " ")}</span>
                      <span className={`font-bold ${Number(v) < 0 ? "text-green-600" : "text-indigo-700"}`}>
                        {Number(v) > 0 ? `+${v}` : v}
                      </span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Reasons */}
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

              <div className="flex gap-2 mt-2">
                <a
                  href={`${API}/reports/report_${detail.total_score}.pdf`}
                  target="_blank"
                  rel="noreferrer"
                  className="flex-1 rounded-xl bg-gradient-to-r from-indigo-600 to-violet-600 text-white font-semibold py-2.5 text-sm text-center hover:shadow-lg transition"
                >
                  📄 PDF Report
                </a>
                <button
                  onClick={() => setDetail(null)}
                  className="flex-1 rounded-xl bg-slate-100 text-slate-700 font-semibold py-2.5 text-sm hover:bg-slate-200 transition"
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
