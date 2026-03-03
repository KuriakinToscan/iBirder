from PySide6.QtCore import QThread, Signal
try:
    import requests
except ImportError:
    requests = None
import logging
import math
import re

def haversine_distance(lat1, lon1, lat2, lon2):
    """Calcula a distância entre dois pontos na Terra em km."""
    if lat1 is None or lon1 is None or lat2 is None or lon2 is None:
        return float('inf')
    R = 6371.0 # Raio da terra em km
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    return R * c

TRADUCOES_TIPO = {
    'song': 'Canto',
    'call': 'Chamado',
    'begging call': 'Pio de filhote',
    'flight call': 'Chamado em voo',
    'alarm call': 'Alarme',
}

TRADUCOES_LICENCA = {
    'cc-by': 'CC BY',
    'cc-by-nc': 'CC BY-NC',
    'cc-by-nd': 'CC BY-ND',
    'cc-by-sa': 'CC BY-SA',
    'cc-by-nc-nd': 'CC BY-NC-ND',
    'cc-by-nc-sa': 'CC BY-NC-SA',
    'cc0': 'CC0 (Domínio Público)',
    'pd': 'Domínio Público',
}

MAPA_ESTADOS = {
    "ac": "acre", "al": "alagoas", "ap": "amapá", "am": "amazonas", "ba": "bahia",
    "ce": "ceará", "df": "distrito federal", "es": "espírito santo", "go": "goiás",
    "ma": "maranhão", "mt": "mato grosso", "ms": "mato grosso do sul", "mg": "minas gerais",
    "pa": "pará", "pb": "paraíba", "pr": "paraná", "pe": "pernambuco", "pi": "piauí",
    "rj": "rio de janeiro", "rn": "rio grande do norte", "rs": "rio grande do sul",
    "ro": "rondônia", "rr": "roraima", "sc": "santa catarina", "sp": "são paulo",
    "se": "sergipe", "to": "tocantins"
}

