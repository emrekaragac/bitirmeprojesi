"use client"

import { useMemo, useState } from "react"

type AnalyzeResult = {
  score: number
  priority: string
  decision: string
  reasons: string[]
  report?: string
  uploaded_files?: {
    car_file?: string
    house_file?: string
  }
  city?: string
  district?: string
  square_meters?: string
  avg_m2_price?: number | null
  property_estimated_value?: number | null
}

const cityDistrictMap: Record<string, string[]> = {
  Istanbul: [
    "Adalar",
    "Arnavutkoy",
    "Atasehir",
    "Avcilar",
    "Bagcilar",
    "Bahcelievler",
    "Bakirkoy",
    "Basaksehir",
    "Bayrampasa",
    "Besiktas",
    "Beykoz",
    "Beylikduzu",
    "Beyoglu",
    "Buyukcekmece",
    "Catalca",
    "Cekmekoy",
    "Esenler",
    "Esenyurt",
    "Eyupsultan",
    "Fatih",
    "Gaziosmanpasa",
    "Gungoren",
    "Kadikoy",
    "Kagithane",
    "Kartal",
    "Kucukcekmece",
    "Maltepe",
    "Pendik",
    "Sancaktepe",
    "Sariyer",
    "Silivri",
    "Sisli",
    "Sultanbeyli",
    "Sultangazi",
    "Tuzla",
    "Umraniye",
    "Uskudar",
    "Zeytinburnu",
  ],
}

const cities = [
  "Adana",
  "Adiyaman",
  "Afyonkarahisar",
  "Agri",
  "Amasya",
  "Ankara",
  "Antalya",
  "Artvin",
  "Aydin",
  "Balikesir",
  "Bilecik",
  "Bingol",
  "Bitlis",
  "Bolu",
  "Burdur",
  "Bursa",
  "Canakkale",
  "Cankiri",
  "Corum",
  "Denizli",
  "Diyarbakir",
  "Edirne",
  "Elazig",
  "Erzincan",
  "Erzurum",
  "Eskisehir",
  "Gaziantep",
  "Giresun",
  "Gumushane",
  "Hakkari",
  "Hatay",
  "Isparta",
  "Mersin",
  "Istanbul",
  "Izmir",
  "Kars",
  "Kastamonu",
  "Kayseri",
  "Kirklareli",
  "Kirsehir",
  "Kocaeli",
  "Konya",
  "Kutahya",
  "Malatya",
  "Manisa",
  "Kahramanmaras",
  "Mardin",
  "Mugla",
  "Mus",
  "Nevsehir",
  "Nigde",
  "Ordu",
  "Rize",
  "Sakarya",
  "Samsun",
  "Siirt",
  "Sinop",
  "Sivas",
  "Tekirdag",
  "Tokat",
  "Trabzon",
  "Tunceli",
  "Sanliurfa",
  "Usak",
  "Van",
  "Yozgat",
  "Zonguldak",
  "Aksaray",
  "Bayburt",
  "Karaman",
  "Kirikkale",
  "Batman",
  "Sirnak",
  "Bartin",
  "Ardahan",
  "Igdir",
  "Yalova",
  "Karabuk",
  "Kilis",
  "Osmaniye",
  "Duzce",
]

function formatCurrency(value?: number | null) {
  if (value === null || value === undefined || Number.isNaN(value)) return "-"
  return new Intl.NumberFormat("tr-TR", {
    style: "currency",
    currency: "TRY",
    maximumFractionDigits: 0,
  }).format(value)
}

