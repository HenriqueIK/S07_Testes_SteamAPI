# Plano DevOps — S07 Testes Steam API

> **O que é esse arquivo?**
> Este documento é o roteiro completo do que o grupo precisa implementar para atender todos
> os requisitos da atividade. Cada etapa explica **o que fazer**, **por que fazer** e **como fazer**.
> Siga a ordem — cada bloco depende do anterior.

---

## Visão geral da arquitetura final

```
┌──────────────────────────────────────────────────────────────┐
│                    Docker Compose                            │
│                                                              │
│  ┌─────────────┐     dispara      ┌──────────────────────┐  │
│  │   Jenkins   │ ─────────────►  │   Newman Runner      │  │
│  │  (container)│                  │ (Dockerfile.newman)  │  │
│  └──────┬──────┘                  └──────────┬───────────┘  │
│         │ envia e-mail                        │ gera         │
│         ▼                                     ▼ relatórios   │
│  ┌─────────────┐                  ┌──────────────────────┐  │
│  │   MailHog   │                  │   Nginx (reports)    │  │
│  │ (SMTP mock) │                  │  serve os HTMLs      │  │
│  └─────────────┘                  └──────────────────────┘  │
│                                                              │
│  Volumes: jenkins_home | reports                             │
└──────────────────────────────────────────────────────────────┘
```

**Por quê essa arquitetura?**
- O projeto já tem testes prontos com Newman — aproveitamos isso.
- Jenkins orquestra o pipeline e roda os testes Newman no próprio agente Jenkins.
- MailHog é um servidor SMTP falso (ideal para dev/lab): captura os e-mails sem precisar
  de conta real — perfeito para demonstrar a etapa de notificação.
- Nginx serve os relatórios HTML já gerados pelo Newman, cumprindo o requisito de
  artefatos acessíveis.
- Total: **4 containers** ✔, comunicação entre Jenkins ↔ MailHog e relatórios compartilhados via volume ✔,
  volume persistindo relatórios ✔.

---

## Checklist geral

- [ ] **ETAPA 1** — Dockerfile.newman do Newman Runner
- [ ] **ETAPA 2** — Script de notificação por e-mail
- [ ] **ETAPA 3** — Jenkinsfile (pipeline completo)
- [ ] **ETAPA 4** — Docker Compose (4 containers)
- [ ] **ETAPA 5** — Publicar imagens no Docker Hub
- [ ] **ETAPA 6** — Atualizar o README (seção "Uso de IA" e demais requisitos)
- [ ] **ETAPA 7** — Publicar no repositório do time no GitHub
- [ ] **ETAPA 8** — Testar o pipeline completo ao vivo

---

## ETAPA 1 — Dockerfile.newman do Newman Runner

### Para que serve?
O `Dockerfile.newman` transforma o projeto (coleções Postman + dependências Node) em uma
**imagem Docker imutável**. Assim, os testes sempre rodam no mesmo ambiente, em qualquer
máquina, sem depender de Node instalado localmente.

### O que criar?
Crie o arquivo `Dockerfile.newman` na raiz do projeto:

```dockerfile
# Dockerfile.newman
FROM node:20-alpine

# Define diretório de trabalho dentro do container
WORKDIR /app

# Copia os arquivos de dependência primeiro (otimiza cache do Docker)
COPY package.json package-lock.json ./

# Instala as dependências (newman + newman-reporter-htmlextra)
RUN npm ci

# Copia todo o restante do projeto (coleções, environments, scripts)
COPY . .

# Cria a pasta de relatórios (será montada como volume pelo Compose)
RUN mkdir -p reports

# Comando padrão: roda todos os testes
CMD ["npm", "run", "test:all"]
```

### Por que `node:20-alpine`?
Alpine é uma distribuição Linux mínima — imagem menor, mais rápida de baixar e mais segura.

### Atenção ao `.dockerignore`
Crie também um `.dockerignore` para não copiar arquivos desnecessários:

```
node_modules
reports
steam_api.postman_environment.json
.git
*.md
```

> **Importante:** o arquivo de environment real (`steam_api.postman_environment.json`)
> com a chave da Steam **não deve entrar na imagem**. Ele será injetado via variável de
> ambiente ou volume em tempo de execução.

---

## ETAPA 2 — Script de notificação por e-mail

### Para que serve?
O professor exige que uma **notificação por e-mail seja enviada** ao final do pipeline,
e que o endereço de e-mail **não seja fixo no código** (variável de ambiente obrigatória).

