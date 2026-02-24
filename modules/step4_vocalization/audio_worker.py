from PySide6.QtCore import QThread, Signal
try:
    import requests
except ImportError:
    requests = None
import traceback
import math

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

class AudioWorker(QThread):
    """
    Worker híbrido para buscar áudios de aves.
    Estratégia:
    1. Xeno-canto (Hierárquico: Município > Estado > Brasil)
    2. iNaturalist (Fallback Global)
    """
    # Emite lista de dicts: [{'url': str, 'autor': str, 'fonte': str}, ...]
    audio_found = Signal(list)
    search_failed = Signal()

    def __init__(self, scientific_name, lat=None, lon=None, municipio=None, estado=None, parent=None):
        super().__init__(parent)
        self.scientific_name = scientific_name
        self.lat = lat
        self.lon = lon
        self.municipio = municipio
        self.estado = estado

    def run(self):
        # Validação de segurança v0.6.1
        if not self.scientific_name or "Inconclusiva" in self.scientific_name:
            print(f"[AudioWorker] Busca abortada: Nome '{self.scientific_name}' inválido.")
            self.search_failed.emit()
            return

        if not requests:
            self.search_failed.emit()
            return

        results = []
        try:
            # 1. Obter resultados de ambas as fontes (v0.8.7)
            xeno_results = self._search_xeno_canto()
            inat_results = self._search_inaturalist()
            
            # 2. Unificar e Rankear: Qualidade (DESC) > Distância (ASC)
            all_audios = xeno_results + inat_results
            all_audios.sort(key=lambda x: (-x.get('q_score', 0), x.get('distancia', float('inf'))))
            
            # 3. Limitar aos 3 melhores registros conforme solicitado
            final_results = all_audios[:3]
            
            if final_results:
                print(f"[AUDIO] Ranking concluído. {len(final_results)} melhores áudios selecionados (Top Quality > Proximidade).")
                self.audio_found.emit(final_results)
            else:
                self.search_failed.emit()

        except Exception as e:
            print(f"[AUDIO] Erro fatal no worker: {e}")
            traceback.print_exc()
            self.search_failed.emit()

    def _get_xeno_recordings(self, query):
        """Executa a chamada para a API pública do Xeno-canto (Transição API-Free)."""
        import urllib.parse
        
        headers = {"User-Agent": "iBirder-App/1.0"}
        quoted_query = urllib.parse.quote(query)
        # O Xeno-canto permite buscas públicas sem necessidade de chave
        url = f"https://xeno-canto.org/api/3/recordings?query={quoted_query}"
        
        try:
            resp = requests.get(url, headers=headers, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                return data.get('recordings', [])
        except Exception:
            pass
        return []

    def _process_recordings(self, raw_recordings):
        """Processa e normaliza uma lista de gravações brutas."""
        processed = []
        for rec in raw_recordings:
            # Tratar Coordenadas
            str_lat, str_lng = rec.get('lat'), rec.get('lng')
            r_lat, r_lng = None, None
            if str_lat and str_lng and str_lat != "null" and str_lng != "null":
                try:
                    tl, tg = float(str_lat), float(str_lng)
                    if tl != 0.0 and tg != 0.0: r_lat, r_lng = tl, tg
                except ValueError: pass

            # Tipo de Som
            raw_type = str(rec.get('type', '')).lower().strip()
            raw_type = " ".join(raw_type.split())
            primeiro_tipo = [t.strip() for t in raw_type.split(',') if t.strip()]
            main_type = primeiro_tipo[0] if primeiro_tipo else 'unknown'
            
            clean_type = 'other'
            for target in ['song', 'begging call', 'flight call', 'alarm call']:
                if target in main_type:
                    clean_type = target
                    break
            if clean_type == 'other' and 'call' in main_type and 'song' not in main_type:
                clean_type = 'call'

            # Distância (Apenas para exibição)
            dist = haversine_distance(self.lat, self.lon, r_lat, r_lng) if self.lat else float('inf')

            # Pontuação de Qualidade (Xeno-canto: A=5, B=4, C=3, D=2, E=1)
            q_map = {'A': 5, 'B': 4, 'C': 3, 'D': 2, 'E': 1}
            q_score = q_map.get(str(rec.get('q', '')).upper(), 1)

            processed.append({
                'raw': rec,
                'distancia': dist,
                'type': clean_type,
                'q': rec.get('q'),
                'q_score': q_score,
                'lat': r_lat,
                'lon': r_lng,
                'id': rec.get('id'),
                'comentarios': rec.get('remarks', '') or rec.get('notes', '')
            })
        return processed

    def _search_xeno_canto(self):
        """Busca em cascata: Município -> Estado -> Brasil."""
        # Categorias que queremos preencher
        faltantes = ['song', 'call', 'begging call', 'flight call', 'alarm call']
        campeoes = {} # tipo -> dados_formatados

        def preencher_vagas(recordings):
            nonlocal faltantes
            if not recordings or not isinstance(recordings, list): return
            
            # Processa e ordena por qualidade/distância dentro deste lote
            procs = self._process_recordings(recordings)
            # Ordenação interna do lote: A > B... 
            procs.sort(key=lambda x: (str(x['q']).upper(), x['distancia']))

            for item in procs:
                t = item['type']
                if t in faltantes:
                    # Encontramos o campeão deste nível para este tipo
                    rec = item['raw']
                    tipo_str = TRADUCOES_TIPO.get(t, t.capitalize())
                    dist_str = f" ({int(item['distancia'])}km)" if item['distancia'] != float('inf') else ""
                    
                    campeoes[t] = {
                        'url': rec.get('file'),
                        'autor': rec.get('rec', 'Desconhecido'),
                        'licenca': rec.get('lic', 'CC BY-NC'),
                        'data': rec.get('date', 'Desconhecida'),
                        'duracao': rec.get('length', '0:00'),
                        'fonte': 'Xeno-canto',
                        'tipo_canto': tipo_str if t != 'other' else str(rec.get('type')).capitalize(),
                        'distancia_texto': dist_str,
                        'distancia': item['distancia'],
                        'lat': item['lat'],
                        'lon': item['lon'],
                        'link_web': "https://xeno-canto.org/" + str(rec.get('id', '')),
                        'id': rec.get('id'),
                        'q': item['q'],
                        'q_score': item['q_score'],
                        'comentarios': item['comentarios']
                    }
                    faltantes.remove(t)

        # Nível 1: Município
        if self.municipio:
            print(f"[AUDIO] Nível 1: Buscando em {self.municipio}...")
            recs = self._get_xeno_recordings(f'sp:"{self.scientific_name}" loc:"{self.municipio}"')
            if recs == "KEY_MISSING": return [{"status": "KEY_MISSING"}]
            preencher_vagas(recs)

        # Nível 2: Estado (se ainda faltar algo)
        if faltantes and self.estado:
            print(f"[AUDIO] Nível 2: Buscando em {self.estado} (Faltam: {faltantes})...")
            recs = self._get_xeno_recordings(f'sp:"{self.scientific_name}" loc:"{self.estado}"')
            preencher_vagas(recs)

        # Nível 3: Brasil (se ainda faltar algo)
        if faltantes:
            print(f"[AUDIO] Nível 3: Buscando no Brasil (Faltam: {faltantes})...")
            recs = self._get_xeno_recordings(f'sp:"{self.scientific_name}" cnt:brazil')
            preencher_vagas(recs)

        return list(campeoes.values())[:4]

    def _search_inaturalist(self):
        """Busca observações com sons no iNaturalist (Fallback Global)."""
        try:
            url = "https://api.inaturalist.org/v1/observations"
            params = {
                'taxon_name': self.scientific_name,
                'sounds': 'true',
                'per_page': 2,
                'order_by': 'votes'
            }
            resp = requests.get(url, params=params, headers={"User-Agent": "iBirder/1.0"}, timeout=10)
            if resp.status_code != 200: return []
                 
            data = resp.json()
            audios = []
            for obs in data.get('results', []):
                obs_lat, obs_lon = None, None
                if loc := obs.get('location'):
                    try:
                        coords = loc.split(',')
                        if float(coords[0]) != 0.0: obs_lat, obs_lon = float(coords[0]), float(coords[1])
                    except: pass

                for sound in obs.get('sounds', []):
                    if file_url := sound.get('file_url'):
                        # Métrica Social de Qualidade (v0.8.7): 0-2 votos=2, 3+ votos=4
                        votos = obs.get('faves_count', 0)
                        social_q = 4 if votos >= 3 else 2
                        
                        audios.append({
                            'url': file_url,
                            'autor': obs.get('user', {}).get('login', 'Desconhecido'),
                            'fonte': 'iNaturalist',
                            'data': obs.get('observed_on_string', 'Desconhecida'),
                            'comentarios': obs.get('description', ''),
                            'link_web': f"https://www.inaturalist.org/observations/{obs.get('id')}",
                            'id': obs.get('id'),
                            'lat': obs_lat,
                            'lon': obs_lon,
                            'distancia': haversine_distance(self.lat, self.lon, obs_lat, obs_lon) if self.lat else float('inf'),
                            'q': f"⭐ {votos}",
                            'q_score': social_q
                        })
                        break
                if len(audios) >= 2: break
            return audios
        except: return []
