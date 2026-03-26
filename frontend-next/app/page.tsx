"use client"

import { useMemo, useState } from "react"

type AnalyzeResult = {
  score: number
  priority: string
  decision: string
  reasons?: string[]
  report: string
  uploaded_files?: {
    car_file?: string
    house_file?: string
  }
  city?: string
  district?: string
  square_meters?: string
  avg_m2_price?: number
  property_estimated_value?: number
}

const cityDistrictMap: Record<string, string[]> = {
  Istanbul: [
    "Beylikduzu",
    "Basaksehir",
    "Kucukcekmece",
    "Fatih",
    "Pendik",
    "Sariyer",
    "Besiktas",
    "Uskudar",
    "Kadikoy",
  ],
}

export default function Home() {
  const [gender, setGender] = useState("female")
  const [parentsDivorced, setParentsDivorced] = useState("yes")
  const [motherWorking, setMotherWorking] = useState("no")
  const [everyoneHealthy, setEveryoneHealthy] = useState("no")
  const [hasCar, setHasCar] = useState("no")
  const [hasHouse, setHasHouse] = useState("no")

  const [city, setCity] = useState("")
  const [district, setDistrict] = useState("")
  const [squareMeters, setSquareMeters] = useState("")

  const [carFile, setCarFile] = useState<File | null>(null)
  const [houseFile, setHouseFile] = useState<File | null>(null)

  const [result, setResult] = useState<AnalyzeResult | null>(null)
  const [loading, setLoading] = useState(false)

  const districts = useMemo(() => {
    if (!city) return []
    return cityDistrictMap[city] || []
  }, [city])

  const handleSubmit = async () => {
    try {
      setLoading(true)

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

      const res = await fetch("http://127.0.0.1:8000/analyze", {
        method: "POST",
        body: formData,
      })

      if (!res.ok) {
        throw new Error("Backend response error")
      }

      const data = await res.json()
      setResult(data)
    } catch (error) {
      console.error(error)
      alert("Bir hata oluştu. Backend açık mı kontrol et.")
    } finally {
      setLoading(false)
    }
  }

  return (
    <main className="min-h-screen bg-slate-100 py-12 px-6 text-slate-900">
      <div className="max-w-3xl mx-auto">
        <div className="bg-white rounded-2xl shadow-xl p-8 border border-slate-200">
          <h1 className="text-4xl font-bold text-center text-slate-800 mb-3">
            Scholarship Decision Support System
          </h1>

          <p className="text-center text-slate-600 mb-8">
            Fill in the form and generate a scholarship priority evaluation.
          </p>

          <div className="space-y-5">
            <div>
              <label className="block mb-2 font-semibold text-slate-800">
                Gender
              </label>
              <select
                value={gender}
                onChange={(e) => setGender(e.target.value)}
                className="w-full border border-slate-300 bg-white text-slate-900 p-3 rounded-lg"
              >
                <option value="female">Female</option>
                <option value="male">Male</option>
              </select>
            </div>

            <div>
              <label className="block mb-2 font-semibold text-slate-800">
                Are your parents divorced?
              </label>
              <select
                value={parentsDivorced}
                onChange={(e) => setParentsDivorced(e.target.value)}
                className="w-full border border-slate-300 bg-white text-slate-900 p-3 rounded-lg"
              >
                <option value="yes">Yes</option>
                <option value="no">No</option>
              </select>
            </div>

            <div>
              <label className="block mb-2 font-semibold text-slate-800">
                Is your mother working?
              </label>
              <select
                value={motherWorking}
                onChange={(e) => setMotherWorking(e.target.value)}
                className="w-full border border-slate-300 bg-white text-slate-900 p-3 rounded-lg"
              >
                <option value="yes">Yes</option>
                <option value="no">No</option>
              </select>
            </div>

            <div>
              <label className="block mb-2 font-semibold text-slate-800">
                Is everyone in the family healthy?
              </label>
              <select
                value={everyoneHealthy}
                onChange={(e) => setEveryoneHealthy(e.target.value)}
                className="w-full border border-slate-300 bg-white text-slate-900 p-3 rounded-lg"
              >
                <option value="yes">Yes</option>
                <option value="no">No</option>
              </select>
            </div>

            <div>
              <label className="block mb-2 font-semibold text-slate-800">
                Do you have a car?
              </label>
              <select
                value={hasCar}
                onChange={(e) => setHasCar(e.target.value)}
                className="w-full border border-slate-300 bg-white text-slate-900 p-3 rounded-lg"
              >
                <option value="yes">Yes</option>
                <option value="no">No</option>
              </select>
            </div>

            {hasCar === "yes" && (
              <div>
                <label className="block mb-2 font-semibold text-slate-800">
                  Upload Vehicle Registration PDF
                </label>
                <input
                  type="file"
                  onChange={(e) => setCarFile(e.target.files?.[0] || null)}
                  className="w-full border border-slate-300 bg-white text-slate-900 p-3 rounded-lg"
                />
              </div>
            )}

            <div>
              <label className="block mb-2 font-semibold text-slate-800">
                Do you have a house?
              </label>
              <select
                value={hasHouse}
                onChange={(e) => {
                  setHasHouse(e.target.value)
                  if (e.target.value === "no") {
                    setCity("")
                    setDistrict("")
                    setSquareMeters("")
                    setHouseFile(null)
                  }
                }}
                className="w-full border border-slate-300 bg-white text-slate-900 p-3 rounded-lg"
              >
                <option value="yes">Yes</option>
                <option value="no">No</option>
              </select>
            </div>

            {hasHouse === "yes" && (
              <>
                <div>
                  <label className="block mb-2 font-semibold text-slate-800">
                    Upload Title Deed PDF
                  </label>
                  <input
                    type="file"
                    onChange={(e) => setHouseFile(e.target.files?.[0] || null)}
                    className="w-full border border-slate-300 bg-white text-slate-900 p-3 rounded-lg"
                  />
                </div>

                <div>
                  <label className="block mb-2 font-semibold text-slate-800">
                    City
                  </label>
                  <select
                    value={city}
                    onChange={(e) => {
                      setCity(e.target.value)
                      setDistrict("")
                    }}
                    className="w-full border border-slate-300 bg-white text-slate-900 p-3 rounded-lg"
                  >
                    <option value="">Select city</option>
                    <option value="Istanbul">Istanbul</option>
                  </select>
                </div>

                <div>
                  <label className="block mb-2 font-semibold text-slate-800">
                    District
                  </label>
                  <select
                    value={district}
                    onChange={(e) => setDistrict(e.target.value)}
                    disabled={!city}
                    className="w-full border border-slate-300 bg-white text-slate-900 p-3 rounded-lg disabled:bg-slate-100"
                  >
                    <option value="">Select district</option>
                    {districts.map((item) => (
                      <option key={item} value={item}>
                        {item}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block mb-2 font-semibold text-slate-800">
                    House Size (m²)
                  </label>
                  <input
                    type="number"
                    value={squareMeters}
                    onChange={(e) => setSquareMeters(e.target.value)}
                    className="w-full border border-slate-300 bg-white text-slate-900 p-3 rounded-lg"
                    placeholder="e.g. 100"
                  />
                </div>
              </>
            )}

            <button
              onClick={handleSubmit}
              disabled={loading}
              className="w-full bg-blue-600 text-white py-3 rounded-lg font-semibold hover:bg-blue-700 disabled:bg-slate-400"
            >
              {loading ? "Analyzing..." : "Analyze Application"}
            </button>
          </div>
        </div>

        {result && (
          <div className="mt-8 bg-white rounded-2xl shadow-xl p-8 border border-slate-200">
            <h2 className="text-2xl font-bold text-slate-800 mb-6">
              Evaluation Result
            </h2>

            <div className="space-y-3 text-slate-700">
              <p>
                <span className="font-semibold">Score:</span> {result.score}
              </p>
              <p>
                <span className="font-semibold">Priority:</span> {result.priority}
              </p>
              <p>
                <span className="font-semibold">Decision:</span> {result.decision}
              </p>

              {result.city && (
                <p>
                  <span className="font-semibold">City:</span> {result.city}
                </p>
              )}

              {result.district && (
                <p>
                  <span className="font-semibold">District:</span> {result.district}
                </p>
              )}

              {result.square_meters && (
                <p>
                  <span className="font-semibold">Square Meters:</span>{" "}
                  {result.square_meters}
                </p>
              )}

              {result.avg_m2_price && (
                <p>
                  <span className="font-semibold">Average m² Price:</span>{" "}
                  {result.avg_m2_price} TL
                </p>
              )}

              {result.property_estimated_value && (
                <p>
                  <span className="font-semibold">Estimated Property Value:</span>{" "}
                  {result.property_estimated_value} TL
                </p>
              )}

              {result.reasons && result.reasons.length > 0 && (
                <div className="pt-2">
                  <p className="font-semibold mb-2">Reasons:</p>
                  <ul className="list-disc pl-5 space-y-1">
                    {result.reasons.map((reason, index) => (
                      <li key={index}>{reason}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>

            <div className="mt-6">
              <a
                href={`http://127.0.0.1:8000/${result.report}`}
                target="_blank"
                rel="noreferrer"
                className="inline-block bg-black text-white px-5 py-3 rounded-lg hover:bg-slate-800"
              >
                Download Report
              </a>
            </div>
          </div>
        )}
      </div>
    </main>
  )
}