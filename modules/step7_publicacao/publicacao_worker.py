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

"""Thread de publicação no iNaturalist: login OAuth (se preciso), JWT e envio."""

import logging

import requests
from PySide6.QtCore import QThread, Signal

from core import inat_oauth
from core.config import atualizar_config, carregar_config
from modules.step7_publicacao import inat_publicador


def executar_publicacao(corpo, caminho_foto, progresso, autorizar=inat_oauth.autorizar,
                        obter_jwt=inat_oauth.obter_jwt, publicar=inat_publicador.publicar):
    """
    Obtém o JWT (entrando no iNaturalist pelo navegador se não houver token válido) e publica.
    Um token salvo que expirou é descartado e o login é refeito uma única vez.
    Separado da thread para ser testado sem Qt e sem rede.
    """
    config = carregar_config()
    app_id = inat_oauth.obter_app_id(config)
    token = (config.get("inat_oauth_token") or "").strip()

    for _ in range(2):
        if not token:
            progresso("Autorize o iBirder no navegador que foi aberto...")
            token = autorizar(app_id)
            atualizar_config(inat_oauth_token=token)
        progresso("Conectando ao iNaturalist...")
        jwt = obter_jwt(token)
        if jwt is None:
            logging.info("[Publicação] Token OAuth expirado; novo login necessário")
            token = ""
            atualizar_config(inat_oauth_token="")
            continue
        try:
            return publicar(jwt, corpo, caminho_foto, progresso=progresso)
        except inat_publicador.TokenExpirado:
            # Recusado antes de criar a observação: seguro tentar de novo com novo login
            token = ""
            atualizar_config(inat_oauth_token="")
    raise inat_publicador.ErroPublicacao("Não foi possível obter autorização do iNaturalist. Tente de novo.")


class PublicacaoInatWorker(QThread):
    progresso = Signal(str)
    concluido = Signal(dict)
    falhou = Signal(str)

    def __init__(self, corpo, caminho_foto, parent=None):
        super().__init__(parent)
        self.corpo = corpo
        self.caminho_foto = caminho_foto

    def run(self):
        try:
            resultado = executar_publicacao(self.corpo, self.caminho_foto, self.progresso.emit)
            self.concluido.emit(resultado)
        except (inat_oauth.ErroLoginInat, inat_publicador.ErroPublicacao) as e:
            self.falhou.emit(str(e))
        except requests.RequestException as e:
            logging.error(f"[Publicação] Erro de rede: {e}")
            self.falhou.emit("Sem conexão com o iNaturalist. Verifique a internet e tente de novo.")
        except Exception as e:
            logging.exception("[Publicação] Falha inesperada")
            self.falhou.emit(f"Falha inesperada na publicação: {e}")
