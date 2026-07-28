"""Default settings and sample challenges — single source of truth.

Used by seed.py (first-run bootstrap) and the admin reset-to-defaults route.
"""

DEFAULT_SETTINGS = {
    "portal_title": "Exam and CTF Portal - DEF CON Las Vegas - 2026",
    "portal_subtitle": "Breaking the Cloud Layer - Modern and Practical Attacks on AWS, Azure, GCP, Aliyun, Railway and Vercel",
    "registration_open": "true",
    "registration_code": "",
    "scoreboard_enabled": "false",
}

SAMPLE_CHALLENGES = [
    {
        "title": "[Sample] AWS - Enumerate S3 Buckets",
        "category": "AWS",
        "description": (
            "You have been given access to an AWS account with limited permissions. "
            "Your goal is to enumerate S3 buckets and discover sensitive data. "
            "Look for publicly accessible buckets and misconfigured permissions."
        ),
        "starting_points": (
            "Start with the AWS CLI: `aws s3 ls` and `aws s3api list-buckets`.\n"
            "Check bucket policies and ACLs.\n"
            "Try accessing buckets with common names."
        ),
        "points": 50,
        "flag": "flag{sample-aws-s3-enum}",
        "sort_order": 1,
    },
    {
        "title": "[Sample] Azure - Storage Account Misconfiguration",
        "category": "Azure",
        "description": (
            "An Azure Storage Account has been misconfigured. "
            "Your task is to identify the misconfiguration and access the container contents."
        ),
        "starting_points": (
            "Use Azure CLI: `az storage container list`.\n"
            "Check for anonymous access configurations.\n"
            "Look for Shared Access Signature (SAS) tokens."
        ),
        "points": 50,
        "flag": "flag{sample-azure-storage}",
        "sort_order": 2,
    },
    {
        "title": "[Sample] GCP - Service Account Key Exposure",
        "category": "GCP",
        "description": (
            "A service account key has been leaked in a public repository. "
            "Use the key to enumerate GCP resources and find the flag."
        ),
        "starting_points": (
            "Authenticate with `gcloud auth activate-service-account --key-file=key.json`.\n"
            "List available resources with `gcloud` commands.\n"
            "Check IAM roles and permissions."
        ),
        "points": 50,
        "flag": "flag{sample-gcp-sa-key}",
        "sort_order": 3,
    },
]
