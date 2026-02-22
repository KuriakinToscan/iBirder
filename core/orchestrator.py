import os
from PySide6.QtCore import QObject, Signal

# Importações dos Workers das Etapas
from modules.step1_identity.id_worker import LocalIdentificationWorker
from modules.step2_biology.wiki_worker import BuscadorWorker
from modules.step3_geography.iucn_worker import IUCNWorker
from modules.step4_vocalization.audio_worker import AudioWorker
from modules.step5_taxonomy.ebird_worker import EBirdWorker
from modules.step3_geography.geo_analyst import GeoAnalyst
from PySide6.QtCore import QObject, Signal, QThread
import requests
from core.config import carregar_config

# Etapa 6 placeholder
# from modules.step6_persistence.exif_manager import EXIFManager

class GeoWorker(QThread):
    finished = Signal(dict)
    
    def __init__(self, lat, lon, parent=None):
        super().__init__(parent)
        self.lat = lat
        self.lon = lon
        
    def run(self):
        analyst = GeoAnalyst()
        details = analyst.get_full_details(self.lat, self.lon)
        self.finished.emit(details)

class Orchestrator(QObject):
    """
    O Cérebro Central (Pipeline de 6 Etapas).
    Gerencia a execução em cascata dos workers, o registro no SessionLogger
    e emite sinais de progresso para a Interface Gráfica, mantendo o total
    desacoplamento das regras de negócio.
    """
    
    # Sinais para atualizar a Janela Principal (View)
    update_available = Signal(dict) # Para OTA Updater
    
    step1_identificacao_concluida = Signal(dict)
    step1_identificacao_erro = Signal(str)
    step1_progress_updated = Signal(str)  # Expondo o progresso para a UI
    
    step2_wiki_concluida = Signal(dict)
    step2_wiki_erro = Signal()
    
    step3_iucn_concluida = Signal(dict)
    step3_geo_concluida = Signal(dict)
    
    step4_audio_concluido = Signal(list)
    step4_audio_erro = Signal()
    
    step5_ebird_concluido = Signal(dict)
    
    # Novo sinal para plotagem externa (v0.4.3)
    audio_processed = Signal(list)
    limpar_painel_audio = Signal() # Sinal para a UI limpar o painel

    def __init__(self, session_logger, parent=None):
        super().__init__(parent)
        self.session_logger = session_logger
        
        # Referências seguras para as threads
        self.id_worker = None
        self.wiki_worker = None
        self.iucn_worker = None
        self.geo_worker = None
        self.audio_worker = None
        self.ebird_worker = None
        
        self.species_cache = {} # Cache de taxonomia e geografia RAM
        
        # Estado Geográfico Armazenado pelo Pipeline
        self.current_lat = None
        self.current_lon = None
        self.has_location = False # Flag de estado (v0.4.3)
        
        # Inteligência Evolutiva (OTA Updater)
        import time
        start_ota_time = time.time()
        
        self.new_ia_available = False
        
        from core.updater import ModelUpdater
        self.updater = ModelUpdater(parent=self)
        # Ao invés de jogar sinal direto para UI agora, armazenamos a informação silenciosamente
        self.updater.update_available.connect(self._on_update_detected)
        # Disparo silencioso em background
        self.updater.check_for_updates()
        
        ota_ms = (time.time() - start_ota_time) * 1000
        print(f"[PERFORMANCE] Dispatch da Thread OTA (Updater) em {ota_ms:.2f} ms")

    def _on_update_detected(self, manifest_data):
        """Callback silencioso que a UI ou fluxo podem consultar depois."""
        self.new_ia_available = True
        self.update_available.emit(manifest_data) # Opcional: mantemos emit dependendo de quem escuta, mas flagamos True

    def start_pipeline_identificacao(self, image_path, skip_model=False, is_photo=True):
        """Inicia a Etapa 1 completa."""
        print(f"[Orchestrator] Iniciando Etapa 1 para: {image_path}")
        if self.id_worker:
            self.id_worker.deleteLater()
            
        self.id_worker = LocalIdentificationWorker(image_path, parent=self)
        self.id_worker.skip_model = skip_model
        self.id_worker.is_photo = is_photo
        self.id_worker.finished.connect(self._on_step1_finished)
        self.id_worker.error.connect(self._on_step1_error)
        self.id_worker.progress_updated.connect(self.step1_progress_updated.emit)
        self.id_worker.start()

    def update_location(self, lat, lon):
        self.current_lat = lat
        self.current_lon = lon
        self.has_location = (lat is not None and lon is not None)
        
    def start_cascade_from_step2(self, sci_name):
        """Dispara as etapas iniciais. O áudio agora segue a geografia."""
        print(f"[Orchestrator] Iniciando cascata a partir da Etapa 2 para: {sci_name}")
        self.start_step2_biology(sci_name)
        self.start_step3_geography(sci_name)
        # Etapa 4 (Audio) agora é disparada no _on_step3_geo_finished
        # Etapa 5 (Taxonomia) pode continuar paralela
        self.start_step5_taxonomy(sci_name)

    def reprocessar_localizacao(self, lat, lon):
        """Atualiza coordenadas, invalida cache de áudio e reinicia busca geo-acústica."""
        # Trava de Redundância (v0.4.3)
        if self.current_lat == lat and self.current_lon == lon and self.has_location:
            print("[Orchestrator] Coordenadas idênticas. Ignorando reprocessamento.")
            return

        print(f"[Orchestrator] Reprocessando localização manual: {lat}, {lon}")
        self.current_lat = lat
        self.current_lon = lon
        self.has_location = (lat is not None and lon is not None)
        
        # Fluxo de Limpeza (v0.4.3)
        self.limpar_painel_audio.emit()

        # Invalida cache de áudio da espécie atual
        sci_name = getattr(self, "_last_sci_name", None)
        if sci_name and hasattr(self, "_cache_audio"):
            if sci_name in self._cache_audio:
                del self._cache_audio[sci_name]
                print(f"[Orchestrator] Cache de áudio para {sci_name} invalidado.")

        # Interromper threads de áudio ativas
        if self.audio_worker and self.audio_worker.isRunning():
            self.audio_worker.requestInterruption()
            self.audio_worker.quit()
            print("[Orchestrator] Busca de áudio anterior interrompida.")

        if sci_name:
            self.start_step3_geography(sci_name)

    # --- Callbacks e Engatilhamentos ---
    
    def _on_step1_error(self, err_msg):
        self.step1_identificacao_erro.emit(err_msg)

    def _on_step1_finished(self, dados_identificacao):
        print("[Orchestrator] Etapa 1 Concluída.")
        
        # Opcional: Registrar Etapa 1 direto no log (já feito na janela, mas poderia ser aqui centralizado)
        # self.session_logger.registrar_identificacao(dados_identificacao)
        
        # Envia pra View pintar o passarinho
        self.step1_identificacao_concluida.emit(dados_identificacao)
        
        nome_cientifico = dados_identificacao.get("nome_cientifico")
        status_msg = dados_identificacao.get("status_msg", "")
        
        # GUARD CLAUSE: Previne processamento pesado para IDs falhadas
        if not nome_cientifico or "Inconclusiva" in status_msg or "Inconclusiva" in nome_cientifico or nome_cientifico == "Desconhecido":
            print("[Orchestrator] Identificação Inconclusiva detectada. Bloqueando cascata de workers externos.")
            return
        
        self._last_sci_name = nome_cientifico
        # Se passou o guard, Engatilha as etapas. O áudio virá após o GeoAnalyst.
        self.start_step2_biology(nome_cientifico)
        self.start_step3_geography(nome_cientifico)
        self.start_step5_taxonomy(nome_cientifico)
            
    # --- Etapa 2 ---
    def start_step2_biology(self, sci_name):
        if self.wiki_worker: self.wiki_worker.deleteLater()
        self.wiki_worker = BuscadorWorker(sci_name, parent=self)
        self.wiki_worker.info_found.connect(self._on_step2_finished)
        self.wiki_worker.error_occurred.connect(self.step2_wiki_erro)
        self.wiki_worker.start()
        
    def _on_step2_finished(self, resultados):
        print("[Orchestrator] Etapa 2 Concluída.")
        if self.session_logger:
            self.session_logger.atualizar_ultimo_registro(resultados)
        self.step2_wiki_concluida.emit(resultados)
        
        # Fallback IUCN via WikiAves
        if getattr(self, "esperando_fallback_iucn", False):
            status_wiki = resultados.get("status_conservacao")
            if status_wiki and status_wiki != "Não encontrado":
                print(f"[Orchestrator] Aplicando Fallback de Conservação WikiAves: {status_wiki}")
                self.step3_iucn_concluida.emit({
                    "iucn_status": f"{status_wiki} (Fonte: WikiAves)",
                    "geojson_path": None,
                    "link_iucn": f"https://www.iucnredlist.org/search?query={resultados.get('original_scientific_name', '').replace(' ', '+')}&searchType=species"
                })
            else:
                print("[Orchestrator] WikiAves não retornou status. Acionando Fallback iNaturalist.")
                self._executar_fallback_inaturalist(resultados.get("original_scientific_name", ""))
            self.esperando_fallback_iucn = False
            
    def _executar_fallback_inaturalist(self, sci_name):
        fallback_res = {
            "iucn_status": "Não Avaliado (Fallback Local)",
            "geojson_path": None,
            "link_iucn": f"https://www.iucnredlist.org/search?query={sci_name.replace(' ', '+')}&searchType=species"
        }
        try:
            resp = requests.get(f"https://api.inaturalist.org/v1/taxa?q={sci_name}&is_active=true&rank=species", timeout=3)
            if resp.status_code == 200 and resp.json().get("results"):
                cs = resp.json()["results"][0].get("conservation_status")
                fallback_res["iucn_status"] = f"{cs.get('status', 'Não Avaliado').upper()} (via iNaturalist)" if cs else "Não Avaliado / Seguro (via iNaturalist)"
        except Exception: pass
        self._on_step3_finished(fallback_res)

    # --- Etapa 3 ---
    def start_step3_geography(self, sci_name):
        """Etapa 3: Geografia (IUCN + GeoAnalyst/Nominatim)."""
        self._last_sci_name = sci_name
        
        # 3A. IUCN
        config = carregar_config()
        token = config.get("iucn_api_key", "").strip() or os.environ.get("TOKEN_IUCN", "").strip()
        
        if not token:
            print("[Orchestrator] Chave IUCN ausente. Aguardando fallback biológico (WikiAves).")
            self.esperando_fallback_iucn = True
        else:
            if self.iucn_worker: self.iucn_worker.deleteLater()
            self.iucn_worker = IUCNWorker(sci_name, parent=self)
            self.iucn_worker.finished.connect(self._on_step3_finished)
            self.iucn_worker.start()

        # 3B. GeoAnalyst (Nominatim/Pampa) - Sempre roda se tivermos coords ou para centroide
        if self.current_lat and self.current_lon:
            if self.geo_worker: self.geo_worker.deleteLater()
            self.geo_worker = GeoWorker(self.current_lat, self.current_lon, parent=self)
            self.geo_worker.finished.connect(self._on_step3_geo_finished)
            self.geo_worker.start()
        else:
            print("[Orchestrator] Lat/Lon ausentes. Aguardando input manual ou fallback para habilitar áudio.")

    def _on_step3_geo_finished(self, details):
        print(f"[Orchestrator] GeoAnalyst concluído para {details.get('municipio')}.")
        # Atualiza coordenadas do Orchestrator com a precisão do Analyst (centroide se necessário)
        self.current_lat = details.get('lat')
        self.current_lon = details.get('lon')
        
        self.step3_geo_concluida.emit(details)
        
        # DISPARO SEQUENCIAL DO ÁUDIO
        if self._last_sci_name:
            self.start_step4_vocalization(self._last_sci_name)

    def _on_step3_finished(self, results):
        print("[Orchestrator] Etapa 3 Concluída.")
        self.step3_iucn_concluida.emit(results)
        
    # --- Etapa 4 ---
    def start_step4_vocalization(self, sci_name):
        if not hasattr(self, '_cache_audio'):
            self._cache_audio = {}
            
        if sci_name in self._cache_audio:
            print(f"[Orchestrator] Cache Hit em Áudio (Vocalização) para {sci_name}. Pulando rede e ressignificando UI instantaneamente!")
            # Retorna via Short-Circuit imitador da conlcusão do worker
            self.step4_audio_concluido.emit(self._cache_audio[sci_name])
            return
            
        if self.audio_worker: self.audio_worker.deleteLater()
        self.audio_worker = AudioWorker(sci_name, lat=self.current_lat, lon=self.current_lon, parent=self)
        
        # Conectar sinal com wrapper (lambda) para interceptar o save state
        self.audio_worker.audio_found.connect(lambda audios: self._on_step4_finished_intercept(sci_name, audios))
        self.audio_worker.search_failed.connect(lambda: self._on_step4_failed_intercept(sci_name))
        self.audio_worker.start()

    def _on_step4_finished_intercept(self, sci_name, audios):
        if sci_name:
            self._cache_audio[sci_name] = audios
            print(f"[Orchestrator] Áudio de {sci_name} persistido ({len(audios)} items) em Layer 4 Cache da Sessão.")
        self.step4_audio_concluido.emit(audios)
        self.audio_processed.emit(audios) # Emitir para plotagem externa (v0.4.3)
        
    def _on_step4_failed_intercept(self, sci_name):
        # Cache negative hit para nao ficar tentando ad æternum se soubemos q nao existiu (API 0)
        if sci_name:
             self._cache_audio[sci_name] = []
        self.step4_audio_erro.emit()
        
    # --- Etapa 5 ---
    def start_step5_taxonomy(self, sci_name):
        if sci_name in self.species_cache:
            print(f"[Orchestrator] Cache Hit em eBird Taxonomia para {sci_name}. Pulando Thread!")
            self._on_step5_finished(self.species_cache[sci_name])
            return

        config = carregar_config()
        token = config.get("ebird_api_key", "").strip() or os.environ.get("EBIRD_API_KEY", "").strip()
        
        if not token:
            print("[Orchestrator] Chave eBird ausente. Evitando instanciar Thread e usando fallback rápido.")
            fallback_res = {
                "nome_ingles": "Desconhecido", "classe": "Aves", "ordem": "Desconhecida",
                "familia": "Desconhecida", "ebird_code": "", "raridade_regional": "Não Avaliado (Fallback Local)", "link_ebird": ""
            }
            try:
                resp = requests.get(f"https://api.inaturalist.org/v1/taxa?q={sci_name}&is_active=true&rank=species", timeout=3)
                if resp.status_code == 200 and resp.json().get("results"):
                    taxon = resp.json()["results"][0]
                    fallback_res["nome_ingles"] = taxon.get("english_common_name", "Desconhecido")
                    for anc in taxon.get("ancestors", []):
                        if anc.get("rank") == "order": fallback_res["ordem"] = anc.get("name", "Desconhecida").capitalize()
                        elif anc.get("rank") == "family": fallback_res["familia"] = anc.get("name", "Desconhecida").capitalize()
            except Exception: pass
            
            self._on_step5_finished(fallback_res, sci_name=sci_name)
            return

        if self.ebird_worker: self.ebird_worker.deleteLater()
        self.ebird_worker = EBirdWorker(sci_name, lat=self.current_lat, lon=self.current_lon, parent=self)
        # Necessitamos injetar sci_name param em Lambda para caching posterior
        self.ebird_worker.finished.connect(lambda res: self._on_step5_finished(res, sci_name=sci_name))
        self.ebird_worker.start()
        
    def _on_step5_finished(self, results, sci_name=None):
        print("[Orchestrator] Etapa 5 Concluída.")
        if sci_name and sci_name not in self.species_cache:
            self.species_cache[sci_name] = results
            
        if self.session_logger:
            self.session_logger.atualizar_ultimo_registro({
                "nome_ingles": results.get("nome_ingles", ""),
                "classe": results.get("classe", "Aves"),
                "ordem": results.get("ordem", ""),
                "familia": results.get("familia", ""),
                "ebird_code": results.get("ebird_code", ""),
                "raridade_regional": results.get("raridade_regional", ""),
                "link_ebird": results.get("link_ebird", "")
            })
        self.step5_ebird_concluido.emit(results)
        
        # Aqui no futuro engatilharemos a Etapa 6
        # from modules.step6_persistence.exif_manager import EXIFManager
        # exif_manager = EXIFManager()
        # exif_manager.escrever_metadados_completos(image_path, self.session_logger.obter_ultimo_registro())
        print("[Orchestrator] Preparado para o EXIF Manager (v0.3.22 Placeholder).")
