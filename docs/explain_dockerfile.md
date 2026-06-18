# Explicação - Dockerfile Jenkins e .dockerignore

## Qual Dockerfile o projeto usa?

O projeto usa apenas um Dockerfile próprio:

```text
Dockerfile.jenkins
```

Ele existe porque a imagem oficial `jenkins/jenkins:lts` já traz o Jenkins, mas não traz todas as ferramentas que a pipeline precisa para executar este projeto.

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

## Por que instalar Node, npm, Python e zip no Jenkins?

Essas ferramentas são dependências do ambiente de CI, não dependências Node do projeto.

| Ferramenta | Onde é usada |
|---|---|
| `nodejs` / `npm` | Stage `Install`, para executar `npm ci` |
| `newman` | Instalado pelo `npm ci` a partir do `package-lock.json` |
| `newman-reporter-htmlextra` | Instalado pelo `npm ci` para gerar relatórios HTML |
| `zip` | Stage `Build`, para gerar `steam-api-tests.zip` |
| `python3` | `post.always`, para executar `scripts/notify.py` |

Por isso essas ferramentas não aparecem no `package-lock.json`: o lockfile controla pacotes Node, enquanto `nodejs`, `npm`, `python3` e `zip` são pacotes do sistema operacional da imagem Jenkins.

## Por que não existe Dockerfile.newman?

Porque o Newman já tem imagem pronta no Docker Hub:

```yaml
newman-runner:
  image: postman/newman:latest
```

No projeto atual, a pipeline principal roda os testes dentro do Jenkins. O container `newman-runner` no `docker-compose.yml` serve para cumprir o requisito de infraestrutura com quatro containers e demonstrar o uso de uma imagem pública pronta do Docker Hub.

Essa decisão evita duplicar responsabilidade:

| Responsabilidade | Onde fica |
|---|---|
| Orquestrar pipeline | Jenkins |
| Instalar dependências do projeto | `npm ci` dentro do Jenkins |
| Rodar testes Newman com HTML | Stage `Test` do Jenkinsfile |
| Servir relatórios | Nginx |
| Capturar e-mail | MailHog |
| Provar imagem Newman pronta | `postman/newman:latest` |

## Para que serve o .dockerignore?

Mesmo com apenas o `Dockerfile.jenkins`, o `.dockerignore` continua útil como proteção caso alguém volte a buildar uma imagem a partir da raiz do projeto no futuro.

Itens sensíveis ou pesados continuam fora de qualquer build:

| Entrada | Motivo |
|---|---|
| `node_modules` | Pasta grande e recriada por `npm ci` |
| `reports` | Relatórios gerados em execução |
| `steam_api.postman_environment.json` | Contém chave privada da Steam |
| `.env` | Variáveis locais e sensíveis |
| `.git` | Histórico Git não é necessário dentro de imagem |

O arquivo real `steam_api.postman_environment.json` nunca deve ir para o Git nem para imagem Docker pública.