### O que criar?
Crie a pasta `scripts/` e dentro dela o arquivo `notify.py`:

```
scripts/
└── notify.py
```

```python
# scripts/notify.py
import smtplib
import os
import sys
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# ─── Leitura de variáveis de ambiente ─────────────────────────────────────────
SMTP_HOST   = os.environ.get("SMTP_HOST", "mailhog")
SMTP_PORT   = int(os.environ.get("SMTP_PORT", "1025"))
EMAIL_TO    = os.environ["EMAIL_TO"]          # Obrigatório — erro se ausente
EMAIL_FROM  = os.environ.get("EMAIL_FROM", "jenkins@steamapi.local")

BUILD_STATUS = sys.argv[1] if len(sys.argv) > 1 else "DESCONHECIDO"
BUILD_NUMBER = os.environ.get("BUILD_NUMBER", "?")
BUILD_URL    = os.environ.get("BUILD_URL", "#")

# ─── Montagem do e-mail ────────────────────────────────────────────────────────
subject = f"[Steam API Tests] Build #{BUILD_NUMBER} — {BUILD_STATUS}"

body = f"""
Pipeline Jenkins — Steam API Testes Automatizados

Status   : {BUILD_STATUS}
Build    : #{BUILD_NUMBER}
URL      : {BUILD_URL}

Verifique os artefatos no Jenkins para os relatórios HTML completos.
"""

msg = MIMEMultipart()
msg["From"]    = EMAIL_FROM
msg["To"]      = EMAIL_TO
msg["Subject"] = subject
msg.attach(MIMEText(body, "plain"))

# ─── Envio ─────────────────────────────────────────────────────────────────────
try:
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.sendmail(EMAIL_FROM, EMAIL_TO, msg.as_string())
    print(f"E-mail enviado para {EMAIL_TO} via {SMTP_HOST}:{SMTP_PORT}")
except Exception as e:
    print(f"Falha ao enviar e-mail: {e}", file=sys.stderr)
    sys.exit(1)
```

### Por que Python?
Python vem instalado na maioria das imagens base e tem a biblioteca `smtplib` nativa —
sem necessidade de instalar pacotes extras. O script é simples, legível e fácil de defender.

### Por que MailHog?
MailHog é um servidor SMTP falso com interface web. Ele **captura** os e-mails enviados
pelo script sem realmente entregá-los. Durante a defesa, você pode abrir `http://localhost:8025`
e mostrar o e-mail recebido em tempo real — ótimo para demonstração.

---

## ETAPA 3 — Jenkinsfile

### Para que serve?
O `Jenkinsfile` é o **pipeline declarativo** que define todas as etapas de CI/CD.
Ele fica no repositório (Infrastructure as Code) — nenhuma etapa é configurada pela
interface gráfica do Jenkins.

### O que criar?
Crie o arquivo `Jenkinsfile` na raiz do projeto:

```groovy
// Jenkinsfile
pipeline {
    agent any

    environment {
        // E-mail de notificação — definido como variável de ambiente no Jenkins
        // Nunca hardcoded aqui!
        EMAIL_TO   = "${env.NOTIFY_EMAIL}"
        SMTP_HOST  = "mailhog"
        SMTP_PORT  = "1025"
        BUILD_URL  = "${env.BUILD_URL}"
    }

    stages {

        // ── 1. Checkout ────────────────────────────────────────────────────────
        // Único passo que pode ser feito pela interface gráfica do Jenkins
        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Prepare') {
            steps {
                sh '''
                    mkdir -p reports /shared-reports
                    cp /var/jenkins_home/steam_api.postman_environment.json steam_api.postman_environment.json
                '''
            }
        }

        // ── 2. Instalar dependências ───────────────────────────────────────────
        stage('Install') {
            steps {
                sh 'npm ci'
            }
        }

        // ── 3. Executar testes ─────────────────────────────────────────────────
        // Newman roda as 3 coleções e gera relatórios HTML em reports/
        stage('Test') {
            steps {
                catchError(buildResult: 'UNSTABLE', stageResult: 'FAILURE') {
                    sh '''
                        set +e
                        npm run test:summaries
                        status_summaries=$?
                        npm run test:recent
                        status_recent=$?
                        npm run test:owned
                        status_owned=$?

                        if [ "$status_summaries" -ne 0 ] || [ "$status_recent" -ne 0 ] || [ "$status_owned" -ne 0 ]; then
                            exit 1
                        fi
                    '''
                }
            }
            post {
                always {
                    sh 'cp -f reports/*.html /shared-reports/ 2>/dev/null || true'
                    // Arquiva os relatórios HTML como artefatos no Jenkins
                    archiveArtifacts artifacts: 'reports/*.html', allowEmptyArchive: true
                }
            }
        }

        // ── 4. Build / empacotamento ───────────────────────────────────────────
        // Cria um .zip com as coleções + relatórios para artefato de entrega
        stage('Build') {
            steps {
                sh 'zip -r steam-api-tests.zip *.json reports/ scripts/ Dockerfile.newman Dockerfile.jenkins'
            }
            post {
                always {
                    archiveArtifacts artifacts: 'steam-api-tests.zip', allowEmptyArchive: true
                }
            }
        }
    }

    // ── 5. Notificação por e-mail (pós-pipeline) ───────────────────────────────
    post {
        always {
            sh "python3 scripts/notify.py ${currentBuild.currentResult}"
        }
    }
}
```

