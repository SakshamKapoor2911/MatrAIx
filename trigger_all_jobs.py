import urllib.request
import json

url = "http://127.0.0.1:8765/api/harbor/jobs"
headers = {"Content-Type": "application/json"}

tasks = [
    {
        "taskPath": "application/tasks/meal-planning-nutrition_chatbot",
        "sampleSize": 10,
        "seed": 42,
        "nConcurrentTrials": 2,
        "personaModel": "dashscope/deepseek-v4-pro"
    },
    {
        "taskPath": "application/tasks/chat_openbb",
        "sampleSize": 10,
        "seed": 42,
        "nConcurrentTrials": 2,
        "personaModel": "dashscope/deepseek-v4-pro"
    },
    {
        "taskPath": "application/tasks/web-playwright-mit-ocw-course-choice",
        "sampleSize": 10,
        "seed": 42,
        "nConcurrentTrials": 2,
        "personaModel": "dashscope/deepseek-v4-pro"
    },
    {
        "taskPath": "application/tasks/web-playwright-books-to-scrape-book-choice",
        "sampleSize": 5,
        "seed": 42,
        "nConcurrentTrials": 2,
        "personaModel": "dashscope/deepseek-v4-pro"
    },
    {
        "taskPath": "application/tasks/web-playwright-wikipedia-article-find",
        "sampleSize": 5,
        "seed": 42,
        "nConcurrentTrials": 2,
        "personaModel": "dashscope/deepseek-v4-pro"
    },
    {
        "taskPath": "application/tasks/web-playwright-mdn-web-docs-doc-find",
        "sampleSize": 5,
        "seed": 42,
        "nConcurrentTrials": 2,
        "personaModel": "dashscope/deepseek-v4-pro"
    },
    {
        "taskPath": "application/tasks/web-playwright-github-pricing-plan-compare",
        "sampleSize": 5,
        "seed": 42,
        "nConcurrentTrials": 2,
        "personaModel": "dashscope/deepseek-v4-pro"
    },
    {
        "taskPath": "application/tasks/web-playwright-hacker-news-story-choice",
        "sampleSize": 5,
        "seed": 42,
        "nConcurrentTrials": 2,
        "personaModel": "dashscope/deepseek-v4-pro"
    },
    {
        "taskPath": "application/tasks/web-playwright-arxiv-paper-choice",
        "sampleSize": 5,
        "seed": 42,
        "nConcurrentTrials": 2,
        "personaModel": "dashscope/deepseek-v4-pro"
    },
    {
        "taskPath": "application/tasks/web-playwright-letterboxd-movie-choice",
        "sampleSize": 5,
        "seed": 42,
        "nConcurrentTrials": 2,
        "personaModel": "dashscope/deepseek-v4-pro"
    },
    {
        "taskPath": "application/tasks/web-playwright-goodreads-book-choice",
        "sampleSize": 5,
        "seed": 42,
        "nConcurrentTrials": 2,
        "personaModel": "dashscope/deepseek-v4-pro"
    },
    {
        "taskPath": "application/tasks/web-playwright-national-park-service-park-compare",
        "sampleSize": 5,
        "seed": 42,
        "nConcurrentTrials": 2,
        "personaModel": "dashscope/deepseek-v4-pro"
    },
    {
        "taskPath": "application/tasks/web-playwright-boardgamegeek-game-choice",
        "sampleSize": 5,
        "seed": 42,
        "nConcurrentTrials": 2,
        "personaModel": "dashscope/deepseek-v4-pro"
    }
]

for t in tasks:
    req = urllib.request.Request(url, data=json.dumps(t).encode("utf-8"), headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            print(f"Triggered {t['taskPath']} -> Job: {data.get('jobName')}")
    except Exception as e:
        print(f"Error triggering {t['taskPath']}: {e}")
        if hasattr(e, "read"):
            print("Response:", e.read().decode("utf-8"))
