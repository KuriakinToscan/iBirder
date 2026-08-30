#  iBirder -  IA para Birdwatching
#  Copyright (C) 2026  Kuriakin Humberto Toscan
#
#  Este programa é um software livre: você pode redistribuí-lo e/ou 
#  modificá-lo sob os termos da Licença Pública Geral GNU conforme 
#  publicada pela Free Software Foundation, tanto a versão 3 da 
#  Licença, como (a seu critério) qualquer versão posterior.
#
#  Este programa é distribuído na esperança de que possa ser útil, 
#  mas SEM NENHUMA GARANTIA; sem uma garantia implícita de 
#  ADEQUAÇÃO A QUALQUER MERCADO OU APLICAÇÃO EM PARTICULAR. 
#  Veja a Licença Pública Geral GNU para mais detalhes.
#
#  Você deve ter recebido uma cópia da Licença Pública Geral GNU 
#  junto com este programa. Se não, veja <https://www.gnu.org/licenses/>.

import os
import sys
import json
import logging
from geopy.geocoders import Nominatim
from shapely.geometry import shape, Point

from core.paths import BASE_DIR

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
        logging.debug("Carregando arquivo de biomas (GeoJSON)...")
        try:
            # Resolve o caminho para funcionar tanto em dev quanto no executável
            if getattr(sys, 'frozen', False):
                path = os.path.join(sys._MEIPASS, "Geo", "biomas.geojson")
            else:
                path = os.path.join(str(BASE_DIR), "Geo", "biomas.geojson")
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    self.biomes_data = json.load(f)
                logging.debug(f"Sucesso! {len(self.biomes_data['features'])} polígonos de bioma carregados.")
            else:
                logging.warning(f"Arquivo de biomas não encontrado em {path}")
        except Exception as e:
            logging.error(f"Erro crítico ao carregar JSON de biomas: {e}")

    def get_biome(self, lat, lon):
        """Verifica em qual polígono do GeoJSON o ponto cai (com Cache Otimizado)."""
        if not self.biomes_data:
            return "Dados de Bioma não carregados"

        # Arredonda para 4 casas decimais (~11m, alta precisão local mas funde pixels vizinhos)
        cache_key = (round(lat, 4), round(lon, 4))
        if cache_key in self._biome_cache:
            logging.debug("Cache hit! Bioma recuperado instantaneamente.")
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
        logging.info(f"Iniciando análise geográfica para Lat: {lat}, Lon: {lon}")
        
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
            logging.debug("Consultando API Nominatim (Endereço)...")
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
                
                logging.debug(f"Endereço estruturado obtido.")
        except Exception as e:
            logging.error(f"Erro na API Nominatim: {e}")

        # 2. Busca Ecológica (Offline)
        try:
            logging.debug("Calculando Bioma (Geometria)...")
            details["bioma"] = self.get_biome(lat, lon)
            logging.info(f"Bioma detectado: {details['bioma']}")
        except Exception as e:
             logging.error(f"Erro ao processar bioma: {e}")
             details["bioma"] = "Erro no processamento"

        return details
