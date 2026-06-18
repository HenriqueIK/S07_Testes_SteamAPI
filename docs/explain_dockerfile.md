# Explicações — Dockerfiles e .dockerignore

## O que foi feito na ETAPA 1

### Os dois arquivos criados

**`Dockerfile.newman`** — é a receita da imagem que executa os testes Newman:

```dockerfile
FROM node:20-alpine        # parte de uma imagem Linux com Node.js já instalado
WORKDIR /app               # define /app como pasta de trabalho dentro do container
COPY package.json package-lock.json ./   # copia só os arquivos de dependência primeiro
RUN npm ci                 # instala newman e newman-reporter-htmlextra
COPY . .                   # copia o restante (coleções Postman, scripts, etc.)
RUN mkdir -p reports       # garante que a pasta de relatórios existe
CMD ["npm", "run", "test:all"]  # comando executado quando o container inicia
```

**`Dockerfile.jenkins`** — é a receita da imagem Jenkins customizada:

```dockerfile
FROM jenkins/jenkins:lts
RUN apt-get update && apt-get install -y --no-install-recommends nodejs npm python3 zip
```

**`.dockerignore`** — funciona igual ao `.gitignore`, mas para o Docker. Impede que arquivos desnecessários ou sensíveis entrem na imagem.

---

## Correção importante: o environment não entra na imagem

O arquivo `steam_api.postman_environment.json` está no `.dockerignore` — ele **nunca é copiado para dentro da imagem**. Isso é intencional por segurança (contém a chave da Steam).

O problema é que o Newman precisa desse arquivo para rodar os testes. A solução é montá-lo como **volume** no `docker-compose.yml` em tempo de execução:

```yaml
newman-runner:
  volumes:
    - reports:/app/reports
    - ./steam_api.postman_environment.json:/app/steam_api.postman_environment.json:ro
```

**O que isso faz:** o Docker lê o arquivo da sua máquina local (`./steam_api...`) e o disponibiliza dentro do container no caminho `/app/steam_api...`. A flag `:ro` significa *read-only* — o container pode ler mas não alterar o arquivo.

**Por que não colocar na imagem?** Porque a imagem vai para o Docker Hub (público). Qualquer pessoa poderia baixar a imagem e extrair a chave. O volume resolve isso: o arquivo fica só na sua máquina, nunca viaja para lugar nenhum.

---

## Por que temos Dockerfile.newman e Dockerfile.jenkins?

Porque os dois containers executam responsabilidades diferentes e precisam de ambientes diferentes.

**Newman Runner — precisa de Dockerfile próprio** porque:
- A imagem base (`node:20-alpine`) não tem nada do projeto
- Precisamos copiar as coleções Postman para dentro
- Precisamos instalar o `newman` e o `newman-reporter-htmlextra`
- Precisamos definir o comando padrão (`npm run test:all`)
- É **o nosso software** — a lógica de negócio do projeto

**Jenkins — precisa de `Dockerfile.jenkins`** porque:
- `jenkins/jenkins:lts` já vem com Jenkins completo, mas não com todas as ferramentas do pipeline
- O stage `Install` usa `npm ci`, então o agente precisa de `nodejs` e `npm`
- O stage `Build` usa `zip`
- O `post.always` usa `python3 scripts/notify.py`

Essas ferramentas não entram no `package-lock.json`, porque não são pacotes Node do projeto. Elas são dependências do sistema operacional da imagem Jenkins.

**MailHog — não precisa de Dockerfile** porque:
- `mailhog/mailhog` já é um servidor SMTP pronto para uso
- Zero configuração necessária — sobe e funciona

**Nginx — não precisa de Dockerfile** porque:
- `nginx:alpine` já serve arquivos estáticos por padrão
- Só precisamos montar o volume com os relatórios HTML nele

Você cria um `Dockerfile` quando precisa **partir de uma imagem base e adicionar o seu código/configuração em cima**. Quando a imagem pública já faz exatamente o que você precisa, você só referencia ela no `docker-compose.yml` com `image:`.

---

## Por que precisa do .dockerignore?

O `.dockerignore` existe porque o comando `COPY . .` no `Dockerfile.newman` copia **tudo** da pasta para dentro da imagem — sem ele, entrariam coisas que não devem.

| Entrada | Motivo |
|---|---|
| `node_modules` | Pasta enorme. O `RUN npm ci` já instala as dependências dentro do container |
| `reports` | Relatórios de execuções locais anteriores. São gerados em tempo de execução |
| `steam_api.postman_environment.json` | **Contém a chave privada da Steam.** Se entrar na imagem e for publicada no Docker Hub, qualquer pessoa consegue extrair a chave |
| `.git` | Histórico completo do Git. Sem utilidade dentro do container |
| `*.md` | Documentação. Não é necessária para rodar os testes |
| `.env` | Arquivo com variáveis sensíveis — nunca deve vazar para a imagem |

**Analogia:** é como o `.gitignore`, mas em vez de proteger o que vai para o repositório, protege o que vai para dentro da imagem Docker.

---

## Por que copiar package.json antes de copiar tudo?

É uma otimização de **cache do Docker**.

O Docker constrói a imagem em camadas — cada instrução gera uma camada. Se uma camada não mudou desde o último build, o Docker reutiliza o cache em vez de reprocessar.

```dockerfile
COPY package.json package-lock.json ./   # camada A
RUN npm ci                               # camada B — demora ~10s
COPY . .                                 # camada C
```

No dia a dia você altera as coleções Postman, o README, scripts — mas raramente muda o `package.json`. Então:

- Camada A → cache válido (package.json não mudou) ✅
- Camada B → cache válido → **`npm ci` é pulado** ✅
- Camada C → cache inválido (você mudou uma coleção) → reprocessa só isso

**Se fizesse tudo de uma vez:**
```dockerfile
COPY . .     # qualquer mudança em qualquer arquivo invalida o cache
RUN npm ci   # sempre reinstala tudo — mesmo que o package.json não mudou
```

Cada build reinstalaria todas as dependências do zero, mesmo que você só tivesse editado um `.json` de teste. Copiar `package.json` primeiro isola a camada lenta (`npm ci`) das camadas que mudam frequentemente.
