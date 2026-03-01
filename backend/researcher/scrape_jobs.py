#!/usr/bin/env python3
"""
Standalone job scraper for CareerAssist.
Scrapes Indeed job listings and stores them in the Aurora database.
No dependency on openai-agents SDK.
"""

import json
import os
import re
import uuid

import boto3
import httpx
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv(override=True)

# Database config
AURORA_CLUSTER_ARN = os.getenv("AURORA_CLUSTER_ARN", "")
AURORA_SECRET_ARN = os.getenv("AURORA_SECRET_ARN", "")
DATABASE_NAME = os.getenv("DATABASE_NAME", "career")
AWS_REGION = os.getenv("DEFAULT_AWS_REGION", "us-east-1")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

SEARCH_QUERIES = [
    "software engineer",
    "data scientist",
    "machine learning engineer",
]


def get_rds_client():
    return boto3.client("rds-data", region_name=AWS_REGION)


def store_job(job: dict) -> bool:
    """Store a job in the discovered_jobs table."""
    if not AURORA_CLUSTER_ARN or not AURORA_SECRET_ARN:
        print(f"  [skip DB] {job['role_title']} at {job['company_name']}")
        return False

    rds = get_rds_client()
    job_id = str(uuid.uuid4())
    source_job_id = job.get("source_job_id") or job_id

    params = [
        {"name": "id", "value": {"stringValue": job_id}},
        {"name": "source", "value": {"stringValue": job.get("source", "indeed")}},
        {"name": "source_url", "value": {"stringValue": job.get("source_url", "")} if job.get("source_url") else {"isNull": True}},
        {"name": "source_job_id", "value": {"stringValue": source_job_id}},
        {"name": "company_name", "value": {"stringValue": job.get("company_name", "Unknown")}},
        {"name": "role_title", "value": {"stringValue": job["role_title"]}},
        {"name": "location", "value": {"stringValue": job.get("location", "")} if job.get("location") else {"isNull": True}},
        {"name": "remote_policy", "value": {"stringValue": job.get("remote_policy", "")} if job.get("remote_policy") else {"isNull": True}},
        {"name": "salary_min", "value": {"longValue": job["salary_min"]} if job.get("salary_min") else {"isNull": True}},
        {"name": "salary_max", "value": {"longValue": job["salary_max"]} if job.get("salary_max") else {"isNull": True}},
        {"name": "description_text", "value": {"stringValue": job.get("description_text", "")} if job.get("description_text") else {"isNull": True}},
        {"name": "requirements_text", "value": {"stringValue": job.get("requirements_text", "")} if job.get("requirements_text") else {"isNull": True}},
    ]

    try:
        rds.execute_statement(
            resourceArn=AURORA_CLUSTER_ARN,
            secretArn=AURORA_SECRET_ARN,
            database=DATABASE_NAME,
            sql="""INSERT INTO discovered_jobs
                   (id, source, source_url, source_job_id, company_name, role_title,
                    location, remote_policy, salary_min, salary_max,
                    description_text, requirements_text, is_active)
                   VALUES (:id::uuid, :source, :source_url, :source_job_id, :company_name,
                           :role_title, :location, :remote_policy, :salary_min, :salary_max,
                           :description_text, :requirements_text, true)
                   ON CONFLICT (source, source_job_id)
                   DO UPDATE SET
                       company_name = EXCLUDED.company_name,
                       role_title = EXCLUDED.role_title,
                       location = EXCLUDED.location,
                       salary_min = EXCLUDED.salary_min,
                       salary_max = EXCLUDED.salary_max,
                       description_text = EXCLUDED.description_text,
                       requirements_text = EXCLUDED.requirements_text,
                       is_active = true,
                       updated_at = NOW()""",
            parameters=params,
        )
        print(f"  [stored] {job['role_title']} at {job['company_name']}")
        return True
    except Exception as e:
        print(f"  [error] {job['role_title']}: {e}")
        return False


