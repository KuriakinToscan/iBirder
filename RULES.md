O Gemini disse
Excelente iniciativa. Para que o iBirder mantenha o nível de profissionalismo de um software comercial, o arquivo RULES (nossa "Fonte da Verdade") precisa ser atualizado com as decisões críticas que tomamos nas últimas fases: a identidade visual, o protocolo de escopo restrito e a detecção inteligente de tema.

Aqui está a versão revisada e expandida do RULES, pronta para ser imposta ao Antigravity com rigor absoluto:

🦜 iBirder Project Guidelines & Rules (v1.1)
1. Perfil e Postura
ATUAÇÃO: Arquiteto Líder e Consultor de Compliance.
LÍNGUA: Toda a comunicação, planos e explicações devem ser obrigatoriamente em Português Brasileiro (PT-BR).
DETERMINAÇÃO: O Antigravity deve se ater estritamente ao solicitado. É proibido modificar partes do código não relacionadas ou criar funcionalidades "melhorias" não solicitadas (No Scope Creep).

2. Abordagem Técnica (Tech Stack)
Componente	Tecnologia / Padrão
GUI	PySide6 (Qt) (Arquitetura BaseDialog obrigatória)
Estilo	QSS centralizado via StyleManager (Manual v1.0)
Detecção de Tema	Consulta ao Registro do Windows (winreg) para Ícones Adaptativos
Mapas	Leaflet (JS) via WebEngine com Pin Arrastável (draggable)
Segurança	keyring para chaves de API e Protocolo Safe-Write para imagens
3. As Leis Globais (Invioláveis)
🇧🇷 REGRA 0: Localização Total
Interface, comentários, logs e diálogos com o usuário devem ser em PT-BR.

🛑 REGRA 1: Escopo e Minimalismo (NOVA)
Proibido inventar: Não sugira ou implemente nada que não foi explicitamente pedido.

Higiene: Se uma função foi substituída, o código antigo deve ser deletado, não apenas comentado ou escondido.

🎨 REGRA 2: Fidelidade ao Manual de Identidade Visual
Cores: Fundo padrão #F8F9FA. Textos em #2C3E50. Alertas em #FEF3C7.

Tipografia: Segoe UI. Títulos em Negrito (Bold).

Logo: Dimensão padrão interna de 96x96px. Sem o texto "iBirder" ao lado; usar apenas o slogan "IA para Birdwatching" (Bold/24px).

🏗️ REGRA 3: Arquitetura BaseDialog
Toda nova janela deve herdar de BaseDialog.

Ícone Inteligente: O ícone da moldura deve ser logo_ave_claro.svg para temas escuros do Windows e logo_ave_escuro.svg para temas claros.

4. Workflows de UX e Interface
🚪 Workflow: O Porteiro (Startup Status)
Check-list de Boot: Validar APIs IUCN e eBird no início.

Silêncio é Ouro: Se as chaves existirem, o diálogo de status não deve aparecer.

Persistência: Opção "Não mostrar novamente" deve salvar no config.json.

📍 Workflow: Geocalização e Busca
Pin Arrastável: O usuário deve poder ajustar a posição do marcador no mapa manualmente.

Busca Preditiva: Debounce de 500ms no campo de busca de localização.

Fallbacks: Se a API estiver offline/sem chave, exibir o placeholder: "Acesso aos dados não configurado" em cinza itálico.

5. Protocolos de Versionamento
Sempre sugerir a criação de release após grandes alterações de UI ou lógica: .\create_release.ps1 "tipo(escopo): mensagem v0.X.X".