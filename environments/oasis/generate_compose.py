# generate_compose.py — Generate docker-compose.yaml for N agents dynamically.
# Usage: python environments/oasis/generate_compose.py --agents 20 --steps 50

from __future__ import annotations

import argparse
from pathlib import Path


def generate(num_agents: int = 20, num_steps: int = 50, llm_model: str = "Qwen/Qwen3-8B", output_path: str = "environments/oasis/docker-compose.generated.yaml"):
    services = []

    services.append("""  platform:
    build:
      context: ../..
      dockerfile: environments/oasis/platform/Dockerfile
    ports:
      - "8000:8000"
    volumes:
      - ./output:/app/output
    environment:
      - DB_PATH=/app/output/simulation.db
      - RECSYS_TYPE=random
      - MAX_REC_POSTS=50
      - PORT=8000
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 5s
      timeout: 3s
      retries: 10""")

    for i in range(1, num_agents + 1):
        services.append(f"""  agent-{i:02d}:
    build:
      context: ../..
      dockerfile: environments/oasis/agents/Dockerfile
    environment:
      - PLATFORM_URL=http://platform:8000
      - PERSONA_PATH=personas/Jun20_1k_persona_description/ID{i:04d}.yaml
      - LLM_BASE_URL=${{LLM_BASE_URL:-http://host.docker.internal:8002/v1}}
      - LLM_MODEL=${{LLM_MODEL:-{llm_model}}}
      - LLM_API_KEY=${{LLM_API_KEY:-no-key}}
      - NUM_STEPS={num_steps}
      - AGENT_ID={i-1}
    depends_on:
      platform:
        condition: service_healthy""")

    services.append("""  dashboard:
    build:
      context: ../..
      dockerfile: environments/oasis/gui/Dockerfile
    ports:
      - "3000:3000"
    volumes:
      - ./output:/app/output
    environment:
      - DB_PATH=/app/output/simulation.db
      - PORT=3000
    depends_on:
      platform:
        condition: service_healthy""")

    content = "services:\n" + "\n\n".join(services) + "\n"

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    Path(output_path).write_text(content)
    print(f"Generated {output_path}: {num_agents} agents, {num_steps} steps, model={llm_model}")
    print(f"  Platform: port 8000")
    print(f"  Dashboard: port 3000")
    print(f"  Agents: {num_agents} containers")
    print(f"\nTo run:")
    print(f"  docker compose -f {output_path} up --build")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--agents", type=int, default=20)
    parser.add_argument("--steps", type=int, default=50)
    parser.add_argument("--model", default="Qwen/Qwen3-8B")
    parser.add_argument("--output", default="environments/oasis/docker-compose.generated.yaml")
    args = parser.parse_args()
    generate(args.agents, args.steps, args.model, args.output)
