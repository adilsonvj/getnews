from flask import Flask, request, jsonify 
from newspaper import Article
import trafilatura
import os

app = Flask(__name__)

@app.route('/extract', methods=['POST'])
def extract_text():
    data = request.get_json()
    url = data.get('url')

    if not url:
        return jsonify({"url" : url,"text": "N/A", "method": "N/A", "error": "URL not provided"}), 400

    # Tenta com newspaper3k
    try:
        article = Article(url)
        article.download()
        article.parse()
        text = article.text.strip()
        if len(text) > 100:
            return jsonify({"url" : url, "text": text, "method": "newspaper3k", "error" : "N/A"}), 200
    except Exception as e:
        print("Erro newspaper3k:", str(e))

    # Fallback com trafilatura
    try:
        html = trafilatura.fetch_url(url)
        if html:
            text = trafilatura.extract(html)
            if text and len(text.strip()) > 100:
                return jsonify({"url" : url, "text": text.strip(), "method": "trafilatura", "error" : "N/A"}), 200
    except Exception as e:
        print("Erro trafilatura:", str(e))

    # Se tudo falhar, retorna N/A
    return jsonify({"url" : url, "text": "N/A", "method": "N/A", "error": "Falha na extração"}), 422


@app.route('/', methods=['GET'])
def health():
    return "OK", 200
# ou JSON:
@app.get("/health", methods=['GET'])
def healthz():
    return jsonify(status="ok"), 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))  # usa porta dinâmica no Render
    app.run(host="0.0.0.0", port=port)


