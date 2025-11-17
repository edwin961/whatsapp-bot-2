from flask import Flask, request, jsonify
from dotenv import load_dotenv
import os
import requests
import json 
import logging

# Configuración del logging para ver errores en Render
# Necesario para que Render/Gunicorn muestre errores claros
logging.basicConfig(level=logging.INFO) 
app = Flask(__name__)

# Cargar las variables del archivo .env (solo para prueba local, Render usa sus variables)
load_dotenv()

# --- Configuración (Obtenida de variables de entorno) ---
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID") 

# --- Función para Enviar Mensajes ---
def send_whatsapp_message(to_number, text_message):
    """Envía un mensaje de texto a un número de WhatsApp."""
    
    # Verifica que las credenciales críticas estén presentes
    if not WHATSAPP_TOKEN or not PHONE_NUMBER_ID:
        app.logger.error("Faltan WHATSAPP_TOKEN o PHONE_NUMBER_ID. No se puede enviar el mensaje.")
        return False
        
    url = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/messages"
    
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json",
    }
    
    data = {
        "messaging_product": "whatsapp",
        "to": to_number,
        "type": "text",
        "text": {"body": text_message}
    }
    
    try:
        response = requests.post(url, headers=headers, data=json.dumps(data), timeout=15)
        
        if response.status_code != 200:
            # Si Meta devuelve un error, lo registramos claramente en Render
            error_data = response.json()
            app.logger.error(f"ERROR API Meta (Código {response.status_code}): {error_data}")
            return False
        
        app.logger.info(f"Mensaje enviado con éxito a {to_number}")
        return True

    except requests.exceptions.RequestException as e:
        app.logger.error(f"ERROR de conexión al enviar mensaje: {e}")
        return False


# --- Lógica de Comandos ---
def handle_commands(sender_id, message_text):
    """Procesa los comandos y devuelve la respuesta apropiada."""
    
    msg_lower = message_text.lower().strip()

    # Mensaje de respuesta por defecto
    default_text = (
        "🤖 ¡Hola! Gracias por tu mensaje. 🤖\n\n"
        "Escribiste: *{text_received}*\n\n"
        "Si necesitas ayuda, usa el comando */help* para ver el menú de opciones."
    ).format(text_received=message_text)
    
    response_text = ""

    # 1. Comando /help
    if msg_lower == "/help":
        response_text = (
            "🤖 **Menú de Ayuda del Bot** 🤖\n"
            "Los comandos disponibles son:\n"
            "*/help* - Muestra este menú.\n"
            "*/bienvenida* - Envía un saludo personalizado.\n"
            "*/status* - Verifica el estado del bot."
        )
    
    # 2. Comando /bienvenida
    elif msg_lower == "/bienvenida":
        response_text = (
            "¡Bienvenido! 👋 Soy tu bot de prueba, funcionando en Render. "
            "Estoy listo para recibir tus comandos."
        )

    # 3. Comando /status
    elif msg_lower == "/status":
        response_text = "🟢 **ESTADO:** Operacional (Live on Render)."
        
    # 4. Respuesta por defecto a CUALQUIER otro texto
    else:
        response_text = default_text
        
    # Enviar la respuesta
    send_whatsapp_message(sender_id, response_text)


# --- Rutas de Flask (Webhook) ---

@app.route("/webhook", methods=["GET"])
def handle_verification():
    """Maneja la verificación inicial del Webhook."""
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN:
        app.logger.info("Webhook VERIFICADO correctamente")
        return challenge, 200
    else:
        app.logger.error("Error de verificación: Token o modo incorrectos")
        return jsonify({"message": "Verificación fallida"}), 403


@app.route("/webhook", methods=["POST"])
def handle_messages():
    """Maneja los mensajes entrantes de WhatsApp."""
    data = request.json
    
    # El mensaje de depuración es CRUCIAL para ver la data en el log de Render
    app.logger.info(f"Datos recibidos del Webhook: {json.dumps(data, indent=2)}")
    
    try:
        # Navegación profunda al cuerpo del mensaje
        entry = data.get('entry', [{}])[0]
        change = entry.get('changes', [{}])[0]
        value = change.get('value', {})
        messages = value.get('messages', [])

        if messages:
            message_data = messages[0]
            sender_id = message_data.get('from')
            message_type = message_data.get('type')

            if message_type == 'text':
                message_text = message_data['text']['body']
                
                app.logger.info(f"Mensaje de {sender_id}: {message_text}")

                handle_commands(sender_id, message_text)
            
            # Procesar otros tipos de mensajes (imágenes, stickers) para enviar una respuesta de texto por defecto
            elif message_type in ['image', 'sticker', 'audio']:
                default_response = "Gracias por el archivo. Por ahora, solo puedo procesar comandos de texto como */help*."
                app.logger.info(f"Recibido {message_type} de {sender_id}")
                send_whatsapp_message(sender_id, default_response)
                
        
    except Exception as e:
        app.logger.error(f"Error general al procesar el mensaje: {e}", exc_info=True)
        # Es vital retornar 200 OK incluso si hay un error en el procesamiento interno
        # para evitar que Meta siga enviando la notificación.
    
    return "OK", 200 

if __name__ == "__main__":
    app.run(port=5000, debug=True)