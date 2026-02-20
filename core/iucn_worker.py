import os
import requests
import json
import traceback
import geopandas as gpd
from PySide6.QtCore import QThread, Signal

class IUCNWorker(QThread):
    finished = Signal(dict)
    error_occurred = Signal(str)

    def __init__(self, scientific_name, shape_path="Geo/aves.shp", export_dir="Geo/exports", parent=None):
        super().__init__(parent)
        self.scientific_name = scientific_name
        self.shape_path = shape_path
        self.export_dir = export_dir

    def run(self):
        print(f"[IUCN Worker] Iniciando processamento para {self.scientific_name}")
        # 1. Obter Status da IUCN
        token = os.environ.get("TOKEN_IUCN", "") 
        iucn_status = "Não Avaliado"
        url_iucn = ""
        
        if token:
            try:
                 api_url = f"https://apiv3.iucnredlist.org/api/v3/species/{self.scientific_name}?token={token}"
                 print(f"[IUCN Worker] Consultando API IUCN...")
                 resp = requests.get(api_url, timeout=10)
                 if resp.status_code == 200:
                     data = resp.json()
                     if data.get("result"):
                         iucn_status = data["result"][0].get("category", "Não Avaliado")
                         # Link para documentacao da IUCN:
                         url_iucn = f"https://www.iucnredlist.org/search?query={self.scientific_name.replace(' ', '+')}&searchType=species"
                         print(f"[IUCN Worker] Status encontrado: {iucn_status}")
                     else:
                         print("[IUCN Worker] Espécie não retornou resultados na IUCN Red List.")
                 else:
                     print(f"[IUCN Worker] Erro HTTP IUCN: {resp.status_code}")
            except Exception as e:
                 print(f"[IUCN Worker] Erro na API da IUCN: {e}")
        else:
            print("[IUCN Worker] TOKEN_IUCN não configurado. Pulando consulta web.")
            
        # URL fallback (sempre formamos o search, pra ajudar o usuario)
        if not url_iucn:
             url_iucn = f"https://www.iucnredlist.org/search?query={self.scientific_name.replace(' ', '+')}&searchType=species"
        
        # 2. Processamento Espacial
        export_path = ""
        try:
            if not os.path.exists(self.export_dir):
                os.makedirs(self.export_dir, exist_ok=True)
                
            raw_name = self.scientific_name
            clean_name = raw_name.replace(" ", "_").lower()
            filename = f"{clean_name}_iucn.geojson"
            export_path = os.path.join(self.export_dir, filename)

            if os.path.exists(self.shape_path):
                print(f"[IUCN Worker] Carregando Shapefile Base: {self.shape_path}")
                gdf = gpd.read_file(self.shape_path)
                
                # Identifica a coluna correta do nome cientifico (ajuste flexível)
                col_name = 'SCINAME'
                if 'SCINAME' not in gdf.columns and 'sci_name' in gdf.columns:
                    col_name = 'sci_name'
                else:
                    for col in gdf.columns:
                        if 'name' in col.lower() and 'sci' in col.lower():
                            col_name = col
                            break

                if col_name in gdf.columns:
                    # Filtra geometricamente
                    filtered_gdf = gdf[gdf[col_name].str.lower() == raw_name.lower()].copy()
                    
                    if not filtered_gdf.empty:
                        # Injeta o status mais recente
                        filtered_gdf['iucn_status'] = iucn_status
                        
                        # Exporta o GeoJSON convertendo para JSON puro e salvando com ensure_ascii=False explícito
                        print(f"[IUCN Worker] Exportando polígonos filtrados: {export_path}")
                        geojson_str = filtered_gdf.to_json()
                        geojson_data = json.loads(geojson_str)
                        
                        with open(export_path, "w", encoding="utf-8") as f:
                            json.dump(geojson_data, f, ensure_ascii=False, indent=2)
                        print("[IUCN Worker] GeoJSON salvo com sucesso! (Caracteres especiais mantidos)")
                    else:
                        print(f"[IUCN Worker] Aviso: Espécie '{raw_name}' não teve polígonos no shapefile.")
                else:
                    print(f"[IUCN Worker] Aviso: Coluna '{col_name}' ou similar não encontrada no shapefile.")
            else:
                print(f"[IUCN Worker] Shapefile mestre não encontrado localmente em {self.shape_path}.")
        except Exception as e:
            print(f"[IUCN Worker] Erro no processamento espacial: {e}")
            traceback.print_exc()

        # 3. Empacota e Sinaliza pra UI
        results = {
            "iucn_status": iucn_status,
            "geojson_path": export_path if os.path.exists(export_path) else None,
            "link_iucn": url_iucn
        }
        self.finished.emit(results)
