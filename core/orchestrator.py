import os
from PySide6.QtCore import QObject, Signal

# Importações dos Workers das Etapas
from modules.step1_identity.id_worker import LocalIdentificationWorker
from modules.step2_biology.wiki_worker import BuscadorWorker
from modules.step3_geography.iucn_worker import IUCNWorker
from modules.step4_vocalization.audio_worker import AudioWorker
from modules.step5_taxonomy.ebird_worker import EBirdWorker
import requests
from core.config import carregar_config

# Etapa 6 placeholder
# from modules.step6_persistence.exif_manager import EXIFManager

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
    
    step4_audio_concluido = Signal(list)
    step4_audio_erro = Signal()
    
    step5_ebird_concluido = Signal(dict)

    def __init__(self, session_logger, parent=None):
        super().__init__(parent)
        self.session_logger = session_logger
        
        # Referências seguras para as threads
        self.id_worker = None
        self.wiki_worker = None
        self.iucn_worker = None
        self.audio_worker = None
        self.ebird_worker = None
        
        self.species_cache = {} # Cache de taxonomia e geografia RAM
        
        # Estado Geográfico Armazenado pelo Pipeline
        self.current_lat = None
        self.current_lon = None
        
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
        
    def start_cascade_from_step2(self, sci_name):
        """Dispara todas as etapas (2 a 5) paralelamente a partir de um nome manual."""
        print(f"[Orchestrator] Iniciando cascata a partir da Etapa 2 para: {sci_name}")
        self.start_step2_biology(sci_name)
        self.start_step3_geography(sci_name)
        self.start_step4_vocalization(sci_name)
        self.start_step5_taxonomy(sci_name)

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
        
        # Se passou o guard, Engatilha Paralelamente o Resto do Pentágono
        self.start_step2_biology(nome_cientifico)
        self.start_step3_geography(nome_cientifico)
        self.start_step4_vocalization(nome_cientifico)
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
        
    # --- Etapa 3 ---
    def start_step3_geography(self, sci_name):
        config = carregar_config()
        token = config.get("iucn_api_key", "").strip() or os.environ.get("TOKEN_IUCN", "").strip()
        
        if not token:
            print("[Orchestrator] Chave IUCN ausente. Evitando instanciar Thread e usando fallback rápido.")
            fallback_res = {
                "iucn_status": "Não Avaliado (Fallback Local)",
                "geojson_path": None,
                "link_iucn": f"https://www.iucnredlist.org/search?query={sci_name.replace(' ', '+')}&searchType=species"
            }
            # Fallback síncrono ultra-rápido iNaturalist
            try:
                resp = requests.get(f"https://api.inaturalist.org/v1/taxa?q={sci_name}&is_active=true&rank=species", timeout=3)
                if resp.status_code == 200 and resp.json().get("results"):
                    cs = resp.json()["results"][0].get("conservation_status")
                    fallback_res["iucn_status"] = f"{cs.get('status', 'Não Avaliado').upper()} (via iNaturalist)" if cs else "Não Avaliado / Seguro (via iNaturalist)"
            except Exception: pass
            
            self._on_step3_finished(fallback_res)
            return

        if self.iucn_worker: self.iucn_worker.deleteLater()
        self.iucn_worker = IUCNWorker(sci_name, parent=self)
        self.iucn_worker.finished.connect(self._on_step3_finished)
        self.iucn_worker.start()
        
    def _on_step3_finished(self, results):
        print("[Orchestrator] Etapa 3 Concluída.")
        self.step3_iucn_concluida.emit(results)
        
    # --- Etapa 4 ---
    def start_step4_vocalization(self, sci_name):
        if self.audio_worker: self.audio_worker.deleteLater()
        self.audio_worker = AudioWorker(sci_name, lat=self.current_lat, lon=self.current_lon, parent=self)
        self.audio_worker.audio_found.connect(self.step4_audio_concluido)
        self.audio_worker.search_failed.connect(self.step4_audio_erro)
        self.audio_worker.start()
        
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
