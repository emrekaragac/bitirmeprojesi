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
  financial: { label: "💸 Finansal",            color: "bg-blue-100 text-blue-700" },
  academic:  { label: "🎓 Akademik",            color: "bg-violet-100 text-violet-700" },
  both:      { label: "⚖️ Finansal + Akademik", color: "bg-indigo-100 text-indigo-700" },
}

function BursIQLogo({ size = 44 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 56 56" fill="none" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <linearGradient id="bq-grad" x1="0" y1="0" x2="56" y2="56" gradientUnits="userSpaceOnUse">
          <stop stopColor="#6366f1"/>
          <stop offset="1" stopColor="#a855f7"/>
        </linearGradient>
        <linearGradient id="bq-grad2" x1="56" y1="0" x2="0" y2="56" gradientUnits="userSpaceOnUse">
          <stop stopColor="#818cf8"/>
          <stop offset="1" stopColor="#c084fc"/>
        </linearGradient>
      </defs>
      {/* Rounded square bg */}
      <rect width="56" height="56" rx="16" fill="url(#bq-grad)"/>
      {/* Graduation cap — flat icon */}
      {/* Board */}
      <polygon points="28,13 48,22 28,31 8,22" fill="white" opacity="0.95"/>
      {/* Cap top shine */}
      <polygon points="28,13 48,22 28,22" fill="white" opacity="0.2"/>
      {/* Left drape */}
      <path d="M14 24v9c0 0 5 5 14 5s14-5 14-5v-9L28 31z" fill="white" opacity="0.85"/>
      {/* Tassel string */}
      <line x1="48" y1="22" x2="48" y2="34" stroke="white" strokeWidth="2" strokeLinecap="round" opacity="0.9"/>
      {/* Tassel ball */}
      <circle cx="48" cy="36" r="2.5" fill="url(#bq-grad2)" stroke="white" strokeWidth="1.5"/>
    </svg>
  )
}

function deadlineInfo(deadline: string) {
  const days = Math.ceil((new Date(deadline).getTime() - Date.now()) / 86400000)
  if (days < 0)   return { label: "Süresi doldu",   color: "text-red-400",    urgent: false, pulse: false }
  if (days === 0) return { label: "🔥 Bugün son gün!", color: "text-red-500", urgent: true,  pulse: true  }
  if (days === 1) return { label: "😱 Yarın bitiyor!", color: "text-red-500", urgent: true,  pulse: true  }
  if (days === 2) return { label: "⚡ Son 2 gün!",    color: "text-orange-500", urgent: true,  pulse: false }
  if (days === 3) return { label: "⏳ Son 3 gün!",    color: "text-orange-500", urgent: true,  pulse: false }
  if (days <= 7)  return { label: `⏰ ${days} gün kaldı`, color: "text-amber-600", urgent: false, pulse: false }
  const d = new Date(deadline)
  const fmt = d.toLocaleDateString("tr-TR", { day: "numeric", month: "long", year: "numeric" })
  return { label: `📅 ${fmt}`, color: "text-slate-400", urgent: false, pulse: false }
}

