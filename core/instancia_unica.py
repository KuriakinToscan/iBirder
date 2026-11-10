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
Instância única do iBirder (por usuário do Windows).

"Abrir com > iBirder" com o app já aberto não cria uma segunda janela (com outro
interpretador da IA e outro Chrome): a nova execução entrega o caminho da foto à janela
existente por um QLocalServer e encerra.
"""

import getpass
import logging
import re
from typing import Callable, Optional

from PySide6.QtCore import QObject
from PySide6.QtNetwork import QLocalServer, QLocalSocket

TEMPO_CONEXAO_MS = 500


def nome_servidor() -> str:
    """Nome do canal local, distinto por usuário (dois usuários na mesma máquina não se misturam)."""
    try:
        usuario = getpass.getuser()
    except Exception:
        usuario = "usuario"
    return "iBirder-" + re.sub(r"[^A-Za-z0-9_-]", "_", usuario)


def enviar_para_instancia_aberta(caminho: Optional[str], nome: Optional[str] = None) -> bool:
    """
    Se já houver um iBirder aberto, envia o caminho da foto (ou nada, só para trazer a janela
    à frente) e retorna True: esta execução deve encerrar. Retorna False se não houver outro.
    """
    socket = QLocalSocket()
    socket.connectToServer(nome or nome_servidor())
    if not socket.waitForConnected(TEMPO_CONEXAO_MS):
        return False
    socket.write((caminho or "").encode("utf-8"))
    socket.flush()
    socket.waitForBytesWritten(TEMPO_CONEXAO_MS)
    socket.disconnectFromServer()
    logging.info("iBirder já estava aberto: foto entregue à janela existente.")
    return True


class ServidorInstancia(QObject):
    """Recebe as fotos enviadas por novas execuções e repassa a ``ao_receber(caminho)``."""

    def __init__(self, ao_receber: Callable[[str], None], nome: Optional[str] = None, parent=None):
        super().__init__(parent)
        self._ao_receber = ao_receber
        self._nome = nome or nome_servidor()
        self._servidor = QLocalServer(self)
        self._servidor.newConnection.connect(self._nova_conexao)

    def iniciar(self) -> bool:
        """Começa a escutar. Remove um canal órfão deixado por um iBirder que travou."""
        QLocalServer.removeServer(self._nome)
        ok = self._servidor.listen(self._nome)
        if not ok:
            logging.warning(f"Instância única indisponível: {self._servidor.errorString()}")
        return ok

    def _nova_conexao(self):
        socket = self._servidor.nextPendingConnection()
        if socket is None:
            return
        socket.readyRead.connect(lambda: None)  # mantém o buffer de leitura ativo
        socket.disconnected.connect(lambda: self._ler(socket))
        if socket.state() != QLocalSocket.LocalSocketState.ConnectedState:
            self._ler(socket)

    def _ler(self, socket):
        if socket.property("lido"):
            return
        socket.setProperty("lido", True)
        caminho = bytes(socket.readAll()).decode("utf-8", errors="replace").strip()
        socket.deleteLater()
        try:
            self._ao_receber(caminho)
        except Exception:
            logging.error("Falha ao abrir a foto recebida de outra execução.", exc_info=True)
