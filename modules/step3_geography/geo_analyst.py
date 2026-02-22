import json
import os
from geopy.geocoders import Nominatim
from shapely.geometry import shape, Point

class GeoAnalyst:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(GeoAnalyst, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
            
        self.geolocator = Nominatim(user_agent="ibirder_app_v0.3.11")
        self.biomes_data = None
        self._biome_cache = {} # Novo: RAM Cache
        self._load_biomes()
        self._initialized = True

    def _load_biomes(self):
        print("[GEO] Carregando arquivo de biomas (GeoJSON)...")
        try:
            # Ajuste o caminho conforme a estrutura do usuário
            path = os.path.join("Geo", "biomas.geojson")
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    self.biomes_data = json.load(f)
                print(f"[GEO] Sucesso! {len(self.biomes_data['features'])} polígonos carregados.")
            else:
                print(f"[GEO] ERRO: Arquivo não encontrado em {path}")
        except Exception as e:
            print(f"[GEO] ERRO CRÍTICO ao carregar JSON: {e}")

    def get_biome(self, lat, lon):
        """Verifica em qual polígono do GeoJSON o ponto cai (com Cache Otimizado)."""
        if not self.biomes_data:
            return "Dados de Bioma não carregados"

        # Arredonda para 4 casas decimais (~11m, alta precisão local mas funde pixels vizinhos)
        cache_key = (round(lat, 4), round(lon, 4))
        if cache_key in self._biome_cache:
            print("[GEO] Cache hit! Bioma recuperado instantaneamente.")
            return self._biome_cache[cache_key]

        # Importante: GeoJSON usa (Longitude, Latitude)
        point = Point(lon, lat)

        for feature in self.biomes_data['features']:
            polygon = shape(feature['geometry'])
            if polygon.contains(point):
                # Tenta recuperar o nome em propriedades comuns
                props = feature.get('properties', {})
                biome = props.get('NOM_BIOMA') or props.get('name_biome') or props.get('Name') or props.get('bioma') or "Desconhecido"
                self._biome_cache[cache_key] = biome
                return biome
        
        self._biome_cache[cache_key] = "Fora de área mapeada"
        return "Fora de área mapeada"

    def get_full_details(self, lat, lon):
        """Retorna dicionário completo: Endereço Estruturado + Bioma"""
        print(f"[GEO] Iniciando análise para Lat: {lat}, Lon: {lon}")
        
        # Inicializa com valores padrão
        details = {
            "lat": lat,
            "lon": lon,
            "pais": "Não identificado",
            "estado": "Não identificado", 
            "municipio": "Não identificado", 
            "localidade": "Não identificada", 
            "bioma": "Não identificado"
        }

        # 1. Busca Administrativa (Online)
        try:
            print("[GEO] Consultando API Nominatim (Endereço)...")
            location = self.geolocator.reverse((lat, lon), exactly_one=True, language='pt-br')
            if location:
                address = location.raw.get('address', {})
                
                # País e Estado
                details["pais"] = address.get('country', list(details.values())[2])
                details["estado"] = address.get('state', list(details.values())[3])
                
                # Município (Cascata)
                details["municipio"] = (
                    address.get('city') or 
                    address.get('town') or 
                    address.get('municipality') or 
                    address.get('county') or 
                    "Não identificado"
                )
                
                # Localidade/Bairro (Cascata)
                details["localidade"] = (
                    address.get('suburb') or 
                    address.get('neighbourhood') or 
                    address.get('village') or 
                    address.get('hamlet') or 
                    address.get('locality') or 
                    address.get('isolated_dwelling') or 
                    address.get('allotment') or 
                    "Não identificada"
                )
                
                print(f"[GEO] Endereço estruturado obtido.")
        except Exception as e:
            print(f"[GEO] Erro na API Nominatim: {e}")

        # 2. Busca Ecológica (Offline)
        try:
            print("[GEO] Calculando Bioma (Geometria)...")
            details["bioma"] = self.get_biome(lat, lon)
            print(f"[GEO] Bioma detectado: {details['bioma']}")
        except Exception as e:
             print(f"[GEO] Erro ao processar bioma: {e}")
             details["bioma"] = "Erro no processamento"

        return details
