# Comandos importantes do projeto

## Docker — imagem

```bash
# Construir a imagem a partir do Dockerfile
docker build -t steam-api-tests:latest .

# Listar imagens locais
docker images

# Publicar no Docker Hub
docker tag steam-api-tests:latest seuusuario/steam-api-tests:latest
docker push seuusuario/steam-api-tests:latest

# Rodar o container manualmente (fora do Compose)
docker run --rm steam-api-tests:latest
```

---

## Docker Compose — infraestrutura

```bash
# Subir todos os 4 containers
docker compose up -d

# Subir e reconstruir a imagem local (após mudança no Dockerfile)
docker compose up --build -d

# Ver status dos containers
docker compose ps

# Ver logs de um container específico
docker compose logs -f jenkins

# Derrubar tudo
docker compose down

# Derrubar tudo E apagar os volumes (dados do Jenkins, relatórios)
docker compose down -v
```

---

## Jenkins — container

```bash
# Pegar senha inicial do Jenkins (só na primeira vez)
docker exec jenkins cat /var/jenkins_home/secrets/initialAdminPassword
```

---

## Git — publicar no GitHub

```bash
# Ver o que mudou
git status

# Adicionar arquivos ao commit
git add .

# Fazer o commit
git commit -m "mensagem do commit"

# Enviar para o GitHub (primeira vez numa branch nova)
git push -u origin nome-da-branch

# Enviar para o GitHub (branches já publicadas)
git push

# Puxar mudanças do GitHub
git pull
```

---

## Fluxo completo do zero (ensaio antes da defesa)

```bash
# 1. Subir a infraestrutura do zero
docker compose down -v
docker compose up --build -d

# 2. Verificar os containers
docker compose ps

# 3. Liberar permissão de diretório no Git (só precisa fazer UMA vez por máquina)
docker exec jenkins git config --global --add safe.directory '*'

# 4. Pegar senha do Jenkins (só na primeira vez)
docker exec jenkins cat /var/jenkins_home/secrets/initialAdminPassword

# 5. Acessar Jenkins em http://localhost:8080
#    → Criar job Pipeline apontando para o GitHub
#    → Em Manage Jenkins > Configure System: adicionar variável NOTIFY_EMAIL
#    → Rodar o pipeline (Build Now)

# 6. Verificar e-mail capturado pelo MailHog
#    http://localhost:8025

# 7. Verificar relatórios HTML servidos pelo Nginx
#    http://localhost:8090

# 8. Verificar artefatos arquivados no Jenkins
#    http://localhost:8080 → job → última build → Artefatos
```

---

## Os que mais aparecem na defesa

| Comando | Por que o professor pode pedir |
|---|---|
| `docker compose ps` | "Mostre os 4 containers rodando" |
| `docker compose logs -f jenkins` | "Mostre o pipeline executando" |
| `docker images` | "Mostre a imagem que vocês criaram" |
| `docker compose down -v` / `up --build` | "Suba do zero na minha frente" |
