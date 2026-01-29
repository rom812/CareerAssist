variable "aws_region" {
  description = "AWS region for deployment"
  type        = string
  default     = "us-east-1"
}

# Clerk validation happens in Lambda, not at API Gateway level
variable "clerk_jwks_url" {
  description = "Clerk JWKS URL for JWT validation in Lambda"
  type        = string
}

variable "clerk_issuer" {
  description = "Clerk issuer URL (kept for Lambda environment)"
  type        = string
  default     = ""  # Not actually used but kept for backwards compatibility
}

# Database configuration from Part 5
variable "aurora_cluster_arn" {
  description = "Aurora cluster ARN from Part 5"
  type        = string
}

variable "aurora_secret_arn" {
  description = "Aurora secret ARN from Part 5"
  type        = string
}

# SQS configuration from Part 6
variable "sqs_queue_url" {
  description = "SQS queue URL from Part 6"
  type        = string
}