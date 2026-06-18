# Explicação da Etapa 4: Docker Compose

Este documento explica a infraestrutura definida em `docker-compose.yml`. O projeto sobe quatro containers, mas mantém apenas um Dockerfile próprio: `Dockerfile.jenkins`.

---

## Serviços

### Container 1 - Jenkins

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

O Jenkins é o container principal. Ele baixa o código do GitHub, instala as dependências com `npm ci`, roda os testes Newman, arquiva relatórios, gera o `.zip` e envia e-mail pelo MailHog.

| Detalhe | Explicação |
|---|---|
| `image` | Usa a imagem customizada publicada no Docker Hub |
| `jenkins_home` | Persiste jobs, plugins e histórico |
| `reports:/shared-reports` | Compartilha os relatórios HTML com o Nginx |
| `steam_api.postman_environment.json` | Monta o environment real sem colocar segredo no Git |
| `NOTIFY_EMAIL` | Vem do `.env` ou configuração global do Jenkins |

---

### Container 2 - Newman Runner

```yaml
newman-runner:
  image: postman/newman:latest
  container_name: newman-runner
  working_dir: /etc/newman
  volumes:
    - .:/etc/newman:ro
  networks:
    - devops-net
  entrypoint: ["/bin/sh", "-c"]
  command: ["newman --version && tail -f /dev/null"]
```

Este container usa uma imagem pública pronta do Docker Hub. Ele não é responsável pela pipeline principal; quem gera os relatórios oficiais é o Jenkins.

O `tail -f /dev/null` mantém o container ativo para que `docker compose ps` mostre os quatro containers rodando durante a apresentação.

| Detalhe | Explicação |
|---|---|
| `postman/newman:latest` | Imagem oficial/pronta do Newman |
| `.:/etc/newman:ro` | Monta o projeto em modo somente leitura |
| `entrypoint` + `command` | Mostra a versão do Newman e mantém o container vivo |

---

### Container 3 - MailHog

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

O MailHog simula um servidor SMTP. O `notify.py` envia e-mail para `mailhog:1025`, e a mensagem fica disponível em `http://localhost:8025`.

---

### Container 4 - Report Server

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
    - jenkins
```

O Nginx serve os relatórios HTML que o Jenkins copia para `/shared-reports`.

| Detalhe | Explicação |
|---|---|
| `reports:/usr/share/nginx/html:ro` | Lê o mesmo volume escrito pelo Jenkins |
| `8090:80` | Permite acessar relatórios em `http://localhost:8090` |
| `depends_on: jenkins` | Sobe depois do Jenkins iniciar |

---

## Volumes

```yaml
volumes:
  jenkins_home:
  reports:
```

| Volume | Usado por | Finalidade |
|---|---|---|
| `jenkins_home` | Jenkins | Persistir configuração, jobs e histórico |
| `reports` | Jenkins + Nginx | Jenkins escreve HTMLs; Nginx lê e publica |

---

## Rede

Todos os containers usam a rede `devops-net`. Isso permite comunicação por nome de serviço:

| Origem | Destino | Para quê |
|---|---|---|
| Jenkins | `mailhog:1025` | Enviar notificação por e-mail |
| Jenkins | volume `reports` | Publicar relatórios para o Nginx |
| Nginx | volume `reports` | Ler relatórios HTML |

---

## Fluxo de execução

```text
1. Docker Compose sobe MailHog, Jenkins, Newman Runner e Nginx.
2. O usuário roda a pipeline no Jenkins.
3. Jenkins executa npm ci.
4. Jenkins roda os testes Newman e gera reports/*.html.
5. Jenkins copia os HTMLs para /shared-reports.
6. Nginx serve esses HTMLs em http://localhost:8090.
7. Jenkins envia o e-mail para mailhog:1025.
8. MailHog exibe o e-mail em http://localhost:8025.
```

Assim o projeto atende ao requisito de quatro containers, comunicação entre containers, volume compartilhado e uso de uma imagem própria publicada no Docker Hub.
