import os
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
from passlib.context import CryptContext

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

# Configuración del contexto de cifrado de contraseñas
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_connection():
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)

def verificar_password(password_plano, password_hash):
    """Compara la contraseña introducida con el hash guardado en la BD."""
    return pwd_context.verify(password_plano, password_hash)

def obtener_usuario_por_nombre(nombre):
    """Busca un usuario por su nombre exacto (case-insensitive)."""
    conn = get_connection()
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM usuarios WHERE LOWER(nombre) = LOWER(%s);", (nombre,))
        user = cur.fetchone()
    conn.close()
    return user

def obtener_jornada_activa(usuario_id):
    """Retorna la jornada activa tal cual está en la base de datos."""
    conn = get_connection()
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id, usuario_id, fecha_inicio FROM fichajes WHERE usuario_id = %s AND fecha_fin IS NULL;",
            (usuario_id,)
        )
        fichaje = cur.fetchone()
    conn.close()
    return fichaje

def iniciar_jornada(usuario_id):
    """Registra el inicio de una nueva jornada."""
    conn = get_connection()
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO fichajes (usuario_id, fecha_inicio) VALUES (%s, NOW());",
            (usuario_id,)
        )
        conn.commit()
    conn.close()

def finalizar_jornada(fichaje_id):
    """Registra el fin de la jornada activa."""
    conn = get_connection()
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE fichajes SET fecha_fin = NOW() WHERE id = %s;",
            (fichaje_id,)
        )
        conn.commit()
    conn.close()

def obtener_historial_fichajes(usuario_id):
    """Obtiene el historial formateando las fechas a la zona horaria de Madrid."""
    conn = get_connection()
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT 
                id,
                TO_CHAR(fecha_inicio AT TIME ZONE 'Europe/Madrid', 'DD/MM/YYYY HH24:MI:SS') AS "Inici",
                TO_CHAR(fecha_fin AT TIME ZONE 'Europe/Madrid', 'DD/MM/YYYY HH24:MI:SS') AS "Fi",
                ROUND(EXTRACT(EPOCH FROM (fecha_fin - fecha_inicio)) / 3600.0, 2) AS "Hores"
            FROM fichajes 
            WHERE usuario_id = %s AND fecha_fin IS NOT NULL
            ORDER BY fecha_inicio DESC;
            """,
            (usuario_id,)
        )
        historial = cur.fetchall()
    conn.close()
    return historial


def obtener_empleados():
    """Obtiene la lista de todos los usuarios con rol 'empleado'."""
    conn = get_connection()
    with conn.cursor() as cur:
        cur.execute("SELECT id, nombre, email FROM usuarios WHERE rol = 'empleado' ORDER BY nombre;")
        empleados = cur.fetchall()
    conn.close()
    return empleados

def obtener_tarifa_mes(usuario_id, anio, mes):
    """
    Obtiene la tarifa del mes seleccionado. Si no existe, busca la última 
    tarifa registrada para ese usuario en meses/años anteriores. Si tampoco 
    hay ninguna previa, devuelve 0.0.
    """
    conn = get_connection()
    with conn.cursor() as cur:
        # 1. Buscar si ya hay una tarifa exacta para este mes y año
        cur.execute(
            "SELECT precio_hora FROM tarifas_mensuales WHERE usuario_id = %s AND anio = %s AND mes = %s;",
            (usuario_id, anio, mes)
        )
        res = cur.fetchone()
        
        if res:
            tarifa = float(res['precio_hora'])
        else:
            # 2. Si no existe, buscar la última tarifa guardada anteriormente
            cur.execute(
                """
                SELECT precio_hora 
                FROM tarifas_mensuales 
                WHERE usuario_id = %s AND (anio < %s OR (anio = %s AND mes < %s))
                ORDER BY anio DESC, mes DESC 
                LIMIT 1;
                """,
                (usuario_id, anio, anio, mes)
            )
            res_anterior = cur.fetchone()
            tarifa = float(res_anterior['precio_hora']) if res_anterior else 0.0

    conn.close()
    return tarifa

def guardar_tarifa_mes(usuario_id, anio, mes, precio_hora):
    """Guarda o actualiza el precio por hora para el mes."""
    conn = get_connection()
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO tarifas_mensuales (usuario_id, anio, mes, precio_hora)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (usuario_id, anio, mes) 
            DO UPDATE SET precio_hora = EXCLUDED.precio_hora;
            """,
            (usuario_id, anio, mes, precio_hora)
        )
        conn.commit()
    conn.close()

def obtener_fichajes_mes(usuario_id, anio, mes):
    """Obtiene los fichajes cerrados de un mes específico."""
    conn = get_connection()
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT 
                id,
                TO_CHAR(fecha_inicio AT TIME ZONE 'Europe/Madrid', 'DD/MM/YYYY HH24:MI:SS') AS "Inici",
                TO_CHAR(fecha_fin AT TIME ZONE 'Europe/Madrid', 'DD/MM/YYYY HH24:MI:SS') AS "Fi",
                ROUND(EXTRACT(EPOCH FROM (fecha_fin - fecha_inicio)) / 3600.0, 2) AS "Hores"
            FROM fichajes 
            WHERE usuario_id = %s 
              AND fecha_fin IS NOT NULL
              AND EXTRACT(YEAR FROM fecha_inicio AT TIME ZONE 'Europe/Madrid') = %s
              AND EXTRACT(MONTH FROM fecha_inicio AT TIME ZONE 'Europe/Madrid') = %s
            ORDER BY fecha_inicio DESC;
            """,
            (usuario_id, anio, mes)
        )
        historial = cur.fetchall()
    conn.close()
    return historial



def obtener_resumen_mes_actual(usuario_id):
    """Calcula las horas exactas redondeadas por fichaje para evitar descuadres de céntimos."""
    conn = get_connection()
    with conn.cursor() as cur:
        # Sumamos los valores YA redondeados por cada fichaje individual (igual que la tabla)
        cur.execute(
            """
            SELECT COALESCE(SUM(ROUND(EXTRACT(EPOCH FROM (fecha_fin - fecha_inicio)) / 3600.0, 2)), 0) AS total_horas
            FROM fichajes
            WHERE usuario_id = %s
              AND fecha_fin IS NOT NULL
              AND EXTRACT(YEAR FROM fecha_inicio AT TIME ZONE 'Europe/Madrid') = EXTRACT(YEAR FROM CURRENT_DATE)
              AND EXTRACT(MONTH FROM fecha_inicio AT TIME ZONE 'Europe/Madrid') = EXTRACT(MONTH FROM CURRENT_DATE);
            """,
            (usuario_id,)
        )
        res_horas = cur.fetchone()
        total_horas = float(res_horas['total_horas']) if res_horas else 0.0

    conn.close()

    # Tarifa aplicable
    from datetime import datetime
    ahora = datetime.now()
    tarifa = obtener_tarifa_mes(usuario_id, ahora.year, ahora.month)

    return total_horas, tarifa