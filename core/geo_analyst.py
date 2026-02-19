import json
import os
from geopy.geocoders import Nominatim
from shapely.geometry import shape, Point

class GeoAnalyst:
    def __init__(self):
        self.geolocator = Nominatim(user_agent="ibirder_app_v0.3.11")
        self.biomes_data = None
        self._load_biomes()

    def _load_biomes(self):
        """Carrega o GeoJSON de biomas na memória (Cache)"""
        try:
            # Ajuste o caminho conforme a estrutura do usuário
            path = os.path.join("Geo", "biomas.geojson")
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    self.biomes_data = json.load(f)
            else:
                print(f"[GEO] Arquivo de biomas não encontrado em: {path}")
        except Exception as e:
            print(f"[GEO] Erro ao carregar biomas: {e}")

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
                return props.get('name_biome') or props.get('Name') or props.get('bioma') or "Desconhecido"
        
        return "Fora de área mapeada"

    def get_full_details(self, lat, lon):
        """Retorna dicionário completo: Endereço + Bioma"""
        details = {
            "pais": "Desconhecido", "estado": "-", 
            "cidade": "-", "localidade": "-", "bioma": "-"
        }

        # 1. Busca Administrativa (Online)
        try:
            location = self.geolocator.reverse((lat, lon), exactly_one=True, language='pt-br')
            if location:
                address = location.raw.get('address', {})
                details["pais"] = address.get('country', '')
                details["estado"] = address.get('state', '')
                details["cidade"] = address.get('city') or address.get('town') or address.get('village', '')
                details["localidade"] = address.get('suburb') or address.get('neighbourhood') or address.get('road', '')
        except Exception as e:
            print(f"[GEO] Erro na API Nominatim: {e}")

        # 2. Busca Ecológica (Offline)
        try:
            details["bioma"] = self.get_biome(lat, lon)
        except Exception as e:
             print(f"[GEO] Erro ao processar bioma: {e}")
             details["bioma"] = "Erro no processamento"

        return details
