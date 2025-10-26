from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import requests
import pyqrcode
import png
from io import BytesIO
import base64

app = Flask(__name__)
CORS(app, origins=["https://br-seguidores.myshopify.com"])

# Variáveis de ambiente
SHOPIFY_STORE = os.environ.get("SHOPIFY_STORE")
SHOPIFY_TOKEN = os.environ.get("SHOPIFY_TOKEN")
PIX_KEY = os.environ.get("PIX_KEY")
MERCHANT_NAME = os.environ.get("MERCHANT_NAME")
MERCHANT_CITY = os.environ.get("MERCHANT_CITY")
SELLER_EMAIL = os.environ.get("SELLER_EMAIL")


@app.route('/checkout', methods=['POST'])
def checkout():
    data = request.json
    product_name = data.get('product_name')
    price = data.get('price')
    user_info = data.get('user_info')

    if not product_name or not price or not user_info:
        return jsonify({"status": "error", "message": "Faltando informações"}), 400

    # --- 1️⃣ Gerar QR Code PIX ---
    pix_payload = f"00020126680014BR.GOV.BCB.PIX0114{PIX_KEY}0206BR5925{MERCHANT_NAME}6009{MERCHANT_CITY}540{price}5802BR5913{product_name}6304"
    qr = pyqrcode.create(pix_payload)
    buffer = BytesIO()
    qr.png(buffer, scale=5)
    qr_b64 = base64.b64encode(buffer.getvalue()).decode('utf-8')

    # --- 2️⃣ Criar pedido na Shopify ---
    order_data = {
        "order": {
            "line_items": [{"title": product_name, "quantity": 1, "price": price}],
            "note": f"Comprador: {user_info}"
        }
    }

    url = f"https://{SHOPIFY_STORE}/admin/api/2025-10/orders.json"
    headers = {
        "Content-Type": "application/json",
        "X-Shopify-Access-Token": SHOPIFY_TOKEN
    }

    r = requests.post(url, json=order_data, headers=headers)
    if r.status_code in [200, 201]:
        return jsonify({
            "status": "success",
            "message": "Pedido criado e PIX gerado!",
            "pix_qr_base64": qr_b64
        })
    else:
        return jsonify({
            "status": "error",
            "message": "Erro ao criar pedido",
            "details": r.text
        }), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)

