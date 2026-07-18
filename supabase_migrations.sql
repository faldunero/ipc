-- Migración Supabase para Predictor IPC

-- Tabla de predicciones
CREATE TABLE ipc_predicciones (
    id BIGSERIAL PRIMARY KEY,
    fecha_prediccion TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    mes_predicho VARCHAR(7),
    ipc_predicho DECIMAL(10, 2),
    ipc_actual DECIMAL(10, 2),
    variacion_esperada DECIMAL(10, 2),
    metodo VARCHAR(50),
    confianza DECIMAL(5, 2),
    notas TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Tabla histórica de IPC
CREATE TABLE ipc_historico (
    id BIGSERIAL PRIMARY KEY,
    mes VARCHAR(7) UNIQUE,
    ipc_index DECIMAL(10, 2),
    variacion_mensual DECIMAL(10, 2),
    variacion_12_meses DECIMAL(10, 2),
    categoria VARCHAR(100),
    fuente VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Tabla de análisis
CREATE TABLE ipc_analisis (
    id BIGSERIAL PRIMARY KEY,
    fecha TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    tendencia TEXT,
    factores TEXT,
    prediccion_groq DECIMAL(10, 2),
    confianza_groq DECIMAL(5, 2),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Índices para performance
CREATE INDEX idx_ipc_predicciones_mes ON ipc_predicciones(mes_predicho);
CREATE INDEX idx_ipc_predicciones_fecha ON ipc_predicciones(fecha_prediccion);
CREATE INDEX idx_ipc_historico_mes ON ipc_historico(mes);
CREATE INDEX idx_ipc_analisis_fecha ON ipc_analisis(fecha);

-- RLS (Row Level Security)
ALTER TABLE ipc_predicciones ENABLE ROW LEVEL SECURITY;
ALTER TABLE ipc_historico ENABLE ROW LEVEL SECURITY;
ALTER TABLE ipc_analisis ENABLE ROW LEVEL SECURITY;

-- Política pública (permitir lectura de todos)
CREATE POLICY "Permitir lectura pública" ON ipc_predicciones
    FOR SELECT USING (true);

CREATE POLICY "Permitir lectura pública" ON ipc_historico
    FOR SELECT USING (true);

CREATE POLICY "Permitir lectura pública" ON ipc_analisis
    FOR SELECT USING (true);
