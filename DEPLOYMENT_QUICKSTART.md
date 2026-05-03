# Quick Start Guide - Deploying Data Platform to Production

## Prerequisites

- Google Cloud Platform account with billing enabled
- GitHub account with repository access
- Docker installed locally
- `gcloud`, `terraform`, and `kubectl` CLIs installed
- OpenAI API key (optional, for AI features)

---

## Step 1: Prepare Your Environment

### 1.1 Clone Repository and Structure

```bash
# Your repository structure should be:
my-data-platform/
├── backend/          # FastAPI application
├── frontend/         # React application
├── terraform/        # IaC configuration
├── .github/
│   └── workflows/    # CI/CD pipelines
├── docker-compose.prod.yml
└── .env.example

# Copy .env.example to .env
cp .env.example .env
```

### 1.2 Create Environment Files

```bash
# .env for local testing
cat > .env << EOF
ENVIRONMENT=development
DB_PASSWORD=your_secure_password_here
REDIS_PASSWORD=your_redis_password_here
OPENAI_API_KEY=your_openai_key
ALLOWED_ORIGINS=http://localhost:5173,http://localhost:3000
LOG_LEVEL=info
EOF

# .env.production for production
cat > .env.production << EOF
ENVIRONMENT=production
DB_PASSWORD=$(openssl rand -base64 32)
REDIS_PASSWORD=$(openssl rand -base64 32)
OPENAI_API_KEY=your_production_key
ALLOWED_ORIGINS=https://yourfrontend.com
LOG_LEVEL=warning
EOF
```

---

## Step 2: Containerize Application

### 2.1 Build Docker Images

```bash
# Backend
docker build -t data-platform-backend:latest -f backend/Dockerfile ./backend

# Frontend
docker build -t data-platform-frontend:latest -f frontend/Dockerfile ./frontend

# Test locally with docker-compose
docker-compose -f docker-compose.prod.yml up -d

# Verify services
docker-compose -f docker-compose.prod.yml ps
docker-compose -f docker-compose.prod.yml logs backend
```

### 2.2 Push to Container Registry

```bash
# For GCP (use Google Artifact Registry)
gcloud auth configure-docker gcr.io

# Tag and push
docker tag data-platform-backend:latest gcr.io/PROJECT_ID/data-platform-backend:latest
docker push gcr.io/PROJECT_ID/data-platform-backend:latest

docker tag data-platform-frontend:latest gcr.io/PROJECT_ID/data-platform-frontend:latest
docker push gcr.io/PROJECT_ID/data-platform-frontend:latest
```

---

## Step 3: Set Up GCP Project

### 3.1 Create Project and Enable APIs

```bash
# Set your project ID
export PROJECT_ID="my-data-platform-prod"
export REGION="us-central1"

# Create project
gcloud projects create $PROJECT_ID --name="Data Platform Production"
gcloud config set project $PROJECT_ID

# Enable required APIs
gcloud services enable run.googleapis.com sql.googleapis.com compute.googleapis.com \
  cloudresourcemanager.googleapis.com servicenetworking.googleapis.com \
  monitoring.googleapis.com logging.googleapis.com artifact-registry.googleapis.com \
  cloudkms.googleapis.com

# Create Artifact Registry for Docker images
gcloud artifacts repositories create data-platform \
  --repository-format=docker \
  --location=$REGION \
  --description="Data Platform container images"
```

### 3.2 Configure Terraform Backend (for state management)

```bash
# Create GCS bucket for Terraform state
gsutil mb -p $PROJECT_ID gs://${PROJECT_ID}-terraform-state

# Create terraform backend config
cat > terraform/backend.tf << 'EOF'
terraform {
  backend "gcs" {
    bucket = "${PROJECT_ID}-terraform-state"
    prefix = "data-platform/prod"
  }
}
EOF

# Replace PROJECT_ID with actual value
sed -i "s/\${PROJECT_ID}/$PROJECT_ID/g" terraform/backend.tf
```

---

## Step 4: Deploy Infrastructure with Terraform

### 4.1 Initialize Terraform

