import os
import logging
import re
import requests
from flask import Flask, request, jsonify

# === Настройки ===
BOT_TOKEN = os.getenv("BOT_TOKEN", "8551418943:AAFplKK48glNeteXeS9QrVch2smuZQ5T-AY")
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID", "890315945"))
COPY_TEXT = os.getenv(
    "COPY_TEXT",
    "Здравствуйте! Благодарим за обращение. Мы свяжемся с вами в ближайшее время."
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

def normalize_russian_phone(phone: str) -> str:
    digits = re.sub(r'\D', '', phone)
    if not digits:
        return phone
    if len(digits) == 10 and digits.startswith('9'):
        return '7' + digits
    elif len(digits) == 11 and digits.startswith('8'):
        return '7' + digits[1:]
    elif len(digits) == 11 and digits.startswith('7'):
        return digits
    elif len(digits) == 10:
        return '7' + digits
    return digits

@app.route('/submit', methods=['POST'])
def receive_application():
    try:
        logger.info(f"📡 Headers: {dict(request.headers)}")
        raw_body = request.get_data().decode('utf-8', errors='replace')
        logger.info(f"📦 Raw body: {raw_body}")

        data = request.form.to_dict()
        if not data:  # ←←← ИСПРАВЛЕНО: добавлено условие
            try:
                json_data = request.get_json(silent=True)
                if json:
                    data = json_data
            except:
                pass

        if not data:  # ←←← ИСПРАВЛЕНО: проверка на пустоту
            return jsonify({"error": "Пустой запрос"}), 400

        full_name = ""
        phone_raw = ""

        for key, value in data.items():
            if isinstance(value, str):
                key_lower = key.lower()
                if any(kw in key_lower for kw in ["name", "fio", "fullname", "имя", "фио", "фамилия", "contact"]):
                    full_name = value.strip()
                if any(kw in key_lower for kw in ["phone", "tel", "телефон", "мобильный", "phone_number"]):
                    phone_raw = value.strip()

        if not full_name or not phone_raw:
            logger.warning("❌ Не найдены ФИО или телефон")
            return jsonify({"error": "Не найдены ФИО или телефон"}), 400

        clean_phone = normalize_russian_phone(phone_raw)

        claim_message = (
            "🔔 <b>Новая заявка с сайта!</b>\n\n"
            f"👤 <b>ФИО:</b> {full_name}\n"
            f"📞 <b>Телефон:</b> <a href='tg://resolve?phone={clean_phone}'>{phone_raw}</a>"
        )

        copy_text_clean = COPY_TEXT

        telegram_url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

        requests.post(
            telegram_url,
            data={
                "chat_id": ADMIN_CHAT_ID,
                "text": claim_message,
                "parse_mode": "HTML"
            },
            timeout=10
        )

        requests.post(
            telegram_url,
            data={
                "chat_id": ADMIN_CHAT_ID,
                "text": copy_text_clean
            },
            timeout=10
        )

        logger.info(f"✅ Заявка от {full_name} успешно отправлена.")
        return jsonify({"status": "ok"}), 200

    except Exception as e:
        logger.exception("❌ Критическая ошибка")
        return jsonify({"error": "Внутренняя ошибка сервера"}), 500

@app.route('/healthz')
def health():
    return "OK", 200

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port, debug=False)