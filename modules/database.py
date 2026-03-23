"""
modules/database.py
Conexión MySQL compatible con XAMPP (sin contraseña por defecto).
Lee configuración desde config.ini junto a app.py.
Memorándum N.° 06-2025 MINEDUCYT
"""
import mysql.connector
from mysql.connector import Error, pooling
import hashlib, os, configparser
from datetime import datetime

# ── Leer config.ini ──────────────────────────────────────────────────────────
def _leer_config():
    """Lee config.ini desde la carpeta del proyecto."""
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    cfg_path = os.path.join(base, "config.ini")
    cfg = configparser.RawConfigParser()
    cfg.read(cfg_path, encoding="utf-8")
    if cfg.has_section("mysql"):
        return {
            "host":     cfg.get("mysql", "host",     fallback="127.0.0.1"),
            "port":     int(cfg.get("mysql", "port", fallback="3306")),
            "database": cfg.get("mysql", "database", fallback="convivencia_escolar"),
            "user":     cfg.get("mysql", "user",     fallback="root"),
            "password": cfg.get("mysql", "password", fallback=""),
        }
    # Fallback: variables de entorno o XAMPP defaults
    return {
        "host":     os.getenv("DB_HOST", "127.0.0.1"),
        "port":     int(os.getenv("DB_PORT", "3306")),
        "database": os.getenv("DB_NAME", "convivencia_escolar"),
        "user":     os.getenv("DB_USER", "root"),
        "password": os.getenv("DB_PASSWORD", ""),
    }

_CFG = _leer_config()

DB_CONFIG = {
    **_CFG,
    "charset":     "utf8mb4",
    "use_unicode": True,
    "autocommit":  False,
}

# ── Catálogos del reglamento ─────────────────────────────────────────────────
CAUSALES_DEMERITO = {
    "A": "A) No saludar al entrar o al salir del aula.",
    "B": "B) Omitir «Por favor» al hacer una petición.",
    "C": "C) Omitir «Gracias» al recibir un favor, material o atención.",
    "D": "D) Usar un tono grosero o irrespetuoso hacia compañeros, docentes o personal.",
}
OPCIONES_REDENCION = {
    "A": "A) Cumplir una semana completa con saludos y expresiones de cortesía ejemplares.",
    "B": "B) Apoyar voluntariamente en actividades de orden y limpieza escolar.",
    "C": "C) Participar en campañas de valores organizadas por el centro educativo.",
}
TIPOS_RECONOCIMIENTO = {
    "A": "A) Diploma de Mención Honorífica de Cortesía Escolar.",
    "B": "B) Mención en Mural Escolar.",
}
ESCALA_CONSECUENCIAS = [
    (3,  5,  "Advertencia verbal y reflexión escrita."),
    (6,  9,  "Comunicación a la familia y tarea correctiva."),
    (10, 10, "Suspensión de privilegios escolares."),
    (11, 14, "Reunión con la dirección y la familia."),
    (15, None, "El estudiante NO podrá ser promovido de grado."),
]
MESES = {1:"Enero",2:"Febrero",3:"Marzo",4:"Abril",5:"Mayo",6:"Junio",
         7:"Julio",8:"Agosto",9:"Septiembre",10:"Octubre",11:"Noviembre",12:"Diciembre"}

def get_consecuencia(saldo):
    for (mn, mx, desc) in ESCALA_CONSECUENCIAS:
        if mx is None and saldo >= mn: return desc
        if mx and mn <= saldo <= mx:   return desc
    return None