```bash
cd terraform

# Initialize
terraform init -backend-config="bucket=${PROJECT_ID}-terraform-state" -backend-config="prefix=data-platform/prod"

# Validate
terraform validate

# Plan deployment (review changes)
terraform plan \
  -var="project_id=$PROJECT_ID" \
  -var="region=$REGION" \
  -var="environment=production" \
  -var="db_password=$(openssl rand -base64 32)" \
  -var="frontend_domain=yourfrontend.com" \
  -var="alert_email=your-email@example.com" \
  -out=tfplan.out
```

### 4.2 Apply Terraform Configuration

```bash
# Apply changes (this provisions all resources)
terraform apply tfplan.out

# Note the outputs
terraform output backend_url
terraform output frontend_static_bucket
terraform output database_connection_name
```

---

## Step 5: Configure Database

### 5.1 Run Database Migrations

```bash
# Get Cloud SQL proxy connection
cloud_sql_instance=$(terraform output -raw database_connection_name)

# Option A: Using Cloud SQL Proxy locally
cloud-sql-proxy $cloud_sql_instance &

# Option B: From inside a container/Cloud Run instance
# Use private IP instead

# Run migrations
cd backend
alembic upgrade head
```

### 5.2 Create Initial Data (Optional)

```bash
# Create admin user, default datasets, etc.
python scripts/setup_initial_data.py
```

---

## Step 6: Set Up CI/CD with GitHub Actions

### 6.1 Create GitHub Secrets

```bash
# Add these as GitHub repository secrets:
# Settings → Secrets and Variables → Actions

# GCP Authentication
GCP_PROJECT_ID="my-data-platform-prod"

# For Workload Identity (recommended)
WIF_PROVIDER="projects/PROJECT_NUMBER/locations/global/workloadIdentityPools/github-pool/providers/github-provider"
WIF_SERVICE_ACCOUNT="github-actions@$PROJECT_ID.iam.gserviceaccount.com"

# API Keys
OPENAI_API_KEY="sk-..."

# Database URLs (from Terraform outputs)
GCP_DATABASE_URL="postgresql://..."
GCP_REDIS_URL="redis://..."

# Slack webhook for notifications
SLACK_WEBHOOK="https://hooks.slack.com/services/..."
```

### 6.2 Update Workflow File

Ensure `.github/workflows/deploy-gcp.yml` has correct paths and secrets referenced.

---

## Step 7: Deploy Application

### 7.1 First Deployment (Manual)

```bash
# Push code to main branch triggers automatic deployment via GitHub Actions
git add .
git commit -m "Deploy to production"
git push origin main

# Monitor deployment
gcloud run services describe data-platform-api --region $REGION
gcloud run jobs describe data-platform-worker --region $REGION

# View logs
gcloud run services logs read data-platform-api --region $REGION --limit=100
```

### 7.2 Deploy Celery Worker

Worker should be deployed automatically via GitHub Actions, but can manually deploy:

```bash
gcloud run jobs deploy data-platform-worker \
  --image gcr.io/$PROJECT_ID/data-platform-backend:latest \
  --region $REGION \
  --memory 4Gi \
  --cpu 2 \
  --command celery \
  --args -A,worker.celery_app,worker,--loglevel=info
```

---

## Step 8: Configure Domain & SSL

### 8.1 Set Up Custom Domain

```bash
# For Cloud Run
gcloud run services update data-platform-api \
  --region $REGION \
  --update-env-vars ALLOWED_ORIGINS=https://yourdomain.com

# Map custom domain
gcloud run domain-mappings create \
  --service data-platform-api \
  --domain api.yourdomain.com \
  --region $REGION
```

### 8.2 Set Up Frontend CDN

```bash
# Frontend is served from Cloud Storage + Cloud CDN (already configured in Terraform)
# Just update your DNS to point to the CDN

# Verify CDN is caching
curl -I https://yourdomain.com | grep Cache-Control
```

---

## Step 9: Monitoring & Logging

### 9.1 Access Monitoring Dashboards

```bash
# List available resources for monitoring
gcloud monitoring dashboards list

# Create custom dashboard
gcloud monitoring dashboards create --config-from-file=monitoring-dashboard.yaml
```

### 9.2 Set Up Alerts

```bash
# Alerts defined in Terraform (alert_rules.yml)
# Access alerting policies:
gcloud alpha monitoring policies list

# View alert history
gcloud logging read "severity>=ERROR" --limit=50
```

