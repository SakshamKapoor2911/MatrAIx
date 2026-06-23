from __future__ import annotations

import json
import os
import re
import sys
import tempfile
from ast import literal_eval
from pathlib import Path
from typing import Any


APP_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = APP_ROOT.parents[1]
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

from recbot.native_contract import build_native_action
from recbot.paths import default_interecagent_root
from recbot.types import RecBotRequest, RecBotTrace, RecBotTurnResult


_AGENT_CACHE: dict[tuple[str, ...], Any] = {}


def _latest_user_message(request: RecBotRequest) -> str:
    return request.latest_user_message


def _build_chat_history(request: RecBotRequest) -> str:
    lines: list[str] = []
    for message in request.messages[:-1]:
        if message.role == "user":
            prefix = "Human"
        elif message.role == "assistant":
            prefix = "Assistent"
        else:
            prefix = "System"
        lines.append(f"{prefix}: {message.content}")
    return "\n".join(lines)


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return int(raw)


def _env_float(name: str, default: float) -> float:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return float(raw)


def _planning_recording_file() -> str:
    return os.environ.get(
        "INTERECAGENT_PLANNING_RECORDING_FILE",
        str(Path(tempfile.gettempdir()) / "matraix_interecagent_plan.jsonl"),
    )


def _resource_mode() -> str:
    return "recai_resources"


def _ranker_mode() -> str:
    return os.environ.get("INTERECAGENT_RANKER_MODE", "native")


def _agent_cache_key(domain: str) -> tuple[str, ...]:
    return (
        os.environ.get("INTERECAGENT_ROOT", ""),
        domain,
        _resource_mode(),
        os.environ.get("INTERECAGENT_CATALOG_PATH", ""),
        os.environ.get("INTERECAGENT_GENERATED_RESOURCE_DIR", ""),
        _ranker_mode(),
        os.environ.get("INTERECAGENT_ENGINE", "gpt-4o-mini"),
        os.environ.get("INTERECAGENT_BOT_TYPE", "chat"),
    )


def _force_hard_filter_selectable_sql(sql: str) -> str:
    # Normalize only the SELECT clause to ``SELECT *`` so item ids stay selectable
    # for the native filter/map tools. The WHERE clause is left intact — in
    # particular a genre filter on the categorical ``tags`` column must pass
    # through unchanged. BaseGallery loads ``tags`` as a comma-joined string, so
    # ``WHERE tags LIKE '%Strategy%'`` filters the corpus correctly (~2978 games);
    # an earlier ``tags -> display_text`` rewrite (display_text is not a real
    # column) broke genre retrieval and forced base-knowledge fallbacks.
    return re.sub(
        r"^\s*SELECT\s+.+?\s+FROM\s+",
        "SELECT * FROM ",
        sql,
        count=1,
        flags=re.IGNORECASE | re.DOTALL,
    )


class _HardFilterSelectAdapter:
    def __init__(self, tool: Any) -> None:
        self._tool = tool
        self.name = tool.name
        self.desc = (
            tool.desc
            + "\nThe SELECT clause is normalized by MatrAIx so candidate ids remain available to the native filter tool."
        )

    def run(self, inputs: str) -> str:
        return self._tool.run(_force_hard_filter_selectable_sql(inputs))


class _SeedExcludingSimilarityAdapter:
    def __init__(self, tool: Any, item_corpus: Any, candidate_buffer: Any) -> None:
        self._tool = tool
        self._item_corpus = item_corpus
        self._candidate_buffer = candidate_buffer
        self.name = tool.name
        self.desc = tool.desc

    def run(self, inputs: str) -> str:
        output = self._tool.run(inputs)
        seed_ids = self._seed_ids(inputs)
        if not seed_ids:
            return output
        candidates = self._candidate_buffer.get()
        filtered = [candidate for candidate in candidates if candidate not in set(seed_ids)]
        if filtered == candidates:
            return output
        self._candidate_buffer.push(self.name, filtered)
        suffix = f" Removed seed items {seed_ids} from similarity candidates."
        if getattr(self._candidate_buffer, "tracker", None):
            self._candidate_buffer.tracker[-1]["output"] = (
                str(self._candidate_buffer.tracker[-1].get("output", "")) + suffix
            )
        return output + suffix

    def _seed_ids(self, inputs: str) -> list[int]:
        try:
            titles = literal_eval(inputs)
        except Exception:
            try:
                titles = json.loads(inputs)
            except Exception:
                return []
        if isinstance(titles, str):
            titles = [titles]
        if not isinstance(titles, list) or not titles:
            return []
        try:
            matched_titles = self._item_corpus.fuzzy_match(titles, "title")
            info = self._item_corpus.convert_title_2_info(matched_titles, col_names="id")
            ids = info["id"]
        except Exception:
            return []
        if isinstance(ids, int):
            return [ids]
        return [int(item_id) for item_id in ids]


