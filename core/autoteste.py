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
Autoteste de inicialização (python main.py --smoke-test / iBirder.exe --smoke-test).

Abre o app completo e, após alguns segundos, confere os componentes que o
instalador precisa levar. Encerra com código 0 (tudo certo) ou 1 (falha).
Usado pelo GitHub Actions para validar o executável gerado.
"""

import json
import logging
import platform
import subprocess

from core.paths import APP_DIR


def _modelo():
    from modules.step1_identity.id_worker import tflite
    if tflite is None:
        raise RuntimeError("runtime TFLite (ai-edge-litert) ausente")
    interp = tflite.Interpreter(model_path=str(APP_DIR / "assets" / "models" / "inat_vision_small.tflite"))
    interp.allocate_tensors()
    rotulos = (APP_DIR / "assets" / "models" / "inat_labels.txt").read_text(encoding="utf-8").splitlines()
    saida = interp.get_output_details()[0]["shape"][-1]
    if saida != len([r for r in rotulos if r.strip()]):
        raise RuntimeError(f"modelo com {saida} saídas e {len(rotulos)} rótulos")
    return f"{saida} espécies"


def _exiftool():
    exe = APP_DIR / "assets" / "exiftool" / "exiftool.exe"
    if not exe.exists():
        raise FileNotFoundError(exe)
    if platform.system() != "Windows":
        return "presente (execução só no Windows)"
    r = subprocess.run([str(exe), "-ver"], capture_output=True, text=True, timeout=60)
    if r.returncode != 0:
        raise RuntimeError(r.stderr.strip())
    return f"versão {r.stdout.strip()}"


def _biomas():
    from modules.step3_geography.geo_analyst import GeoAnalyst
    bioma = GeoAnalyst().get_biome(-23.55, -46.63)
    if bioma != "Mata Atlântica":
        raise RuntimeError(f"São Paulo resultou em {bioma!r}")
    return "São Paulo -> Mata Atlântica"


def _ebird():
    from modules.step5_taxonomy import ebird_taxonomy
    r = ebird_taxonomy.buscar("Pitangus sulphuratus")
    if not r or r["species_code"] != "grekis":
        raise RuntimeError("tabela eBird ausente ou inválida")
    return "Pitangus sulphuratus -> grekis"


def _guia():
    json.loads((APP_DIR / "assets" / "models" / "model_meta.json").read_text(encoding="utf-8"))
    for arquivo in ("guia_do_usuario.md", "manual_apis_nuvem.md"):
        if not (APP_DIR / arquivo).exists():
            raise FileNotFoundError(arquivo)
    return "manuais e metadados presentes"


VERIFICACOES = [
    ("Modelo de IA", _modelo),
    ("ExifTool", _exiftool),
    ("Biomas (IBGE)", _biomas),
    ("Taxonomia eBird", _ebird),
    ("Manuais", _guia),
]


def executar_smoke_test():
    """Executa as verificações, registra no log/console e retorna o código de saída."""
    falhas = 0
    for nome, verificar in VERIFICACOES:
        try:
            detalhe = verificar()
            msg = f"[SMOKE] OK    {nome}: {detalhe}"
        except Exception as e:
            falhas += 1
            msg = f"[SMOKE] FALHA {nome}: {e!r}"
        logging.info(msg)
        print(msg, flush=True)
    resultado = "SUCESSO" if falhas == 0 else f"{falhas} FALHA(S)"
    logging.info(f"[SMOKE] Resultado: {resultado}")
    print(f"[SMOKE] Resultado: {resultado}", flush=True)
    return 0 if falhas == 0 else 1
