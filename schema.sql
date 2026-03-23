-- ============================================================
-- SISTEMA DE GESTIÓN DE CONVIVENCIA ESCOLAR
-- Basado en: Memorándum N.° 06-2025 MINEDUCYT
-- Instrumento No. 001: Tarjeta de Deméritos del Estudiante
-- Instrumento No. 002: Registro Consolidado Mensual (Docente)
-- ============================================================

CREATE DATABASE IF NOT EXISTS convivencia_escolar
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE convivencia_escolar;

-- ============================================================
-- TABLA: roles
-- ============================================================
CREATE TABLE IF NOT EXISTS roles (
    id_rol      INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    nombre      VARCHAR(50) NOT NULL UNIQUE,
    descripcion VARCHAR(255)
);

INSERT INTO roles (nombre, descripcion) VALUES
    ('Administrador', 'Acceso completo al sistema'),
    ('Docente', 'Registro de eventos y consulta de sus registros')
ON DUPLICATE KEY UPDATE nombre = nombre;

-- ============================================================
-- TABLA: usuarios
-- ============================================================
CREATE TABLE IF NOT EXISTS usuarios (
    id_usuario      INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    nombre_completo VARCHAR(150) NOT NULL,
    correo          VARCHAR(150) NOT NULL UNIQUE,
    contrasena_hash VARCHAR(255) NOT NULL,
    id_rol          INT UNSIGNED NOT NULL,
    activo          TINYINT(1) DEFAULT 1,
    primer_login    TINYINT(1) DEFAULT 1,
    creado_en       DATETIME DEFAULT CURRENT_TIMESTAMP,
    actualizado_en  DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_usuario_rol FOREIGN KEY (id_rol) REFERENCES roles(id_rol)
);

-- ============================================================
-- TABLA: centros_educativos
-- Campos 1-5 de ambos instrumentos
-- ============================================================
CREATE TABLE IF NOT EXISTS centros_educativos (
    id_centro       INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    nombre          VARCHAR(200) NOT NULL,
    codigo          VARCHAR(10)  NOT NULL UNIQUE,
    departamento    VARCHAR(60)  NOT NULL,
    municipio       VARCHAR(80)  NOT NULL,
    distrito        VARCHAR(80)  NOT NULL
);

INSERT INTO centros_educativos (nombre, codigo, departamento, municipio, distrito)
VALUES ('Centro Escolar Nacional', '10001', 'San Salvador', 'San Salvador Sur', 'Panchimalco')
ON DUPLICATE KEY UPDATE nombre = nombre;

-- ============================================================
-- TABLA: grados  (Campo 9: Grado/Sección)
-- ============================================================
CREATE TABLE IF NOT EXISTS grados (
    id_grado    INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    nombre      VARCHAR(50) NOT NULL,
    seccion     VARCHAR(5)  NOT NULL,
    nivel       VARCHAR(50),
    UNIQUE KEY uk_grado_seccion (nombre, seccion)
);

INSERT INTO grados (nombre, seccion, nivel) VALUES
    ('1°','A','Básica'),('1°','B','Básica'),
    ('2°','A','Básica'),('2°','B','Básica'),
    ('3°','A','Básica'),('3°','B','Básica'),
    ('4°','A','Básica'),('4°','B','Básica'),
    ('5°','A','Básica'),('5°','B','Básica'),
    ('6°','A','Básica'),('6°','B','Básica'),
    ('7°','A','Básica'),('7°','B','Básica'),
    ('8°','A','Básica'),('8°','B','Básica'),
    ('9°','A','Básica'),('9°','B','Básica'),
    ('1° Bachillerato','A','Bachillerato'),
    ('1° Bachillerato','B','Bachillerato'),
    ('2° Bachillerato','A','Bachillerato'),
    ('2° Bachillerato','B','Bachillerato')
ON DUPLICATE KEY UPDATE nombre = nombre;

