
import requests
import math
import json
import urllib.parse
import os
import re

# Contexto da Simulação (Rosário do Sul, RS)
SCI_NAME = "Zonotrichia capensis"
LAT = -30.109521666666666
LON = -54.948303333333335
MUNICIPIO = "Rosário do Sul"
ESTADO = "Rio Grande do Sul"

LOG_FILE = "relatorio_detalhado_inaturalist_v0_9_2.md"

MAPA_ESTADOS = {
    "ac": "acre", "al": "alagoas", "ap": "amapá", "am": "amazonas", "ba": "bahia",
    "ce": "ceará", "df": "distrito federal", "es": "espírito santo", "go": "goiás",
    "ma": "maranhão", "mt": "mato grosso", "ms": "mato grosso do sul", "mg": "minas gerais",
    "pa": "pará", "pb": "paraíba", "pr": "paraná", "pe": "pernambuco", "pi": "piauí",
    "rj": "rio de janeiro", "rn": "rio grande do norte", "rs": "rio grande do sul",
    "ro": "rondônia", "rr": "roraima", "sc": "santa cararina", "sp": "são paulo",
    "se": "sergipe", "to": "tocantins"
}

def haversine_distance(lat1, lon1, lat2, lon2):
    if lat1 is None or lon1 is None or lat2 is None or lon2 is None:
        return float('inf')
    R = 6371.0
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    return R * c

def simulate():
    output = []
    output.append(f"# Auditoria Detalhada de Busca iNaturalist v0.9.2\n")
    output.append(f"## Contexto do Usuário")
    output.append(f"- **Espécie**: `{SCI_NAME}`")
    output.append(f"- **Local**: `{MUNICIPIO}, {ESTADO}`")
    output.append(f"- **Coordenadas**: `{LAT}, {LON}`\n")

    # 1. Sintaxe de Busca
    output.append(f"## 1. Sintaxe de Busca (API)")
    url_inat = "https://api.inaturalist.org/v1/observations"
    params_inat = {
        'taxon_name': SCI_NAME,
        'sounds': 'true',
        'per_page': 200, # Limite máximo efetivo do iNaturalist
        'order_by': 'votes'
    }
    output.append(f"A requisição utiliza a API v1 do iNaturalist:")
    output.append(f"```http\nGET {url_inat}?{urllib.parse.urlencode(params_inat)}\n```\n")
    
    # 2. Resultados Brutos
    output.append(f"## 2. Todos os Resultados Retornados (Bruto)")
    inat_raw = []
    try:
        resp = requests.get(url_inat, params=params_inat, timeout=10)
        if resp.status_code == 200:
            inat_data = resp.json()
            inat_raw = inat_data.get('results', [])
            output.append(f"Foram retornados **{len(inat_raw)}** registros da API.\n")
            
            output.append("| ID | Lugar (place_guess) | Latitude | Longitude | Favoritos |")
            output.append("|---|---|---|---|---|")
            for obs in inat_raw:
                loc = obs.get('location', 'N/D')
                place = obs.get('place_guess') or 'Sem Endereço'
                output.append(f"| {obs['id']} | {place[:45]} | {loc.split(',')[0] if ',' in loc else 'N/D'} | {loc.split(',')[1] if ',' in loc else 'N/D'} | {obs.get('faves_count', 0)} |")
        else:
            output.append(f"❌ Erro na API: {resp.status_code}")
            return
    except Exception as e:
        output.append(f"❌ Erro de conexão: {e}")
        return

    # 3. Aplicação do Ranking Concêntrico
    output.append(f"\n## 3. Processamento de Ranking Geográfico")
    output.append("Aplicando lógica de 5 camadas (Mun > UF > 150km > Brasil > Global)...\n")
    
    candidates = []
    for obs in inat_raw:
        place = str(obs.get('place_guess') or '').lower()
        loc = obs.get('location')
        o_lat, o_lon = None, None
        if loc:
            coords = loc.split(',')
            o_lat, o_lon = float(coords[0]), float(coords[1])
        
        dist = haversine_distance(LAT, LON, o_lat, o_lon)
        
        # Inteligência de Siglas v0.9.2
        uf_alvo = ESTADO.lower()
        sigla_alvo = next((s for s, n in MAPA_ESTADOS.items() if n == uf_alvo), None)
        
        detectou_uf = False
        if uf_alvo in place:
            detectou_uf = True
        elif sigla_alvo and re.search(rf'\b{sigla_alvo}\b', place):
            detectou_uf = True

        camada = 4 # Global
        if MUNICIPIO.lower() in place:
            camada = 0
        elif detectou_uf:
            camada = 1
        elif dist < 150:
            camada = 2
        elif any(x in place for x in ['brazil', 'brasil', ', br', ' br ']):
            camada = 3
            
        candidates.append({
            'id': obs['id'],
            'place': place,
            'dist': dist,
            'camada': camada,
            'faves': obs.get('faves_count', 0),
            'url': obs.get('sounds', [{}])[0].get('file_url') if obs.get('sounds') else None
        })

    # Ordenação Final
    candidates.sort(key=lambda x: (x['camada'], -x['faves']))
    
    output.append("| Posição | ID | Distância | Camada Requerida | Motivo | Link Registro |")
    output.append("|---|---|---|---|---|---|")
    for i, c in enumerate(candidates):
        tag = ["MUNICÍPIO", "ESTADO", "BIOMA/REGIONAL", "BRASIL", "GLOBAL"][c['camada']]
        rank_str = f"Top {i+1}" if i < 3 else "Descartado"
        link_obs = f"https://www.inaturalist.org/observations/{c['id']}"
        output.append(f"| {rank_str} | {c['id']} | {c['dist']:.1f}km | **C{c['camada']}** | {tag} | [Ver Rebgistro]({link_obs}) |")

    output.append(f"\n## Conclusão da Simulação")
    if candidates:
        output.append(f"O sistema selecionou **{min(3, len(candidates))}** áudios prioritários.")
        output.append(f"Primeiro áudio: `{candidates[0]['url']}`")
    else:
        output.append("Nenhum áudio válido encontrado após processamento.")

    with open(LOG_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(output))

if __name__ == "__main__":
    simulate()
