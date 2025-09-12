from flask import Flask, request, Response
from newspaper import Article
import trafilatura
import urllib.parse
import os

# Novo: decodificador Google News
from googlenewsdecoder import gnewsdecoder

app = Flask(__name__)

# --- Helpers ---------------------------------------------------------------

def is_google_news_url(url: str) -> bool:
    try:
        p = urllib.parse.urlparse(url)
        if 'news.google.' not in p.netloc:
            return False
        # cobre formatos /read/..., /articles/..., ou com ?url=
        return ('/read' in p.path) or ('/articles' in p.path) or ('url=' in p.query)
    except Exception:
        return False

def decode_google_news_url(gn_url: str, interval_time: int = 1) -> str | None:
    """
    Usa googlenewsdecoder para obter a URL final do artigo.
    Retorna a URL decodificada ou None em caso de falha.
    """
    try:
        decoded = gnewsdecoder(gn_url, interval=interval_time)
        if isinstance(decoded, dict) and decoded.get("status") and decoded.get("decoded_url"):
            return decoded["decoded_url"]
    except Exception as e:
        print(f"[decode_google_news_url] Falha: {e}")
    return None

def extract_with_newspaper(url: str) -> str | None:
    try:
        article = Article(url)
        article.download()
        article.parse()
        text = (article.text or "").strip()
        return text if len(text) > 100 else None
    except Exception as e:
        print(f"[newspaper3k] Falha: {e}")
        return None

def extract_with_trafilatura(url: str) -> str | None:
    try:
        html = trafilatura.fetch_url(url)
        if not html:
            return None
        text = trafilatura.extract(html)
        if text:
            text = text.strip()
        return text if text and len(text) > 100 else None
    except Exception as e:
        print(f"[trafilatura] Falha: {e}")
        return None

# --- Rotas -----------------------------------------------------------------

@app.route('/extract', methods=['POST'])
def extract_text():
    data = request.get_json(silent=True) or {}
    url = data.get('url', '') or ''

    # Se não veio URL, responde corpo vazio (sem erro/mensagem)
    if not url:
        return Response("", mimetype='text/plain; charset=utf-8', status=200)

    # Se for Google News, decodifica para URL final
    if is_google_news_url(url):
        decoded = decode_google_news_url(url, interval_time=1)
        if decoded:
            url = decoded
        # Se não conseguir decodificar, seguimos tentando extrair do próprio GN (provável que falhe, mas sem erro no body)

    # Tenta extrair com newspaper3k
    text = extract_with_newspaper(url)
    if not text:
        # Fallback trafilatura
        text = extract_with_trafilatura(url)

    # Responde apenas o texto puro (ou vazio se não conseguiu)
    if not text:
        text = ""

    return Response(text, mimetype='text/plain; charset=utf-8', status=200)

@app.route('/', methods=['GET'])
def health():
    return "API online!", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
