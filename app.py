from flask import Flask, request, jsonify
from newspaper import Article

app = Flask(__name__)

@app.route('/extract', methods=['POST'])
def extract_text():
    data = request.get_json()
    url = data.get('url')

    if not url:
        return jsonify({"error": "URL not provided"}), 400

    try:
        article = Article(url)
        article.download()
        article.parse()
        return jsonify({"text": article.text})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

import os

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))  # usa porta do Render
    app.run(host="0.0.0.0", port=port)


@app.route('/', methods=['GET'])
def health():
    return "API online!", 200

