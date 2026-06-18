# Explicação do Jenkinsfile — Steam API Tests

> Este documento explica bloco a bloco o `Jenkinsfile` criado para o pipeline de CI/CD
> do projeto S07 Testes Steam API. Leia antes da defesa — o professor vai perguntar.

---

## O arquivo completo

```groovy
pipeline {
    agent any

    environment {
        EMAIL_TO  = "${env.NOTIFY_EMAIL}"
        SMTP_HOST = "mailhog"
        SMTP_PORT = "1025"
        BUILD_URL = "${env.BUILD_URL}"
    }

    stages {

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

        stage('Install') {
            steps {
                sh 'npm ci'
            }
        }

        stage('Test') {
            parallel {
                stage('Player Summaries') {
                    steps {
                        catchError(buildResult: 'UNSTABLE', stageResult: 'FAILURE') {
                            sh 'npm run test:summaries'
                        }
                    }
                }

                stage('Recently Played') {
                    steps {
                        catchError(buildResult: 'UNSTABLE', stageResult: 'FAILURE') {
                            sh 'npm run test:recent'
                        }
                    }
                }

                stage('Owned Games') {
                    steps {
                        catchError(buildResult: 'UNSTABLE', stageResult: 'FAILURE') {
                            sh 'npm run test:owned'
                        }
                    }
                }
            }
            post {
                always {
                    sh 'cp -f reports/*.html /shared-reports/ 2>/dev/null || true'
                    archiveArtifacts artifacts: 'reports/*.html', allowEmptyArchive: true
                }
            }
        }

        stage('Build') {
            steps {
                sh 'zip -r steam-api-tests.zip *.json reports/ scripts/ Dockerfile.jenkins'
            }
            post {
                always {
                    archiveArtifacts artifacts: 'steam-api-tests.zip', allowEmptyArchive: true
                }
            }
        }
    }

    post {
        always {
            sh "python3 scripts/notify.py ${currentBuild.currentResult}"
        }
    }
}
```

---

## Bloco `environment {}`

```groovy
environment {
    EMAIL_TO  = "${env.NOTIFY_EMAIL}"
    SMTP_HOST = "mailhog"
    SMTP_PORT = "1025"
    BUILD_URL = "${env.BUILD_URL}"
}
```

Define variáveis de ambiente disponíveis para **todos os stages do pipeline** — funciona
como um `.env` global. Qualquer `sh` ou script posterior pode ler essas variáveis.

| Variável | Valor | Estratégia | Motivo |
|---|---|---|---|
| `EMAIL_TO` | `env.NOTIFY_EMAIL` | Vem de fora | Dado pessoal — não entra no repositório |
| `SMTP_HOST` | `"mailhog"` | Fixo no código | Nome do container na rede Docker — igual em todos os ambientes |
| `SMTP_PORT` | `"1025"` | Fixo no código | Porta padrão do MailHog — não muda |
| `BUILD_URL` | `env.BUILD_URL` | Re-exposta do Jenkins | Nativa do Jenkins, mas precisa ser propagada ao shell para o `notify.py` usar |

`env` é o objeto global do Jenkins que expõe variáveis configuradas fora do Jenkinsfile.
`NOTIFY_EMAIL` é cadastrada em **Manage Jenkins → Configure System → Global properties**
— assim o e-mail do grupo nunca aparece no código-fonte. O `${}` é interpolação de string Groovy.

`SMTP_HOST = "mailhog"` funciona porque, dentro da rede Docker (`devops-net`), os
containers se resolvem pelo nome como se fosse um DNS interno.

---

## Bloco `stages {}`

É o corpo do pipeline. Cada `stage` aparece como uma fase visual na interface do Jenkins,
com nome, ícone de status (✅ / ❌) e tempo de execução. A ordem importa: se um stage
falhar, os seguintes são pulados — exceto o `post`, que sempre roda.

---

### Stage 1 — `Checkout`

```groovy
stage('Checkout') {
    steps {
        checkout scm
    }
}
```

`scm` significa *Source Control Management* — referência automática ao repositório
configurado no job do Jenkins. O `checkout scm` baixa o código do branch/commit que
disparou o build.

