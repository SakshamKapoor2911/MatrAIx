FROM python:3.11-slim

ARG MEDICAL_ASSISTANT_REPO=https://github.com/souvikmajumder26/Multi-Agent-Medical-Assistant.git
ARG MEDICAL_ASSISTANT_REF=dee00a4df4d7142186c30bf2893406a0074faa51

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV OPENAI_MODEL=gpt-4o-mini

WORKDIR /app

RUN python - <<'PY'
import os
import shutil
import tarfile
import tempfile
import urllib.request
from pathlib import Path

repo = os.environ.get(
    "MEDICAL_ASSISTANT_REPO",
    "https://github.com/souvikmajumder26/Multi-Agent-Medical-Assistant.git",
)
ref = os.environ.get(
    "MEDICAL_ASSISTANT_REF",
    "dee00a4df4d7142186c30bf2893406a0074faa51",
)
archive_url = repo.removesuffix(".git") + "/archive/" + ref + ".tar.gz"
with tempfile.TemporaryDirectory() as tmp:
    archive = Path(tmp) / "medical.tar.gz"
    src_root = Path(tmp) / "src"
    urllib.request.urlretrieve(archive_url, archive)
    src_root.mkdir()
    with tarfile.open(archive, "r:gz") as tar:
        tar.extractall(src_root)
    extracted = next(src_root.iterdir())
    for child in extracted.iterdir():
        destination = Path("/app") / child.name
        if destination.exists():
            if destination.is_dir():
                shutil.rmtree(destination)
            else:
                destination.unlink()
        shutil.move(str(child), str(destination))
PY

RUN python - <<'PY'
import re
from pathlib import Path

config = Path("config.py")
text = config.read_text()
text = text.replace(
    "from langchain_openai import AzureOpenAIEmbeddings, AzureChatOpenAI",
    """from langchain_openai import (
    AzureChatOpenAI,
    AzureOpenAIEmbeddings,
    ChatOpenAI,
    OpenAIEmbeddings,
)""",
)
text = text.replace(
    "# Load environment variables from .env file\nload_dotenv()\n",
    """# Load environment variables from .env file
load_dotenv()


def _has_azure_chat_config():
    return all(
        os.getenv(name)
        for name in (
            "deployment_name",
            "model_name",
            "azure_endpoint",
            "openai_api_key",
            "openai_api_version",
        )
    )


def _has_azure_embedding_config():
    return all(
        os.getenv(name)
        for name in (
            "embedding_deployment_name",
            "embedding_model_name",
            "embedding_azure_endpoint",
            "embedding_openai_api_key",
            "embedding_openai_api_version",
        )
    )


def _chat_model(*, temperature):
    if _has_azure_chat_config():
        return AzureChatOpenAI(
            deployment_name=os.getenv("deployment_name"),
            model_name=os.getenv("model_name"),
            azure_endpoint=os.getenv("azure_endpoint"),
            openai_api_key=os.getenv("openai_api_key"),
            openai_api_version=os.getenv("openai_api_version"),
            temperature=temperature,
        )
    return ChatOpenAI(
        model=os.getenv("OPENAI_MODEL")
        or os.getenv("model_name")
        or "gpt-4o-mini",
        api_key=os.getenv("OPENAI_API_KEY") or os.getenv("openai_api_key"),
        temperature=temperature,
    )


def _embedding_model():
    if _has_azure_embedding_config():
        return AzureOpenAIEmbeddings(
            deployment=os.getenv("embedding_deployment_name"),
            model=os.getenv("embedding_model_name"),
            azure_endpoint=os.getenv("embedding_azure_endpoint"),
            openai_api_key=os.getenv("embedding_openai_api_key"),
            openai_api_version=os.getenv("embedding_openai_api_version"),
        )
    return OpenAIEmbeddings(
        model=os.getenv("OPENAI_EMBEDDING_MODEL")
        or os.getenv("embedding_model_name")
        or "text-embedding-3-small",
        api_key=os.getenv("OPENAI_API_KEY")
        or os.getenv("embedding_openai_api_key")
        or os.getenv("openai_api_key"),
    )
""",
)

def _replace_chat_model(match):
    temperature = re.search(
        r"temperature\s*=\s*([0-9.]+)", match.group("body")
    ).group(1)
    return "self.{} = _chat_model(temperature={})".format(
        match.group("name"), temperature
    )

text, chat_replacements = re.subn(
    r"self\.(?P<name>[A-Za-z0-9_]+) = AzureChatOpenAI\(\n(?P<body>.*?)\n\s*\)",
    _replace_chat_model,
    text,
    flags=re.S,
)
text, embedding_replacements = re.subn(
    r"self\.embedding_model = AzureOpenAIEmbeddings\(\n(?P<body>.*?)\n\s*\)",
    "self.embedding_model = _embedding_model()",
    text,
    count=1,
    flags=re.S,
)
if chat_replacements != 8 or embedding_replacements != 1:
    raise SystemExit(
        "medical upstream patch failed: chat={} embedding={}".format(
            chat_replacements, embedding_replacements
        )
    )
config.write_text(text)

agent = Path("agents/agent_decision.py")
text = agent.read_text()
for line in (
    "from agents.rag_agent import MedicalRAG\n",
    "from agents.web_search_processor_agent import WebSearchProcessorAgent\n",
    "from agents.image_analysis_agent import ImageAnalysisAgent\n",
    "import cv2\n",
    "import numpy as np\n",
):
    text = text.replace(line, "")
text = text.replace(
    "    image_analyzer = ImageAnalysisAgent(config=config)\n",
    """    image_analyzer = None

    @classmethod
    def get_image_analyzer(cls):
        if cls.image_analyzer is None:
            from agents.image_analysis_agent import ImageAnalysisAgent

            cls.image_analyzer = ImageAnalysisAgent(config=config)
        return cls.image_analyzer
""",
)
text = text.replace("AgentConfig.image_analyzer.", "AgentConfig.get_image_analyzer().")
text = text.replace(
    "        rag_agent = MedicalRAG(config)\n",
    "        from agents.rag_agent import MedicalRAG\n\n        rag_agent = MedicalRAG(config)\n",
    1,
)
text = text.replace(
    "        web_search_processor = WebSearchProcessorAgent(config)\n",
    "        from agents.web_search_processor_agent import WebSearchProcessorAgent\n\n        web_search_processor = WebSearchProcessorAgent(config)\n",
    1,
)
agent.write_text(text)
PY

RUN pip install --no-cache-dir \
    fastapi==0.115.11 \
    uvicorn==0.34.0 \
    pydantic==2.10.6 \
    python-dotenv==1.0.1 \
    python-multipart==0.0.20 \
    langchain-openai==0.3.8 \
    langchain==0.3.20 \
    langchain-community==0.3.19 \
    langgraph==0.3.9 \
    requests==2.32.3 \
    Werkzeug==3.1.3 \
    pydub==0.25.1 \
    elevenlabs==1.54.0 \
    Jinja2==3.1.6

RUN mkdir -p uploads/backend uploads/frontend uploads/skin_lesion_output uploads/speech data

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=5).read()"

CMD ["python", "app.py"]
