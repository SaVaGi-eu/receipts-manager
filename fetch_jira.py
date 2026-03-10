@ -0,0 +1,40 @@
import os

from dotenv import load_dotenv
from jira import JIRA

load_dotenv()

JIRA_URL = "https://savagi.atlassian.net"
JIRA_EMAIL = "vasileios@savagi.eu"
JIRA_API_TOKEN = os.environ.get("JIRA_API_TOKEN")
PROJECT_KEY = "RM"
OUTPUT_DIR = ".continue/jira"

if not JIRA_API_TOKEN:
    raise ValueError("JIRA_API_TOKEN is not set. Check your .env file.")
def fetch_issues():
    jira = JIRA(server=JIRA_URL, basic_auth=(JIRA_EMAIL, JIRA_API_TOKEN))
    issues = jira.search_issues(
        f'project={PROJECT_KEY} AND  status IN ("Selected for Development", "In Progress")',
        maxResults=20
    )
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    for issue in issues:
        filename = f"{OUTPUT_DIR}/{issue.key}.md"
        content = f"""# {issue.key}: {issue.fields.summary}

**Status**: {issue.fields.status.name}
**Priority**: {issue.fields.priority.name}
**Updated**: {issue.fields.updated}

## Description
{issue.fields.description or 'No description provided.'}
"""
        with open(filename, "w") as f:
            f.write(content)
        print(f"✅ Saved {issue.key}")
    print(f"\n✅ Done. {len(issues)} issues saved to {OUTPUT_DIR}/")

if __name__ == "__main__":
    fetch_issues()
