#  iBirder -  IA para Birdwatching
#  Copyright (C) 2026  Kuriakin Humberto Toscan
#
#  Este programa é um software livre: você pode redistribuí-lo e/ou
#  modificá-lo sob os termos da Licença Pública Geral GNU conforme
#  publicada pela Free Software Foundation, tanto a versão 3 da
#  Licença, como (a seu critério) qualquer versão posterior.
#
#  Este programa é distribuído na esperança de que possa ser útil,
#  mas SEM NENHUMA GARANTIA; sem uma garantia implícita de
#  ADEQUAÇÃO A QUALQUER MERCADO OU APLICAÇÃO EM PARTICULAR.
#  Veja a Licença Pública Geral GNU para mais detalhes.
#
#  Você deve ter recebido uma cópia da Licença Pública Geral GNU
#  junto com este programa. Se não, veja <https://www.gnu.org/licenses/>.

"""
Arquivos da IA local.

- BioCLIP (o modelo do app, desde a v1.5): ~90 MB, grande demais para o repositório. Fica numa
  Release própria do GitHub ("modelo-bioclip-N", marcada como pré-lançamento para não virar a
  "última versão" do aviso de atualização) e é descrito em assets/models/bioclip_modelo.json
  (versionado: nome, tamanho e SHA-256 de cada arquivo). O build do instalador baixa e confere
  os arquivos (python -m core.model_manager); quem roda pelo ZIP baixa na primeira identificação.
- MobileNetV2 "Birds V1" (Google AIY, até a v1.4): fica no repositório só como referência da
  avaliação (tools/avaliar_identificacao.py); não vai para o instalador (ibirder.spec).
"""

import hashlib
import json
import logging
import sys
from pathlib import Path
from typing import Callable, Dict, Optional

import requests

from core.paths import APP_DIR

PASTA_MODELOS = APP_DIR / "assets" / "models"
MANIFESTO_BIOCLIP = PASTA_MODELOS / "bioclip_modelo.json"


def sha256_arquivo(caminho: Path) -> str:
    h = hashlib.sha256()
    with open(caminho, "rb") as f:
        for bloco in iter(lambda: f.read(1 << 20), b""):
            h.update(bloco)
    return h.hexdigest()


class ModelManager:
    def __init__(self, pasta_modelos: Optional[Path] = None):
        self.assets_dir = Path(pasta_modelos) if pasta_modelos else PASTA_MODELOS
        self.manifesto_path = self.assets_dir / MANIFESTO_BIOCLIP.name
        self.bioclip_dir = self.assets_dir / "bioclip"
        # Referência da avaliação (MobileNetV2), fora do instalador
        self.model_path = self.assets_dir / "inat_vision_small.tflite"
        self.labels_path = self.assets_dir / "inat_labels.txt"

    def manifesto(self) -> Dict:
        """Conteúdo de bioclip_modelo.json: {"url_base": ..., "arquivos": {nome: {"bytes", "sha256"}}}."""
        dados = json.loads(self.manifesto_path.read_text(encoding="utf-8"))
        if not dados.get("arquivos") or not dados.get("url_base"):
            raise ValueError(f"{self.manifesto_path.name} sem 'arquivos' ou 'url_base'.")
        return dados

    def check_resources(self) -> bool:
        """True se todos os arquivos do BioCLIP estão na pasta com o tamanho esperado (SHA-256 só no download)."""
        try:
            arquivos = self.manifesto()["arquivos"]
        except (OSError, ValueError) as e:
            logging.error(f"Manifesto do modelo ilegível: {e}")
            return False
        for nome, dados in arquivos.items():
            caminho = self.bioclip_dir / nome
            if not caminho.is_file() or caminho.stat().st_size != int(dados["bytes"]):
                return False
        return True

    def download_resources(self, callback: Optional[Callable[[str], None]] = None) -> bool:
        """
        Baixa da Release os arquivos ausentes ou com tamanho errado, confere o SHA-256 e só então
        os coloca no lugar. ``callback(str)`` recebe mensagens de progresso.
        """
        try:
            manifesto = self.manifesto()
            self.bioclip_dir.mkdir(parents=True, exist_ok=True)
            for nome, dados in manifesto["arquivos"].items():
                destino = self.bioclip_dir / nome
                if destino.is_file() and destino.stat().st_size == int(dados["bytes"]):
                    continue
                self._baixar(manifesto["url_base"].rstrip("/") + "/" + nome, destino, dados, callback)
            return True
        except Exception as e:
            logging.error(f"Erro no download do modelo de IA: {e}")
            if callback:
                callback(f"Erro no download: {e}")
            return False

    @staticmethod
    def _baixar(url: str, destino: Path, dados: Dict, callback) -> None:
        esperado, tamanho = dados["sha256"].lower(), int(dados["bytes"])
        parcial = destino.with_name(destino.name + ".parcial")
        logging.info(f"Baixando {url} ({tamanho / 1e6:.0f} MB)")
        h, baixado, ultimo = hashlib.sha256(), 0, -1
        with requests.get(url, stream=True, timeout=60, headers={"User-Agent": "iBirder"}) as resposta:
            resposta.raise_for_status()
            with open(parcial, "wb") as f:
                for bloco in resposta.iter_content(chunk_size=1 << 20):
                    f.write(bloco)
                    h.update(bloco)
                    baixado += len(bloco)
                    pct = int(100 * baixado / tamanho) if tamanho else 0
                    if callback and pct // 10 != ultimo:
                        ultimo = pct // 10
                        callback(f"Baixando o modelo de IA, só na 1ª vez ({min(pct, 100)}%)...")
        if baixado != tamanho or h.hexdigest() != esperado:
            parcial.unlink(missing_ok=True)
            raise ValueError(f"{destino.name}: arquivo baixado não confere ({baixado} bytes, "
                             f"SHA-256 {h.hexdigest()[:12]}...; esperado {tamanho} bytes, {esperado[:12]}...)")
        parcial.replace(destino)
        logging.info(f"Modelo conferido: {destino}")


def main() -> int:
    """python -m core.model_manager: baixa e confere (SHA-256) o BioCLIP; usado pelo build do instalador."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    gerente = ModelManager()
    if not gerente.download_resources(callback=print):
        return 1
    erros = 0
    for nome, dados in gerente.manifesto()["arquivos"].items():
        caminho = gerente.bioclip_dir / nome
        sha = sha256_arquivo(caminho)
        confere = sha == dados["sha256"].lower()
        erros += not confere
        logging.info(f"{nome}: {caminho.stat().st_size / 1e6:.1f} MB, SHA-256 {sha} "
                     f"{'(confere)' if confere else '(NÃO CONFERE com o manifesto)'}")
    return 1 if erros else 0


if __name__ == "__main__":
    sys.exit(main())
