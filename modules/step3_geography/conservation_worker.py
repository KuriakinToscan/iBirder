import requests
from PySide6.QtCore import QThread, Signal

class NationalConservationWorker(QThread):
    """
    Worker especializado em consolidar dados de conservação:
    1. JBRJ (Endemismo e Ocorrência)
    2. ICMBio/SALVE (Status Nacional por Extenso)
    3. CITES (Comércio Internacional)
    """
    finished = Signal(dict)
    error_occurred = Signal(str)

    # Dicionário de Tradução de Status (Sigla -> Extenso em Português)
    TRADUCAO_STATUS = {
        "EX": "Extinta",
        "EW": "Extinta na Natureza",
        "CR": "Criticamente em Perigo",
        "EN": "Em Perigo",
        "VU": "Vulnerável",
        "NT": "Quase Ameaçada",
        "LC": "Pouco Preocupante",
        "DD": "Dados Insuficientes",
        "NE": "Não Avaliada"
    }

    def __init__(self, scientific_name, country="Brazil", parent=None):
        super().__init__(parent)
        self.scientific_name = scientific_name
        self.country = country or "Brazil"

    def run(self):
        print(f"[ConservationWorker] Iniciando análise para: {self.scientific_name} (País: {self.country})")
        
        results = {
            "status_icmbio": "Não Avaliado",
            "status_cites": "Não Listado",
            "endemismo": "Não",
            "msg_distribuicao": "Distribuição padrão",
            "is_brazil": self.country.lower() in ["brazil", "brasil"]
        }

        try:
            # 1. Busca CITES (Global)
            self._fetch_cites_status(results)

            # 2. Busca Específica Brasil (JBRJ + ICMBio/SALVE)
            if results["is_brazil"]:
                self._fetch_brazilian_data(results)
            else:
                results["status_icmbio"] = "Informação Não Disponível (Registro Internacional)"
            
            self.finished.emit(results)
        except Exception as e:
            print(f"[ConservationWorker] Erro: {e}")
            self.error_occurred.emit(str(e))

    def _fetch_cites_status(self, results):
        """Busca status na API do Species+/CITES (Simulação/Fallback iNaturalist)."""
        # Em v1.0.0 usamos o iNaturalist como proxy para CITES quando disponível
        try:
            url = f"https://api.inaturalist.org/v1/taxa?q={self.scientific_name}"
            resp = requests.get(url, timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("results"):
                    taxon = data["results"][0]
                    # Algumas taxonomias no iNat marcam CITES em 'conservation_statuses'
                    statuses = taxon.get("conservation_statuses", [])
                    for s in statuses:
                        if s.get("authority", "").upper() == "CITES":
                            results["status_cites"] = f"Anexo {s.get('status')}"
        except: pass

    def _fetch_brazilian_data(self, results):
        """Busca dados oficiais do catálogo brasileiro."""
        try:
            # Consulta ao Catálogo Taxonômico (JBRJ) - Simulado via API iNaturalist / Proxy
            # No futuro, aqui consultaria o dataset oficial do Zenodo/JBRJ
            url = f"https://api.inaturalist.org/v1/taxa?q={self.scientific_name}&place_id=6857" # ID 6857 = Brasil
            resp = requests.get(url, timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("results"):
                    taxon = data["results"][0]
                    
                    # 1. Endemismo
                    if taxon.get("endemic"):
                        results["endemismo"] = "Sim"
                    
                    # 2. Status ICMBio (SALVE)
                    cs = taxon.get("conservation_status", {})
                    if cs and cs.get("authority", "").lower() in ["icmbio", "brazil"]:
                        sigla = cs.get("status", "NE").upper()
                        results["status_icmbio"] = self.TRADUCAO_STATUS.get(sigla, sigla)
        except: pass

    @staticmethod
    def traduzir_iucn(sigla):
        """Utilitário para traduzir siglas IUCN para extenso."""
        sigla_clean = sigla.split('(')[0].strip().upper() if sigla else "NE"
        return NationalConservationWorker.TRADUCAO_STATUS.get(sigla_clean, sigla)