É o único stage que depende de configuração pela interface gráfica (apontar o repositório
GitHub no job). Todo o resto vive no próprio Jenkinsfile.

---

### Stage 2 — `Prepare`

```groovy
stage('Prepare') {
    steps {
        sh '''
            mkdir -p reports /shared-reports
            cp /var/jenkins_home/steam_api.postman_environment.json steam_api.postman_environment.json
        '''
    }
}
```

Esse stage prepara o workspace depois do checkout. O arquivo real
`steam_api.postman_environment.json` não fica no Git; ele é montado pelo Docker Compose
em `/var/jenkins_home/steam_api.postman_environment.json` e copiado para o workspace para
que os comandos Newman consigam usar `-e steam_api.postman_environment.json`.

O diretório `/shared-reports` é o volume `reports` montado no Jenkins e no Nginx. Quando
o pipeline copia os HTMLs para lá, eles ficam disponíveis em `http://localhost:8090`.

---

### Stage 3 — `Install`

```groovy
stage('Install') {
    steps {
        sh 'npm ci'
    }
}
```

`sh` executa um comando shell no agente Jenkins. O `npm ci` é diferente do `npm install`:

| | `npm install` | `npm ci` |
|---|---|---|
| Lê | `package.json` | `package-lock.json` |
| Atualiza o lock? | Sim | Nunca |
| Apaga `node_modules` antes? | Não | Sempre |
| Ideal para | Desenvolvimento local | CI/CD |

Em pipeline sempre se usa `npm ci` — garante que todo build instala exatamente as mesmas
versões, sem surpresas entre máquinas ou datas diferentes.

---

### Stage 4 — `Test`

```groovy
stage('Test') {
    parallel {
        stage('Player Summaries') {
            steps {
                catchError(buildResult: 'UNSTABLE', stageResult: 'FAILURE') {
                    sh 'npm run test:summaries'
                }
            }
        }

        stage('Recently Played') {
            steps {
                catchError(buildResult: 'UNSTABLE', stageResult: 'FAILURE') {
                    sh 'npm run test:recent'
                }
            }
        }

        stage('Owned Games') {
            steps {
                catchError(buildResult: 'UNSTABLE', stageResult: 'FAILURE') {
                    sh 'npm run test:owned'
                }
            }
        }
    }
    post {
        always {
            sh 'cp -f reports/*.html /shared-reports/ 2>/dev/null || true'
            archiveArtifacts artifacts: 'reports/*.html', allowEmptyArchive: true
        }
    }
}
```

Quatro pontos importantes:

**`parallel {}`** — faz o Jenkins executar as três collections ao mesmo tempo. Na interface
do Jenkins, cada collection aparece como um substage separado dentro do stage `Test`.

**Um `catchError` por collection** — permite que uma falha em `Player Summaries`, por
exemplo, não cancele imediatamente `Recently Played` ou `Owned Games`. Cada substage
termina sua execução e o resultado final da build fica `UNSTABLE` se algum teste falhar.

**`catchError(buildResult: 'UNSTABLE')`** — deixa o Jenkins registrar que houve falha de
teste, mas mantém o pipeline vivo para arquivar relatórios, gerar o `.zip` e enviar e-mail.
Assim a build não mente como `SUCCESS`, mas também não interrompe a etapa de evidências.

**`archiveArtifacts`** — arquiva os HTMLs gerados pelo Newman como artefatos do Jenkins,
acessíveis individualmente na interface de cada build. O `allowEmptyArchive: true` evita
erro caso nenhum HTML tenha sido gerado. Esses arquivos ficam disponíveis para download
logo após o stage `Test`.

**Cópia para `/shared-reports`** — publica os mesmos HTMLs no volume lido pelo Nginx,
permitindo visualizar os relatórios em `http://localhost:8090`.

---

### Stage 5 — `Build`

```groovy
stage('Build') {
    steps {
        sh 'zip -r steam-api-tests.zip *.json reports/ scripts/ Dockerfile.jenkins'
    }
    post {
        always {
            archiveArtifacts artifacts: 'steam-api-tests.zip', allowEmptyArchive: true
        }
    }
}
```

Atende ao requisito de **artefato de build**. O `zip -r` empacota recursivamente:

