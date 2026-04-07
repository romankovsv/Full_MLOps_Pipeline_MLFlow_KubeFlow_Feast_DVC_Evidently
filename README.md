

Kubeflow Pipelines
       │
       ▼
 Model Training
       │
 ┌─────┴─────────┐
 ▼               ▼
MLflow      Feature Store
 │               │
 ▼               ▼
PostgreSQL   Feast
                 │
      ┌──────────┴──────────┐
      ▼                     ▼
Offline Store         Online Store
   (File)                (Redis)
      │                     │
      └──────────┬──────────┘
                 ▼
               MinIO
              /  |  \
             ▼   ▼   ▼
         DVC   MLflow Artifacts
                 │
                 ▼
         Drift Monitoring
             Evidently
                 │
                 ▼
        Prometheus + Grafana
____________________________________________________________________________________

colima start --arch x86_64 --vm-type qemu --cpu 7 --memory 13 --disk 20

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
colima start --arch x86_64 --vm-type qemu --cpu 8 --memory 14 --disk 25

k3d cluster create mlops \
  --agents 1 \
  --servers 1 \
  --agents-memory 8g \
  --servers-memory 4g \
  -p "5001:5000@server:0:direct" \
  -p "8383:80@server:0:direct" \
  -p "9000:9000@server:0:direct" \
  -p "9001:9001@server:0:direct" \
  --no-lb \
  --k3s-arg "--disable=traefik@server:0" \
  --timeout 5m

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

export AWS_ACCESS_KEY_ID=
export AWS_SECRET_ACCESS_KEY=
export MLFLOW_S3_ENDPOINT_URL=http://127.0.0.1:9000
export AWS_ENDPOINT_URL=http://127.0.0.1:9000

feast feature-views list