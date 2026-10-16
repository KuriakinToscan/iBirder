# Identificação na nuvem (opcional)

O iBirder identifica a ave **no seu computador**, sem internet. Quando essa identificação fica com **menos de 70% de certeza**, o app pode pedir uma segunda opinião a um serviço na nuvem, usando **uma chave sua** (nada é enviado sem uma chave configurada).

- **O que é enviado:** só uma cópia reduzida da foto (até 800 pixels, sem os metadados). A foto original nunca sai do computador.
- **Quando é usado:** apenas quando a IA local está em dúvida.
- **É obrigatório?** Não. Sem chaves, o iBirder funciona normalmente; nas fotos difíceis, você pode usar a **Busca Manual** ou o **Google Lens**.

> **Por que vale a pena no Brasil:** a IA local reconhece 965 espécies de aves do mundo todo, mas só cerca de 230 delas ocorrem no Brasil. Para as demais, a consulta ao iNaturalist faz muita diferença.

## Qual serviço escolher?

| | **iNaturalist** (recomendado) | **Google Cloud Vision** |
|---|---|---|
| Custo | Grátis | Grátis até 1.000 consultas por mês |
| Precisa de cartão de crédito? | Não | **Sim** (o Google exige, mesmo no uso gratuito) |
| Qualidade para aves | Excelente (especialista em biodiversidade) | Genérica (reconhece "ave", "gavião"...) |
| Tempo para configurar | 2 minutos | 15 minutos |
| Validade da chave | Cerca de 24 horas (precisa renovar) | Não expira |

**Resumo:** comece pelo **iNaturalist**. Configure o Google apenas se já usa o Google Cloud ou quer um segundo recurso.

---

## 1. iNaturalist (2 minutos, grátis)

1. Entre na sua conta em [inaturalist.org](https://www.inaturalist.org). Se não tiver conta, crie uma (é grátis).
2. Com a conta aberta, acesse [inaturalist.org/users/api_token](https://www.inaturalist.org/users/api_token).
3. Aparece uma página quase em branco com um texto longo, começando com `{"api_token":"eyJ...`. Selecione **tudo** (Ctrl+A) e copie (Ctrl+C). O iBirder separa o código sozinho.
4. No iBirder, clique na **engrenagem (⚙)**, cole o código em **"Token iNaturalist"** e clique em **Testar Chaves**.
5. Se aparecer ✅, clique em **Salvar**.

> **Atenção:** esse código **vale por cerca de 24 horas**. Quando expirar, o teste mostra "Token inválido ou expirado": basta repetir os passos 2 a 5.

---

## 2. Google Cloud Vision (15 minutos, exige cartão)

**Antes de começar, saiba que:**

- O Google pede um **cartão de crédito** para ativar o serviço, mesmo que você fique dentro da cota gratuita. É a parte que mais confunde: sem o cartão (faturamento), a chave é criada mas **não funciona**.
- A cota gratuita é de **1.000 consultas por mês**. O iBirder só consulta o Google quando a IA local e o iNaturalist não resolvem, então o uso pessoal normal fica muito abaixo disso.
- Para não ter surpresas, o passo 6 mostra como criar um **alerta de gastos**.

Use uma conta Google (Gmail). Os links abaixo abrem direto na tela certa.

### Passo 1: criar um projeto
1. Acesse [console.cloud.google.com/projectcreate](https://console.cloud.google.com/projectcreate).
2. Em **Nome do projeto**, digite `iBirder` e clique em **Criar**.
3. Aguarde alguns segundos e confira, no topo da página, se o projeto **iBirder** está selecionado.

### Passo 2: ativar o faturamento (cartão)
1. Acesse [console.cloud.google.com/billing](https://console.cloud.google.com/billing).
2. Se ainda não tiver uma conta de faturamento, clique em **Criar conta** (ou **Adicionar conta de faturamento**) e informe o cartão. O Google pode oferecer um **teste gratuito com créditos**: pode aceitar.
3. Confira se o projeto **iBirder** está vinculado a essa conta de faturamento (em **Gerenciar contas de faturamento** > **Meus projetos**).

### Passo 3: ativar a Cloud Vision API
1. Acesse [console.cloud.google.com/apis/library/vision.googleapis.com](https://console.cloud.google.com/apis/library/vision.googleapis.com).
2. Com o projeto **iBirder** selecionado no topo, clique em **Ativar**.

### Passo 4: criar a chave
1. Acesse [console.cloud.google.com/apis/credentials](https://console.cloud.google.com/apis/credentials).
2. Clique em **+ Criar credenciais** > **Chave de API**.
3. Aparece a chave, um código que começa com `AIza`. Clique no botão de **copiar**.

### Passo 5 (recomendado): proteger a chave
1. Na mesma tela, clique no nome da chave criada.
2. Em **Restrições de API**, escolha **Restringir chave** e marque apenas **Cloud Vision API**.
3. Em **Restrições de aplicativo**, deixe **Nenhuma**.
4. Clique em **Salvar**.

Assim, se a chave vazar, ela só serve para a Cloud Vision.

### Passo 6 (recomendado): alerta de gastos
1. Acesse [console.cloud.google.com/billing](https://console.cloud.google.com/billing), abra sua conta de faturamento e clique em **Orçamentos e alertas**.
2. Clique em **Criar orçamento**, defina um valor baixo (por exemplo, R$ 5) e conclua.

Você recebe um e-mail se houver qualquer cobrança perto desse valor.

### Passo 7: colar no iBirder
1. No iBirder, clique na **engrenagem (⚙)** e cole a chave em **"Chave Google Vision"**.
2. Clique em **Testar Chaves**. Se aparecer ✅, clique em **Salvar**.

---

## Se o teste mostrar ❌

O botão **Testar Chaves** diz exatamente o que falta:

| Mensagem | O que fazer |
|---|---|
| **Chave inválida** | A chave foi copiada pela metade ou apagada. Copie de novo (passo 4). |
| **O faturamento não está ativado** | Faça o passo 2 e confira se o projeto está vinculado à conta de faturamento. |
| **A Cloud Vision API não está ativada** | Faça o passo 3. Se acabou de ativar, aguarde 2 a 5 minutos. |
| **A chave está restrita** | Revise o passo 5: permita a Cloud Vision API e deixe "Restrições de aplicativo" como "Nenhuma". |
| **Token inválido ou expirado** (iNaturalist) | Gere um novo token (passos 2 a 5 da seção do iNaturalist). |
| **Sem conexão** | Verifique a internet ou o firewall da rede (redes corporativas podem bloquear). |

## Como saber se está funcionando no dia a dia?

Ao identificar uma foto difícil, observe a barra de status, na parte de baixo da janela. Aparecem mensagens como **"Confiança local baixa. Consultando iNaturalist (Nuvem)..."**. Quando a nuvem resolve, a linha **Certeza** mostra a fonte, por exemplo: `iNaturalist API (Nuvem)`.
