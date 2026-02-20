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
        
        # Inicializa a estrutura JSON base (uma lista vazia)
        try:
            json.dump([], temp_file)
        except Exception as e:
            print(f"[SessionLogger] Falha ao inicializar JSON no temp_file: {e}")
        finally:
            # Fechamos imediatamente o descritor original. O arquivo permanece no disco.
            temp_file.close()
            
        print(f"[SessionLogger] Caderneta temporária criada em: {self.filepath}")

    def registrar_identificacao(self, dados: dict):
        """Append seguro de um dicionário no arquivo temporário JSON."""
        try:
            # 1. Leitura do estado atual
            with open(self.filepath, 'r', encoding='utf-8') as f:
                sessao_atual = json.load(f)
            
            # 2. Append e Update
            sessao_atual.append(dados)
            
            # 3. Sobrescrita limpa
            with open(self.filepath, 'w', encoding='utf-8') as f:
                json.dump(sessao_atual, f, indent=4, ensure_ascii=False)
                
            print(f"[SessionLogger] Resumo salvo com sucesso na caderneta. (Total: {len(sessao_atual)})")
        except Exception as e:
            print(f"[SessionLogger] Erro ao registrar_identificacao: {e}")
            traceback.print_exc()

    def limpar_sessao(self):
        """Metodo manual para destruir o arquivo temporário ao final do app."""
        try:
            if os.path.exists(self.filepath):
                os.remove(self.filepath)
                print("[SessionLogger] Caderneta temporária limpa com sucesso.")
        except Exception as e:
            print(f"[SessionLogger] Atenção: não foi possível remover o tmp {self.filepath}: {e}")
