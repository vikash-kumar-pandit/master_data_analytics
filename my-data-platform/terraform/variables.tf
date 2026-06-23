# Terraform Variables
# Save as: terraform/variables.tf

variable "project_id" {
  description = "GCP Project ID"
  type        = string
}

variable "region" {
  description = "GCP Region"
  type        = string
  default     = "us-central1"
}

variable "environment" {
  description = "Environment (development, staging, production)"
  type        = string
  default     = "development"
}

variable "db_password" {
  description = "PostgreSQL database password"
  type        = string
  sensitive   = true
}

variable "openai_api_key" {
  description = "OpenAI API key for LLM features"
  type        = string
  sensitive   = true
  default     = ""
}

variable "frontend_domain" {
  description = "Frontend domain for CORS"
  type        = string
}

variable "alert_email" {
  description = "Email for monitoring alerts"
  type        = string
}

# Terraform outputs
# Save as: terraform/outputs.tf

output "backend_url" {
  value       = google_cloud_run_service.backend.status[0].url
  description = "Backend API URL"
}

output "frontend_static_bucket" {
  value       = google_storage_bucket.static.name
  description = "Frontend static assets bucket"
}

output "database_connection_name" {
  value       = google_sql_database_instance.postgres.connection_name
  description = "Cloud SQL instance connection name"
}

output "redis_host_port" {
  value       = "${google_redis_instance.cache.host}:${google_redis_instance.cache.port}"
  description = "Redis connection string"
}

# Terraform locals (shared variables)
# Save as: terraform/locals.tf

locals {
  environment_prefix = var.environment == "production" ? "prod" : "dev"
  
  common_labels = {
    environment = var.environment
    managed_by  = "terraform"
    project     = "data-platform"
  }
  
  backup_retention_days = var.environment == "production" ? 90 : 7
}