| O que entra no `.zip` | Por quê |
|---|---|
| `*.json` | As coleções e environments Postman |
| `reports/` | Os HTMLs já gerados pelo Newman no stage anterior |
| `scripts/` | O `notify.py` |
| `Dockerfile.jenkins` | A definição da imagem customizada do Jenkins |

O stage `Build` não gera os relatórios — eles já foram gerados no stage `Test`. O `Build`
apenas os reempacota junto com o restante do projeto, formando um pacote de entrega
completo para download.

---

### Dois artefatos, dois propósitos

| Artefato | Gerado em | Conteúdo | Uso |
|---|---|---|---|
| `reports/*.html` | Stage `Test` | HTMLs individuais do Newman | Visualizar resultados diretamente no browser |
| `steam-api-tests.zip` | Stage `Build` | Tudo junto (coleções + relatórios + scripts) | Pacote de entrega completo |

Os HTMLs também são servidos pelo **Nginx** via volume compartilhado — esse é o terceiro
ponto de acesso, definido no `docker-compose.yml`.

---

## Bloco `post {}` do pipeline

```groovy
post {
    always {
        sh "python3 scripts/notify.py ${currentBuild.currentResult}"
    }
}
```

Roda **fora e depois de todos os stages**, independente do que aconteceu antes — mesmo
que o pipeline esteja marcado como `FAILURE`.

Os `post` dentro dos stages `Test` e `Build` são locais, respondem só ao stage pai.
Este é o `post` do pipeline inteiro.

### Condições disponíveis no `post`

| Condição | Quando roda |
|---|---|
| `always` | Sempre, sem exceção |
| `success` | Só se tudo passou |
| `failure` | Só se algo falhou |
| `unstable` | Se houve testes com falha mas o pipeline não quebrou |
| `changed` | Se o resultado mudou em relação ao build anterior |

### O argumento `${currentBuild.currentResult}`

`currentBuild` é um objeto Groovy nativo do Jenkins com metadados do build atual.
O `.currentResult` retorna o estado final como string: `SUCCESS`, `FAILURE`,
`UNSTABLE` ou `ABORTED`.

Esse valor é passado como argumento posicional para o `notify.py`:

```python
BUILD_STATUS = sys.argv[1] if len(sys.argv) > 1 else "DESCONHECIDO"
```

E aparece no assunto do e-mail:
```
[Steam API Tests] Build #42 — FAILURE
```

---

## Fluxo completo em caso de falha

```
Checkout ✅ → Prepare ✅ → Install ✅ → Test ❌ (testes falharam)
                                             ↓
                                  catchError marca UNSTABLE
                                             ↓
                       Build ✅ → post.always → notify.py "UNSTABLE"
                                                      ↓
                                              E-mail chega no MailHog
```

Sem o `catchError`, o pipeline poderia encerrar antes do `Build` e do `post.always`.
Com ele, a falha de teste aparece no resultado, mas as evidências continuam sendo geradas.

---

## Perguntas da defesa — respostas prontas

**"Por que usaram `npm ci` e não `npm install`?"**
`npm ci` lê o `package-lock.json` e nunca o atualiza — garante que todo build instala
exatamente as mesmas versões, tornando o ambiente reproduzível.

**"Por que usaram `catchError` no stage de testes?"**
Para que falhas do Newman não interrompam a geração de artefatos e o envio de e-mail.
A diferença para `|| true` é que o Jenkins não mente: a build fica `UNSTABLE` quando há
falha de teste.

**"Por que o e-mail fica no `post` e não em um stage normal?"**
O bloco `post` roda sempre, mesmo após falhas. Um stage normal seria pulado se o
anterior falhasse — o e-mail não chegaria quando os testes quebram.

**"O `NOTIFY_EMAIL` está no código?"**
Não. Ele é configurado em **Manage Jenkins → Configure System → Global properties**
e injetado em tempo de execução via `env.NOTIFY_EMAIL`. O repositório não contém
nenhum e-mail.

**"Quem gera os relatórios HTML?"**
O Newman, durante o stage `Test`. O stage `Build` apenas os reempacota no `.zip`.
Os HTMLs também ficam disponíveis via Nginx, servidos pelo volume compartilhado
`reports` definido no `docker-compose.yml`.