export default function Page() {
  const [gender, setGender] = useState("")
  const [parentsDivorced, setParentsDivorced] = useState("")
  const [motherWorking, setMotherWorking] = useState("")
  const [everyoneHealthy, setEveryoneHealthy] = useState("")
  const [hasCar, setHasCar] = useState("")
  const [hasHouse, setHasHouse] = useState("")

  const [city, setCity] = useState("")
  const [district, setDistrict] = useState("")
  const [squareMeters, setSquareMeters] = useState("")

  const [carFile, setCarFile] = useState<File | null>(null)
  const [houseFile, setHouseFile] = useState<File | null>(null)

  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<AnalyzeResult | null>(null)
  const [error, setError] = useState("")

  const showDistrict = city === "Istanbul"
  const currentDistricts = useMemo(() => {
    if (city === "Istanbul") return cityDistrictMap.Istanbul
    return []
  }, [city])

  const handleCityChange = (value: string) => {
    setCity(value)
    if (value !== "Istanbul") {
      setDistrict("")
    }
  }

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    setLoading(true)
    setError("")
    setResult(null)

    try {
      const formData = new FormData()
      formData.append("gender", gender)
      formData.append("parents_divorced", parentsDivorced)
      formData.append("mother_working", motherWorking)
      formData.append("everyone_healthy", everyoneHealthy)
      formData.append("has_car", hasCar)
      formData.append("has_house", hasHouse)
      formData.append("city", city)
      formData.append("district", district)
      formData.append("square_meters", squareMeters)

      if (carFile) formData.append("car_file", carFile)
      if (houseFile) formData.append("house_file", houseFile)

      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:9001"
      const response = await fetch(`${apiUrl}/analyze`, {
        method: "POST",
        body: formData,
      })

      if (!response.ok) {
        const text = await response.text()
        throw new Error(text || "Request failed")
      }

      const data = await response.json()
      setResult(data)
    } catch (err) {
      console.error(err)
      setError("Something went wrong while analyzing the application.")
    } finally {
      setLoading(false)
    }
  }

  return (
    <main className="min-h-screen bg-slate-100 py-10 px-4">
      <div className="mx-auto max-w-4xl">
        <div className="rounded-2xl bg-white shadow-lg border border-slate-200 overflow-hidden">
          <div className="bg-slate-900 px-8 py-6">
            <h1 className="text-3xl font-bold text-white">
              Scholarship Decision Support System
            </h1>
            <p className="mt-2 text-slate-300">
              Fill in the form and generate a scholarship priority evaluation.
            </p>
          </div>

          <form onSubmit={handleSubmit} className="px-8 py-8 space-y-6">
            <div>
              <label className="block text-sm font-semibold text-slate-700 mb-2">
                Gender
              </label>
              <select
                value={gender}
                onChange={(e) => setGender(e.target.value)}
                className="w-full rounded-xl border border-slate-300 px-4 py-3 outline-none focus:ring-2 focus:ring-slate-400"
                required
              >
                <option value="">Select gender</option>
                <option value="Female">Female</option>
                <option value="Male">Male</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-semibold text-slate-700 mb-2">
                Are your parents divorced?
              </label>
              <select
                value={parentsDivorced}
                onChange={(e) => setParentsDivorced(e.target.value)}
                className="w-full rounded-xl border border-slate-300 px-4 py-3 outline-none focus:ring-2 focus:ring-slate-400"
                required
              >
                <option value="">Select option</option>
                <option value="Yes">Yes</option>
                <option value="No">No</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-semibold text-slate-700 mb-2">
                Is your mother working?
              </label>
              <select
                value={motherWorking}
                onChange={(e) => setMotherWorking(e.target.value)}
                className="w-full rounded-xl border border-slate-300 px-4 py-3 outline-none focus:ring-2 focus:ring-slate-400"
                required
              >
                <option value="">Select option</option>
                <option value="Yes">Yes</option>
                <option value="No">No</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-semibold text-slate-700 mb-2">
                Is everyone in the family healthy?
              </label>
              <select
                value={everyoneHealthy}
                onChange={(e) => setEveryoneHealthy(e.target.value)}
                className="w-full rounded-xl border border-slate-300 px-4 py-3 outline-none focus:ring-2 focus:ring-slate-400"
                required
              >
                <option value="">Select option</option>
                <option value="Yes">Yes</option>
                <option value="No">No</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-semibold text-slate-700 mb-2">
                Do you have a car?
              </label>
              <select
                value={hasCar}
                onChange={(e) => setHasCar(e.target.value)}
                className="w-full rounded-xl border border-slate-300 px-4 py-3 outline-none focus:ring-2 focus:ring-slate-400"
                required
              >
                <option value="">Select option</option>
                <option value="Yes">Yes</option>
                <option value="No">No</option>
              </select>
            </div>

            {hasCar === "Yes" && (
              <div>
                <label className="block text-sm font-semibold text-slate-700 mb-2">
                  Upload Vehicle License PDF
                </label>
                <input
                  type="file"
                  accept=".pdf,.jpg,.jpeg,.png"
                  onChange={(e) => setCarFile(e.target.files?.[0] || null)}
                  className="w-full rounded-xl border border-slate-300 px-4 py-3 bg-white"
                />
              </div>
            )}

            <div>
              <label className="block text-sm font-semibold text-slate-700 mb-2">
                Do you have a house?
              </label>
              <select
                value={hasHouse}
                onChange={(e) => setHasHouse(e.target.value)}
                className="w-full rounded-xl border border-slate-300 px-4 py-3 outline-none focus:ring-2 focus:ring-slate-400"
                required
              >
                <option value="">Select option</option>
                <option value="Yes">Yes</option>
                <option value="No">No</option>
              </select>
            </div>

            {hasHouse === "Yes" && (
              <>
                <div>
                  <label className="block text-sm font-semibold text-slate-700 mb-2">
                    Upload Title Deed PDF
                  </label>
                  <input
                    type="file"
                    accept=".pdf,.jpg,.jpeg,.png"
                    onChange={(e) => setHouseFile(e.target.files?.[0] || null)}
                    className="w-full rounded-xl border border-slate-300 px-4 py-3 bg-white"
                  />
                </div>

                <div>
                  <label className="block text-sm font-semibold text-slate-700 mb-2">
                    City
                  </label>
                  <select
                    value={city}
                    onChange={(e) => handleCityChange(e.target.value)}
                    className="w-full rounded-xl border border-slate-300 px-4 py-3 outline-none focus:ring-2 focus:ring-slate-400"
                    required={hasHouse === "Yes"}
                  >
                    <option value="">Select city</option>
                    {cities.map((cityName) => (
                      <option key={cityName} value={cityName}>
                        {cityName}
                      </option>
                    ))}
                  </select>
                </div>

                {showDistrict && (
                  <div>
                    <label className="block text-sm font-semibold text-slate-700 mb-2">
                      District
                    </label>
                    <select
                      value={district}
                      onChange={(e) => setDistrict(e.target.value)}
                      className="w-full rounded-xl border border-slate-300 px-4 py-3 outline-none focus:ring-2 focus:ring-slate-400"
                      required={city === "Istanbul"}
                    >
                      <option value="">Select district</option>
                      {currentDistricts.map((districtName) => (
                        <option key={districtName} value={districtName}>
                          {districtName}
                        </option>
                      ))}
                    </select>
                  </div>
                )}

                <div>
                  <label className="block text-sm font-semibold text-slate-700 mb-2">
                    House Size (m²)
                  </label>
                  <input
                    type="number"
                    min="1"
                    value={squareMeters}
                    onChange={(e) => setSquareMeters(e.target.value)}
                    className="w-full rounded-xl border border-slate-300 px-4 py-3 outline-none focus:ring-2 focus:ring-slate-400"
                    placeholder="Enter house size"
                    required={hasHouse === "Yes"}
                  />
                </div>
              </>
            )}

            {error && (
              <div className="rounded-xl bg-red-50 border border-red-200 px-4 py-3 text-red-700">
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full rounded-xl bg-slate-900 text-white font-semibold py-3 hover:bg-slate-800 transition disabled:opacity-60"
            >
              {loading ? "Analyzing..." : "Analyze Application"}
            </button>
          </form>

          {result && (
            <div className="border-t border-slate-200 px-8 py-8 bg-slate-50">
              <h2 className="text-2xl font-bold text-slate-900 mb-6">
                Analysis Result
              </h2>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
                <div className="rounded-2xl bg-white border border-slate-200 p-5 shadow-sm">
                  <p className="text-sm text-slate-500">Score</p>
                  <p className="text-3xl font-bold text-slate-900 mt-2">
                    {result.score ?? "-"}
                  </p>
                </div>

                <div className="rounded-2xl bg-white border border-slate-200 p-5 shadow-sm">
                  <p className="text-sm text-slate-500">Priority</p>
                  <p className="text-2xl font-bold text-slate-900 mt-2">
                    {result.priority ?? "-"}
                  </p>
                </div>

                <div className="rounded-2xl bg-white border border-slate-200 p-5 shadow-sm">
                  <p className="text-sm text-slate-500">Decision</p>
                  <p className="text-2xl font-bold text-slate-900 mt-2">
                    {result.decision ?? "-"}
                  </p>
                </div>
              </div>

              <div className="rounded-2xl bg-white border border-slate-200 p-6 shadow-sm mb-6">
                <h3 className="text-lg font-semibold text-slate-900 mb-4">
                  Property Valuation
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-slate-700">
                  <div>
                    <span className="font-semibold">City:</span>{" "}
                    {result.city || "-"}
                  </div>
                  <div>
                    <span className="font-semibold">District:</span>{" "}
                    {result.district || "-"}
                  </div>
                  <div>
                    <span className="font-semibold">Square meters:</span>{" "}
                    {result.square_meters || "-"}
                  </div>
                  <div>
                    <span className="font-semibold">Average m² price:</span>{" "}
                    {formatCurrency(result.avg_m2_price)}
                  </div>
                  <div className="md:col-span-2">
                    <span className="font-semibold">Estimated property value:</span>{" "}
                    {formatCurrency(result.property_estimated_value)}
                  </div>
                </div>
              </div>

              <div className="rounded-2xl bg-white border border-slate-200 p-6 shadow-sm mb-6">
                <h3 className="text-lg font-semibold text-slate-900 mb-4">
                  Reasons
                </h3>
                {result.reasons && result.reasons.length > 0 ? (
                  <ul className="list-disc pl-5 space-y-2 text-slate-700">
                    {result.reasons.map((reason, index) => (
                      <li key={index}>{reason}</li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-slate-500">No reasons returned.</p>
                )}
              </div>

              {result.report && (
                <div className="rounded-2xl bg-white border border-slate-200 p-6 shadow-sm">
                  <h3 className="text-lg font-semibold text-slate-900 mb-3">
                    Report
                  </h3>
                  <a
                    href={`${process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:9001"}/${result.report}`}
                    target="_blank"
                    rel="noreferrer"
                    className="inline-flex items-center rounded-xl bg-slate-900 px-4 py-2 text-white font-medium hover:bg-slate-800 transition"
                  >
                    Open Generated Report
                  </a>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </main>
  )
}