import requests
import logging
from urllib.parse import quote
import re

class INaturalistClient:
    API_URL = "https://api.inaturalist.org/v1/taxa"

    def __init__(self):
        self.session = requests.Session()
        self.headers = {
            'User-Agent': 'iBirder/1.0 (Integration; +https://github.com/KuriakinToscan/iBirder)'
        }
        self.session.headers.update(self.headers)

    def _clean_html(self, raw_html):
        """Remove tags HTML e limpa o texto."""
        if not raw_html:
            return ""
        # Remove tags HTML
        clean_text = re.sub(r'<[^>]+>', '', raw_html)
        # Remove espaços extras
        clean_text = re.sub(r'\s+', ' ', clean_text).strip()
        return clean_text

    def get_species_info(self, scientific_name):
        """
        Busca informações da espécie na API do iNaturalist.
        Retorna uma tupla (descrição, nome_popular, fonte_url).
        """
        try:
            params = {
                'q': scientific_name,
                'locale': 'pt-BR',
                'rank': 'species',
                'per_page': 1
            }
            
            response = self.session.get(self.API_URL, params=params, timeout=10)
            
            if response.status_code != 200:
                logging.error(f"[INATURALIST] Erro API: {response.status_code}")
                return "Serviço indisponível no momento.", None, None

            data = response.json()
            results = data.get('results', [])
            
            if not results:
                return "Espécie não encontrada no iNaturalist.", None, None

            taxon = results[0]
            
            # Extração de dados
            description_html = taxon.get('wikipedia_summary', '')
            description = self._clean_html(description_html)
            
            if not description:
                description = "Descrição não disponível nesta fonte."

            common_name = taxon.get('preferred_common_name', '').title()
            
            # URL da espécie no iNaturalist (para o botão 'Abrir Fonte')
            source_url = f"https://www.inaturalist.org/taxa/{taxon.get('id')}"

            return description, common_name, source_url

        except requests.exceptions.RequestException as e:
            logging.error(f"[INATURALIST] Erro de conexão: {e}")
            return None, None, None
        except Exception as e:
            logging.error(f"[INATURALIST] Erro inesperado: {e}")
            return "Ocorreu um erro ao processar os dados.", None, None
