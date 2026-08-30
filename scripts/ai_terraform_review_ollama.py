import json
import os
import sys
import urllib.request
import urllib.error
from pathlib import Path

PROJECT_ROOT = Path.cwd()

PLAN_JSON = PROJECT_ROOT / "plan.json"
CHECKOV_JSON = PROJECT_ROOT / "checkov-report.json"
OUTPUT_FILE = PROJECT_ROOT / "reports" / "ai-review.md"


def read_json_file(path: Path):
    if path.is_dir():
        print(f"ERROR: {path} is a directory, but it must be a JSON file.")
        print("Fix:")
        print(f"rm -rf {path}")
        print("Then regenerate Checkov JSON using:")
        print("checkov -d terraform/ec2-secure --check CKV_AWS_24,CKV_AWS_8 -o json > checkov-report.json || true")
        sys.exit(1)

    if not path.exists():
        print(f"ERROR: Missing file: {path}")
        sys.exit(1)

    try:
        with path.open("r") as file:
            return json.load(file)
    except json.JSONDecodeError as error:
        print(f"ERROR: Invalid JSON in {path}")
        print(error)
        sys.exit(1)


def summarize_plan(plan):
    changes = plan.get("resource_changes", [])

    summary = {
        "create": [],
        "update": [],
        "delete": [],
        "replace": [],
        "no_op": []
    }

    for item in changes:
        address = item.get("address", "unknown")
        actions = item.get("change", {}).get("actions", [])

        if actions == ["create"]:
            summary["create"].append(address)
        elif actions == ["update"]:
            summary["update"].append(address)
        elif actions == ["delete"]:
            summary["delete"].append(address)
        elif "delete" in actions and "create" in actions:
            summary["replace"].append(address)
        else:
            summary["no_op"].append(address)

    return summary


def summarize_checkov(checkov):
    results = checkov.get("results", {})
    failed_checks = results.get("failed_checks", [])
    passed_checks = results.get("passed_checks", [])

    failed_summary = []

    for item in failed_checks:
        failed_summary.append({
            "check_id": item.get("check_id"),
            "check_name": item.get("check_name"),
            "resource": item.get("resource"),
            "file_path": item.get("file_path")
        })

    return {
        "passed_count": len(passed_checks),
        "failed_count": len(failed_checks),
        "failed_checks": failed_summary
    }


def build_prompt(plan_summary, checkov_summary):
    return f"""
You are a senior DevSecOps engineer reviewing a Terraform deployment.

Review the Terraform plan summary and Checkov security scan.

Terraform plan summary:
{json.dumps(plan_summary, indent=2)}

Checkov summary:
{json.dumps(checkov_summary, indent=2)}

Give the result in this exact markdown format:

# AI Terraform Review

## Summary

## Terraform Change Analysis

## Checkov Findings

## Risk Score

Use a score from 1 to 10.

## Final Decision

Use only one of these:
APPROVE
APPROVE_WITH_CAUTION
REJECT

## Recommended Fixes

Keep the explanation simple for a beginner DevOps engineer.
"""


def call_ollama(prompt):
    ollama_url = os.environ.get("OLLAMA_URL")
    model = os.environ.get("OLLAMA_MODEL", "llama3.2:1b")

    if not ollama_url:
        print("ERROR: OLLAMA_URL is missing.")
        print("Example:")
        print("export OLLAMA_URL=http://172.17.0.1:11434/api/generate")
        sys.exit(1)

    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False
    }

    data = json.dumps(payload).encode("utf-8")

    request = urllib.request.Request(
        ollama_url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    try:
        with urllib.request.urlopen(request, timeout=300) as response:
            result = json.loads(response.read().decode("utf-8"))
            return result.get("response", "")
    except urllib.error.URLError as error:
        print("ERROR: Could not connect to Ollama.")
        print(f"Ollama URL used: {ollama_url}")
        print(error)
        sys.exit(1)


def main():
    plan = read_json_file(PLAN_JSON)
    checkov = read_json_file(CHECKOV_JSON)

    plan_summary = summarize_plan(plan)
    checkov_summary = summarize_checkov(checkov)

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    prompt = build_prompt(plan_summary, checkov_summary)

    review = call_ollama(prompt)

    if not review.strip():
        print("ERROR: Ollama returned empty response.")
        sys.exit(1)

    OUTPUT_FILE.write_text(review)

    print(review)
    print(f"\nAI review saved to: {OUTPUT_FILE}")

    enforce = os.environ.get("ENFORCE_AI_DECISION", "false").lower()

    if enforce == "true" and "REJECT" in review:
        print("AI decision is REJECT. Failing pipeline.")
        sys.exit(2)


if __name__ == "__main__":
    main()
