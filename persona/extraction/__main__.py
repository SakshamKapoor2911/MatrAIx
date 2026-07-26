"""Command-line entry point for the treiver.

Examples::

    # regex only (offline, no API key)
    python -m persona.extraction "a retired nurse in rural Kentucky, born 1950"

    # add the Claude LLM judge over the regex candidates
    python -m persona.extraction --llm "a retired nurse in rural Kentucky"

    # read the prompt from stdin, emit JSON
    echo "young woman, expert in data science" | python -m persona.extraction --json
"""

from __future__ import annotations

import argparse
import json
import sys

from .treiver import Treiver


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m persona.extraction",
        description="Match a free-text prompt to persona attributes (regex + optional LLM judge).",
    )
    parser.add_argument(
        "prompt",
        nargs="?",
        help="the description to match; if omitted, read from stdin",
    )
    parser.add_argument(
        "--llm",
        action="store_true",
        help="run the Claude LLM judge over the regex candidates (needs anthropic + API key)",
    )
    parser.add_argument(
        "--schema",
        default=None,
        help="path to an alternative dimensions.json (defaults to the bundled schema)",
    )
    parser.add_argument(
        "--backend",
        choices=("auto", "openai", "anthropic"),
        default="auto",
        help="LLM judge backend when --llm is set (default: auto — the OpenAI "
        "endpoint if OPENAI_API_KEY is set, else the anthropic SDK)",
    )
    parser.add_argument(
        "--model",
        default=None,
        help="override the judge model id (also settable via OPENAI_MODEL)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="emit the full result as JSON instead of a table",
    )
    args = parser.parse_args(argv)

    prompt = args.prompt if args.prompt is not None else sys.stdin.read().strip()
    if not prompt:
        parser.error("no prompt given (as an argument or on stdin)")

    judge = None
    if args.llm:
        from .llm_judge import LLMJudge
        from .schema import load_schema, default_schema

        schema = load_schema(args.schema) if args.schema else default_schema()
        judge_kwargs = {"backend": args.backend}
        if args.model:
            judge_kwargs["model"] = args.model
        judge = LLMJudge(schema, **judge_kwargs)

    treiver = Treiver(schema_path=args.schema, judge=judge)
    try:
        result = treiver.match(prompt, use_llm=args.llm)
    except Exception as exc:  # no credential, gateway down, etc.
        print(f"error: LLM judge could not run ({exc})", file=sys.stderr)
        print(
            "hint: set OPENAI_API_KEY (and optionally OPENAI_BASE_URL) or "
            "ANTHROPIC_API_KEY, or drop --llm for the offline regex stage.",
            file=sys.stderr,
        )
        return 1

    if args.json:
        json.dump(result.as_dict(), sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
        return 0

    print(f"prompt: {prompt}")
    print(f"candidates: {len(result.candidate_dimension_ids)} dimension(s); "
          f"llm={'on' if result.used_llm else 'off'}")
    print(f"attributes: {len(result.attributes)}")
    for a in result.attributes:
        conf = f"{a.confidence:.2f}"
        line = f"  {a.dimension_id:<28} = {a.value!r:<20} [{a.method:<5} {conf}]"
        if a.evidence:
            line += f"  ⟵ {a.evidence!r}"
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