def _prepare_imports(interecagent_root: str, domain: str, require_resources: bool = False) -> None:
    root = Path(interecagent_root).expanduser().resolve()
    if not root.exists():
        raise RuntimeError(f"INTERECAGENT_ROOT does not exist: {root}")
    if not (root / "llm4crs").exists():
        raise RuntimeError(f"INTERECAGENT_ROOT must point to the InteRecAgent directory: {root}")
    resources_dir = root / "resources" / domain
    if require_resources and not resources_dir.exists():
        raise RuntimeError(
            f"RecAI resources for domain '{domain}' are missing at {resources_dir}. "
            "Download and unpack the ready-to-run InteRecAgent resources before running the smoke test."
        )
    os.environ["DOMAIN"] = domain
    root_path = str(root)
    sys.path[:] = [path for path in sys.path if path != root_path]
    sys.path.insert(0, root_path)


def _normalize_plan_inputs(inputs):
    """Un-wrap a tool plan that an LLM double-encoded as a JSON string.

    Well-behaved output is a raw JSON array (``[{"tool_name": ...}]``). Some
    models (notably ``gpt-4o-mini``) emit it wrapped/escaped as a JSON *string*
    (``"[{\\"tool_name\\": ...}]"``); RecAI's strict ``json.loads`` then yields a
    str, the parse fails, and the turn returns "Something went wrong". Decoding
    the outer string layer here restores a clean JSON array for RecAI's parser.
    """
    if isinstance(inputs, str):
        stripped = inputs.strip()
        if stripped[:1] in ('"', "'"):
            try:
                decoded = json.loads(stripped)
            except Exception:
                return inputs
            if isinstance(decoded, str) and decoded.strip()[:1] in ("[", "{"):
                return decoded
    return inputs


def _patch_recai_plan_parser() -> None:
    """Wrap ``ToolBox.run`` to normalize a double-encoded plan before parsing.

    Idempotent; applied lazily when the agent is built so the in-repo RecAI
    submodule needs no edits. See :func:`_normalize_plan_inputs`.
    """
    from llm4crs.agent_plan_first_openai import ToolBox

    if getattr(ToolBox.run, "_matraix_patched", False):
        return
    _orig_run = ToolBox.run

    def run(self, inputs, *args, **kwargs):
        return _orig_run(self, _normalize_plan_inputs(inputs), *args, **kwargs)

    run._matraix_patched = True
    ToolBox.run = run


#: The sentinel RecAI returns when a tool plan can't be parsed/executed.
_PLAN_ERROR_PREFIX = "Something went wrong, please retry."


def _retry_malformed_plan(call, max_attempts: int = 3):
    """Run one plan attempt via ``call()``; re-call on a parse-error response.

    gpt-4o-mini intermittently emits the tool plan as prose (or otherwise
    unparseable), which RecAI's single-shot ``plan_and_exe`` turns into a dead
    "Something went wrong" turn. Each ``call()`` re-samples the LLM, so a retry
    usually yields a valid plan. The parse failure happens before any
    candidate-buffer mutation, so retrying is side-effect-free.
    """
    resp = call()
    attempts = 1
    while (
        isinstance(resp, str)
        and resp.startswith(_PLAN_ERROR_PREFIX)
        and attempts < max_attempts
    ):
        attempts += 1
        resp = call()
    return resp


