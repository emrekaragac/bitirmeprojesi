"""
PSDS — Araç ve Konut Fiyat Çekici

Pipeline:
  1. DuckDuckGo arama → arabam.com / sahibinden.com URL'leri bul
  2. Listing sayfalarını scrape et
  3. Regex ile TL fiyatları çıkar (min 10 kayıt hedefi)
  4. IQR yöntemiyle outlier temizle
  5. Ortalama / medyan döndür
"""

import re
import statistics
from typing import Optional

try:
    import httpx
    _WEB_OK = True
except ImportError:
    _WEB_OK = False


_HEADERS = {
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
        headers = {**_HEADERS, **(extra_headers or {})}
        with httpx.Client(timeout=_TIMEOUT, headers=headers, follow_redirects=True) as client:
            r = client.get(url)
            if r.status_code == 200 and len(r.text) > 3000:
                return r.text
            print(f"[WEB] {url[:80]} → HTTP {r.status_code}, len={len(r.text)}")
    except Exception as e:
        print(f"[WEB] fetch error: {e}")
    return None


# ── Fiyat çıkarma ────────────────────────────────────────────────────────────

_PRICE_PATTERNS = [
    r'(\d{1,3}(?:\.\d{3})+)\s*(?:TL|₺)',          # 1.500.000 TL
    r'(?:TL|₺)\s*(\d{1,3}(?:\.\d{3})+)',          # ₺ 1.500.000
    r'"price"\s*:\s*"?(\d{6,9})"?',               # JSON: "price": "1500000"
    r'data-price["\s=:]+(\d{6,9})',                # data attribute
    r'content["\s=:]+(\d{6,9})',                   # meta content
    r'(\d{1,3}(?:,\d{3})+)\s*(?:TL|₺)',           # 1,500,000 TL
    r'fiyat[^0-9]{0,10}(\d{6,9})',                 # fiyat: 1500000
]


def _extract_prices(html: str, min_val: int, max_val: int) -> list[int]:
    prices: set[int] = set()
    for pattern in _PRICE_PATTERNS:
        for tok in re.findall(pattern, html, re.IGNORECASE):
            clean = tok.replace(".", "").replace(",", "")
            try:
                val = int(clean)
                if min_val <= val <= max_val:
                    prices.add(val)
            except ValueError:
                pass
    return sorted(prices)


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


# ── DuckDuckGo arama → URL listesi ──────────────────────────────────────────

def _ddg_search_urls(query: str, domains: list[str]) -> list[str]:
    """DuckDuckGo HTML aramadan belirtilen domainlere ait URL'leri çıkarır."""
    q = query.replace(" ", "+")
    url = f"https://html.duckduckgo.com/html/?q={q}"
    html = _fetch(url, extra_headers={"Referer": "https://duckduckgo.com/"})
    if not html:
        return []
    # href içindeki URL'leri bul
    href_pattern = r'href="(https?://[^"]+)"'
    all_urls = re.findall(href_pattern, html)
    result = []
    for u in all_urls:
        if any(d in u for d in domains):
            # DuckDuckGo redirect URL'lerini temizle
            clean = re.sub(r'^https?://[^/]*duckduckgo[^/]*/l/\?uddg=', '', u)
            try:
                from urllib.parse import unquote
                clean = unquote(clean)
            except Exception:
                pass
            if any(d in clean for d in domains):
                result.append(clean)
    return list(dict.fromkeys(result))[:10]  # deduplicate, max 10


# ── ARAÇ fiyat çekme ─────────────────────────────────────────────────────────

def fetch_car_prices(brand: str, model: str, year: int) -> dict:
    """
    arabam.com ve sahibinden.com'dan araç fiyatları çeker.
    Min 10 kayıt hedefi, IQR outlier temizleme, ortalama/medyan döndürür.
    """
    sb = _slugify(brand)
    sm = _slugify(model) if model else ""
    all_prices: list[int] = []
    used_urls: list[str] = []

    # 1. arabam.com doğrudan arama sayfaları
    arabam_urls = [
        f"https://www.arabam.com/ikinci-el/otomobil/{sb}-{sm}?minYear={year}&maxYear={year}",
        f"https://www.arabam.com/ikinci-el/otomobil/{sb}-{sm}?minYear={year-1}&maxYear={year+1}",
        f"https://www.arabam.com/ikinci-el/otomobil/{sb}?query={sm}&minYear={year}&maxYear={year}",
        f"https://www.arabam.com/ikinci-el/otomobil/{sb}-{sm}",
    ]
    for url in arabam_urls:
        html = _fetch(url)
        if html:
            prices = _extract_prices(html, 100_000, 25_000_000)
            if prices:
                all_prices.extend(prices)
                used_urls.append(url)
                print(f"[WEB] arabam {url[-50:]} → {len(prices)} fiyat")
        if len(set(all_prices)) >= 10:
            break

    # 2. sahibinden.com doğrudan arama sayfaları
    if len(set(all_prices)) < 10:
        sahibinden_urls = [
            f"https://www.sahibinden.com/otomobil?query={brand}+{model}&minYear={year}&maxYear={year}",
            f"https://www.sahibinden.com/otomobil?query={brand}+{model}&minYear={year-1}&maxYear={year+1}",
        ]
        for url in sahibinden_urls:
            html = _fetch(url)
            if html:
                prices = _extract_prices(html, 100_000, 25_000_000)
                if prices:
                    all_prices.extend(prices)
                    used_urls.append(url)
                    print(f"[WEB] sahibinden {url[-50:]} → {len(prices)} fiyat")
            if len(set(all_prices)) >= 10:
                break

    # 3. DuckDuckGo arama → ek URL'ler
    if len(set(all_prices)) < 5:
        query = f"{year} {brand} {model} ikinci el fiyat arabam sahibinden"
        extra_urls = _ddg_search_urls(query, ["arabam.com", "sahibinden.com"])
        for url in extra_urls[:5]:
            html = _fetch(url)
            if html:
                prices = _extract_prices(html, 100_000, 25_000_000)
                if prices:
                    all_prices.extend(prices)
                    used_urls.append(url)
                    print(f"[WEB] DDG extra → {len(prices)} fiyat")
            if len(set(all_prices)) >= 10:
                break

    unique = sorted(set(all_prices))
    if not unique:
        return {"found": False, "prices": [], "avg": 0, "median": 0, "count": 0, "url": ""}

    filtered = _remove_outliers(unique)
    print(f"[WEB] Araç: {len(unique)} ham → {len(filtered)} temiz fiyat | ort={int(statistics.mean(filtered)):,} TL")

    return {
        "found": True,
        "prices": filtered,
        "raw_count": len(unique),
        "filtered_count": len(filtered),
        "avg": int(statistics.mean(filtered)),
        "median": int(statistics.median(filtered)),
        "count": len(filtered),
        "url": used_urls[0] if used_urls else "",
        "sources": used_urls,
    }


# ── EMLAK fiyat çekme ─────────────────────────────────────────────────────────

def fetch_property_prices(city: str, district: str) -> dict:
    """
    hepsiemlak.com ve sahibinden.com'dan konut fiyatları çeker.
    IQR outlier temizleme, m² bazlı ortalama döndürür.
    """
    sc = _slugify(city)
    sd = _slugify(district) if district else ""
    all_prices: list[int] = []
    used_urls: list[str] = []

    # 1. hepsiemlak.com
    he_urls = []
    if sd:
        he_urls.append(f"https://www.hepsiemlak.com/{sc}-{sd}-satilik-daire")
        he_urls.append(f"https://www.hepsiemlak.com/{sc}-{sd}-satilik")
    he_urls.append(f"https://www.hepsiemlak.com/{sc}-satilik-daire")
    he_urls.append(f"https://www.hepsiemlak.com/{sc}-satilik")

    for url in he_urls:
        html = _fetch(url)
        if html:
            prices = _extract_prices(html, 500_000, 200_000_000)
            if prices:
                all_prices.extend(prices)
                used_urls.append(url)
                print(f"[WEB] hepsiemlak → {len(prices)} fiyat")
        if len(set(all_prices)) >= 10:
            break

    # 2. sahibinden.com
    if len(set(all_prices)) < 10:
        sah_urls = []
        if sd:
            sah_urls.append(f"https://www.sahibinden.com/satilik-konut/{sc}/{sd}")
        sah_urls.append(f"https://www.sahibinden.com/satilik-konut/{sc}")
        sah_urls.append(f"https://www.sahibinden.com/satilik?query={city}+{district}+daire")

        for url in sah_urls:
            html = _fetch(url)
            if html:
                prices = _extract_prices(html, 500_000, 200_000_000)
                if prices:
                    all_prices.extend(prices)
                    used_urls.append(url)
                    print(f"[WEB] sahibinden konut → {len(prices)} fiyat")
            if len(set(all_prices)) >= 10:
                break

    # 3. DuckDuckGo arama
    if len(set(all_prices)) < 5:
        query = f"{city} {district} satilik daire fiyat hepsiemlak sahibinden"
        extra_urls = _ddg_search_urls(query, ["hepsiemlak.com", "sahibinden.com"])
        for url in extra_urls[:5]:
            html = _fetch(url)
            if html:
                prices = _extract_prices(html, 500_000, 200_000_000)
                if prices:
                    all_prices.extend(prices)
                    used_urls.append(url)
                    print(f"[WEB] DDG konut extra → {len(prices)} fiyat")
            if len(set(all_prices)) >= 10:
                break

    unique = sorted(set(all_prices))
    if not unique:
        return {"found": False, "prices": [], "avg_total": 0, "median_total": 0, "count": 0, "url": ""}

    filtered = _remove_outliers(unique)
    print(f"[WEB] Konut: {len(unique)} ham → {len(filtered)} temiz | ort={int(statistics.mean(filtered)):,} TL")

    return {
        "found": True,
        "prices": filtered,
        "raw_count": len(unique),
        "filtered_count": len(filtered),
        "avg_total": int(statistics.mean(filtered)),
        "median_total": int(statistics.median(filtered)),
        "count": len(filtered),
        "url": used_urls[0] if used_urls else "",
        "sources": used_urls,
    }
