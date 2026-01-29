import boto3
import json
import uuid
import os
from dotenv import load_dotenv

load_dotenv()

db_client = boto3.client('rds-data', region_name='us-east-1')
sqs_client = boto3.client('sqs', region_name='us-east-1')

cluster_arn = "arn:aws:rds:us-east-1:199789641539:cluster:career-aurora-cluster"
secret_arn = "arn:aws:secretsmanager:us-east-1:199789641539:secret:career-aurora-credentials-0a049ec1-uQI1rA"
database = "career"
queue_url = "https://sqs.us-east-1.amazonaws.com/199789641539/career-analysis-jobs"

# Get data from previous job
response = db_client.execute_statement(
    resourceArn=cluster_arn,
    secretArn=secret_arn,
    database=database,
    sql="SELECT input_data FROM jobs WHERE id = '7be5fd28-4e79-4771-82c6-9066a0ad24c4'"
)
input_data_str = response['records'][0][0]['stringValue']
input_data = json.loads(input_data_str)

job_id = str(uuid.uuid4())
clerk_user_id = "user_33C0IdAcCY3XqUhNnZ6Bu3T2M6R"
user_id = "7d4ca845-39eb-4f76-b48a-d83ab392a38d"

# Create job
db_client.execute_statement(
    resourceArn=cluster_arn,
    secretArn=secret_arn,
    database=database,
    sql="INSERT INTO jobs (id, user_id, clerk_user_id, job_type, status, input_data) VALUES (:id::uuid, :user_id::uuid, :clerk_id, 'full_analysis', 'pending', :input_data::jsonb)",
    parameters=[
        {'name': 'id', 'value': {'stringValue': job_id}},
        {'name': 'user_id', 'value': {'stringValue': user_id}},
        {'name': 'clerk_id', 'value': {'stringValue': clerk_user_id}},
        {'name': 'input_data', 'value': {'stringValue': json.dumps(input_data)}}
    ]
)

# Send SQS
sqs_client.send_message(
    QueueUrl=queue_url,
    MessageBody=json.dumps({
        "job_id": job_id,
        "clerk_user_id": clerk_user_id,
        "job_type": "full_analysis"
    })
)

print(f"✅ Job triggered: {job_id}")
