import json
import os
import tempfile
import traceback

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
            print(f"[SessionLogger] Falha ao inicializar JSON no temp_file: {e}")
        finally:
            # Fechamos imediatamente o descritor original. O arquivo permanece no disco.
            temp_file.close()
            
        print(f"[SessionLogger] Caderneta temporária criada em: {self.filepath}")

    def flush(self):
        """Escreve o buffer da RAM no disco (Arquivo JSON temporário) apenas de uma vez."""
        if not self.buffer:
            return
            
        try:
            with open(self.filepath, 'w', encoding='utf-8') as f:
                json.dump(self.buffer, f, indent=4, ensure_ascii=False)
            print(f"[SessionLogger] I/O Batch Flush Executado! ({len(self.buffer)} registros atualizados em disco).")
        except Exception as e:
            print(f"[SessionLogger] Erro ao executar o flush (Batch Log): {e}")

    def registrar_identificacao(self, dados: dict):
        """Append seguro de um dicionário na Session RAM Buffer."""
        try:
            self.buffer.append(dados)
        except Exception as e:
            print(f"[SessionLogger] Erro ao registrar_identificacao no Batch: {e}")
            traceback.print_exc()

    def limpar_sessao(self):
        """Metodo manual para destruir o arquivo temporário ao final do app."""
        try:
            if os.path.exists(self.filepath):
                os.remove(self.filepath)
                print("[SessionLogger] Caderneta temporária limpa com sucesso.")
        except Exception as e:
            print(f"[SessionLogger] Atenção: não foi possível remover o tmp {self.filepath}: {e}")

    def reset(self):
        """Limpa o buffer da RAM para permitir um novo início limpo sem deletar o arquivo."""
        print("[SessionLogger] Resetando buffer da caderneta para novo ciclo.")
        self.buffer = []

    def atualizar_ultimo_registro(self, novos_dados: dict):
        """Atualiza o último registro no RAM Logger, ou cria um novo se estiver vazio (v0.8.7)."""
        try:
            if self.buffer and isinstance(self.buffer, list):
                # Recupera a última entrada (Etapa 1) e injeta/sobrescreve os dados agregados na Memória VRAM
                self.buffer[-1].update(novos_dados)
            else:
                # Se o buffer estiver vazio (ex: após busca manual/reset), criamos a entrada agora
                self.registrar_identificacao(novos_dados)
                    
        except Exception as e:
            print(f"[SessionLogger] Erro ao atualizar_ultimo_registro na Memória: {e}")
            traceback.print_exc()