### 9.3 View Application Logs

```bash
# Cloud Run application logs
gcloud run services logs read data-platform-api --region $REGION --tail

# Filter by request path
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=data-platform-api AND httpRequest.requestUrl=~/api/datasets" --limit=50
```

---

## Step 10: Testing & Validation

### 10.1 Health Checks

```bash
# Get backend URL
backend_url=$(gcloud run services describe data-platform-api --region $REGION --format='value(status.url)')

# Test API health
curl $backend_url/health

# Test database connectivity
curl $backend_url/api/datasets -H "Authorization: Bearer YOUR_TOKEN"

# Test frontend
# Open https://yourdomain.com in browser
```

### 10.2 Load Testing

```bash
# Install Apache Bench
# macOS: brew install ab
# Ubuntu: sudo apt-get install apache2-utils

# Basic load test (100 requests, 10 concurrent)
ab -n 100 -c 10 $backend_url/api/datasets

# More sophisticated load testing with k6
npm install -g k6

k6 run load-test.js
```

---

## Step 11: Scaling & Optimization

### 11.1 Configure Auto-scaling

```bash
# Already configured in Terraform, but can adjust:
gcloud run services update data-platform-api \
  --region $REGION \
  --min-instances=1 \
  --max-instances=100
```

### 11.2 Database Connection Pooling

```bash
# Cloud SQL Proxy handles this, but for direct connections:
# Update SQLAlchemy pool settings in backend/db.py

DATABASE_URL = "postgresql://...?pool_size=20&max_overflow=40"
```

### 11.3 CDN Cache Invalidation

```bash
# When deploying new frontend
gcloud compute backend-buckets invalidate-cdn-cache data-platform-backend-bucket \
  --path "/*" \
  --region $REGION
```

---

## Step 12: Backup & Disaster Recovery

### 12.1 Database Backups

```bash
# Automated backups configured in Terraform
# Verify backup settings
gcloud sql instances describe data-platform-db --format='value(settings.backupConfiguration)'

# Manual backup
gcloud sql backups create \
  --instance=data-platform-db \
  --description="Pre-major-release backup"

# List backups
gcloud sql backups list --instance=data-platform-db
```

### 12.2 Restore from Backup

```bash
# If needed (CAREFUL!)
gcloud sql backups restore BACKUP_ID \
  --backup-instance=data-platform-db \
  --backup-configuration=<config-id>
```

---

## Troubleshooting

### Issue: Backend can't connect to database

```bash
# Check Cloud SQL proxy
gcloud sql instances describe data-platform-db --format='value(ipAddresses)'

# Verify service account has SQL permissions
gcloud projects get-iam-policy $PROJECT_ID \
  --flatten="bindings[].members" \
  --filter="bindings.members:serviceAccount:*" \
  --format="table(bindings.role)" | grep sql
```

### Issue: Frontend shows 404

```bash
# Verify static files uploaded to Cloud Storage
gsutil ls -r gs://$PROJECT_ID-static/

# Check CDN cache
gcloud compute backend-buckets get-health-check data-platform-backend-bucket
```

### Issue: Celery tasks not processing

```bash
# Check Redis connection
gcloud redis instances describe data-platform-redis --region $REGION

# View Celery logs
gcloud logging read "resource.type=cloud_run_job AND severity=ERROR" --limit=50
```

---

## Cost Optimization Tips

1. **Use Preemptible VMs** for non-critical workers (70% cost savings)
2. **Enable CDN caching** for static assets (free tier included)
3. **Set up auto-scaling** to scale down during off-hours
4. **Use Cloud Storage lifecycle policies** to move old backups to Nearline
5. **Monitor costs** with Cost Management dashboard

---

## Next Steps

1. ✅ Complete deployment as per above
2. ✅ Run integration tests
3. ✅ Load test the platform
4. ✅ Set up team access (IAM roles)
5. ✅ Document deployment procedures for team
6. ✅ Set up runbooks for common operations
7. ✅ Plan disaster recovery drills

---

For more details, refer to [PLATFORM_RECOMMENDATIONS.md](./PLATFORM_RECOMMENDATIONS.md)
