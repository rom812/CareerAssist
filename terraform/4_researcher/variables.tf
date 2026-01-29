variable "aws_region" {
  description = "AWS region for resources"
  type        = string
}

variable "openai_api_key" {
  description = "OpenAI API key for the researcher agent"
  type        = string
  sensitive   = true
}

variable "career_api_endpoint" {
  description = "Career API endpoint from Part 3"
  type        = string
}

variable "career_api_key" {
  description = "Career API key from Part 3"
  type        = string
  sensitive   = true
}

variable "scheduler_enabled" {
  description = "Enable automated research scheduler"
  type        = bool
  default     = false
}

# Database variables for discovered jobs storage
variable "aurora_cluster_arn" {
  description = "Aurora cluster ARN for discovered jobs storage"
  type        = string
  default     = ""
}

variable "aurora_secret_arn" {
  description = "Aurora secret ARN for database authentication"
  type        = string
  default     = ""
}

variable "database_name" {
  description = "Aurora database name"
  type        = string
  default     = "career"
}