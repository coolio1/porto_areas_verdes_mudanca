"""
Compilação de dados de atropelamentos de peões e ciclistas - Grande Porto
Fontes: ANSR (relatórios públicos), notícias, INE/PORDATA
"""

import sqlite3
import csv
import os
import json
from pathlib import Path

DB_PATH = Path(__file__).parent / "atropelamentos_grande_porto.db"
CSV_OUTPUT = Path(__file__).parent / "atropelamentos_grande_porto.csv"
SCHEMA_PATH = Path(__file__).parent / "schema.sql"

def criar_bd():
    """Cria a base de dados SQLite com o esquema definido."""
    if DB_PATH.exists():
        DB_PATH.unlink()

    conn = sqlite3.connect(str(DB_PATH))
    with open(SCHEMA_PATH, 'r', encoding='utf-8') as f:
        conn.executescript(f.read())
    return conn


def importar_noticias(conn):
    """Importa casos individuais recolhidos de notícias."""
    csv_path = Path(__file__).parent / "casos_noticias_todos.csv"
    if not csv_path.exists():
        csv_path = Path(__file__).parent / "casos_noticias_porto.csv"
    if not csv_path.exists():
        print("AVISO: casos_noticias_porto.csv não encontrado")
        return 0

    count = 0
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Normalizar tipo de vítima
            tipo_vitima_raw = row.get('tipo_vitima', '').lower()
            if 'ciclist' in tipo_vitima_raw:
                tipo_vitima = 'ciclista'
                tipo_sinistro = 'atropelamento_ciclista'
            elif 'trotinet' in tipo_vitima_raw:
                tipo_vitima = 'ciclista'  # modos suaves
                tipo_sinistro = 'atropelamento_ciclista'
            else:
                tipo_vitima = 'peao'
                tipo_sinistro = 'atropelamento_peao'

            # Normalizar gravidade
            sev = row.get('severidade', '').lower()
            if 'fatal' in sev or 'mort' in sev:
                gravidade = 'mortal'
                vm, fg, fl = 1, 0, 0
            elif 'grave' in sev:
                gravidade = 'ferido_grave'
                vm, fg, fl = 0, 1, 0
            elif 'leve' in sev or 'ligeiro' in sev:
                gravidade = 'ferido_leve'
                vm, fg, fl = 0, 0, 1
            else:
                gravidade = 'ferido_leve'
                vm, fg, fl = 0, 0, 1

            # Normalizar sexo
            sexo_raw = row.get('genero_vitima', '').lower()
            sexo = None
            if 'masculin' in sexo_raw:
                sexo = 'M'
            elif 'feminin' in sexo_raw:
                sexo = 'F'

            # Extrair idade (primeiro número encontrado)
            idade = None
            idade_raw = row.get('idade_vitima', '')
            if idade_raw:
                import re
                nums = re.findall(r'\d+', str(idade_raw))
                if nums:
                    idade = int(nums[0])

            # Normalizar veículo
            veiculo_raw = row.get('veiculo_envolvido', '').lower()
            if 'metro' in veiculo_raw:
                tipo_veiculo = 'metro'
            elif 'comboio' in veiculo_raw or 'trem' in veiculo_raw:
                tipo_veiculo = 'comboio'
            elif 'autocarro' in veiculo_raw or 'stcp' in veiculo_raw or 'bus' in veiculo_raw:
                tipo_veiculo = 'autocarro'
            elif 'pesado' in veiculo_raw or 'camião' in veiculo_raw or 'camiao' in veiculo_raw:
                tipo_veiculo = 'pesado_mercadorias'
            elif 'automóvel' in veiculo_raw or 'automovel' in veiculo_raw or 'carro' in veiculo_raw or 'ligeiro' in veiculo_raw:
                tipo_veiculo = 'ligeiro_passageiros'
            else:
                tipo_veiculo = 'outro'

            # Data - pode ter formatos variados
            data = row.get('data', '')
            if len(data) == 7:  # YYYY-MM
                data = data + '-01'  # aproximar ao primeiro dia do mês

            conn.execute("""
                INSERT INTO acidentes (
                    data, concelho, freguesia, morada,
                    tipo_sinistro, tipo_vitima, idade_vitima, sexo_vitima,
                    tipo_veiculo, gravidade,
                    num_vitimas_mortais, num_feridos_graves, num_feridos_leves,
                    fonte, url_fonte, confianca_geolocalizacao, notas
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                data,
                row.get('municipio', ''),
                row.get('freguesia_zona', ''),
                row.get('localizacao', ''),
                tipo_sinistro,
                tipo_vitima,
                idade,
                sexo,
                tipo_veiculo,
                gravidade,
                vm, fg, fl,
                'noticia',
                row.get('fonte', ''),
                'aproximada',
                row.get('circunstancias', '')
            ))
            count += 1

    conn.commit()
    print(f"Importados {count} casos de notícias")
    return count


def importar_dados_agregados_ansr(conn):
    """
    Importa dados agregados da ANSR para o distrito do Porto.
    Estes são registos resumo (não individuais) mas dão o contexto estatístico.
    """
    # Dados extraídos dos relatórios ANSR Excel (Anexo_Relatorio_Anual)
    # Fonte: Quadro 4.10 - Peões vítimas por distrito (Porto)
    # e Quadro 1.10 - Sinistralidade por distrito (Porto)

    dados_peoes_porto = [
        # (ano, VM, FG, FL) - Peões vítimas no distrito do Porto
        (2019, 26, 43, 1093),
        (2023, 16, 47, 1028),
        (2024, 20, 37, 1033),
    ]

    # Dados nacionais de atropelamentos (Quadro 1.6)
    dados_atropelamentos_nacional = [
        # (ano, AcV, VM, FG, FL)
        (2019, 5565, 134, 427, 5513),
        (2023, 4873, 106, 346, 4787),
        (2024, 5073, 107, 404, 5030),
    ]

    # Dados nacionais de velocípede/ciclista (Quadro 6.13 - condutores vítimas)
    dados_ciclistas_nacional = [
        # (ano, VM, FG, FL)
        (2019, 27, 97, 1644),
        (2023, 32, 180, 2946),
        (2024, 30, 167, 3323),
    ]

    # Sinistralidade geral distrito do Porto (Quadro 1.10)
    dados_geral_porto = [
        # (ano, AcV, VM, FG, FL)
        (2019, 6245, 79, 205, 7738),
        (2023, 6107, 61, 216, 7261),
        (2024, 6384, 76, 218, 7609),
    ]

    # Evolução peões nacional (Quadro 4.2) - para contexto temporal completo
    dados_peoes_nacional = [
        # (ano, VM, FG, FL)
        (2019, 140, 450, 5391),
        (2020, 101, 291, 3484),
        (2021, 100, 306, 3717),
        (2022, 109, 350, 4302),
        (2023, 109, 350, 4648),
        (2024, 111, 426, 4847),
    ]

    # Guardar como ficheiro de referência
    resumo = {
        "fonte": "ANSR - Relatório Anual de Sinistralidade Rodoviária a 30 dias",
        "ficheiros": [
            "Anexo_Relatorio_Anual_2024_30dias.xlsx",
            "Anexo_Relatorio_Anual_2023_30dias.xlsx",
            "Anexo_Relatorio_Anual_2024_24h.xlsx",
            "Anexo_Relatorio_Mensal_Set2025.xlsx"
        ],
        "distrito_porto": {
            "peoes_vitimas": {
                "descricao": "Quadro 4.10 - Peões vítimas por distrito",
                "dados": [{"ano": a, "vitimas_mortais": v, "feridos_graves": f, "feridos_leves": l}
                         for a, v, f, l in dados_peoes_porto]
            },
            "sinistralidade_geral": {
                "descricao": "Quadro 1.10 - Sinistralidade por distrito",
                "dados": [{"ano": a, "acidentes_com_vitimas": ac, "vitimas_mortais": v, "feridos_graves": f, "feridos_leves": l}
                         for a, ac, v, f, l in dados_geral_porto]
            }
        },
        "nacional": {
            "atropelamentos": {
                "descricao": "Quadro 1.6 - Sinistralidade por natureza (atropelamento)",
                "dados": [{"ano": a, "acidentes": ac, "vitimas_mortais": v, "feridos_graves": f, "feridos_leves": l}
                         for a, ac, v, f, l in dados_atropelamentos_nacional]
            },
            "ciclistas_vitimas": {
                "descricao": "Quadro 6.13 - Condutores vítimas por categoria (velocípede)",
                "dados": [{"ano": a, "vitimas_mortais": v, "feridos_graves": f, "feridos_leves": l}
                         for a, v, f, l in dados_ciclistas_nacional]
            },
            "peoes_evolucao": {
                "descricao": "Quadro 4.2 - Evolução peões vítimas (nacional)",
                "dados": [{"ano": a, "vitimas_mortais": v, "feridos_graves": f, "feridos_leves": l}
                         for a, v, f, l in dados_peoes_nacional]
            }
        },
        "notas": [
            "VM = Vítimas Mortais (a 30 dias), FG = Feridos Graves, FL = Feridos Leves",
            "AcV = Acidentes com Vítimas",
            "Ciclistas classificados como 'condutores de velocípede' pela ANSR",
            "Dados por distrito não distinguem ciclistas - apenas disponível a nível nacional",
            "Para dados georreferenciados e por concelho: necessário protocolo com ANSR"
        ]
    }

    resumo_path = Path(__file__).parent / "dados_agregados_ansr.json"
    with open(resumo_path, 'w', encoding='utf-8') as f:
        json.dump(resumo, f, ensure_ascii=False, indent=2)

    print(f"Dados agregados ANSR guardados em {resumo_path}")
    return resumo


def integrar_coordenadas(conn):
    """Integra coordenadas GPS geocodificadas nos registos existentes."""
    coords_path = Path(__file__).parent / "coordenadas_acidentes.csv"
    if not coords_path.exists():
        print("AVISO: coordenadas_acidentes.csv não encontrado")
        return 0

    count = 0
    with open(coords_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            lat = row.get('latitude', '')
            lon = row.get('longitude', '')
            loc = row.get('localizacao', '')
            conf = row.get('confianca', 'baixa')
            if lat and lon and loc:
                conn.execute("""
                    UPDATE acidentes
                    SET latitude = ?, longitude = ?, confianca_geolocalizacao = ?
                    WHERE morada = ?
                """, (float(lat), float(lon), conf, loc))
                count += 1

    conn.commit()
    geocoded = conn.execute("SELECT COUNT(*) FROM acidentes WHERE latitude IS NOT NULL").fetchone()[0]
    print(f"Coordenadas integradas: {geocoded}/{conn.execute('SELECT COUNT(*) FROM acidentes').fetchone()[0]} registos")
    return count


def importar_noticias_extra(conn):
    """Importa casos extra de notícias (segunda ronda de pesquisa)."""
    csv_path = Path(__file__).parent / "casos_noticias_porto_extra.csv"
    if not csv_path.exists():
        return 0

    count = 0
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            tipo_vitima_raw = row.get('tipo_vitima', '').lower()
            if 'ciclist' in tipo_vitima_raw:
                tipo_vitima = 'ciclista'
                tipo_sinistro = 'atropelamento_ciclista'
            elif 'trotinet' in tipo_vitima_raw:
                tipo_vitima = 'ciclista'
                tipo_sinistro = 'atropelamento_ciclista'
            else:
                tipo_vitima = 'peao'
                tipo_sinistro = 'atropelamento_peao'

            sev = row.get('severidade', '').lower()
            if 'fatal' in sev or 'mort' in sev:
                gravidade = 'mortal'
                vm, fg, fl = 1, 0, 0
            elif 'grave' in sev:
                gravidade = 'ferido_grave'
                vm, fg, fl = 0, 1, 0
            else:
                gravidade = 'ferido_leve'
                vm, fg, fl = 0, 0, 1

            sexo_raw = row.get('genero_vitima', '').lower()
            sexo = None
            if 'masculin' in sexo_raw:
                sexo = 'M'
            elif 'feminin' in sexo_raw:
                sexo = 'F'

            idade = None
            idade_raw = row.get('idade_vitima', '')
            if idade_raw:
                import re
                nums = re.findall(r'\d+', str(idade_raw))
                if nums:
                    idade = int(nums[0])

            veiculo_raw = row.get('veiculo_envolvido', '').lower()
            if 'metro' in veiculo_raw:
                tipo_veiculo = 'metro'
            elif 'comboio' in veiculo_raw or 'trem' in veiculo_raw:
                tipo_veiculo = 'comboio'
            elif 'autocarro' in veiculo_raw or 'stcp' in veiculo_raw:
                tipo_veiculo = 'autocarro'
            elif 'pesado' in veiculo_raw or 'camião' in veiculo_raw:
                tipo_veiculo = 'pesado_mercadorias'
            elif 'automóvel' in veiculo_raw or 'automovel' in veiculo_raw or 'carro' in veiculo_raw or 'ligeiro' in veiculo_raw:
                tipo_veiculo = 'ligeiro_passageiros'
            else:
                tipo_veiculo = 'outro'

            data = row.get('data', '')
            if len(data) == 7:
                data = data + '-01'
            if len(data) == 4:
                data = data + '-01-01'

            conn.execute("""
                INSERT INTO acidentes (
                    data, concelho, freguesia, morada,
                    tipo_sinistro, tipo_vitima, idade_vitima, sexo_vitima,
                    tipo_veiculo, gravidade,
                    num_vitimas_mortais, num_feridos_graves, num_feridos_leves,
                    fonte, url_fonte, confianca_geolocalizacao, notas
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                data,
                row.get('municipio', ''),
                row.get('freguesia_zona', ''),
                row.get('localizacao', ''),
                tipo_sinistro, tipo_vitima, idade, sexo,
                tipo_veiculo, gravidade, vm, fg, fl,
                'noticia',
                row.get('fonte', ''),
                'aproximada',
                row.get('circunstancias', '')
            ))
            count += 1

    conn.commit()
    if count:
        print(f"Importados {count} casos extra de notícias")
    return count


