"use client"

import { useState, useEffect } from "react"
import { useRouter } from "next/navigation"

const API = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:9001"

type Scholarship = {
  id: string
  name: string
  description: string
  slots: number
  deadline: string
  type: "financial" | "academic" | "both"
  financial_weight: number
  academic_weight: number
  created_at: string
}

const TYPE_BADGE: Record<string, { label: string; color: string }> = {
  financial: { label: "💸 Financial",         color: "bg-blue-100 text-blue-700" },
  academic:  { label: "🎓 Academic",          color: "bg-violet-100 text-violet-700" },
  both:      { label: "⚖️ Financial + Academic", color: "bg-indigo-100 text-indigo-700" },
}

function PSSDLogo({ size = 48 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg">
      <rect width="48" height="48" rx="14" fill="url(#grad)" />
      <path d="M14 34V14h10c4.418 0 7 2.2 7 5.5 0 2-1.1 3.6-2.8 4.4C30.8 24.8 32 26.6 32 29c0 3.6-2.8 5-7.5 5H14z" fill="white"/>
      <rect x="19" y="18" width="4.5" height="4" rx="1" fill="url(#grad)"/>
      <rect x="19" y="25" width="5.5" height="4" rx="1" fill="url(#grad)"/>
      <defs>
        <linearGradient id="grad" x1="0" y1="0" x2="48" y2="48" gradientUnits="userSpaceOnUse">
          <stop stopColor="#6366f1"/>
          <stop offset="1" stopColor="#8b5cf6"/>
        </linearGradient>
      </defs>
    </svg>
  )
}

function DeadlineBadge({ deadline }: { deadline: string }) {
  if (!deadline) return null
  const days = Math.ceil((new Date(deadline).getTime() - Date.now()) / 86400000)
  if (days < 0) return <span className="text-xs text-red-500 font-semibold">Closed</span>
  if (days <= 7) return <span className="text-xs text-orange-500 font-semibold">⏰ {days}d left</span>
  return <span className="text-xs text-slate-400">{deadline}</span>
}

