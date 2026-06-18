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
    }

    stages {

        // 1. Checkout
        // Único passo que pode ser configurado pela interface gráfica do Jenkins
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
        // Newman roda as 3 coleções e gera relatórios HTML em reports/
        // catchError marca falhas como UNSTABLE sem impedir artefatos e notificação
        stage('Test') {
            steps {
                catchError(buildResult: 'UNSTABLE', stageResult: 'FAILURE') {
                    sh '''
                        set +e
                        npm run test:summaries
                        status_summaries=$?
                        npm run test:recent
                        status_recent=$?
                        npm run test:owned
                        status_owned=$?

                        if [ "$status_summaries" -ne 0 ] || [ "$status_recent" -ne 0 ] || [ "$status_owned" -ne 0 ]; then
                            exit 1
                        fi
                    '''
                }
            }
            post {
                always {
                    sh 'cp -f reports/*.html /shared-reports/ 2>/dev/null || true'
                    // Arquiva os relatórios HTML como artefatos acessíveis no Jenkins
                    archiveArtifacts artifacts: 'reports/*.html', allowEmptyArchive: true
                }
            }
        }

        // 5. Build / empacotamento
        // Gera um .zip com as coleções + relatórios + scripts como artefato de entrega
        stage('Build') {
            steps {
                sh 'zip -r steam-api-tests.zip *.json reports/ scripts/ Dockerfile.newman Dockerfile.jenkins'
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