def _patch_recai_plan_retry() -> None:
    """Make ``CRSAgentPlanFirstOpenAI.plan_and_exe`` retry a malformed plan.

    Idempotent; applied lazily at agent build so the recai submodule stays
    pristine. See :func:`_retry_malformed_plan`.
    """
    from llm4crs.agent_plan_first_openai import CRSAgentPlanFirstOpenAI

    if getattr(CRSAgentPlanFirstOpenAI.plan_and_exe, "_matraix_retry", False):
        return
    _orig_plan_and_exe = CRSAgentPlanFirstOpenAI.plan_and_exe

    def plan_and_exe(self, prompt, prompt_map):
        return _retry_malformed_plan(lambda: _orig_plan_and_exe(self, prompt, prompt_map))

    plan_and_exe._matraix_retry = True
    CRSAgentPlanFirstOpenAI.plan_and_exe = plan_and_exe


def _build_interecagent(domain: str):
    from llm4crs.agent_plan_first_openai import CRSAgentPlanFirstOpenAI
    from llm4crs.buffer import CandidateBuffer
    from llm4crs.corups import BaseGallery
    from llm4crs.mapper import MapTool
    from llm4crs.prompt import (
        CANDIDATE_STORE_TOOL_DESC,
        HARD_FILTER_TOOL_DESC,
        LOOK_UP_TOOL_DESC,
        MAP_TOOL_DESC,
        RANKING_TOOL_DESC,
        SOFT_FILTER_TOOL_DESC,
        TOOL_NAMES,
    )
    from llm4crs.query import QueryTool
    from llm4crs.retrieval import SQLSearchTool, SimilarItemTool
    from llm4crs.utils import FuncToolWrapper

    # Make the vendored RecAI planner tolerant of a double-encoded tool plan,
    # and retry a malformed (e.g. prose) plan instead of failing the turn
    # (kept here, in our code, so the recai submodule stays pristine).
    _patch_recai_plan_parser()
    _patch_recai_plan_retry()

    resource_mode = _resource_mode()
    if resource_mode == "recai_resources":
        # environ_variables materializes ABSOLUTE per-domain resource paths from
        # os.environ['DOMAIN'] at IMPORT TIME, and Python caches the module in
        # sys.modules. DOMAIN is already set (in _prepare_imports) before we get
        # here; drop the cached module so a second domain in the same process
        # re-imports against the current DOMAIN instead of reusing the first
        # domain's item table / similarity matrix / checkpoint.
        sys.modules.pop("llm4crs.environ_variables", None)
        from llm4crs.environ_variables import (
            CATEGORICAL_COLS,
            GAME_INFO_FILE,
            ITEM_SIM_FILE,
            MODEL_CKPT_FILE,
            TABLE_COL_DESC_FILE,
            USE_COLS,
        )
    else:
        raise RuntimeError(
            "INTERECAGENT_RESOURCE_MODE must be 'recai_resources'"
        )

    domain_map = {"item": domain, "Item": domain.capitalize(), "ITEM": domain.upper()}
    tool_names = {key: value.format(**domain_map) for key, value in TOOL_NAMES.items()}
    max_candidate_num = _env_int("INTERECAGENT_MAX_CANDIDATE_NUM", 1000)

    item_corpus = BaseGallery(
        GAME_INFO_FILE,
        TABLE_COL_DESC_FILE,
        f"{domain}_information",
        columns=USE_COLS,
        fuzzy_cols=["title"] + CATEGORICAL_COLS,
        categorical_cols=CATEGORICAL_COLS,
    )
    candidate_buffer = CandidateBuffer(
        item_corpus,
        num_limit=max_candidate_num,
    )
    similarity_tool = SimilarItemTool(
        name=tool_names["SoftFilterTool"],
        desc=SOFT_FILTER_TOOL_DESC.format(**domain_map),
        item_sim_path=ITEM_SIM_FILE,
        item_corups=item_corpus,
        buffer=candidate_buffer,
        top_ratio=_env_float("INTERECAGENT_SIMILAR_RATIO", 0.05),
    )

    tools = {
        "BufferStoreTool": FuncToolWrapper(
            func=candidate_buffer.init_candidates,
            name=tool_names["BufferStoreTool"],
            desc=CANDIDATE_STORE_TOOL_DESC.format(**domain_map),
        ),
        "LookUpTool": QueryTool(
            name=tool_names["LookUpTool"],
            desc=LOOK_UP_TOOL_DESC.format(**domain_map),
            item_corups=item_corpus,
            buffer=candidate_buffer,
        ),
        "HardFilterTool": _HardFilterSelectAdapter(
            SQLSearchTool(
                name=tool_names["HardFilterTool"],
                desc=HARD_FILTER_TOOL_DESC.format(**domain_map),
                item_corups=item_corpus,
                buffer=candidate_buffer,
                max_candidates_num=max_candidate_num,
            )
        ),
        "SoftFilterTool": _SeedExcludingSimilarityAdapter(
            similarity_tool,
            item_corpus,
            candidate_buffer,
        ),
        "MapTool": MapTool(
            name=tool_names["MapTool"],
            desc=MAP_TOOL_DESC.format(**domain_map),
            item_corups=item_corpus,
            buffer=candidate_buffer,
        ),
    }
    map_tool = tools.pop("MapTool")
    ranker_mode = _ranker_mode()
    if ranker_mode == "native":
        from llm4crs.ranking import RecModelTool

        tools["RankingTool"] = RecModelTool(
            name=tool_names["RankingTool"],
            desc=RANKING_TOOL_DESC.format(**domain_map),
            model_fpath=MODEL_CKPT_FILE,
            item_corups=item_corpus,
            buffer=candidate_buffer,
            rec_num=_env_int("INTERECAGENT_RANK_NUM", 100),
        )
    else:
        raise RuntimeError(
            "INTERECAGENT_RANKER_MODE must be native"
        )
    tools["MapTool"] = map_tool
    agent = CRSAgentPlanFirstOpenAI(
        domain,
        tools,
        candidate_buffer,
        item_corpus,
        os.environ.get("INTERECAGENT_ENGINE", "gpt-4o-mini"),
        os.environ.get("INTERECAGENT_BOT_TYPE", "chat"),
        max_tokens=_env_int("INTERECAGENT_MAX_OUTPUT_TOKENS", 1024),
        enable_shorten=bool(_env_int("INTERECAGENT_ENABLE_SHORTEN", 0)),
        demo_mode=os.environ.get("INTERECAGENT_DEMO_MODE", "zero"),
        demo_dir_or_file=os.environ.get("INTERECAGENT_DEMO_DIR_OR_FILE"),
        num_demos=_env_int("INTERECAGENT_NUM_DEMOS", 3),
        critic=None,
        reflection_limits=_env_int("INTERECAGENT_REFLECTION_LIMITS", 3),
        planning_recording_file=_planning_recording_file(),
        verbose=bool(_env_int("INTERECAGENT_VERBOSE", 0)),
        reply_style=os.environ.get("INTERECAGENT_REPLY_STYLE", "detailed"),
        enable_summarize=_env_int("INTERECAGENT_ENABLE_SUMMARIZE", 1),
    )
    agent.init_agent()
    agent.set_mode(os.environ.get("INTERECAGENT_MODE", "accuracy"))
    return agent


