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
        
        # Travas de Redundância v0.8.9
        self._last_geo_run = {"sci_name": None, "lat": None, "lon": None}
        
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
        """Atualiza estado geográfico sem disparar pipeline."""
        self.current_lat = lat
        self.current_lon = lon
        self.has_location = (lat is not None and lon is not None)
        
    def reset(self):
        """Interrompe todos os workers e limpa estado interno (v0.5.1)."""
        print("[Orchestrator] Reset total solicitado. Interrompendo workers...")
        
        workers = [
            self.id_worker, self.wiki_worker, self.iucn_worker, 
            self.geo_worker, self.audio_worker, self.ebird_worker
        ]
        
        for w in workers:
            if w and w.isRunning():
                try:
                    w.requestInterruption()
                    w.quit()
                    # w.wait(500) # Optional wait
                except: pass
                
        # Limpar referências
        self.id_worker = None
        self.wiki_worker = None
        self.iucn_worker = None
        self.geo_worker = None
        self.audio_worker = None
        self.ebird_worker = None
        
        self.current_lat = None
        self.current_lon = None
        self.has_location = False
        self._last_sci_name = None
        
    def start_cascade_from_step2(self, sci_name):
        """Inicia a cascata linear estrita 2->3->4->5 (v0.4.8)."""
        print(f"[Orchestrator] Iniciando cascata linear a partir da Etapa 2 para: {sci_name}")
        self._last_sci_name = sci_name # Sincronização v0.6.7
        self.start_step2_biology(sci_name)
        # As etapas seguintes (3, 4 e 5) serão disparadas sequencialmente pelos callbacks.

    def reprocessar_localizacao(self, lat, lon):
        """Atualiza coordenadas, invalida cache de áudio e reinicia busca geo-acústica."""
        # Trava de Redundância (v0.4.3)
        if self.current_lat == lat and self.current_lon == lon and self.has_location:
            # Só ignora se realmente já processamos este local com sucesso
            print("[Orchestrator] Localização já confirmada e idêntica. Ignorando redundância.")
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
        
        self._last_sci_name = nome_cientifico
        
        # REGISTRO CENTRALIZADO: ETAPA 1 (v0.4.6)
        conf_valor = dados_identificacao.get("confianca", "N/A")
        print(f"[Orchestrator] Etapa 1 Concluída. Espécie: {nome_cientifico} ({conf_valor})")
        
        if self.session_logger:
            self.session_logger.registrar_identificacao({
                 "nome_cientifico": nome_cientifico,
                 "status_msg": status_msg,
                 "confianca": conf_valor
            })

        # CASCATA LINEAR: Só inicia a Etapa 2 se a espécie for válida (v0.6.1)
        # Bloqueia explicitamente nomes genéricos ou falhas de confiança
        if nome_cientifico == "Identificação Inconclusiva" or status_msg == "Baixa confiança":
            print("[Orchestrator] Identificação Inconclusiva detectada. Interrompendo cascata automática.")
            return

        print(f"[Orchestrator] Espécie validada. Iniciando cascata para: {nome_cientifico}")
        self.start_step2_biology(nome_cientifico)
            
    # --- Etapa 2 ---
    def start_step2_biology(self, sci_name):
        if self.wiki_worker: self.wiki_worker.deleteLater()
        self.wiki_worker = BuscadorWorker(sci_name, parent=self)
        self.wiki_worker.info_found.connect(self._on_step2_finished)
        self.wiki_worker.error_occurred.connect(self.step2_wiki_erro)
        self.wiki_worker.start()
        
    def _on_step2_finished(self, resultados):
        cons = resultados.get("status_conservacao", "N/A")
        print(f"[Orchestrator] Etapa 2 (Biologia) Concluída. Conservação: {cons}")
        
        if self.session_logger:
            self.session_logger.atualizar_ultimo_registro(resultados)
        self.step2_wiki_concluida.emit(resultados)
        
        # CASCATA LINEAR CONTINUA: 2 -> 3
        if self._last_sci_name:
            self.start_step3_geography(self._last_sci_name)
        
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
        # Trava de Redundância Atômica v0.8.9
        if (self._last_geo_run["sci_name"] == sci_name and 
            self._last_geo_run["lat"] == self.current_lat and 
            self._last_geo_run["lon"] == self.current_lon):
            print(f"[Orchestrator] Geografia para {sci_name} já processada nesta posição. Ignorando disparo redundante.")
            return

        self._last_geo_run = {"sci_name": sci_name, "lat": self.current_lat, "lon": self.current_lon}
        self._last_sci_name = sci_name
        
        if self.iucn_worker:
            try:
                self.iucn_worker.finished.disconnect()
                # Não deletamos imediatamente se estiver rodando para evitar crash
                if not self.iucn_worker.isRunning():
                    self.iucn_worker.deleteLater()
            except: pass
            
        self.iucn_worker = IUCNWorker(sci_name, parent=self)
        self.iucn_worker.finished.connect(self._on_step3_finished)
        self.iucn_worker.start()

        # 3B. GeoAnalyst (Nominatim/Pampa) - Sempre roda se tivermos coords ou para centroide
        if self.current_lat and self.current_lon:
            if self.geo_worker:
                try:
                    self.geo_worker.finished.disconnect()
                    # Não deletamos imediatamente se estiver rodando v0.8.9
                    if not self.geo_worker.isRunning():
                        self.geo_worker.deleteLater()
                except: pass
                
            self.geo_worker = GeoWorker(self.current_lat, self.current_lon, parent=self)
            self.geo_worker.finished.connect(self._on_step3_geo_finished)
            self.geo_worker.start()
        else:
            print("[Orchestrator] Lat/Lon ausentes. Saltando Etapa 3-Geo e prosseguindo para Etapa 4 (v0.4.8).")
            # REGISTRO DE DADOS AUSENTES (v0.4.6/0.4.8)
            if self.session_logger:
                self.session_logger.atualizar_ultimo_registro({
                    "municipio": "Não informado", "estado": "N/A", "bioma": "Não mapeado"
                })
            # Engatilha a próxima etapa imediatamente para não quebrar a corrente linear
            self.start_step4_vocalization(sci_name)

    def _on_step3_geo_finished(self, details):
        mun = details.get('municipio', 'N/D')
        uf = details.get('estado', 'N/D')
        bio = details.get('bioma', 'N/D')
        print(f"[Orchestrator] Etapa 3 (Geo) Concluída. Local: {mun}-{uf}, Bioma: {bio}")
        
        # Atualiza coordenadas do Orchestrator com a precisão do Analyst (centroide se necessário)
        self.current_lat = details.get('lat')
        self.current_lon = details.get('lon')
        
        # REGISTRO INTEGRAL: ETAPA 3 (v0.4.6)
        if self.session_logger:
            self.session_logger.atualizar_ultimo_registro(details)
            
        self.step3_geo_concluida.emit(details)
        
        # DISPARO SEQUENCIAL DO ÁUDIO (Blindagem v0.4.5)
        # O áudio só é buscado após o GeoAnalyst garantir as coordenadas precisas.
        if self._last_sci_name:
            print(f"[Orchestrator] Step 3 (Geo) resolvido. Engatilhando Step 4 (Áudio) para {self._last_sci_name}")
            self.start_step4_vocalization(self._last_sci_name)

    def _on_step3_finished(self, results):
        iucn = results.get("iucn_status", "Indisponível")
        print(f"[Orchestrator] Etapa 3 (IUCN) Concluída. Status: {iucn}")
        if self.session_logger:
            self.session_logger.atualizar_ultimo_registro({"iucn_status": iucn})
        self.step3_iucn_concluida.emit(results)
        
    # --- Etapa 4 ---
    def start_step4_vocalization(self, sci_name):
        if not hasattr(self, '_cache_audio'):
            self._cache_audio = {}
            
        if sci_name in self._cache_audio:
            print(f"[Orchestrator] Cache Hit em Áudio para {sci_name}. Sincronizando UI e Mapa.")
            audios = self._cache_audio[sci_name]
            self.step4_audio_concluido.emit(audios)
            self.audio_processed.emit(audios) # Garantir plotagem no mapa em cache hit (v0.4.32)
            return
            
        if self.audio_worker: self.audio_worker.deleteLater()
        
        # Extrair dados regionais da caderneta de campo (SessionLogger) se disponíveis
        municipio = None
        estado = None
        bioma = None
        pais = None
        if self.session_logger and self.session_logger.buffer:
            ultimo_registro = self.session_logger.buffer[-1]
            municipio = ultimo_registro.get("municipio")
            estado = ultimo_registro.get("estado")
            bioma = ultimo_registro.get("bioma")
            pais = ultimo_registro.get("pais")
            
            # Validação para evitar valores genéricos
            if municipio in ["Não identificado", "Não informado", "N/D"]: municipio = None
            if estado in ["Não identificado", "Não informado", "N/D", "N/A"]: estado = None

        print(f"[Orchestrator] Iniciando busca de áudio regionalizada para {sci_name}")
        print(f"               Contexto: {municipio}-{estado} | Bioma: {bioma} | País: {pais}")
        self.audio_worker = AudioWorker(
            sci_name, 
            lat=self.current_lat, 
            lon=self.current_lon, 
            municipio=municipio,
            estado=estado,
            bioma=bioma,
            pais=pais,
            parent=self
        )
        
        # Conectar sinal com wrapper (lambda) para interceptar o save state
        self.audio_worker.audio_found.connect(lambda audios: self._on_step4_finished_intercept(sci_name, audios))
        self.audio_worker.search_failed.connect(lambda: self._on_step4_failed_intercept(sci_name))
        self.audio_worker.start()

    def _on_step4_finished_intercept(self, sci_name, audios):
        if sci_name:
            self._cache_audio[sci_name] = audios
            print(f"[Orchestrator] Etapa 4 (Áudio) Concluída. Encontrados {len(audios)} vocalizações para {sci_name}")
        
        # Registrar Vocalização e Auditoria (v0.9.6)
        if self.session_logger:
            vocal_data = {"vocalizacoes": len(audios)}
            for i, audio in enumerate(audios[:3]):
                key = f"vocal_top{i+1}"
                vocal_data[key] = {
                    "id": audio.get("id_original") or audio.get("id"),
                    "distancia_km": audio.get("distancia_km"),
                    "localidade": audio.get("audit_geo"),
                    "camada": audio.get("camada"),
                    "link_registro": audio.get("link_observacao"),
                    "link_audio": audio.get("link_audio")
                }
            self.session_logger.atualizar_ultimo_registro(vocal_data)
            
        self.step4_audio_concluido.emit(audios)
        self.audio_processed.emit(audios) # Emitir para plotagem externa (v0.4.3)
        
        # CASCATA LINEAR CONTINUA: 4 -> 5
        if sci_name:
            self.start_step5_taxonomy(sci_name)
        
    def _on_step4_failed_intercept(self, sci_name):
        # Cache negative hit (v0.4.5)
        if sci_name:
             self._cache_audio[sci_name] = []
        
        print(f"[Orchestrator] Etapa 4 (Áudio) Falhou. Nenhuma vocalização encontrada para {sci_name}")
        if self.session_logger:
             self.session_logger.atualizar_ultimo_registro({"vocalizacoes": 0})
             
        self.step4_audio_erro.emit()
        
        # CASCATA LINEAR CONTINUA mesmo em falha: 4 -> 5
        if sci_name:
            self.start_step5_taxonomy(sci_name)
        
    # --- Etapa 5 ---
    def start_step5_taxonomy(self, sci_name):
        if sci_name in self.species_cache:
            print(f"[Orchestrator] Cache Hit em eBird Taxonomia para {sci_name}. Pulando Thread!")
            self._on_step5_finished(self.species_cache[sci_name])
            return

        if self.ebird_worker: self.ebird_worker.deleteLater()
        self.ebird_worker = EBirdWorker(sci_name, lat=self.current_lat, lon=self.current_lon, parent=self)
        # Necessitamos injetar sci_name param em Lambda para caching posterior
        self.ebird_worker.finished.connect(lambda res: self._on_step5_finished(res, sci_name=sci_name))
        self.ebird_worker.start()
        
    def _on_step5_finished(self, results, sci_name=None):
        fam = results.get("familia", "N/D")
        ordem = results.get("ordem", "N/D")
        print(f"[Orchestrator] Etapa 5 (Taxonomia) Concluída. Família: {fam}, Ordem: {ordem}")
        
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
        
        # Batch Flush Finalizado (v0.4.4)
        if self.session_logger:
            self.session_logger.flush()
        
        # Aqui no futuro engatilharemos a Etapa 6
        # from modules.step6_persistence.exif_manager import EXIFManager
        # exif_manager = EXIFManager()
        # exif_manager.escrever_metadados_completos(image_path, self.session_logger.obter_ultimo_registro())
        print("[Orchestrator] Preparado para o EXIF Manager (v0.3.22 Placeholder).")
