from flask import Flask, request, jsonify
import os
import requests
import pyqrcode
from io import BytesIO
import base64

app = Flask(__name__)

# --- Variáveis de ambiente ---
SHOPIFY_STORE = os.environ.get("SHOPIFY_STORE")       # ex: seguidores-pro.myshopify.com
SHOPIFY_TOKEN = os.environ.get("SHOPIFY_TOKEN")       # token da API Admin
PIX_KEY = os.environ.get("PIX_KEY")                   # ex: 44458558803
MERCHANT_NAME = os.environ.get("MERCHANT_NAME")       # ex: Seguidores.pro
MERCHANT_CITY = os.environ.get("MERCHANT_CITY")       # ex: SAO PAULO
SELLER_EMAIL = os.environ.get("SELLER_EMAIL")         # ex: br.seguidores.pro@gmail.com

if not all([SHOPIFY_STORE, SHOPIFY_TOKEN, PIX_KEY, MERCHANT_NAME, MERCHANT_CITY, SELLER_EMAIL]):
    raise Exception("Alguma variável de ambiente está faltando. Configure todas antes de rodar o app.")


@app.route('/checkout', methods=['POST'])
def checkout():
    data = request.json

    # --- Ler campos do JSON ---
    product_name = data.get('product_name')
    price = data.get('price')
    user_name = data.get('user_name')
    user_email = data.get('user_email')

    if not product_name or not price or not user_name or not user_email:
        return jsonify({"status": "error", "message": "Faltando informações"}), 400

    # --- Combinar nome e email para nota do pedido ---
    user_info = f"{user_name} <{user_email}>"

    try:
        # --- Gerar QR Code PIX ---
        pix_payload = f"00020126680014BR.GOV.BCB.PIX0114{PIX_KEY}0206BR5925{MERCHANT_NAME}6009{MERCHANT_CITY}540{price}5802BR5913{product_name}6304"
        qr = pyqrcode.create(pix_payload)
        buffer = BytesIO()
        qr.png(buffer, scale=5)
        qr_b64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
    except Exception as e:
        return jsonify({"status": "error", "message": f"Erro ao gerar QR Code PIX: {str(e)}"}), 500

    try:
        # --- Criar pedido na Shopify ---
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
        if r.status_code not in [200, 201]:
            return jsonify({
                "status": "error",
                "message": "Erro ao criar pedido na Shopify",
                "details": r.text
            }), 500
    except Exception as e:
        return jsonify({"status": "error", "message": f"Erro na API Shopify: {str(e)}"}), 500

    # --- Retornar QR Code para o frontend ---
    return jsonify({
        "status": "success",
        "message": "Pedido criado e PIX gerado!",
        "pix_qr_base64": qr_b64
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