### Explicação de cada stage

| Stage | O que faz | Por que é necessário |
|---|---|---|
| `Checkout` | Baixa o código do GitHub | Ponto de entrada do pipeline |
| `Prepare` | Copia o environment montado e cria pastas de relatório | Mantém a chave fora do Git e prepara o volume do Nginx |
| `Install` | Roda `npm ci` | Garante dependências exatas do `package-lock.json` |
| `Test` | Executa as 3 coleções Newman e gera HTMLs | Requisito principal: cobertura de testes, marcando falhas como `UNSTABLE` |
| `Build` | Empacota tudo em `.zip` | Requisito: artefato de build no Jenkins |
| `post.always` | Chama `notify.py` | Requisito: notificação por e-mail em qualquer resultado |

### Como configurar `NOTIFY_EMAIL` no Jenkins (sem interface de pipeline)
1. Acesse **Jenkins → Manage Jenkins → Configure System** (ou **Credentials**).
2. Em **Global properties**, adicione a variável de ambiente `NOTIFY_EMAIL` com o e-mail do grupo.
3. Isso é permitido — a restrição é não criar **etapas** de pipeline pela UI, não variáveis globais.

---

## ETAPA 4 — Docker Compose

### Para que serve?
O `docker-compose.yml` sobe **toda a infraestrutura com um único comando**.
Define os 4 containers, suas dependências, volumes e redes — tudo como código.

### O que criar?
Crie o arquivo `docker-compose.yml` na raiz do projeto:

```yaml
# docker-compose.yml
version: '3.9'

services:

  # ── Container 1: Jenkins ────────────────────────────────────────────────────
  # Imagem customizada do Jenkins com Node.js, npm, zip e Python.
  jenkins:
    image: seuusuario/steam-api-jenkins:latest
    container_name: jenkins
    ports:
      - "8080:8080"    # Interface web do Jenkins
      - "50000:50000"  # Porta de agentes Jenkins
    volumes:
      - jenkins_home:/var/jenkins_home          # Persiste configurações e jobs
      - reports:/shared-reports                 # Compartilha relatórios com o Nginx
      - ./steam_api.postman_environment.json:/var/jenkins_home/steam_api.postman_environment.json:ro
    environment:
      - NOTIFY_EMAIL=${NOTIFY_EMAIL}            # Passado via arquivo .env
    networks:
      - devops-net
    depends_on:
      - mailhog

  # ── Container 2: Newman Runner ──────────────────────────────────────────────
  # Construído a partir do Dockerfile.newman local. Executa os testes da Steam API.
  newman-runner:
    build:
      context: .
      dockerfile: Dockerfile.newman
    image: seuusuario/steam-api-tests:latest
    container_name: newman-runner
    volumes:
      - reports:/app/reports                   # Persiste relatórios para o Nginx
      - ./steam_api.postman_environment.json:/app/steam_api.postman_environment.json:ro
    environment:
      - STEAM_API_KEY=${STEAM_API_KEY}         # Chave Steam via .env (nunca no código)
      - STEAM_ID=${STEAM_ID}
    networks:
      - devops-net
    # Roda os testes e encerra (não é um serviço contínuo)
    command: ["npm", "run", "test:all"]

  # ── Container 3: MailHog ────────────────────────────────────────────────────
  # Servidor SMTP falso. Captura e-mails do Jenkins sem enviá-los de verdade.
  mailhog:
    image: mailhog/mailhog:latest
    container_name: mailhog
    ports:
      - "1025:1025"   # Porta SMTP (usada pelo notify.py)
      - "8025:8025"   # Interface web para visualizar e-mails recebidos
    networks:
      - devops-net

  # ── Container 4: Nginx (servidor de relatórios) ─────────────────────────────
  # Serve os HTMLs gerados pelo Newman como páginas web acessíveis.
  report-server:
    image: nginx:alpine
    container_name: report-server
    ports:
      - "8090:80"     # Acesse em http://localhost:8090
    volumes:
      - reports:/usr/share/nginx/html:ro      # Lê os relatórios gerados pelo newman-runner
    networks:
      - devops-net
    depends_on:
      - newman-runner

# ── Volumes ──────────────────────────────────────────────────────────────────
volumes:
  jenkins_home:   # Persiste todo estado do Jenkins entre reinicializações
  reports:        # Compartilhado entre newman-runner (escrita) e nginx (leitura)

# ── Rede interna ─────────────────────────────────────────────────────────────
networks:
  devops-net:
    driver: bridge
```

