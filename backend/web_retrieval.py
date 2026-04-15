"""
PSDS — Gerçek Zamanlı Web Fiyat Çekici
Sahibinden.com  → emlak m² fiyatları
Arabam.com      → ikinci el araç fiyatları

Her iki site de başarısız olursa boş liste döner (rag_valuation fallback devreye girer).
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
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
}
_TIMEOUT = 12  # saniye


# ─── Yardımcı: HTML'den TL fiyat listesi çıkar ───────────────────────────────

def _extract_prices(html: str, min_val: int, max_val: int) -> list[int]:
    """
    HTML içindeki tüm TL fiyat örüntülerini yakalar.
    Desteklenen formatlar: 1.200.000 TL  |  1,200,000 TL  |  1.200.000 ₺
    """
    pattern = r"([\d]{1,3}(?:[.,][\d]{3})+)\s*(?:TL|₺)"
    raw = re.findall(pattern, html, re.IGNORECASE)
    prices = []
    for tok in raw:
        # Nokta ve virgülü temizle
        clean = tok.replace(".", "").replace(",", "")
        try:
            val = int(clean)
            if min_val <= val <= max_val:
                prices.append(val)
        except ValueError:
            pass
    return prices


def _fetch(url: str) -> Optional[str]:
    """HTTP GET, hata olursa None döner."""
    if not _WEB_OK:
        return None
    try:
        with httpx.Client(timeout=_TIMEOUT, headers=_HEADERS,
                          follow_redirects=True) as client:
            r = client.get(url)
            if r.status_code == 200:
                return r.text
    except Exception:
        pass
    return None


# ─── Slug yardımcıları ────────────────────────────────────────────────────────

_TR_MAP = str.maketrans("çğıöşüÇĞİÖŞÜ", "cgiosuCGIOSU")

def _slugify(s: str) -> str:
    return s.lower().translate(_TR_MAP).replace(" ", "-")


# ─── ARAÇ: arabam.com ─────────────────────────────────────────────────────────

def fetch_car_prices(brand: str, model: str, year: int) -> dict:
    """
    arabam.com'dan marka/model/yıl ilanlarını çekip ortalama fiyat döner.
    Dönüş: { found: bool, prices: list, avg: int, median: int, count: int, url: str }
    """
    slug_brand = _slugify(brand)
    slug_model = _slugify(model)

    # İki URL denemesi: yıl filtreli ve filtresiz
    urls = [
        f"https://www.arabam.com/ikinci-el/otomobil/{slug_brand}-{slug_model}"
        f"?minYear={year - 1}&maxYear={year + 1}",
        f"https://www.arabam.com/ikinci-el/otomobil/{slug_brand}-{slug_model}",
    ]

    for url in urls:
        html = _fetch(url)
        if not html:
            continue
        prices = _extract_prices(html, min_val=50_000, max_val=20_000_000)
        if len(prices) >= 3:
            return {
                "found": True,
                "prices": prices[:30],
                "avg": int(statistics.mean(prices[:30])),
                "median": int(statistics.median(prices[:30])),
                "count": len(prices[:30]),
                "url": url,
            }

    return {"found": False, "prices": [], "avg": 0, "median": 0, "count": 0, "url": ""}


# ─── ARAÇ: sahibinden.com (yedek) ────────────────────────────────────────────

def fetch_car_prices_sahibinden(brand: str, model: str, year: int) -> dict:
    query = f"{brand} {model} {year}".replace(" ", "+")
    url = f"https://www.sahibinden.com/otomobil?query={query}&minYear={year - 1}&maxYear={year + 1}"
    html = _fetch(url)
    if not html:
        return {"found": False, "prices": [], "avg": 0, "median": 0, "count": 0, "url": url}

    prices = _extract_prices(html, min_val=50_000, max_val=20_000_000)
    if len(prices) >= 3:
        return {
            "found": True,
            "prices": prices[:30],
            "avg": int(statistics.mean(prices[:30])),
            "median": int(statistics.median(prices[:30])),
            "count": len(prices[:30]),
            "url": url,
        }
    return {"found": False, "prices": [], "avg": 0, "median": 0, "count": 0, "url": url}


# ─── EMlAK: hepsiemlak.com ───────────────────────────────────────────────────

def fetch_property_prices(city: str, district: str) -> dict:
    """
    hepsiemlak.com'dan şehir/ilçe bazlı satılık daire ilanlarını çekip
    m² fiyatı döner. İlan fiyatlarından m² hesabı yapılmaz —
    doğrudan m² fiyat datasını kullanırız.

    Dönüş: { found, prices, avg_total, median_total, count, url }
    """
    slug_city     = _slugify(city)
    slug_district = _slugify(district)

    urls = [
        f"https://www.hepsiemlak.com/{slug_city}-{slug_district}-satilik-daire",
        f"https://www.hepsiemlak.com/{slug_city}-satilik-daire",
    ]

    for url in urls:
        html = _fetch(url)
        if not html:
            continue
        # Konut fiyatları: 500.000 – 100.000.000 TL arası
        prices = _extract_prices(html, min_val=500_000, max_val=100_000_000)
        if len(prices) >= 3:
            return {
                "found": True,
                "prices": prices[:30],
                "avg_total": int(statistics.mean(prices[:30])),
                "median_total": int(statistics.median(prices[:30])),
                "count": len(prices[:30]),
                "url": url,
            }

    return {"found": False, "prices": [], "avg_total": 0, "median_total": 0, "count": 0, "url": ""}


# ─── EMlAK: sahibinden.com (yedek) ───────────────────────────────────────────

def fetch_property_prices_sahibinden(city: str, district: str) -> dict:
    slug_city     = _slugify(city)
    slug_district = _slugify(district)

    urls = [
        f"https://www.sahibinden.com/satilik-konut/{slug_city}/{slug_district}",
        f"https://www.sahibinden.com/satilik-konut/{slug_city}",
    ]

    for url in urls:
        html = _fetch(url)
        if not html:
            continue
        prices = _extract_prices(html, min_val=500_000, max_val=100_000_000)
        if len(prices) >= 3:
            return {
                "found": True,
                "prices": prices[:30],
                "avg_total": int(statistics.mean(prices[:30])),
                "median_total": int(statistics.median(prices[:30])),
                "count": len(prices[:30]),
                "url": url,
            }

    return {"found": False, "prices": [], "avg_total": 0, "median_total": 0, "count": 0, "url": ""}
