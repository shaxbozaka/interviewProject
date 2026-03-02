#!/usr/bin/env bash
set -euo pipefail

# ============================================================================
#  Kubernetes Deployment Script for Library Management System
# ============================================================================
#
#  Usage:
#    ./k8s/deploy.sh                    # Deploy everything
#    ./k8s/deploy.sh --infra-only       # Deploy only infrastructure
#    ./k8s/deploy.sh --app-only         # Deploy only application
#    ./k8s/deploy.sh --seed             # Run the massive data seeder
#    ./k8s/deploy.sh --destroy          # Tear down everything
#
#  Prerequisites:
#    - kubectl configured and connected to cluster
#    - Docker image built: docker build -t library-web:latest .
# ============================================================================

NAMESPACE="library"
IMAGE_NAME="library-web:latest"

echo "============================================"
echo "  Library Management — K8s Deployment"
echo "============================================"
echo ""

# Parse arguments
ACTION="${1:-deploy}"

case "$ACTION" in
  --destroy)
    echo "Destroying namespace '$NAMESPACE'..."
    kubectl delete namespace "$NAMESPACE" --ignore-not-found
    echo "Done."
    exit 0
    ;;
  --seed)
    echo "Running massive data seeder..."
    kubectl delete job db-seed -n "$NAMESPACE" --ignore-not-found 2>/dev/null
    kubectl apply -f k8s/jobs.yaml -n "$NAMESPACE"
    echo "Waiting for seed job to complete (this may take a few minutes)..."
    kubectl wait --for=condition=complete job/db-seed -n "$NAMESPACE" --timeout=600s
    kubectl logs job/db-seed -n "$NAMESPACE"
    echo ""
    echo "Running ES reindex..."
    kubectl delete job es-reindex -n "$NAMESPACE" --ignore-not-found 2>/dev/null
    kubectl apply -f k8s/jobs.yaml -n "$NAMESPACE"
    kubectl wait --for=condition=complete job/es-reindex -n "$NAMESPACE" --timeout=120s
    echo "Seed complete!"
    exit 0
    ;;
  --infra-only|--app-only|deploy)
    ;;
  *)
    echo "Unknown action: $ACTION"
    echo "Usage: $0 [--infra-only|--app-only|--seed|--destroy]"
    exit 1
    ;;
esac

# Step 1: Build Docker image
echo "[1/6] Building Docker image..."
docker build -t "$IMAGE_NAME" -f Dockerfile \
  --build-arg REQUIREMENTS_FILE=requirements/base.txt .
echo ""

# Step 2: Create namespace and configs
echo "[2/6] Creating namespace and configuration..."
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/secrets.yaml
kubectl apply -f k8s/configmap.yaml
echo ""

if [ "$ACTION" != "--app-only" ]; then
  # Step 3: Deploy infrastructure
  echo "[3/6] Deploying infrastructure (Postgres, Redis, RabbitMQ, Kafka, ES)..."
  kubectl apply -f k8s/postgres.yaml
  kubectl apply -f k8s/redis.yaml
  kubectl apply -f k8s/rabbitmq.yaml
  kubectl apply -f k8s/kafka.yaml
  kubectl apply -f k8s/elasticsearch.yaml

  echo "Waiting for infrastructure to be ready..."
  kubectl rollout status deployment/postgres -n "$NAMESPACE" --timeout=120s
  kubectl rollout status deployment/redis -n "$NAMESPACE" --timeout=60s
  kubectl rollout status deployment/rabbitmq -n "$NAMESPACE" --timeout=120s
  kubectl rollout status deployment/zookeeper -n "$NAMESPACE" --timeout=60s
  kubectl rollout status deployment/kafka -n "$NAMESPACE" --timeout=120s
  kubectl rollout status deployment/elasticsearch -n "$NAMESPACE" --timeout=180s
  echo "Infrastructure ready."
  echo ""
fi

if [ "$ACTION" != "--infra-only" ]; then
  # Step 4: Run migrations
  echo "[4/6] Running database migrations..."
  kubectl delete job db-migrate -n "$NAMESPACE" --ignore-not-found 2>/dev/null
  kubectl apply -f k8s/jobs.yaml
  kubectl wait --for=condition=complete job/db-migrate -n "$NAMESPACE" --timeout=120s
  echo "Migrations complete."
  echo ""

  # Step 5: Deploy application
  echo "[5/6] Deploying application (Web, Celery, Nginx)..."
  kubectl apply -f k8s/web.yaml
  kubectl apply -f k8s/celery.yaml
  kubectl apply -f k8s/nginx.yaml
  kubectl apply -f k8s/ingress.yaml

  kubectl rollout status deployment/web -n "$NAMESPACE" --timeout=120s
  kubectl rollout status deployment/celery-worker -n "$NAMESPACE" --timeout=120s
  kubectl rollout status deployment/nginx -n "$NAMESPACE" --timeout=60s
  echo "Application deployed."
  echo ""

  # Step 6: Summary
  echo "[6/6] Deployment summary..."
  echo ""
  kubectl get pods -n "$NAMESPACE" -o wide
  echo ""
  kubectl get svc -n "$NAMESPACE"
  echo ""

  NGINX_IP=$(kubectl get svc nginx -n "$NAMESPACE" -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || echo "pending")
  echo "============================================"
  echo "  Deployment Complete!"
  echo "============================================"
  echo ""
  echo "  Load Balancer IP: $NGINX_IP"
  echo "  Health Check:     curl http://$NGINX_IP/health/"
  echo "  API Docs:         http://$NGINX_IP/api/v1/"
  echo ""
  echo "  To seed with massive data:"
  echo "    ./k8s/deploy.sh --seed"
  echo ""
  echo "  To port-forward locally:"
  echo "    kubectl port-forward svc/nginx 8080:80 -n library"
  echo ""
fi
