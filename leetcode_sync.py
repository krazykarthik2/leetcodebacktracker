import os
import cloudscraper
from notion_client import Client
from datetime import datetime, timezone, timedelta

# --- CONFIGURATION ---
NOTION_TOKEN = os.environ.get("NOTION_TOKEN", "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")
DATABASE_ID = os.environ.get("DATABASE_ID", "341c4db880d9804680c1e847537f76ea")
LEETCODE_USERNAME = "karthikkrazy"

notion = Client(auth=NOTION_TOKEN)
scraper = cloudscraper.create_scraper()

def get_leetcode_data():
    url = "https://leetcode.com/graphql"
    query = """
    query userRecentSubmissionList($username: String!, $limit: Int!) {
        recentSubmissionList(username: $username, limit: $limit) {
            title
            titleSlug
            timestamp
            statusDisplay
        }
    }
    """
    try:
        r = scraper.post(url, json={'query': query, 'variables': {"username": LEETCODE_USERNAME, "limit": 50}}, timeout=10)
        return r.json().get('data', {}).get('recentSubmissionList', [])
    except Exception as e:
        print(f"[-] Error: {e}")
        return []

def get_problem_id(slug):
    query = """
    query questionData($titleSlug: String!) {
        question(titleSlug: $titleSlug) { frontendQuestionId }
    }
    """
    try:
        r = scraper.post("https://leetcode.com/graphql", json={'query': query, 'variables': {"titleSlug": slug}})
        return r.json()['data']['question']['frontendQuestionId']
    except:
        return "N/A"

def run_sync():
    print(f"[*] Fetching backlog for {LEETCODE_USERNAME}...")
    submissions = get_leetcode_data()
    
    # Calculate "Yesterday" in IST (UTC+5:30)
    # If running at 1:30 AM IST Tuesday, we want Monday's problems.
    now_utc = datetime.now(timezone.utc)
    ist_now = now_utc + timedelta(hours=5, minutes=30)
    yesterday_ist = ist_now - timedelta(days=1)
    
    start_of_target_day = yesterday_ist.replace(hour=0, minute=0, second=0, microsecond=0)
    end_of_target_day = start_of_target_day + timedelta(days=1)

    # Filter Accepted problems that occurred during the target day
    target_problems = []
    for s in submissions:
        ts = datetime.fromtimestamp(int(s['timestamp']), timezone.utc)
        ts_ist = ts + timedelta(hours=5, minutes=30)
        
        if s['statusDisplay'] == 'Accepted' and start_of_target_day <= ts_ist < end_of_target_day:
            target_problems.append(s)

    target_problems.sort(key=lambda x: x['timestamp'])

    if len(target_problems) <= 5:
        print(f"[!] Only {len(target_problems)} problems found for {start_of_target_day.date()}. Requirement not met.")
        return

    backlog = target_problems[5:]
    print(f"[+] Found {len(backlog)} backlog items.")

    for item in backlog:
        prob_id = get_problem_id(item['titleSlug'])
        notion.pages.create(
            parent={"database_id": DATABASE_ID},
            properties={
                "Problem Name": {"title": [{"text": {"content": item['title']}}]},
                "Problem No.": {"rich_text": [{"text": {"content": str(prob_id)}}]},
                "Status": {"select": {"name": "Backlog Cleared"}},
                "Date": {"date": {"start": start_of_target_day.strftime('%Y-%m-%d')}}
            }
        )
        print(f"[OK] Synced: {item['title']}")

if __name__ == "__main__":
    run_sync()