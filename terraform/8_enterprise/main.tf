# Part 8: Enterprise - CloudWatch Dashboards for Monitoring

terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# Data sources
data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

locals {
  name_prefix = "career"

  common_tags = {
    Project   = "career"
    Part      = "8_enterprise"
    ManagedBy = "terraform"
  }
}

# ========================================
# Bedrock & AI Model Usage Dashboard
# ========================================

resource "aws_cloudwatch_dashboard" "ai_model_usage" {
  dashboard_name = "${local.name_prefix}-ai-model-usage"

  dashboard_body = jsonencode({
    widgets = [
      # Bedrock Model Invocations
      {
        type   = "metric"
        width  = 12
        height = 6
        properties = {
          metrics = [
            ["AWS/Bedrock", "Invocations", "ModelId", var.bedrock_model_id, { stat = "Sum", label = "Model Invocations", id = "m1", color = "#1f77b4" }],
            [".", "InvocationClientErrors", ".", ".", { stat = "Sum", label = "Client Errors", id = "m2", color = "#d62728" }],
            [".", "InvocationServerErrors", ".", ".", { stat = "Sum", label = "Server Errors", id = "m3", color = "#ff7f0e" }]
          ]
          view    = "timeSeries"
          stacked = false
          region  = var.bedrock_region
          title   = "Bedrock Model Invocations (${var.bedrock_model_id})"
          period  = 300
          stat    = "Sum"
          yAxis = {
            left = {
              label     = "Count"
              showUnits = false
            }
          }
        }
      },
      # Bedrock Token Usage
      {
        type   = "metric"
        width  = 12
        height = 6
        properties = {
          metrics = [
            ["AWS/Bedrock", "InputTokenCount", "ModelId", var.bedrock_model_id, { stat = "Sum", label = "Input Tokens", id = "t1", color = "#2ca02c" }],
            [".", "OutputTokenCount", ".", ".", { stat = "Sum", label = "Output Tokens", id = "t2", color = "#9467bd" }]
          ]
          view    = "timeSeries"
          stacked = true
          region  = var.bedrock_region
          title   = "Bedrock Token Usage (${var.bedrock_model_id})"
          period  = 300
          stat    = "Sum"
          yAxis = {
            left = {
              label     = "Tokens"
              showUnits = false
            }
          }
        }
      },
      # Bedrock Latency
      {
        type   = "metric"
        width  = 12
        height = 6
        properties = {
          metrics = [
            ["AWS/Bedrock", "InvocationLatency", "ModelId", var.bedrock_model_id, { stat = "Average", label = "Average Latency", id = "l1", color = "#1f77b4" }],
            [".", ".", ".", ".", { stat = "Maximum", label = "Max Latency", id = "l2", color = "#d62728" }],
            [".", ".", ".", ".", { stat = "Minimum", label = "Min Latency", id = "l3", color = "#2ca02c" }]
          ]
          view    = "timeSeries"
          stacked = false
          region  = var.bedrock_region
          title   = "Bedrock Response Latency (${var.bedrock_model_id})"
          period  = 300
          yAxis = {
            left = {
              label     = "Latency (ms)"
              showUnits = false
            }
          }
        }
      },
      # SageMaker Endpoint Invocations
      {
        type   = "metric"
        width  = 12
        height = 6
        properties = {
          metrics = [
            [{ expression = "SEARCH(' {AWS/SageMaker,EndpointName,VariantName} MetricName=\"Invocations\" EndpointName=\"career-embedding-endpoint\" ', 'Sum')", id = "s1", label = "Invocations", color = "#1f77b4" }],
            [{ expression = "SEARCH(' {AWS/SageMaker,EndpointName,VariantName} MetricName=\"Invocation4XXErrors\" EndpointName=\"career-embedding-endpoint\" ', 'Sum')", id = "s2", label = "4XX Errors", color = "#ff7f0e" }],
            [{ expression = "SEARCH(' {AWS/SageMaker,EndpointName,VariantName} MetricName=\"Invocation5XXErrors\" EndpointName=\"career-embedding-endpoint\" ', 'Sum')", id = "s3", label = "5XX Errors", color = "#d62728" }]
          ]
          view    = "timeSeries"
          stacked = false
          region  = var.aws_region
          title   = "SageMaker Embedding Endpoint Invocations"
          period  = 300
          yAxis = {
            left = {
              label     = "Count"
              showUnits = false
            }
          }
        }
      },
      # SageMaker Model Latency
      {
        type   = "metric"
        width  = 12
        height = 6
        properties = {
          metrics = [
            [{ expression = "SEARCH(' {AWS/SageMaker,EndpointName,VariantName} MetricName=\"ModelLatency\" EndpointName=\"career-embedding-endpoint\" ', 'Average')", id = "ml1", label = "Average Latency", color = "#2ca02c" }],
            [{ expression = "SEARCH(' {AWS/SageMaker,EndpointName,VariantName} MetricName=\"ModelLatency\" EndpointName=\"career-embedding-endpoint\" ', 'Maximum')", id = "ml2", label = "Max Latency", color = "#d62728" }],
            [{ expression = "SEARCH(' {AWS/SageMaker,EndpointName,VariantName} MetricName=\"ModelLatency\" EndpointName=\"career-embedding-endpoint\" ', 'Minimum')", id = "ml3", label = "Min Latency", color = "#1f77b4" }]
          ]
          view    = "timeSeries"
          stacked = false
          region  = var.aws_region
          title   = "SageMaker Model Latency"
          period  = 300
          yAxis = {
            left = {
              label     = "Latency (μs)"
              showUnits = false
            }
          }
        }
      }
    ]
  })

}