def exportar_csv(conn):
    """Exporta a base de dados para CSV."""
    cursor = conn.execute("SELECT * FROM acidentes ORDER BY data DESC")
    columns = [desc[0] for desc in cursor.description]
    rows = cursor.fetchall()

    with open(CSV_OUTPUT, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(columns)
        writer.writerows(rows)

    print(f"Exportados {len(rows)} registos para {CSV_OUTPUT}")


def imprimir_resumo(conn):
    """Imprime um resumo da base de dados."""
    print("\n" + "="*60)
    print("RESUMO DA BASE DE DADOS")
    print("="*60)

    # Total de registos
    total = conn.execute("SELECT COUNT(*) FROM acidentes").fetchone()[0]
    print(f"\nTotal de registos individuais: {total}")

    # Por tipo de vítima
    print("\nPor tipo de vítima:")
    for row in conn.execute("SELECT tipo_vitima, COUNT(*) FROM acidentes GROUP BY tipo_vitima"):
        print(f"  {row[0]}: {row[1]}")

    # Por gravidade
    print("\nPor gravidade:")
    for row in conn.execute("SELECT gravidade, COUNT(*) FROM acidentes GROUP BY gravidade ORDER BY gravidade"):
        print(f"  {row[0]}: {row[1]}")

    # Por concelho
    print("\nPor concelho:")
    for row in conn.execute("SELECT concelho, COUNT(*) FROM acidentes GROUP BY concelho ORDER BY COUNT(*) DESC"):
        print(f"  {row[0]}: {row[1]}")

    # Mortais
    mortais = conn.execute("SELECT COUNT(*) FROM acidentes WHERE gravidade='mortal'").fetchone()[0]
    print(f"\nTotal de casos mortais registados: {mortais}")

    # Fontes
    print("\nPor fonte:")
    for row in conn.execute("SELECT fonte, COUNT(*) FROM acidentes GROUP BY fonte"):
        print(f"  {row[0]}: {row[1]}")

    print("\n" + "="*60)
    print("DADOS AGREGADOS ANSR - DISTRITO DO PORTO")
    print("="*60)
    print("\nPeões vítimas (Distrito do Porto):")
    print(f"  {'Ano':<6} {'VM':>4} {'FG':>4} {'FL':>6} {'Total':>6}")
    for ano, vm, fg, fl in [(2019,26,43,1093), (2023,16,47,1028), (2024,20,37,1033)]:
        print(f"  {ano:<6} {vm:>4} {fg:>4} {fl:>6} {vm+fg+fl:>6}")

    print("\nSinistralidade geral (Distrito do Porto):")
    print(f"  {'Ano':<6} {'AcV':>6} {'VM':>4} {'FG':>4} {'FL':>6}")
    for ano, acv, vm, fg, fl in [(2019,6245,79,205,7738), (2023,6107,61,216,7261), (2024,6384,76,218,7609)]:
        print(f"  {ano:<6} {acv:>6} {vm:>4} {fg:>4} {fl:>6}")

    print("\nCiclistas vítimas (Nacional - não disponível por distrito):")
    print(f"  {'Ano':<6} {'VM':>4} {'FG':>4} {'FL':>6} {'Total':>6}")
    for ano, vm, fg, fl in [(2019,27,97,1644), (2023,32,180,2946), (2024,30,167,3323)]:
        print(f"  {ano:<6} {vm:>4} {fg:>4} {fl:>6} {vm+fg+fl:>6}")


def main():
    print("Compilando base de dados de atropelamentos - Grande Porto")
    print("-" * 60)

    conn = criar_bd()
    importar_noticias(conn)
    importar_noticias_extra(conn)
    integrar_coordenadas(conn)
    importar_dados_agregados_ansr(conn)
    exportar_csv(conn)
    imprimir_resumo(conn)

    conn.close()
    print(f"\nBase de dados: {DB_PATH}")
    print(f"CSV exportado: {CSV_OUTPUT}")


if __name__ == "__main__":
    main()
