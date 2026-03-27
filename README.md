                Kubeflow Pipelines
                       │
                       ▼
                 Model Training
                       │
           ┌───────────┴───────────┐
           ▼                       ▼
        MLflow                Feature Store
           │                       │
           ▼                       ▼
       PostgreSQL                Feast
           │                       │
           └───────────┬───────────┘
                       ▼
                     MinIO
                       │
                       ▼
                      DVC
                       │
                       ▼
               Drift Monitoring
                   Evidently
                       │
                       ▼
              Prometheus + Grafana

MLOps Stack on Apple Silicon (M3) — Complete Fix Log
Problem 1: KFP metadata-writer ImagePullBackOff
Root cause: KFP images are AMD64-only. Native ARM64 (aarch64) Colima can't pull them.

Fix: Switch Colima to x86_64 + QEMU emulation.

Problem 2: controller-manager OOMKilled
Root cause: Default memory limits too tight.

Fix: Patch memory limits after deploy:

kubectl set resources deployment controller-manager -n kubeflow \
  --limits=memory=512Mi,cpu=500m \
  --requests=memory=256Mi,cpu=100m

Problem 3: Colima arch/vm-type locked after creation
Root cause: colima stop/start won't change arch or vm-type — only colima delete resets them.

Fix:

colima stop       # full wipe required
colima delete --force
colima start --arch x86_64 --vm-type qemu --cpu 6 --memory 12 --disk 20

k3d cluster create mlops \
  --servers 1 \
  --agents 1 \
  --no-lb \
  --k3s-node-label "role=server@server:0" \
  --agents-memory 10g

Problem 4: QEMU missing x86_64 guest agent binary
Root cause: lima-additional-guestagents package not installed — QEMU needs it to run x86_64 VMs on ARM host.

Fix:

brew install lima-additional-guestagents

Problem 5: Colima failed to start Docker after partial VM boot
Root cause: Interrupted first boot left a corrupted instance state.

Fix:

colima delete --force
colima start --arch x86_64 --vm-type qemu --cpu 6 --memory 12 --disk 40

Problem 6: kubectl pointing to dead cluster (connection refused 0.0.0.0:62619)
Root cause: Old k3d-mycluster was the current context but was down. New mlops cluster hadn't been created yet.

Fix:

k3d cluster delete mycluster
k3d cluster create mlops --agents 1 --servers 1 --agents-memory 8g
kubectl config use-context k3d-mlops

Problem 7: k3d load balancer node crash (k3d-mlops-serverlb restarting)
Root cause: Port conflict on host — NGINX LB node couldn't bind.

Fix: Skip the LB node (not needed for local port-forward dev):

colima delete --force
colima start --arch x86_64 --vm-type qemu --cpu 6 --memory 12 --disk 40

k3d cluster create mlops \
  --servers 1 \
  --agents 1 \
  --no-lb \
  --k3s-node-label "role=server@server:0" \
  --agents-memory 8g

Final Working Colima Start Command
brew install lima-additional-guestagents   # one-time
colima delete --force
colima start --arch x86_64 --vm-type qemu --cpu 6 --memory 12 --disk 40

Verify Architecture
colima status --extended | grep arch   # must show: arch: x86_64
colima ssh -- uname -m                 # must show: x86_64

Final Working Cluster Create Command
k3d cluster create mlops \
  --agents 2 \
  --servers 1 \
  --agents-memory 6g \
  --no-lb
kubectl config use-context k3d-mlops


1. Cluster and architecture fixes (Apple Silicon + KFP)

Root cause for KFP image pull errors was architecture mismatch (ARM host vs AMD64 images).
Reliable setup was Colima in x86_64 mode with QEMU:
colima delete --force
colima start --arch x86_64 --vm-type qemu --cpu 6 --memory 12 --disk 40
If Colima failed due missing guest agent binaries, install:
brew install lima-additional-guestagents
Recreate k3d after Colima changes:
k3d cluster delete mlops
k3d cluster create mlops --agents 2 --servers 1 --agents-memory 6g
Ensure kubectl context points to live cluster:
kubectl config use-context k3d-mlops
2. MinIO deployment fixes

