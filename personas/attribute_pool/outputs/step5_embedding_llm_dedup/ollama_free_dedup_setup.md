# Free Ollama Dedup Setup

## 1. Install Ollama

Install Ollama from:

https://ollama.com/download

After installation, open a new PowerShell and check:

```powershell
ollama --version
```

## 2. Pull Free Local Models

Recommended:

```powershell
ollama pull nomic-embed-text
ollama pull qwen3:8b
```

Lower-memory alternative:

```powershell
ollama pull nomic-embed-text
ollama pull gemma3:4b
```

## 3. Run Embedding + LLM Dedup

From:

```powershell
cd "D:\Yilan_Fan\学习\AI Persona Project\Attributes"
```

Run a small test first:

```powershell
python embedding_llm_dedup_pipeline.py --provider ollama --run-llm --max-llm-pairs 25 --ollama-embedding-model nomic-embed-text --ollama-llm-model qwen3:8b
```

Then run a larger batch:

```powershell
python embedding_llm_dedup_pipeline.py --provider ollama --run-llm --max-llm-pairs 500 --ollama-embedding-model nomic-embed-text --ollama-llm-model qwen3:8b
```

## Outputs

- `llm_adjudicated_pairs.csv`
- `llm_confirmed_merges.csv`
- `llm_graph_edges.csv`
- `llm_review_needed.csv`
- `llm_rejected_pairs.csv`

Only rows in `llm_confirmed_merges.csv` should be merged automatically.