# ========================================
# Agent Performance Dashboard
# ========================================

resource "aws_cloudwatch_dashboard" "agent_performance" {
  dashboard_name = "${local.name_prefix}-agent-performance"

  dashboard_body = jsonencode({
    widgets = [
      # Agent Execution Times
      {
        type   = "metric"
        width  = 12
        height = 6
        properties = {
          metrics = [
            ["AWS/Lambda", "Duration", "FunctionName", "career-orchestrator", { stat = "Average", label = "Orchestrator", id = "m1", color = "#1f77b4" }],
            [".", ".", ".", "career-analyzer", { stat = "Average", label = "Analyzer", id = "m2", color = "#2ca02c" }],
            [".", ".", ".", "career-charter", { stat = "Average", label = "Charter", id = "m3", color = "#ff7f0e" }],
            [".", ".", ".", "career-interviewer", { stat = "Average", label = "Interviewer", id = "m4", color = "#d62728" }],
            [".", ".", ".", "career-extractor", { stat = "Average", label = "Extractor", id = "m5", color = "#9467bd" }]
          ]
          view    = "timeSeries"
          stacked = false
          region  = var.aws_region
          title   = "Agent Execution Times"
          period  = 300
          stat    = "Average"
          yAxis = {
            left = {
              label     = "Duration (ms)"
              showUnits = false
            }
          }
        }
      },
      # Agent Error Rates
      {
        type   = "metric"
        width  = 12
        height = 6
        properties = {
          metrics = [
            ["AWS/Lambda", "Errors", "FunctionName", "career-orchestrator", { stat = "Sum", label = "Orchestrator Errors", id = "e1", color = "#1f77b4" }],
            [".", ".", ".", "career-analyzer", { stat = "Sum", label = "Analyzer Errors", id = "e2", color = "#2ca02c" }],
            [".", ".", ".", "career-charter", { stat = "Sum", label = "Charter Errors", id = "e3", color = "#ff7f0e" }],
            [".", ".", ".", "career-interviewer", { stat = "Sum", label = "Interviewer Errors", id = "e4", color = "#d62728" }],
            [".", ".", ".", "career-extractor", { stat = "Sum", label = "Extractor Errors", id = "e5", color = "#9467bd" }]
          ]
          view    = "timeSeries"
          stacked = false
          region  = var.aws_region
          title   = "Agent Error Rates"
          period  = 300
          stat    = "Sum"
          yAxis = {
            left = {
              label     = "Error Count"
              showUnits = false
            }
          }
        }
      },
      # Agent Invocations
      {
        type   = "metric"
        width  = 12
        height = 6
        properties = {
          metrics = [
            ["AWS/Lambda", "Invocations", "FunctionName", "career-orchestrator", { stat = "Sum", label = "Orchestrator", id = "i1", color = "#1f77b4" }],
            [".", ".", ".", "career-analyzer", { stat = "Sum", label = "Analyzer", id = "i2", color = "#2ca02c" }],
            [".", ".", ".", "career-charter", { stat = "Sum", label = "Charter", id = "i3", color = "#ff7f0e" }],
            [".", ".", ".", "career-interviewer", { stat = "Sum", label = "Interviewer", id = "i4", color = "#d62728" }],
            [".", ".", ".", "career-extractor", { stat = "Sum", label = "Extractor", id = "i5", color = "#9467bd" }]
          ]
          view    = "timeSeries"
          stacked = false
          region  = var.aws_region
          title   = "Agent Invocation Counts"
          period  = 300
          stat    = "Sum"
          yAxis = {
            left = {
              label     = "Invocation Count"
              showUnits = false
            }
          }
        }
      },
      # Concurrent Executions
      {
        type   = "metric"
        width  = 12
        height = 6
        properties = {
          metrics = [
            ["AWS/Lambda", "ConcurrentExecutions", "FunctionName", "career-orchestrator", { stat = "Maximum", label = "Orchestrator", id = "c1", color = "#1f77b4" }],
            [".", ".", ".", "career-analyzer", { stat = "Maximum", label = "Analyzer", id = "c2", color = "#2ca02c" }],
            [".", ".", ".", "career-charter", { stat = "Maximum", label = "Charter", id = "c3", color = "#ff7f0e" }],
            [".", ".", ".", "career-interviewer", { stat = "Maximum", label = "Interviewer", id = "c4", color = "#d62728" }],
            [".", ".", ".", "career-extractor", { stat = "Maximum", label = "Extractor", id = "c5", color = "#9467bd" }]
          ]
          view    = "timeSeries"
          stacked = false
          region  = var.aws_region
          title   = "Concurrent Executions"
          period  = 300
          stat    = "Maximum"
          yAxis = {
            left = {
              label     = "Concurrent Executions"
              showUnits = false
            }
          }
        }
      },
      # Throttles
      {
        type   = "metric"
        width  = 12
        height = 6
        properties = {
          metrics = [
            ["AWS/Lambda", "Throttles", "FunctionName", "career-orchestrator", { stat = "Sum", label = "Orchestrator Throttles", id = "t1", color = "#1f77b4" }],
            [".", ".", ".", "career-analyzer", { stat = "Sum", label = "Analyzer Throttles", id = "t2", color = "#2ca02c" }],
            [".", ".", ".", "career-charter", { stat = "Sum", label = "Charter Throttles", id = "t3", color = "#ff7f0e" }],
            [".", ".", ".", "career-interviewer", { stat = "Sum", label = "Interviewer Throttles", id = "t4", color = "#d62728" }],
            [".", ".", ".", "career-extractor", { stat = "Sum", label = "Extractor Throttles", id = "t5", color = "#9467bd" }]
          ]
          view    = "timeSeries"
          stacked = false
          region  = var.aws_region
          title   = "Agent Throttles"
          period  = 300
          stat    = "Sum"
          yAxis = {
            left = {
              label     = "Throttle Count"
              showUnits = false
            }
          }
        }
      }
    ]
  })

}
