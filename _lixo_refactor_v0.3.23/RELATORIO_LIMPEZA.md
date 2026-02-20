# Relatório de Limpeza e Manutenção - iBirder v0.8.7+

Este relatório identifica arquivos e diretórios que podem ser removidos com segurança para limpar o projeto, baseando-se na arquitetura atual (iNaturalist API).

## 1. Dependências (requirements.txt)
O arquivo `requirements.txt` já foi limpo anteriormente.
- **Mantidas:** `Pillow`, `requests`, `google-genai`, `keyring`.
- **Removidas:** `beautifulsoup4` (Scraping descontinuado).

## 2. Arquivos de Mídia Órfãos (assets/)
Arquivos de imagem que não parecem estar sendo utilizados no código atual ou são artefatos de geração.

- [ ] `assets/Gemini_Generated_Image_889mj6889mj6889m.jpg`
  - **Motivo:** Artefato gerado, sem uso no código.
- [ ] `assets/config_gear.png`
  - **Motivo:** O código (`ui/janela_principal.py`) prioriza `icon_config.svg`. Este PNG parece ser um fallback ou artefato do script `generate_gear_icon.py`.
- [ ] `assets/aves_locais.json`
  - **Motivo:** Não referenciado no código atual. Parece ser um arquivo de dados antigo ou de teste.

## 3. Código Morto e Estruturas Vazias
Diretórios e arquivos de código que não têm função na versão atual.

- [ ] `services/` (Diretório)
  - **Motivo:** Contém apenas `__init__.py`. As lógicas de serviço estão em `core/`.
- [ ] `generate_gear_icon.py` e `generate_search_icon.py`
  - **Motivo:** Scripts utilitários de desenvolvimento ("one-off"). Não necessários para execução da aplicação. Podem ser movidos para uma pasta `tools/` ou deletados se os assets já estiverem gerados.

## 4. Arquivos Temporários e Caches
Arquivos gerados automaticamente que não devem ser versionados.

- [ ] `__pycache__/` (em vários diretórios)
  - **Motivo:** Cache de bytecode Python. Pode ser deletado com segurança.
- [ ] `.venv/` (se for recriar ambiente)
  - **Motivo:** Ambiente virtual. (Manter se estiver em uso, mas ignorar no git).
- [ ] `temp/`
  - **Motivo:** Diretório temporário da aplicação (imagens otimizadas, downloads). O código já possui rotina de limpeza (`atexit`), mas pode ser limpo manualmente.
- [ ] `proposals/`
  - **Motivo:** Diretório desconhecido/não padrão. Investigar conteúdo.

## Ações Recomendadas
1. Executar exclusão dos arquivos listados na seção 2.
2. Remover diretório `services/`.
3. Adicionar `__pycache__` e `temp/` ao `.gitignore` (se ainda não estiverem).
