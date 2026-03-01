# Relatório: Informações da Caderneta de Campo (iBirder)

Este documento detalha todas as informações salvas na **Caderneta de Campo** do iBirder, organizadas por etapa de processamento e indicando suas respectivas fontes de dados.

---

### 📔 Estrutura da Caderneta de Campo (SessionLogger)
A caderneta funciona como um log de sessão temporário (arquivo JSON) que armazena os dados coletados ao longo do pipeline de identificação.

---

### 🟢 Etapa 1: Identificação de Espécie
*   **Fonte:** Inteligência Artificial Local (Modelo *iNaturalist Vision* via TFLite).
*   **Informações Salvas:**
    *   `nome_cientifico`: O nome taxonômico principal identificado (ex: *Turdus rufiventris*).
    *   `confianca`: O nível de certeza da IA (0.0 a 1.0).
    *   `status_msg`: Mensagem de status da identificação (ex: "Baixa confiança" ou "Identificação local").
    *   `top3`: Lista das 3 espécies mais prováveis com suas respectivas confianças.

### 🔵 Etapa 2: Biologia e Etimologia
*   **Fonte:** [WikiAves](https://www.wikiaves.com.br) (via Scraper automatizado).
*   **Informações Salvas:**
    *   `nome_comum`: Nome popular da ave em português (ex: Sabiá-laranjeira).
    *   `nome_ingles`: Nome comum internacional oficial (ex: Rufous-bellied Thrush). [v0.8.3]
    *   `etimologia`: A origem e significado do nome científico.
    *   `descricao`: Características físicas detalhadas da espécie.
    *   `link_origem`: URL direta para a página da espécie no WikiAves.
    *   `status_conservacao`: Categoria de ameaça (extraído da página).

### 🟠 Etapa 3: Geografia e Conservação Nacional
*   **Fontes:** 
    *   Administrativo: **Nominatim (OpenStreetMap)** via API.
    *   Ecológico: **GeoJSON Local** (`biomas.geojson`).
    *   Conservação Global: **IUCN Red List** (via `IUCNWorker`).
    *   Conservação Nacional: **ICMBio / SALVE** e **JBRJ** (Catálogo Taxonômico da Fauna do Brasil).
    *   Comércio Internacional: **CITES** (Convenção sobre o Comércio Internacional).
*   **Informações Salvas:**
    *   `iucn_status`: Status de conservação global (Termo por extenso em português, ex: "Vulnerável").
    *   `status_icmbio`: Status de ameaça oficial no Brasil via ICMBio (Termo por extenso).
    *   `status_cites`: Status de controle de comércio internacional (Anexos I, II ou III).
    *   `endemismo`: Indica se a espécie é **"Endêmica do Brasil"**.
    *   `msg_distribuicao`: Alerta de sanidade geográfica (ex: **"Fora da distribuição conhecida"**).
    *   `pais` / `estado` / `municipio`: Dados administrativos da localização da foto.
    *   `bioma`: Bioma ecológico onde a ave foi registrada (ex: Mata Atlântica, Cerrado).
    *   `lat` / `lon`: Coordenadas geográficas exatas (extraídas do EXIF ou mapa).

### 🟣 Etapa 4: Vocalizações (Áudio)
*   **Fonte:** [iNaturalist API](https://api.inaturalist.org) (com ranking geográfico regionalizado).
*   **Informações Salvas:**
    *   `vocalizacoes`: Quantidade total de registros de áudio encontrados na região.
    *   `vocal_top1, 2 e 3`: Detalhes dos 3 melhores áudios selecionados (distância, localidade, camada e links).

### 🟡 Etapa 5: Taxonomia Complementar
*   **Fonte:** [iNaturalist](https://api.inaturalist.org) / [eBird](https://ebird.org).
*   **Informações Salvas:**
    *   `classe` / `ordem` / `familia`: Classificação taxonômica completa.
    *   `ebird_code`: Código único da espécie no sistema eBird.
    *   `raridade_regional`: Status de raridade conforme base regional.
    *   `link_ebird`: Link para a página da espécie no eBird.

---

### 🚀 Processamento e Persistência
1.  **Orchestrator:** Gerencia a execução sequencial das 5 etapas, incluindo a nova lógica de **Soberania de Dados** (Prioridade JBRJ/ICMBio no Brasil vs Fallback Global).
2.  **Batch Flush:** Os dados são acumulados na memória RAM e gravados no disco (arquivo JSON) somente após a conclusão da Etapa 5, garantindo a integridade da caderneta.
3.  **Metadados (Etapa 6):** Placeholder para gravação direta no EXIF da fotografia.