export default function LandingPage() {
  const router = useRouter()
  const [scholarships, setScholarships] = useState<Scholarship[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState("")
  const [filter, setFilter] = useState<"all" | "financial" | "academic" | "both">("all")

  useEffect(() => {
    fetch(`${API}/scholarships`)
      .then(r => r.json())
      .then(data => setScholarships(Array.isArray(data) ? data : []))
      .catch(() => setScholarships([]))
      .finally(() => setLoading(false))
  }, [])

  const filtered = scholarships.filter(s => {
    const matchSearch = !search ||
      s.name.toLowerCase().includes(search.toLowerCase()) ||
      s.description.toLowerCase().includes(search.toLowerCase())
    const matchFilter = filter === "all" || s.type === filter
    return matchSearch && matchFilter
  })

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-indigo-950 to-slate-900 flex flex-col">

      {/* ── Top Bar ── */}
      <div className="flex items-center justify-between px-6 py-4">
        <div className="flex items-center gap-2.5">
          <PSSDLogo size={36} />
          <div>
            <span className="text-white font-black text-lg tracking-tight leading-none block">PSDS</span>
            <span className="text-indigo-300 text-[10px] leading-none hidden sm:block">Parametric Scholarship Distribution System</span>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <a href="/setup" className="text-xs bg-white/10 hover:bg-white/20 transition text-white px-3 py-1.5 rounded-lg font-semibold border border-white/10">
            + Create Scholarship
          </a>
          <a href="/admin" className="text-xs text-indigo-300 hover:text-white transition font-medium">
            Admin →
          </a>
        </div>
      </div>

      {/* ── Hero ── */}
      <div className="text-center px-4 pt-6 pb-8">
        <h1 className="text-3xl sm:text-4xl font-black text-white mb-2 leading-tight">
          Find Your{" "}
          <span className="bg-gradient-to-r from-indigo-400 to-violet-400 bg-clip-text text-transparent">
            Scholarship
          </span>
        </h1>
        <p className="text-slate-400 text-sm max-w-md mx-auto">
          Browse open scholarships and apply directly. Each scholarship has its own criteria and scoring system.
        </p>
      </div>

      {/* ── Search + Filter ── */}
      <div className="max-w-3xl mx-auto w-full px-4 mb-6">
        <div className="flex flex-col sm:flex-row gap-3">
          <input
            value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder="Search scholarships…"
            className="flex-1 rounded-xl bg-white/10 border border-white/10 text-white placeholder-slate-400 px-4 py-2.5 text-sm outline-none focus:ring-2 focus:ring-indigo-400"
          />
          <div className="flex gap-2">
            {(["all","financial","academic","both"] as const).map(f => (
              <button
                key={f}
                onClick={() => setFilter(f)}
                className={`px-3 py-2 rounded-xl text-xs font-semibold transition capitalize ${
                  filter === f
                    ? "bg-indigo-500 text-white"
                    : "bg-white/10 text-slate-300 hover:bg-white/20 border border-white/10"
                }`}
              >
                {f === "all" ? "All" : f === "both" ? "Both" : f}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* ── Scholarship List ── */}
      <div className="max-w-3xl mx-auto w-full px-4 flex-1">
        {loading ? (
          <div className="text-center py-20">
            <div className="w-8 h-8 border-4 border-indigo-400 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
            <p className="text-slate-400 text-sm">Loading scholarships…</p>
          </div>
        ) : filtered.length === 0 ? (
          <div className="text-center py-20">
            <div className="text-4xl mb-3">{scholarships.length === 0 ? "📭" : "🔍"}</div>
            {scholarships.length === 0 ? (
              <>
                <p className="text-slate-400 text-sm mb-2">No scholarships available yet.</p>
                <a href="/setup" className="text-indigo-400 hover:text-indigo-300 text-sm font-semibold underline">
                  Create the first one →
                </a>
              </>
            ) : (
              <p className="text-slate-400 text-sm">No scholarships match your search.</p>
            )}
          </div>
        ) : (
          <div className="space-y-3 pb-12">
            {/* Count */}
            <p className="text-slate-400 text-xs px-1">{filtered.length} scholarship{filtered.length !== 1 ? "s" : ""} available</p>

            {filtered.map(s => {
              const badge = TYPE_BADGE[s.type] || { label: s.type, color: "bg-slate-100 text-slate-600" }
              const isClosed = s.deadline && new Date(s.deadline) < new Date()
              return (
                <div
                  key={s.id}
                  className={`bg-white/5 backdrop-blur border border-white/10 rounded-2xl p-5 hover:bg-white/10 transition cursor-pointer group ${isClosed ? "opacity-60" : ""}`}
                  onClick={() => !isClosed && router.push(`/apply/${s.id}`)}
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1 flex-wrap">
                        <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${badge.color}`}>
                          {badge.label}
                        </span>
                        {s.type === "both" && (
                          <span className="text-xs text-slate-400">
                            {s.financial_weight}% Financial · {s.academic_weight}% Academic
                          </span>
                        )}
                        {isClosed && (
                          <span className="text-xs bg-red-500/20 text-red-400 px-2 py-0.5 rounded-full font-semibold">
                            Closed
                          </span>
                        )}
                      </div>
                      <h2 className="text-white font-black text-lg group-hover:text-indigo-300 transition leading-tight">
                        {s.name}
                      </h2>
                      {s.description && (
                        <p className="text-slate-400 text-sm mt-1 line-clamp-2">{s.description}</p>
                      )}
                      <div className="flex items-center gap-4 mt-3">
                        {s.slots > 0 && (
                          <span className="text-xs text-slate-400 flex items-center gap-1">
                            <span>👥</span> {s.slots} slots
                          </span>
                        )}
                        {s.deadline && (
                          <span className="text-xs text-slate-400 flex items-center gap-1">
                            <span>📅</span> <DeadlineBadge deadline={s.deadline} />
                          </span>
                        )}
                        <span className="text-xs font-mono text-slate-500">#{s.id}</span>
                      </div>
                    </div>

                    {!isClosed && (
                      <div className="shrink-0">
                        <div className="w-10 h-10 rounded-xl bg-indigo-500/20 group-hover:bg-indigo-500/40 transition flex items-center justify-center text-indigo-300 text-lg">
                          →
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </div>

      {/* ── Footer ── */}
      <div className="text-center py-4 text-slate-600 text-xs border-t border-white/5">
        PSDS © 2024 — Parametric Scholarship Distribution System
      </div>
    </div>
  )
}
