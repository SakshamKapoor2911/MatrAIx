#!/usr/bin/env python3
"""Derive clean text, sections, and chunks from raw Wikipedia person pages."""

from __future__ import annotations

import argparse
import concurrent.futures
import gzip
import html
import json
import os
from pathlib import Path
import re
import sys
import time

try:
    import mwparserfromhell  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    mwparserfromhell = None


HEADING_RE = re.compile(r"^(={2,6})\s*(.*?)\s*\1\s*$", re.MULTILINE)
COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
REF_BLOCK_RE = re.compile(r"<ref\b[^>/]*?>.*?</ref>", re.IGNORECASE | re.DOTALL)
REF_SELF_CLOSING_RE = re.compile(r"<ref\b[^>]*/\s*>", re.IGNORECASE)
REF_LINE_RE = re.compile(r"<\s*/?\s*ref\b[^>\n]*(?:>|$)", re.IGNORECASE | re.MULTILINE)
HTML_TAG_RE = re.compile(r"<[^>]+>")
FILE_LINK_RE = re.compile(r"\[\[(?:File|Image):([^\]|]+)", re.IGNORECASE)
CATEGORY_LINK_RE = re.compile(r"\[\[Category:[^\]]+\]\]", re.IGNORECASE)
WIKI_LINK_WITH_LABEL_RE = re.compile(r"\[\[([^|\]]+)\|([^\]]+)\]\]")
WIKI_LINK_RE = re.compile(r"\[\[([^\]]+)\]\]")
MALFORMED_WIKI_LINK_WITH_LABEL_RE = re.compile(r"\[\[[^\]\n|]+\|([^\[\]\n]*)(?=\[\[|\]\]|\n|$)")
MALFORMED_WIKI_LINK_RE = re.compile(r"\[\[([^\[\]\n|]*)(?=\[\[|\]\]|\n|$)")
EXTERNAL_LINK_WITH_LABEL_RE = re.compile(r"\[(?:https?|ftp)://[^\s\]]+\s+([^\]]+)\]")
BARE_EXTERNAL_LINK_RE = re.compile(r"\[(?:https?|ftp)://[^\]]+\]")
DASH_TEMPLATE_RE = re.compile(r"\{\{\s*(?:snd|spaced ndash|spaced en dash|spaced dash)\s*\}\}", re.IGNORECASE)
ENDASH_TEMPLATE_RE = re.compile(r"\{\{\s*(?:ndash|endash)\s*\}\}", re.IGNORECASE)
EMDASH_TEMPLATE_RE = re.compile(r"\{\{\s*(?:mdash|emdash)\s*\}\}", re.IGNORECASE)
BOLD_ITALIC_RE = re.compile(r"'{2,5}")
TEMPLATE_RE = re.compile(r"\{\{[^{}]*\}\}", re.DOTALL)
TABLE_RE = re.compile(r"\{\|.*?\|\}", re.DOTALL)
MALFORMED_TEMPLATE_RE = re.compile(r"\{\{[^{}\n]*(?=\n|$)")
RESIDUAL_MARKUP_RE = re.compile(
    r"\{\{|\}\}|\[\[|\]\]|<\s*/?\s*ref\b|<!--|\{\|",
    re.IGNORECASE,
)

SKIP_HEADINGS = {
    "bibliography",
    "citations",
    "external links",
    "footnotes",
    "further reading",
    "notes",
    "references",
    "see also",
    "sources",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create clean text, section, and chunk JSONL shards from raw enwiki person pages."
    )
    parser.add_argument("--raw-dir", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=min(8, os.cpu_count() or 1))
    parser.add_argument("--chunk-size", type=int, default=2000)
    parser.add_argument("--chunk-overlap", type=int, default=200)
    parser.add_argument("--min-section-chars", type=int, default=80)
    parser.add_argument("--min-chunk-chars", type=int, default=120)
    parser.add_argument("--gzip-level", type=int, default=3)
    parser.add_argument("--max-shards", type=int, help="Smoke test: process first N raw shards.")
    parser.add_argument(
        "--max-pages-per-shard",
        type=int,
        help="Smoke test: process at most N pages per raw shard.",
    )
    return parser.parse_args()


def stable_slug(text: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9]+", "_", text.strip().lower()).strip("_")
    return slug or "lead"


def json_dump(row: dict) -> str:
    return json.dumps(row, ensure_ascii=False, separators=(",", ":"))