def _last_recorded_plan(agent: Any) -> str | None:
    record_cache = getattr(agent, "_plan_record_cache", {})
    trajectory = record_cache.get("traj", []) if isinstance(record_cache, dict) else []
    for entry in reversed(trajectory):
        if isinstance(entry, dict) and entry.get("role") == "plan":
            return entry.get("content")
    return None


def _recommended_item_ids(agent: Any, start: int = 0) -> list[str]:
    candidate_buffer = getattr(agent, "candidate_buffer", None)
    tracker = getattr(candidate_buffer, "tracker", [])
    item_corpus = getattr(agent, "item_corups", None)
    if not isinstance(tracker, list) or item_corpus is None:
        return []
    # Only consider tracker entries appended during THIS turn (>= start). The
    # tracker spans the whole cross-turn conversation; scanning all of it would
    # re-return a previous turn's Map output on a turn that only asks a
    # clarifying question (no Map executed). If this turn ran no Map, return [].
    for entry in reversed(tracker[start:]):
        if not isinstance(entry, dict):
            continue
        tool_name = str(entry.get("tool", ""))
        if "map" not in tool_name.lower():
            continue
        output = str(entry.get("output", ""))
        marker = "Here are recommendations:"
        if marker in output:
            output = output.split(marker, 1)[1]
        titles = [title.strip() for title in output.split(";") if title.strip()]
        if not titles:
            continue
        # Resolve recommended titles to ids (recai_resources mode); fall back across id columns.
        for id_col in ("external_id", "id"):
            try:
                info = item_corpus.convert_title_2_info(titles, col_names=id_col)
                ids = info[id_col]
                if isinstance(ids, (str, int)):
                    return [str(ids)]
                return [str(item_id) for item_id in ids]
            except Exception:
                continue
        return []
    return []


