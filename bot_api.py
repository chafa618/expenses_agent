import os
import logging
from typing import Dict, Any

from fastapi import FastAPI, Request, Response, HTTPException
from telegram import Update, Bot
from telegram.ext import Application, MessageHandler, CommandHandler, filters
from telegram.constants import ParseMode

# Importamos las funciones de nuestro módulo de base de datos
from database_manager import setup_database, parsear_gasto_csv, insertar_gasto, MEDIOS_DE_PAGO_VALIDOS

# --- Configuración del Bot y Logging ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

# Reemplaza 'TU_TELEGRAM_BOT_TOKEN_AQUI' con el token que obtuviste de BotFather.
# Usar una variable de entorno es la forma más segura en producción.
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "TU_TELEGRAM_BOT_TOKEN_AQUI")
if TELEGRAM_BOT_TOKEN == "TU_TELEGRAM_BOT_TOKEN_AQUI":
    logger.warning("ADVERTENCIA: TELEGRAM_BOT_TOKEN no establecido. Usa una variable de entorno o reemplaza en el código.")

# El puerto en el que la aplicación FastAPI escuchará.
# Cloud Run espera que las apps escuchen en el puerto 8080 por defecto.
PORT = int(os.getenv("PORT", 8080))

# --- Instancia de la Aplicación FastAPI ---
app = FastAPI(docs_url="/docs", redoc_url="/redoc") # Añadimos URLs para la documentación automática de FastAPI

# Instancia de la aplicación de Telegram
# La aplicación se inicializa aquí, pero no se inicia con polling.
# En su lugar, se usa para procesar las actualizaciones que llegan vía webhook.
application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

# --- Handlers de Comandos y Mensajes ---
async def start(update: Update, context) -> None:
    """Envía un mensaje de bienvenida cuando se ejecuta el comando /start."""
    user = update.effective_user
    await update.message.reply_html(
        f"¡Hola, {user.mention_html()}! 👋\n"
        "Soy tu asistente personal de gastos. Puedes registrar un gasto enviándome un mensaje en formato CSV:\n\n"
        "<b>monto,descripcion,medio_pago,fecha(opcional)</b>\n\n"
        "Ejemplo: <code>150.75,Cena con amigos,Tarjeta de Crédito BBVA</code>\n"
        "Ejemplo con fecha: <code>50,Café,Efectivo,12/07/2025</code>\n\n"
        "Medios de pago válidos: " + ", ".join(MEDIOS_DE_PAGO_VALIDOS) + "\n\n"
        "¡Estoy listo para ayudarte a llevar un control de tus finanzas!"
    )

async def help_command(update: Update, context) -> None:
    """Envía un mensaje de ayuda cuando se ejecuta el comando /help."""
    await update.message.reply_text(
        "Para registrar un gasto, usa el formato: <b>monto,descripcion,medio_pago,fecha(opcional)</b>\n"
        "Ejemplo: <code>150.75,Cena con amigos,Tarjeta de Crédito BBVA</code>\n"
        "Si no pones la fecha, usaré la de hoy. Medios de pago válidos: " + ", ".join(MEDIOS_DE_PAGO_VALIDOS) + "\n\n"
        "Próximamente agregaré más funcionalidades como ver resúmenes y presupuestos.",
        parse_mode=ParseMode.HTML # Para que se vean las etiquetas <b> y <code>
    )

async def handle_message(update: Update, context) -> None:
    """Maneja los mensajes de texto recibidos y trata de registrar un gasto."""
    user_message = update.message.text
    logger.info(f"Mensaje recibido de {update.effective_user.first_name}: {user_message}")

    gasto_data = parsear_gasto_csv(user_message)

    if gasto_data:
        if insertar_gasto(**gasto_data):
            await update.message.reply_text(
                f"✅ ¡Gasto registrado exitosamente! ✅\n"
                f"Monto: ${gasto_data['monto']:.2f}\n"
                f"Descripción: {gasto_data['descripcion']}\n"
                f"Medio de Pago: {gasto_data['medio_pago']}\n"
                f"Fecha: {gasto_data['fecha']}"
            )
        else:
            await update.message.reply_text("❌ Ocurrió un error al guardar el gasto en la base de datos. Por favor, inténtalo de nuevo.")
    else:
        await update.message.reply_text(
            "❌ No pude entender tu mensaje. Por favor, asegúrate de usar el formato correcto:\n"
            "<b>monto,descripcion,medio_pago,fecha(opcional)</b>\n\n"
            "Ejemplo: <code>150.75,Cena con amigos,Tarjeta de Crédito BBVA</code>\n"
            "Medios de pago válidos: " + ", ".join(MEDIOS_DE_PAGO_VALIDOS),
            parse_mode=ParseMode.HTML
        )

# --- Configuración de Handlers para la Aplicación de Telegram ---
def setup_handlers():
    """Registra los handlers de comandos y mensajes con la aplicación de Telegram."""
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

# --- Rutas de FastAPI ---

@app.on_event("startup")
async def startup_event():
    """Se ejecuta al iniciar la aplicación FastAPI."""
    logger.info("Iniciando aplicación FastAPI...")
    setup_database() # Asegúrate de que la DB esté configurada al iniciar
    setup_handlers() # Registra los handlers de Telegram
    # Es recomendable establecer el webhook aquí en un entorno de producción,
    # pero para desarrollo y pruebas, lo haremos manualmente o en la consola de GCP.
    # El URL del webhook será la URL de tu servicio Cloud Run + /telegram-webhook
    # bot_info = await application.bot.get_me()
    # logger.info(f"Bot info: {bot_info}")
    # webhook_url = "TU_URL_DE_CLOUD_RUN" + "/telegram-webhook"
    # await application.bot.set_webhook(url=webhook_url)
    # logger.info(f"Webhook establecido a: {webhook_url}")

@app.post("/telegram-webhook")
async def telegram_webhook(request: Request) -> Dict[str, Any]:
    """Endpoint para recibir las actualizaciones de Telegram."""
    try:
        # Obtiene el cuerpo de la petición como JSON
        update_json = await request.json()
        # Convierte el JSON en un objeto Update de python-telegram-bot
        update = Update.de_json(update_json, application.bot)
        # Procesa la actualización
        await application.process_update(update)
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Error procesando webhook: {e}", exc_info=True)
        # Es buena práctica retornar un 200 OK para evitar que Telegram siga intentando.
        # Un 500 interno es para nuestros logs, no para que Telegram se alarme.
        return {"status": "error", "message": str(e)}, 200 # No enviamos 500, Telegram espera 200 OK

@app.get("/")
async def root():
    """Ruta raíz para verificar que el servicio está funcionando."""
    return {"message": "Agente de Gastos - Bot de Telegram. La API del webhook está en /telegram-webhook"}

# --- Bloque de Ejecución Principal ---
# Para ejecutar localmente, usaríamos:
# uvicorn telegram_bot:app --host 0.0.0.0 --port 8080 --reload
# El --reload es útil para desarrollo, pero no para producción.
# En producción (ej. Cloud Run), Gunicorn o un supervisor iniciará Uvicorn.
# No necesitamos un `if __name__ == "__main__":` complejo aquí,
# ya que FastAPI se inicia a través de Uvicorn.