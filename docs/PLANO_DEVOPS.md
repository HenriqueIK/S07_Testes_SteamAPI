# Plano DevOps - S07 Testes Steam API

Este roteiro descreve a arquitetura atual do projeto. A decisão adotada é:

```text
Dockerfile próprio: somente Dockerfile.jenkins
Newman: imagem pronta postman/newman do Docker Hub
Pipeline oficial: Jenkinsfile
```

---

## Arquitetura

```text
Docker Compose
├── jenkins
│   ├── usa duartefrugoli/steam-api-jenkins:latest
│   ├── roda npm ci
│   ├── executa os testes Newman
│   ├── gera reports/*.html
│   ├── publica relatórios no volume reports
│   └── envia e-mail para MailHog
├── newman-runner
│   └── usa postman/newman:latest, imagem pronta do Docker Hub
├── mailhog
│   └── captura e-mails enviados pelo Jenkins
└── report-server
    └── Nginx servindo os relatórios do volume reports
```

Essa arquitetura atende aos pontos principais da atividade:

| Requisito | Como o projeto atende |
|---|---|
| Jenkins em container | Serviço `jenkins` no `docker-compose.yml` |
| Pipeline no Jenkinsfile | `Jenkinsfile` com Checkout, Prepare, Install, Test, Build e post de e-mail |
| Sem GitHub Actions | Pipeline roda no Jenkins |
| Testes automatizados | Newman executado via `npm run test:*` |
| Artefatos | HTMLs e `steam-api-tests.zip` arquivados no Jenkins |
| E-mail | `scripts/notify.py` envia para MailHog |
| E-mail por variável | `NOTIFY_EMAIL` vem do ambiente |
| Docker Hub | `duartefrugoli/steam-api-jenkins:latest` |
| 4 containers | Jenkins, Newman Runner, MailHog e Nginx |
| Comunicação entre containers | Jenkins -> MailHog e Jenkins/Nginx via volume `reports` |
| Volumes | `jenkins_home` e `reports` |

---

## Dockerfile.jenkins

O único Dockerfile próprio instala as ferramentas que o Jenkins precisa para rodar a pipeline:

```dockerfile
FROM jenkins/jenkins:lts

USER root

RUN apt-get update \
 && apt-get install -y --no-install-recommends nodejs npm python3 zip \
 && mkdir -p /shared-reports \
 && chown -R jenkins:jenkins /shared-reports \
 && rm -rf /var/lib/apt/lists/*

USER jenkins
```

Por que isso fica no Dockerfile e não no Jenkinsfile?

Porque `nodejs`, `npm`, `python3` e `zip` são dependências do sistema operacional do container Jenkins. Se fossem instaladas em stage da pipeline, todo build dependeria de `apt-get`, permissões de root e rede disponível.

---

## Newman sem Dockerfile próprio

O projeto não precisa mais de `Dockerfile.newman`, porque existe imagem pronta:

```yaml
newman-runner:
  image: postman/newman:latest
```

A pipeline principal não depende desse container para gerar os relatórios HTML. Ela roda Newman dentro do Jenkins depois de instalar as dependências Node com:

```bash
npm ci
```

Isso é importante porque o relatório HTML usa `newman-reporter-htmlextra`, que está no `package-lock.json` do projeto.

---

## docker-compose.yml

O Compose sobe quatro containers:

```yaml
services:
  jenkins:
    image: duartefrugoli/steam-api-jenkins:latest

  newman-runner:
    image: postman/newman:latest

  mailhog:
    image: mailhog/mailhog:latest

  report-server:
    image: nginx:alpine
```

O volume `reports` é compartilhado entre Jenkins e Nginx:

```text
Jenkins escreve: /shared-reports
Nginx lê:        /usr/share/nginx/html
```

Depois que a pipeline roda, os relatórios ficam acessíveis em:

```text
http://localhost:8090/player-summaries.html
http://localhost:8090/recently-played.html
http://localhost:8090/owned-games.html
```

---

## Jenkinsfile

Fluxo da pipeline:

| Stage | Função |
|---|---|
| `Checkout` | Baixa o código do GitHub |
| `Prepare` | Copia o environment real montado pelo Compose |
| `Install` | Executa `npm ci` |
| `Test` | Roda as três collections Newman em paralelo e gera HTML |
| `Build` | Gera `steam-api-tests.zip` |
| `post.always` | Envia e-mail com `scripts/notify.py` |

O `.zip` deve incluir apenas arquivos existentes do projeto:

```groovy
sh '''
    zip -r steam-api-tests.zip \
        owned-games.postman_collection.json \
        recently-played.postman_collection.json \
        player-summaries.postman_collection.json \
        steam-api.postman_environment.example.json \
        package.json package-lock.json \
        reports/ scripts/ Dockerfile.jenkins docker-compose.yml README.md
'''
```

---

## Publicação no Docker Hub

Só a imagem Jenkins precisa ser construída e publicada pelo grupo:

```bash
docker build -t steam-api-jenkins:latest -f Dockerfile.jenkins .
docker tag steam-api-jenkins:latest duartefrugoli/steam-api-jenkins:latest
docker push duartefrugoli/steam-api-jenkins:latest
```

Depois de publicar uma nova versão:

```bash
docker compose pull jenkins
docker compose up -d --force-recreate jenkins
```

---

## Validação antes da defesa

```bash
docker compose down -v
docker compose pull
docker compose up -d
docker compose ps
```

No Jenkins:

1. Criar job Pipeline apontando para o repositório.
2. Configurar o branch correto, por exemplo `*/pedro-frugoli`.
3. Configurar `NOTIFY_EMAIL`.
4. Rodar `Build Now`.
5. Conferir artefatos HTML e `steam-api-tests.zip`.
6. Conferir e-mail no MailHog em `http://localhost:8025`.
7. Conferir relatórios no Nginx em `http://localhost:8090`.

---

## Checklist final

- [ ] `Dockerfile.jenkins` existe e instala `nodejs`, `npm`, `python3` e `zip`
- [ ] `Dockerfile.newman` não existe mais
- [ ] `docker-compose.yml` usa `postman/newman:latest`
- [ ] Jenkins usa `duartefrugoli/steam-api-jenkins:latest`
- [ ] Jenkinsfile não tem stage `Setup` com `apt-get`
- [ ] Jenkinsfile arquiva `reports/*.html`
- [ ] Jenkinsfile gera `steam-api-tests.zip`
- [ ] `NOTIFY_EMAIL` vem de variável de ambiente
- [ ] `steam_api.postman_environment.json` não está versionado
- [ ] README menciona o uso de IA