def _recommended_items_with_titles(agent: Any, item_ids: list[str]) -> list[dict]:
    item_corpus = getattr(agent, "item_corups", None)
    items: list[dict] = []
    for raw_id in item_ids:
        title = None
        if item_corpus is not None:
            for key in (raw_id, _as_int_or_none(raw_id)):
                if key is None:
                    continue
                try:
                    info = item_corpus.convert_id_2_info([key], col_names="title")
                    titles = info["title"] if isinstance(info, dict) else None
                    if titles:
                        title = titles[0] if isinstance(titles, (list, tuple)) else titles
                        break
                except Exception:
                    continue
        items.append({"id": str(raw_id), "title": title})
    return items


def _as_int_or_none(value: Any):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _raw_tool_outputs(agent: Any) -> Any:
    candidate_buffer = getattr(agent, "candidate_buffer", None)
    tracker = getattr(candidate_buffer, "tracker", None)
    if tracker:
        return tracker
    return getattr(candidate_buffer, "track_info", None)


def _repair_empty_tool_plan_response(response: str, native_action: Any, domain: str) -> str:
    if (
        response.startswith("Something went wrong, please retry.")
        and isinstance(getattr(native_action, "raw_tool_plan", None), list)
        and len(native_action.raw_tool_plan) == 0
    ):
        noun = domain.replace("_", " ")
        return (
            f"What kind of {noun} are you looking for? "
            "Tell me your preferences, constraints, or an example you liked."
        )
    return response


def run_turn(request: RecBotRequest) -> RecBotTurnResult:
    interecagent_root = os.environ.get("INTERECAGENT_ROOT") or str(default_interecagent_root())

    domain = os.environ.get("INTERECAGENT_DOMAIN", request.metadata.get("domain", "movie"))
    _prepare_imports(
        interecagent_root,
        domain,
        require_resources=True,
    )
    if os.environ.get("INTERECAGENT_CACHE_AGENT", "0") == "0":
        agent = _build_interecagent(domain)
    else:
        cache_key = _agent_cache_key(domain)
        agent = _AGENT_CACHE.get(cache_key)
        if agent is None:
            agent = _build_interecagent(domain)
            _AGENT_CACHE[cache_key] = agent

    user_message = _latest_user_message(request)
    os.environ["MATRAIX_CURRENT_USER_REQUEST"] = user_message
    # Mark where this turn's tracker entries begin so we only read back THIS
    # turn's Map output (the tracker is cross-turn; see _recommended_item_ids).
    tracker_start = len(
        getattr(getattr(agent, "candidate_buffer", None), "tracker", []) or []
    )
    response = agent.run({"input": user_message}, chat_history=_build_chat_history(request))
    raw_plan = _last_recorded_plan(agent)
    native_raw = raw_plan if raw_plan else f"Final Answer: {response}"
    native_action = build_native_action(native_raw)
    response = _repair_empty_tool_plan_response(response, native_action, domain)
    raw_tool_plan = native_action.raw_tool_plan if isinstance(native_action.raw_tool_plan, list) else []
    recommended_item_ids = _recommended_item_ids(agent, start=tracker_start)
    trace = RecBotTrace(
        raw_tool_plan=raw_tool_plan,
        raw_tool_outputs=_raw_tool_outputs(agent),
        recommended_item_ids=recommended_item_ids,
        recommended_items=_recommended_items_with_titles(agent, recommended_item_ids),
    )
    return RecBotTurnResult(
        backend="interecagent",
        conversation_id=request.conversation_id,
        turn_id=request.turn_id,
        user_message=user_message,
        assistant_message=response,
        native_action=native_action,
        trace=trace,
    )
