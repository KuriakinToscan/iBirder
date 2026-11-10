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

"""Aviso de nova versão do aplicativo (Releases do GitHub).

A atualização "OTA" do modelo de IA foi removida na v1.4: nunca baixou modelos reais e a troca
em Program Files exigiria administrador.
"""

import logging
from PySide6.QtCore import QObject, Signal, QThread

class AppUpdater(QObject):
    """
    Verifica se há versão nova do aplicativo (Releases do GitHub). Regras em
    core/verificacao_versao.py.

    Sinais:
    - app_update_available(info): há versão nova a avisar (info de ler_release).
    - verificacao_concluida(info, erro, manual): fim de qualquer consulta; info vazio se não
      houver Release, erro vazio se a consulta funcionou.
    """
    app_update_available = Signal(dict)
    verificacao_concluida = Signal(dict, str, bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        from core.config import APP_VERSION
        self.current_version = APP_VERSION
        self.worker = None

    def check_for_updates(self, manual=False):
        """
        Inicia a consulta em segundo plano. Automática (manual=False): respeita a opção
        "verificar_atualizacoes" e o intervalo de 24 h. Retorna False se não consultou.
        """
        from core.config import carregar_config
        from core.verificacao_versao import deve_verificar
        if not manual and not deve_verificar(carregar_config()):
            logging.info("Verificação de nova versão do app: desativada ou feita há menos de 24 h.")
            return False
        if self.worker is not None and self.worker.isRunning():
            if manual:
                self.worker.manual = True  # o resultado em andamento passa a ser mostrado
            return True
        self.worker = AppCheckWorker(manual=manual)
        self.worker.resultado.connect(self._on_resultado)
        self.worker.start()
        return True

    def _on_resultado(self, info, erro, manual):
        from core.config import atualizar_config, carregar_config
        from core.verificacao_versao import deve_avisar
        from datetime import datetime, timezone
        if erro:
            logging.warning(f"Verificação de nova versão do app falhou: {erro}")
        else:
            # Só conta como verificada se a consulta funcionou (falha de rede tenta na próxima abertura)
            atualizar_config(ultima_verificacao_versao=datetime.now(timezone.utc).isoformat(timespec="seconds"))
            if deve_avisar(info, self.current_version, carregar_config(), manual=manual):
                logging.info(f"Nova versão do app encontrada: {info['tag']} (atual: {self.current_version})")
                self.app_update_available.emit(info)
            else:
                logging.info(f"Aplicativo na última versão ({self.current_version}) ou versão ignorada.")
        self.verificacao_concluida.emit(info or {}, erro, manual)

    def ignorar_versao(self, versao):
        """Não avisar mais desta versão na verificação automática."""
        from core.config import atualizar_config
        atualizar_config(versao_ignorada=versao)
        logging.info(f"Versão {versao} marcada como ignorada pelo usuário.")


class AppCheckWorker(QThread):
    """Consulta a última Release fora da thread da interface."""
    resultado = Signal(dict, str, bool)  # info (vazio se não houver Release), erro, manual

    def __init__(self, manual=False, parent=None):
        super().__init__(parent)
        self.manual = manual

    def run(self):
        from core.verificacao_versao import consultar_ultima_release
        try:
            info, erro = consultar_ultima_release() or {}, ""
        except Exception as e:
            info, erro = {}, str(e)
        self.resultado.emit(info, erro, self.manual)