-- ============================================================
-- TABLA: estudiantes  (Campos 6-10 Instrumento No. 001)
-- ============================================================
CREATE TABLE IF NOT EXISTS estudiantes (
    id_estudiante       INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    nie                 VARCHAR(20) NOT NULL UNIQUE,        -- Campo 7. NIE
    nombre              VARCHAR(100) NOT NULL,              -- Campo 6. Nombre (parte)
    apellido            VARCHAR(100) NOT NULL,              -- Campo 6. Nombre (parte)
    sexo                ENUM('M','H') NOT NULL,             -- Campo 8. Sexo M=Mujer H=Hombre
    id_grado            INT UNSIGNED NOT NULL,              -- Campo 9. Grado/Sección
    turno               ENUM('Matutino','Vespertino','Nocturno') DEFAULT 'Matutino', -- Campo 10
    id_centro           INT UNSIGNED NOT NULL DEFAULT 1,
    nombre_responsable  VARCHAR(150),
    correo_responsable  VARCHAR(150),
    telefono_responsable VARCHAR(20),
    activo              TINYINT(1) DEFAULT 1,
    creado_en           DATETIME DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_est_grado  FOREIGN KEY (id_grado)  REFERENCES grados(id_grado),
    CONSTRAINT fk_est_centro FOREIGN KEY (id_centro) REFERENCES centros_educativos(id_centro)
);

-- ============================================================
-- CATÁLOGOS EXACTOS DEL REGLAMENTO
-- ============================================================

-- Causales de Demérito — Art. 3 / Campo 12 (columnas A, B, C, D)
CREATE TABLE IF NOT EXISTS causales_demerito (
    codigo      CHAR(1) PRIMARY KEY,
    descripcion TEXT NOT NULL
);
INSERT INTO causales_demerito (codigo, descripcion) VALUES
    ('A','No saludar al entrar o al salir del aula.'),
    ('B','Omitir «Por favor» al hacer una petición.'),
    ('C','Omitir «Gracias» al recibir un favor, material o atención.'),
    ('D','Usar un tono grosero o irrespetuoso hacia compañeros, docentes o personal.')
ON DUPLICATE KEY UPDATE descripcion = descripcion;

-- Opciones de Redención — Art. 6 / Campo 13 (columnas A, B, C)
CREATE TABLE IF NOT EXISTS opciones_redencion (
    codigo      CHAR(1) PRIMARY KEY,
    descripcion TEXT NOT NULL
);
INSERT INTO opciones_redencion (codigo, descripcion) VALUES
    ('A','Cumplir una semana completa con saludos y expresiones de cortesía ejemplares.'),
    ('B','Apoyar voluntariamente en actividades de orden y limpieza escolar.'),
    ('C','Participar en campañas de valores organizadas por el centro educativo.')
ON DUPLICATE KEY UPDATE descripcion = descripcion;

-- Tipos de Reconocimiento — Art. 7 / Campo 14 (columnas A, B)
CREATE TABLE IF NOT EXISTS tipos_reconocimiento (
    codigo      CHAR(1) PRIMARY KEY,
    descripcion TEXT NOT NULL
);
INSERT INTO tipos_reconocimiento (codigo, descripcion) VALUES
    ('A','Diploma de Mención Honorífica de Cortesía Escolar.'),
    ('B','Mención en Mural Escolar.')
ON DUPLICATE KEY UPDATE descripcion = descripcion;

-- Escala de consecuencias — Art. 5
CREATE TABLE IF NOT EXISTS escala_consecuencias (
    id_escala   INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    umbral_min  INT UNSIGNED NOT NULL,
    umbral_max  INT UNSIGNED,
    descripcion TEXT NOT NULL
);
INSERT INTO escala_consecuencias (umbral_min, umbral_max, descripcion) VALUES
    (3,  5,  'Advertencia verbal y reflexión escrita («La importancia de la cortesía»).'),
    (6,  9,  'Comunicación a la familia y tarea correctiva (redactar un texto, elaborar un cartel o participar en una actividad sobre cortesía).'),
    (10, 10, 'Suspensión de privilegios escolares (participación en juegos, actividades culturales o recreativas).'),
    (11, 14, 'Reunión con la dirección y la familia, acompañada de una última advertencia para el estudiante.'),
    (15, NULL,'El estudiante no podrá ser promovido de grado.')
ON DUPLICATE KEY UPDATE descripcion = descripcion;

