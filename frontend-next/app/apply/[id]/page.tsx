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

type BreakdownEntry = number | { weight: number; answer: string; score: number; points: number }

type Result = {
  application_id: number
  score: number
  priority: string
  decision: string
  reasons: string[]
  breakdown: Record<string, BreakdownEntry>
  property_estimated_value?: number
  avg_m2_price?: number
  estimated_car_value?: number
}

const INCOME_OPTIONS = [
  { val: "under_22000",   label: "₺22.000 altı — asgari ücret altı" },
  { val: "22000_40000",   label: "₺22.000 – ₺40.000" },
  { val: "40000_75000",   label: "₺40.000 – ₺75.000" },
  { val: "75000_150000",  label: "₺75.000 – ₺150.000" },
  { val: "over_150000",   label: "₺150.000 üstü" },
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

// ── KVKK Metni ──────────────────────────────────────────────
const KVKK_TEXT = `PSDS — Açık Rıza Beyanı

Veri Sorumlusu: Parametrik Burs Dağıtım Sistemi (PSDS)
Kapsam: Burs başvurusu kapsamında işlenecek tüm kişisel veriler
Dayanak: 6698 Sayılı Kişisel Verilerin Korunması Kanunu (KVKK)

1. İŞLENECEK KİŞİSEL VERİLER

a) Kimlik ve İletişim Bilgileri
Ad, soyad, doğum tarihi, e-posta adresi, telefon numarası, ikamet adresi.

b) Finansal Veriler
Hane halkı gelir düzeyi, taşınmaz mülkiyet bilgisi, araç mülkiyeti, borç yükümlülükleri, aile fertleri sayısı ve gelir durumları. Beyan ettiğiniz araç ve/veya taşınmaz bilgileri (marka, model, yıl, konum gibi özellikler), piyasa değeri tahmini amacıyla kamuya açık Türk ilan platformlarından (arabam.com, hepsiemlak.com, sahibinden.com) toplanan güncel fiyat verileriyle birlikte işlenmektedir.

c) Akademik Veriler
Not ortalaması (GPA), öğrenci belgesi, burs ve başarı belgeleri, dil sertifikaları, araştırma faaliyetleri.

d) Liderlik ve Sosyal Etki Verileri
Dernek/kulüp üyelikleri, gönüllülük faaliyetleri, girişimcilik deneyimi.

e) Yüklenen Belgeler — OCR ile İşlenen Veriler
Yüklenen belgeler pdfplumber ve pytesseract kütüphaneleri kullanılarak optik karakter tanıma (OCR) işlemine tabi tutulmaktadır. Elde edilen veriler, formda beyan ettiğiniz bilgilerle çapraz doğrulama amacıyla kullanılmakta; her başvuru için 0–100 arasında bir güven puanı hesaplanmaktadır.

2. VERİLERİN İŞLENME AMAÇLARI

• Burs başvurusunun alınması, değerlendirilmesi ve sonuçlandırılması
• Beyan edilen finansal varlıkların güncel piyasa verileriyle doğrulanması
• Yüklenen belgeler ile form beyanlarının tutarlılığının denetlenmesi
• Burs programına özgü ağırlıklı puanlama formülüne göre başvurunun puanlanması
• Sistem yöneticileri tarafından aday sıralamasının görüntülenmesi

3. VERİLERİN AKTARILACAĞI TARAFLAR

Sistem Yönetimi: Başvurunuz ve puan dökümünüz yalnızca PSDS sistem yöneticileri tarafından görüntülenebilir. Verileriniz herhangi bir burs sağlayıcısı, vakıf veya üçüncü taraf kurumla paylaşılmamaktadır.

Anthropic Inc. — Yurt Dışı Aktarım (KVKK Madde 9): Finansal varlık değerleme sürecinde, beyan ettiğiniz araç veya taşınmaz özellikleri (marka, model, yıl, konum gibi) kamuya açık piyasa verileriyle birlikte Anthropic Inc. tarafından işletilen yapay zeka API'sine (Claude) iletilmektedir. Anthropic Inc. Amerika Birleşik Devletleri'nde yerleşik bir şirkettir; bu iletim KVKK'nın 9. maddesi kapsamında yurt dışına kişisel veri aktarımı niteliği taşımaktadır. Söz konusu aktarım yalnızca piyasa değeri tahmini amacıyla gerçekleştirilmekte olup adınız, kimlik numaranız ve iletişim bilgileriniz bu aktarıma dahil edilmemektedir.

Altyapı Hizmet Sağlayıcıları: Vercel (frontend barındırma) ve Render (backend barındırma) platformları teknik veri işleyici konumundadır; kişisel verilerinize bağımsız olarak erişemezler.

4. SAKLAMA SÜRESİ

Kişisel verileriniz, burs değerlendirme sürecinin tamamlanmasından itibaren ilgili mevzuatta öngörülen süreler boyunca saklanacak; akabinde güvenli biçimde silinecek veya anonimleştirilecektir.

5. KVKK KAPSAMINDAKİ HAKLARINIZ

KVKK'nın 11. maddesi uyarınca: kişisel verilerinizin işlenip işlenmediğini öğrenme, işlenen verileriniz hakkında bilgi talep etme, verilerin işlenme amacını öğrenme, yurt içinde veya yurt dışında aktarıldığı üçüncü kişileri öğrenme, eksik veya yanlış işlenmiş verilerin düzeltilmesini isteme, KVKK'nın 7. maddesi çerçevesinde silinmesini ya da yok edilmesini isteme, otomatik sistemler aracılığıyla aleyhinize sonuç doğuran işlemlere itiraz etme ve kanuna aykırı işleme nedeniyle uğradığınız zararın giderilmesini talep etme haklarına sahipsiniz.

6. RIZANIN GERİ ALINMASI

Açık rızanızı dilediğiniz zaman geri alabilirsiniz. Geri alma, önceki veri işleme faaliyetlerinin hukukiliğini etkilemez.

PSDS — Kadir Has Üniversitesi, Yönetim Bilişim Sistemleri, 2025–2026
Sude Yerekonmaz · Nora Mardikyan · Emre Karagac · Beyzanur Pala`

const CAR_BRANDS: Record<string, string[]> = {
  "Toyota":       ["Corolla", "Yaris", "Camry", "C-HR", "RAV4", "Land Cruiser", "Hilux", "Auris", "Prius", "Verso"],
  "Volkswagen":   ["Polo", "Golf", "Passat", "Tiguan", "T-Roc", "T-Cross", "Caddy", "Transporter", "Arteon"],
  "Renault":      ["Clio", "Megane", "Symbol", "Fluence", "Kadjar", "Captur", "Duster", "Taliant", "Zoe", "Talisman"],
  "Fiat":         ["Egea", "500", "Doblo", "Panda", "Tipo", "Fiorino", "Ducato"],
  "Ford":         ["Fiesta", "Focus", "Mondeo", "Kuga", "EcoSport", "Puma", "Ranger", "Transit", "Transit Connect"],
  "Hyundai":      ["i10", "i20", "i30", "Elantra", "Tucson", "Santa Fe", "Kona", "Bayon"],
  "Kia":          ["Picanto", "Rio", "Ceed", "Sportage", "Sorento", "Stonic", "Niro"],
  "BMW":          ["1 Serisi", "2 Serisi", "3 Serisi", "4 Serisi", "5 Serisi", "7 Serisi", "X1", "X2", "X3", "X5", "X6"],
  "Mercedes-Benz":["A Serisi", "B Serisi", "C Serisi", "E Serisi", "S Serisi", "GLA", "GLB", "GLC", "GLE", "GLS", "Vito"],
  "Audi":         ["A1", "A3", "A4", "A5", "A6", "A7", "A8", "Q2", "Q3", "Q5", "Q7", "Q8"],
  "Opel":         ["Corsa", "Astra", "Insignia", "Mokka", "Crossland", "Grandland", "Combo"],
  "Peugeot":      ["108", "208", "308", "408", "508", "2008", "3008", "5008", "Partner", "Expert"],
  "Citroen":      ["C1", "C3", "C4", "C5 Aircross", "Berlingo", "Jumpy"],
  "Dacia":        ["Sandero", "Logan", "Duster", "Jogger", "Spring", "Dokker"],
  "SEAT":         ["Ibiza", "Leon", "Arona", "Ateca", "Tarraco"],
  "Skoda":        ["Fabia", "Scala", "Octavia", "Superb", "Kamiq", "Karoq", "Kodiaq"],
  "Honda":        ["Jazz", "Civic", "Accord", "HR-V", "CR-V"],
  "Nissan":       ["Micra", "Note", "Juke", "Qashqai", "X-Trail", "Navara"],
  "Mazda":        ["Mazda2", "Mazda3", "Mazda6", "CX-3", "CX-5", "CX-30"],
  "Volvo":        ["V40", "V60", "V90", "S60", "S90", "XC40", "XC60", "XC90"],
  "Mitsubishi":   ["Colt", "Lancer", "Outlander", "Eclipse Cross", "ASX", "L200"],
  "Suzuki":       ["Alto", "Swift", "Baleno", "Vitara", "S-Cross", "Ignis"],
  "Subaru":       ["Impreza", "Forester", "Outback", "XV", "Legacy"],
  "Jeep":         ["Renegade", "Compass", "Cherokee", "Grand Cherokee", "Wrangler"],
  "Land Rover":   ["Defender", "Discovery", "Discovery Sport", "Range Rover", "Range Rover Sport", "Range Rover Evoque"],
  "Porsche":      ["911", "718 Boxster", "718 Cayman", "Cayenne", "Macan", "Panamera", "Taycan"],
  "TOGG":         ["T10X", "T10F"],
  "Tofaş":        ["Şahin", "Kartal", "Doğan", "Tempra"],
}

const DOC_LABELS: Record<string, { label: string; icon: string }> = {
  car_file:            { label: "Vehicle Registration (Ruhsat)", icon: "🚗" },
  house_file:          { label: "Title Deed (Tapu)",             icon: "🏠" },
  transcript_file:     { label: "Transcript",                    icon: "📋" },
  income_file:         { label: "Income Statement",              icon: "💰" },
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
  const [submitError, setSubmitError] = useState<string | null>(null)
  const [result, setResult]  = useState<Result | null>(null)
  const [savedAt, setSavedAt] = useState<string | null>(null)
  const [kvkkAccepted, setKvkkAccepted] = useState(false)
  const [kvkkOpen, setKvkkOpen] = useState(false)
  const [docValidation, setDocValidation] = useState<Record<string, {
    status: "checking" | "valid" | "invalid" | "unknown"
    message: string
    visionUnavailable?: boolean   // true → Vision okuyamadı, manuel giriş gerekebilir
  }>>({})


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

  async function setFile(key: string, f: File | null) {
    setFiles(prev => {
      if (!f) { const n = { ...prev }; delete n[key]; return n }
      return { ...prev, [key]: f }
    })
    if (!f) {
      setDocValidation(prev => { const n = { ...prev }; delete n[key]; return n })
      return
    }
    setDocValidation(prev => ({ ...prev, [key]: { status: "checking", message: "" } }))
    try {
      const fd = new FormData()
      fd.append("file", f)
      const res = await fetch(`${API}/validate-document/${key}`, { method: "POST", body: fd })
      if (res.ok) {
        const data = await res.json()
        const isDefinitelyInvalid = data.valid === false && !data.vision_unavailable
        const visionUnavailable = !!data.vision_unavailable
        setDocValidation(prev => ({
          ...prev,
          [key]: {
            status: isDefinitelyInvalid ? "invalid" : data.valid ? "valid" : "unknown",
            message: data.message ?? "",
            visionUnavailable,
          },
        }))
        // Tapu için Vision'dan çıkarılan il/ilçe/m² bilgilerini otomatik doldur
        if (key === "house_file" && data.valid) {
          setValues(prev => ({
            ...prev,
            ...(data.il         && !prev.city          ? { city:          data.il }                : {}),
            ...(data.ilce       && !prev.district       ? { district:      data.ilce }              : {}),
            ...(data.yuzolcumu  && !prev.square_meters  ? { square_meters: String(data.yuzolcumu) } : {}),
          }))
        }
        // Transkript için Vision'dan çıkarılan GNO/sistem bilgilerini doldur — her yüklemede güncelle
        if (key === "transcript_file" && data.valid && data.gno != null) {
          setValues(prev => ({
            ...prev,
            gpa: String(data.gno),
            ...(data.sistem ? { gpa_system: String(data.sistem) } : {}),
          }))
        }
      } else {
        setDocValidation(prev => ({
          ...prev,
          [key]: { status: "unknown", message: "⚠️ Doğrulama servisi yanıt vermedi. Belge kabul edildi, manuel incelemeye alınacak.", visionUnavailable: true },
        }))
      }
    } catch {
      setDocValidation(prev => ({
        ...prev,
        [key]: { status: "unknown", message: "⚠️ Doğrulama servisi yanıt vermedi. Belge kabul edildi ancak manuel incelemeye alınacak.", visionUnavailable: true },
      }))
    }
  }

  async function handleSubmit() {
    if (!scholarship) return
    setLoading(true)
    setSubmitError(null)
    try {
      const fd = new FormData()
      // identity
      ;["first_name","last_name","tc_no","birth_date","phone","email",
        "university","department","grade","gender"].forEach(k => {
        fd.append(k, values[k] || "")
      })
      // car/house sub-fields
      ;["car_brand","car_model","car_year","car_damage",
        "city","district","square_meters"].forEach(k => {
        fd.append(k, values[k] || "")
      })
      // scholarship questions — hem doğrudan ekle (eski alanlar için)
      // hem de extra_fields JSON olarak gönder (yeni/custom sorular backend'e ulaşsın)
      const extraFields: Record<string, string> = {}
      scholarship.config.questions.forEach(q => {
        const val = values[q.id] ?? (q.type === "yesno" ? "no" : "")
        fd.append(q.id, val)
        extraFields[q.id] = val
      })
      fd.append("extra_fields", JSON.stringify(extraFields))
      // Araç/tapu dosyası yüklendiyse has_car/has_house'u zorla "yes" yap
      // (scholarship'ta bu soru yoksa bile backend değer hesaplasın)
      if (files["car_file"])   fd.set("has_car",   "yes")
      if (files["house_file"]) fd.set("has_house", "yes")
      // files
      scholarship.config.documents.forEach(docId => {
        if (files[docId]) fd.append(docId, files[docId])
      })

      const res = await fetch(`${API}/scholarship/${id}/apply`, { method: "POST", body: fd })
      if (!res.ok) {
        const txt = await res.text().catch(() => `HTTP ${res.status}`)
        throw new Error(txt)
      }
      const data = await res.json()

      // ── RAG debug logları (browser console) ────────────────────────────
      // Sunucuda araç/konut değer tahmini nasıl yapıldı, hangi fiyatlar bulundu,
      // outlier filtresi sonrası ne kaldı, web_search mi yoksa fallback formül mü.
      try {
        console.log("[apply] full backend response:", data)
        const dbg = data?._rag_debug
        if (!dbg) {
          console.warn("[RAG] _rag_debug alanı yok — backend eski kod çalıştırıyor olabilir")
        }
        if (dbg) {
          console.groupCollapsed("%c[RAG] Değerleme debug", "color:#4f46e5;font-weight:bold")
          const tierLabel = (t: number | undefined) =>
            t === 1 ? "Tier 1: Gerçek ilanlar"
            : t === 2 ? "Tier 2: Claude segment tahmini"
            : "Tier 3: Marka/şehir formülü (fallback)"
          if (dbg.car) {
            console.groupCollapsed("ARAÇ")
            console.log("tier:", tierLabel(dbg.car.trace?.find((s: { tier?: number }) => s?.tier)?.tier))
            console.log("source:", dbg.car.source, "| confidence:", dbg.car.confidence)
            console.log("estimate:", dbg.car.estimate, "TL")
            console.log("raw_prices:", dbg.car.raw_prices)
            console.log("filtered_prices (IQR):", dbg.car.filtered_prices)
            console.log("reasoning:", dbg.car.reasoning)
            console.log("trace:", dbg.car.trace)
            if (dbg.car.error) console.error("error:", dbg.car.error)
            console.groupEnd()
          }
          if (dbg.property) {
            console.groupCollapsed("KONUT")
            console.log("tier:", tierLabel(dbg.property.trace?.find((s: { tier?: number }) => s?.tier)?.tier))
            console.log("source:", dbg.property.source, "| confidence:", dbg.property.confidence)
            console.log("estimate:", dbg.property.estimate, "TL  (m²:", dbg.property.m2_price, "TL)")
            console.log("raw_prices:", dbg.property.raw_prices)
            console.log("filtered_prices (IQR):", dbg.property.filtered_prices)
            console.log("reasoning:", dbg.property.reasoning)
            console.log("trace:", dbg.property.trace)
            if (dbg.property.error) console.error("error:", dbg.property.error)
            console.groupEnd()
          }
          console.groupEnd()
        }
      } catch {}

      setResult(data)
      setStep(3)
      try { localStorage.removeItem(DRAFT_KEY) } catch {}
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e)
      const isFetch = msg.toLowerCase().includes("fetch") || msg.toLowerCase().includes("network")
      setSubmitError(
        isFetch
          ? "Sunucuya bağlanılamadı. İnternet bağlantınızı kontrol edip tekrar deneyin."
          : `Gönderim hatası: ${msg.slice(0, 200)}`
      )
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

            {/* KVKK Açık Rıza */}
            <div className="bg-white rounded-2xl border border-slate-100 shadow-sm p-5 space-y-3">
              <div className="flex items-center justify-between">
                <h3 className="font-bold text-slate-700 text-sm flex items-center gap-2">
                  <span>🔒</span> Kişisel Verilerin Korunması (KVKK)
                </h3>
                <button
                  type="button"
                  onClick={() => setKvkkOpen(v => !v)}
                  className="text-xs text-indigo-600 font-semibold hover:underline"
                >
                  {kvkkOpen ? "Gizle ▲" : "Metni Oku ▼"}
                </button>
              </div>

              {kvkkOpen && (
                <div className="bg-slate-50 border border-slate-200 rounded-xl p-4 max-h-64 overflow-y-auto text-xs text-slate-600 leading-relaxed whitespace-pre-wrap font-mono">
                  {KVKK_TEXT}
                </div>
              )}

              <label className="flex items-start gap-3 cursor-pointer select-none">
                <input
                  type="checkbox"
                  checked={kvkkAccepted}
                  onChange={e => setKvkkAccepted(e.target.checked)}
                  className="mt-0.5 w-4 h-4 accent-indigo-600 shrink-0"
                />
                <span className="text-xs text-slate-600 leading-snug">
                  Yukarıdaki bilgilendirmeyi okuduğumu ve anladığımı; kişisel verilerimin açıklanan amaçlar ve kapsam dahilinde işlenmesine,{" "}
                  <span className="font-semibold">Anthropic Inc.'e yurt dışı aktarım dahil olmak üzere</span>, özgür irademle rıza verdiğimi beyan ederim.
                </span>
              </label>

              {!kvkkAccepted && (
                <p className="text-xs text-amber-600 font-medium">
                  ⚠️ Devam edebilmek için KVKK aydınlatma metnini onaylamanız gerekmektedir.
                </p>
              )}
            </div>

            <button
              onClick={() => goStep(1)}
              disabled={!values.first_name || !values.last_name || !kvkkAccepted}
              className="w-full rounded-xl bg-gradient-to-r from-indigo-600 to-violet-600 text-white font-bold py-3 disabled:opacity-50 disabled:cursor-not-allowed"
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
                // Engellilik raporu sadece "has_disability = yes" seçiliyse göster
                if (docId === "disability_report" && values["has_disability"] !== "yes") return null

                const meta   = DOC_LABELS[docId] || { label: docId, icon: "📄" }
                const file   = files[docId]
                const dv     = docValidation[docId]
                const status = dv?.status ?? "idle"

                const borderCls = !file ? "border-slate-200"
                  : status === "checking" ? "border-amber-300 bg-amber-50"
                  : status === "valid"    ? "border-emerald-300 bg-emerald-50"
                  : status === "invalid"  ? "border-red-300 bg-red-50"
                  : status === "unknown"  ? "border-amber-200 bg-amber-50"
                  : "border-slate-200"

                const fileCls = !file
                  ? "border-slate-300 text-slate-400 hover:border-indigo-300 hover:text-indigo-500"
                  : status === "checking" ? "border-amber-300 text-amber-600"
                  : status === "valid"    ? "border-emerald-300 text-emerald-600"
                  : status === "invalid"  ? "border-red-300 text-red-500"
                  : "border-amber-200 text-amber-600"

                return (
                  <div key={docId} className={`p-4 rounded-xl border-2 transition ${borderCls}`}>
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <span className="text-xl">{meta.icon}</span>
                        <span className="text-sm font-semibold text-slate-800">{meta.label}</span>
                      </div>
                      {file && (
                        status === "checking" ? (
                          <span className="flex items-center gap-1 text-xs text-amber-600 font-semibold">
                            <span className="w-3 h-3 border-2 border-amber-500 border-t-transparent rounded-full animate-spin" />
                            Doğrulanıyor…
                          </span>
                        ) : status === "valid" ? (
                          <span className="text-xs text-emerald-600 font-semibold">✅ Geçerli</span>
                        ) : status === "invalid" ? (
                          <span className="text-xs text-red-600 font-semibold">❌ Geçersiz</span>
                        ) : (
                          <span className="text-xs text-amber-600 font-semibold">⚠️ Doğrulanamadı</span>
                        )
                      )}
                    </div>
                    {/* Transkript için notlama sistemi seçimi — yüklemeden önce seçin */}
                    {docId === "transcript_file" && (
                      <div className="mb-3 space-y-1">
                        <p className="text-xs font-semibold text-slate-600">Notlama Sistemi (önce seçin):</p>
                        <div className="flex gap-2">
                          {GPA_SYSTEM_OPTIONS.map(o => (
                            <button
                              key={o.val}
                              type="button"
                              onClick={() => setValues(p => ({ ...p, gpa_system: o.val }))}
                              className={`flex-1 py-1.5 text-xs font-semibold rounded-lg border-2 transition ${
                                values["gpa_system"] === o.val
                                  ? "border-indigo-500 bg-indigo-50 text-indigo-700"
                                  : "border-slate-200 bg-white text-slate-500 hover:border-indigo-300"
                              }`}
                            >
                              {o.label}
                            </button>
                          ))}
                        </div>
                      </div>
                    )}
                    <label className="block cursor-pointer">
                      <div className={`border-2 border-dashed rounded-xl p-3 text-center text-xs transition ${fileCls}`}>
                        {file ? file.name : "PDF seçmek için tıklayın"}
                      </div>
                      <input type="file" accept=".pdf"
                        onChange={e => setFile(docId, e.target.files?.[0] || null)}
                        className="hidden" />
                    </label>
                    {file && status !== "checking" && dv?.message && (
                      <p className={`mt-2 text-xs font-medium leading-snug
                        ${status === "valid" ? "text-emerald-700"
                        : status === "invalid" ? "text-red-600"
                        : "text-amber-700"}`}>
                        {dv.message}
                      </p>
                    )}

                    {/* Transkript — okunan GNO göster */}
                    {file && status === "valid" && docId === "transcript_file" && values["gpa"] && (
                      <p className="mt-2 text-xs font-semibold text-emerald-700">
                        📊 Okunan GNO: <strong>{values["gpa"]}</strong>
                        {values["gpa_system"] ? ` (${values["gpa_system"] === "4" ? "4.0 sistemi" : "100'lük sistem"})` : ""}
                      </p>
                    )}

                    {/* Manuel giriş — Vision okuyamadığında veya servis erişilemediğinde */}
                    {file && status !== "checking" && status !== "invalid" && (dv?.visionUnavailable || status === "unknown") && docId === "car_file" && (
                      <div className="mt-3 pt-3 border-t border-amber-200 space-y-2">
                        <p className="text-xs font-semibold text-amber-800">Araç bilgilerini girin (fiyat tahmini için):</p>
                        <div className="grid grid-cols-2 gap-2">
                          {/* Marka */}
                          <select
                            className="col-span-1 px-2 py-1.5 text-xs border border-amber-300 rounded-lg bg-white focus:outline-none focus:ring-1 focus:ring-amber-400"
                            value={values["car_brand"] || ""}
                            onChange={e => setValues(p => ({ ...p, car_brand: e.target.value, car_model: "" }))}
                          >
                            <option value="">— Marka seçin —</option>
                            {Object.keys(CAR_BRANDS).sort().map(b => (
                              <option key={b} value={b}>{b}</option>
                            ))}
                          </select>
                          {/* Model — markaya göre dinamik */}
                          <select
                            className="col-span-1 px-2 py-1.5 text-xs border border-amber-300 rounded-lg bg-white focus:outline-none focus:ring-1 focus:ring-amber-400 disabled:opacity-40"
                            value={values["car_model"] || ""}
                            disabled={!values["car_brand"]}
                            onChange={e => setValues(p => ({ ...p, car_model: e.target.value }))}
                          >
                            <option value="">— Model seçin —</option>
                            {(CAR_BRANDS[values["car_brand"] || ""] || []).map(m => (
                              <option key={m} value={m}>{m}</option>
                            ))}
                          </select>
                          {/* Yıl */}
                          <select
                            className="col-span-1 px-2 py-1.5 text-xs border border-amber-300 rounded-lg bg-white focus:outline-none focus:ring-1 focus:ring-amber-400"
                            value={values["car_year"] || ""}
                            onChange={e => setValues(p => ({ ...p, car_year: e.target.value }))}
                          >
                            <option value="">— Yıl —</option>
                            {Array.from({ length: 30 }, (_, i) => 2025 - i).map(y => (
                              <option key={y} value={y}>{y}</option>
                            ))}
                          </select>
                          {/* Hasar */}
                          <select
                            className="col-span-1 px-2 py-1.5 text-xs border border-amber-300 rounded-lg bg-white focus:outline-none focus:ring-1 focus:ring-amber-400"
                            value={values["car_damage"] || "no"}
                            onChange={e => setValues(p => ({ ...p, car_damage: e.target.value }))}
                          >
                            <option value="no">Hasar kaydı yok</option>
                            <option value="yes">Hasar kaydı var</option>
                          </select>
                        </div>
                      </div>
                    )}

                    {file && status !== "checking" && status !== "invalid" && docId === "house_file" && (
                      <div className="mt-3 pt-3 border-t border-amber-200 space-y-2">
                        <p className="text-xs font-semibold text-amber-800">
                          {(dv?.visionUnavailable || status === "unknown")
                            ? "Tapu bilgilerini manuel girin:"
                            : "Tapudan okunan bilgiler (gerekirse düzeltin):"}
                        </p>
                        <div className="grid grid-cols-2 gap-2">
                          <input
                            className="col-span-1 px-2 py-1.5 text-xs border border-amber-300 rounded-lg bg-white focus:outline-none focus:ring-1 focus:ring-amber-400"
                            placeholder="Şehir (ör. İstanbul)"
                            value={values["city"] || ""}
                            onChange={e => setValues(p => ({ ...p, city: e.target.value }))}
                          />
                          <input
                            className="col-span-1 px-2 py-1.5 text-xs border border-amber-300 rounded-lg bg-white focus:outline-none focus:ring-1 focus:ring-amber-400"
                            placeholder="İlçe (ör. Kadıköy)"
                            value={values["district"] || ""}
                            onChange={e => setValues(p => ({ ...p, district: e.target.value }))}
                          />
                          <input
                            className="col-span-2 px-2 py-1.5 text-xs border border-amber-300 rounded-lg bg-white focus:outline-none focus:ring-1 focus:ring-amber-400"
                            placeholder="Alan (m²) ör. 95"
                            type="number"
                            value={values["square_meters"] || ""}
                            onChange={e => setValues(p => ({ ...p, square_meters: e.target.value }))}
                          />
                        </div>
                      </div>
                    )}
                  </div>
                )
              })}
            </div>

            {/* Geçersiz belge uyarısı — gönderimi engeller */}
            {Object.values(docValidation).some(v => v.status === "invalid") && (
              <div className="bg-red-50 border-2 border-red-300 rounded-xl p-4 text-sm text-red-700 space-y-1">
                <p className="font-bold">❌ Geçersiz belge tespit edildi</p>
                <p>Lütfen kırmızı işaretli belgeleri kaldırıp doğru belgeyi yükleyin. Yanlış belgeyle başvuru gönderilemez.</p>
              </div>
            )}

            {/* Gönderim hatası */}
            {submitError && (
              <div className="bg-red-50 border-2 border-red-300 rounded-xl p-4 space-y-2">
                <p className="text-sm font-bold text-red-700">❌ Başvuru gönderilemedi</p>
                <p className="text-xs text-red-600">{submitError}</p>
                <button
                  onClick={handleSubmit}
                  className="mt-1 px-4 py-2 bg-red-600 hover:bg-red-700 text-white text-xs font-bold rounded-lg"
                >
                  Tekrar Dene
                </button>
              </div>
            )}

            <div className="flex gap-3">
              <button onClick={() => goStep(1)} className="flex-1 rounded-xl bg-slate-100 text-slate-700 font-semibold py-3 text-sm">← Geri</button>
              <button
                onClick={handleSubmit}
                disabled={
                  loading ||
                  Object.values(docValidation).some(v => v.status === "checking") ||
                  Object.values(docValidation).some(v => v.status === "invalid")
                }
                className="flex-1 rounded-xl bg-gradient-to-r from-emerald-500 to-teal-500 text-white font-bold py-3 text-sm disabled:opacity-40 disabled:cursor-not-allowed"
              >
                {loading ? (
                  <span className="flex items-center justify-center gap-2">
                    <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                    Analiz ediliyor…
                  </span>
                ) : Object.values(docValidation).some(v => v.status === "checking")
                  ? "Belgeler kontrol ediliyor…"
                  : "Başvuruyu Gönder →"}
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
                {Object.entries(result.breakdown || {}).map(([key, val]) => {
                  // Parametric scoring returns objects; legacy scoring returns numbers
                  const isObj = typeof val === "object" && val !== null
                  const points = isObj ? (val as { points: number }).points : Number(val)
                  const score  = isObj ? (val as { score: number }).score  : Number(val)
                  const answer = isObj ? (val as { answer: string }).answer : undefined
                  const weight = isObj ? (val as { weight: number }).weight : undefined
                  const barPct = isObj
                    ? Math.min(Math.abs(score), 100)
                    : Math.min(Math.abs(points) * 3, 100)
                  return (
                    <div key={key}>
                      <div className="flex justify-between text-xs mb-1">
                        <span className="text-slate-500 capitalize">{key.replace(/_/g, " ")}</span>
                        <div className="text-right">
                          <span className={`font-bold ${points < 0 ? "text-red-500" : "text-indigo-600"}`}>
                            {points > 0 ? `+${points}` : points} pts
                          </span>
                          {answer !== undefined && (
                            <span className="ml-2 text-slate-400">({answer}{weight !== undefined ? `, w:${weight}%` : ""})</span>
                          )}
                        </div>
                      </div>
                      <div className="w-full bg-slate-100 rounded-full h-1.5">
                        <div
                          className={`h-1.5 rounded-full ${points < 0 ? "bg-red-400" : "bg-indigo-500"}`}
                          style={{ width: `${isNaN(barPct) ? 0 : barPct}%` }}
                        />
                      </div>
                    </div>
                  )
                })}
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
