# Terraform configuration for GCP deployment
# Save as: terraform/main.tf

terraform {
  required_version = ">= 1.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# Enable required APIs
resource "google_project_service" "required_apis" {
  for_each = toset([
    "run.googleapis.com",
    "sql.googleapis.com",
    "compute.googleapis.com",
    "cloudresourcemanager.googleapis.com",
    "servicenetworking.googleapis.com",
    "monitoring.googleapis.com",
    "logging.googleapis.com"
  ])
  
  service            = each.value
  disable_on_destroy = false
}

# VPC Network
resource "google_compute_network" "vpc" {
  name                    = "${var.project_id}-vpc"
  auto_create_subnetworks = false
}

resource "google_compute_subnetwork" "subnet" {
  name          = "${var.project_id}-subnet"
  ip_cidr_range = "10.0.0.0/24"
  region        = var.region
  network       = google_compute_network.vpc.id
}

# Cloud SQL PostgreSQL Instance
resource "google_sql_database_instance" "postgres" {
  name             = "${var.project_id}-db"
  database_version = "POSTGRES_15"
  region           = var.region
  
  settings {
    tier              = "db-f1-micro"
    availability_type = "REGIONAL"
    
    backup_configuration {
      enabled                        = true
      point_in_time_recovery_enabled = true
      backup_retention_days          = 30
    }
    
    ip_configuration {
      ipv4_enabled    = false
      private_network = google_compute_network.vpc.id
      require_ssl     = true
    }
    
    database_flags {
      name  = "max_connections"
      value = "100"
    }
    
    database_flags {
      name  = "shared_buffers"
      value = "262144"  # 2GB
    }
  }
  
  deletion_protection = var.environment == "production" ? true : false
  
  depends_on = [google_project_service.required_apis]
}

resource "google_sql_database" "data_platform_db" {
  name     = "data_platform"
  instance = google_sql_database_instance.postgres.name
}

resource "google_sql_user" "db_user" {
  name     = "dataplatform"
  instance = google_sql_database_instance.postgres.name
  password = var.db_password
}

# Cloud Memorystore Redis Instance
resource "google_redis_instance" "cache" {
  name           = "${var.project_id}-redis"
  tier           = "BASIC"
  memory_size_gb = 1
  region         = var.region
  
  redis_configs = {
    maxmemory-policy = "allkeys-lru"
  }
  
  auth_enabled = true
  
  depends_on = [google_project_service.required_apis]
}

# Cloud Run Backend Service
resource "google_cloud_run_service" "backend" {
  name     = "${var.project_id}-api"
  location = var.region
  
  template {
    spec {
      containers {
        image = "gcr.io/${var.project_id}/data-platform-backend:latest"
        
        env {
          name  = "DATABASE_URL"
          value = "postgresql://${google_sql_user.db_user.name}:${google_sql_user.db_user.password}@${google_sql_database_instance.postgres.private_ip_address}:5432/${google_sql_database.data_platform_db.name}"
        }
        
        env {
          name  = "REDIS_URL"
          value = "redis://:${random_password.redis_auth.result}@${google_redis_instance.cache.host}:${google_redis_instance.cache.port}"
        }
        
        env {
          name  = "ENVIRONMENT"
          value = var.environment
        }
        
        env {
          name  = "OPENAI_API_KEY"
          value = var.openai_api_key
        }
        
        resources {
          limits = {
            cpu    = "2"
            memory = "4Gi"
          }
        }
        
        ports {
          container_port = 8000
        }
      }
      
      service_account_name = google_service_account.backend.email
      
      timeout_seconds       = 3600
      service_account_name  = google_service_account.backend.email
    }
    
    metadata {
      annotations = {
        "autoscaling.knative.dev/maxScale" = "100"
        "autoscaling.knative.dev/minScale" = "1"
      }
    }
  }
  
  traffic {
    percent         = 100
    latest_revision = true
  }
  
  depends_on = [google_project_service.required_apis]
}

# Cloud Run Celery Worker
resource "google_cloud_run_job" "celery_worker" {
  name     = "${var.project_id}-worker"
  location = var.region
  
  template {
    spec {
      containers {
        image = "gcr.io/${var.project_id}/data-platform-backend:latest"
        
        command = [
          "celery",
          "-A",
          "worker.celery_app",
          "worker",
          "--loglevel=info",
          "-c",
          "4"
        ]
        
        env {
          name  = "DATABASE_URL"
          value = "postgresql://${google_sql_user.db_user.name}:${google_sql_user.db_user.password}@${google_sql_database_instance.postgres.private_ip_address}:5432/${google_sql_database.data_platform_db.name}"
        }
        
        env {
          name  = "REDIS_URL"
          value = "redis://:${random_password.redis_auth.result}@${google_redis_instance.cache.host}:${google_redis_instance.cache.port}"
        }
        
        resources {
          limits = {
            cpu    = "2"
            memory = "4Gi"
          }
        }
      }
      
      service_account_name = google_service_account.backend.email
      timeout_seconds      = 3600
    }
  }
  
  depends_on = [google_project_service.required_apis]
}

# Cloud Storage for uploads
resource "google_storage_bucket" "uploads" {
  name          = "${var.project_id}-uploads"
  location      = var.region
  force_destroy = var.environment != "production" ? true : false
  
  lifecycle_rule {
    action {
      type          = "Delete"
      storage_class = "NEARLINE"
    }
    condition {
      age = 90  # Delete after 90 days
    }
  }
  
  cors {
    origin          = ["https://${var.frontend_domain}"]
    method          = ["GET", "PUT", "POST"]
    response_header = ["Content-Type"]
    max_age_seconds = 3600
  }
}

# Cloud Storage for static assets
resource "google_storage_bucket" "static" {
  name          = "${var.project_id}-static"
  location      = var.region
  force_destroy = var.environment != "production" ? true : false
  
  website {
    main_page_suffix = "index.html"
    not_found_page   = "404.html"
  }
}

resource "google_storage_bucket_object" "frontend_files" {
  for_each       = toset(fileset("../frontend/dist", "**"))
  bucket         = google_storage_bucket.static.name
  name           = each.value
  source         = "../frontend/dist/${each.value}"
  content_type   = lookup(local.mime_types, split(".", each.value)[length(split(".", each.value)) - 1], "application/octet-stream")
  cache_control  = startswith(each.value, "index.html") ? "no-cache" : "public, max-age=31536000"
}

locals {
  mime_types = {
    "html" = "text/html"
    "css"  = "text/css"
    "js"   = "application/javascript"
    "json" = "application/json"
    "png"  = "image/png"
    "jpg"  = "image/jpeg"
    "svg"  = "image/svg+xml"
  }
}

# Cloud CDN
resource "google_compute_backend_bucket" "static_cdn" {
  name            = "${var.project_id}-backend-bucket"
  bucket_name     = google_storage_bucket.static.name
  enable_cdn      = true
  compression_mode = "AUTOMATIC"
  
  cdn_policy {
    cache_mode        = "CACHE_ALL_STATIC"
    client_ttl        = 3600
    default_ttl       = 3600
    max_ttl           = 86400
    negative_caching  = true
    serve_while_stale = 86400
  }
}

# Service Account
resource "google_service_account" "backend" {
  account_id   = "${var.project_id}-backend"
  display_name = "Data Platform Backend Service Account"
}

# IAM Roles
resource "google_project_iam_member" "backend_sql_user" {
  project = var.project_id
  role    = "roles/cloudsql.client"
  member  = "serviceAccount:${google_service_account.backend.email}"
}

resource "google_project_iam_member" "backend_storage" {
  project = var.project_id
  role    = "roles/storage.admin"
  member  = "serviceAccount:${google_service_account.backend.email}"
}

# Random password for Redis
resource "random_password" "redis_auth" {
  length  = 32
  special = true
}

# Cloud Monitoring Alert Policy
resource "google_monitoring_alert_policy" "backend_error_rate" {
  display_name = "High Error Rate - ${var.project_id}"
  combiner     = "OR"
  
  conditions {
    display_name = "Error rate > 5%"
    
    condition_threshold {
      filter          = "resource.type=\"cloud_run_revision\" AND metric.type=\"run.googleapis.com/request_count\" AND resource.labels.service_name=\"${google_cloud_run_service.backend.name}\""
      duration        = "60s"
      comparison      = "COMPARISON_GT"
      threshold_value = 0.05
      
      aggregations {
        alignment_period  = "60s"
        per_series_aligner = "ALIGN_RATE"
      }
    }
  }
  
  notification_channels = [google_monitoring_notification_channel.email.name]
}

resource "google_monitoring_notification_channel" "email" {
  display_name = "Data Platform Alerts"
  type         = "email"
  
  labels = {
    email_address = var.alert_email
  }
}

# Output important values
output "backend_url" {
  value       = google_cloud_run_service.backend.status[0].url
  description = "Backend Cloud Run service URL"
}

output "database_private_ip" {
  value       = google_sql_database_instance.postgres.private_ip_address
  description = "Cloud SQL private IP address"
}

output "redis_host" {
  value       = google_redis_instance.cache.host
  description = "Redis instance host"
}

output "static_bucket_url" {
  value       = "gs://${google_storage_bucket.static.name}"
  description = "Static assets bucket URL"
}
