import os
import logging
import re
import requests

# === Настройки ===
BOT_TOKEN = os.getenv("BOT_TOKEN", "8551418943:AAFplKK48glNeteXeS9QrVch2smuZQ5T-AY")
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID", "890315945"))
COPY_TEXT = os.getenv(
    "COPY_TEXT",
    "Шаблон ответа: Здравствуйте! Благодарим за обращение. Мы свяжемся с вами в ближайшее время."
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from flask import Flask, request, jsonify
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
        data = request.get_json()
        logger.info(f"📥 Получены данные: {data}")
        if not data:
            return jsonify({"error": "Пустой запрос"}), 400

        full_name = ""
        phone_raw = ""

        for key, value in data.items():
            if isinstance(value, str):
                key_lower = key.lower()
                if "name" in key_lower or "fio" in key_lower or "fullname" in key_lower:
                    full_name = value.strip()
                if "phone" in key_lower or "tel" in key_lower:
                    phone_raw = value.strip()

        if not full_name or not phone_raw:
            return jsonify({"error": "Не найдены ФИО или телефон"}), 400

        clean_phone = normalize_russian_phone(phone_raw)
        phone_link = f"tg://resolve?phone={clean_phone}"

        # Форматируем сообщение в HTML (Telegram поддерживает)
        message = (
            "🔔 <b>Новая заявка с сайта!</b>\n\n"
            f"👤 <b>ФИО:</b> {full_name}\n"
            f"📞 <b>Телефон:</b> <a href='{phone_link}'>{phone_raw}</a>\n\n"
            f"<b>📋 Текст для копирования:</b>\n"
            f"<pre>{COPY_TEXT}</pre>"
        )

        # Отправляем через прямой HTTP-запрос к Telegram API
        telegram_url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": ADMIN_CHAT_ID,
            "text": message,
            "parse_mode": "HTML"
        }

        response = requests.post(telegram_url, json=payload, timeout=10)
        if response.status_code != 200:
            logger.error(f"❌ Ошибка Telegram API: {response.text}")
            return jsonify({"error": "Не удалось отправить в Telegram"}), 500

        logger.info(f"✅ Заявка от {full_name} отправлена.")
        return jsonify({"status": "ok"}), 200

    except Exception as e:
        logger.exception("❌ Ошибка при обработке заявки")
        return jsonify({"error": "Внутренняя ошибка"}), 500

@app.route('/healthz')
def health():
    return "OK", 200

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port, debug=False)