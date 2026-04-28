"""
PSDS — Araç ve Konut Fiyat Çekici

Pipeline:
  1. Google (→ DuckDuckGo fallback) arama
  2. Arama sonucu snippet metinlerinden TL fiyatlarını regex ile çek
  3. IQR ile outlier temizle
  4. Ortalama / medyan döndür
"""

import re
import statistics
from typing import Optional

try:
    import httpx
    _WEB_OK = True
except ImportError:
    _WEB_OK = False


_HEADERS_GOOGLE = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "tr-TR,tr;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Cache-Control": "no-cache",
    "DNT": "1",
}
_TIMEOUT = 15

_TR_MAP = str.maketrans("çğıöşüÇĞİÖŞÜ", "cgiosuCGIOSU")


def _slugify(s: str) -> str:
    return s.lower().translate(_TR_MAP).replace(" ", "-").strip("-")


def _fetch(url: str, extra_headers: dict | None = None) -> Optional[str]:
    if not _WEB_OK:
        return None
    try:
        headers = {**_HEADERS_GOOGLE, **(extra_headers or {})}
        with httpx.Client(timeout=_TIMEOUT, headers=headers, follow_redirects=True) as client:
            r = client.get(url)
            if r.status_code == 200 and len(r.text) > 3000:
                return r.text
            print(f"[WEB] {url[:80]} → HTTP {r.status_code}, len={len(r.text)}")
    except Exception as e:
        print(f"[WEB] fetch error: {e}")
    return None


# ── Arama sayfası çekme ──────────────────────────────────────────────────────

def _fetch_search(query: str) -> Optional[str]:
    """Google → DuckDuckGo sırasıyla dener, snippet HTML'i döndürür."""
    q = query.replace(" ", "+")
    urls = [
        f"https://www.google.com/search?q={q}&hl=tr&num=20&lr=lang_tr",
        f"https://html.duckduckgo.com/html/?q={q}&kl=tr-tr",
    ]
    for url in urls:
        referer = "https://www.google.com/" if "google" in url else "https://duckduckgo.com/"
        html = _fetch(url, extra_headers={"Referer": referer})
        if html and len(html) > 5000:
            print(f"[WEB] Search OK: {url[:60]}")
            return html
    return None


# ── Fiyat çıkarma (snippet metninden) ───────────────────────────────────────

_PRICE_RE = [
    r'(\d{1,3}(?:\.\d{3})+)\s*(?:TL|₺)',      # 12.249.900 TL
    r'(?:TL|₺)\s*(\d{1,3}(?:\.\d{3})+)',      # ₺ 12.249.900
    r'(\d{1,3}(?:,\d{3})+)\s*(?:TL|₺)',       # 12,249,900 TL
    r'"price"\s*:\s*"?(\d{6,10})"?',           # JSON "price":"12249900"
    r'data-price["\s=:]+(\d{6,10})',            # data-price="12249900"
]


def _extract_prices(text: str, min_val: int, max_val: int) -> list[int]:
    found: set[int] = set()
    for pat in _PRICE_RE:
        for tok in re.findall(pat, text, re.IGNORECASE):
            clean = tok.replace(".", "").replace(",", "")
            try:
                v = int(clean)
                if min_val <= v <= max_val:
                    found.add(v)
            except ValueError:
                pass
    return sorted(found)


# ── IQR outlier temizleme ────────────────────────────────────────────────────

def _remove_outliers(prices: list[int]) -> list[int]:
    if len(prices) < 4:
        return prices
    s = sorted(prices)
    n = len(s)
    q1 = s[n // 4]
    q3 = s[(3 * n) // 4]
    iqr = q3 - q1
    if iqr == 0:
        return prices
    lo = q1 - 1.5 * iqr
    hi = q3 + 1.5 * iqr
    filtered = [p for p in s if lo <= p <= hi]
    return filtered if len(filtered) >= 3 else s


# ── ARAÇ fiyat çekme ─────────────────────────────────────────────────────────

def fetch_car_prices(brand: str, model: str, year: int) -> dict:
    """
    Google/DDG'de arama yap, snippet'lerden fiyat çek, IQR uygula.

    Sorgular:
      1. "{year} {brand} {model} ikinci el fiyat sahibinden arabam"
      2. "site:sahibinden.com {year} {brand} {model} ikinci el"  (fallback)
    """
    all_prices: list[int] = []
    queries = [
        f"{year} {brand} {model} ikinci el fiyat sahibinden arabam",
        f"site:sahibinden.com {year} {brand} {model} ikinci el",
        f"site:arabam.com {year} {brand} {model}",
    ]

    for q in queries:
        html = _fetch_search(q)
        if html:
            prices = _extract_prices(html, 100_000, 80_000_000)
            if prices:
                all_prices.extend(prices)
                print(f"[WEB] Araç query '{q[:50]}' → {len(prices)} fiyat")
        if len(set(all_prices)) >= 10:
            break

    unique = sorted(set(all_prices))
    if not unique:
        return {"found": False, "prices": [], "avg": 0, "median": 0, "count": 0}

    filtered = _remove_outliers(unique)
    avg = int(statistics.mean(filtered))
    med = int(statistics.median(filtered))

    print(
        f"[WEB] Araç sonuç: {len(unique)} ham → {len(filtered)} temiz | "
        f"ort=₺{avg:,} | med=₺{med:,}"
    )

    return {
        "found": True,
        "prices": filtered,
        "raw_count": len(unique),
        "filtered_count": len(filtered),
        "avg": avg,
        "median": med,
        "count": len(filtered),
    }


# ── EMLAK fiyat çekme ─────────────────────────────────────────────────────────

def fetch_property_prices(city: str, district: str) -> dict:
    """
    Google/DDG'de konut araması yap, snippet'lerden fiyat çek, IQR uygula.
    """
    all_prices: list[int] = []
    loc = f"{city} {district}".strip()
    queries = [
        f"{loc} satilik daire fiyat hepsiemlak sahibinden",
        f"site:sahibinden.com {loc} satilik daire",
        f"site:hepsiemlak.com {loc} satilik",
    ]

    for q in queries:
        html = _fetch_search(q)
        if html:
            prices = _extract_prices(html, 500_000, 500_000_000)
            if prices:
                all_prices.extend(prices)
                print(f"[WEB] Konut query '{q[:50]}' → {len(prices)} fiyat")
        if len(set(all_prices)) >= 10:
            break

    unique = sorted(set(all_prices))
    if not unique:
        return {"found": False, "prices": [], "avg_total": 0, "median_total": 0, "count": 0}

    filtered = _remove_outliers(unique)
    avg = int(statistics.mean(filtered))
    med = int(statistics.median(filtered))

    print(
        f"[WEB] Konut sonuç: {len(unique)} ham → {len(filtered)} temiz | "
        f"ort=₺{avg:,} | med=₺{med:,}"
    )

    return {
        "found": True,
        "prices": filtered,
        "raw_count": len(unique),
        "filtered_count": len(filtered),
        "avg_total": avg,
        "median_total": med,
        "count": len(filtered),
    }
