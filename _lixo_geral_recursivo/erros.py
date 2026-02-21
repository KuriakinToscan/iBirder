class ChaveApiFaltandoErro(Exception):
    """Exceção levantada quando a chave da API não é encontrada no keyring."""
    pass

class ErroArquivoInvalido(Exception):
    """Exceção levantada quando o arquivo é inválido ou não gravável."""
    pass
