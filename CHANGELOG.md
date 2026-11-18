# Histórico de versões

## v1.6 (em desenvolvimento)

### Novidades
- **Modo claro e escuro**: em **Configurações > Aparência > Modo**, o padrão **Igual ao Windows** acompanha o modo do sistema e troca sozinho com o iBirder aberto (sinal `colorSchemeChanged` do Qt 6.5+; sem resposta do Qt, lê o registro do Windows). **Claro** e **Escuro** fixam o modo. Logo, ícones do topo, barra de título e mapa seguem o modo; no mapa, só a camada do OpenStreetMap é escurecida (filtro CSS), e os pinos e as cores de densidade do GBIF ficam como estão.
- **Paletas de cores**: além de Off-White, Clean e Clássico, que ganham versão escura e não mudam no modo claro, entram **Gralha-azul**, **Sabiá** e **Alto contraste** (contraste mínimo de 7:1). As Configurações mostram uma amostra de cada paleta no modo em uso.

### Alterações
- **Temas viram paleta x modo** (`core/temas.py`): cada paleta declara as cores-base de cada modo e o resto é derivado (`derivar_tokens`), podendo ser sobrescrito. Os testes conferem contraste de 4,5:1 (7:1 no Alto contraste) nas 12 combinações, incluindo texto sobre o item selecionado e sob o mouse. O `config.json` ganha `"modo"` (`sistema`, `claro` ou `escuro`); a paleta continua na chave `"tema"`, então configurações antigas abrem sem mudança.
- **Logos das paletas** em PNG de 256 cores (6 a 10 KB cada, antes 80 KB), gerados por `python tools/gerar_logos.py` para cada paleta e modo.

## v1.5 (em desenvolvimento)

### Novidades
- **Nova IA local: BioCLIP** (imageomics/bioclip, licença MIT), no lugar do MobileNetV2 "Birds V1". Ela reconhece pelo nome científico e em inglês todas as cerca de 1.760 aves com registro no Brasil (o modelo antigo conhecia ~230) e, para fotos com GPS fora do Brasil, as ~11 mil espécies do catálogo eBird. Em 300 fotos do iNaturalist de 210 espécies no Brasil, acertou a espécie na 1ª opção em 46,7% das fotos, contra 16,3% do modelo antigo (111 x 7 fotos discordantes, McNemar p < 0,001); nas espécies que o modelo antigo conhecia, empatou (59,5% x 59,0%). Roda no computador, sem internet, em cerca de 0,1 s por foto (LiteRT, INT8 dinâmico, 88 MB). O instalador cresce cerca de 85 MB. Quem roda pelo código-fonte baixa o modelo (~90 MB, conferido por SHA-256) na primeira identificação.
- **Avaliação da IA local** (`tools/avaliar_identificacao.py`, ferramenta de manutenção): roda o modelo em uma pasta de fotos de espécie conhecida (planilha `arquivo;especie` ou o nome gravado pelo iBirder) e relata o acerto top-1 e top-3 com intervalo de confiança de 95%, a comparação entre a foto com borda e a foto espremida (teste exato de McNemar) e a tabela de limiares de confiança. Nenhuma foto é alterada nem enviada.
- **Avaliação: prior Brasil e foto espelhada**: o relatório compara, nas mesmas fotos, a IA como está no app com três variantes (média com a foto espelhada; só espécies registradas no Brasil, com as probabilidades renormalizadas; as duas juntas) e com a foto em letterbox, cada uma contra o app pelo teste exato de McNemar. Nada muda no app até a medição.
- **Avaliação: BioCLIP** (`--bioclip`, só no ambiente de teste, com `open_clip_torch` e `torch`): compara o BioCLIP (ViT-B/16, licença MIT) sem treino, entre as aves registradas no Brasil, com nomes científicos e com nome científico e inglês, e com os pesos em FP16 (172 MB) e em INT8 por canal (87 MB), e mostra o tempo médio por foto e o tamanho de cada modelo.
- **BioCLIP em LiteRT** (`tools/converter_bioclip_litert.py`, roda no GitHub Actions: workflow "Converter BioCLIP"): converte o codificador de imagem para `.tflite` com pesos INT8 por canal (só pesos e INT8 dinâmico, ~88 MB cada), confere contra o PyTorch e grava os textos das 1.759 aves do Brasil. A avaliação lê a pasta com `--bioclip-litert` usando só o `ai-edge-litert` do app e mede acerto, tempo e tamanho reais.
- **Amostra do iNaturalist para a avaliação** (`tools/amostra_inaturalist.py`, ou `--baixar-inat N` na avaliação): baixa fotos de aves do Brasil em grau de pesquisa e licença aberta (CC0, CC BY, CC BY-NC), observadas desde 2023, no máximo 2 por espécie, com `especies.csv` e `creditos.csv` (observação, autor e licença).

