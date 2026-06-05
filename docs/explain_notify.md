# Explicações — Script de Notificação por E-mail

## O que foi feito na ETAPA 2

### O arquivo criado

**`scripts/notify.py`** — é um script Python que envia um e-mail ao final do pipeline Jenkins, informando se os testes passaram ou falharam.

---

## Como o script funciona

### 1. Leitura de variáveis de ambiente

```python
SMTP_HOST   = os.environ.get("SMTP_HOST", "mailhog")      # padrão: mailhog
SMTP_PORT   = int(os.environ.get("SMTP_PORT", "1025"))    # padrão: 1025
EMAIL_TO    = os.environ["EMAIL_TO"]                       # OBRIGATÓRIO — erro se faltar
EMAIL_FROM  = os.environ.get("EMAIL_FROM", "jenkins@steamapi.local")
```

O script **não hardcoda** nada. Tudo vem de variáveis de ambiente:
- Se a variável existir, usa seu valor
- Se não existir, usa um padrão (com `.get()`)
- `EMAIL_TO` é exceção — **não tem padrão**. Sem ela, o script falha imediatamente

**Por quê?** Porque a chave SMTP, o servidor e o e-mail mudam conforme o ambiente (dev, CI, produção).

### 2. Captura de informações do Jenkins

```python
BUILD_STATUS = sys.argv[1]              # vem da linha de comando
BUILD_NUMBER = os.environ.get("BUILD_NUMBER", "?")
BUILD_URL    = os.environ.get("BUILD_URL", "#")
```

O script recebe o **status da build** como argumento: `python3 scripts/notify.py SUCCESS` ou `python3 scripts/notify.py FAILURE`.

Jenkins injeta automaticamente `BUILD_NUMBER` e `BUILD_URL` em todas as builds.

### 3. Montagem do e-mail

```python
msg = MIMEMultipart()
msg["From"]    = EMAIL_FROM
msg["To"]      = EMAIL_TO
msg["Subject"] = f"[Steam API Tests] Build #{BUILD_NUMBER} — {BUILD_STATUS}"
msg.attach(MIMEText(body, "plain"))
```

Cria um e-mail estruturado com cabeçalhos (From, To, Subject) e corpo de texto.

### 4. Envio via SMTP

```python
with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
    server.sendmail(EMAIL_FROM, EMAIL_TO, msg.as_string())
```

Conecta ao servidor SMTP (MailHog no desenvolvimento) e envia o e-mail.

Se falhar, o script imprime o erro e sai com `sys.exit(1)` — Jenkins detecta a falha.

---

## Por que Python?

| Vantagem | Motivo |
|---|---|
| Nativa em Linux | Vem instalado na maioria das distribuições e imagens Docker |
| `smtplib` nativa | Não precisa instalar pacotes extras para SMTP |
| Legível | Fácil de entender, defender e modificar |
| Simples | Sem dependências externas = container mais leve |

Poderíamos usar Node.js, Shell script ou outras linguagens — mas Python é o mais direto para SMTP.

---

## Por que MailHog em desenvolvimento?

| Aspecto | SMTP Real | MailHog |
|---|---|---|
| **Conta necessária?** | Sim (Gmail, Outlook, etc.) | Não |
| **Credenciais no código?** | Arriscado | Desnecessário |
| **Visualizar e-mail?** | Caixa de entrada real | Interface web local |
| **Envio real?** | Sim — e-mail sai mesmo | Não — captura apenas |
| **Ideal para dev/teste?** | Não | Sim ✅ |

**Durante a defesa**, você acessa `http://localhost:8025` e mostra o e-mail recebido em tempo real — perfeito para demonstração.

---

## Como o script se encaixa no pipeline

No `Jenkinsfile`:

```groovy
post {
    always {
        sh "python3 scripts/notify.py ${currentBuild.currentResult}"
    }
}```

---

## Correção importante: python3 e zip não existem no Jenkins

A imagem `jenkins/jenkins:lts` é um Linux Debian mínimo — ela **não vem com `python3` nem com `zip` instalados**. Sem eles, o pipeline quebraria:
- Stage `Build` → `zip: command not found`
- `post.always` → `python3: command not found`

A solução foi adicionar um stage `Setup` **antes** de todos os outros, que instala esses pacotes:

```groovy
stage('Setup') {
    steps {
        sh 'apt-get update && apt-get install -y zip python3 --no-install-recommends'
    }
}
```

**Por que `--no-install-recommends`?** Evita instalar pacotes extras sugeridos pelo apt, mantendo a instalação mínima e rápida.

**Por que instalar no pipeline e não num Dockerfile do Jenkins?** Porque o professor exige que só o `newman-runner` tenha Dockerfile próprio. Para o Jenkins, a solução permitida é instalar via script dentro do próprio pipeline — que é exatamente o que o `apt-get` no stage `Setup` faz.
```

Após todas as etapas (stage Test, stage Build), o Jenkins executa:
- `python3 scripts/notify.py SUCCESS` — se tudo passou
- `python3 scripts/notify.py FAILURE` — se algo falhou

`always` garante que a notificação é enviada em **qualquer resultado** — não só em sucesso.

---

## Variáveis de ambiente no docker-compose.yml

```yaml
jenkins:
  environment:
    - NOTIFY_EMAIL=${NOTIFY_EMAIL}      # vem do arquivo .env
```

Você define no `.env`:
```
NOTIFY_EMAIL=seu-email@exemplo.com
```

O Docker Compose passa para o container Jenkins. O Jenkinsfile lê e passa para o script.

**Fluxo:**
```
.env (NOTIFY_EMAIL=seu-email@exemplo.com)
  ↓
docker-compose.yml (environment)
  ↓
Jenkins container (variável de ambiente)
  ↓
Jenkinsfile (${env.NOTIFY_EMAIL})
  ↓
scripts/notify.py (os.environ["EMAIL_TO"])
```

---

## O que acontece se algo der errado

| Cenário | Resultado |
|---|---|
| `EMAIL_TO` não definida | Script falha imediatamente com `KeyError` |
| MailHog offline | Timeout da conexão SMTP — script falha e sai com `sys.exit(1)` |
| Permissões SMTP negadas | Exceção capturada — imprime erro e falha |
| Tudo OK | E-mail enviado, script imprime "E-mail enviado para..." e sai com sucesso |

Jenkins vê `sys.exit(1)` como falha — a build fica marcada com problema, mas não afeta os artefatos (estão já arquivados no stage anterior).