-- ============================================================
-- TABLA PRINCIPAL: tarjetas_demerito
-- Instrumento No. 001, Campos 11-17
-- Una fila = una entrada en la tarjeta física del estudiante
-- ============================================================
CREATE TABLE IF NOT EXISTS tarjetas_demerito (
    id_registro             BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    id_estudiante           INT UNSIGNED NOT NULL,
    -- Campo 11. Fecha (dd/mm/aaaa en UI, DATE en BD)
    fecha                   DATE NOT NULL,
    mes_periodo             TINYINT UNSIGNED NOT NULL,
    anio_periodo            YEAR NOT NULL,
    -- Campo 12. D: Demérito  (solo una letra: A, B, C, D  — o NULL)
    causal_demerito         CHAR(1) DEFAULT NULL,
    -- Campo 13. R: Redención  (solo una letra: A, B, C   — o NULL)
    opcion_redencion        CHAR(1) DEFAULT NULL,
    -- Campo 14. RC: Reconocimiento  (solo una letra: A, B — o NULL)
    tipo_reconocimiento     CHAR(1) DEFAULT NULL,
    -- Campo 15. Nombre y firma de quien registra
    id_docente_registra     INT UNSIGNED NOT NULL,
    -- Campo 16. Nombre y firma del Responsable de Cumplimiento de Redención
    nombre_resp_redencion   VARCHAR(150) DEFAULT NULL,
    -- Campo 17. Firma del estudiante (booleano: 1 = firmó)
    firma_estudiante        TINYINT(1) DEFAULT 0,
    -- Referencias y control
    id_demerito_ref         BIGINT UNSIGNED DEFAULT NULL,
    autorizado_por          INT UNSIGNED DEFAULT NULL,
    activo                  TINYINT(1) DEFAULT 1,
    creado_en               DATETIME DEFAULT CURRENT_TIMESTAMP,
    actualizado_en          DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_td_estudiante FOREIGN KEY (id_estudiante)      REFERENCES estudiantes(id_estudiante),
    CONSTRAINT fk_td_docente    FOREIGN KEY (id_docente_registra) REFERENCES usuarios(id_usuario),
    CONSTRAINT fk_td_autorizado FOREIGN KEY (autorizado_por)     REFERENCES usuarios(id_usuario),
    CONSTRAINT fk_td_dem_ref    FOREIGN KEY (id_demerito_ref)    REFERENCES tarjetas_demerito(id_registro),
    CONSTRAINT fk_td_causal     FOREIGN KEY (causal_demerito)    REFERENCES causales_demerito(codigo),
    CONSTRAINT fk_td_redencion  FOREIGN KEY (opcion_redencion)   REFERENCES opciones_redencion(codigo),
    CONSTRAINT fk_td_reconoc    FOREIGN KEY (tipo_reconocimiento) REFERENCES tipos_reconocimiento(codigo)
);

-- ============================================================
-- TABLA: boletas_notificacion
-- ============================================================
CREATE TABLE IF NOT EXISTS boletas_notificacion (
    id_boleta           BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    id_estudiante       INT UNSIGNED NOT NULL,
    ruta_archivo        VARCHAR(500),
    mes_periodo         TINYINT UNSIGNED NOT NULL,
    anio_periodo        YEAR NOT NULL,
    demeritos_al_generar INT UNSIGNED,
    generada_por        INT UNSIGNED NOT NULL,
    generada_en         DATETIME DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_bol_est FOREIGN KEY (id_estudiante) REFERENCES estudiantes(id_estudiante),
    CONSTRAINT fk_bol_usr FOREIGN KEY (generada_por)  REFERENCES usuarios(id_usuario)
);

-- ============================================================
-- TABLA: configuracion_sistema
-- ============================================================
CREATE TABLE IF NOT EXISTS configuracion_sistema (
    clave       VARCHAR(100) PRIMARY KEY,
    valor       VARCHAR(500) NOT NULL,
    descripcion TEXT
);

INSERT INTO configuracion_sistema (clave, valor, descripcion) VALUES
    ('UMBRAL_BOLETA',               '3',   'Deméritos para generar boleta PDF automática'),
    ('UMBRAL_ALERTA',               '3',   'Saldo neto para alerta visual al Administrador'),
    ('FACTOR_REDENCION',            '1',   'Cada N redenciones cancela 1 demérito'),
    ('NOMBRE_INSTITUCION',          'Centro Escolar Nacional', 'Nombre completo del C.E.'),
    ('CODIGO_CE',                   '10001','Código del C.E. (5 dígitos)'),
    ('DEPARTAMENTO_CE',             'San Salvador','Departamento'),
    ('MUNICIPIO_CE',                'San Salvador Sur','Municipio'),
    ('DISTRITO_CE',                 'Panchimalco','Distrito'),
    ('DOMINIO_CORREO',              '@clases.edu.sv','Dominio institucional')
