"""
Mapa interactivo e dashboard de atropelamentos - Grande Porto
Gera um ficheiro HTML com mapa Leaflet + gráficos integrados
"""

import sqlite3
import json
import csv
from pathlib import Path

DB_PATH = Path(__file__).parent / "atropelamentos_grande_porto.db"
COORDS_PATH = Path(__file__).parent / "coordenadas_acidentes.csv"
AGREGADOS_PATH = Path(__file__).parent / "dados_agregados_ansr.json"
OUTPUT_HTML = Path(__file__).parent / "dashboard_atropelamentos.html"


def carregar_casos():
    """Carrega casos individuais da BD com coordenadas."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    rows = conn.execute("""
        SELECT * FROM acidentes
        WHERE latitude IS NOT NULL AND longitude IS NOT NULL
        ORDER BY data DESC
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def carregar_agregados():
    """Carrega dados agregados ANSR."""
    with open(AGREGADOS_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)


def gerar_html(casos, agregados):
    """Gera o dashboard HTML completo."""

    # Preparar dados para JavaScript
    markers_js = []
    for c in casos:
        color = 'red' if c['gravidade'] == 'mortal' else 'orange' if c['gravidade'] == 'ferido_grave' else 'blue'
        icon = 'person-walking' if c['tipo_vitima'] == 'peao' else 'bicycle'

        popup = f"""
            <b>{c['data']}</b><br>
            <b>{c['morada'] or 'Localização GPS'}</b>, {c['concelho']}<br>
            Vítima: {c['tipo_vitima'].replace('peao', 'Peão').replace('ciclista', 'Ciclista')}<br>
            Gravidade: <span style='color:{color};font-weight:bold'>{c['gravidade'].replace('_',' ').title()}</span><br>
            Veículo: {(c['tipo_veiculo'] or '').replace('_', ' ').title()}<br>
            {'Idade: ' + str(c['idade_vitima']) if c['idade_vitima'] else ''}
            {'| Sexo: ' + c['sexo_vitima'] if c['sexo_vitima'] else ''}<br>
            <small>{(c['notas'] or '')[:200]}</small><br>
            <a href='{c['url_fonte'] or '#'}' target='_blank'>Fonte</a>
        """.replace('\n', ' ').replace("'", "\\'")

        markers_js.append(f"""
            L.circleMarker([{c['latitude']}, {c['longitude']}], {{
                radius: {'10' if c['gravidade'] == 'mortal' else '7' if c['gravidade'] == 'ferido_grave' else '5'},
                fillColor: '{color}',
                color: '#333',
                weight: 1,
                opacity: 1,
                fillOpacity: 0.8
            }}).addTo(map).bindPopup('{popup}');
        """)

    # Dados para gráficos
    peoes = agregados['distrito_porto']['peoes_vitimas']['dados']
    geral = agregados['distrito_porto']['sinistralidade_geral']['dados']
    ciclistas = agregados['nacional']['ciclistas_vitimas']['dados']

    # Contar por concelho e gravidade
    concelho_counts = {}
    for c in casos:
        key = c['concelho']
        if key not in concelho_counts:
            concelho_counts[key] = {'mortal': 0, 'ferido_grave': 0, 'ferido_leve': 0}
        concelho_counts[key][c['gravidade']] += 1

    html = f"""<!DOCTYPE html>
<html lang="pt">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Atropelamentos no Grande Porto — Dashboard</title>
    <meta name="description" content="Dashboard de sinistralidade rodoviária com peões e ciclistas no Grande Porto, com dados ANSR e notícias geolocalizadas.">
    <link rel="canonical" href="https://coolio1.github.io/porto_areas_verdes_mudanca/atropelamentos/dashboard_atropelamentos.html">
    <meta property="og:title" content="Atropelamentos no Grande Porto — Dashboard">
    <meta property="og:description" content="Dashboard de sinistralidade rodoviária com peões e ciclistas no Grande Porto.">
    <meta property="og:url" content="https://coolio1.github.io/porto_areas_verdes_mudanca/atropelamentos/dashboard_atropelamentos.html">
    <meta property="og:type" content="website">
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: 'Segoe UI', system-ui, sans-serif; background: #0f172a; color: #e2e8f0; }}

        .header {{
            background: linear-gradient(135deg, #1e293b, #334155);
            padding: 24px 32px;
            border-bottom: 3px solid #ef4444;
        }}
        .header h1 {{ font-size: 1.8rem; color: #f8fafc; }}
        .header p {{ color: #94a3b8; margin-top: 4px; font-size: 0.95rem; }}

        .stats-row {{
            display: flex;
            flex-wrap: wrap;
            justify-content: center;
            gap: 10px;
            padding: 16px 32px;
        }}
        .stat-card {{
            background: #1e293b;
            border-radius: 10px;
            padding: 12px 16px;
            border-left: 3px solid #3b82f6;
            min-width: 130px;
        }}
        .stat-card.danger {{ border-left-color: #ef4444; }}
        .stat-card.warning {{ border-left-color: #f59e0b; }}
        .stat-card.info {{ border-left-color: #06b6d4; }}
        .stat-card .number {{ font-size: 1.6rem; font-weight: 700; color: #f8fafc; }}
        .stat-card .label {{ font-size: 0.8rem; color: #94a3b8; margin-top: 2px; }}
        .stat-card .sublabel {{ font-size: 0.7rem; color: #64748b; }}

        .content {{ padding: 0 32px 32px; }}

        .map-container {{
            border-radius: 12px;
            overflow: hidden;
            margin-bottom: 24px;
            border: 1px solid #334155;
        }}
        #map {{ height: 500px; width: 100%; }}

        .legend {{
            background: rgba(15, 23, 42, 0.9);
            padding: 12px 16px;
            border-radius: 8px;
            line-height: 1.8;
            color: #e2e8f0;
            font-size: 0.85rem;
        }}
        .legend i {{
            width: 14px; height: 14px;
            display: inline-block;
            border-radius: 50%;
            margin-right: 6px;
            vertical-align: middle;
        }}

        .charts-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
            gap: 24px;
            margin-bottom: 24px;
        }}
        .chart-card {{
            background: #1e293b;
            border-radius: 12px;
            padding: 24px;
        }}
        .chart-card h3 {{
            font-size: 1rem;
            color: #94a3b8;
            margin-bottom: 16px;
            font-weight: 500;
        }}

        .table-card {{
            background: #1e293b;
            border-radius: 12px;
            padding: 24px;
            overflow-x: auto;
            margin-bottom: 24px;
        }}
        .table-card h3 {{
            font-size: 1rem; color: #94a3b8; margin-bottom: 16px; font-weight: 500;
        }}
        table {{ width: 100%; border-collapse: collapse; font-size: 0.85rem; }}
        th {{ text-align: left; padding: 10px 12px; color: #64748b; border-bottom: 1px solid #334155; font-weight: 500; }}
        td {{ padding: 10px 12px; border-bottom: 1px solid #1e293b; }}
        tr:hover td {{ background: #334155; }}
        .badge {{
            display: inline-block; padding: 2px 8px; border-radius: 9999px; font-size: 0.75rem; font-weight: 600;
        }}
        .badge-red {{ background: #450a0a; color: #fca5a5; }}
        .badge-orange {{ background: #451a03; color: #fdba74; }}
        .badge-blue {{ background: #0c1e3a; color: #93c5fd; }}

        .footer {{
            text-align: center; padding: 24px; color: #475569; font-size: 0.8rem;
            border-top: 1px solid #1e293b;
        }}
        .footer a {{ color: #3b82f6; text-decoration: none; }}

        .note-box {{
            background: #1e293b; border-left: 4px solid #f59e0b; border-radius: 8px;
            padding: 16px 20px; margin-bottom: 24px; font-size: 0.9rem; color: #94a3b8;
        }}
        .note-box strong {{ color: #f59e0b; }}
    </style>
</head>
<body>

<div class="header">
    <h1>Atropelamentos de Peões e Ciclistas — Grande Porto</h1>
    <p>Base de dados de sinistralidade rodoviária | Fontes: ANSR, INE, notícias</p>
</div>

<div class="stats-row">
    <div class="stat-card danger">
        <div class="number">~1090</div>
        <div class="label">Peões vítimas/ano</div>
        <div class="sublabel">Distrito do Porto, 2024 (ANSR)</div>
    </div>
    <div class="stat-card danger">
        <div class="number">20</div>
        <div class="label">Vítimas mortais (peões)</div>
        <div class="sublabel">Distrito do Porto, 2024</div>
    </div>
    <div class="stat-card warning">
        <div class="number">37</div>
        <div class="label">Feridos graves (peões)</div>
        <div class="sublabel">Distrito do Porto, 2024</div>
    </div>
    <div class="stat-card info">
        <div class="number">1033</div>
        <div class="label">Feridos leves (peões)</div>
        <div class="sublabel">Distrito do Porto, 2024</div>
    </div>
    <div class="stat-card">
        <div class="number">6384</div>
        <div class="label">Acidentes com vítimas (total)</div>
        <div class="sublabel">Distrito do Porto, 2024</div>
    </div>
</div>

<div class="content">

    <div class="map-container">
        <div id="map"></div>
    </div>

    <div class="note-box">
        <strong>Nota:</strong> O mapa mostra {len(casos)} casos individuais recolhidos de notícias (2017-2026).
        Estes representam &lt;2% do total real — a maioria dos ~1090 atropelamentos anuais não é noticiada.
        Dados georreferenciados completos requerem protocolo com a ANSR.
    </div>

    <div class="charts-grid">
        <div class="chart-card" style="grid-column: 1 / -1;">
            <h3>Mortes de peões por 100 000 habitantes — comparação internacional (2022)</h3>
            <canvas id="chartInternacional" style="min-height:300px"></canvas>
        </div>
    </div>

    <div class="table-card">
        <h3>Casos individuais registados ({len(casos)} ocorrências)</h3>
        <table>
            <thead>
                <tr>
                    <th>Data</th>
                    <th>Local</th>
                    <th>Concelho</th>
                    <th>Vítima</th>
                    <th>Gravidade</th>
                    <th>Veículo</th>
                    <th>Idade</th>
                    <th>Fonte</th>
                </tr>
            </thead>
            <tbody>
                {''.join(f"""<tr>
                    <td>{c['data']}</td>
                    <td>{(c['morada'] or '')[:45]}</td>
                    <td>{c['concelho']}</td>
                    <td>{c['tipo_vitima'].replace('peao', 'Peão').replace('ciclista', 'Ciclista')}</td>
                    <td><span class="badge {'badge-red' if c['gravidade']=='mortal' else 'badge-orange' if c['gravidade']=='ferido_grave' else 'badge-blue'}">{c['gravidade'].replace('_',' ')}</span></td>
                    <td>{(c['tipo_veiculo'] or '').replace('_',' ')}</td>
                    <td>{c['idade_vitima'] or '-'}</td>
                    <td><a href="{c['url_fonte'] or '#'}" target="_blank" style="color:#3b82f6">link</a></td>
                </tr>""" for c in casos)}
            </tbody>
        </table>
    </div>

    <div class="table-card">
        <h3>Dados agregados ANSR — Peões vítimas (Distrito do Porto)</h3>
        <table>
            <thead><tr><th>Ano</th><th>Vítimas Mortais</th><th>Feridos Graves</th><th>Feridos Leves</th><th>Total</th></tr></thead>
            <tbody>
                {''.join(f"""<tr>
                    <td><b>{p['ano']}</b></td>
                    <td style="color:#fca5a5">{p['vitimas_mortais']}</td>
                    <td style="color:#fdba74">{p['feridos_graves']}</td>
                    <td>{p['feridos_leves']}</td>
                    <td><b>{p['vitimas_mortais']+p['feridos_graves']+p['feridos_leves']}</b></td>
                </tr>""" for p in peoes)}
            </tbody>
        </table>
    </div>

</div>

<div class="footer">
    <p>Dados compilados a partir de fontes públicas (ANSR, INE, notícias) | Actualizado: Março 2026</p>
    <p>Para dados completos georreferenciados: estabelecer protocolo com a <a href="https://www.ansr.pt">ANSR</a></p>
    <p>Projecto para redução de mortes e acidentes com peões e ciclistas no Grande Porto</p>
</div>

<script>
    // === MAPA ===
    var map = L.map('map').setView([41.16, -8.63], 12);
    L.tileLayer('https://{{s}}.basemaps.cartocdn.com/light_all/{{z}}/{{x}}/{{y}}{{r}}.png', {{
        attribution: '&copy; OpenStreetMap &copy; CARTO',
        maxZoom: 19
    }}).addTo(map);

    // Markers
    {''.join(markers_js)}

    // Legend
    var legend = L.control({{position: 'bottomright'}});
    legend.onAdd = function(map) {{
        var div = L.DomUtil.create('div', 'legend');
        div.style.background = 'rgba(255,255,255,0.92)';
        div.style.color = '#1e293b';
        div.innerHTML = '<b>Gravidade</b><br>' +
            '<i style="background:#ef4444"></i> Mortal<br>' +
            '<i style="background:#f59e0b"></i> Ferido grave<br>' +
            '<i style="background:#3b82f6"></i> Ferido leve';
        return div;
    }};
    legend.addTo(map);

    // === GRAFICOS ===
    var chartColors = {{
        red: '#ef4444', orange: '#f59e0b', blue: '#3b82f6', cyan: '#06b6d4',
        grid: '#334155', text: '#94a3b8'
    }};
    var defaultOptions = {{
        responsive: true,
        plugins: {{ legend: {{ labels: {{ color: chartColors.text }} }} }},
        scales: {{
            x: {{ ticks: {{ color: chartColors.text }}, grid: {{ color: chartColors.grid }} }},
            y: {{ ticks: {{ color: chartColors.text }}, grid: {{ color: chartColors.grid }} }}
        }}
    }};

    // Comparação internacional — mortes de peões por 100 000 hab. (cidades)
    // Fontes: TfL 2022, NYC DOT 2022, ANSR 2024, ITF/OECD Safer City Streets, CSE India, PMC11329493
    var intlData = [
        {{ city: 'Deli',          rate: 5.5,  color: '#64748b' }},
        {{ city: 'Bogotá',        rate: 3.8,  color: '#64748b' }},
        {{ city: 'São Paulo',     rate: 2.7,  color: '#64748b' }},
        {{ city: 'Porto',         rate: 1.18, color: '#ef4444' }},
        {{ city: 'Nova Iorque',   rate: 1.13, color: '#64748b' }},
        {{ city: 'Lisboa',        rate: 0.95, color: '#f59e0b' }},
        {{ city: 'Paris',         rate: 0.70, color: '#64748b' }},
        {{ city: 'Londres',       rate: 0.67, color: '#64748b' }},
        {{ city: 'Berlim',        rate: 0.50, color: '#64748b' }},
        {{ city: 'Tóquio',        rate: 0.50, color: '#64748b' }},
        {{ city: 'Estocolmo',     rate: 0.24, color: '#64748b' }},
        {{ city: 'Oslo',          rate: 0.15, color: '#22c55e' }}
    ];

    new Chart(document.getElementById('chartInternacional'), {{
        type: 'bar',
        data: {{
            labels: intlData.map(d => d.city),
            datasets: [{{
                label: 'Mortes de peões / 100 000 hab.',
                data: intlData.map(d => d.rate),
                backgroundColor: intlData.map(d => d.color),
                borderColor: intlData.map(d => (d.city === 'Porto' || d.city === 'Lisboa') ? '#fff' : 'transparent'),
                borderWidth: intlData.map(d => (d.city === 'Porto' || d.city === 'Lisboa') ? 2 : 0),
                barThickness: 18
            }}]
        }},
        options: {{
            indexAxis: 'y',
            responsive: true,
            maintainAspectRatio: false,
            plugins: {{
                legend: {{ display: false }},
                subtitle: {{ display: true, text: 'Fontes: ANSR 2024, TfL 2022, NYC DOT 2022, ITF/OECD, CSE India, PMC11329493', color: '#64748b', font: {{ size: 10 }}, padding: {{ bottom: 8 }} }},
                tooltip: {{ callbacks: {{ label: function(ctx) {{ return ctx.parsed.x.toFixed(2) + ' mortes / 100 000 hab.'; }} }} }}
            }},
            scales: {{
                x: {{ ticks: {{ color: chartColors.text }}, grid: {{ color: chartColors.grid }}, title: {{ display: true, text: 'Mortes de peões por 100 000 hab./ano', color: chartColors.text, font: {{ size: 11 }} }} }},
                y: {{ ticks: {{ color: function(context) {{ var c = intlData[context.index]?.city; return c === 'Porto' ? '#ef4444' : c === 'Lisboa' ? '#f59e0b' : chartColors.text; }}, font: function(context) {{ var c = intlData[context.index]?.city; return {{ weight: (c === 'Porto' || c === 'Lisboa') ? 'bold' : 'normal', size: 12 }}; }} }}, grid: {{ color: chartColors.grid }} }}
            }}
        }}
    }});

</script>

</body>
</html>"""
    return html


def main():
    print("Gerando dashboard...")
    casos = carregar_casos()
    agregados = carregar_agregados()
    html = gerar_html(casos, agregados)

    with open(OUTPUT_HTML, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f"Dashboard gerado: {OUTPUT_HTML}")
    print(f"  {len(casos)} casos no mapa")
    print(f"  Abrir no browser para visualizar")


if __name__ == "__main__":
    main()
