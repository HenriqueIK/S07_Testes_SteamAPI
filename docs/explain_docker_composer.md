# Explicação da Etapa 4: Docker Compose

Este documento descreve a etapa de orquestração de containers do projeto, definida no arquivo `docker-compose.yml`. A infraestrutura é composta por quatro serviços que trabalham em conjunto para executar testes automatizados da Steam API, notificar por e-mail e servir relatórios web.

---

Obs: Todos os containers se comunicam pela rede interna `devops-net` (bridge), isolada da rede do host.

---

## Versão do Compose

```yaml
version: '3.9'
```

Define o uso da especificação Compose na versão 3.9, compatível com Docker Engine 19.03+. Garante acesso a recursos modernos como healthchecks avançados e suporte completo a secrets.

---

## Serviços

### Container 1 — Jenkins

```yaml
jenkins:
  image: duartefrugoli/steam-api-jenkins:latest
  container_name: jenkins
  ports:
    - "8080:8080"
    - "50000:50000"
  volumes:
    - jenkins_home:/var/jenkins_home
    - reports:/shared-reports
    - ./steam_api.postman_environment.json:/var/jenkins_home/steam_api.postman_environment.json:ro
  environment:
    - NOTIFY_EMAIL=${NOTIFY_EMAIL}
  networks:
    - devops-net
  depends_on:
    - mailhog
```

**O que faz:** Orquestra todo o pipeline de CI/CD. É o "maestro" da infraestrutura — dispara os testes, coleta resultados e envia notificações.

| Detalhe | Explicação |
|---|---|
| `image: duartefrugoli/steam-api-jenkins:latest` | Puxa do Docker Hub a imagem Jenkins customizada com `nodejs`, `npm`, `zip` e `python3` |
| `ports: 8080` | Interface web do Jenkins, acessível em `http://localhost:8080` |
| `ports: 50000` | Porta de comunicação com agentes Jenkins remotos (JNLP) |
| `jenkins_home:/var/jenkins_home` | Persiste jobs, plugins e configurações entre reinicializações do container |
| `reports:/shared-reports` | Compartilha com o Nginx os relatórios gerados no pipeline Jenkins |
| `steam_api.postman_environment.json` | Disponibiliza para o Jenkins o environment real sem colocar a chave no Git |
| `NOTIFY_EMAIL` | E-mail de destino para notificações, lido do arquivo `.env` — nunca hardcoded no código |
| `depends_on: mailhog` | Garante que o servidor de e-mail suba antes do Jenkins, evitando falhas de conexão SMTP na inicialização |

> No fluxo atual, o Jenkins não precisa montar o Docker socket. Ele se comunica com o MailHog para notificação e compartilha relatórios com o Nginx pelo volume `reports`.

---

### Container 2 — Newman Runner

```yaml
newman-runner:
  build:
    context: .
    dockerfile: Dockerfile.newman
  container_name: newman-runner
  volumes:
    - reports:/app/reports
    - ./steam_api.postman_environment.json:/app/steam_api.postman_environment.json:ro
  environment:
    - STEAM_API_KEY=${STEAM_API_KEY}
    - STEAM_ID=${STEAM_ID}
  networks:
    - devops-net
  command: ["npm", "run", "test:all"]
```

**O que faz:** Executa a suíte de testes automatizados contra a Steam API usando o Newman (runner CLI do Postman). É um container **efêmero** — roda, gera os relatórios e encerra.

| Detalhe | Explicação |
|---|---|
| `build: context: .` | Constrói a imagem localmente a partir do `Dockerfile.newman`, ao invés de baixar do Hub |
| `reports:/app/reports` | Escreve os relatórios HTML gerados pelo Newman neste volume, que será lido pelo Nginx |
| `steam_api.postman_environment.json` | Environment real montado como somente leitura, fora da imagem e fora do Git |
| `STEAM_API_KEY` e `STEAM_ID` | Variáveis disponíveis para extensão do fluxo; os scripts atuais usam o arquivo de environment do Postman |
| `command: ["npm", "run", "test:all"]` | Sobrescreve o CMD do Dockerfile para executar o script de testes. Quando o script termina, o container encerra |

> **Container one-shot:** Diferente dos outros serviços, o `newman-runner` não fica rodando em loop. Ele executa sua tarefa e para — um padrão comum para containers de CI que realizam uma tarefa pontual.

---

### Container 3 — MailHog

```yaml
mailhog:
  image: mailhog/mailhog:latest
  container_name: mailhog
  ports:
    - "1025:1025"
    - "8025:8025"
  networks:
    - devops-net
```

