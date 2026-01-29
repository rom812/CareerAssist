#!/usr/bin/env python3
"""
Full test for Charter agent via Lambda
Tests application analytics and chart generation for CareerAssist
"""

import json
import boto3
import time
from dotenv import load_dotenv

from src import Database
from src.schemas import JobCreate

load_dotenv(override=True)


def test_charter_lambda():
    """Test the Charter agent via Lambda invocation"""

    db = Database()
    lambda_client = boto3.client("lambda")

    # Create test job for application analytics
    test_user_id = "test_user_001"

    job_create = JobCreate(
        clerk_user_id=test_user_id,
        job_type="get_analytics",
        request_payload={"analysis_type": "application_analytics", "test": True},
    )
    job_id = db.jobs.create(job_create.model_dump())

    # Prepare analytics data
    analytics_data = {
        "user_id": test_user_id,
        "job_id": job_id,
    }

    print(f"Testing Charter Lambda with job {job_id}")
    print("=" * 60)

    # Invoke Lambda
    try:
        response = lambda_client.invoke(
            FunctionName="career-charter",
            InvocationType="RequestResponse",
            Payload=json.dumps({"job_id": job_id, "analytics_data": analytics_data}),
        )

        result = json.loads(response["Payload"].read())
        print(f"Lambda Response: {json.dumps(result, indent=2)}")

        # Check database for results
        time.sleep(2)  # Give it a moment
        job = db.jobs.find_by_id(job_id)

        if job and job.get("charts_payload"):
            print(f"\n📊 Charts Created ({len(job['charts_payload'])} total):")
            print("=" * 50)
            for chart_key, chart_data in job["charts_payload"].items():
                print(f"\n🎯 Chart: {chart_key}")
                print(f"   Title: {chart_data.get('title', 'N/A')}")
                print(f"   Type: {chart_data.get('type', 'N/A')}")
                print(f"   Description: {chart_data.get('description', 'N/A')}")

                data_points = chart_data.get("data", [])
                print(f"   Data Points ({len(data_points)}):")
                for i, point in enumerate(data_points[:5]):  # Show first 5
                    name = point.get("name", "N/A")
                    value = point.get("value", 0)
                    print(f"     {i+1}. {name}: {value}")

        else:
            print("\n❌ No charts found in database")

    except Exception as e:
        print(f"Error invoking Lambda: {e}")

    print("=" * 60)


if __name__ == "__main__":
    test_charter_lambda()
