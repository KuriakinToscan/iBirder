import requests
import logging

def get_gbif_taxon_key(scientific_name):
    logging.debug(f"Buscando GBIF Taxon Key para: {scientific_name}")
    url = "https://api.gbif.org/v1/species/match"
    # Strict matching helps avoid bad fuzzy matches.
    # Verbose=true provides more context if needed, but standard match response usually suffices.
    params = {
        "name": scientific_name, 
        "kingdom": "Animalia", 
        "strict": "true",
        "verbose": "false" 
    }
    
    try:
        response = requests.get(url, params=params, timeout=5)
        if response.status_code == 200:
            data = response.json()
            
            # Check for usageKey (direct or accepted)
            # 'acceptedUsageKey' points to the valid taxon if the matched name is a synonym.
            # 'usageKey' is the key of the taxon matched (could be synonym or accepted).
            # We prefer 'acceptedUsageKey' if present to link to the valid species page.
            key = data.get("acceptedUsageKey") or data.get("usageKey")
            
            if key:
                logging.debug(f"ID GBIF Encontrado: {key}")
                return key
            else:
                logging.debug(f"Nenhum ID GBIF encontrado para {scientific_name}")
                
    except Exception as e:
        logging.error(f"Erro ao buscar chave GBIF: {e}")
        
    return None
