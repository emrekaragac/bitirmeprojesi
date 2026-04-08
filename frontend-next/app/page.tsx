"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"

function BursIQLogo({ size = 48 }: { size?: number }) {
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

export default function LandingPage() {
  const router = useRouter()
  const [scholarshipId, setScholarshipId] = useState("")
  const [idErr, setIdErr] = useState(false)

  function handleApply() {
    if (!scholarshipId.trim()) { setIdErr(true); return }
    router.push(`/apply/${scholarshipId.trim().toUpperCase()}`)
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-indigo-950 to-slate-900 flex flex-col">
      {/* Top bar */}
      <div className="flex items-center justify-between px-6 py-4">
        <div className="flex items-center gap-2">
          <BursIQLogo size={36} />
          <span className="text-white font-black text-xl tracking-tight">BursIQ</span>
        </div>
        <a href="/admin" className="text-indigo-300 hover:text-white text-sm font-medium transition">
          Admin Panel →
        </a>
      </div>

      {/* Hero */}
      <div className="flex-1 flex flex-col items-center justify-center px-4 py-12 text-center">
        <div className="mb-6">
          <BursIQLogo size={72} />
        </div>
        <h1 className="text-4xl sm:text-5xl font-black text-white mb-3 leading-tight">
          Smart Scholarship<br />
          <span className="bg-gradient-to-r from-indigo-400 to-violet-400 bg-clip-text text-transparent">
            Decision System
          </span>
        </h1>
        <p className="text-slate-400 text-lg max-w-md mb-12">
          AI-powered scholarship evaluation with automatic scoring, document OCR, and financial analysis.
        </p>

        {/* Two paths */}
        <div className="grid sm:grid-cols-2 gap-5 w-full max-w-2xl">

          {/* Provider Card */}
          <div className="bg-white/5 backdrop-blur-sm border border-white/10 rounded-2xl p-6 flex flex-col items-center text-center hover:bg-white/10 transition group">
            <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-violet-500 to-indigo-600 flex items-center justify-center text-2xl mb-4 group-hover:scale-110 transition">
              🏛️
            </div>
            <h2 className="text-white font-black text-lg mb-2">I'm a Scholarship Provider</h2>
            <p className="text-slate-400 text-sm mb-5">
              Create a custom scholarship with your own criteria, documents, and scoring weights.
            </p>
            <a
              href="/setup"
              className="w-full rounded-xl bg-gradient-to-r from-violet-600 to-indigo-600 text-white font-bold py-3 text-sm hover:shadow-lg hover:shadow-indigo-900/50 transition block text-center"
            >
              Create Scholarship →
            </a>
          </div>

          {/* Applicant Card */}
          <div className="bg-white/5 backdrop-blur-sm border border-white/10 rounded-2xl p-6 flex flex-col items-center text-center hover:bg-white/10 transition group">
            <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-emerald-500 to-teal-600 flex items-center justify-center text-2xl mb-4 group-hover:scale-110 transition">
              🎓
            </div>
            <h2 className="text-white font-black text-lg mb-2">I'm an Applicant</h2>
            <p className="text-slate-400 text-sm mb-4">
              Enter your scholarship ID to start your application. Get instant results.
            </p>
            <div className="w-full space-y-2">
              <input
                value={scholarshipId}
                onChange={e => { setScholarshipId(e.target.value.toUpperCase()); setIdErr(false) }}
                onKeyDown={e => e.key === "Enter" && handleApply()}
                placeholder="Scholarship ID (e.g. A1B2C3)"
                className={`w-full rounded-xl border-2 ${idErr ? "border-red-500" : "border-white/20"} bg-white/10 text-white placeholder-slate-400 px-4 py-2.5 text-sm outline-none focus:ring-2 focus:ring-emerald-400`}
              />
              {idErr && <p className="text-red-400 text-xs">Please enter a scholarship ID</p>}
              <button
                onClick={handleApply}
                className="w-full rounded-xl bg-gradient-to-r from-emerald-500 to-teal-500 text-white font-bold py-3 text-sm hover:shadow-lg hover:shadow-emerald-900/50 transition"
              >
                Apply Now →
              </button>
            </div>
          </div>
        </div>

        {/* Features */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 w-full max-w-2xl mt-10">
          {[
            { icon: "🤖", label: "AI Scoring" },
            { icon: "📄", label: "OCR Documents" },
            { icon: "📊", label: "Real-time Results" },
            { icon: "🔒", label: "Secure & Private" },
          ].map(f => (
            <div key={f.label} className="bg-white/5 border border-white/10 rounded-xl px-3 py-3 text-center">
              <div className="text-xl mb-1">{f.icon}</div>
              <div className="text-slate-400 text-xs font-medium">{f.label}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Footer */}
      <div className="text-center py-4 text-slate-600 text-xs">
        BursIQ © 2024 — Scholarship Decision Support System
      </div>
    </div>
  )
}
