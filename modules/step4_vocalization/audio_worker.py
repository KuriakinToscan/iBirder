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
    1. Xeno-canto (Prioridade - Qualidade A)
    2. iNaturalist (Fallback)
    """
    # Emite lista de dicts: [{'url': str, 'autor': str, 'fonte': str}, ...]
    audio_found = Signal(list)
    search_failed = Signal()

    def __init__(self, scientific_name, lat=None, lon=None, parent=None):
        super().__init__(parent)
        self.scientific_name = scientific_name
        self.lat = lat
        self.lon = lon

    def run(self):
        if not requests:
            self.search_failed.emit()
            return

        results = []
        try:
            # 1. Tentativa Xeno-canto
            results = self._search_xeno_canto()
            
            # 2. Fallback iNaturalist se Xeno-canto não retornou nada
            if not results:
                print(f"[AUDIO] Xeno-canto sem resultados para {self.scientific_name}. Tentando iNaturalist...")
                results = self._search_inaturalist()
            
            if results:
                self.audio_found.emit(results)
            else:
                self.search_failed.emit()

        except Exception as e:
            print(f"[AUDIO] Erro fatal no worker: {e}")
            traceback.print_exc()
            self.search_failed.emit()

    def _search_xeno_canto(self):
        """Busca gravações no Xeno-canto com urllib encode e filtragem v3 com autenticação."""
        import urllib.parse
        from core.config import carregar_config
        try:
            # Carregar Configurações e Chave XC
            config = carregar_config()
            xc_key = config.get("xc_api_key", "").strip()
            
            if not xc_key:
                print("[AUDIO] Chave de acesso XenoCanto ausente. Notificando UI para convite de ativação.")
                return [{"status": "KEY_MISSING"}]
            
            headers = {"User-Agent": "iBirder-App/1.0"}
            recordings = []
            
            # API v3: Pesquisa com sp: e aspas para precisão, + país
            # sp:"genus species"
            raw_query = f'sp:"{self.scientific_name}" cnt:brazil'
                
            quoted_query = urllib.parse.quote(raw_query)
            # URL v3 com parâmetro de chave
            url = f"https://xeno-canto.org/api/3/recordings?query={quoted_query}"
            url += f"&key={xc_key}"
            print(f"[AUDIO] Xeno-canto request (v3 API): {url}")
            resp = requests.get(url, headers=headers, timeout=10)
            
            if resp.status_code == 200:
                data = resp.json()
                
                # Tratamento de erro específico da v3
                if data.get("error") == "missing_parameter":
                    print("[AUDIO] Erro Xeno-canto v3: 'missing_parameter'. Verifique sua API Key ou Query.")
                    return []
                
                # Validação Rápida da Presença da Ave na API
                num_recordings = data.get("numRecordings", "0")
                if num_recordings == "0" or not data.get('recordings'):
                    print(f"[AUDIO] Nenhuma gravação existente no Brasil para {self.scientific_name} (Xeno-canto v3 retornou 0).")
                    return []
                
                recs_totais = data.get('recordings', [])
                
                # Filtragem Passiva de Alta Qualidade (A e B) In-Memory
                recs_alta_qualidade = [r for r in recs_totais if str(r.get('q')).upper() in ['A', 'B']]
                
                if recs_alta_qualidade:
                    recordings = recs_alta_qualidade
                    print(f"[AUDIO] Curadoria v3 retém {len(recordings)} gravações de Alta Qualidade (A/B) de {len(recs_totais)} disponíveis.")
                else:
                    print(f"[AUDIO] Sem áudios Alta Qualidade A/B (v3). Fallback para as {min(5, len(recs_totais))} melhores.")
                    recordings = recs_totais[:5]

            elif resp.status_code == 401:
                print("[AUDIO] Erro 401: Chave de API Xeno-canto inválida ou ausente.")
                return []

            if not recordings:
                return []

            # 1. Enriquecer gravações e agrupar em baldes por tipo
            baldes_por_tipo = {}
            has_reference = (self.lat is not None and self.lon is not None)
            
            for rec in recordings:
                # Tratar Coordenadas GPS (Blidar nulls)
                str_lat = rec.get('lat')
                str_lng = rec.get('lng')
                if str_lat and str_lng and str_lat != "null" and str_lng != "null":
                    try:
                        r_lat, r_lng = float(str_lat), float(str_lng)
                    except ValueError:
                        r_lat, r_lng = None, None
                else:
                    r_lat, r_lng = None, None

                # Cálculo de distância condicional (v0.4.3)
                if has_reference:
                    dist = haversine_distance(self.lat, self.lon, r_lat, r_lng)
                else:
                    dist = float('inf') # Sem referencia, distancia é irrelevante para o sort inicial
                
                raw_type = str(rec.get('type', '')).lower().strip()
                # Remove espaços duplos e trailing spaces
                raw_type = " ".join(raw_type.split())
                
                # Normaliza o tipo (primeiro item se houver multiplos separados por virgula)
                primeiro_tipo = [t.strip() for t in raw_type.split(',') if t.strip()]
                main_type = primeiro_tipo[0] if primeiro_tipo else 'unknown'
                
                # Mapeia tipos principais
                clean_type = 'other'
                for target_type in ['song', 'begging call', 'flight call', 'alarm call']:
                     if target_type in main_type:
                         clean_type = target_type
                         break
                
                # Evita sobrescrever 'song' ou calls genéricos
                if clean_type == 'other' and 'call' in main_type and 'song' not in main_type:
                     clean_type = 'call'

                item_data = {
                    'raw': rec,
                    'distancia': dist,
                    'type': clean_type,
                    'q': rec.get('q'),
                    'lat': r_lat,
                    'lon': r_lng
                }
                
                if clean_type not in baldes_por_tipo:
                     baldes_por_tipo[clean_type] = []
                baldes_por_tipo[clean_type].append(item_data)

            # 2. Selecionar o Campeão: Regional (Proximidade) ou Elite (Qualidade A/B se sem GPS)
            selected = []
            for t_type, balde in baldes_por_tipo.items():
                if has_reference:
                    # Campeões Regionais (v0.4.3)
                    balde.sort(key=lambda x: x['distancia']) 
                else:
                    # Campeões de Elite Mundiais (A > B > C...) (v0.4.3)
                    balde.sort(key=lambda x: str(x['q']).upper())
                
                selected.append(balde[0])

            # Ordenar por distancia de volta apenas para visualização (se houver ref)
            if has_reference:
                selected.sort(key=lambda x: x['distancia'])

            # Limitar a no max 4
            selected = selected[:4]

            # 3. Formatar output
            audios = []
            for item in selected:
                rec = item['raw']
                file_url = rec.get('file')
                base_link = "https://xeno-canto.org/" + str(rec.get('id', ''))
                
                if file_url:
                    tipo_str = TRADUCOES_TIPO.get(item['type'], item['type'].capitalize())
                    if tipo_str == 'Other':
                         tipo_str = str(rec.get('type')).capitalize()
                    
                    dist_str = f" ({int(item['distancia'])}km)" if item['distancia'] != float('inf') else ""
                         
                    audios.append({
                        'url': file_url,
                        'autor': rec.get('rec', 'Desconhecido'),
                        'licenca': rec.get('lic', 'CC BY-NC'),
                        'data': rec.get('date', 'Desconhecido'),
                        'duracao': rec.get('length', '0:00'),
                        'fonte': 'Xeno-canto',
                        'tipo_canto': tipo_str,
                        'distancia_texto': dist_str,
                        'distancia': item['distancia'],
                        'lat': item['lat'],
                        'lon': item['lon'],
                        'link_web': base_link,
                        'q': item['q']
                    })
            
            if audios:
                print(f"[AUDIO] Retornadas {len(audios)} vocalizações (campeões).")
            
            return audios

        except Exception as e:
            print(f"[AUDIO] Erro na busca Xeno-canto: {e}")
            traceback.print_exc()
            return []

    def _search_inaturalist(self):
        """Busca observações com sons no iNaturalist."""
        try:
            url = "https://api.inaturalist.org/v1/observations"
            params = {
                'taxon_name': self.scientific_name,
                'sounds': 'true',
                'per_page': 2,
                'order_by': 'votes' # Tenta pegar as "melhores" observações
            }
            headers = {"User-Agent": "iBirder/1.0"}
            
            resp = requests.get(url, params=params, headers=headers, timeout=10)
            if resp.status_code != 200:
                 print(f"[AUDIO] Erro iNaturalist: {resp.status_code}")
                 return []
                 
            data = resp.json()
            results = data.get('results', [])
            
            audios = []
            for obs in results:
                location = obs.get('location') # Formato "lat,lon"
                obs_lat, obs_lon = None, None
                if location:
                    try:
                        coords = location.split(',')
                        obs_lat, obs_lon = float(coords[0]), float(coords[1])
                    except (ValueError, IndexError): pass

                sounds = obs.get('sounds', [])
                for sound in sounds:
                    file_url = sound.get('file_url')
                    if file_url:
                        user = obs.get('user', {}).get('login', 'Desconhecido')
                        audios.append({
                            'url': file_url,
                            'autor': user,
                            'fonte': 'iNaturalist',
                            'tipo_canto': 'Gravação Geral',
                            'distancia_texto': '',
                            'lat': obs_lat,
                            'lon': obs_lon
                        })
                        break # Um áudio por observação basta
                
                if len(audios) >= 2:
                    break
            
            if audios:
                print(f"[AUDIO] Encontrados {len(audios)} áudios no iNaturalist.")
                
            return audios

        except Exception as e:
            print(f"[AUDIO] Erro na busca iNaturalist: {e}")
            return []
