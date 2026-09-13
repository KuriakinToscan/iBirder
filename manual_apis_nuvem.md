# Manual de Configuração de APIs (Nuvem) - iBirder v1.1

A partir da versão 1.1, o iBirder conta com um poderoso sistema de identificação em cascata. Isso significa que, caso a Inteligência Artificial Local tenha dúvidas sobre a foto (Confiança < 70%), o aplicativo pode consultar os supercomputadores do **iNaturalist** ou do **Google Vision** automaticamente para tentar salvar a sua identificação.

Para proteger a sua privacidade e evitar custos centralizados, o iBirder usa o modelo **Bring Your Own Key (Traga Sua Própria Chave)**. Siga o passo a passo abaixo para gerar as suas chaves gratuitas e turbinar o seu app.

---

## 1. Configurando o iNaturalist (Recomendado)

O iNaturalist possui o melhor modelo de identificação de biodiversidade do mundo. A API deles é restrita, mas pesquisadores e usuários avançados podem usar um token JWT (JSON Web Token) atrelado à própria conta.

### Passo a passo para obter o Token:
1. Acesse o site do [iNaturalist](https://www.inaturalist.org) e faça login na sua conta.
2. Abra uma nova aba no seu navegador e acesse a página de API para desenvolvedores: `https://www.inaturalist.org/users/api_token`
3. Você verá uma página em branco contendo apenas um bloco de texto grande com várias letras e números, semelhante a isto: `eyJhbGciOiJIUzUxMiJ9.eyJ1c2VyX2lk...`
4. **Copie todo este texto**.
5. Abra o **iBirder**.
6. Clique no ícone de **Engrenagem (⚙)** no canto superior direito.
7. Cole o texto copiado no campo **"Token iNaturalist"** e clique em Salvar.

> **⚠️ Atenção:** O token do iNaturalist expira de tempos em tempos (geralmente a cada 24 horas). Se a identificação em nuvem parar de funcionar, basta repetir este processo.

---

## 2. Configurando o Google Cloud Vision (Avançado)

O Google Cloud Vision é um excelente classificador genérico. Se o iNaturalist falhar, ele ajuda a pelo menos identificar se é um pássaro específico, pato, gavião, etc., analisando inclusive registros similares espalhados pela Web.

### Passo a passo para obter a API Key do Google:
1. Acesse o [Google Cloud Console](https://console.cloud.google.com/).
2. Crie um novo projeto (ex: `iBirder-Vision`).
3. Vá em **"APIs e Serviços"** > **"Biblioteca"**.
4. Pesquise por **Cloud Vision API** e clique em **Ativar**.
5. No menu lateral, vá em **"APIs e Serviços"** > **"Credenciais"**.
6. Clique em **"+ Criar Credenciais"** e selecione **"Chave de API"** (API Key).
7. Uma janela aparecerá com sua chave (`AIzaSy...`). **Copie esta chave**.
   - *(Recomendado: Clique em "Restringir Chave" e limite-a apenas à "Cloud Vision API" para sua segurança).*
8. Abra o **iBirder**, clique na **Engrenagem (⚙)**, cole a chave no campo **"Chave Google Vision"** e clique em Salvar.

> **💰 Sobre custos:** O Google Cloud Vision oferece 1.000 (mil) requisições gratuitas por mês. Como o iBirder só aciona o Google quando a IA local falha, é quase impossível você ultrapassar esse limite no uso diário comum.

---

## Como testar se está funcionando?

1. Carregue no iBirder uma foto bem borrada ou de uma ave que o modelo local normalmente não conhece.
2. Fique de olho na barra de status inferior.
3. Você deverá ver a mensagem `"Analisando imagem..."` e, logo em seguida, `"Confiança local baixa. Consultando iNaturalist (Nuvem)..."` ou `"Consultando Google Vision..."`.
4. Se o resultado aparecer com sucesso (e o texto de descrição disser "Identificado na nuvem..."), a sua configuração está perfeita!
