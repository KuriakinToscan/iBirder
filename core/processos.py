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
Execução de programas externos (ExifTool, chromedriver) sem janela de console.

O iBirder empacotado é um app de janela (sem console): no Windows, cada programa de
console chamado por subprocess abre uma janela cmd que pisca na tela. CREATE_NO_WINDOW
impede isso. Toda chamada a subprocess do app deve passar por aqui.
"""

import subprocess
import sys

# 0x08000000 = CREATE_NO_WINDOW (a constante só existe no subprocess do Windows)
SEM_JANELA = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000) if sys.platform == "win32" else 0


def executar(args, **kwargs):
    """subprocess.run sem janela de console no Windows (mesmos argumentos e retorno)."""
    if SEM_JANELA:
        kwargs["creationflags"] = kwargs.get("creationflags", 0) | SEM_JANELA
    return subprocess.run(args, **kwargs)
