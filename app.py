from flask import Flask, request, jsonify
from dotenv import load_dotenv
import os
import requests
import json
import logging
import threading
import time
from datetime import datetime

logging.basicConfig(level=logging.INFO)
app = Flask(__name__)
load_dotenv()

VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")

# -----------------------------
#   MEMORIA TEMPORAL
# -----------------------------
pending_event = {}   # Guarda el progreso del usuario con /crear_evento
event_list = []      # Aquí se guardarán los eventos definitivos


# -----------------------------
#   ENVIAR MENSAJES
# -----------------------------
def send_whatsapp_message(to, text):
    if not WHATSAPP_TOKEN or not PHONE_NUMBER_ID:
        return

    url = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }
    data = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": text}
    }
    requests.post(url, headers=headers, data=json.dumps(data))


# -----------------------------
#   RECORDATORIOS AUTOMÁTICOS
# -----------------------------
def reminder_loop():
    while True:
        now = datetime.now().strftime("%d/%m/%Y %H:%M")

        for event in event_list[:]:
            if event["datetime"] == now:
                send_whatsapp_message(event["user"], f"⏰ *Recordatorio:* {event['motivo']}")
                event_list.remove(event)

        time.sleep(30)  # revisa cada 30 segundos


# Iniciar hilo de recordatorios
threading.Thread(target=reminder_loop, daemon=True).start()



# -----------------------------
#   MANEJO DE COMANDOS
# -----------------------------
def handle_commands(user, text):

    # 🔥 Si está creando un evento, manejar flujo paso a paso
    if user in pending_event:
        step = pending_event[user]["step"]

        # 1️⃣ FECHA
        if step == "fecha":
            pending_event[user]["fecha"] = text.strip()
            pending_event[user]["step"] = "hora"
            send_whatsapp_message(user, "📌 Ahora dime la *hora* (HH:MM)")
            return

        # 2️⃣ HORA
        if step == "hora":
            pending_event[user]["hora"] = text.strip()
            pending_event[user]["step"] = "motivo"
            send_whatsapp_message(user, "📝 ¿Cuál es el *motivo* del recordatorio?")
            return

        # 3️⃣ MOTIVO
        if step == "motivo":
            fecha = pending_event[user]["fecha"]
            hora = pending_event[user]["hora"]
            motivo = text.strip()

            # Combinar fecha y hora
            try:
                fecha_hora = datetime.strptime(f"{fecha} {hora}", "%d/%m/%Y %H:%M")
            except:
                send_whatsapp_message(user, "❌ Formato incorrecto. Usa DD/MM/AAAA y HH:MM")
                del pending_event[user]
                return

            event_list.append({
                "user": user,
                "motivo": motivo,
                "datetime": fecha_hora.strftime("%d/%m/%Y %H:%M")
            })

            send_whatsapp_message(user, f"✅ *Evento creado*\n📅 {fecha}\n⏰ {hora}\n📝 {motivo}\n\nTe lo recordaré a esa hora.")

            del pending_event[user]
            return


    # -----------------------
    #   COMANDOS NORMALES
    # -----------------------

    t = text.lower().strip()

    if t == "/crear_evento":
        pending_event[user] = {"step": "fecha"}
        send_whatsapp_message(user, "📅 Dime la *fecha* del evento (DD/MM/AAAA):")
        return

    if t == "/help":
        menu = (
            "📘 *Menú de Ayuda*\n\n"
            "/help - Mostrar comandos\n"
            "/bienvenida - Saludo\n"
            "/status - Estado del bot\n"
            "/crear_evento - Programar recordatorio automático\n"
        )
        send_whatsapp_message(user, menu)
        return

    if t == "/bienvenida":
        send_whatsapp_message(user, "👋 ¡Bienvenido! Soy tu bot funcionando en Render.")
        return

    if t == "/status":
        send_whatsapp_message(user, "🟢 Bot funcionando (Render online)")
        return

    # Respuesta por defecto
    send_whatsapp_message(user, f"🤖 Escribiste: {text}\nUsa */help* para ver opciones.")



# -----------------------------
#     WEBHOOKS
# -----------------------------
@app.route("/webhook", methods=["GET"])
def verify():
    if request.args.get("hub.mode") == "subscribe" and request.args.get("hub.verify_token") == VERIFY_TOKEN:
        return request.args.get("hub.challenge")
    return "No autorizado", 403



@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json

    try:
        entry = data["entry"][0]
        event = entry["changes"][0]["value"]

        if "messages" in event:
            msg = event["messages"][0]
            sender = msg["from"]

            if msg["type"] == "text":
                body = msg["text"]["body"]
                handle_commands(sender, body)

    except Exception as e:
        print("Error:", e)

    return "OK", 200



if __name__ == "__main__":
    app.run(port=5000, debug=True)
