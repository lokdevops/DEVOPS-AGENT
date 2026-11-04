pipeline {
    agent any

    options {
        disableConcurrentBuilds()
        timestamps()
    }

    parameters {
        string(
            name: 'IMAGE_REPOSITORY',
            defaultValue: 'registry.example.com/your-team/url-shortener',
            description: 'Container registry repository for the application image'
        )
        string(
            name: 'REGISTRY_CREDENTIAL_ID',
            defaultValue: 'container-registry-creds',
            description: 'Jenkins username/password credential ID for the container registry'
        )
        string(
            name: 'KUBECONFIG_CREDENTIAL_ID',
            defaultValue: 'dev-kubeconfig',
            description: 'Jenkins secret-file credential ID for the Dev cluster kubeconfig'
        )
    }

    stages {
        stage('Test') {
            steps {
                sh '''
                    python3 -m venv .venv
                    .venv/bin/python -m pip install --upgrade pip
                    .venv/bin/python -m pip install -r requirements.txt
                    .venv/bin/python -m pytest -q tests
                '''
            }
        }

        stage('Build and publish image') {
            when {
                expression {
                    env.BRANCH_NAME == 'main' || env.GIT_BRANCH == 'origin/main'
                }
            }
            steps {
                script {
                    if (!(params.IMAGE_REPOSITORY ==~ /[a-z0-9][a-z0-9.\/:_-]*/)) {
                        error('IMAGE_REPOSITORY contains unsupported characters')
                    }
                    env.IMAGE_REF = "${params.IMAGE_REPOSITORY}:${env.GIT_COMMIT}"
                    env.REGISTRY_HOST = params.IMAGE_REPOSITORY.tokenize('/')[0]
                }
                withCredentials([
                    usernamePassword(
                        credentialsId: params.REGISTRY_CREDENTIAL_ID,
                        usernameVariable: 'REGISTRY_USER',
                        passwordVariable: 'REGISTRY_PASSWORD'
                    )
                ]) {
                    sh '''
                        set +x
                        export DOCKER_CONFIG="$(mktemp -d)"
                        trap 'docker logout "$REGISTRY_HOST" >/dev/null 2>&1 || true; rm -rf "$DOCKER_CONFIG"' EXIT
                        printf '%s' "$REGISTRY_PASSWORD" |
                            docker login "$REGISTRY_HOST" --username "$REGISTRY_USER" --password-stdin
                        docker build --pull --tag "$IMAGE_REF" .
                        docker push "$IMAGE_REF"
                    '''
                }
            }
        }

        stage('Deploy to Dev') {
            when {
                expression {
                    env.BRANCH_NAME == 'main' || env.GIT_BRANCH == 'origin/main'
                }
            }
            steps {
                withCredentials([
                    file(
                        credentialsId: params.KUBECONFIG_CREDENTIAL_ID,
                        variable: 'KUBECONFIG'
                    )
                ]) {
                    sh '''
                        set -eu
                        export IMAGE_REF
                        export RENDERED_MANIFEST="$(mktemp)"
                        trap 'rm -f "$RENDERED_MANIFEST"' EXIT
                        python3 -c 'from pathlib import Path; import os; source=Path("k8s/dev.yaml"); Path(os.environ["RENDERED_MANIFEST"]).write_text(source.read_text().replace("IMAGE_PLACEHOLDER", os.environ["IMAGE_REF"]))'
                        kubectl apply -f "$RENDERED_MANIFEST"
                        kubectl rollout status deployment/url-shortener --namespace dev --timeout=180s
                    '''
                }
            }
        }
    }

    post {
        always {
            echo 'Pipeline finished.'
        }
    }
}
