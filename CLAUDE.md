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
- O iNaturalist não tem a lista nacional (ICMBio) nem os anexos da CITES: desde a v1.3 elas vêm
  das tabelas embarcadas (seção abaixo). Do iNaturalist vêm só as listas estaduais e de outros
  países ("Outras avaliações"). Sem dado, mostrar "Não disponível", nunca inventar "Não Avaliado".
- Gravações do iNaturalist são ~47% `.m4a` (AAC): o QtWebEngine do PySide6 (pip) não toca AAC;
  usar o player QtMultimedia (`ui/widgets/audio_player.py`).

## Listas de conservação embarcadas (v1.3)

- `assets/conservacao/`: `lista_nacional_aves_mma2022.csv` (Portaria MMA 148/2022, com `inat_id`),
  `cites_aves.csv` (Species+, com sinônimos) e `aves_registradas_brasil.csv` (iNaturalist, place 6878).
- Geradas por `python tools/atualizar_listas_conservacao.py [mma|cites|brasil]` (exige `pdftotext`);
  consultadas por `modules/step3_geography/listas_conservacao.py`.
- Subespécie da portaria só casa com subespécie no iNaturalist (nunca marcar a espécie inteira).

## Postagem no iNaturalist e no WikiAves (planejada, issue #9; decisões de 24/10/2026)

- **iNaturalist**: autenticação por **OAuth** (aplicativo registrado), não pelo JWT de 24 h usado na
  identificação. API v1: `POST /observations` e depois `POST /observation_photos`. Requisitos de
  registro do app e suporte a PKCE ainda não verificados.
- Licenças padrão: **observação CC BY** e **foto CC BY-NC**. Só observações em CC0, CC BY ou CC BY-NC
  vão para o GBIF. Geoprivacidade **aberta** por padrão, com sugestão de **ocultada** para espécies CR/EN/VU
  da Portaria MMA 148/2022 ou do Anexo I da CITES (tabelas de `assets/conservacao/`). O usuário confirma
  antes de cada envio, e o id da observação fica guardado para evitar duplicata.
- **WikiAves** (Termos de Uso v02, 31/08/2021): o item 13.3 proíbe mineração de dados, bots e
  "operações massificadas". **Não automatizar o envio.** O app só prepara foto, espécie, data e município,
  mostra o checklist das regras (mídia própria; ave nativa pela lista do CBRO e em liberdade; sem
  pessoa, borda ou assinatura) e abre a página de envio, e o usuário envia manualmente, logado na própria
  conta. Nunca guardar a senha do WikiAves.
- A leitura automatizada da etapa 2 foi mantida por decisão do mantenedor (uso não comercial, com
  crédito; issue #10 fechada). Os textos wiki estão em CC BY-NC-SA 4.0 (item 12.6 dos termos).
- O ambiente do Claude não alcança wikiaves.com.br: para ler páginas do site, pedir o texto ao usuário.

## Temas (v1.4)

- Tokens em `core/temas.py` (Off-White, Clean, Clássico); escolha salva em `config.json` (`"tema"`).
- Nada de cor fixa na `ui/`: escrever QSS/HTML com `var(--token)` e aplicar por
  `StyleManager.estilizar(widget, qss)` / `StyleManager.definir_texto(rotulo, html)`, que guardam o
  modelo e renderizam de novo na troca de tema (sem reiniciar). `tests/test_temas.py` acusa `#RRGGBB`
  na `ui/` (exceto as cores de dado do mapa) e contraste de texto abaixo de 4,5:1.
- Logos dos temas: `python tools/gerar_logos.py` (duotone do `assets/logo_ave.svg`).
- Layouts (`ui/layouts/`): a janela cria os painéis uma vez (`Paineis`) e toda a lógica fala com
  eles; um layout só os posiciona em `montar()` (cada painel uma vez). Trocar de layout reparenta os
  painéis (`JanelaPrincipal._aplicar_layout`), sem recriar. Escolha em `config.json` (`"layout"`).
  A etapa atual (sem foto, identificando, conferir, gravada...) fica em `ui/estado_identificacao.py`.

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