def parse_salary(salary_text: str) -> tuple[int, int]:
    """Extract min/max salary from text like '$120K - $180K a year'."""
    amounts = re.findall(r"\$?([\d,]+\.?\d*)K?", salary_text, re.IGNORECASE)
    if not amounts:
        return 0, 0

    values = []
    for a in amounts:
        val = float(a.replace(",", ""))
        # If value seems like it's in thousands (e.g., "120K")
        if val < 1000 and "k" in salary_text.lower():
            val *= 1000
        values.append(int(val))

    if len(values) >= 2:
        return min(values), max(values)
    elif len(values) == 1:
        return values[0], values[0]
    return 0, 0


def detect_remote_policy(text: str) -> str:
    """Detect remote policy from job text."""
    text_lower = text.lower()
    if "remote" in text_lower and "hybrid" not in text_lower:
        return "remote"
    if "hybrid" in text_lower:
        return "hybrid"
    if "on-site" in text_lower or "onsite" in text_lower or "in-office" in text_lower:
        return "onsite"
    return ""


def scrape_indeed(query: str, location: str = "", num_pages: int = 1) -> list[dict]:
    """Scrape Indeed search results."""
    jobs = []

    for page in range(num_pages):
        start = page * 10
        params = {"q": query, "start": start}
        if location:
            params["l"] = location

        url = "https://www.indeed.com/jobs"
        print(f"Fetching Indeed: q={query}, start={start}")

        try:
            with httpx.Client(headers=HEADERS, follow_redirects=True, timeout=30) as client:
                resp = client.get(url, params=params)
                resp.raise_for_status()
        except Exception as e:
            print(f"  [fetch error] {e}")
            continue

        soup = BeautifulSoup(resp.text, "html.parser")

        # Indeed uses various card selectors
        cards = soup.select("div.job_seen_beacon") or soup.select("div.jobsearch-ResultsList > div") or soup.select("li.css-5lfssm")

        if not cards:
            # Try finding job data in embedded JSON (Indeed often uses this)
            scripts = soup.find_all("script", type="application/ld+json")
            for script in scripts:
                try:
                    data = json.loads(script.string)
                    if isinstance(data, list):
                        for item in data:
                            if item.get("@type") == "JobPosting":
                                jobs.append(_parse_jsonld_job(item))
                    elif isinstance(data, dict) and data.get("@type") == "JobPosting":
                        jobs.append(_parse_jsonld_job(data))
                except (json.JSONDecodeError, AttributeError):
                    continue

            # Also try the mosaic provider data
            for script in soup.find_all("script"):
                if script.string and "mosaic-provider-jobcards" in (script.get("id") or ""):
                    try:
                        match = re.search(r"window\.mosaic\.providerData\[\"mosaic-provider-jobcards\"\]\s*=\s*({.*?});", script.string, re.DOTALL)
                        if match:
                            data = json.loads(match.group(1))
                            for result in data.get("metaData", {}).get("mosaicProviderJobCardsModel", {}).get("results", []):
                                jobs.append(_parse_mosaic_job(result))
                    except (json.JSONDecodeError, AttributeError):
                        continue
            continue

        for card in cards:
            job = _parse_html_card(card)
            if job and job.get("role_title"):
                jobs.append(job)

    return jobs


def _parse_jsonld_job(data: dict) -> dict:
    """Parse a JSON-LD JobPosting."""
    salary_min, salary_max = 0, 0
    salary = data.get("baseSalary", {})
    if isinstance(salary, dict):
        value = salary.get("value", {})
        if isinstance(value, dict):
            salary_min = int(value.get("minValue", 0) or 0)
            salary_max = int(value.get("maxValue", 0) or 0)

    org = data.get("hiringOrganization", {})
    company = org.get("name", "Unknown") if isinstance(org, dict) else str(org)

    location_data = data.get("jobLocation", {})
    loc = ""
    if isinstance(location_data, dict):
        address = location_data.get("address", {})
        if isinstance(address, dict):
            parts = [address.get("addressLocality", ""), address.get("addressRegion", "")]
            loc = ", ".join(p for p in parts if p)

    desc = data.get("description", "")
    # Strip HTML from description
    if "<" in desc:
        desc = BeautifulSoup(desc, "html.parser").get_text(separator="\n")

    return {
        "source": "indeed",
        "role_title": data.get("title", ""),
        "company_name": company,
        "location": loc,
        "description_text": desc[:5000],
        "salary_min": salary_min,
        "salary_max": salary_max,
        "source_url": data.get("url", ""),
        "source_job_id": data.get("identifier", {}).get("value", "") if isinstance(data.get("identifier"), dict) else "",
        "remote_policy": detect_remote_policy(f"{data.get('title', '')} {loc} {desc[:500]}"),
    }


