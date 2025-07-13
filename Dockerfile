# Usa una imagen base de Python. Esto ya incluye Python y pip.
FROM python:3.12-slim

# Establece el directorio de trabajo dentro del contenedor
WORKDIR /app

# Copia los archivos de requerimientos primero para aprovechar el cache de Docker
# Aquí asumo que tendrás un requirements.txt, lo crearemos en el siguiente paso.
COPY requirements.txt .

# Instala las dependencias
RUN pip install --no-cache-dir -r requirements.txt

# Copia el resto de los archivos de tu aplicación al contenedor
COPY . .

# Establece la variable de entorno para el token de Telegram
# Importante: No pongas tu token directamente aquí por seguridad.
# Lo pasaremos cuando ejecutemos el contenedor.
ENV TELEGRAM_BOT_TOKEN="some_default_value_or_empty"

# Comando para ejecutar la aplicación cuando el contenedor se inicie
CMD ["python", "telegram_bot.py"]