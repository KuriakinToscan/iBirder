import json
import logging
from PySide6.QtCore import QThread, Signal, QSettings

class IUCNWorker(QThread):
    finished = Signal(dict)
    error_occurred = Signal(str)

    def __init__(self, scientific_name, shape_path="Geo/aves.shp", export_dir="Geo/exports", parent=None):
        super().__init__(parent)
        self.scientific_name = scientific_name
        self.shape_path = shape_path
        self.export_dir = export_dir

    def run(self):
        logging.info(f"Iniciando Etapa 3-IUCN para {self.scientific_name}")
        # 1. Obter Status da IUCN
        # Transição API-Free (v0.8.0): IUCN API desativada.
        iucn_status = "Não Avaliado"
        url_iucn = ""
        is_fallback = True
        
            
        # URL oficial (sempre formamos o search, pra ajudar o usuario msm que nao tenha a exata string da categoria)
        if not url_iucn:
             url_iucn = f"https://www.iucnredlist.org/search?query={self.scientific_name.replace(' ', '+')}&searchType=species"

        # -------------------
        # Fallback iNaturalist (v0.8.3 - Consulta em 2 Etapas)
        # -------------------
        if is_fallback:
            try:
                logging.debug(f"Buscando ID no iNaturalist para {self.scientific_name}...")
                search_url = f"https://api.inaturalist.org/v1/taxa?q={self.scientific_name}&is_active=true&rank=species"
                resp_search = requests.get(search_url, timeout=10)
                
                if resp_search.status_code == 200:
                    search_data = resp_search.json()
                    if search_data.get("results") and len(search_data["results"]) > 0:
                        taxon_id = search_data["results"][0]["id"]
                        
                        logging.debug(f"Buscando detalhes para Taxon ID {taxon_id}...")
                        detail_url = f"https://api.inaturalist.org/v1/taxa/{taxon_id}"
                        resp_detail = requests.get(detail_url, timeout=10)
                        
                        if resp_detail.status_code == 200:
                            detail_data = resp_detail.json()
                            results = detail_data.get("results", [])
                            if results:
                                taxon_details = results[0]
                                c_statuses = taxon_details.get("conservation_statuses", [])
                                
                                # Busca o status global da IUCN
                                iucn_entry = next((s for s in c_statuses if "IUCN" in (s.get("authority") or "")), None)
                                
                                if iucn_entry:
                                    raw_status = iucn_entry.get("status", "NE").upper()
                                    # Mapeamento para Português (v0.8.3)
                                    mapeamento = {
                                        "LC": "Pouco Preocupante (LC)",
                                        "NT": "Quase Ameaçada (NT)",
                                        "VU": "Vulnerável (VU)",
                                        "EN": "Em Perigo (EN)",
                                        "CR": "Criticamente em Perigo (CR)",
                                        "EW": "Extinta na Natureza (EW)",
                                        "EX": "Extinta (EX)",
                                        "DD": "Dados Insuficientes (DD)",
                                        "NE": "Não Avaliada (NE)"
                                    }
                                    status_traduzido = mapeamento.get(raw_status, raw_status)
                                    iucn_status = status_traduzido
                                else:
                                    iucn_status = "Não Avaliado / Seguro"
                            else:
                                iucn_status = "Erro nos detalhes (iNaturalist)"
                        else:
                            iucn_status = "Erro na API de Detalhes (iNaturalist)"
                    else:
                        iucn_status = "Espécie não encontrada (iNaturalist)"
                else:
                    iucn_status = "Erro na API de Busca (iNaturalist)"
                
                logging.debug(f"Status IUCN Final: {iucn_status}")
            except Exception as e:
                logging.error(f"Erro no Fallback IUCN iNaturalist: {e}")
                iucn_status = "Erro de Conexão (Fallback)"
        
        # 2. Processamento Espacial
        export_path = ""
        if not is_fallback:
            try:
                if not os.path.exists(self.export_dir):
                    os.makedirs(self.export_dir, exist_ok=True)
                    
                raw_name = self.scientific_name
                clean_name = raw_name.replace(" ", "_").lower()
                filename = f"{clean_name}_iucn.geojson"
                export_path = os.path.join(self.export_dir, filename)

                if os.path.exists(self.shape_path):
                    import geopandas as gpd
                    logging.debug(f"Carregando Shapefile Base: {self.shape_path}")
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
                            logging.info(f"Exportando polígonos filtrados: {export_path}")
                            geojson_str = filtered_gdf.to_json()
                            geojson_data = json.loads(geojson_str)
                            
                            with open(export_path, "w", encoding="utf-8") as f:
                                json.dump(geojson_data, f, ensure_ascii=False, indent=2)
                            logging.debug("GeoJSON de ocorrência salvo com sucesso.")
                        else:
                            logging.warning(f"Espécie '{raw_name}' não teve polígonos no shapefile.")
                    else:
                        logging.warning(f"Coluna científica não encontrada no shapefile.")
                else:
                    logging.warning(f"Shapefile mestre não encontrado localmente em {self.shape_path}.")
            except Exception as e:
                logging.error(f"Erro no processamento espacial: {e}", exc_info=True)
        else:
             logging.debug("Ignorando geração do GeoJSON devido ao Fallback.")

        # 3. Empacota e Sinaliza pra UI
        results = {
            "iucn_status": iucn_status,
            "geojson_path": export_path if os.path.exists(export_path) else None,
            "link_iucn": url_iucn
        }
        self.finished.emit(results)