class AudioWorker(QThread):
    """
    Worker para realizar a busca de áudios de aves.
    Estratégia:
    1. iNaturalist (Fonte única de áudio v0.8.2)
    """
    audio_found = Signal(list)
    search_failed = Signal()

    def __init__(self, scientific_name, lat=None, lon=None, municipio=None, estado=None, bioma=None, pais=None, parent=None):
        super().__init__(parent)
        self.scientific_name = scientific_name
        self.lat = lat
        self.lon = lon
        self.municipio = municipio
        self.estado = estado
        self.bioma = bioma
        self.pais = pais or 'Brazil'

    def run(self):
        logging.info(f"Iniciando busca de vocalizações para {self.scientific_name}")
        if not self.scientific_name or "Inconclusiva" in self.scientific_name:
            logging.warning(f"Busca de áudio abortada: Nome '{self.scientific_name}' inválido.")
            self.search_failed.emit()
            return

        if not requests:
            self.search_failed.emit()
            return

        try:
            # 1. Busca exclusivamente no iNaturalist (v0.8.2)
            inat_results = self._search_inaturalist()
            
            all_audios = inat_results
            
            # 2. Classificação em Camadas Concêntricas
            for audio in all_audios:
                audio['camada'] = self._calcular_camada_geografica(audio)
            
            # 3. Ordenação: Camada (ASC) > Qualidade (DESC) > Distância (ASC)
            all_audios.sort(key=lambda x: (x['camada'], -x.get('q_score', 0), x.get('distancia', float('inf'))))
            
            # 4. Limite de 3 resultados (Seleção da melhor qualidade por camada disponível)
            final_results = []
            for i, audio in enumerate(all_audios[:3]):
                raw = audio.get('raw', {}) or {}
                audio['posicao_ranking'] = i + 1
                audio['audit_geo'] = str(raw.get('place_guess') or 'Desconhecido')
                audio['distancia_km'] = round(audio.get('distancia', 0), 2) if audio.get('distancia') else 0
                
                # Garantir sanitização de URL (Protocolo Seguro)
                if audio['url'] and audio['url'].startswith('//'):
                    audio['url'] = 'https:' + audio['url']
                if audio.get('link_audio') and audio['link_audio'].startswith('//'):
                    audio['link_audio'] = 'https:' + audio['link_audio']

                final_results.append(audio)
            
            if final_results:
                logging.debug(f"Busca iNaturalist concluída. {len(final_results)} sons selecionados.")
                self.audio_found.emit(final_results)
            else:
                self.search_failed.emit()

        except Exception as e:
            logging.error(f"Erro no AudioWorker: {e}", exc_info=True)
            self.search_failed.emit()

    def _calcular_camada_geografica(self, audio):
        """Atribui uma camada de 0 (perto) a 4 (longe) baseada na localidade."""
        raw = audio.get('raw', {}) or {}
        rec_loc = str(raw.get('place_guess') or '').lower()
        
        # Heurística para Brasil
        rec_country = 'brazil' if any(x in rec_loc for x in ['brazil', 'brasil', ', br', ' br ']) else 'global'
        
        rec_uf = None
        if self.estado:
            uf_alvo = self.estado.lower()
            sigla_alvo = next((s for s, n in MAPA_ESTADOS.items() if n == uf_alvo), None)
            if uf_alvo in rec_loc or (sigla_alvo and re.search(rf'\b{sigla_alvo}\b', rec_loc)):
                rec_uf = uf_alvo
        
        if self.municipio and self.municipio.lower() in rec_loc: return 0
        if rec_uf: return 1
        if audio.get('distancia', 9999) < 150: return 2
        if rec_country == 'brazil': return 3
        return 4

    def _search_inaturalist(self):
        """Busca observações com sons no iNaturalist (v0.8.2)."""
        try:
            url = "https://api.inaturalist.org/v1/observations"
            params = {
                'taxon_name': self.scientific_name,
                'sounds': 'true',
                'per_page': 100,
                'order_by': 'votes'
            }
            headers = {"User-Agent": "iBirder/1.0 (Windows NT 10.0; Win64; x64)"}
            resp = requests.get(url, params=params, headers=headers, timeout=10)
            if resp.status_code != 200: return []
                 
            data = resp.json()
            audios = []
            for obs in data.get('results', []):
                obs_lat, obs_lon = None, None
                if loc := obs.get('location'):
                    try:
                        coords = loc.split(',')
                        obs_lat, obs_lon = float(coords[0]), float(coords[1])
                    except: pass

                for sound in obs.get('sounds', []):
                    if file_url := sound.get('file_url'):
                        votos = obs.get('faves_count', 0)
                        social_q = 4 if votos >= 3 else 2
                        
                        licenca_raw = sound.get('license_code') or obs.get('license_code') or 'copyright'
                        licenca = TRADUCOES_LICENCA.get(str(licenca_raw).lower(), "Direitos reservados")
                        if licenca == "Direitos reservados" and licenca_raw != 'copyright':
                             licenca = f"Alguns direitos reservados ({str(licenca_raw).upper()})"
                        elif licenca == "Direitos reservados":
                             licenca = "Todos os direitos reservados"

                        audios.append({
                            'url': file_url,
                            'link_audio': file_url,
                            'link_observacao': f"https://www.inaturalist.org/observations/{obs.get('id')}",
                            'id_original': obs.get('id'),
                            'autor': obs.get('user', {}).get('name') or obs.get('user', {}).get('login', 'Desconhecido'),
                            'licenca': licenca,
                            'fonte': 'iNaturalist',
                            'data': obs.get('observed_on_string', 'Desconhecida'),
                            'comentarios': obs.get('description', ''),
                            'link_web': f"https://www.inaturalist.org/observations/{obs.get('id')}",
                            'id': str(obs.get('id')), # Garantir ID como string
                            'lat': obs_lat,
                            'lon': obs_lon,
                            'distancia': haversine_distance(self.lat, self.lon, obs_lat, obs_lon) if self.lat else float('inf'),
                            'q': f"⭐ {votos}",
                            'q_score': social_q,
                            'raw': obs
                        })
                        break
            return audios
        except: return []
