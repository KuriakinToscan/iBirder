# Histórico de versões

## Próxima versão (em desenvolvimento)

### Novidades
- **Temas de aparência**: Off-White (o visual de sempre), Clean (fundo branco, fonte Figtree, verde-petróleo nas ações principais) e Clássico (papel creme, títulos com serifa Georgia, verde-musgo). A escolha fica em **Configurações (⚙) > Aparência**, é aplicada na hora, sem reiniciar, e cada tema usa o logo original recolorido. Toda cor da interface passou a vir de tokens (`core/temas.py`).
- **Layout da janela principal** (base): **Configurações (⚙) > Aparência** ganhou a escolha do layout, separada do tema. Por enquanto há só o **Painel completo** (a tela de sempre); Fluxo guiado, Ficha compacta e Mesa de trabalho aparecem como "em breve". Internamente, a janela passou a ser montada a partir de painéis (`ui/layouts/`) e a etapa da identificação fica em `ui/estado_identificacao.py`.
- **Botão principal destacado**: **Gravar Dados na Fotografia**, **Salvar** e as ações principais dos diálogos usam a cor de destaque do tema; botões desativados ficam visualmente diferentes dos ativos.
- **Aviso de novas versões**: ao abrir, o app consulta a última Release no GitHub (no máximo uma vez a cada 24 h) e, se houver versão nova, mostra as novidades com os botões **Baixar instalador** (link direto do `.exe`), **Ver no GitHub**, **Lembrar depois** e **Ignorar esta versão**, além de um aviso na barra de status. **Ajuda (?) > Verificar atualizações** consulta na hora, e o aviso pode ser desligado nas configurações (⚙). Antes, só aparecia um botão discreto na barra de status, a consulta era feita a cada abertura e as falhas não eram informadas.
- **Instalador**: ao atualizar por cima, apaga a pasta `_internal` da versão anterior antes de copiar a nova (arquivos removidos não ficam para trás), fecha o iBirder se estiver aberto e fixa o `AppId` usado desde a v1.1. Configurações e chaves (`%APPDATA%\iBirder`) são mantidas.

### Correções
- Etimologia e descrição mostram **"Consultando o WikiAves..."** depois que a espécie é identificada (antes ficava "Aguardando identificação....", como se a IA ainda estivesse trabalhando). Sem descrição no WikiAves, o campo passa a dizer "Descrição não disponível no WikiAves." em vez de ficar à espera.
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