function DeadlineBadge({ deadline }: { deadline: string }) {
  if (!deadline) return null
  const { label, color, pulse } = deadlineInfo(deadline)
  return (
    <span className={`text-sm font-semibold ${color} ${pulse ? "animate-pulse" : ""}`}>
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
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-indigo-50 to-violet-50 flex flex-col">

      {/* ── Top Bar ── */}
      <div className="flex items-center justify-between px-8 py-5 border-b border-indigo-100 bg-white/70 backdrop-blur sticky top-0 z-10">
        <div className="flex items-center gap-3">
          <BursIQLogo size={44} />
          <div>
            <span className="text-indigo-900 font-black text-xl tracking-tight leading-none block">BursIQ</span>
            <span className="text-indigo-400 text-[11px] font-medium leading-none">Parametrik Burs Sistemi</span>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <a href="/setup"
            className="text-sm bg-indigo-600 hover:bg-indigo-700 transition text-white px-4 py-2 rounded-xl font-semibold shadow-sm shadow-indigo-200">
            + Burs Oluştur
          </a>
          <a href="/admin" className="text-sm text-indigo-500 hover:text-indigo-800 transition font-semibold">
            Admin →
          </a>
        </div>
      </div>

      {/* ── Hero ── */}
      <div className="text-center px-4 pt-16 pb-12">
        <div className="inline-flex items-center gap-2 bg-indigo-100 text-indigo-700 text-sm font-semibold px-4 py-1.5 rounded-full mb-6">
          🎓 Türkiye&apos;nin Akıllı Burs Platformu
        </div>
        <h1 className="text-5xl sm:text-6xl font-black text-indigo-950 mb-4 leading-tight tracking-tight">
          Bursunu{" "}
          <span className="bg-gradient-to-r from-indigo-500 to-violet-500 bg-clip-text text-transparent">
            Bul & Başvur
          </span>
        </h1>
        <p className="text-slate-500 text-lg max-w-lg mx-auto leading-relaxed">
          Açık burs programlarına göz at, hemen başvur. Her bursun kendi kriterleri ve puanlama sistemi var.
        </p>

        {/* Stats row */}
        <div className="flex items-center justify-center gap-8 mt-10">
          {[
            { n: scholarships.length, label: "Aktif Burs" },
            { n: "AI", label: "Destekli Analiz" },
            { n: "100%", label: "Şeffaf Puanlama" },
          ].map(({ n, label }) => (
            <div key={label} className="text-center">
              <div className="text-2xl font-black text-indigo-700">{n}</div>
              <div className="text-xs text-slate-400 font-medium mt-0.5">{label}</div>
            </div>
          ))}
        </div>
      </div>

      {/* ── Search + Filter ── */}
      <div className="max-w-3xl mx-auto w-full px-6 mb-8">
        <div className="flex flex-col sm:flex-row gap-3">
          <input
            value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder="Burs ara…"
            className="flex-1 rounded-2xl bg-white border border-indigo-100 text-slate-800 placeholder-slate-400 px-5 py-3.5 text-base outline-none focus:ring-2 focus:ring-indigo-400 shadow-sm"
          />
          <div className="flex gap-2">
            {(["all","financial","academic","both"] as const).map(f => (
              <button
                key={f}
                onClick={() => setFilter(f)}
                className={`px-4 py-3 rounded-2xl text-sm font-semibold transition shadow-sm ${
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
      <div className="max-w-3xl mx-auto w-full px-6 flex-1">
        {loading ? (
          <div className="text-center py-24">
            <div className="w-10 h-10 border-4 border-indigo-400 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
            <p className="text-slate-400 font-medium">Yükleniyor…</p>
          </div>
        ) : fetchError ? (
          <div className="text-center py-24">
            <div className="text-5xl mb-4">⚠️</div>
            <p className="text-red-500 font-semibold mb-1">Sunucuya ulaşılamadı.</p>
            <p className="text-slate-400 text-sm font-mono">{fetchError}</p>
          </div>
        ) : filtered.length === 0 ? (
          <div className="text-center py-24">
            <div className="text-5xl mb-4">{scholarships.length === 0 ? "📭" : "🔍"}</div>
            {scholarships.length === 0 ? (
              <>
                <p className="text-slate-500 font-medium mb-3">Henüz burs eklenmemiş.</p>
                <a href="/setup" className="text-indigo-600 hover:text-indigo-800 font-bold underline">
                  İlk bursu oluştur →
                </a>
              </>
            ) : (
              <p className="text-slate-500 font-medium">Arama kriterlerine uyan burs bulunamadı.</p>
            )}
          </div>
        ) : (
          <div className="space-y-4 pb-16">
            <p className="text-slate-400 text-sm font-medium px-1">{filtered.length} burs mevcut</p>

            {filtered.map(s => {
              const badge = TYPE_BADGE[s.type] || { label: s.type, color: "bg-slate-100 text-slate-600" }
              const isClosed = s.deadline && new Date(s.deadline) < new Date()
              const dl = s.deadline && !isClosed ? deadlineInfo(s.deadline) : null
              return (
                <div
                  key={s.id}
                  className={`border rounded-2xl p-6 transition cursor-pointer group shadow-sm
                    ${isClosed
                      ? "opacity-50 bg-slate-100 border-slate-200 cursor-default"
                      : dl?.urgent
                        ? "bg-orange-50 border-orange-200 hover:border-orange-400 hover:shadow-lg hover:-translate-y-0.5"
                        : "bg-white border-indigo-100 hover:border-indigo-400 hover:shadow-lg hover:-translate-y-0.5"}`}
                  style={{ transition: "all 0.18s ease" }}
                  onClick={() => !isClosed && router.push(`/apply/${s.id}`)}
                >
                  <div className="flex items-center justify-between gap-4">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-2 flex-wrap">
                        <span className={`text-xs font-bold px-2.5 py-1 rounded-full ${badge.color}`}>
                          {badge.label}
                        </span>
                        {s.type === "both" && (
                          <span className="text-xs text-slate-400 font-medium">
                            {s.financial_weight}% Finansal · {s.academic_weight}% Akademik
                          </span>
                        )}
                        {isClosed && (
                          <span className="text-xs bg-red-100 text-red-500 px-2.5 py-1 rounded-full font-bold">
                            Kapalı
                          </span>
                        )}
                      </div>
                      <h2 className={`font-black text-xl leading-tight mb-1 transition
                        ${isClosed ? "text-slate-400" : "text-slate-900 group-hover:text-indigo-700"}`}>
                        {s.name}
                      </h2>
                      {s.description && (
                        <p className="text-slate-500 text-sm line-clamp-1 mb-2">{s.description}</p>
                      )}
                      {s.deadline && (
                        <DeadlineBadge deadline={s.deadline} />
                      )}
                    </div>

                    {!isClosed && (
                      <div className="shrink-0">
                        <div className="w-12 h-12 rounded-2xl bg-indigo-100 group-hover:bg-indigo-600 transition flex items-center justify-center text-indigo-500 group-hover:text-white text-xl font-black">
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
      <div className="text-center py-6 text-slate-400 text-sm border-t border-indigo-100 mt-4">
        BursIQ © 2025 — Parametrik Burs Dağıtım Sistemi
      </div>
    </div>
  )
}
