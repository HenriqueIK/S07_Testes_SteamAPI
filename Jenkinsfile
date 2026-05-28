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

        // ── 1. Checkout ────────────────────────────────────────────────────────
        // Único passo que pode ser configurado pela interface gráfica do Jenkins
        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        // ── 2. Instalar dependências ───────────────────────────────────────────
        // npm ci garante instalação exata conforme o package-lock.json
        stage('Install') {
            steps {
                sh 'npm ci'
            }
        }

        // ── 3. Executar testes ─────────────────────────────────────────────────
        // Newman roda as 3 coleções e gera relatórios HTML em reports/
        // O '|| true' evita que uma falha de teste interrompa o pipeline antes
        // da notificação por e-mail ser enviada
        stage('Test') {
            steps {
                sh '''
                    npm run test:summaries || true
                    npm run test:recent    || true
                    npm run test:owned     || true
                '''
            }
            post {
                always {
                    // Arquiva os relatórios HTML como artefatos acessíveis no Jenkins
                    archiveArtifacts artifacts: 'reports/*.html', allowEmptyArchive: true
                }
            }
        }

        // ── 4. Build / empacotamento ───────────────────────────────────────────
        // Gera um .zip com as coleções + relatórios + scripts como artefato de entrega
        stage('Build') {
            steps {
                sh 'zip -r steam-api-tests.zip *.json reports/ scripts/ Dockerfile'
            }
            post {
                always {
                    archiveArtifacts artifacts: 'steam-api-tests.zip', allowEmptyArchive: true
                }
            }
        }
    }

    // ── 5. Notificação por e-mail (pós-pipeline) ───────────────────────────────
    // Roda SEMPRE — independentemente de sucesso ou falha nos stages anteriores
    post {
        always {
            sh "python3 scripts/notify.py ${currentBuild.currentResult}"
        }
    }
}