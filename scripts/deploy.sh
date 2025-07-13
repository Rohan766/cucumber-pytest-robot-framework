#!/bin/bash

# Test Execution System Deployment Script
# Supports AWS ECS, Kubernetes, and Docker Compose

set -e

# Default values
ENVIRONMENT="staging"
PLATFORM="docker"
REGION="us-west-2"
PROJECT_NAME="test-execution-system"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

success() {
    echo -e "${GREEN}[SUCCESS] $1${NC}"
}

warning() {
    echo -e "${YELLOW}[WARNING] $1${NC}"
}

error() {
    echo -e "${RED}[ERROR] $1${NC}"
    exit 1
}

usage() {
    echo "Usage: $0 [OPTIONS]"
    echo "Options:"
    echo "  -e, --environment  Environment (staging|production) [default: staging]"
    echo "  -p, --platform     Platform (docker|aws|k8s|azure|gcp) [default: docker]"
    echo "  -r, --region       Cloud region [default: us-west-2]"
    echo "  -n, --name         Project name [default: test-execution-system]"
    echo "  -h, --help         Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 --environment production --platform aws"
    echo "  $0 --platform k8s --environment staging"
    echo "  $0 --platform docker"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -e|--environment)
            ENVIRONMENT="$2"
            shift 2
            ;;
        -p|--platform)
            PLATFORM="$2"
            shift 2
            ;;
        -r|--region)
            REGION="$2"
            shift 2
            ;;
        -n|--name)
            PROJECT_NAME="$2"
            shift 2
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            error "Unknown option: $1"
            ;;
    esac
done

# Validate environment
if [[ "$ENVIRONMENT" != "staging" && "$ENVIRONMENT" != "production" ]]; then
    error "Environment must be 'staging' or 'production'"
fi

# Validate platform
if [[ ! "$PLATFORM" =~ ^(docker|aws|k8s|azure|gcp)$ ]]; then
    error "Platform must be one of: docker, aws, k8s, azure, gcp"
fi

log "Starting deployment for $PROJECT_NAME"
log "Environment: $ENVIRONMENT"
log "Platform: $PLATFORM"
log "Region: $REGION"

# Check prerequisites
check_prerequisites() {
    log "Checking prerequisites..."
    
    # Common tools
    command -v docker >/dev/null 2>&1 || error "Docker is required but not installed"
    command -v git >/dev/null 2>&1 || error "Git is required but not installed"
    
    case $PLATFORM in
        aws)
            command -v aws >/dev/null 2>&1 || error "AWS CLI is required but not installed"
            command -v terraform >/dev/null 2>&1 || error "Terraform is required but not installed"
            ;;
        k8s)
            command -v kubectl >/dev/null 2>&1 || error "kubectl is required but not installed"
            command -v helm >/dev/null 2>&1 || warning "Helm is recommended for Kubernetes deployments"
            ;;
        azure)
            command -v az >/dev/null 2>&1 || error "Azure CLI is required but not installed"
            ;;
        gcp)
            command -v gcloud >/dev/null 2>&1 || error "Google Cloud CLI is required but not installed"
            ;;
    esac
    
    success "Prerequisites check passed"
}

# Build and push container image
build_and_push_image() {
    log "Building and pushing container image..."
    
    local image_tag
    if [[ "$ENVIRONMENT" == "production" ]]; then
        image_tag="ghcr.io/${GITHUB_REPOSITORY:-yourusername/test-execution-system}:latest"
    else
        image_tag="ghcr.io/${GITHUB_REPOSITORY:-yourusername/test-execution-system}:${ENVIRONMENT}"
    fi
    
    log "Building image: $image_tag"
    docker build -t "$image_tag" .
    
    log "Pushing image to registry..."
    docker push "$image_tag"
    
    success "Image built and pushed: $image_tag"
}

