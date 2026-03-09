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

from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS
import logging

def get_decimal_from_dms(dms, ref):
    degrees = dms[0]
    minutes = dms[1]
    seconds = dms[2]
    decimal = degrees + (minutes / 60.0) + (seconds / 3600.0)
    if ref in ['S', 'W']:
        decimal = -decimal
    return decimal

def extract_lat_lon(image_path):
    try:
        image = Image.open(image_path)
        exif_data = image._getexif()
        if not exif_data: return None

        gps_info = {}
        for tag, value in exif_data.items():
            decoded = TAGS.get(tag, tag)
            if decoded == "GPSInfo":
                for t in value:
                    sub_decoded = GPSTAGS.get(t, t)
                    gps_info[sub_decoded] = value[t]

        if not gps_info: return None

        lat = get_decimal_from_dms(gps_info['GPSLatitude'], gps_info['GPSLatitudeRef'])
        lon = get_decimal_from_dms(gps_info['GPSLongitude'], gps_info['GPSLongitudeRef'])

        return lat, lon
    except Exception as e:
        logging.debug(f"Erro ao ler EXIF de {image_path}: {e}")
        return None

try:
    from geopy.geocoders import Nominatim
except ImportError:
    Nominatim = None

def search_location(query, user_agent="ibirder_app_v0.3.7"):
    """
    Busca coordenadas para um determinado local (cidade, endereço, etc).
    Retorna uma lista de dicionários: [{'address': str, 'lat': float, 'lon': float}, ...]
    """
    if Nominatim is None:
        logging.warning("Geopy não instalado. Instale com 'pip install geopy'.")
        return []

    try:
        geolocator = Nominatim(user_agent=user_agent)
        locations = geolocator.geocode(query, exactly_one=False, limit=5, language='pt')
        
        results = []
        if locations:
            for loc in locations:
                results.append({
                    'address': loc.address,
                    'lat': loc.latitude,
                    'lon': loc.longitude
                })
        return results
    except Exception as e:
        logging.error(f"Erro na busca de localização: {e}")
        return []