ON DUPLICATE KEY UPDATE valor = valor;

-- ============================================================
-- VISTA: Campo 18. Total — Instrumento No. 001
-- Replica exactamente la fila de totales de la tarjeta física
-- ============================================================
CREATE OR REPLACE VIEW v_totales_tarjeta AS
SELECT
    e.id_estudiante,
    CONCAT(e.nombre,' ',e.apellido) AS nombre_completo,
    e.nie,
    e.sexo,
    g.nombre    AS grado,
    g.seccion,
    e.turno,
    t.mes_periodo,
    t.anio_periodo,
    -- Totales deméritos por causal (columnas A,B,C,D del campo 12)
    SUM(CASE WHEN t.causal_demerito='A' AND t.activo=1 THEN 1 ELSE 0 END) AS d_A,
    SUM(CASE WHEN t.causal_demerito='B' AND t.activo=1 THEN 1 ELSE 0 END) AS d_B,
    SUM(CASE WHEN t.causal_demerito='C' AND t.activo=1 THEN 1 ELSE 0 END) AS d_C,
    SUM(CASE WHEN t.causal_demerito='D' AND t.activo=1 THEN 1 ELSE 0 END) AS d_D,
    SUM(CASE WHEN t.causal_demerito IS NOT NULL AND t.activo=1 THEN 1 ELSE 0 END) AS total_demeritos,
    -- Totales redenciones por opción (columnas A,B,C del campo 13)
    SUM(CASE WHEN t.opcion_redencion='A' AND t.activo=1 THEN 1 ELSE 0 END) AS r_A,
    SUM(CASE WHEN t.opcion_redencion='B' AND t.activo=1 THEN 1 ELSE 0 END) AS r_B,
    SUM(CASE WHEN t.opcion_redencion='C' AND t.activo=1 THEN 1 ELSE 0 END) AS r_C,
    SUM(CASE WHEN t.opcion_redencion IS NOT NULL AND t.activo=1 THEN 1 ELSE 0 END) AS total_redenciones,
    -- Totales reconocimientos (columnas A,B del campo 14)
    SUM(CASE WHEN t.tipo_reconocimiento='A' AND t.activo=1 THEN 1 ELSE 0 END) AS rc_A,
    SUM(CASE WHEN t.tipo_reconocimiento='B' AND t.activo=1 THEN 1 ELSE 0 END) AS rc_B,
    SUM(CASE WHEN t.tipo_reconocimiento IS NOT NULL AND t.activo=1 THEN 1 ELSE 0 END) AS total_reconocimientos,
    -- Saldo neto = Deméritos - Redenciones
    (SUM(CASE WHEN t.causal_demerito IS NOT NULL AND t.activo=1 THEN 1 ELSE 0 END)
   - SUM(CASE WHEN t.opcion_redencion IS NOT NULL AND t.activo=1 THEN 1 ELSE 0 END)) AS saldo_neto
FROM tarjetas_demerito t
JOIN estudiantes e ON t.id_estudiante = e.id_estudiante
JOIN grados g      ON e.id_grado = g.id_grado
GROUP BY e.id_estudiante, t.mes_periodo, t.anio_periodo;

