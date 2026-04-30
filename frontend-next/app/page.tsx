"use client"

import { useState, useEffect } from "react"
import { useRouter } from "next/navigation"

const API = process.env.NEXT_PUBLIC_API_URL || "https://bitirmeprojesi-gza2.onrender.com"

type Scholarship = {
  id: string
  name: string
  description: string
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

function deadlineInfo(deadline: string) {
  const days = Math.ceil((new Date(deadline).getTime() - Date.now()) / 86400000)
  if (days < 0)  return { label: "❌ Süresi doldu",          color: "text-red-400",    urgent: false, pulse: false }
  if (days === 0) return { label: "🔥 Bugün son gün!",        color: "text-red-400",    urgent: true,  pulse: true  }
  if (days === 1) return { label: "😱 Yarın bitiyor!",        color: "text-red-400",    urgent: true,  pulse: true  }
  if (days === 2) return { label: "⚡ Son 2 gün!",            color: "text-orange-400", urgent: true,  pulse: false }
  if (days === 3) return { label: "⏳ Son 3 gün!",            color: "text-orange-400", urgent: true,  pulse: false }
  if (days <= 7)  return { label: `⏰ ${days} gün kaldı`,     color: "text-amber-400",  urgent: false, pulse: false }
  const d = new Date(deadline)
  const fmt = d.toLocaleDateString("tr-TR", { day: "numeric", month: "long", year: "numeric" })
  return { label: `📅 ${fmt}`,                               color: "text-slate-400",  urgent: false, pulse: false }
}

function DeadlineBadge({ deadline }: { deadline: string }) {
  if (!deadline) return null
  const { label, color, pulse } = deadlineInfo(deadline)
  return (
    <span className={`text-xs font-semibold ${color} ${pulse ? "animate-pulse" : ""}`}>
      {label}
    </span>
  )
}

export default function LandingPage() {
  const router = useRouter()
  const [scholarships, setScholarships] = useState<Scholarship[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState("")
  const [filter, setFilter] = useState<"all" | "financial" | "academic" | "both">("all")
  const [fetchError, setFetchError] = useState<string | null>(null)

  useEffect(() => {
    fetch(`${API}/scholarships`)
      .then(r => { if (!r.ok) throw new Error(`HTTP ${r.status}`); return r.json() })
      .then(data => setScholarships(Array.isArray(data) ? data : []))
      .catch(e => { setScholarships([]); setFetchError(String(e)) })
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
    <div className="min-h-screen bg-gradient-to-br from-indigo-50 via-violet-50 to-sky-50 flex flex-col">

      {/* ── Top Bar ── */}
      <div className="flex items-center justify-between px-6 py-4">
        <div className="flex items-center gap-2.5">
          <PSSDLogo size={36} />
          <div>
            <span className="text-indigo-900 font-black text-lg tracking-tight leading-none block">PSDS</span>
            <span className="text-indigo-400 text-[10px] leading-none hidden sm:block">Parametric Scholarship Distribution System</span>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <a href="/setup" className="text-xs bg-indigo-600 hover:bg-indigo-700 transition text-white px-3 py-1.5 rounded-lg font-semibold shadow-sm">
            + Create Scholarship
          </a>
          <a href="/admin" className="text-xs text-indigo-500 hover:text-indigo-700 transition font-semibold">
            Admin →
          </a>
        </div>
      </div>

      {/* ── Hero ── */}
      <div className="text-center px-4 pt-6 pb-8">
        <h1 className="text-3xl sm:text-4xl font-black text-indigo-900 mb-2 leading-tight">
          Bursunu{" "}
          <span className="bg-gradient-to-r from-indigo-500 to-violet-500 bg-clip-text text-transparent">
            Bul & Başvur
          </span>{" "}🎓
        </h1>
        <p className="text-slate-500 text-sm max-w-md mx-auto">
          Açık burs programlarına göz at, hemen başvur. Her bursun kendi kriterleri ve puanlama sistemi var.
        </p>
      </div>

      {/* ── Search + Filter ── */}
      <div className="max-w-3xl mx-auto w-full px-4 mb-6">
        <div className="flex flex-col sm:flex-row gap-3">
          <input
            value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder="Burs ara…"
            className="flex-1 rounded-xl bg-white border border-indigo-100 text-slate-800 placeholder-slate-400 px-4 py-2.5 text-sm outline-none focus:ring-2 focus:ring-indigo-400 shadow-sm"
          />
          <div className="flex gap-2">
            {(["all","financial","academic","both"] as const).map(f => (
              <button
                key={f}
                onClick={() => setFilter(f)}
                className={`px-3 py-2 rounded-xl text-xs font-semibold transition capitalize shadow-sm ${
                  filter === f
                    ? "bg-indigo-600 text-white shadow-indigo-200 shadow-md"
                    : "bg-white text-slate-600 hover:bg-indigo-50 border border-indigo-100"
                }`}
              >
                {f === "all" ? "Hepsi" : f === "both" ? "İkisi" : f === "financial" ? "Finansal" : "Akademik"}
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
            <p className="text-slate-400 text-sm">Yükleniyor…</p>
          </div>
        ) : fetchError ? (
          <div className="text-center py-20">
            <div className="text-4xl mb-3">⚠️</div>
            <p className="text-red-500 text-sm mb-1">Sunucuya ulaşılamadı.</p>
            <p className="text-slate-400 text-xs font-mono">{fetchError}</p>
          </div>
        ) : filtered.length === 0 ? (
          <div className="text-center py-20">
            <div className="text-4xl mb-3">{scholarships.length === 0 ? "📭" : "🔍"}</div>
            {scholarships.length === 0 ? (
              <>
                <p className="text-slate-500 text-sm mb-2">Henüz burs eklenmemiş.</p>
                <a href="/setup" className="text-indigo-500 hover:text-indigo-700 text-sm font-semibold underline">
                  İlk bursu oluştur →
                </a>
              </>
            ) : (
              <p className="text-slate-500 text-sm">Arama kriterlerine uyan burs bulunamadı.</p>
            )}
          </div>
        ) : (
          <div className="space-y-3 pb-12">
            <p className="text-slate-400 text-xs px-1">{filtered.length} burs mevcut</p>

            {filtered.map(s => {
              const badge = TYPE_BADGE[s.type] || { label: s.type, color: "bg-slate-100 text-slate-600" }
              const isClosed = s.deadline && new Date(s.deadline) < new Date()
              const dl = s.deadline && !isClosed ? deadlineInfo(s.deadline) : null
              return (
                <div
                  key={s.id}
                  className={`border rounded-2xl p-5 transition cursor-pointer group shadow-sm
                    ${isClosed
                      ? "opacity-50 bg-slate-100 border-slate-200 cursor-default"
                      : dl?.urgent
                        ? "bg-orange-50 border-orange-200 hover:border-orange-400 hover:shadow-md"
                        : "bg-white border-indigo-100 hover:border-indigo-300 hover:shadow-md"}`}
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
                            {s.financial_weight}% Finansal · {s.academic_weight}% Akademik
                          </span>
                        )}
                        {isClosed && (
                          <span className="text-xs bg-red-100 text-red-500 px-2 py-0.5 rounded-full font-semibold">
                            Kapalı
                          </span>
                        )}
                      </div>
                      <h2 className={`font-black text-lg leading-tight transition
                        ${isClosed ? "text-slate-400" : "text-slate-800 group-hover:text-indigo-600"}`}>
                        {s.name}
                      </h2>
                      {s.description && (
                        <p className="text-slate-500 text-sm mt-1 line-clamp-2">{s.description}</p>
                      )}
                      {s.deadline && (
                        <div className="mt-2">
                          <DeadlineBadge deadline={s.deadline} />
                        </div>
                      )}
                    </div>

                    {!isClosed && (
                      <div className="shrink-0">
                        <div className="w-10 h-10 rounded-xl bg-indigo-100 group-hover:bg-indigo-600 transition flex items-center justify-center text-indigo-500 group-hover:text-white text-lg font-bold">
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
      <div className="text-center py-4 text-slate-400 text-xs border-t border-indigo-100">
        PSDS © 2025 — Parametrik Burs Dağıtım Sistemi
      </div>
    </div>
  )
}
