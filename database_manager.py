import sqlite3
from datetime import datetime

DATABASE_NAME = 'gastos.db'

# Definimos los medios de pago válidos
MEDIOS_DE_PAGO_VALIDOS = [
    "Efectivo",
    "TD ICBC",
    "TC BBVA",
    "TC ICBC",
    "AMEX",
    "TBN"
]

def setup_database():
    """
    Configura la base de datos SQLite:
    - Crea la conexión.
    - Crea la tabla 'gastos' si no existe.
    """
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_NAME)
        cursor = conn.cursor()

        # Crear la tabla gastos si no existe
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS gastos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                monto REAL NOT NULL,
                descripcion TEXT NOT NULL,
                medio_pago TEXT NOT NULL,
                fecha TEXT NOT NULL
            )
        ''')
        conn.commit()
        print(f"Base de datos '{DATABASE_NAME}' y tabla 'gastos' verificadas/creadas exitosamente.")
    except sqlite3.Error as e:
        print(f"Error al configurar la base de datos: {e}")
    finally:
        if conn:
            conn.close()

def insertar_gasto(monto: float, descripcion: str, medio_pago: str, fecha: str = None):
    """
    Inserta un nuevo gasto en la base de datos.
    Si la fecha no se provee, usa la fecha actual.
    """
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_NAME)
        cursor = conn.cursor()

        if fecha is None:
            fecha = datetime.now().strftime('%Y-%m-%d') # Formato YYYY-MM-DD para fácil ordenamiento

        cursor.execute('''
            INSERT INTO gastos (monto, descripcion, medio_pago, fecha)
            VALUES (?, ?, ?, ?)
        ''', (monto, descripcion, medio_pago, fecha))
        conn.commit()
        print(f"Gasto registrado: {monto}, '{descripcion}', '{medio_pago}', '{fecha}'")
        return True
    except sqlite3.Error as e:
        print(f"Error al insertar gasto: {e}")
        return False
    finally:
        if conn:
            conn.close()

def parsear_gasto_csv(mensaje_csv: str) -> dict:
    """
    Parsea un mensaje CSV del usuario y extrae la información del gasto.
    Formato esperado: monto,descripcion,medio_pago,fecha(opcional)
    Retorna un diccionario con los datos del gasto o None si hay un error.
    """
    partes = [p.strip() for p in mensaje_csv.split(',')]

    if not (3 <= len(partes) <= 4):
        print("Error: Formato CSV incorrecto. Se esperan 3 o 4 partes (monto,descripcion,medio_pago,fecha[opcional]).")
        return None

    try:
        monto = float(partes[0])
    except ValueError:
        print(f"Error: El monto '{partes[0]}' no es un número válido.")
        return None

    descripcion = partes[1]
    medio_pago = partes[2]
    fecha = None

    if len(partes) == 4:
        fecha_str = partes[3]
        try:
            # Intentar parsear la fecha en formato DD/MM/AAAA
            fecha = datetime.strptime(fecha_str, '%d/%m/%Y').strftime('%Y-%m-%d')
        except ValueError:
            print(f"Error: El formato de fecha '{fecha_str}' no es válido. Use DD/MM/AAAA.")
            return None
    else:
        fecha = datetime.now().strftime('%Y-%m-%d') # Fecha actual por defecto

    # Validar el medio de pago
    if medio_pago not in MEDIOS_DE_PAGO_VALIDOS:
        print(f"Error: Medio de pago '{medio_pago}' no reconocido. Los válidos son: {', '.join(MEDIOS_DE_PAGO_VALIDOS)}")
        return None

    return {
        "monto": monto,
        "descripcion": descripcion,
        "medio_pago": medio_pago,
        "fecha": fecha
    }

# --- Bloque de prueba (Puedes ejecutar este archivo directamente para probar la DB y el parser) ---
if __name__ == "__main__":
    setup_database()

    print("\n--- Probando el parser de gastos ---")

    # Ejemplos válidos
    gasto1 = parsear_gasto_csv("150.75,Cena con amigos,Tarjeta de Crédito BBVA")
    if gasto1:
        print(f"Parseado correctamente (sin fecha): {gasto1}")
        insertar_gasto(**gasto1)

    gasto2 = parsear_gasto_csv("50,Café,Efectivo,12/07/2025")
    if gasto2:
        print(f"Parseado correctamente (con fecha): {gasto2}")
        insertar_gasto(**gasto2)

    gasto3 = parsear_gasto_csv("3000,Alquiler,Transferencia Bancaria")
    if gasto3:
        print(f"Parseado correctamente (sin fecha): {gasto3}")
        insertar_gasto(**gasto3)

    # Ejemplos inválidos
    print("\n--- Probando el parser con errores ---")
    parsear_gasto_csv("cien,Comida,Efectivo") # Monto inválido
    parsear_gasto_csv("100,Comida,Tarjeta Inexistente") # Medio de pago inválido
    parsear_gasto_csv("200,Libro,Efectivo,ayer") # Formato de fecha inválido
    parsear_gasto_csv("50") # Muy pocas partes
    parsear_gasto_csv("50,desc,medio,fecha,extra") # Demasiadas partes


    # Opcional: Verificar los gastos después de las nuevas inserciones
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_NAME)
        cursor = conn.cursor()
        print("\n--- Gastos actuales en la base de datos (incluyendo los nuevos) ---")
        for row in cursor.execute("SELECT id, monto, descripcion, medio_pago, fecha FROM gastos ORDER BY fecha DESC"):
            print(row)
    except sqlite3.Error as e:
        print(f"Error al leer gastos: {e}")
    finally:
        if conn:
            conn.close()