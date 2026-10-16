# iBirder — notas para o Claude Code

Aplicativo desktop (Windows) em Python 3.12 + PySide6 para identificação de aves por foto.
Pipeline em `core/orchestrator.py`; etapas em `modules/step1..step6`; interface em `ui/`.

## Ambiente de testes do usuário (Windows / Anaconda)

O usuário mantém um ambiente conda **`ibirder-teste`** no computador dele, criado para testes reais
que não podem rodar no servidor do Claude (o Cloudflare do WikiAves bloqueia IPs de datacenter,
inclusive com Chrome headless).

- Criado com `conda create -n ibirder-teste python=3.12`; já tem o `requirements.txt` completo
  instalado, então roda o app inteiro (`python main.py`) a partir do ZIP da branch.
- Teste real do WikiAves: `python tools\testar_wikiaves.py` (opções: `--visivel`, ou nomes
  científicos como argumentos). O relatório sai em `tools\relatorio_wikiaves.txt`.
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

## Dados e fontes (verificados em 16/10/2026)

- Modelo local: MobileNetV2 "Birds V1" (Google AIY), 965 espécies; só ~230 ocorrem no Brasil.
- iNaturalist: lugar Brasil = `place_id` 6878 (6857 é o Reino Unido). Endemismo vem de
  `establishment_means` no detalhe do táxon com `preferred_place_id=6878`.
- O iNaturalist não tem a lista nacional (ICMBio) nem os anexos da CITES: mostrar
  "Não disponível", nunca "Não Avaliado"/"Não Listado".
- Gravações do iNaturalist são ~47% `.m4a` (AAC): o QtWebEngine do PySide6 (pip) não toca AAC;
  usar o player QtMultimedia (`ui/widgets/audio_player.py`).

## Testes

- Offline: `python -m pytest tests` (sem rede, sem Chrome).
- ExifTool: as tags Darwin Core corretas são `XMP-dwc:TaxonScientificName`, `TaxonFamily` etc.
  (estrutura `Taxon`); `XMP-dwc:ScientificName` não existe e é ignorada em silêncio.

## Documentação

- `guia_do_usuario.md` é exibido no app por um conversor próprio (`ui/dialogs/manual_dialog.py`):
  suporta `##`, `###`, `### [ETAPA n] título` (card), listas `-`/`1.`, `> aviso`,
  `> **DICA PRO:** ...`, `---`, links `[texto](https://...)`, `código`, **negrito** e *itálico*.
  Não suporta tabelas.
- `manual_apis_nuvem.md` é exibido com o Markdown nativo do Qt (suporta tabelas e links).
- Histórico em `CHANGELOG.md`; versão única em `core/config.py` (`APP_VERSION`).

## Convenções

- Textos, comentários e mensagens de commit em português.
- `config.json` (chaves de API do usuário) nunca deve ser versionado; use `config.example.json`.