-- ============================================================
-- VISTA: Instrumento No. 002 — Registro Consolidado Mensual
-- Columnas exactas: 11.Mes 12.Matrícula(M/H/Total)
--   13.Dem(M/H/Total) 14.Dem causales(A/B/C/D/Total)
--   15.Red(M/H/Total) 16.Red opciones(A/B/C/Total)
--   17.Reconoc(M/H/Total) 18.Total general
-- ============================================================
CREATE OR REPLACE VIEW v_consolidado_instrumento002 AS
SELECT
    e.id_centro,
    g.nombre        AS grado,
    g.seccion,
    e.turno,
    t.mes_periodo,
    t.anio_periodo,
    -- Col 12. Matrícula por sexo
    COUNT(DISTINCT CASE WHEN e.sexo='M' THEN e.id_estudiante END) AS mat_M,
    COUNT(DISTINCT CASE WHEN e.sexo='H' THEN e.id_estudiante END) AS mat_H,
    COUNT(DISTINCT e.id_estudiante)                                AS mat_Total,
    -- Col 13. Deméritos por sexo
    SUM(CASE WHEN t.causal_demerito IS NOT NULL AND e.sexo='M' AND t.activo=1 THEN 1 ELSE 0 END) AS dem_M,
    SUM(CASE WHEN t.causal_demerito IS NOT NULL AND e.sexo='H' AND t.activo=1 THEN 1 ELSE 0 END) AS dem_H,
    SUM(CASE WHEN t.causal_demerito IS NOT NULL AND t.activo=1 THEN 1 ELSE 0 END)                 AS dem_Total,
    -- Col 14. Deméritos por causal
    SUM(CASE WHEN t.causal_demerito='A' AND t.activo=1 THEN 1 ELSE 0 END) AS dem_A,
    SUM(CASE WHEN t.causal_demerito='B' AND t.activo=1 THEN 1 ELSE 0 END) AS dem_B,
    SUM(CASE WHEN t.causal_demerito='C' AND t.activo=1 THEN 1 ELSE 0 END) AS dem_C,
    SUM(CASE WHEN t.causal_demerito='D' AND t.activo=1 THEN 1 ELSE 0 END) AS dem_D,
    SUM(CASE WHEN t.causal_demerito IS NOT NULL AND t.activo=1 THEN 1 ELSE 0 END) AS dem_causal_Total,
    -- Col 15. Redenciones por sexo
    SUM(CASE WHEN t.opcion_redencion IS NOT NULL AND e.sexo='M' AND t.activo=1 THEN 1 ELSE 0 END) AS red_M,
    SUM(CASE WHEN t.opcion_redencion IS NOT NULL AND e.sexo='H' AND t.activo=1 THEN 1 ELSE 0 END) AS red_H,
    SUM(CASE WHEN t.opcion_redencion IS NOT NULL AND t.activo=1 THEN 1 ELSE 0 END)                 AS red_Total,
    -- Col 16. Redenciones por opción elegida
    SUM(CASE WHEN t.opcion_redencion='A' AND t.activo=1 THEN 1 ELSE 0 END) AS red_A,
    SUM(CASE WHEN t.opcion_redencion='B' AND t.activo=1 THEN 1 ELSE 0 END) AS red_B,
    SUM(CASE WHEN t.opcion_redencion='C' AND t.activo=1 THEN 1 ELSE 0 END) AS red_C,
    SUM(CASE WHEN t.opcion_redencion IS NOT NULL AND t.activo=1 THEN 1 ELSE 0 END) AS red_op_Total,
    -- Col 17. Reconocimientos por sexo
    SUM(CASE WHEN t.tipo_reconocimiento IS NOT NULL AND e.sexo='M' AND t.activo=1 THEN 1 ELSE 0 END) AS reconoc_M,
    SUM(CASE WHEN t.tipo_reconocimiento IS NOT NULL AND e.sexo='H' AND t.activo=1 THEN 1 ELSE 0 END) AS reconoc_H,
    SUM(CASE WHEN t.tipo_reconocimiento IS NOT NULL AND t.activo=1 THEN 1 ELSE 0 END)                 AS reconoc_Total
FROM tarjetas_demerito t
JOIN estudiantes e ON t.id_estudiante = e.id_estudiante
JOIN grados g      ON e.id_grado = g.id_grado
GROUP BY e.id_centro, g.nombre, g.seccion, e.turno, t.mes_periodo, t.anio_periodo;

-- Tabla grados asignados a docentes
CREATE TABLE IF NOT EXISTS usuario_grados (
    id          INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    id_usuario  INT UNSIGNED NOT NULL,
    id_grado    INT UNSIGNED NOT NULL,
    UNIQUE KEY uq_usr_grado (id_usuario, id_grado),
    CONSTRAINT fk_ug_usr   FOREIGN KEY (id_usuario) REFERENCES usuarios(id_usuario) ON DELETE CASCADE,
    CONSTRAINT fk_ug_grado FOREIGN KEY (id_grado)   REFERENCES grados(id_grado)    ON DELETE CASCADE
);