# Deploy with Docker Compose
deploy_docker() {
    log "Deploying with Docker Compose..."
    
    # Set environment variables
    export ENVIRONMENT=$ENVIRONMENT
    export PROJECT_NAME=$PROJECT_NAME
    
    # Create environment file if it doesn't exist
    if [[ ! -f .env ]]; then
        log "Creating .env file from template..."
        cp .env.example .env 2>/dev/null || warning ".env.example not found, please create .env manually"
    fi
    
    # Deploy
    docker-compose -f docker-compose.yml down --remove-orphans
    docker-compose -f docker-compose.yml up -d
    
    # Health check
    log "Waiting for services to be healthy..."
    sleep 30
    
    if curl -f http://localhost:8000/health > /dev/null 2>&1; then
        success "Docker deployment completed successfully"
        log "Application is available at: http://localhost:8000"
    else
        error "Health check failed"
    fi
}

# Deploy to AWS ECS
deploy_aws() {
    log "Deploying to AWS ECS..."
    
    # Check AWS credentials
    if ! aws sts get-caller-identity > /dev/null 2>&1; then
        error "AWS credentials not configured"
    fi
    
    # Set Terraform variables
    export TF_VAR_environment=$ENVIRONMENT
    export TF_VAR_project_name=$PROJECT_NAME
    export TF_VAR_aws_region=$REGION
    
    # Deploy infrastructure
    log "Deploying infrastructure with Terraform..."
    cd infrastructure/aws
    
    terraform init
    terraform plan -out=tfplan
    terraform apply tfplan
    
    # Get outputs
    local lb_dns=$(terraform output -raw load_balancer_dns)
    local cluster_name=$(terraform output -raw ecs_cluster_name)
    
    cd ../..
    
    # Update ECS service
    log "Updating ECS service..."
    aws ecs update-service \
        --cluster "$cluster_name" \
        --service "${PROJECT_NAME}-service" \
        --force-new-deployment \
        --region "$REGION"
    
    # Wait for deployment
    log "Waiting for deployment to complete..."
    aws ecs wait services-stable \
        --cluster "$cluster_name" \
        --services "${PROJECT_NAME}-service" \
        --region "$REGION"
    
    success "AWS ECS deployment completed successfully"
    log "Application is available at: http://$lb_dns"
}

# Deploy to Kubernetes
deploy_k8s() {
    log "Deploying to Kubernetes..."
    
    # Check kubectl context
    local current_context=$(kubectl config current-context 2>/dev/null || echo "")
    if [[ -z "$current_context" ]]; then
        error "No Kubernetes context configured"
    fi
    
    log "Deploying to Kubernetes context: $current_context"
    
    # Create namespace
    kubectl create namespace test-execution --dry-run=client -o yaml | kubectl apply -f -
    kubectl create namespace monitoring --dry-run=client -o yaml | kubectl apply -f -
    
    # Deploy application
    log "Applying Kubernetes manifests..."
    kubectl apply -f k8s/namespace.yaml
    kubectl apply -f k8s/configmap.yaml
    kubectl apply -f k8s/storage.yaml
    kubectl apply -f k8s/deployment.yaml
    kubectl apply -f k8s/services.yaml
    kubectl apply -f k8s/ingress.yaml
    
    # Deploy monitoring (optional)
    log "Deploying monitoring stack..."
    kubectl apply -f monitoring/prometheus.yaml
    kubectl apply -f monitoring/grafana.yaml
    
    # Wait for deployment
    log "Waiting for deployment to be ready..."
    kubectl rollout status deployment/test-execution-api -n test-execution --timeout=300s
    
    # Get ingress URL
    local ingress_ip=$(kubectl get ingress test-execution-ingress -n test-execution -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || echo "")
    
    success "Kubernetes deployment completed successfully"
    if [[ -n "$ingress_ip" ]]; then
        log "Application is available at: http://$ingress_ip"
    else
        log "Use 'kubectl port-forward svc/test-execution-api 8000:8000 -n test-execution' to access locally"
    fi
}