def remove_balanced_markup(text: str, pattern: re.Pattern[str], max_rounds: int = 30) -> str:
    previous = None
    current = text
    rounds = 0
    while current != previous and rounds < max_rounds:
        previous = current
        current = pattern.sub(" ", current)
        rounds += 1
    return current


def has_residual_markup(text: str) -> bool:
    return bool(RESIDUAL_MARKUP_RE.search(text))


def drop_residual_markup_lines(text: str) -> str:
    lines = []
    for raw_line in text.splitlines():
        stripped = raw_line.strip()
        if stripped.startswith(("<!--", "-->", "{{", "}}", "{|", "|}")):
            continue
        lines.append(raw_line)
    return "\n".join(lines)


def preclean_wikitext(text: str) -> str:
    text = DASH_TEMPLATE_RE.sub(" - ", text)
    text = ENDASH_TEMPLATE_RE.sub("-", text)
    text = EMDASH_TEMPLATE_RE.sub("--", text)
    text = COMMENT_RE.sub(" ", text)
    text = REF_BLOCK_RE.sub(" ", text)
    text = REF_SELF_CLOSING_RE.sub(" ", text)
    text = CATEGORY_LINK_RE.sub(" ", text)
    text = remove_balanced_markup(text, TABLE_RE)
    return text


def fallback_strip_wikitext(text: str) -> str:
    text = preclean_wikitext(text)
    text = remove_balanced_markup(text, TEMPLATE_RE)
    text = re.sub(r"^\s*[*#;:]+\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\s*[|!].*$", " ", text, flags=re.MULTILINE)
    text = EXTERNAL_LINK_WITH_LABEL_RE.sub(r"\1", text)
    text = BARE_EXTERNAL_LINK_RE.sub(" ", text)
    text = WIKI_LINK_WITH_LABEL_RE.sub(r"\2", text)
    text = WIKI_LINK_RE.sub(lambda match: match.group(1).split("#", 1)[0], text)
    text = MALFORMED_WIKI_LINK_WITH_LABEL_RE.sub(r"\1", text)
    text = MALFORMED_WIKI_LINK_RE.sub(lambda match: match.group(1).split("#", 1)[0], text)
    text = MALFORMED_TEMPLATE_RE.sub(" ", text)
    text = REF_LINE_RE.sub(" ", text)
    text = text.replace("[[", "").replace("]]", "")
    text = text.replace("{{", "").replace("}}", "").replace("{|", "")
    text = drop_residual_markup_lines(text)
    text = BOLD_ITALIC_RE.sub("", text)
    text = HTML_TAG_RE.sub(" ", text)
    text = html.unescape(text)
    return normalize_text(text)


def strip_wikitext(text: str) -> str:
    text = preclean_wikitext(text)
    if mwparserfromhell is not None:
        try:
            code = mwparserfromhell.parse(text)
            stripped = code.strip_code(normalize=True, collapse=True)
            stripped = normalize_text(stripped)
            if has_residual_markup(stripped):
                stripped = fallback_strip_wikitext(stripped)
            return stripped
        except Exception:
            pass
    return fallback_strip_wikitext(text)


def normalize_text(text: str) -> str:
    text = re.sub(r"\(\s*\)", "", text)
    text = re.sub(r"\[\s*\]", "", text)
    text = re.sub(r"\s+([,.;:!?])", r"\1", text)
    lines = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            if lines and lines[-1] != "":
                lines.append("")
            continue
        line = re.sub(r"\s+", " ", line)
        lines.append(line)
    text = "\n".join(lines)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def extract_media_refs(wikitext: str) -> list[dict]:
    refs = []
    seen = set()
    for match in FILE_LINK_RE.finditer(wikitext):
        filename = match.group(1).strip()
        if not filename or filename in seen:
            continue
        seen.add(filename)
        refs.append({"filename": filename, "source": "wikitext_file_link"})
    return refs


def split_raw_sections(wikitext: str) -> list[dict]:
    sections = []
    matches = list(HEADING_RE.finditer(wikitext))
    if not matches:
        return [{"heading": "Lead", "level": 0, "raw_text": wikitext}]

    lead = wikitext[: matches[0].start()]
    if lead.strip():
        sections.append({"heading": "Lead", "level": 0, "raw_text": lead})

    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(wikitext)
        heading = strip_wikitext(match.group(2)).strip() or "Untitled"
        level = len(match.group(1))
        sections.append({"heading": heading, "level": level, "raw_text": wikitext[start:end]})
    return sections


def should_skip_heading(heading: str) -> bool:
    normalized = heading.strip().lower()
    return normalized in SKIP_HEADINGS


