# iBirder — notas para o Claude Code

Aplicativo desktop (Windows) em Python 3.12 + PySide6 para identificação de aves por foto.
Pipeline em `core/orchestrator.py`; etapas em `modules/step1..step6`; interface em `ui/`.

## Ambiente de testes do usuário (Windows / Anaconda)

O usuário mantém um ambiente conda **`ibirder-teste`** no computador dele, criado para testes reais
que não podem rodar no servidor do Claude (o Cloudflare do WikiAves bloqueia IPs de datacenter,
inclusive com Chrome headless).

- Criado com: `conda create -n ibirder-teste python=3.12` +
  `pip install selenium webdriver-manager beautifulsoup4 lxml`
- Uso: `conda activate ibirder-teste` e, na pasta do projeto, `python tools\testar_wikiaves.py`
  (opções: `--visivel`, ou nomes científicos como argumentos). O relatório sai em
  `tools\relatorio_wikiaves.txt`, que o usuário envia de volta para análise.
- Quando precisar validar algo que dependa de sites externos bloqueados aqui, peça ao usuário
  para rodar no `ibirder-teste`. Se forem necessárias outras bibliotecas, diga exatamente qual
  `pip install` executar nesse ambiente.
- **Pendente:** quando o ambiente não for mais necessário, lembrar o usuário de removê-lo com
  `conda env remove -n ibirder-teste`. Não remover sem o usuário pedir.

## WikiAves (validado em 16/10/2026 no Windows do usuário, 10/10 casos corretos)

- O site fica atrás do Cloudflare: requisições HTTP simples recebem 403. Usar o Chrome via
  Selenium (`modules/step2_biology/wiki_scraper.py`).
- Fluxo: busca interna `getTaxonsJSON.php?term=<nome científico>` (campos `wid`, `label`, `nome`)
  → `/wiki/<wid>` → extração. Lista vazia `[]` = espécie não existe no WikiAves (resposta
  definitiva, não usar buscadores externos: antes isso trocava *Haemorhous cassinii* pelo guaxe).
  DuckDuckGo/Bing só quando a busca interna falha (erro/Cloudflare).
- Só aceitar resultado com o mesmo nome científico (exato ou gênero + espécie) e exigir o nome
  científico na página extraída.

## Testes

- Offline: `python -m pytest tests` (sem rede, sem Chrome).
- ExifTool: as tags Darwin Core corretas são `XMP-dwc:TaxonScientificName`, `TaxonFamily` etc.
  (estrutura `Taxon`); `XMP-dwc:ScientificName` não existe e é ignorada em silêncio.

## Convenções

- Textos, comentários e mensagens de commit em português.
- `config.json` (chaves de API do usuário) nunca deve ser versionado; use `config.example.json`.
