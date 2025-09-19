from flask import Flask, request, jsonify
import os, warnings

# Silencia SyntaxWarning vindo do newspaper
warnings.filterwarnings("ignore", category=SyntaxWarning, module=r"newspaper.*")

# --- newspaper3k com config ---
from newspaper import Article, Config as NPConfig
import trafilatura

app = Flask(__name__)

# Config do newspaper (user-agent e timeout ajudam a reduzir falhas)
np_cfg = NPConfig()
np_cfg.browser_user_agent = os.environ.get(
    "BROWSER_UA",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
np_cfg.request_timeout = int(os.environ.get("REQUEST_TIMEOUT", "20"))
np_cfg.fetch_images = False
np_cfg.keep_article_html = False

@app.route("/extract", methods=["POST"])
def extract_text():
    data = request.get_json(silent=True) or {}
    url = (data.get("url") or "").strip()

    if not url:
        return jsonify({"url": url, "text": None, "method": None, "error": "URL not provided"}), 200

    # 1) newspaper3k
    try:
        art = Article(url, config=np_cfg)
        art.download()
        art.parse()
        text = (art.text or "").strip()
        if len(text) > 100:
            return jsonify({"url": url, "text": text, "method": "newspaper3k", "error": None}), 200
    except Exception as e:
        # NÃO retornar aqui: deixa o fallback tentar
        app.logger.warning("newspaper3k failed for %s: %s", url, e)

    # 2) trafilatura (fallback)
    try:
        html = trafilatura.fetch_url(url, no_ssl=False)
        if html:
            text = trafilatura.extract(
                html,
                favor_recall=True,      # puxa mais conteúdo quando possível
                include_comments=False,
                include_tables=False
            )
            if text:
                text = text.strip()
                if len(text) > 100:
                    return jsonify({"url": url, "text": text, "method": "trafilatura", "error": None}), 200
    except Exception as e:
        # Se o fallback também falhar, aí sim devolvemos erro
        app.logger.warning("trafilatura failed for %s: %s", url, e)
        return jsonify({"url": url, "text": None, "method": "trafilatura", "error": str(e)}), 200

    # 3) Nada funcionou
    return jsonify({"url": url, "text": None, "method": None, "error": "Falha na extração"}), 200


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"}), 200


if __name__ == "__main__":
    # Local: python app.py
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