### Crie também o arquivo `.env.example`
**Nunca** commite o `.env` real — crie um exemplo para guiar o grupo:

```
# .env.example
NOTIFY_EMAIL=seu-email@exemplo.com
STEAM_API_KEY=SUA_CHAVE_STEAM_AQUI
STEAM_ID=SEU_STEAMID64_AQUI
```

E adicione `.env` ao `.gitignore`.

### Como subir tudo
```bash
# Copie e preencha o .env
cp .env.example .env

# Suba todos os containers
docker compose up -d

# Acompanhe os logs do Jenkins
docker compose logs -f jenkins
```

---

## ETAPA 5 — Publicar no Docker Hub

### Para que serve?
O requisito exige que as imagens estejam publicamente disponíveis no Docker Hub, com links
entregue junto ao repositório.

### Passo a passo

```bash
# 1. Faça login no Docker Hub (conta gratuita em hub.docker.com)
docker login

# 2. Construa a imagem com a tag do seu usuário Docker Hub
#    Substitua 'seuusuario' pelo usuário real do grupo
docker build -t seuusuario/steam-api-tests:latest -f Dockerfile.newman .
docker build -t seuusuario/steam-api-jenkins:latest -f Dockerfile.jenkins .

# 3. Envie para o Docker Hub
docker push seuusuario/steam-api-tests:latest
docker push seuusuario/steam-api-jenkins:latest

# 4. (Opcional mas recomendado) Envie também com tag de versão
docker tag seuusuario/steam-api-tests:latest seuusuario/steam-api-tests:1.0.0
docker push seuusuario/steam-api-tests:1.0.0
docker tag seuusuario/steam-api-jenkins:latest seuusuario/steam-api-jenkins:1.0.0
docker push seuusuario/steam-api-jenkins:1.0.0
```

### Resultado
O link ficará no formato:
```
https://hub.docker.com/r/seuusuario/steam-api-tests
https://hub.docker.com/r/seuusuario/steam-api-jenkins
```
Inclua esse link no README e na entrega do Teams.

### Usando a imagem do Docker Hub no Compose
Após publicar, você pode trocar o bloco `build` do `newman-runner` por `image`:

```yaml
newman-runner:
  image: seuusuario/steam-api-tests:latest  # puxa do Docker Hub
```

Isso demonstra o requisito de ter um container vindo do Docker Hub.

---

## ETAPA 6 — Atualizar o README

### Para que serve?
O professor exige README com: instalação, execução, uso, funcionalidades e **seção "Uso de IA"**.
O README atual já tem boa parte — falta adicionar as seções DevOps e a seção de IA.

### Seções a adicionar ao README existente

#### Seção: Infraestrutura DevOps

```markdown
## Infraestrutura DevOps

### Pré-requisitos adicionais
- [Docker](https://www.docker.com/) e Docker Compose
- Conta no [Docker Hub](https://hub.docker.com/)

### Subindo a infraestrutura completa

```bash
cp .env.example .env
# Edite o .env com suas credenciais

