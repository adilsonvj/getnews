# app.py
from flask import Flask, request, jsonify
from googlenewsdecoder import gnewsdecoder
import trafilatura
import requests
import os, time, threading
from typing import Optional

# ===== Config (somente opcionais de performance) =====
REQUEST_TIMEOUT = float(os.environ.get("REQUEST_TIMEOUT", "12"))   # seg
CONNECT_TIMEOUT = float(os.environ.get("CONNECT_TIMEOUT", "6"))    # seg
DECODE_TTL = int(os.environ.get("DECODE_TTL", "86400"))            # 24h
TEXT_TTL = int(os.environ.get("TEXT_TTL", "86400"))                # 24h
MAX_TEXT_LEN_MIN = int(os.environ.get("MAX_TEXT_LEN_MIN", "100"))  # mínimo p/ considerar sucesso

USER_AGENT = os.environ.get(
    "USER_AGENT",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)

# ===== Caches TTL simples =====
_cache_lock = threading.Lock()
_decode_cache = {}  # key=url_gn -> (expires, decoded_url)
_text_cache = {}    # key=url_final -> (expires, text)

def _get_cache(cache, key):
    now = time.time()
    with _cache_lock:
        item = cache.get(key)
        if not item:
            return None
        expires, val = item
        if expires < now:
            cache.pop(key, None)
            return None
        return val

def _set_cache(cache, key, val, ttl):
    with _cache_lock:
        cache[key] = (time.time() + ttl, val)

# ===== HTTP Session (keep-alive) =====
session = requests.Session()
session.headers.update({
    "User-Agent": USER_AGENT,
    "Accept": "*/*",
    "Accept-Encoding": "gzip, deflate, br",
})

# ===== Helpers =====
def decode_if_gnews(url: str) -> str:
    if "news.google.com" not in url:
        return url
    cached = _get_cache(_decode_cache, url)
    if cached:
        return cached
    # Sem interval (default=None) => sem sleep desnecessário
    res = gnewsdecoder(url)
    if isinstance(res, dict) and res.get("status") and res.get("decoded_url"):
        decoded = res["decoded_url"]
        _set_cache(_decode_cache, url, decoded, DECODE_TTL)
        return decoded
    # Se falhar, segue com a original
    return url

def fetch_html(url: str) -> Optional[str]:
    try:
        r = session.get(url, timeout=(CONNECT_TIMEOUT, REQUEST_TIMEOUT), allow_redirects=True)
        if r.ok and r.text:
            return r.text
    except Exception:
        pass
    return None

def extract_with_trafilatura(url: str) -> str:
    html = fetch_html(url)
    if html:
        text = trafilatura.extract(
            html,
            include_comments=False,
            include_links=False,
            include_images=False,
            favor_precision=True,
            url=url,
        )
        if text and len(text.strip()) >= MAX_TEXT_LEN_MIN:
            return text.strip()

    try:
        html2 = trafilatura.fetch_url(url)
        if html2:
            text2 = trafilatura.extract(
                html2,
                include_comments=False,
                include_links=False,
                include_images=False,
                favor_precision=True,
                url=url,
            )
            if text2 and len(text2.strip()) >= MAX_TEXT_LEN_MIN:
                return text2.strip()
    except Exception:
        pass

    return ""

def extract_with_newspaper(url: str) -> str:
    try:
        from newspaper import Article  # lazy import
    except Exception:
        return ""

    try:
        _ = fetch_html(url)  # aquece DNS/TLS
        art = Article(url, language="pt")
        art.download()
        art.parse()
        txt = (art.text or "").strip()
        if len(txt) >= MAX_TEXT_LEN_MIN:
            return txt
    except Exception:
        return ""
    return ""

def extract_text_pipeline(url: str) -> str:
    cached = _get_cache(_text_cache, url)
    if cached is not None:
        return cached

    text = extract_with_trafilatura(url)
    if not text:
        text = extract_with_newspaper(url)

    if text is None:
        text = ""

    _set_cache(_text_cache, url, text, TEXT_TTL if text else 300)  # 5 min p/ falhas
    return text

# ===== Flask App =====
app = Flask(__name__)

@app.route("/extract", methods=["POST"])
def extract_endpoint():
    payload = request.get_json(silent=True) or {}
    url = (payload.get("url") or "").strip()

    if not url:
        return jsonify({"text": ""})

    final_url = decode_if_gnews(url)
    text = extract_text_pipeline(final_url)

    # Sempre só {"text": "..."}
    return jsonify({"text": text})

@app.route("/", methods=["GET"])
def health():
    return "OK", 200

if __name__ == "__main__":
    # Para rodar local. No Render, use Gunicorn no Start Command.
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, threaded=True)


