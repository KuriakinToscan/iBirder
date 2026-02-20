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
        """Busca gravações de qualidade A e B no Xeno-canto no Brasil."""
        try:
            url = "https://xeno-canto.org/api/2/recordings"
            # Buscando de forma abrangente no Brasil e qualidades boas para ter pool para filtrar
            query = f"{self.scientific_name} cnt:Brazil"
            params = {'query': query}
            
            resp = requests.get(url, params=params, timeout=10)
            if resp.status_code != 200:
                print(f"[AUDIO] Erro Xeno-canto: {resp.status_code}")
                return []
                
            data = resp.json()
            recordings = data.get('recordings', [])
            
            if not recordings:
                return []

            # 1. Enriquecer gravações com distância e extrair tipo
            processed_recs = []
            for rec in recordings:
                # Filtrar qualidade A ou B apenas
                if rec.get('q') not in ['A', 'B']:
                    continue

                rec_lat = rec.get('lat')
                rec_lng = rec.get('lng')
                
                try:
                    r_lat = float(rec_lat) if rec_lat else None
                    r_lng = float(rec_lng) if rec_lng else None
                except ValueError:
                    r_lat, r_lng = None, None

                dist = haversine_distance(self.lat, self.lon, r_lat, r_lng)
                
                # Normaliza o tipo (primeiro item se houver multiplos separados por virgula)
                raw_type = str(rec.get('type', '')).lower()
                primeiro_tipo = [t.strip() for t in raw_type.split(',') if t.strip()]
                main_type = primeiro_tipo[0] if primeiro_tipo else 'unknown'
                
                # Mapeia tipos principais que queremos se houver match solto
                clean_type = 'other'
                for target_type in ['song', 'begging call', 'flight call', 'alarm call']:
                     if target_type in main_type:
                         clean_type = target_type
                         break
                # Trata 'call' separado para não conflitar com 'x call'
                if clean_type == 'other' and 'call' in main_type and 'song' not in main_type:
                     clean_type = 'call'

                processed_recs.append({
                    'raw': rec,
                    'dist': dist,
                    'q': rec.get('q'),
                    'type': clean_type,
                    'lat': r_lat,
                    'lon': r_lng
                })

            # 2. Ordenar: Qualidade A > Menor Distância, depois Qualidade B > Menor distância
            processed_recs.sort(key=lambda x: (0 if x['q'] == 'A' else 1, x['dist']))

            # 3. Selecionar diversidade: 1 de cada tipo principal se disponível, até max 4
            selected = []
            types_seen = set()
            
            for pr in processed_recs:
                 if len(selected) >= 4:
                     break
                 if pr['type'] not in types_seen:
                     selected.append(pr)
                     types_seen.add(pr['type'])

            # Fazer uma segunda passada se não atingiu diversidade pra pegar os melhores q sobraram
            if len(selected) < 2:
                 for pr in processed_recs:
                      if len(selected) >= 3: break
                      if pr not in selected:
                           selected.append(pr)

            # Formatar output
            audios = []
            for item in selected:
                rec = item['raw']
                file_url = rec.get('file')
                if file_url:
                    tipo_str = TRADUCOES_TIPO.get(item['type'], item['type'].capitalize())
                    if tipo_str == 'Other':
                         tipo_str = str(rec.get('type')).capitalize()
                    
                    dist_str = f" ({int(item['dist'])}km)" if item['dist'] != float('inf') else ""
                         
                    audios.append({
                        'url': file_url,
                        'autor': rec.get('rec', 'Desconhecido'),
                        'fonte': 'Xeno-canto',
                        'tipo_canto': tipo_str,
                        'distancia_texto': dist_str,
                        'lat': item['lat'],
                        'lon': item['lon']
                    })
            
            if audios:
                print(f"[AUDIO] Encontrados {len(audios)} áudios diversificados no Xeno-canto.")
            
            return audios

        except Exception as e:
            print(f"[AUDIO] Erro na busca Xeno-canto: {e}")
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
                sounds = obs.get('sounds', [])
                for sound in sounds:
                    file_url = sound.get('file_url')
                    # iNat as vezes retorna file_url como None se for soundcloud (não suportado direto no player simples as vezes)
                    # Mas se for arquivo hosted 'file_url' costuma vir mp3/m4a
                    if file_url:
                        user = obs.get('user', {}).get('login', 'Desconhecido')
                        audios.append({
                            'url': file_url,
                            'autor': user,
                            'fonte': 'iNaturalist',
                            'tipo_canto': 'Gravação Geral',
                            'distancia_texto': '',
                            'lat': None,
                            'lon': None
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
