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


helm install redis bitnami/redis -n mlops

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