#!/usr/bin/env python3
"""
Simple test for Charter agent - Application Analytics
"""

import asyncio
import json
from dotenv import load_dotenv

load_dotenv(override=True)

import sys
import os
# Add database directory to path so 'src' module can be found
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../database")))

from src import Database
from src.schemas import JobCreate
from lambda_handler import lambda_handler


def test_charter():
    """Test the charter agent with job application analytics"""

    # Create a real job in the database
    db = Database()
    job_create = JobCreate(
        clerk_user_id="test_user_001",
        job_type="application_analytics",
        request_payload={"test": True}
    )
    job_id = db.jobs.create(job_create.model_dump())
    print(f"Created test job: {job_id}")

    # Sample application tracking data for chart generation
    test_event = {
        "job_id": job_id,
        "application_data": {
            "total_applications": 25,
            "applications_by_status": {
                "saved": 5,
                "applied": 8,
                "screening": 4,
                "interview": 3,
                "offer": 1,
                "rejected": 4
            },
            "applications_by_month": [
                {"month": "2024-01", "count": 5},
                {"month": "2024-02", "count": 8},
                {"month": "2024-03", "count": 7},
                {"month": "2024-04", "count": 5}
            ],
            "applications_by_role": [
                {"role": "Software Engineer", "count": 10, "response_rate": 40},
                {"role": "Senior Engineer", "count": 8, "response_rate": 50},
                {"role": "Tech Lead", "count": 4, "response_rate": 25},
                {"role": "Staff Engineer", "count": 3, "response_rate": 33}
            ],
            "skill_gaps_frequency": [
                {"skill": "Kubernetes", "count": 8},
                {"skill": "System Design", "count": 6},
                {"skill": "Leadership", "count": 5},
                {"skill": "AWS", "count": 4},
                {"skill": "Machine Learning", "count": 3}
            ],
            "response_times_days": [3, 5, 7, 7, 10, 14, 14, 21, 28, 30]
        }
    }

    print("Testing Charter Agent - Application Analytics...")
    print("=" * 60)

    import sys

    print("About to call lambda_handler...", flush=True)
    sys.stdout.flush()
    result = lambda_handler(test_event, None)
    print("lambda_handler returned", flush=True)

    print(f"Status Code: {result['statusCode']}")

    if result["statusCode"] == 200:
        body = json.loads(result["body"])
        print(f"Success: {body.get('success', False)}")
        print(f"Message: {body.get('message', 'N/A')}")

        # Check what charts were created
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
                    color = point.get("color", "N/A")
                    if isinstance(value, (int, float)):
                        print(f"     {i+1}. {name}: {value} {color}")
                    else:
                        print(f"     {i+1}. {name}: {value}")
                if len(data_points) > 5:
                    print(f"     ... and {len(data_points) - 5} more")

        else:
            print("\n❌ No charts found in database")
    else:
        print(f"Error: {result['body']}")

    # Clean up - delete the test job
    db.jobs.delete(job_id)
    print(f"Deleted test job: {job_id}")

    print("=" * 60)


if __name__ == "__main__":
    test_charter()