Helm install timeout was caused by unschedulable MinIO pod due very high memory request.
Reduced MinIO values solved scheduling:
persistence size reduced (2Gi worked in your setup)
resources requests/limits reduced (for example request 2Gi, limit 4Gi)
Namespace issues caused “service not found” confusion:
Always use -n mlops or set default namespace with kubectl config set-context --current --namespace=mlops
3. MinIO access and console behavior

MinIO console port-forward timeout/broken pipe messages were mostly non-fatal websocket behavior with kubectl port-forward.
Console login issues were bypassed by using MinIO CLI directly.
Bucket creation/verification that worked:
mc alias set local http://127.0.0.1:9000 admin admin12345
mc mb local/mlflow
mc ls local
Important gotcha: your shell had mc as Midnight Commander earlier, not MinIO client. Installing MinIO mc fixed that.
4. MLflow connectivity fixes

MLflow failures were initially DB auth and DB permission issues.
Working MLflow startup args included:
--backend-store-uri postgresql://mlflow:mlflowpass@postgres-postgresql:5432/mlflowdb
--default-artifact-root s3://mlflow
--host 0.0.0.0
--allowed-hosts *
Port-forward for MLflow should target app port 5000:
kubectl port-forward deployment/mlflow 5000:5000 -n mlops
“connection refused” during port-forward generally meant pod restart/crash during startup window.
5. PostgreSQL/MLflow DB issues

Reinstalling Postgres without cleaning old state can keep old credentials/data.
Helm warning about old PVC/password reuse was relevant in your case.
You recovered by fixing roles/db/privileges manually; final blocking error was schema permissions.
Critical DB grant that resolved MLflow table init:
GRANT ALL ON SCHEMA public TO mlflow;
6. Kubeflow Pipelines fixes

Missing Application CRD caused initial apply failure:
Install applications.app.k8s.io CRD before KFP env/dev apply.
workflow-controller CrashLoopBackOff with “workflows.argoproj.io not found” was fixed by installing Argo Workflows CRDs.
proxy-agent ImagePullBackOff in local setup was mitigated by scaling to 0:
kubectl scale deployment proxy-agent -n kubeflow --replicas=0
controller-manager OOMKilled was mitigated by increasing/patching memory resources.
7. DVC setup fixes

DVC must be initialized in a Git repository (or use --no-scm).
You hit:
dvc init failed when repo was not under SCM
dvc init failed with “.dvc exists” once already initialized (expected)
DVC remote to MinIO that worked:
dvc remote add -d minio s3://mlflow/dvc
dvc remote modify minio endpointurl http://127.0.0.1:9000
dvc remote modify minio access_key_id admin
dvc remote modify minio secret_access_key admin12345
dvc remote modify minio use_ssl false

____________________________________________________________________________


colima start --arch x86_64 --vm-type qemu --cpu 6 --memory 13 --disk 40

k3d cluster delete mlops

 k3d cluster create mlops \
  --agents 2 \
  --servers 1 \
  --agents-memory 6g


kubectl create namespace mlops
kubectl config set-context --current --namespace=mlops

helm repo add bitnami https://charts.bitnami.com/bitnami
helm repo add minio https://charts.min.io/
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update


helm install postgres bitnami/postgresql --namespace mlops \
  --set auth.username=mlflow \
  --set auth.password=mlflowpass \
  --set auth.database=mlflowdb

helm install minio minio/minio -n mlops -f minio-values.yaml

kubectl port-forward svc/minio 9000:9000
kubectl port-forward svc/minio-console 9001:9001


helm install redis bitnami/redis -n mlops \
  --set architecture=standalone \
  --set auth.enabled=false

kubectl apply -f mlflow-deployment.yaml

kubectl port-forward deployment/mlflow 5000:5000

k create namespace kubeflow 

kubectl apply -k \
github.com/kubeflow/pipelines/manifests/kustomize/cluster-scoped-resources

kubectl apply -k \
github.com/kubeflow/pipelines/manifests/kustomize/env/dev

kubectl apply -k https://github.com/argoproj/argo-workflows/manifests/base/crds/minimal?ref=v3.7.3
kubectl rollout restart deployment/workflow-controller -n kubeflow
kubectl scale deployment proxy-agent -n kubeflow --replicas=0

kubectl apply -f https://raw.githubusercontent.com/kubernetes-sigs/application/master/config/crd/bases/app.k8s.io_applications.yaml
kubectl apply -k github.com/kubeflow/pipelines/manifests/kustomize/env/dev



