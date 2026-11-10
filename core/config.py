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

import json
import logging
import os
from core.paths import BASE_DIR

CONFIG_FILE = "config.json"
APP_VERSION = "1.4"  # fonte única da versão (instalador, CI, interface, logs)

def obter_caminho_config():
    """Retorna o caminho absoluto para o arquivo de configuração."""
    return BASE_DIR / CONFIG_FILE

def carregar_config():
    """Carrega a configuração local ou retorna padrão."""
    config_path = obter_caminho_config()
    default_config = {
        "pular_pergunta_atalho": False,
        "modo_operacao": None, # "online" ou "offline"
        "lembrar_modo": False,
        "xc_api_key": "",
        "inat_api_token": "",
        "google_vision_api_key": "",
        # Publicação no iNaturalist (core/inat_oauth.py, issue #9): token OAuth do login no
        # navegador, ID do aplicativo (vazio = o embarcado) e licença padrão da observação
        "inat_oauth_token": "",
        "inat_app_id": "",
        "inat_licenca_observacao": "CC-BY",
        # Aviso de novas versões (core/verificacao_versao.py)
        "verificar_atualizacoes": True,
        "ultima_verificacao_versao": "",
        "versao_ignorada": "",
        # Tema visual (core/temas.py): "offwhite", "clean" ou "classico"
        "tema": "offwhite",
        # Arrumação da janela principal (ui/layouts/)
        "layout": "completo"
    }
    
    if config_path.exists():
        try:
            # utf-8-sig: aceita o BOM que o Bloco de Notas pode gravar ao editar o arquivo
            with open(config_path, "r", encoding="utf-8-sig") as f:
                user_config = json.load(f)
            if not isinstance(user_config, dict):
                raise ValueError("o conteúdo não é um objeto JSON")
            # Merge com default para garantir que chaves novas existam
            default_config.update(user_config)
        except ValueError as e:
            # JSON inválido ou texto que não é UTF-8 (UnicodeDecodeError). Sem guardar a cópia,
            # o próximo salvar_config gravaria o padrão por cima e apagaria as chaves.
            _guardar_config_corrompido(config_path, e)
        except OSError as e:
            logging.error(f"Não foi possível ler a configuração ({e}); usando o padrão nesta leitura.")

    return default_config


# Caminho da cópia do último config ilegível (a janela principal avisa o usuário ao abrir)
config_corrompido = None


def _guardar_config_corrompido(config_path, erro):
    """Renomeia o config ilegível para config.json.corrompido(-N) e registra no log."""
    global config_corrompido
    destino = config_path.with_name(config_path.name + ".corrompido")
    n = 1
    while destino.exists():
        n += 1
        destino = config_path.with_name(f"{config_path.name}.corrompido-{n}")
    try:
        os.replace(config_path, destino)
        config_corrompido = destino
        logging.error(f"Configuração ilegível ({erro}). Cópia guardada em {destino}; "
                      "o app volta às configurações padrão e as chaves de API precisam ser informadas de novo.")
    except OSError as e:
        logging.error(f"Configuração ilegível ({erro}) e não foi possível guardar a cópia: {e}")


def salvar_config(config):
    """
    Salva a configuração local de forma atômica: grava um arquivo temporário na mesma
    pasta e troca pelo definitivo com os.replace (uma queda no meio não deixa o
    config.json pela metade).
    """
    config_path = obter_caminho_config()
    temporario = config_path.with_name(config_path.name + ".tmp")
    try:
        with open(temporario, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temporario, config_path)
        from core.logger import atualizar_segredos
        atualizar_segredos(config)  # novas chaves passam a ser mascaradas nos logs
    except Exception as e:
        logging.error(f"Erro ao salvar config: {e}")


def atualizar_config(**campos):
    """Relê a configuração, altera só os campos indicados e salva (evita sobrescrever outros)."""
    config = carregar_config()
    config.update(campos)
    salvar_config(config)
    return config
