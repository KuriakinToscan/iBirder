import requests

def get_gbif_taxon_key(scientific_name):
    print(f"[GBIF] Buscando ID para: {scientific_name}")
    url = "https://api.gbif.org/v1/species/match"
    params = {"name": scientific_name, "kingdom": "Animalia"}
    
    try:
        response = requests.get(url, params=params, timeout=5)
        if response.status_code == 200:
            data = response.json()
            if "usageKey" in data:
                print(f"[GBIF] ID Encontrado: {data['usageKey']}")
                return data["usageKey"]
    except Exception as e:
        print(f"Error fetching GBIF key: {e}")
        
    print("[GBIF] ID não encontrado.")
    return None