**O que faz:** Simula um servidor de e-mail SMTP em ambiente de desenvolvimento. Captura todos os e-mails enviados pelo Jenkins sem entregá-los de verdade, permitindo inspeção segura.

| Detalhe | Explicação |
|---|---|
| `image: mailhog/mailhog:latest` | Imagem pública do MailHog, um fake SMTP server muito usado em ambientes de dev/test |
| `ports: 1025` | Porta SMTP padrão — o script `notify.py` do Jenkins aponta para `mailhog:1025` para "enviar" e-mails |
| `ports: 8025` | Interface web do MailHog, acessível em `http://localhost:8025`, onde todos os e-mails capturados podem ser visualizados |

> **Por que MailHog?** Em ambientes de desenvolvimento e testes, nunca se deve configurar um servidor SMTP real — risco de vazar dados, spammar contatos reais ou expor credenciais. O MailHog resolve isso: o Jenkins "acha" que está enviando e-mails, mas tudo fica preso na interface local.

---

### Container 4 — Report Server (Nginx)

```yaml
report-server:
  image: nginx:alpine
  container_name: report-server
  ports:
    - "8090:80"
  volumes:
    - reports:/usr/share/nginx/html:ro
  networks:
    - devops-net
  depends_on:
    - newman-runner
```

**O que faz:** Serve os relatórios HTML gerados pelo Newman como páginas web acessíveis pelo navegador.

| Detalhe | Explicação |
|---|---|
| `image: nginx:alpine` | Usa o Nginx na variante Alpine Linux — extremamente leve (~5MB), ideal para servir arquivos estáticos |
| `ports: 8090` | Os relatórios ficam disponíveis em `http://localhost:8090` |
| `reports:/usr/share/nginx/html:ro` | Monta o mesmo volume de relatórios do `newman-runner`, mas em modo **somente leitura** (`:ro`) — o Nginx não pode modificar os arquivos |
| `depends_on: newman-runner` | O Nginx só sobe depois que o `newman-runner` iniciar (não garante que os relatórios já foram gerados, apenas a ordem de inicialização) |

> **Compartilhamento via volume:** O volume `reports` é o elo entre o `newman-runner` (que escreve) e o `report-server` (que lê). Esse padrão de volume compartilhado é uma forma simples e eficiente de passar artefatos entre containers sem precisar de uma API ou sistema de arquivos externo.

---

## Volumes

```yaml
volumes:
  jenkins_home:
  reports:
```

| Volume | Usado por | Finalidade |
|---|---|---|
| `jenkins_home` | Jenkins | Persiste toda a configuração do Jenkins, jobs, plugins e histórico de builds entre reinicializações |
| `reports` | Jenkins/Newman Runner (escrita) + Nginx (leitura) | Canal de comunicação para relatórios HTML, permitindo que o Nginx publique os resultados gerados |

Ambos são **named volumes** gerenciados pelo Docker, o que garante persistência mesmo que os containers sejam removidos (`docker-compose down` sem a flag `--volumes`).

---

## Rede

```yaml
networks:
  devops-net:
    driver: bridge
```

Todos os containers compartilham a rede `devops-net` do tipo **bridge**. Isso significa:

- Os containers se enxergam pelo nome do serviço (ex: `jenkins` pode se conectar a `mailhog:1025` diretamente)
- O tráfego interno é isolado da rede do host e da internet
- Apenas as portas explicitamente declaradas em `ports:` ficam expostas para o host

---

## Fluxo de Execução

```
1. Docker sobe mailhog (Jenkins depende dele)
2. Docker sobe Jenkins
3. Docker sobe newman-runner → executa npm run test:all → gera relatórios em /app/reports → encerra
4. Docker sobe report-server (Nginx) → serve os relatórios via HTTP

Jenkins, durante o pipeline:
  └─▶ roda npm ci e os scripts Newman no workspace
  └─▶ copia reports/*.html para o volume reports em /shared-reports
  └─▶ envia notificação via notify.py → mailhog:1025
  └─▶ MailHog captura o e-mail → disponível em http://localhost:8025
```

---

## Variáveis de Ambiente (`.env`)

Nenhuma credencial está escrita no `docker-compose.yml`. Todas são injetadas via arquivo `.env` na raiz do projeto:

```env
NOTIFY_EMAIL=dev@exemplo.com
STEAM_API_KEY=sua_chave_aqui
STEAM_ID=seu_id_aqui
```

Essa prática segue o princípio dos [12-Factor Apps](https://12factor.net/config): configuração separada do código, sem segredos no repositório.
