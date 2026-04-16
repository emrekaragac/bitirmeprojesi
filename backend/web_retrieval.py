"""
PSDS — Gerçek Zamanlı Web Fiyat Çekici
Arabam.com / Hepsiemlak.com / Sahibinden.com

Bot koruması nedeniyle scraping başarısız olursa boş liste döner
→ rag_valuation.py Claude'a genel bilgiyle tahmin yaptırır.
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
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Cache-Control": "no-cache",
}
_TIMEOUT = 15


def _extract_prices(html: str, min_val: int, max_val: int) -> list[int]:
    """
    HTML içindeki TL fiyat örüntülerini çıkar.
    Format desteği: 1.200.000 TL | 1,200,000 TL | 1.200.000 ₺ | 1200000
    """
    prices = []
    # Noktalı/virgüllü fiyatlar
    pattern1 = r"([\d]{1,3}(?:[.,][\d]{3})+)\s*(?:TL|₺)"
    for tok in re.findall(pattern1, html, re.IGNORECASE):
        clean = tok.replace(".", "").replace(",", "")
        try:
            val = int(clean)
            if min_val <= val <= max_val:
                prices.append(val)
        except ValueError:
            pass
    # JSON benzeri ham sayılar (data-price gibi attributelerde)
    pattern2 = r'"price"\s*:\s*"?([\d]{6,9})"?'
    for tok in re.findall(pattern2, html):
        try:
            val = int(tok)
            if min_val <= val <= max_val:
                prices.append(val)
        except ValueError:
            pass
    return list(set(prices))  # duplikatları kaldır


def _fetch(url: str) -> Optional[str]:
    if not _WEB_OK:
        return None
    try:
        with httpx.Client(
            timeout=_TIMEOUT,
            headers=_HEADERS,
            follow_redirects=True,
        ) as client:
            r = client.get(url)
            if r.status_code == 200 and len(r.text) > 5000:
                return r.text
            print(f"[WEB] {url} → HTTP {r.status_code}, len={len(r.text)}")
    except Exception as e:
        print(f"[WEB] fetch error {url}: {e}")
    return None


_TR_MAP = str.maketrans("çğıöşüÇĞİÖŞÜ", "cgiosuCGIOSU")

def _slugify(s: str) -> str:
    return s.lower().translate(_TR_MAP).replace(" ", "-").strip("-")


# ─── ARAÇ: arabam.com ──────────────────────────────────────────

def fetch_car_prices(brand: str, model: str, year: int) -> dict:
    slug_brand = _slugify(brand)
    slug_model = _slugify(model) if model else ""

    base = "https://www.arabam.com/ikinci-el/otomobil"
    slug = f"{slug_brand}-{slug_model}".strip("-")

    urls = [
        f"{base}/{slug}?minYear={year - 1}&maxYear={year + 1}",
        f"{base}/{slug_brand}?query={slug_model}&minYear={year - 1}&maxYear={year + 1}",
        f"{base}/{slug}",
    ]

    for url in urls:
        html = _fetch(url)
        if not html:
            continue
        prices = _extract_prices(html, min_val=100_000, max_val=25_000_000)
        if len(prices) >= 3:
            prices.sort()
            trimmed = prices[1:-1] if len(prices) > 6 else prices  # uç değerleri at
            print(f"[WEB] arabam.com → {len(trimmed)} fiyat, medyan={statistics.median(trimmed):,}")
            return {
                "found": True,
                "prices": trimmed[:30],
                "avg": int(statistics.mean(trimmed[:30])),
                "median": int(statistics.median(trimmed[:30])),
                "count": len(trimmed[:30]),
                "url": url,
            }

    return {"found": False, "prices": [], "avg": 0, "median": 0, "count": 0, "url": ""}


def fetch_car_prices_sahibinden(brand: str, model: str, year: int) -> dict:
    query = f"{brand}+{model}+{year}".replace(" ", "+")
    urls = [
        f"https://www.sahibinden.com/otomobil?query={query}&minYear={year-1}&maxYear={year+1}",
        f"https://www.sahibinden.com/otomobil?query={brand}+{model}&minYear={year-1}&maxYear={year+1}",
    ]
    for url in urls:
        html = _fetch(url)
        if not html:
            continue
        prices = _extract_prices(html, min_val=100_000, max_val=25_000_000)
        if len(prices) >= 3:
            prices.sort()
            trimmed = prices[1:-1] if len(prices) > 6 else prices
            return {
                "found": True,
                "prices": trimmed[:30],
                "avg": int(statistics.mean(trimmed[:30])),
                "median": int(statistics.median(trimmed[:30])),
                "count": len(trimmed[:30]),
                "url": url,
            }
    return {"found": False, "prices": [], "avg": 0, "median": 0, "count": 0, "url": urls[0]}


# ─── EMLAK: hepsiemlak.com ─────────────────────────────────────

def fetch_property_prices(city: str, district: str) -> dict:
    slug_city = _slugify(city)
    slug_dist = _slugify(district) if district else ""

    urls = []
    if slug_dist:
        urls.append(f"https://www.hepsiemlak.com/{slug_city}-{slug_dist}-satilik-daire")
        urls.append(f"https://www.hepsiemlak.com/{slug_city}-{slug_dist}-satilik")
    urls.append(f"https://www.hepsiemlak.com/{slug_city}-satilik-daire")

    for url in urls:
        html = _fetch(url)
        if not html:
            continue
        prices = _extract_prices(html, min_val=500_000, max_val=200_000_000)
        if len(prices) >= 3:
            prices.sort()
            trimmed = prices[1:-1] if len(prices) > 6 else prices
            print(f"[WEB] hepsiemlak.com → {len(trimmed)} fiyat, medyan={statistics.median(trimmed):,}")
            return {
                "found": True,
                "prices": trimmed[:30],
                "avg_total": int(statistics.mean(trimmed[:30])),
                "median_total": int(statistics.median(trimmed[:30])),
                "count": len(trimmed[:30]),
                "url": url,
            }

    return {"found": False, "prices": [], "avg_total": 0, "median_total": 0, "count": 0, "url": ""}


def fetch_property_prices_sahibinden(city: str, district: str) -> dict:
    slug_city = _slugify(city)
    slug_dist = _slugify(district) if district else ""

    urls = []
    if slug_dist:
        urls.append(f"https://www.sahibinden.com/satilik-konut/{slug_city}/{slug_dist}")
    urls.append(f"https://www.sahibinden.com/satilik-konut/{slug_city}")
    urls.append(f"https://www.sahibinden.com/satilik?query={city}+{district}+daire")

    for url in urls:
        html = _fetch(url)
        if not html:
            continue
        prices = _extract_prices(html, min_val=500_000, max_val=200_000_000)
        if len(prices) >= 3:
            prices.sort()
            trimmed = prices[1:-1] if len(prices) > 6 else prices
            return {
                "found": True,
                "prices": trimmed[:30],
                "avg_total": int(statistics.mean(trimmed[:30])),
                "median_total": int(statistics.median(trimmed[:30])),
                "count": len(trimmed[:30]),
                "url": url,
            }
    return {"found": False, "prices": [], "avg_total": 0, "median_total": 0, "count": 0, "url": urls[0]}