dvc init
dvc remote add -d minio s3://mlflow/dvc
dvc remote modify minio endpointurl http://127.0.0.1:9000
dvc remote modify minio access_key_id admin
dvc remote modify minio secret_access_key admin12345
dvc remote modify minio use_ssl false




HOW TO START LATEST:
colima start --arch x86_64 --vm-type qemu --cpu 7 --memory 13 --disk 20

k3d cluster create mlops \
  --agents 1 \
  --servers 1 \
  --agents-memory 8g \
  --no-lb \
  -p "5001:5000@server:0" \
  -p "8080:80@server:0" \
  -p "9000:9000@server:0" \
  -p "9001:9001@server:0"

!!!Then patch MLflow service to NodePort and it's accessible at localhost:5001 without any port-forward

kubectl config use-context k3d-mlops
kubectl config set-context --current --namespace=mlops

kubectl create namespace mlops
kubectl config set-context --current --namespace=mlops
helm install postgres bitnami/postgresql -n mlops \
  --set auth.username=mlflow \
  --set auth.password=mlflowpass \
  --set auth.database=mlflowdb
helm install minio minio/minio -n mlops -f minio-values.yaml
helm install redis bitnami/redis -n mlops \
  --set architecture=standalone \
  --set auth.enabled=false
kubectl apply -f mlflow-deployment.yaml

kubectl port-forward svc/minio 9000:9000 -n mlops &
mc alias set local http://127.0.0.1:9000 admin admin12345
mc mb local/mlflow
mc mb local/feast-registry


!!! MLFLOW container starts about 4-5 minutes, so just wait before port-forward 
WAIT until Logs starts 
kubeflow logs -n mlops deployment/mlflow -f 
ONLY then kubectl port-forward svc/mlflow 5001:5000 -n mlops

IN CASE OF ERRORS:
kubectl exec -it postgres-postgresql-0 -n mlops -- \
  psql -U mlflow -d mlflowdb -c "
DROP SCHEMA public CASCADE;
CREATE SCHEMA public;
GRANT ALL ON SCHEMA public TO mlflow;
GRANT ALL ON SCHEMA public TO public;
"

mlflowpass

kubectl rollout restart deployment/mlflow -n mlops
kubectl rollout status deployment/mlflow -n mlops

kubectl port-forward svc/mlflow 5001:5000 -n mlops


INSTALLATION OF KUBEFLOW

# 1. Create namespace
kubectl create namespace kubeflow

# 2. Apply Application CRD FIRST (missing this causes apply failure)
kubectl apply -f https://raw.githubusercontent.com/kubernetes-sigs/application/master/config/crd/bases/app.k8s.io_applications.yaml

# 3. Apply cluster-scoped resources
kubectl apply -k github.com/kubeflow/pipelines/manifests/kustomize/cluster-scoped-resources

# 4. Apply KFP dev environment
kubectl apply -k github.com/kubeflow/pipelines/manifests/kustomize/env/dev

# 5. Apply Argo Workflows CRDs (workflow-controller crashes without these)
kubectl apply -k "https://github.com/argoproj/argo-workflows/manifests/base/crds/minimal?ref=v3.7.3"

# 6. Restart workflow-controller to pick up CRDs
kubectl rollout restart deployment/workflow-controller -n kubeflow

# 7. Scale down proxy-agent (ImagePullBackOff in local setup — not needed)
kubectl scale deployment proxy-agent -n kubeflow --replicas=0

# 8. Patch controller-manager memory (OOMKilled otherwise)
kubectl set resources deployment controller-manager -n kubeflow \
  --limits=memory=512Mi,cpu=500m \
  --requests=memory=256Mi,cpu=100m

!!! WAIT ABOUT 20-30 MINUTES ALL SUPPOSE TO RUNNING Except proxy-agent stays at 0 replicas intentionally

kubectl get pods -n kubeflow -w

export AWS_ACCESS_KEY_ID=admin
export AWS_SECRET_ACCESS_KEY=admin12345
export MLFLOW_S3_ENDPOINT_URL=http://127.0.0.1:9000
export AWS_ENDPOINT_URL=http://127.0.0.1:9000

feast feature-views list