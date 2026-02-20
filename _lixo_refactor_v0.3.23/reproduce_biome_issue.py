from core.geo_analyst import GeoAnalyst

print("Iniciando reprodução do erro de bioma...")
analyst = GeoAnalyst()

# Coordenadas de Rosário do Sul, RS (Deveria ser Pampa)
lat = -30.1095
lon = -54.9483

print(f"Testando coordenadas: Lat {lat}, Lon {lon}")
biome = analyst.get_biome(lat, lon)
print(f"Bioma detectado: {biome}")

# Teste com coordenadas conhecidas (ex: Amazônia - Manaus)
lat_am = -3.1190
lon_am = -60.0217
print(f"Testando coordenadas (Manaus): Lat {lat_am}, Lon {lon_am}")
biome_am = analyst.get_biome(lat_am, lon_am)
print(f"Bioma detectado: {biome_am}")
