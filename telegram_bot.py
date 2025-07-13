import os
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters
import logging
from dotenv import load_dotenv

# Importamos las funciones de nuestro módulo de base de datos
from database_manager import setup_database, parsear_gasto_csv, insertar_gasto, MEDIOS_DE_PAGO_VALIDOS

# --- Configuración del Bot ---
# Habilita el logging para ver lo que está haciendo tu bot
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logging.getLogger("httpx").setLevel(logging.WARNING) # Reduce el log de httpx que es muy verboso
logger = logging.getLogger(__name__)

load_dotenv()  # Carga las variables de entorno desde un archivo .env si existe
# Reemplaza 'TU_TELEGRAM_BOT_TOKEN' con el token que obtuviste de BotFather
# Es mejor usar una variable de entorno para esto en producción.
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "TU_TELEGRAM_BOT_TOKEN_AQUI")

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
        parse_mode='HTML' # Para que se vean las etiquetas <b> y <code>
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
        # Si parsear_gasto_csv retorna None, significa que hubo un error de formato.
        # parsear_gasto_csv ya imprime un mensaje de error por consola,
        # pero también debemos informar al usuario en Telegram.
        await update.message.reply_text(
            "❌ No pude entender tu mensaje. Por favor, asegúrate de usar el formato correcto:\n"
            "<b>monto,descripcion,medio_pago,fecha(opcional)</b>\n\n"
            "Ejemplo: <code>150.75,Cena con amigos,Tarjeta de Crédito BBVA</code>\n"
            "Medios de pago válidos: " + ", ".join(MEDIOS_DE_PAGO_VALIDOS),
            parse_mode='HTML'
        )

# --- Función Principal (main) ---
def main() -> None:
    """Inicia el bot."""
    # Asegúrate de que la base de datos esté configurada
    setup_database()

    # Crea la Application y pásale el token de tu bot.
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Registra los handlers de comandos
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))

    # Registra el handler para mensajes de texto (no comandos)
    # filters.TEXT & ~filters.COMMAND asegura que solo procese mensajes de texto que no sean comandos.
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Inicia el bot (polling)
    logger.info("Bot iniciado. Escuchando mensajes...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    if TELEGRAM_BOT_TOKEN == "TU_TELEGRAM_BOT_TOKEN_AQUI":
        print("ADVERTENCIA: Por favor, reemplaza 'TU_TELEGRAM_BOT_TOKEN_AQUI' en telegram_bot.py con tu token real de BotFather.")
        print("También puedes establecerlo como una variable de entorno llamada TELEGRAM_BOT_TOKEN.")
    else:
        main()