def split_chunks(text: str, chunk_size: int, overlap: int, min_chunk_chars: int) -> list[str]:
    if len(text) <= chunk_size:
        return [text] if len(text) >= min_chunk_chars else []

    paragraphs = [part.strip() for part in re.split(r"\n\s*\n", text) if part.strip()]
    chunks = []
    current = ""
    for paragraph in paragraphs:
        candidate = paragraph if not current else current + "\n\n" + paragraph
        if len(candidate) <= chunk_size:
            current = candidate
            continue
        if current and len(current) >= min_chunk_chars:
            chunks.append(current)
        if len(paragraph) <= chunk_size:
            current = paragraph
            continue
        start = 0
        while start < len(paragraph):
            piece = paragraph[start : start + chunk_size].strip()
            if len(piece) >= min_chunk_chars:
                chunks.append(piece)
            if start + chunk_size >= len(paragraph):
                break
            start += max(1, chunk_size - overlap)
        current = ""
    if current and len(current) >= min_chunk_chars:
        chunks.append(current)

    if overlap <= 0 or len(chunks) <= 1:
        return chunks

    overlapped = [chunks[0]]
    for chunk in chunks[1:]:
        prefix = overlapped[-1][-overlap:].strip()
        overlapped.append((prefix + "\n\n" + chunk).strip() if prefix else chunk)
    return overlapped


def base_metadata(row: dict) -> dict:
    keys = (
        "page_id",
        "qid",
        "title",
        "entity_type",
        "tags",
        "source_url",
        "revision_id",
        "revision_timestamp",
        "source_project",
        "source_dump",
    )
    return {key: row.get(key) for key in keys if key in row}


def derive_page(
    row: dict,
    chunk_size: int,
    chunk_overlap: int,
    min_section_chars: int,
    min_chunk_chars: int,
) -> tuple[dict, list[dict], list[dict]]:
    metadata = base_metadata(row)
    wikitext = row.get("wikitext") or ""
    media_refs = extract_media_refs(wikitext)
    section_rows = []
    chunk_rows = []
    plain_parts = []

    raw_sections = split_raw_sections(preclean_wikitext(wikitext))
    section_seen: dict[str, int] = {}
    for section_index, raw_section in enumerate(raw_sections):
        heading = raw_section["heading"]
        if should_skip_heading(heading):
            continue
        text = strip_wikitext(raw_section["raw_text"])
        if len(text) < min_section_chars:
            continue
        slug = stable_slug(heading)
        section_seen[slug] = section_seen.get(slug, 0) + 1
        suffix = "" if section_seen[slug] == 1 else f"_{section_seen[slug]}"
        section_id = f"{metadata.get('qid') or metadata.get('page_id')}::{slug}{suffix}"
        section_row = {
            **metadata,
            "section_id": section_id,
            "section_index": section_index,
            "heading": heading,
            "level": raw_section["level"],
            "text": text,
            "char_count": len(text),
        }
        section_rows.append(section_row)
        plain_parts.append(text)

        chunks = split_chunks(text, chunk_size, chunk_overlap, min_chunk_chars)
        for chunk_index, chunk in enumerate(chunks):
            chunk_rows.append(
                {
                    **metadata,
                    "chunk_id": f"{section_id}::{chunk_index:03d}",
                    "section_id": section_id,
                    "section_index": section_index,
                    "section_heading": heading,
                    "chunk_index": chunk_index,
                    "text": chunk,
                    "char_count": len(chunk),
                }
            )

    plain_text = normalize_text("\n\n".join(plain_parts))
    clean_row = {
        **metadata,
        "plain_text": plain_text,
        "plain_text_chars": len(plain_text),
        "section_count": len(section_rows),
        "chunk_count": len(chunk_rows),
        "media_refs": media_refs,
    }
    return clean_row, section_rows, chunk_rows


def output_path(out_dir: Path, part_index: int) -> Path:
    return out_dir / f"part-{part_index:05d}.jsonl.gz"


