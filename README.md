# S07 - Testes Automatizados: Steam API

Suíte de testes automatizados para a [Steam Web API](https://steamcommunity.com/dev), desenvolvida com [Postman](https://www.postman.com/) e executável via linha de comando com [Newman](https://github.com/postmanlabs/newman).

---

## Pré-requisitos

- [Node.js](https://nodejs.org/) (v18 ou superior)
- Uma chave de API da Steam ([obtenha aqui](https://steamcommunity.com/dev/apikey))
- Um SteamID64 válido ([descubra o seu aqui](https://www.steamidfinder.com/))

---

## Instalação

```bash
# Clone o repositório
git clone https://github.com/HenriqueIK/S07_Testes_SteamAPI.git
cd S07_Testes_SteamAPI

# Instale as dependências
npm install
```

---

## Configuração do ambiente

Copie o arquivo de exemplo e preencha com seus dados:

```bash
cp steam-api.postman_environment.example.json steam_api.postman_environment.json
```

Abra o arquivo `steam_api.postman_environment.json` e substitua os placeholders:

| Variável | Descrição |
|---|---|
| `steam_api_key` | Sua chave de API da Steam |
| `steam_id` | Seu SteamID64 (17 dígitos) |
| `baseurl` | `https://api.steampowered.com` (já preenchido) |

> **Atenção:** o arquivo `steam_api.postman_environment.json` está no `.gitignore` e nunca deve ser commitado — ele contém sua chave privada.

---

## Executando os testes

| Comando | Descrição |
|---|---|
| `npm run test:summaries` | Roda os testes de perfil do jogador (TC-015 a TC-020) |
| `npm run test:recent` | Roda os testes de jogos recentes (TC-009 a TC-014) |
| `npm run test:owned` | Roda os testes de jogos possuídos (TC-001 a TC-008) |
| `npm run test:all` | Roda todas as collections em paralelo |

---

## Casos de teste

### `owned-games.postman_collection.json` — GetOwnedGames

Testa o endpoint `/IPlayerService/GetOwnedGames/v0001/`.

| ID | Tipo | Descrição |
|---|---|---|
| TC-001 | ✅ Feliz | Valida que o campo `playtime_forever` existe e é um número não-negativo |
| TC-002 | ✅ Feliz | Valida que o retorno é 200 e contém a propriedade `games` |
| TC-003 | ✅ Feliz | Valida que Dota 2 (F2P) não aparece na lista de jogos possuídos |
| TC-004 | ✅ Feliz | Valida que `game_count` bate com o tamanho real da lista retornada |
| TC-005 | ❌ Triste | Simula que a API bloqueia requisições com chave inválida (espera 401/403) |
| TC-006 | ❌ Triste | Simula que a API rejeita um SteamID em formato de texto (espera resposta sem `games`) |
| TC-007 | ❌ Triste | Simula que a API bloqueia métodos HTTP diferentes de GET (espera 405) |
| TC-008 | ❌ Triste | Simula que a API retorna erro ou ignora `include_appinfo` inválido (nunca 500) |

---

### `player-summaries.postman_collection.json` — GetPlayerSummaries

Testa o endpoint `/ISteamUser/GetPlayerSummaries/v2/`.

| ID | Tipo | Descrição |
|---|---|---|
| TC-015 | ✅ Feliz | Valida que o retorno contém ao menos 1 jogador na lista |
| TC-016 | ✅ Feliz | Valida que os campos obrigatórios do perfil existem (`steamid`, `personaname`, `profileurl`, `avatar`) |
| TC-017 | ✅ Feliz | Valida que `communityvisibilitystate` é um valor válido (1, 2 ou 3) |
| TC-018 | ❌ Triste | Simula `personaname` com valor errado para demonstrar falha de validação de dado |
| TC-019 | ❌ Triste | Simula `communityvisibilitystate = 1` (privado) quando deveria ser 3 (público) |
| TC-020 | ❌ Triste | Simula lista de players vazia para demonstrar falha de contagem |

---

### `recently-played.postman_collection.json` — GetRecentlyPlayedGames

Testa o endpoint `/IPlayerService/GetRecentlyPlayedGames/v0001/`.

| ID | Tipo | Descrição |
|---|---|---|
| TC-009 | ✅ Feliz | Valida que todos os jogos recentes têm `playtime_2weeks` maior que zero |
| TC-010 | ✅ Feliz | Valida que `total_count` é consistente com o tamanho real da lista retornada |
| TC-011 | ✅ Feliz | Valida que `img_icon_url` de cada jogo é um hash hex válido de 40 caracteres |
| TC-012 | ❌ Triste | Simula `playtime_2weeks = 0` em jogo recente (por definição nunca pode ser zero) |
| TC-013 | ❌ Triste | Simula `total_count = 999` e verifica que não bate com o tamanho real da lista |
| TC-014 | ❌ Triste | Simula `img_icon_url` com valor malformado que não segue o padrão hex de 40 caracteres |

---

## Estrutura do projeto

```
S07_Testes_SteamAPI/
├── owned-games.postman_collection.json         # Testes TC-001 a TC-008
├── recently-played.postman_collection.json     # Testes TC-009 a TC-014
├── player-summaries.postman_collection.json    # Testes TC-015 a TC-020
├── steam-api.postman_environment.example.json  # Modelo de environment (sem dados sensíveis)
└── package.json                                # Scripts de execução via Newman
```

---

## Contribuidores

| Membro | Branch |
|---|---|
| HenriqueIK | `main` |
| Thiago | `thiago-alteracoes` |
| Pedro Frugoli | `pedro-frugoli` |

---

## Uso de Inteligência Artificial

Este projeto utilizou IA generativa como apoio no desenvolvimento. Foram utilizadas versões recentes do modelo **Claude** (Anthropic), acessado tanto diretamente no **Postman** (para escrita e revisão dos scripts de teste) quanto via **GitHub Copilot** no VS Code (para correções, padronização e documentação), para auxiliar nas seguintes tarefas:

- Revisão e correção dos testes das collections Postman
- Identificação de bugs estruturais (URL malformada, chave hardcoded, variáveis incorretas)
- Sugestão de casos de teste robustos e independentes do usuário
- Padronização de nomes de arquivos e scripts
- Elaboração deste README

Todo o código gerado foi revisado, validado e ajustado pelos membros do grupo antes de ser commitado.
