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
        """Verifica em qual polígono do GeoJSON o ponto cai."""
        if not self.biomes_data:
            return "Dados de Bioma não carregados"

        # Importante: GeoJSON usa (Longitude, Latitude)
        point = Point(lon, lat)

        for feature in self.biomes_data['features']:
            polygon = shape(feature['geometry'])
            if polygon.contains(point):
                # Tenta recuperar o nome em propriedades comuns
                props = feature.get('properties', {})
                return props.get('NOM_BIOMA') or props.get('name_biome') or props.get('Name') or props.get('bioma') or "Desconhecido"
        
        return "Fora de área mapeada"

    def get_full_details(self, lat, lon):
        """Retorna dicionário completo: Endereço + Bioma"""
        print(f"[GEO] Iniciando análise para Lat: {lat}, Lon: {lon}")
        details = {
            "pais": "Desconhecido", "estado": "-", 
            "cidade": "-", "localidade": "-", "bioma": "-"
        }

        # 1. Busca Administrativa (Online)
        try:
            print("[GEO] Consultando API Nominatim (Endereço)...")
            location = self.geolocator.reverse((lat, lon), exactly_one=True, language='pt-br')
            if location:
                print(f"[GEO] Endereço encontrado: {location.address[:30]}...")
                address = location.raw.get('address', {})
                details["pais"] = address.get('country', '')
                details["estado"] = address.get('state', '')
                details["cidade"] = address.get('city') or address.get('town') or address.get('village', '')
                details["localidade"] = address.get('suburb') or address.get('neighbourhood') or address.get('road', '')
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