### Alterações
- **Modelo de IA fora do repositório**: os arquivos do BioCLIP ficam numa Release de pré-lançamento própria (`modelo-bioclip-1`), descrita em `assets/models/bioclip_modelo.json` (tamanho e SHA-256). O build do instalador baixa e confere (`python -m core.model_manager`). O MobileNetV2 continua no repositório só como referência da avaliação e não vai mais para o instalador.
- **IA local só com aves do Brasil**: para fotos com GPS no Brasil, e para fotos sem GPS, a IA local considera só as cerca de 1.750 espécies com registro no país (lista embarcada do iNaturalist), com a confiança renormalizada entre elas. Com 200 fotos do iNaturalist de espécies que o modelo conhece, o acerto na 1ª opção subiu de 48,0% para 59,0% (22 fotos ganhas, nenhuma perdida). Nova opção em **Configurações > Identificação** para desligar o filtro em fotos sem GPS (quem fotografa no exterior).
- **Nuvem sempre consultada quando configurada**: numa amostra de 300 fotos de aves do Brasil, só 29% eram de espécies que a IA local conhece, e nenhum limiar de confiança passou de 60% de acerto. Por isso a IA local não decide mais sozinha: com chave do iNaturalist ou do Google Vision, a espécie é sempre confirmada na nuvem. Sem nuvem, o resultado local aparece como sugestão, com aviso para conferir e as outras candidatas; abaixo de 30% de confiança, é inconclusivo. Sai o aviso "sem registro no Brasil", que o filtro tornou desnecessário.
- **IA local volta a receber a foto inteira esticada para 224x224 px** (sem recorte), em vez da borda cinza (letterbox) adotada na v1.4. Na avaliação com 200 fotos do iNaturalist de 110 espécies que o modelo conhece, esticar acertou a espécie na 1ª opção em 46,0% das fotos, contra 41,5% com borda (top-3: 63,5% contra 59,5%; 15 x 6 fotos discordantes, McNemar p = 0,078). A abertura reduzida e a cópia de 1024 px para a nuvem continuam preservando a proporção original. O relatório da avaliação traz a tabela de limiares dos dois modos e sai em UTF-8 com BOM (acentos certos no PowerShell).

## v1.4

