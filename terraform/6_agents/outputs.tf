output "sqs_queue_url" {
  description = "URL of the SQS queue for job submission"
  value       = aws_sqs_queue.analysis_jobs.url
}

output "sqs_queue_arn" {
  description = "ARN of the SQS queue"
  value       = aws_sqs_queue.analysis_jobs.arn
}

output "lambda_functions" {
  description = "Names of deployed Lambda functions"
  value = {
    orchestrator = aws_lambda_function.orchestrator.function_name
    extractor    = aws_lambda_function.extractor.function_name
    analyzer     = aws_lambda_function.analyzer.function_name
    charter      = aws_lambda_function.charter.function_name
    interviewer  = aws_lambda_function.interviewer.function_name
  }
}

output "setup_instructions" {
  description = "Instructions for testing the agents"
  value = <<-EOT
    
    ✅ CareerAssist Agent infrastructure deployed successfully!
    
    Lambda Functions:
    - Orchestrator: ${aws_lambda_function.orchestrator.function_name}
    - Extractor: ${aws_lambda_function.extractor.function_name}
    - Analyzer: ${aws_lambda_function.analyzer.function_name}
    - Charter: ${aws_lambda_function.charter.function_name}
    - Interviewer: ${aws_lambda_function.interviewer.function_name}
    
    SQS Queue: ${aws_sqs_queue.analysis_jobs.name}
    
    To test the system:
    1. First, package and deploy each agent's code:
       cd backend/orchestrator && uv run package_docker.py --deploy
       cd backend/extractor && uv run package_docker.py --deploy
       cd backend/analyzer && uv run package_docker.py --deploy
       cd backend/charter && uv run package_docker.py --deploy
       cd backend/interviewer && uv run package_docker.py --deploy
    
    2. Run the full integration test:
       cd backend/orchestrator
       uv run run_full_test.py
    
    3. Monitor progress in CloudWatch Logs:
       - /aws/lambda/career-orchestrator
       - /aws/lambda/career-extractor
       - /aws/lambda/career-analyzer
       - /aws/lambda/career-charter
       - /aws/lambda/career-interviewer
    
    Bedrock Model: ${var.bedrock_model_id}
    Region: ${var.bedrock_region}
  EOT
}