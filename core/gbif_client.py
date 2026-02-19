import requests

def get_gbif_taxon_key(scientific_name):
    """Obtém o usageKey da espécie na API do GBIF."""
    try:
        url = "https://api.gbif.org/v1/species/match"
        params = {"name": scientific_name, "kingdom": "Animalia", "class": "Aves"}
        response = requests.get(url, params=params, timeout=3)
        if response.status_code == 200:
            data = response.json()
            if "usageKey" in data: return data["usageKey"]
        return None
    except Exception: return None
