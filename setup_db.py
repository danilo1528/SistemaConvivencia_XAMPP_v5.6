"""
setup_db.py — Configuracion inicial del Sistema de Convivencia Escolar
Ejecutar UNA VEZ antes de usar la aplicacion.
Compatible con XAMPP (MySQL sin contrasena) y MySQL con contrasena.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.chdir(os.path.dirname(os.path.abspath(__file__)))

import mysql.connector
from mysql.connector import Error
import hashlib, configparser

ADMIN_EMAIL    = "admin@clases.edu.sv"
ADMIN_PASSWORD = "Admin2024!"
ADMIN_NOMBRE   = "Administrador del Sistema"

def hash_password(pwd):
    return hashlib.sha256(f"convivencia_salt_2024{pwd}".encode()).hexdigest()

def leer_config():
    cfg = configparser.RawConfigParser()
    cfg.read("config.ini", encoding="utf-8")
    if cfg.has_section("mysql"):
        return {
            "host":     cfg.get("mysql","host",    fallback="127.0.0.1"),
            "port":     int(cfg.get("mysql","port",fallback="3306")),
            "database": cfg.get("mysql","database",fallback="convivencia_escolar"),
            "user":     cfg.get("mysql","user",    fallback="root"),
            "password": cfg.get("mysql","password",fallback=""),
        }
    return {"host":"127.0.0.1","port":3306,"database":"convivencia_escolar","user":"root","password":""}

def guardar_config(cfg_data):
    cfg = configparser.RawConfigParser()
    cfg["mysql"] = {
        "host":     cfg_data["host"],
        "port":     str(cfg_data["port"]),
        "database": cfg_data["database"],
        "user":     cfg_data["user"],
        "password": cfg_data["password"],
    }
    with open("config.ini","w",encoding="utf-8") as f:
        cfg.write(f)
    print("  Configuracion guardada en config.ini")

def run_schema(cursor):
    print("  Creando tablas...")
    with open("schema.sql","r",encoding="utf-8") as f:
        sql = f.read()

    # Eliminar comentarios de línea completa
    import re
    lines = []
    for line in sql.splitlines():
        stripped = line.strip()
        if stripped.startswith("--"):
            continue
        lines.append(line)
    sql_clean = "\n".join(lines)

    # Dividir en sentencias por ";" pero respetando bloques completos
    # Usamos regex para dividir por ";" seguido de salto de línea o fin
    statements = re.split(r';\s*\n', sql_clean)

    for stmt in statements:
        stmt = stmt.strip()
        if not stmt:
            continue
        # Ignorar solo CREATE DATABASE y USE (ya ejecutados antes)
        upper = stmt.upper()
        if upper.startswith("CREATE DATABASE") or upper.startswith("USE "):
            continue
        try:
            cursor.execute(stmt)
        except Error as e:
            # Ignorar errores de "ya existe"
            if e.errno in (1060, 1061, 1062, 1050, 1304, 1065):
                pass
            else:
                print(f"  Aviso {e.errno}: {str(e.msg)[:100]}")

def setup():
    print()
    print("=" * 55)
    print("  CONFIGURACION INICIAL")
    print("  Sistema de Convivencia Escolar - MINEDUCYT")
    print("=" * 55)
    print()

    # Leer config existente
    cfg = leer_config()

    print(f"  Servidor MySQL : {cfg['host']}:{cfg['port']}")
    print(f"  Base de datos  : {cfg['database']}")
    print(f"  Usuario        : {cfg['user']}")
    print(f"  Contrasena     : {'(configurada)' if cfg['password'] else '(vacia - XAMPP default)'}")
    print()

    # Si no hay config.ini o la contrasena esta vacia, preguntar
    cfg_file_existe = os.path.exists("config.ini")
    if not cfg_file_existe:
        # Primera vez: preguntar contrasena
        print("  XAMPP MySQL normalmente NO tiene contrasena.")
        print("  Si su MySQL no tiene contrasena, solo presione Enter.")
        resp = input("  Contrasena de MySQL (Enter si no tiene): ").strip()
        cfg["password"] = resp
        guardar_config(cfg)
    else:
        print("  Usando configuracion de config.ini")

    print()
    print("  Conectando a MySQL...")

    try:
        conn = mysql.connector.connect(
            host=cfg["host"], port=cfg["port"],
            user=cfg["user"], password=cfg["password"],
            charset="utf8mb4", connection_timeout=10
        )
        print("  Conexion exitosa!")
        cursor = conn.cursor()

        # Crear base de datos
        cursor.execute(
            f"CREATE DATABASE IF NOT EXISTS `{cfg['database']}` "
            "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
        )
        cursor.execute(f"USE `{cfg['database']}`")
        conn.database = cfg["database"]
        print(f"  Base de datos '{cfg['database']}' lista.")

        # Crear tablas
        run_schema(cursor)
        conn.commit()
        print("  Tablas creadas correctamente.")

        # Crear tabla usuario_grados si no existe (nueva en v3.5)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS usuario_grados (
                id         INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
                id_usuario INT UNSIGNED NOT NULL,
                id_grado   INT UNSIGNED NOT NULL,
                UNIQUE KEY uq_usr_grado (id_usuario, id_grado),
                CONSTRAINT fk_ug_usr   FOREIGN KEY (id_usuario) REFERENCES usuarios(id_usuario) ON DELETE CASCADE,
                CONSTRAINT fk_ug_grado FOREIGN KEY (id_grado)   REFERENCES grados(id_grado)    ON DELETE CASCADE
            )
        """)
        conn.commit()

        # Crear usuario admin
        hash_admin = hash_password(ADMIN_PASSWORD)
        cursor.execute("""
            INSERT INTO usuarios (nombre_completo, correo, contrasena_hash, id_rol)
            VALUES (%s, %s, %s, 1)
            ON DUPLICATE KEY UPDATE
                contrasena_hash = VALUES(contrasena_hash),
                nombre_completo = VALUES(nombre_completo)
        """, (ADMIN_NOMBRE, ADMIN_EMAIL, hash_admin))
        conn.commit()
        print(f"  Usuario administrador configurado.")

        cursor.close()
        conn.close()

        # Guardar config final con contrasena
        guardar_config(cfg)

        print()
        print("=" * 55)
        print("  CONFIGURACION COMPLETADA EXITOSAMENTE")
        print("=" * 55)
        print()
        print("  Credenciales de acceso al sistema:")
        print(f"  Correo    : {ADMIN_EMAIL}")
        print(f"  Contrasena: {ADMIN_PASSWORD}")
        print()
        print("  Para iniciar el servidor:")
        print("  python app.py")
        print()
        print("  Luego abra en su navegador:")
        print("  http://localhost:5000")
        print()

    except Error as e:
        print()
        print("  ERROR DE CONEXION MySQL:")
        print(f"  {e}")
        print()
        print("  Soluciones:")
        print("  1. Verifique que XAMPP este abierto y MySQL este en verde (Running)")
        print("  2. Verifique la contrasena en config.ini")
        print("  3. Intente cambiar host de localhost a 127.0.0.1 en config.ini")
        print()
        raise SystemExit(1)

if __name__ == "__main__":
    setup()
