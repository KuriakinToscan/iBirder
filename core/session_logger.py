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

import os
import tempfile
import traceback
import logging
import json

class SessionLogger:
    """
    Gerencia uma caderneta de campo temporária para a sessão atual.
    As identificações são salvas em um arquivo JSON temporário que sobrevive
    fechamentos de arquivos para contornar problemas de lock no Windows.
    """
    
    def __init__(self):
        # Usamos delete=False para que o Windows não segure o lock do arquivo e
        # permita que nós (e o PySide) read/write independentemente ao longo do uso.
        temp_file = tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.json', encoding='utf-8')
        self.filepath = temp_file.name
        self.buffer = [] # RAM Cache para escritas em Batch
        
        # Inicializa a estrutura JSON base (uma lista vazia)
        try:
            json.dump([], temp_file)
        except Exception as e:
            logging.error(f"Falha ao inicializar JSON no temp_file: {e}")
        finally:
            temp_file.close()
            
        logging.debug(f"Caderneta temporária criada em: {self.filepath}")

    def flush(self):
        """Escreve o buffer da RAM no disco (Arquivo JSON temporário) apenas de uma vez."""
        if not self.buffer:
            return
            
        try:
            with open(self.filepath, 'w', encoding='utf-8') as f:
                json.dump(self.buffer, f, indent=4, ensure_ascii=False)
            logging.debug(f"I/O Batch Flush Executado! ({len(self.buffer)} registros atualizados em disco).")
        except Exception as e:
            logging.error(f"Erro ao executar o flush (Batch Log): {e}")

    def registrar_identificacao(self, dados: dict):
        """Append seguro de um dicionário na Session RAM Buffer."""
        try:
            self.buffer.append(dados)
        except Exception as e:
            logging.error(f"Erro ao registrar_identificacao no Batch: {e}", exc_info=True)

    def limpar_sessao(self):
        """Metodo manual para destruir o arquivo temporário ao final do app."""
        try:
            if os.path.exists(self.filepath):
                os.remove(self.filepath)
                logging.debug("Caderneta temporária limpa com sucesso.")
        except Exception as e:
            logging.warning(f"Atenção: não foi possível remover o tmp {self.filepath}: {e}")

    def reset(self):
        """Limpa o buffer da RAM para permitir um novo início limpo sem deletar o arquivo."""
        logging.info("Resetando buffer da caderneta para novo ciclo.")
        self.buffer = []

    def atualizar_ultimo_registro(self, novos_dados: dict):
        """Atualiza o último registro no RAM Logger, ou cria um novo se estiver vazio (v0.8.7).
        Garante que valores nulos/vazios não sobrescrevam dados já existentes (v0.9.5)."""
        try:
            if self.buffer and isinstance(self.buffer, list):
                ultimo = self.buffer[-1]
                # Injetamos apenas dados novos ou que não sejam vazios onde já existe valor
                for k, v in novos_dados.items():
                    pode_atualizar = True
                    # Se ja temos um valor bom e o novo é ruim, ignoramos
                    if k in ultimo and v in [None, "", "Desconhecida", "Desconhecido", "N/D"]:
                         if ultimo[k] not in [None, "", "Desconhecida", "Desconhecido", "N/D"]:
                              pode_atualizar = False
                    
                    if pode_atualizar:
                        ultimo[k] = v
            else:
                # Se o buffer estiver vazio (ex: após busca manual/reset), criamos a entrada agora
                self.registrar_identificacao(novos_dados)
                    
        except Exception as e:
            logging.error(f"Erro ao atualizar_ultimo_registro na Memória: {e}", exc_info=True)