docker compose up -d
```

| Serviço | URL | Descrição |
|---|---|---|
| Jenkins | http://localhost:8080 | Pipeline CI/CD |
| MailHog | http://localhost:8025 | Visualizar e-mails de notificação |
| Relatórios | http://localhost:8090 | Relatórios HTML dos testes |

### Imagem Docker Hub
[hub.docker.com/r/seuusuario/steam-api-tests](https://hub.docker.com/r/seuusuario/steam-api-tests)
```

---

## ETAPA 7 — Repositório GitHub

### Checklist do repositório

- [ ] Repositório criado no **time da matéria** no GitHub (não na conta pessoal)
- [ ] Repositório **público**
- [ ] Todos os integrantes com commits relevantes (não só um pushando tudo)
- [ ] `.gitignore` atualizado (excluir `.env`, `steam_api.postman_environment.json`, `node_modules`, `reports/`)
- [ ] Todos os arquivos novos commitados: `Dockerfile.newman`, `Dockerfile.jenkins`, `.dockerignore`, `Jenkinsfile`, `docker-compose.yml`, `.env.example`, `scripts/notify.py`

### Estrutura final esperada do repositório

```
S07_Testes_SteamAPI/
├── .dockerignore
├── .env.example
├── .gitignore
├── docker-compose.yml
├── Dockerfile.newman
├── Dockerfile.jenkins
├── Jenkinsfile
├── package.json
├── package-lock.json
├── README.md
├── PLANO_DEVOPS.md                          ← este arquivo (pode remover após usar)
├── owned-games.postman_collection.json
├── recently-played.postman_collection.json
├── player-summaries.postman_collection.json
├── steam-api.postman_environment.example.json
└── scripts/
    └── notify.py
```

---

## ETAPA 8 — Teste completo (ensaio antes da defesa)

### Sequência de validação

```bash
# 1. Suba a infraestrutura do zero
docker compose down -v          # limpa tudo
docker compose up --build -d    # reconstrói e sobe

# 2. Verifique se os 4 containers estão rodando
docker compose ps

# 3. Acesse o Jenkins
# http://localhost:8080
# Na primeira vez: pegue a senha inicial com:
docker exec jenkins cat /var/jenkins_home/secrets/initialAdminPassword

# 4. Configure o job no Jenkins apontando para o repositório GitHub
# (única parte permitida via interface — o checkout)

# 5. Execute o pipeline e acompanhe os stages

# 6. Verifique o e-mail no MailHog
# http://localhost:8025

# 7. Verifique os relatórios HTML no Nginx
# http://localhost:8090

# 8. Verifique os artefatos arquivados no Jenkins
# http://localhost:8080 → job → última build → Artefatos
```

---

## Perguntas que o professor pode fazer (prepare respostas)

| Pergunta | Onde está a resposta |
|---|---|
| "Por que usaram MailHog em vez de SMTP real?" | Etapa 2 deste plano + seção "Uso de IA" do README |
| "Mostre o Jenkinsfile e explique cada stage" | `Jenkinsfile` na raiz |
| "Como o e-mail é enviado sem hardcode?" | `scripts/notify.py` linha `EMAIL_TO = os.environ["EMAIL_TO"]` |
| "Quantos containers têm e como se comunicam?" | `docker-compose.yml` + diagrama no início deste plano |
| "Como a cobertura de testes é ≥ 90%?" | Mostrar os 20 TCs das coleções Newman nos relatórios HTML |
| "Qual volume está sendo usado e para quê?" | `jenkins_home` (Jenkins) e `reports` (compartilhado Newman ↔ Nginx) |
| "A IA gerou o Jenkinsfile inteiro?" | Seção "Uso de IA" no README — prompt 3 e o que foi ajustado |
| "Mostre um commit seu no repositório" | Cada integrante deve ter commits com nome próprio |

---

## Resumo de arquivos a criar

| Arquivo | O que é |
|---|---|
| `Dockerfile.newman` | Containeriza o projeto Newman |
| `Dockerfile.jenkins` | Customiza a imagem Jenkins com nodejs, npm, zip e python3 |
| `.dockerignore` | Evita copiar arquivos desnecessários para a imagem |
| `Jenkinsfile` | Pipeline completo de CI/CD |
| `scripts/notify.py` | Script de notificação por e-mail |
| `docker-compose.yml` | Orquestra os 4 containers |
| `.env.example` | Modelo de variáveis de ambiente (sem valores reais) |
| Atualizar `README.md` | Adicionar seções DevOps e "Uso de IA" |
