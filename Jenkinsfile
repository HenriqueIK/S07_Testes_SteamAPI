// Jenkinsfile
pipeline {
    agent any

    environment {
        // E-mail de notificação — definido como variável de ambiente global no Jenkins
        // Nunca hardcoded aqui!
        EMAIL_TO  = "${env.NOTIFY_EMAIL}"
        SMTP_HOST = "mailhog"
        SMTP_PORT = "1025"
        BUILD_URL = "${env.BUILD_URL}"
        NEWMAN_CONTAINER = "newman-runner"
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        // 2. Preparar workspace
        // O environment real fica fora do Git; o Compose monta uma cópia segura no Jenkins.
        stage('Prepare') {
            steps {
                sh '''
                    mkdir -p reports /shared-reports
                    cp /var/jenkins_home/steam_api.postman_environment.json steam_api.postman_environment.json

                    echo "Copiando enviroment para container Newman"
                    docker cp steam_api.postman_environment.json ${NEWMAN_CONTAINER}:/etc/newman/ || true

                    echo "Verificando conectividade com Newman"
                    docker exec ${NEWMAN_CONTAINER} newman --version
                '''
            }
        }

        // 3. Instalar dependências
        // npm ci garante instalação exata conforme o package-lock.json
        stage('Install') {
            steps {
                sh 'npm ci'
            }
        }

        // 4. Executar testes
        // catchError marca falhas como UNSTABLE sem impedir artefatos e notificação
            stage('Test - Player Summaries') {
            steps {
                catchError(buildResult: 'UNSTABLE', stageResult: 'FAILURE') {
                    // Executa o script dentro do container do newman usando os arquivos mapeados nele
                    sh '''
                    echo "Executando testes: Player Summaries em ${NEWMAN_CONTAINER}"
                    docker exec -t ${NEWMAN_CONTAINER} \
                    newman run "/etc/newman/player-summaries.postman_collection.json" \
                    -e "/etc/newman/steam_api.postman_environment.json" \
                    --reporters cli,htmlextra \
                    --reporter-htmlextra-export /reports/player-summaries.html \
                    --insecure

                    echo "Player Summaries concluído"
                    '''
                }
            }
        }

        stage('Test - Recently Played') {
            steps {
                catchError(buildResult: 'UNSTABLE', stageResult: 'FAILURE') {
                    sh '''
                    echo "Executando testes: Recently Played em ${NEWMAN_CONTAINER}"
                    docker exec ${NEWMAN_CONTAINER} \
                    newman run "/etc/newman/recently-played.postman_collection.json" \
                    -e "/etc/newman/steam_api.postman_environment.json" \
                    --reporters cli,htmlextra \
                    --reporter-htmlextra-export /reports/recently-played.html \
                    --insecure

                    echo "Recently Played concluído"
                    '''
                }
            }
        }

        stage('Test - Owned Games') {
            steps {
                catchError(buildResult: 'UNSTABLE', stageResult: 'FAILURE') {
                    sh '''
                    echo "Executando testes: Owned Games em ${NEWMAN_CONTAINER}"
                    docker exec ${NEWMAN_CONTAINER} \
                    newman run "/etc/newman/owned-games.postman_collection.json" \
                    -e "/etc/newman/steam_api.postman_environment.json" \
                    --reporters cli,htmlextra \
                    --reporter-htmlextra-export /reports/owned-games.html \
                    --insecure

                    echo "Owned Games concluído"
                    '''
                }
            }
        }

        post {
            always {
                sh '''
                echo "Copiando relatorios do container Newman para Jenkins"
                docker cp ${NEWMAN_CONTAINER}:/reports/. reports/ 2>/dev/null || true
                echo "Verificando relatorios copiados"
                ls -lah reports/ || true
                '''

                archiveArtifacts artifacts: 'reports/*.html', allowEmptyArchive: true
            }
        }

        // 5. Build / empacotamento
        // Gera um .zip seguro sem incluir o environment real com chave da Steam
        stage('Build') {
            steps {
                sh '''
                    zip -r steam-api-tests.zip \
                        owned-games.postman_collection.json \
                        recently-played.postman_collection.json \
                        player-summaries.postman_collection.json \
                        steam-api.postman_environment.example.json \
                        package.json package-lock.json \
                        reports/ scripts/ Dockerfile.jenkins docker-compose.yml README.md
                '''
            }
            post {
                always {
                    archiveArtifacts artifacts: 'steam-api-tests.zip', allowEmptyArchive: true
                }
            }
        }
    }

    // 6. Notificação por e-mail (pós-pipeline)
    // Roda SEMPRE — independentemente de sucesso ou falha nos stages anteriores
    post {
        always {
            sh "python3 scripts/notify.py ${currentBuild.currentResult}"
        }
    }
}
