from flask import Flask, request, jsonify
from googlenewsdecoder import gnewsdecoder
from newspaper import Article
import trafilatura
import os

app = Flask(__name__)

@app.route('/extract', methods=['POST'])
def extract_text():
    data = request.get_json()
    url = data.get('url')

    if not url:
        return jsonify({"text": "N/A", "error": "URL not provided"}), 400

    if 'news.google.com' in url:
        decoded_url = gnewsdecoder(url, interval=1)
        if decoded_url.get("status"):
            url = decoded_url["decoded_url"]
        else:
            print(decoded_url["message"])
            return jsonify({"text": "N/A", "error": "URL decoder failed"}), 400

    # Tenta com newspaper3k
    try:
        article = Article(url)
        article.download()
        article.parse()
        text = article.text.strip()
        if len(text) > 100:
            return jsonify({"text": text, "method": "newspaper3k"})
    except Exception as e:
        print("Erro newspaper3k:", str(e))

    # Fallback com trafilatura
    try:
        html = trafilatura.fetch_url(url)
        if html:
            text = trafilatura.extract(html)
            if text and len(text.strip()) > 100:
                return jsonify({"text": text.strip(), "method": "trafilatura"})
    except Exception as e:
        print("Erro trafilatura:", str(e))

    # Se tudo falhar, retorna N/A
    return jsonify({"text": "N/A", "error": "Falha na extração"}), 200


@app.route('/', methods=['GET'])
def health():
    return "API online!", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))  # usa porta dinâmica no Render
    app.run(host="0.0.0.0", port=port)

