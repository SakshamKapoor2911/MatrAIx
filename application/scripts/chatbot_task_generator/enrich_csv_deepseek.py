import csv
import json
import os
import sys
import time
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

# Load .env
env_path = Path(r"c:\Users\Saksham Kapoor\Documents\MatrAIx\.env")
if env_path.exists():
    for line in env_path.read_text().splitlines():
        if line.strip() and not line.startswith("#") and "=" in line:
            key, val = line.split("=", 1)
            os.environ[key.strip()] = val.strip()

API_KEY = os.environ.get("DEEPSEEK_API_KEY")
if not API_KEY:
    print("Error: DEEPSEEK_API_KEY not found in .env")
    sys.exit(1)

URL = "https://api.deepseek.com/chat/completions"

SYSTEM_PROMPT = """You are an expert conversational AI dataset generator.
Your task is to take a synthetic user persona background and generate 5 specific fields to guide the synthetic user's behavior during a chatbot evaluation.

CRITICAL RULES — Follow these exactly:
1. INSTANTIATE ALL VARIABLES. Every abstract category must become a concrete named item with a property that matters for the conversation. For example, don't say "you have photos" — say "printed photos from a trip to Maine, some with sticky residue from an old album". Don't say "you have cards" — say "handwritten birthday cards from your grandmother, fragile and double-sided, so they can't be glued on one side". The chatbot must have specific details to fail on. If the background is vague, INVENT plausible specific items with properties.
2. Separate goal from behavior policy. "goal" describes ONLY what the persona wants to achieve (e.g., "Get a concrete starting plan: how to organize these three memory types, and a shortlist of supplies for your first session"). Do NOT mix behavioral rules into the goal. "behavior_constraints" describes ONLY how the persona should act during the conversation (e.g., withhold info initially, push back on generic advice, mention budget).
3. Operationalize termination. "termination_conditions" must specify explicit A/B conditions referencing the concrete variables. "success_judgment" must be a specific rubric that references the instantiated variables by name to determine if the chatbot actually helped.

Output strictly valid JSON with exactly these 5 keys (all string values, use bullet points where appropriate):
- goal: What the persona specifically wants to achieve. Pure goal, no behavioral rules.
- behavior_constraints: 3-4 bullet points detailing how the persona should act. Include "Open by describing your [concrete situation], but don't reveal your specific question until the chatbot asks a follow-up or gives generic advice." Include "If the chatbot gives a generic listicle, push back and ask how it applies to your specific [named items]." Include budget constraints if money is relevant.
- interaction_requirements: "At least two back-and-forth exchanges (4+ messages total). Each exchange should move the conversation forward."
- termination_conditions: "End the conversation when EITHER (a) [specific condition referencing concrete variables], OR (b) after 5 exchanges the chatbot has still not addressed your [specific named items/constraints]."
- success_judgment: "The chatbot helped if its advice referenced your specific [named items] (not generic tips) and you left with an actionable first step you could take."

Output ONLY the JSON object. Do not wrap it in markdown code blocks like ```json.
"""

def _sanitize_field(value) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        return "\n".join(
            f"- {item.strip('- ')}" if isinstance(item, str) and item.strip().startswith("- ")
            else f"- {item}" if isinstance(item, str)
            else str(item)
            for item in value
        )
    if not isinstance(value, str) or not value.strip():
        return str(value) if not isinstance(value, str) else value
    stripped = value.strip()
    if stripped.startswith("[") and stripped.endswith("]"):
        try:
            parsed = json.loads(stripped.replace("'", '"'))
            if isinstance(parsed, list):
                return "\n".join(f"- {item.strip('- ')}" if item.strip().startswith("- ") else f"- {item.strip()}" for item in parsed)
        except (json.JSONDecodeError, Exception):
            pass
    if stripped.startswith('["') or stripped.startswith("['"):
        try:
            import ast
            parsed = ast.literal_eval(stripped)
            if isinstance(parsed, list):
                return "\n".join(f"- {item.strip('- ')}" if item.strip().startswith("- ") else f"- {item.strip()}" for item in parsed)
        except Exception:
            pass
    return value

def call_llm(domain: str, background: str, retries=3) -> dict:
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}"
    }
    
    prompt = f"Domain: {domain}\nPersona Background: {background}\n\nGenerate the 5 JSON fields."
    
    data = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0.7
    }
    
    req = urllib.request.Request(URL, data=json.dumps(data).encode("utf-8"), headers=headers)
    
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                result = json.loads(response.read().decode("utf-8"))
                content = result["choices"][0]["message"]["content"].strip()
                # DeepSeek might still return markdown blocks despite json_object format, though json_object should enforce JSON.
                if content.startswith("```json"):
                    content = content[7:-3].strip()
                elif content.startswith("```"):
                    content = content[3:-3].strip()
                return json.loads(content)
        except Exception as e:
            if attempt == retries - 1:
                print(f"Failed after {retries} attempts for domain {domain}: {e}")
                return {}
            time.sleep(2)

def main():
    csv_path = Path(__file__).parent / "chatbot_domains_352.csv"
    if not csv_path.exists():
        print(f"File not found: {csv_path}")
        return

    # Read original data
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        fieldnames = list(reader.fieldnames)

    # Add new columns if not present
    new_cols = ["goal", "behavior_constraints", "interaction_requirements", "termination_conditions", "success_judgment"]
    for col in new_cols:
        if col not in fieldnames:
            fieldnames.append(col)

    print(f"Processing {len(rows)} tasks...")

    def process_row(idx, row):
        # Only process if missing
        if all(row.get(col, "").strip() for col in new_cols):
            return idx, row
            
        print(f"Processing {idx+1}/{len(rows)}: {row['name']}...")
        result = call_llm(row["domain"], row["persona_background"])
        if result:
            for col in new_cols:
                if col in result:
                    row[col] = _sanitize_field(result[col])
        return idx, row

    start_time = time.time()
    
    # Process in parallel
    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = {executor.submit(process_row, i, row): i for i, row in enumerate(rows)}
        for future in as_completed(futures):
            # Just iterating to catch exceptions and monitor progress
            idx, updated_row = future.result()
            rows[idx] = updated_row

    print(f"Completed processing in {time.time() - start_time:.1f}s.")
    
    # Backup original
    backup_path = csv_path.with_suffix(".csv.bak_llm")
    import shutil
    shutil.copy2(csv_path, backup_path)
    print(f"Backed up original to {backup_path.name}")
    
    # Write back
    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Successfully updated {csv_path.name}")

if __name__ == "__main__":
    main()