def _parse_mosaic_job(result: dict) -> dict:
    """Parse an Indeed mosaic provider job card."""
    salary_text = result.get("formattedSalary", "") or result.get("salarySnippet", {}).get("text", "")
    salary_min, salary_max = parse_salary(salary_text)

    return {
        "source": "indeed",
        "role_title": result.get("title", ""),
        "company_name": result.get("company", "Unknown"),
        "location": result.get("formattedLocation", ""),
        "description_text": result.get("snippet", "")[:5000],
        "salary_min": salary_min,
        "salary_max": salary_max,
        "source_url": f"https://www.indeed.com/viewjob?jk={result.get('jobkey', '')}",
        "source_job_id": result.get("jobkey", ""),
        "remote_policy": detect_remote_policy(f"{result.get('title', '')} {result.get('formattedLocation', '')}"),
    }


def _parse_html_card(card) -> dict:
    """Parse an Indeed HTML job card."""
    title_el = card.select_one("h2.jobTitle a, a[data-jk]")
    title = title_el.get_text(strip=True) if title_el else ""
    job_key = ""
    if title_el:
        job_key = title_el.get("data-jk", "") or ""
        href = title_el.get("href", "")
        match = re.search(r"jk=([a-f0-9]+)", href)
        if match:
            job_key = match.group(1)

    company_el = card.select_one("span[data-testid='company-name'], span.companyName")
    company = company_el.get_text(strip=True) if company_el else "Unknown"

    location_el = card.select_one("div[data-testid='text-location'], div.companyLocation")
    location = location_el.get_text(strip=True) if location_el else ""

    salary_el = card.select_one("div.salary-snippet-container, div[data-testid='attribute_snippet_testid']")
    salary_text = salary_el.get_text(strip=True) if salary_el else ""
    salary_min, salary_max = parse_salary(salary_text)

    snippet_el = card.select_one("div.job-snippet, td.resultContent div.css-9446fg")
    snippet = snippet_el.get_text(strip=True) if snippet_el else ""

    return {
        "source": "indeed",
        "role_title": title,
        "company_name": company,
        "location": location,
        "description_text": snippet[:5000],
        "salary_min": salary_min,
        "salary_max": salary_max,
        "source_url": f"https://www.indeed.com/viewjob?jk={job_key}" if job_key else "",
        "source_job_id": job_key,
        "remote_policy": detect_remote_policy(f"{title} {location}"),
    }


def main():
    print("=" * 60)
    print("CareerAssist Job Scraper")
    print("=" * 60)

    all_jobs = []
    for query in SEARCH_QUERIES:
        print(f"\nSearching: '{query}'")
        jobs = scrape_indeed(query, num_pages=1)
        print(f"  Found {len(jobs)} jobs")
        all_jobs.extend(jobs)

    # Deduplicate by source_job_id
    seen = set()
    unique_jobs = []
    for job in all_jobs:
        key = job.get("source_job_id") or job.get("role_title", "") + job.get("company_name", "")
        if key and key not in seen:
            seen.add(key)
            unique_jobs.append(job)

    print(f"\n{len(unique_jobs)} unique jobs found across all queries")
    print("-" * 60)

    stored = 0
    for job in unique_jobs:
        if store_job(job):
            stored += 1

    print(f"\n{'=' * 60}")
    print(f"Done! Stored {stored}/{len(unique_jobs)} jobs in database")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