class DatabaseManager:
    _pool = None

    @classmethod
    def init_pool(cls):
        """Crea el pool de conexiones. Relee config.ini en cada intento."""
        global DB_CONFIG, _CFG
        _CFG    = _leer_config()
        DB_CONFIG = {**_CFG, "charset":"utf8mb4", "use_unicode":True, "autocommit":False}
        try:
            cls._pool = pooling.MySQLConnectionPool(
                pool_name="conv_pool", pool_size=5, **DB_CONFIG)
        except Error as e:
            raise ConnectionError(
                f"No se pudo conectar a MySQL.\n"
                f"  Host: {_CFG['host']}:{_CFG['port']}\n"
                f"  Usuario: {_CFG['user']}\n"
                f"  Contraseña: {'(vacía)' if not _CFG['password'] else '(configurada)'}\n"
                f"  Error: {e}\n\n"
                f"  Verifique que XAMPP MySQL esté activo y que config.ini tenga los datos correctos."
            )

    @classmethod
    def get_connection(cls):
        if cls._pool is None:
            cls.init_pool()
        try:
            return cls._pool.get_connection()
        except Error:
            cls._pool = None
            cls.init_pool()
            return cls._pool.get_connection()

    @staticmethod
    def hash_password(pwd):
        return hashlib.sha256(f"convivencia_salt_2024{pwd}".encode()).hexdigest()

    @staticmethod
    def execute_query(conn, query, params=None, fetch=False):
        cur = conn.cursor(dictionary=True)
        cur.execute(query, params or ())
        if fetch:
            res = cur.fetchall()
            cur.close()
            return res
        cur.close()

    # ── Configuración ────────────────────────────────────────────────────────
    @classmethod
    def get_config(cls, clave):
        conn = cls.get_connection()
        try:
            rows = cls.execute_query(conn,
                "SELECT valor FROM configuracion_sistema WHERE clave=%s",
                (clave,), fetch=True)
            return rows[0]["valor"] if rows else None
        except: return None
        finally: conn.close()

    @classmethod
    def get_config_ce(cls):
        keys = ["NOMBRE_INSTITUCION","CODIGO_CE","DEPARTAMENTO_CE","MUNICIPIO_CE","DISTRITO_CE"]
        result = {}
        conn = cls.get_connection()
        try:
            rows = cls.execute_query(conn,
                "SELECT clave, valor FROM configuracion_sistema WHERE clave IN (%s,%s,%s,%s,%s)",
                tuple(keys), fetch=True)
            for r in rows: result[r["clave"]] = r["valor"]
        finally: conn.close()
        return result

    # ── Dashboard ────────────────────────────────────────────────────────────
    @classmethod
    def obtener_estadisticas_dashboard(cls, mes, anio, grados_filtro=None):
        conn = cls.get_connection()
        try:
            umbral = int(cls.get_config("UMBRAL_ALERTA") or 3)

            # Construir query y params según si hay filtro de grados
            base_sql = """
                SELECT
                    COUNT(DISTINCT e.id_estudiante) AS total_estudiantes,
                    COALESCE(SUM(CASE WHEN t.causal_demerito IS NOT NULL AND t.activo=1 THEN 1 ELSE 0 END),0) AS total_demeritos,
                    COALESCE(SUM(CASE WHEN t.opcion_redencion IS NOT NULL AND t.activo=1 THEN 1 ELSE 0 END),0) AS total_redenciones,
                    COALESCE(SUM(CASE WHEN t.tipo_reconocimiento IS NOT NULL AND t.activo=1 THEN 1 ELSE 0 END),0) AS total_reconocimientos
                FROM estudiantes e
                LEFT JOIN tarjetas_demerito t
                    ON e.id_estudiante=t.id_estudiante
                    AND t.mes_periodo=%s AND t.anio_periodo=%s AND t.activo=1
                WHERE e.activo=1
            """
            params_est = [mes, anio]
            params_crit = [mes, anio, umbral]

            if grados_filtro and len(grados_filtro) > 0:
                ph = ",".join(["%s"] * len(grados_filtro))
                base_sql = base_sql.rstrip() + " AND e.id_grado IN (" + ph + ")"
                params_est = [mes, anio] + list(grados_filtro)
                params_crit = [mes, anio, umbral] + list(grados_filtro)
                crit_sql = """
                    SELECT COUNT(*) AS n FROM v_totales_tarjeta v
                    JOIN estudiantes e ON v.id_estudiante=e.id_estudiante
                    WHERE v.mes_periodo=%s AND v.anio_periodo=%s
                      AND v.saldo_neto>=%s AND e.id_grado IN (""" + ph + ")"
            else:
                crit_sql = """
                    SELECT COUNT(*) AS n FROM v_totales_tarjeta
                    WHERE mes_periodo=%s AND anio_periodo=%s AND saldo_neto>=%s
                """

            rows = cls.execute_query(conn, base_sql, params_est, fetch=True)
            row0 = rows[0] if rows else {}
            stats = {
                "total_estudiantes":    int(row0.get("total_estudiantes", 0) or 0),
                "total_demeritos":      int(row0.get("total_demeritos", 0) or 0),
                "total_redenciones":    int(row0.get("total_redenciones", 0) or 0),
                "total_reconocimientos":int(row0.get("total_reconocimientos", 0) or 0),
            }

            crit = cls.execute_query(conn, crit_sql, params_crit, fetch=True)
            stats["criticos"] = int(crit[0]["n"]) if crit else 0
            return stats
        finally: conn.close()

    # ── Autenticación ────────────────────────────────────────────────────────
    @classmethod
    def autenticar_usuario(cls, correo, password):
        dominio = "@clases.edu.sv"
        try: dominio = cls.get_config("DOMINIO_CORREO") or dominio
        except: pass
        if not correo.endswith(dominio):
            return None
        conn = cls.get_connection()
        try:
            rows = cls.execute_query(conn, """
                SELECT u.id_usuario, u.nombre_completo, u.correo,
                       u.contrasena_hash, u.activo, u.primer_login, r.nombre AS rol
                FROM usuarios u
                JOIN roles r ON u.id_rol=r.id_rol
                WHERE u.correo=%s AND u.activo=1
            """, (correo,), fetch=True)
            if not rows: return None
            u = rows[0]
            if u["contrasena_hash"] == cls.hash_password(password):
                return {"id_usuario": u["id_usuario"],
                        "nombre_completo": u["nombre_completo"],
                        "correo": u["correo"], "rol": u["rol"],
                        "primer_login": int(u.get("primer_login") or 0)}
            return None
        finally: conn.close()

    # ── Usuarios ─────────────────────────────────────────────────────────────
    @classmethod
    def listar_usuarios(cls):
        conn = cls.get_connection()
        try:
            return cls.execute_query(conn, """
                SELECT u.id_usuario, u.nombre_completo, u.correo,
                       u.activo, u.id_rol, u.primer_login, r.nombre AS rol_nombre
                FROM usuarios u JOIN roles r ON u.id_rol=r.id_rol
                ORDER BY u.nombre_completo
            """, fetch=True)
        finally: conn.close()

    @classmethod
    def crear_usuario(cls, nombre, correo, password, id_rol):
        conn = cls.get_connection()
        try:
            cls.execute_query(conn, """
                INSERT INTO usuarios (nombre_completo, correo, contrasena_hash, id_rol)
                VALUES (%s, %s, %s, %s)
            """, (nombre, correo, cls.hash_password(password), id_rol))
            conn.commit()
        finally: conn.close()

    @classmethod
    def resetear_contrasena(cls, id_usr, nueva):
        conn = cls.get_connection()
        try:
            cls.execute_query(conn,
                "UPDATE usuarios SET contrasena_hash=%s WHERE id_usuario=%s",
                (cls.hash_password(nueva), id_usr))
            conn.commit()
        finally: conn.close()

    @classmethod
    def togglear_usuario(cls, id_usr, activo):
        conn = cls.get_connection()
        try:
            cls.execute_query(conn,
                "UPDATE usuarios SET activo=%s WHERE id_usuario=%s", (activo, id_usr))
            conn.commit()
        finally: conn.close()

    @classmethod
    def listar_roles(cls):
        conn = cls.get_connection()
        try: return cls.execute_query(conn, "SELECT * FROM roles ORDER BY id_rol", fetch=True)
        finally: conn.close()

    # ── Estudiantes ──────────────────────────────────────────────────────────
    @classmethod
    def listar_estudiantes(cls):
        conn = cls.get_connection()
        try:
            return cls.execute_query(conn, """
                SELECT e.id_estudiante, e.nie, e.nombre, e.apellido,
                       e.sexo, e.turno, e.activo,
                       g.nombre AS grado_nombre, g.seccion
                FROM estudiantes e JOIN grados g ON e.id_grado=g.id_grado
                WHERE e.activo=1 ORDER BY e.apellido, e.nombre
            """, fetch=True)
        finally: conn.close()

    @classmethod
    def buscar_estudiantes(cls, q):
        conn = cls.get_connection()
        try:
            like = f"%{q}%"
            return cls.execute_query(conn, """
                SELECT e.id_estudiante, e.nie, e.nombre, e.apellido,
                       e.sexo, e.turno, e.activo,
                       g.nombre AS grado_nombre, g.seccion
                FROM estudiantes e JOIN grados g ON e.id_grado=g.id_grado
                WHERE e.activo=1 AND (e.nie LIKE %s OR e.nombre LIKE %s OR e.apellido LIKE %s)
                ORDER BY e.apellido, e.nombre LIMIT 50
            """, (like, like, like), fetch=True)
        finally: conn.close()

    @classmethod
    def crear_estudiante(cls, datos):
        conn = cls.get_connection()
        try:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO estudiantes
                  (nie, nombre, apellido, sexo, id_grado, turno,
                   nombre_responsable, correo_responsable, telefono_responsable)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """, (datos["nie"], datos["nombre"], datos["apellido"],
                  datos["sexo"], datos["id_grado"], datos.get("turno","Matutino"),
                  datos.get("nombre_responsable",""),
                  datos.get("correo_responsable",""),
                  datos.get("telefono_responsable","")))
            conn.commit()
            return cur.lastrowid
        finally: conn.close()

    @classmethod
    def obtener_estudiante(cls, id_est):
        conn = cls.get_connection()
        try:
            rows = cls.execute_query(conn, """
                SELECT e.*, g.nombre AS grado_nombre, g.seccion
                FROM estudiantes e JOIN grados g ON e.id_grado=g.id_grado
                WHERE e.id_estudiante=%s
            """, (id_est,), fetch=True)
            return rows[0] if rows else {}
        finally: conn.close()

    @classmethod
    def listar_grados(cls):
        conn = cls.get_connection()
        try:
            return cls.execute_query(conn,
                "SELECT id_grado, nombre, seccion, nivel FROM grados ORDER BY id_grado",
                fetch=True)
        finally: conn.close()

    # ── Registros (Instrumento 001) ──────────────────────────────────────────
    @classmethod
    def registrar_evento(cls, datos):
        conn = cls.get_connection()
        try:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO tarjetas_demerito
                  (id_estudiante, fecha, mes_periodo, anio_periodo,
                   causal_demerito, opcion_redencion, tipo_reconocimiento,
                   id_docente_registra, nombre_resp_redencion,
                   firma_estudiante, id_demerito_ref)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """, (
                datos["id_estudiante"],
                datos.get("fecha", datetime.now().strftime("%Y-%m-%d")),
                datos.get("mes_periodo",  datetime.now().month),
                datos.get("anio_periodo", datetime.now().year),
                datos.get("causal_demerito"),
                datos.get("opcion_redencion"),
                datos.get("tipo_reconocimiento"),
                datos["id_docente_registra"],
                datos.get("nombre_resp_redencion"),
                int(datos.get("firma_estudiante", 0)),
                datos.get("id_demerito_ref"),
            ))
            conn.commit()
            return cur.lastrowid
        finally: conn.close()

    @classmethod
    def listar_tarjeta_estudiante(cls, id_est, mes, anio):
        conn = cls.get_connection()
        try:
            return cls.execute_query(conn, """
                SELECT t.*, u.nombre_completo AS docente_nombre
                FROM tarjetas_demerito t
                JOIN usuarios u ON t.id_docente_registra=u.id_usuario
                WHERE t.id_estudiante=%s AND t.mes_periodo=%s AND t.anio_periodo=%s AND t.activo=1
                ORDER BY t.fecha, t.id_registro
            """, (id_est, mes, anio), fetch=True)
        finally: conn.close()

    @classmethod
    def obtener_demeritos_activos_estudiante(cls, id_est, mes, anio):
        conn = cls.get_connection()
        try:
            return cls.execute_query(conn, """
                SELECT id_registro AS id_tarjeta, fecha, causal_demerito
                FROM tarjetas_demerito
                WHERE id_estudiante=%s AND mes_periodo=%s AND anio_periodo=%s
                  AND causal_demerito IS NOT NULL AND activo=1
                ORDER BY fecha
            """, (id_est, mes, anio), fetch=True)
        finally: conn.close()

    @classmethod
    def obtener_totales_tarjeta(cls, id_est, mes, anio):
        conn = cls.get_connection()
        try:
            rows = cls.execute_query(conn, """
                SELECT * FROM v_totales_tarjeta
                WHERE id_estudiante=%s AND mes_periodo=%s AND anio_periodo=%s
            """, (id_est, mes, anio), fetch=True)
            return rows[0] if rows else None
        finally: conn.close()

    @classmethod
    def obtener_estudiantes_en_alerta(cls, mes, anio, grados_filtro=None):
        conn = cls.get_connection()
        try:
            umbral = int(cls.get_config("UMBRAL_ALERTA") or 3)
            # Filtro por grados si se especifica (para docentes)
            if grados_filtro:
                ph = ",".join(["%s"] * len(grados_filtro))
                params = (mes, anio, umbral) + tuple(grados_filtro)
                extra  = f" AND e.id_grado IN ({ph})"
            else:
                params = (mes, anio, umbral)
                extra  = ""
            rows = cls.execute_query(conn, f"""
                SELECT
                    e.id_estudiante, e.nie, e.nombre, e.apellido,
                    e.nombre_responsable, e.telefono_responsable,
                    g.nombre AS grado_nombre, g.seccion, e.turno,
                    v.mes_periodo, v.anio_periodo,
                    v.d_A, v.d_B, v.d_C, v.d_D,
                    v.total_demeritos, v.total_redenciones,
                    v.r_A, v.r_B, v.r_C,
                    v.rc_A, v.rc_B, v.total_reconocimientos,
                    v.saldo_neto
                FROM v_totales_tarjeta v
                JOIN estudiantes e ON v.id_estudiante = e.id_estudiante
                JOIN grados      g ON e.id_grado      = g.id_grado
                WHERE v.mes_periodo=%s AND v.anio_periodo=%s
                  AND v.saldo_neto>=%s{extra}
                ORDER BY v.saldo_neto DESC
            """, params, fetch=True)
            for r in rows:
                r["consecuencia"] = get_consecuencia(int(r.get("saldo_neto", 0) or 0))
            return rows
        finally: conn.close()

    # ── Consolidado (Instrumento 002) ────────────────────────────────────────
    @classmethod
    def obtener_detalle_consolidado_por_mes(cls, anio):
        conn = cls.get_connection()
        try:
            # Matrícula total por sexo (base fija independiente de registros)
            mat = cls.execute_query(conn, """
                SELECT
                    SUM(CASE WHEN sexo='M' THEN 1 ELSE 0 END) AS mat_m,
                    SUM(CASE WHEN sexo='H' THEN 1 ELSE 0 END) AS mat_h
                FROM estudiantes WHERE activo=1
            """, fetch=True)
            mat_m = int(mat[0]["mat_m"] or 0) if mat else 0
            mat_h = int(mat[0]["mat_h"] or 0) if mat else 0

            # Registros por mes del año
            rows = cls.execute_query(conn, """
                SELECT
                    t.mes_periodo AS mes_num,
                    SUM(CASE WHEN t.causal_demerito IS NOT NULL AND e.sexo='M' AND t.activo=1 THEN 1 ELSE 0 END) AS demeritos_m,
                    SUM(CASE WHEN t.causal_demerito IS NOT NULL AND e.sexo='H' AND t.activo=1 THEN 1 ELSE 0 END) AS demeritos_h,
                    SUM(CASE WHEN t.causal_demerito='A' AND t.activo=1 THEN 1 ELSE 0 END) AS d_A,
                    SUM(CASE WHEN t.causal_demerito='B' AND t.activo=1 THEN 1 ELSE 0 END) AS d_B,
                    SUM(CASE WHEN t.causal_demerito='C' AND t.activo=1 THEN 1 ELSE 0 END) AS d_C,
                    SUM(CASE WHEN t.causal_demerito='D' AND t.activo=1 THEN 1 ELSE 0 END) AS d_D,
                    SUM(CASE WHEN t.opcion_redencion IS NOT NULL AND e.sexo='M' AND t.activo=1 THEN 1 ELSE 0 END) AS redenciones_m,
                    SUM(CASE WHEN t.opcion_redencion IS NOT NULL AND e.sexo='H' AND t.activo=1 THEN 1 ELSE 0 END) AS redenciones_h,
                    SUM(CASE WHEN t.opcion_redencion='A' AND t.activo=1 THEN 1 ELSE 0 END) AS r_A,
                    SUM(CASE WHEN t.opcion_redencion='B' AND t.activo=1 THEN 1 ELSE 0 END) AS r_B,
                    SUM(CASE WHEN t.opcion_redencion='C' AND t.activo=1 THEN 1 ELSE 0 END) AS r_C,
                    SUM(CASE WHEN t.tipo_reconocimiento IS NOT NULL AND e.sexo='M' AND t.activo=1 THEN 1 ELSE 0 END) AS reconoc_m,
                    SUM(CASE WHEN t.tipo_reconocimiento IS NOT NULL AND e.sexo='H' AND t.activo=1 THEN 1 ELSE 0 END) AS reconoc_h
                FROM tarjetas_demerito t
                JOIN estudiantes e ON t.id_estudiante=e.id_estudiante
                WHERE t.anio_periodo=%s AND t.activo=1
                GROUP BY t.mes_periodo
                ORDER BY t.mes_periodo
            """, (anio,), fetch=True)

            # Agregar matrícula y forzar tipos numéricos
            int_fields = ["demeritos_m","demeritos_h","d_A","d_B","d_C","d_D",
                          "redenciones_m","redenciones_h","r_A","r_B","r_C",
                          "reconoc_m","reconoc_h"]
            for r in rows:
                r["matricula_m"] = int(mat_m)
                r["matricula_h"] = int(mat_h)
                for f in int_fields:
                    r[f] = int(r.get(f) or 0)

            # Si no hay ningún registro, devolver al menos los meses con matrícula
            if not rows:
                from datetime import datetime
                mes_actual = datetime.now().month
                rows = [{"mes_num": m, "matricula_m": mat_m, "matricula_h": mat_h,
                         "demeritos_m":0,"demeritos_h":0,"d_A":0,"d_B":0,"d_C":0,"d_D":0,
                         "redenciones_m":0,"redenciones_h":0,"r_A":0,"r_B":0,"r_C":0,
                         "reconoc_m":0,"reconoc_h":0}
                        for m in range(1, mes_actual+1)]
            return rows
        finally: conn.close()


    # ── Grados asignados a usuarios ──────────────────────────────────────────

    @classmethod
    def obtener_consolidado_filtrado(cls, anio, id_grado=None, id_docente=None):
        """Consolidado filtrado por grado y/o docente."""
        conn = cls.get_connection()
        try:
            # Matrícula filtrada
            mat_q = ("SELECT SUM(CASE WHEN sexo='M' THEN 1 ELSE 0 END) AS mat_m,"
                     " SUM(CASE WHEN sexo='H' THEN 1 ELSE 0 END) AS mat_h"
                     " FROM estudiantes WHERE activo=1")
            params_mat = []
            if id_grado:
                mat_q += " AND id_grado=%s"
                params_mat.append(int(id_grado))
            mat = cls.execute_query(conn, mat_q, params_mat if params_mat else None, fetch=True)
            mat_m = int(mat[0]["mat_m"] or 0) if mat else 0
            mat_h = int(mat[0]["mat_h"] or 0) if mat else 0

            # Construir WHERE sin f-strings para evitar conflictos
            where_parts = ["t.anio_periodo=%s", "t.activo=1"]
            params = [anio]
            if id_grado:
                where_parts.append("e.id_grado=%s")
                params.append(int(id_grado))
            if id_docente:
                where_parts.append("t.id_docente_registra=%s")
                params.append(int(id_docente))
            where = " AND ".join(where_parts)

            sql = ("SELECT t.mes_periodo AS mes_num,"
                   " SUM(CASE WHEN t.causal_demerito IS NOT NULL AND e.sexo='M' THEN 1 ELSE 0 END) AS demeritos_m,"
                   " SUM(CASE WHEN t.causal_demerito IS NOT NULL AND e.sexo='H' THEN 1 ELSE 0 END) AS demeritos_h,"
                   " SUM(CASE WHEN t.causal_demerito='A' THEN 1 ELSE 0 END) AS d_A,"
                   " SUM(CASE WHEN t.causal_demerito='B' THEN 1 ELSE 0 END) AS d_B,"
                   " SUM(CASE WHEN t.causal_demerito='C' THEN 1 ELSE 0 END) AS d_C,"
                   " SUM(CASE WHEN t.causal_demerito='D' THEN 1 ELSE 0 END) AS d_D,"
                   " SUM(CASE WHEN t.opcion_redencion IS NOT NULL AND e.sexo='M' THEN 1 ELSE 0 END) AS redenciones_m,"
                   " SUM(CASE WHEN t.opcion_redencion IS NOT NULL AND e.sexo='H' THEN 1 ELSE 0 END) AS redenciones_h,"
                   " SUM(CASE WHEN t.opcion_redencion='A' THEN 1 ELSE 0 END) AS r_A,"
                   " SUM(CASE WHEN t.opcion_redencion='B' THEN 1 ELSE 0 END) AS r_B,"
                   " SUM(CASE WHEN t.opcion_redencion='C' THEN 1 ELSE 0 END) AS r_C,"
                   " SUM(CASE WHEN t.tipo_reconocimiento IS NOT NULL AND e.sexo='M' THEN 1 ELSE 0 END) AS reconoc_m,"
                   " SUM(CASE WHEN t.tipo_reconocimiento IS NOT NULL AND e.sexo='H' THEN 1 ELSE 0 END) AS reconoc_h"
                   " FROM tarjetas_demerito t"
                   " JOIN estudiantes e ON t.id_estudiante=e.id_estudiante"
                   " WHERE " + where +
                   " GROUP BY t.mes_periodo ORDER BY t.mes_periodo")

            rows = cls.execute_query(conn, sql, params, fetch=True)

            int_fields = ["demeritos_m","demeritos_h","d_A","d_B","d_C","d_D",
                          "redenciones_m","redenciones_h","r_A","r_B","r_C",
                          "reconoc_m","reconoc_h"]
            for r in rows:
                r["matricula_m"] = int(mat_m)
                r["matricula_h"] = int(mat_h)
                for f in int_fields:
                    r[f] = int(r.get(f) or 0)

            if not rows:
                from datetime import datetime as _dt
                mes_actual = _dt.now().month
                rows = [{"mes_num": m, "matricula_m": mat_m, "matricula_h": mat_h,
                         "demeritos_m":0,"demeritos_h":0,"d_A":0,"d_B":0,"d_C":0,"d_D":0,
                         "redenciones_m":0,"redenciones_h":0,"r_A":0,"r_B":0,"r_C":0,
                         "reconoc_m":0,"reconoc_h":0}
                        for m in range(1, mes_actual+1)]
            return rows
        finally: conn.close()

    @classmethod
    def actualizar_estudiante(cls, id_est, datos):
        """Actualiza los datos de un estudiante."""
        conn = cls.get_connection()
        try:
            cls.execute_query(conn, """
                UPDATE estudiantes SET nie=%s, nombre=%s, apellido=%s, sexo=%s,
                    id_grado=%s, turno=%s, nombre_responsable=%s,
                    telefono_responsable=%s, correo_responsable=%s
                WHERE id_estudiante=%s
            """, (datos.get("nie"), datos.get("nombre"), datos.get("apellido"),
                  datos.get("sexo"), datos.get("id_grado"), datos.get("turno"),
                  datos.get("nombre_responsable",""), datos.get("telefono_responsable",""),
                  datos.get("correo_responsable",""), id_est))
            conn.commit()
        finally: conn.close()

    @classmethod
    def eliminar_estudiante(cls, id_est):
        """Desactiva (soft-delete) un estudiante."""
        conn = cls.get_connection()
        try:
            cls.execute_query(conn, "UPDATE estudiantes SET activo=0 WHERE id_estudiante=%s", (id_est,))
            conn.commit()
        finally: conn.close()

    @classmethod
    def eliminar_usuario(cls, id_usuario):
        """Elimina permanentemente un usuario."""
        conn = cls.get_connection()
        try:
            cls.execute_query(conn, "DELETE FROM usuario_grados WHERE id_usuario=%s", (id_usuario,))
            cls.execute_query(conn, "DELETE FROM usuarios WHERE id_usuario=%s", (id_usuario,))
            conn.commit()
        finally: conn.close()

    @classmethod
    def obtener_estudiante(cls, id_est):
        """Obtiene datos completos de un estudiante para edición."""
        conn = cls.get_connection()
        try:
            rows = cls.execute_query(conn, """
                SELECT e.*, g.nombre AS grado_nombre, g.seccion
                FROM estudiantes e JOIN grados g ON e.id_grado=g.id_grado
                WHERE e.id_estudiante=%s
            """, (id_est,), fetch=True)
            return rows[0] if rows else None
        finally: conn.close()

    @classmethod
    def obtener_grados_usuario(cls, id_usuario):
        """Retorna lista de id_grado asignados. Si es Admin o no tiene asignados: todos."""
        conn = cls.get_connection()
        try:
            # Verificar si es admin
            rows = cls.execute_query(conn,
                "SELECT r.nombre FROM usuarios u JOIN roles r ON u.id_rol=r.id_rol WHERE u.id_usuario=%s",
                (id_usuario,), fetch=True)
            if rows and rows[0]["nombre"] == "Administrador":
                all_g = cls.execute_query(conn, "SELECT id_grado FROM grados", fetch=True)
                return [r["id_grado"] for r in all_g]
            asig = cls.execute_query(conn,
                "SELECT id_grado FROM usuario_grados WHERE id_usuario=%s", (id_usuario,), fetch=True)
            if asig:
                return [r["id_grado"] for r in asig]
            # Sin asignación específica: acceso a todos
            all_g = cls.execute_query(conn, "SELECT id_grado FROM grados", fetch=True)
            return [r["id_grado"] for r in all_g]
        finally: conn.close()

    @classmethod
    def asignar_grados_usuario(cls, id_usuario, lista_id_grados):
        """Reemplaza los grados asignados al usuario."""
        conn = cls.get_connection()
        try:
            cls.execute_query(conn,
                "DELETE FROM usuario_grados WHERE id_usuario=%s", (id_usuario,))
            for id_g in lista_id_grados:
                try:
                    cls.execute_query(conn,
                        "INSERT IGNORE INTO usuario_grados (id_usuario,id_grado) VALUES (%s,%s)",
                        (id_usuario, int(id_g)))
                except: pass
            conn.commit()
        finally: conn.close()

    @classmethod
    def listar_grados_con_asignacion(cls, id_usuario):
        """Lista todos los grados indicando si están asignados al usuario."""
        conn = cls.get_connection()
        try:
            rows = cls.execute_query(conn, """
                SELECT g.id_grado, g.nombre, g.seccion, g.nivel,
                       CASE WHEN ug.id_usuario IS NOT NULL THEN 1 ELSE 0 END AS asignado
                FROM grados g
                LEFT JOIN usuario_grados ug
                       ON g.id_grado=ug.id_grado AND ug.id_usuario=%s
                ORDER BY g.id_grado
            """, (id_usuario,), fetch=True)
            return rows
        finally: conn.close()

    @classmethod
    def listar_estudiantes_por_usuario(cls, id_usuario, q="", id_grado_filtro=None):
        """Retorna estudiantes filtrados según grados asignados al usuario y filtro opcional."""
        grados = cls.obtener_grados_usuario(id_usuario)
        if not grados:
            return []
        # Si hay filtro de grado específico, verificar que esté en los grados permitidos
        if id_grado_filtro and int(id_grado_filtro) in grados:
            grados = [int(id_grado_filtro)]
        elif id_grado_filtro:
            return []  # grado no permitido
        conn = cls.get_connection()
        try:
            placeholders = ",".join(["%s"]*len(grados))
            base = f"""
                SELECT e.id_estudiante, e.nie, e.nombre, e.apellido,
                       e.sexo, e.turno, e.activo, e.id_grado,
                       g.nombre AS grado_nombre, g.seccion
                FROM estudiantes e JOIN grados g ON e.id_grado=g.id_grado
                WHERE e.activo=1 AND e.id_grado IN ({placeholders})
            """
            params = list(grados)
            if q:
                base += " AND (e.nie LIKE %s OR e.nombre LIKE %s OR e.apellido LIKE %s)"
                like = f"%{q}%"
                params += [like, like, like]
            base += " ORDER BY g.nombre, g.seccion, e.apellido, e.nombre LIMIT 200"
            return cls.execute_query(conn, base, tuple(params), fetch=True)
        finally: conn.close()

    @classmethod
    def registrar_boleta(cls, id_est, ruta, mes, anio, demeritos, generada_por):
        conn = cls.get_connection()
        try:
            cls.execute_query(conn, """
                INSERT INTO boletas_notificacion
                  (id_estudiante,ruta_archivo,mes_periodo,anio_periodo,demeritos_al_generar,generada_por)
                VALUES (%s,%s,%s,%s,%s,%s)
            """, (id_est, ruta, mes, anio, demeritos, generada_por))
            conn.commit()
        finally: conn.close()
