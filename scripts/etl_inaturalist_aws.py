#  iBirder -  IA para Birdwatching
#  Copyright (C) 2026  Kuriakin Humberto Toscan
#  Script de ETL: Extração de Dados do iNaturalist Open Data (AWS S3)

import os
import sys
import gzip
import csv
import urllib.request
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

BASE_DIR = Path(__file__).parent.parent
DATASET_DIR = BASE_DIR / "dataset_inaturalist"
DATASET_DIR.mkdir(parents=True, exist_ok=True)

TAXA_URL = "https://inaturalist-open-data.s3.amazonaws.com/taxa.csv.gz"
PHOTOS_URL = "https://inaturalist-open-data.s3.amazonaws.com/photos.csv.gz"

def download_if_not_exists(url, local_path):
    if not local_path.exists():
        logging.info(f"Baixando {url} para {local_path}...")
        urllib.request.urlretrieve(url, local_path)
        logging.info(f"Download de {local_path.name} concluído.")
    else:
        logging.info(f"Arquivo já existe: {local_path}")

def filtrar_aves_neotropicais():
    """
    Filtra as espécies da Classe Aves (taxon_id 3) no catálogo do iNaturalist.
    """
    taxa_gz = DATASET_DIR / "taxa.csv.gz"
    download_if_not_exists(TAXA_URL, taxa_gz)

    aves_ids = set()
    aves_taxonomy = {}

    logging.info("Processando arquivo de taxonomia (taxa.csv.gz)...")
    with gzip.open(taxa_gz, mode="rt", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            taxon_id = row.get("taxon_id")
            rank = row.get("rank")
            ancestry = (row.get("ancestry") or "").split("/")
            name = row.get("name")
            active = row.get("active")

            # Taxon ID 3 é o nó raiz da Classe Aves no iNaturalist
            if rank == "species" and "3" in ancestry and active == "true":
                aves_ids.add(taxon_id)
                aves_taxonomy[taxon_id] = name

    logging.info(f"Total de espécies de Aves identificadas no iNaturalist: {len(aves_ids)}")
    return aves_ids, aves_taxonomy

if __name__ == "__main__":
    logging.info("=== Iniciando Pipeline ETL iNaturalist AWS Open Data ===")
    aves_ids, taxonomy = filtrar_aves_neotropicais()
    logging.info(f"Extração de metadados concluída com sucesso! ({len(aves_ids)} espécies mapeadas).")