### Novidades
- **Publicar no iNaturalist** (issue #9): botão **Publicar no iNaturalist** cria a observação na conta do usuário com a foto, a espécie, a data de captura e o local. Antes do envio, uma janela de conferência mostra tudo e permite escolher a localização pública (aberta, ocultada ou privada; ocultar é sugerido para espécies CR/EN/VU da Portaria MMA 148/2022 e do Anexo I da CITES), a licença da observação (padrão CC BY) e a descrição; o envio só é liberado depois de o usuário confirmar a conferência. O login é por OAuth com PKCE no navegador (a senha não passa pelo iBirder), e o número da observação é gravado na foto para evitar publicação duplicada. Requer o registro do aplicativo iBirder no iNaturalist.
- **Temas de aparência**: Off-White (o visual de sempre), Clean (fundo branco, fonte Figtree, verde-petróleo nas ações principais) e Clássico (papel creme, títulos com serifa Georgia, verde-musgo). A escolha fica em **Configurações (⚙) > Aparência**, é aplicada na hora, sem reiniciar, e cada tema usa o logo original recolorido. Toda cor da interface passou a vir de tokens (`core/temas.py`).
- **Layout da janela principal** (base): **Configurações (⚙) > Aparência** ganhou a escolha do layout, separada do tema. Há o **Painel completo** (a tela de sempre), o **Fluxo guiado**, a **Ficha compacta** e a **Mesa de trabalho**. Internamente, a janela passou a ser montada a partir de painéis (`ui/layouts/`) e a etapa da identificação fica em `ui/estado_identificacao.py`.
- **Layout Fluxo guiado**: uma etapa por vez (Foto › Identificação › Conferir › Gravar), com a etapa atual em destaque e uma dica do próximo passo. Sem foto aberta, só o quadro da foto aparece; depois, fotos lado a lado, identificação à direita e o restante em abas (Descrição, Classificação e conservação, Local, Sons), sem rolar a janela.
- **Layout Ficha compacta**: tudo numa tela, em três colunas (fotos; identificação, descrição, etimologia, taxonomia e conservação; mapa, dados geográficos e vocalizações), cada uma com rolagem própria, e a barra de ações no rodapé.
- **Layout Mesa de trabalho** (fotos em lote): **Abrir pasta...** (ou **Ctrl+Shift+O**) monta a fila com as fotos JPG e PNG da pasta, com miniaturas e a situação de cada uma (pendente, aberta, gravada, já tinha registro, pulada). A leitura das miniaturas e dos registros do iBirder roda em segundo plano; as fotos já gravadas antes ficam fora da fila. Com **Ir para a próxima ao gravar**, gravar abre a próxima foto pendente, sem o aviso de sucesso a cada foto; **Pular** deixa a foto para depois. A identificação continua uma foto por vez (`core/fila_fotos.py`, `ui/widgets/painel_fila.py`).
- **Busca rápida de espécies**: ao digitar no campo Nome Científico aparecem sugestões do catálogo embarcado (todas as espécies do eBird, as registradas no Brasil primeiro), casando nome científico ou nome em inglês, sem acento e por partes ("turdus rufiv", "great kiskadee"). **Ctrl+K** leva direto ao campo. Ainda não há nome popular em português embarcado: ele continua vindo do WikiAves.
- **Sugestões da IA como botões**: as espécies alternativas aparecem como botões (nome científico e certeza); um clique pesquisa a espécie.
- **Atalhos de teclado**: **Ctrl+O** abre uma foto, **Ctrl+S** grava os dados na fotografia e **Ctrl+K** vai para a busca de espécies (em todos os layouts); **Ctrl+Shift+O** abre uma pasta na fila da Mesa de trabalho.
- **Botão principal destacado**: **Gravar Dados na Fotografia**, **Salvar** e as ações principais dos diálogos usam a cor de destaque do tema; botões desativados ficam visualmente diferentes dos ativos.
- **Aviso de novas versões**: ao abrir, o app consulta a última Release no GitHub (no máximo uma vez a cada 24 h) e, se houver versão nova, mostra as novidades com os botões **Baixar instalador** (link direto do `.exe`), **Ver no GitHub**, **Lembrar depois** e **Ignorar esta versão**, além de um aviso na barra de status. **Ajuda (?) > Verificar atualizações** consulta na hora, e o aviso pode ser desligado nas configurações (⚙). Antes, só aparecia um botão discreto na barra de status, a consulta era feita a cada abertura e as falhas não eram informadas.
- **Instalador**: ao atualizar por cima, apaga a pasta `_internal` da versão anterior antes de copiar a nova (arquivos removidos não ficam para trás), fecha o iBirder se estiver aberto e fixa o `AppId` usado desde a v1.1. Configurações e chaves (`%APPDATA%\iBirder`) são mantidas.

### Correções
- **Nuvem sem "espécies" falsas**: a resposta do Google Vision podia virar "Bird" ou um nome em inglês tratado como nome científico. Agora todo nome devolvido pela nuvem é conferido no catálogo do eBird embarcado: nome em inglês é convertido para o científico e rótulos genéricos ("Bird", "Beak") são descartados. O iNaturalist passa a mostrar o top-3 real, com a certeza de cada sugestão (antes, só a primeira com 99% inventado), e descarta gêneros e organismos que não são aves.
- **Configurações protegidas**: o `config.json` é gravado de forma atômica (uma queda de energia no meio não o deixa pela metade). Se estiver ilegível, o app guarda uma cópia (`config.json.corrompido`) e avisa, em vez de gravar o padrão por cima e apagar as chaves de API. O arquivo editado no Bloco de Notas (UTF-8 com BOM) também é aceito.
- **Instância única**: **Abrir com > iBirder** com o app já aberto envia a foto para a janela existente, em vez de abrir uma segunda janela com outra IA e outro Chrome.
- **IA local**: a inferência passa por uma trava, evitando que a identificação da foto anterior e a da nova usem o mesmo interpretador ao mesmo tempo.
- **Limpeza**: removida a "atualização OTA" do modelo de IA, desativada desde a v1.2 (nunca baixou modelos reais), junto com a restauração de modelo que exigiria administrador em Program Files.
- **Build**: UPX desligado no executável (causa conhecida de falso positivo de antivírus em DLLs do Qt; o instalador já comprime com LZMA2). O CI checa o código com `ruff` e deixou de rodar duas vezes para cada PR. Removidos 73 imports sem uso e 8 `except:` nus.
- **Identificação sem deformar a foto**: antes, a foto inteira era espremida para 224x224 px (numa foto 3:2, a ave ficava achatada em 33% na horizontal). Agora o lado maior vai a 224 px e o restante do quadrado recebe borda cinza neutra, sem recorte. A foto também é aberta já reduzida (no JPEG, a própria decodificação reduz para no mínimo 896 px no lado maior): numa foto de 24 Mpx, cerca de 1,5 Mpx em memória em vez de 24 Mpx e preparo cerca de 2,8 vezes mais rápido no teste. A cópia enviada ao iNaturalist e ao Google Vision passou de 800 para 1024 px no lado maior, também com a proporção original (`modules/step1_identity/preprocessamento.py`).
- Nome comum, etimologia e descrição mostram **"Consultando o WikiAves..."** depois que a espécie é identificada (antes ficava "Aguardando identificação....", como se a IA ainda estivesse trabalhando). Sem descrição no WikiAves, o campo passa a dizer "Descrição não disponível no WikiAves." em vez de ficar à espera.
- Textos de nota e de espera ("Aguardando identificação…") passaram de cinza #9CA3AF para #6B7280: o contraste sobre o fundo branco subiu de 2,5:1 para 4,8:1 (mínimo WCAG AA: 4,5:1).

## v1.3

### Novidades
- **Lista nacional (ICMBio/MMA)**: Portaria MMA nº 148/2022 embarcada (257 aves ameaçadas, incluindo 51 subespécies, e 6 extintas), comparada pelo ID do iNaturalist e pelo nome. Subespécies ameaçadas não marcam a espécie inteira.
- **CITES**: anexos de 1.545 espécies e subespécies de aves (Checklist oficial), com sinônimos e populações não listadas.
- **Outras avaliações (iNaturalist)**: listas estaduais e de outros países no card de conservação, com link; a do estado da foto aparece primeiro.
- **Foto já processada**: o app detecta os dados gravados pelo iBirder, mostra o que foi gravado e quando, e pergunta se deve processar novamente ou ignorar. A gravação passa a incluir `iBirder|Registro|Data` e `iBirder|Registro|Versao`, e regravar substitui o registro anterior.
- **Renomear ao gravar**: no diálogo de gravação, opção de renomear a foto para `NomeComum_aaaammdd` (PascalCase, sem acentos; ex.: `SabiaLaranjeira_20261016.jpg`), com os padrões alternativos com a hora ou com o nome científico, nome editável com prévia e validação, sufixo `_2`, `_3` para nomes existentes, RAW e `.xmp` de mesmo nome renomeados junto. A renomeação acontece depois da gravação: se falhar (arquivo aberto em outro programa), os dados continuam gravados.
- **Nome original preservado**: gravado em `XMP-xmpMM:PreservedFileName` (só na primeira vez), no comentário da foto ("Arquivo original: ...", visível no Explorer), na palavra-chave `iBirder|Arquivo|NomeOriginal` e no `.xmp` do RAW (criado se não existir; o RAW não é alterado). Histórico em `logs/renomeacoes.csv`. O app confere o nome original na foto antes de renomear, e o aviso de foto já processada tem o botão **Desfazer renomeação** (volta também o RAW e o `.xmp`, sem nunca sobrescrever).
- **Aviso de região**: espécie sugerida sem registro no Brasil (lista de 1.759 espécies do iNaturalist) para foto do Brasil aciona a nuvem ou um aviso com os candidatos que ocorrem no país; os candidatos são clicáveis.
- **Instalador menor**: o build exclui QML, bibliotecas Qt não usadas (3D, Charts, Quick Controls...), as DevTools e as traduções do navegador interno, exceto português e inglês (cerca de 150 MB a menos antes da compressão).
- Ferramenta de manutenção `tools/atualizar_listas_conservacao.py`.

### Correções
- **Privacidade**: removidos de `assets/exiftool/` oito arquivos de depuração (`dump_*.txt`, `exif_part*.txt`, `exif_structured_final.md`) com os metadados completos de uma foto do autor (GPS, números de série da câmera e da lente, caminho do usuário no Windows). Não eram usados pelo código e iam para o instalador.

## v1.2

### Novidades
- **WikiAves**: busca interna do próprio site (`getTaxonsJSON.php`), aceitando apenas o resultado com o mesmo nome científico e exigindo esse nome na página. Lista vazia significa "espécie não existe no WikiAves": os buscadores externos não são usados (antes, *Haemorhous cassinii* recebia os dados do guaxe). Validado com 10 espécies no Windows.
- **Etapas em paralelo** (biologia, geografia, taxonomia), com dados do iNaturalist centralizados (de ~9 para 2 requisições por espécie).
- **eBird embarcado**: tabela com 11.167 espécies (código, nome em inglês, ordem, família e link oficial).
- **Player de vocalizações nativo** (QtMultimedia/FFmpeg): toca M4A, MP3 e WAV.
- **Mapa incremental** com Leaflet embarcado e GBIF em segundo plano.
- **Logs** persistentes com rotação, chaves de API mascaradas e **Copiar diagnóstico** no menu de ajuda.
- **Chaves de API** (issue #1): passo a passo reescrito para leigos, incluindo o faturamento exigido pelo Google, links diretos para cada tela e tabela de erros. O botão **Testar Chaves** explica o problema (chave inválida, faturamento, API desativada, chave restrita, token expirado), e o token do iNaturalist pode ser colado como a página o mostra.
- **Build automático** no GitHub Actions: testes, executável, autoteste (`--smoke-test`) e instalador; Release automática em tags `vX.Y`.
- Versão definida em um único lugar (`core/config.py`).

### Correções
- Chaves de API do autor estavam versionadas e eram distribuídas no instalador.
- **Endemismo**: a consulta usava o lugar 6857 do iNaturalist (Reino Unido) e um campo que a API não devolve; toda espécie saía "não endêmica" e isso era gravado nas fotos. Agora usa o Brasil (6878) e mostra endêmica/nativa/introduzida.
- **ICMBio e CITES**: deixam de exibir "Não Avaliado"/"Não Listado" (afirmações falsas) e passam a "Não disponível" enquanto as listas não forem integradas.
- **Gravação na foto**:
  - Darwin Core nunca era gravado (tags inexistentes no ExifTool); agora usa a estrutura `Taxon`.
  - GPS do hemisfério sul/oeste era gravado como norte/leste.
  - Palavras-chave duplicavam a cada gravação.
  - Campos desmarcados no diálogo eram gravados mesmo assim.
  - O autor da foto (`dc:creator`) e o software da câmera eram sobrescritos.
  - Valores desconhecidos viravam dados ("Não endêmico", nome comum "Ave").
  - Valores padrão sobrescreviam dados reais quando uma etapa terminava antes da outra.
- **Teste da chave do Google** mostrava "Sucesso" para chaves inválidas.
- **Vocalizações** em M4A (quase metade das do iNaturalist) não tocavam.
- **Mapa**: arrastar o pino e clicar nos pinos de áudio não tinham efeito.
- **Estabilidade**: resultados de uma foto anterior podiam aparecer na atual; threads em execução eram destruídas (risco de travamento); a interface congelava ao trocar a imagem de referência e ao consultar o GBIF.
- Falha no WikiAves interrompia todas as etapas seguintes; sem GPS, a taxonomia nunca era buscada; com o WikiAves indisponível, os campos ficavam em "Aguardando..." e a gravação ficava bloqueada.
- Fotos verticais eram analisadas deitadas.
- O log de erro era apagado ao fechar o app; o log registrava a chave do Google em texto aberto.
- Em modo desenvolvimento, os biomas não carregavam e o app exigia uma pasta `.venv` (não rodava em conda).
- Documentação corrigida: o modelo é uma **MobileNetV2** (não EfficientNet), reconhece 965 espécies do mundo (cerca de 230 do Brasil), o limiar é 70% e as vocalizações vêm do iNaturalist (não do Xeno-Canto).

## v1.1
- Migração do gerenciador de pacotes para `uv`.
- Caminhos de arquivos empacotados (`APP_DIR`/`sys._MEIPASS`) corrigidos no Windows.
- Ícones *line-art* SVG e padronização visual da interface.
- Identificação em cascata na nuvem (iNaturalist e Google Cloud Vision) e botão para testar as chaves.