def process_shard(
    shard_index: int,
    shard_path: Path,
    out_dir: Path,
    chunk_size: int,
    chunk_overlap: int,
    min_section_chars: int,
    min_chunk_chars: int,
    gzip_level: int,
    max_pages_per_shard: int | None,
) -> dict:
    start = time.time()
    clean_dir = out_dir / "person_pages_clean"
    sections_dir = out_dir / "person_page_sections"
    chunks_dir = out_dir / "person_page_chunks"
    for directory in (clean_dir, sections_dir, chunks_dir):
        directory.mkdir(parents=True, exist_ok=True)

    clean_path = output_path(clean_dir, shard_index)
    sections_path = output_path(sections_dir, shard_index)
    chunks_path = output_path(chunks_dir, shard_index)
    tmp_clean = clean_path.with_suffix(clean_path.suffix + ".tmp")
    tmp_sections = sections_path.with_suffix(sections_path.suffix + ".tmp")
    tmp_chunks = chunks_path.with_suffix(chunks_path.suffix + ".tmp")

    scanned = 0
    clean_pages = 0
    sections = 0
    chunks = 0
    plain_text_chars = 0

    with gzip.open(shard_path, "rt", encoding="utf-8") as source, gzip.open(
        tmp_clean, "wt", encoding="utf-8", compresslevel=gzip_level
    ) as clean_out, gzip.open(
        tmp_sections, "wt", encoding="utf-8", compresslevel=gzip_level
    ) as sections_out, gzip.open(
        tmp_chunks, "wt", encoding="utf-8", compresslevel=gzip_level
    ) as chunks_out:
        for line in source:
            if max_pages_per_shard is not None and scanned >= max_pages_per_shard:
                break
            scanned += 1
            row = json.loads(line)
            clean_row, section_rows, chunk_rows = derive_page(
                row,
                chunk_size,
                chunk_overlap,
                min_section_chars,
                min_chunk_chars,
            )
            clean_out.write(json_dump(clean_row))
            clean_out.write("\n")
            clean_pages += 1
            plain_text_chars += clean_row["plain_text_chars"]
            for section_row in section_rows:
                sections_out.write(json_dump(section_row))
                sections_out.write("\n")
            sections += len(section_rows)
            for chunk_row in chunk_rows:
                chunks_out.write(json_dump(chunk_row))
                chunks_out.write("\n")
            chunks += len(chunk_rows)

    tmp_clean.replace(clean_path)
    tmp_sections.replace(sections_path)
    tmp_chunks.replace(chunks_path)
    return {
        "shard_index": shard_index,
        "input_file": shard_path.name,
        "clean_file": str(clean_path.relative_to(out_dir)),
        "sections_file": str(sections_path.relative_to(out_dir)),
        "chunks_file": str(chunks_path.relative_to(out_dir)),
        "scanned_pages": scanned,
        "clean_pages": clean_pages,
        "sections": sections,
        "chunks": chunks,
        "plain_text_chars": plain_text_chars,
        "elapsed_seconds": round(time.time() - start, 3),
    }


def main() -> int:
    args = parse_args()
    if args.chunk_overlap >= args.chunk_size:
        raise ValueError("--chunk-overlap must be smaller than --chunk-size")
    args.out_dir.mkdir(parents=True, exist_ok=True)
    shards = sorted(args.raw_dir.glob("part-*.jsonl.gz"))
    if args.max_shards:
        shards = shards[: args.max_shards]
    if not shards:
        raise FileNotFoundError(f"No part-*.jsonl.gz files found in {args.raw_dir}")

    results = []
    with concurrent.futures.ProcessPoolExecutor(max_workers=args.workers) as executor:
        futures = {
            executor.submit(
                process_shard,
                index,
                shard,
                args.out_dir,
                args.chunk_size,
                args.chunk_overlap,
                args.min_section_chars,
                args.min_chunk_chars,
                args.gzip_level,
                args.max_pages_per_shard,
            ): shard
            for index, shard in enumerate(shards)
        }
        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            results.append(result)
            print(
                f"[derive {result['shard_index']:05d}] pages={result['clean_pages']} "
                f"sections={result['sections']} chunks={result['chunks']} "
                f"in {result['elapsed_seconds']}s",
                file=sys.stderr,
            )

    results.sort(key=lambda item: item["shard_index"])
    manifest = {
        "raw_dir": str(args.raw_dir),
        "parser": "mwparserfromhell" if mwparserfromhell is not None else "regex_fallback",
        "chunk_size": args.chunk_size,
        "chunk_overlap": args.chunk_overlap,
        "min_section_chars": args.min_section_chars,
        "min_chunk_chars": args.min_chunk_chars,
        "workers": args.workers,
        "total_pages": sum(item["clean_pages"] for item in results),
        "total_sections": sum(item["sections"] for item in results),
        "total_chunks": sum(item["chunks"] for item in results),
        "total_plain_text_chars": sum(item["plain_text_chars"] for item in results),
        "shards": results,
    }
    (args.out_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"wrote manifest to {args.out_dir / 'manifest.json'}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
