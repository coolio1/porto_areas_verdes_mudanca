-- Base de Dados de Atropelamentos de Peões e Ciclistas - Grande Porto
-- Desde 1 de Janeiro de 2000

CREATE TABLE IF NOT EXISTS acidentes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    -- Cronologia
    data DATE NOT NULL,                    -- Data da ocorrência (YYYY-MM-DD)
    hora TIME,                             -- Hora da ocorrência (HH:MM)
    dia_semana TEXT,                        -- Dia da semana

    -- Localização geoespacial
    latitude REAL,                          -- Coordenada GPS
    longitude REAL,                         -- Coordenada GPS
    morada TEXT,                            -- Arruamento / endereço
    intersecao TEXT,                        -- Intersecção (se aplicável)
    freguesia TEXT,                         -- Freguesia
    concelho TEXT NOT NULL,                 -- Município (Porto, Matosinhos, V.N. Gaia, etc.)
    distrito TEXT DEFAULT 'Porto',          -- Distrito

    -- Tipologia do sinistro
    tipo_sinistro TEXT NOT NULL,            -- 'atropelamento_peao', 'atropelamento_ciclista', 'colisao_ciclista'

    -- Tipologia de intervenientes - Vítima
    tipo_vitima TEXT NOT NULL,              -- 'peao', 'ciclista'
    idade_vitima INTEGER,                   -- Idade da vítima
    sexo_vitima TEXT,                       -- 'M', 'F'

    -- Tipologia de intervenientes - Veículo
    tipo_veiculo TEXT,                      -- 'ligeiro_passageiros', 'pesado_mercadorias', 'motociclo', 'autocarro', 'bicicleta', 'trotinete', 'outro'

    -- Gravidade (classificação ANSR)
    gravidade TEXT NOT NULL,                -- 'mortal' (30 dias), 'ferido_grave', 'ferido_leve', 'ileso'
    num_vitimas_mortais INTEGER DEFAULT 0,
    num_feridos_graves INTEGER DEFAULT 0,
    num_feridos_leves INTEGER DEFAULT 0,

    -- Condições
    condicoes_meteorologicas TEXT,          -- 'bom_tempo', 'chuva', 'nevoeiro', 'vento_forte'
    luminosidade TEXT,                      -- 'dia', 'noite_com_iluminacao', 'noite_sem_iluminacao', 'aurora_crepusculo'
    tipo_via TEXT,                          -- 'arruamento', 'estrada_nacional', 'autoestrada', 'estrada_municipal'

    -- Metadados
    fonte TEXT NOT NULL,                    -- 'ansr', 'noticia', 'inquerido', 'cm_porto', 'outro'
    url_fonte TEXT,                         -- Link para a fonte original
    confianca_geolocalizacao TEXT,          -- 'exata' (GPS), 'aproximada' (geocodificada), 'concelho_apenas'
    notas TEXT,                             -- Observações adicionais

    data_registo TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Índices para consultas comuns
CREATE INDEX idx_data ON acidentes(data);
CREATE INDEX idx_concelho ON acidentes(concelho);
CREATE INDEX idx_tipo_vitima ON acidentes(tipo_vitima);
CREATE INDEX idx_gravidade ON acidentes(gravidade);
CREATE INDEX idx_coords ON acidentes(latitude, longitude);
CREATE INDEX idx_tipo_sinistro ON acidentes(tipo_sinistro);

-- Vista para estatísticas anuais
CREATE VIEW IF NOT EXISTS estatisticas_anuais AS
SELECT
    strftime('%Y', data) AS ano,
    concelho,
    tipo_vitima,
    COUNT(*) AS total_acidentes,
    SUM(num_vitimas_mortais) AS total_mortais,
    SUM(num_feridos_graves) AS total_feridos_graves,
    SUM(num_feridos_leves) AS total_feridos_leves
FROM acidentes
GROUP BY ano, concelho, tipo_vitima
ORDER BY ano DESC, concelho;

-- Vista para hotspots (requer coordenadas)
CREATE VIEW IF NOT EXISTS hotspots AS
SELECT
    ROUND(latitude, 3) AS lat_zona,
    ROUND(longitude, 3) AS lon_zona,
    concelho,
    COUNT(*) AS total_acidentes,
    SUM(num_vitimas_mortais) AS total_mortais,
    SUM(num_feridos_graves) AS total_feridos_graves
FROM acidentes
WHERE latitude IS NOT NULL AND longitude IS NOT NULL
GROUP BY lat_zona, lon_zona, concelho
HAVING total_acidentes >= 3
ORDER BY total_acidentes DESC;
