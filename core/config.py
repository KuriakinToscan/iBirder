import json
from pathlib import Path

CONFIG_FILE = "config.json"

def obter_caminho_config():
    """Retorna o caminho absoluto para o arquivo de configuração."""
    # Salva na raiz do projeto/executável para portabilidade simples
    base_path = Path(__file__).parent.parent.absolute()
    return base_path / CONFIG_FILE

def carregar_config():
    """Carrega a configuração local ou retorna padrão."""
    config_path = obter_caminho_config()
    default_config = {
        "pular_pergunta_atalho": False,
        "modo_operacao": None, # "online" ou "offline"
        "lembrar_modo": False,
        "mostrar_alerta_boot_api": True,
        "xc_api_key": ""
    }
    
    if config_path.exists():
        try:
            with open(config_path, "r") as f:
                user_config = json.load(f)
                # Merge com default para garantir que chaves novas existam
                default_config.update(user_config)
                return default_config
        except:
            pass
            
    return default_config

def salvar_config(config):
    """Salva a configuração local."""
    config_path = obter_caminho_config()
    try:
        with open(config_path, "w") as f:
            json.dump(config, f, indent=4)
    except Exception as e:
        print(f"Erro ao salvar config: {e}")
