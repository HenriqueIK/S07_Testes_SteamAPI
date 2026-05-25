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

## Os que mais aparecem na defesa

| Comando | Por que o professor pode pedir |
|---|---|
| `docker compose ps` | "Mostre os 4 containers rodando" |
| `docker compose logs -f jenkins` | "Mostre o pipeline executando" |
| `docker images` | "Mostre a imagem que vocês criaram" |
| `docker compose down -v` / `up --build` | "Suba do zero na minha frente" |
