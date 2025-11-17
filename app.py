from flask import Flask, request, jsonify
from dotenv import load_dotenv
import os
import requests
import json # Necesario para manejar la estructura JSON del mensaje

# Cargar las variables del archivo .env
load_dotenv()

app = Flask(__name__)

# --- Configuración (Obtenida de .env) ---
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID") 

# --- Función para Enviar Mensajes ---
def send_whatsapp_message(to_number, text_message):
    """Envía un mensaje de texto a un número de WhatsApp."""
    
    # URL de la API de WhatsApp para enviar mensajes (debe incluir el ID del número de teléfono)
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
    
    response = requests.post(url, headers=headers, data=json.dumps(data))
    
    if response.status_code != 200:
        print(f"ERROR al enviar mensaje: {response.json()}")
        return False
    return True


# --- Lógica de Comandos (Aquí implementaremos tus funciones) ---

def handle_commands(sender_id, message_text, sender_name):
    """Procesa los comandos y devuelve la respuesta apropiada."""
    
    msg_lower = message_text.lower().strip()

    # 1. Comando /help
    if msg_lower == "/help":
        help_text = (
            "🤖 **Menú de Ayuda del Bot** 🤖\n\n"
            "Los comandos disponibles son:\n"
            "*/help* - Muestra este menú.\n"
            "*/bienvenida* - Envía un saludo (simulación de Bienvenida).\n"
            "*/chatbot* - Inicia el modo de chat simple.\n"
            "*/anuncio* - Simulación de un anuncio (Función futura).\n"
            "*/despedida* - Mensaje de despedida (Función futura)."
        )
        send_whatsapp_message(sender_id, help_text)
    
    # 2. Comando /bienvenida
    elif msg_lower == "/bienvenida":
        welcome_text = (
            f"¡Hola, *{sender_name}*! 👋\n"
            "Soy tu bot de gestión. ¿En qué puedo ayudarte hoy? Usa */help* para ver los comandos."
        )
        send_whatsapp_message(sender_id, welcome_text)

    # 3. Chat Bot Simple
    elif "hola" in msg_lower or "saludo" in msg_lower:
        response_text = "¡Hola! ¿Buscabas ayuda o solo pasabas a saludar? Recuerda usar */help* si necesitas el menú."
        send_whatsapp_message(sender_id, response_text)
    
    # 4. Respuesta por defecto
    else:
        default_text = (
            "Lo siento, no entendí ese comando. 😔\n"
            "Escribe */help* para ver todos los comandos disponibles."
        )
        send_whatsapp_message(sender_id, default_text)


# --- Rutas de Flask (Webhook) ---

@app.route("/webhook", methods=["GET"])
def handle_verification():
    """Maneja la verificación inicial del Webhook (igual que antes)."""
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN:
        print("Webhook VERIFICADO correctamente")
        return challenge, 200
    else:
        print("Error de verificación: Token o modo incorrectos")
        return jsonify({"message": "Verificación fallida"}), 403


@app.route("/webhook", methods=["POST"])
def handle_messages():
    """Maneja los mensajes entrantes de WhatsApp."""
    data = request.json
    
    # 1. Asegúrate de que el evento sea una notificación válida de WhatsApp
    if data and 'entry' in data and data['entry'][0]['changes'][0]['value'].get('messages'):
        
        try:
            # 2. Extraer los datos clave del mensaje
            message_data = data['entry'][0]['changes'][0]['value']['messages'][0]
            
            sender_id = message_data['from']
            message_type = message_data['type']

            # 3. Solo procesar mensajes de texto
            if message_type == 'text':
                message_text = message_data['text']['body']
                
                # Obtener el nombre del contacto (puede requerir llamadas adicionales a la API, 
                # pero para la prueba usaremos el ID como nombre)
                sender_name = sender_id 
                
                print(f"Mensaje de {sender_id}: {message_text}")

                # 4. Procesar el comando o la respuesta
                handle_commands(sender_id, message_text, sender_name)
            
        except Exception as e:
            print(f"Error al procesar el mensaje: {e}")
    
    # Es crucial retornar 200 OK rápidamente
    return "OK", 200 

if __name__ == "__main__":
    app.run(port=5000, debug=True)