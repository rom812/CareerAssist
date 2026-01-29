"""
Seed the vector knowledge base with career content.
This script ingests all career knowledge base documents from the data directory.
"""

import os
import json
import boto3
import uuid
import datetime
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from project root
env_path = Path(__file__).parent.parent.parent / '.env'
load_dotenv(env_path, override=True)

# Get configuration
VECTOR_BUCKET = os.getenv('VECTOR_BUCKET')
SAGEMAKER_ENDPOINT = os.getenv('SAGEMAKER_ENDPOINT', 'career-embedding-endpoint')
INDEX_NAME = 'career-knowledge'

# Initialize AWS clients
s3_vectors = boto3.client('s3vectors')
sagemaker_runtime = boto3.client('sagemaker-runtime')


def get_embedding(text: str) -> list:
    """Get embedding vector from SageMaker endpoint."""
    response = sagemaker_runtime.invoke_endpoint(
        EndpointName=SAGEMAKER_ENDPOINT,
        ContentType='application/json',
        Body=json.dumps({'inputs': text})
    )
    
    result = json.loads(response['Body'].read().decode())
    # HuggingFace returns nested array [[[embedding]]], extract the actual embedding
    if isinstance(result, list) and len(result) > 0:
        if isinstance(result[0], list) and len(result[0]) > 0:
            if isinstance(result[0][0], list):
                return result[0][0]  # Extract from [[[embedding]]]
            return result[0]  # Extract from [[embedding]]
    return result  # Return as-is if not nested


def ingest_document(text: str, metadata: dict) -> str:
    """Ingest a single document to S3 Vectors."""
    # Get embedding from SageMaker
    embedding = get_embedding(text)
    
    # Generate unique ID for the vector
    vector_id = str(uuid.uuid4())
    
    # Store in S3 Vectors
    s3_vectors.put_vectors(
        vectorBucketName=VECTOR_BUCKET,
        indexName=INDEX_NAME,
        vectors=[{
            "key": vector_id,
            "data": {"float32": embedding},
            "metadata": {
                "text": text,
                "timestamp": datetime.datetime.utcnow().isoformat(),
                **metadata
            }
        }]
    )
    
    return vector_id


def process_bullet_template(file_path: Path) -> int:
    """Process a CV bullet template file and ingest each bullet."""
    count = 0
    with open(file_path) as f:
        data = json.load(f)
    
    role_category = data.get('role_category', 'general')
    
    for bullet in data.get('bullets', []):
        text = f"CV bullet example for {role_category.replace('_', ' ').title()}: {bullet['text']}"
        metadata = {
            'type': 'cv_bullet_template',
            'role_category': role_category,
            'skill_area': bullet.get('skill_area', 'general'),
            'impact_type': bullet.get('impact_type', 'qualitative'),
            'source_file': file_path.name
        }
        try:
            doc_id = ingest_document(text, metadata)
            print(f"    ✓ Bullet: {bullet['text'][:50]}... -> {doc_id}")
            count += 1
        except Exception as e:
            print(f"    ✗ Error: {e}")
    
    return count


def process_interview_questions(file_path: Path) -> int:
    """Process an interview question file and ingest each question."""
    count = 0
    with open(file_path) as f:
        data = json.load(f)
    
    category = data.get('category', 'general')
    
    for question in data.get('questions', []):
        text = f"Interview question ({category}): {question['question']}. "
        text += f"What they're testing: {question.get('what_theyre_testing', 'Various skills')}. "
        text += f"Good answer structure: {question.get('good_answer_structure', 'Use STAR method.')}"
        
        metadata = {
            'type': 'interview_question',
            'category': category,
            'topic': question.get('topic', 'general'),
            'source_file': file_path.name
        }
        try:
            doc_id = ingest_document(text, metadata)
            print(f"    ✓ Question: {question['question'][:40]}... -> {doc_id}")
            count += 1
        except Exception as e:
            print(f"    ✗ Error: {e}")
    
    return count


def process_ats_keywords(file_path: Path) -> int:
    """Process an ATS keyword guide file and ingest it."""
    count = 0
    with open(file_path) as f:
        data = json.load(f)
    
    role = data.get('role', 'general')
    industry = data.get('industry', 'general')
    
    # Create a comprehensive text for the keywords
    must_have = ', '.join(data.get('must_have_keywords', []))
    nice_to_have = ', '.join(data.get('nice_to_have_keywords', []))
    tips = ' '.join(data.get('tips', []))
    
    text = f"ATS keyword guide for {role.replace('_', ' ').title()} in {industry}. "
    text += f"Must-have keywords: {must_have}. "
    text += f"Nice-to-have keywords: {nice_to_have}. "
    text += f"Tips: {tips}"
    
    metadata = {
        'type': 'ats_keyword_guide',
        'role': role,
        'industry': industry,
        'source_file': file_path.name
    }
    try:
        doc_id = ingest_document(text, metadata)
        print(f"    ✓ ATS Guide: {role} -> {doc_id}")
        count += 1
    except Exception as e:
        print(f"    ✗ Error: {e}")
    
    return count


def seed_knowledge_base():
    """Main function to seed all knowledge base content."""
    if not VECTOR_BUCKET:
        print("Error: VECTOR_BUCKET not set. Please run Guide 3 Step 4 to save it to .env")
        return
    
    print("=" * 60)
    print("CareerAssist Knowledge Base Seeding")
    print("=" * 60)
    print(f"Bucket: {VECTOR_BUCKET}")
    print(f"Index: {INDEX_NAME}")
    print(f"Embedding Model: {SAGEMAKER_ENDPOINT}")
    print()
    
    data_dir = Path(__file__).parent / 'data'
    total_documents = 0
    
    # Process CV bullet templates
    bullets_dir = data_dir / 'bullets'
    if bullets_dir.exists():
        print("📝 Processing CV Bullet Templates...")
        for json_file in bullets_dir.glob('*.json'):
            print(f"  File: {json_file.name}")
            count = process_bullet_template(json_file)
            total_documents += count
        print()
    
    # Process interview questions
    interviews_dir = data_dir / 'interviews'
    if interviews_dir.exists():
        print("🎤 Processing Interview Questions...")
        for json_file in interviews_dir.glob('*.json'):
            print(f"  File: {json_file.name}")
            count = process_interview_questions(json_file)
            total_documents += count
        print()
    
    # Process ATS keyword guides
    ats_dir = data_dir / 'ats'
    if ats_dir.exists():
        print("🔍 Processing ATS Keyword Guides...")
        for json_file in ats_dir.glob('*.json'):
            print(f"  File: {json_file.name}")
            count = process_ats_keywords(json_file)
            total_documents += count
        print()
    
    print("=" * 60)
    print(f"✅ Seeding complete! Ingested {total_documents} documents.")
    print("=" * 60)
    print("\n💡 You can now run test_search_s3vectors.py to search the knowledge base!")


if __name__ == "__main__":
    seed_knowledge_base()
