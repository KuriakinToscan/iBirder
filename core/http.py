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

import threading
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# User-Agent de navegador: alguns sites (buscadores, WikiAves) recusam clientes sem identificação
BROWSER_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)
DEFAULT_TIMEOUT = 10

_local = threading.local()


def get_session() -> requests.Session:
    """
    Sessão HTTP reutilizável (uma por thread, pois requests.Session não é thread-safe).
    Reaproveita conexões TCP/TLS e faz até 2 novas tentativas em erros transitórios
    (429/5xx e falhas de conexão), com espera crescente.
    """
    session = getattr(_local, "session", None)
    if session is None:
        session = requests.Session()
        retry = Retry(
            total=2,
            backoff_factor=0.5,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=("GET", "HEAD"),
            respect_retry_after_header=True,
        )
        adapter = HTTPAdapter(max_retries=retry, pool_maxsize=10)
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        session.headers.update({
            "User-Agent": BROWSER_UA,
            "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
        })
        _local.session = session
    return session


def get(url, timeout=DEFAULT_TIMEOUT, **kwargs) -> requests.Response:
    """Atalho para GET com timeout padrão na sessão compartilhada."""
    return get_session().get(url, timeout=timeout, **kwargs)