# Deploy to Azure
deploy_azure() {
    log "Deploying to Azure..."
    
    # Check Azure login
    if ! az account show > /dev/null 2>&1; then
        error "Not logged in to Azure. Run 'az login' first."
    fi
    
    local resource_group="${PROJECT_NAME}-${ENVIRONMENT}-rg"
    local container_group="${PROJECT_NAME}-${ENVIRONMENT}-cg"
    
    # Create resource group
    log "Creating resource group..."
    az group create --name "$resource_group" --location "$REGION"
    
    # Deploy container instance
    log "Deploying container instance..."
    az container create \
        --resource-group "$resource_group" \
        --name "$container_group" \
        --image "ghcr.io/yourusername/test-execution-system:latest" \
        --ports 8000 \
        --dns-name-label "${PROJECT_NAME}-${ENVIRONMENT}" \
        --environment-variables \
            ENVIRONMENT="$ENVIRONMENT" \
            DB_HOST="localhost" \
        --cpu 2 \
        --memory 4
    
    # Get FQDN
    local fqdn=$(az container show --resource-group "$resource_group" --name "$container_group" --query ipAddress.fqdn --output tsv)
    
    success "Azure deployment completed successfully"
    log "Application is available at: http://$fqdn:8000"
}

# Deploy to Google Cloud Platform
deploy_gcp() {
    log "Deploying to Google Cloud Platform..."
    
    # Check GCP authentication
    if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" > /dev/null 2>&1; then
        error "Not authenticated with GCP. Run 'gcloud auth login' first."
    fi
    
    local project_id=$(gcloud config get-value project)
    local service_name="${PROJECT_NAME}-${ENVIRONMENT}"
    
    if [[ -z "$project_id" ]]; then
        error "No GCP project configured. Run 'gcloud config set project PROJECT_ID'"
    fi
    
    log "Deploying to GCP project: $project_id"
    
    # Deploy to Cloud Run
    log "Deploying to Cloud Run..."
    gcloud run deploy "$service_name" \
        --image "ghcr.io/yourusername/test-execution-system:latest" \
        --platform managed \
        --region "$REGION" \
        --allow-unauthenticated \
        --set-env-vars "ENVIRONMENT=$ENVIRONMENT" \
        --memory 2Gi \
        --cpu 2
    
    # Get service URL
    local service_url=$(gcloud run services describe "$service_name" --platform managed --region "$REGION" --format 'value(status.url)')
    
    success "GCP deployment completed successfully"
    log "Application is available at: $service_url"
}

# Run health check
health_check() {
    log "Running post-deployment health check..."
    
    local url
    case $PLATFORM in
        docker)
            url="http://localhost:8000"
            ;;
        *)
            log "Manual health check required for $PLATFORM deployment"
            return 0
            ;;
    esac
    
    local max_attempts=30
    local attempt=1
    
    while [[ $attempt -le $max_attempts ]]; do
        if curl -f "$url/health" > /dev/null 2>&1; then
            success "Health check passed"
            return 0
        fi
        
        log "Health check attempt $attempt/$max_attempts failed, retrying in 10 seconds..."
        sleep 10
        ((attempt++))
    done
    
    error "Health check failed after $max_attempts attempts"
}

# Main deployment function
main() {
    check_prerequisites
    
    case $PLATFORM in
        docker)
            build_and_push_image
            deploy_docker
            health_check
            ;;
        aws)
            build_and_push_image
            deploy_aws
            ;;
        k8s)
            build_and_push_image
            deploy_k8s
            ;;
        azure)
            build_and_push_image
            deploy_azure
            ;;
        gcp)
            build_and_push_image
            deploy_gcp
            ;;
    esac
    
    success "Deployment completed successfully!"
    
    # Print useful information
    echo ""
    log "Deployment Information:"
    log "Environment: $ENVIRONMENT"
    log "Platform: $PLATFORM"
    log "Region: $REGION"
    echo ""
    log "Useful commands:"
    case $PLATFORM in
        docker)
            log "  View logs: docker-compose logs -f"
            log "  Stop services: docker-compose down"
            ;;
        aws)
            log "  View logs: aws logs tail /aws/ecs/$PROJECT_NAME --follow"
            log "  Scale service: aws ecs update-service --cluster $PROJECT_NAME-cluster --service $PROJECT_NAME-service --desired-count 3"
            ;;
        k8s)
            log "  View logs: kubectl logs -f deployment/test-execution-api -n test-execution"
            log "  Scale deployment: kubectl scale deployment test-execution-api --replicas=3 -n test-execution"
            ;;
    esac
}

# Run main function
main 