"""Generate downloadable MatrAIx PDF reports for Harbor batch jobs and trials."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

from fpdf import FPDF

# Portable Helvetica is Latin-1 only; normalize common Unicode punctuation.
_UNICODE_MAP = str.maketrans(
    {
        "\u2013": "-",  # en dash
        "\u2014": "-",  # em dash
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u2026": "...",
        "\u00b7": "-",
        "\u00d7": "x",
        "\u2212": "-",
        "\u00a0": " ",
        "\u2022": "-",
        "\u2192": "->",
        "\ufeff": "",
    }
)


def _safe(value: object, *, limit: int | None = None) -> str:
    text = " ".join(str(value if value is not None else "").translate(_UNICODE_MAP).split())
    if limit is not None and len(text) > limit:
        text = text[: max(0, limit - 1)].rstrip() + "..."
    return text.encode("latin-1", "replace").decode("latin-1")


def _fmt_num(value: object) -> str:
    if value is None:
        return "-"
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, float):
        if value == int(value):
            return str(int(value))
        return f"{value:.2f}"
    return _safe(value)


def _humanize(value: object) -> str:
    text = _safe(value)
    if not text or text == "-":
        return text
    if re.fullmatch(r"[a-z0-9]+(?:_[a-z0-9]+)+", text):
        return text.replace("_", " ").strip().capitalize()
    return text


def _pct(count: int, total: int) -> str:
    if total <= 0:
        return "0%"
    return f"{round(100.0 * count / total)}%"


def _bar(count: int, total: int, *, width: int = 18) -> str:
    if total <= 0 or count <= 0:
        return "." * width
    filled = max(1, round(width * count / total))
    return "#" * min(width, filled) + "." * max(0, width - filled)


class _ReportPDF(FPDF):
    def __init__(self) -> None:
        super().__init__(orientation="P", unit="mm", format="A4")
        self.set_auto_page_break(auto=True, margin=18)
        self.set_margins(18, 16, 18)
        self._in_header = False

    def header(self) -> None:
        if self.page_no() == 1:
            return
        self._in_header = True
        self.set_font("Helvetica", "B", 8)
        self.set_text_color(0, 118, 194)
        self.cell(0, 4, "MatrAIx", new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(0, 118, 194)
        self.set_line_width(0.35)
        self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
        self.ln(5)
        self._in_header = False

    def footer(self) -> None:
        self.set_y(-12)
        self.set_font("Helvetica", "", 8)
        self.set_text_color(120, 120, 120)
        self.cell(0, 4, f"Page {self.page_no()}/{{nb}}", align="C")

    def content_width(self) -> float:
        return self.w - self.l_margin - self.r_margin

    def ensure_space(self, height: float) -> None:
        if self._in_header:
            return
        if self.get_y() + height > self.h - self.b_margin:
            self.add_page()

    def cover(self, *, eyebrow: str, title: str, meta_lines: list[str]) -> None:
        self.add_page()
        self.set_font("Helvetica", "B", 9)
        self.set_text_color(0, 118, 194)
        self.cell(0, 5, "MatrAIx", new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(0, 118, 194)
        self.set_line_width(0.45)
        self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
        self.ln(8)
        self.set_font("Helvetica", "", 11)
        self.set_text_color(0, 118, 194)
        self.cell(0, 6, _safe(eyebrow), new_x="LMARGIN", new_y="NEXT")
        self.ln(1)
        self.set_font("Helvetica", "B", 16)
        self.set_text_color(17, 23, 31)
        self.multi_cell(0, 7, _safe(title, limit=160), new_x="LMARGIN", new_y="NEXT")
        self.ln(3)
        self.set_font("Helvetica", "", 10)
        self.set_text_color(71, 85, 105)
        for line in meta_lines:
            if line:
                self.multi_cell(0, 5, _safe(line, limit=220), new_x="LMARGIN", new_y="NEXT")
        self.ln(4)

    def section(self, title: str) -> None:
        self.ensure_space(16)
        self.ln(2)
        self.set_font("Helvetica", "B", 13)
        self.set_text_color(15, 23, 42)
        self.cell(0, 7, _safe(title), new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(203, 213, 225)
        self.set_line_width(0.25)
        self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
        self.ln(3)

    def h3(self, title: str) -> None:
        self.ensure_space(12)
        self.set_font("Helvetica", "B", 11)
        self.set_text_color(30, 41, 59)
        self.multi_cell(0, 5.5, _safe(title, limit=240), new_x="LMARGIN", new_y="NEXT")
        self.ln(1)

    def muted(self, text: str) -> None:
        self.ensure_space(8)
        self.set_font("Helvetica", "", 9)
        self.set_text_color(100, 116, 139)
        self.multi_cell(0, 4.5, _safe(text, limit=300), new_x="LMARGIN", new_y="NEXT")
        self.ln(1)

    def body(self, text: str, *, size: int = 10) -> None:
        self.ensure_space(10)
        self.set_font("Helvetica", "", size)
        self.set_text_color(51, 65, 85)
        self.multi_cell(0, 5, _safe(text), new_x="LMARGIN", new_y="NEXT")
        self.ln(0.5)

    def bullet(self, text: str) -> None:
        self.ensure_space(8)
        self.set_font("Helvetica", "", 9)
        self.set_text_color(51, 65, 85)
        self.multi_cell(0, 4.5, f"- {_safe(text, limit=360)}", new_x="LMARGIN", new_y="NEXT")

    def kv_block(self, rows: list[tuple[str, str]]) -> None:
        """Single-column key/value rows — never splits across pages mid-row."""
        if not rows:
            self.body("No data.")
            return
        label_w = 42.0
        value_w = self.content_width() - label_w
        for label, value in rows:
            left = _safe(label, limit=40)
            right = _safe(value if value not in (None, "") else "-", limit=500)
            approx_lines = max(1, (len(right) // 70) + 1)
            self.ensure_space(5.0 * approx_lines + 2)
            y0 = self.get_y()
            self.set_font("Helvetica", "B", 9)
            self.set_text_color(100, 116, 139)
            self.set_xy(self.l_margin, y0)
            self.multi_cell(label_w, 5, left, new_x="LMARGIN", new_y="NEXT")
            y_left = self.get_y()
            self.set_xy(self.l_margin + label_w, y0)
            self.set_font("Helvetica", "", 9)
            self.set_text_color(30, 41, 59)
            self.multi_cell(value_w, 5, right, new_x="LMARGIN", new_y="NEXT")
            self.set_y(max(y_left, self.get_y()) + 0.8)

    def metric_strip(self, items: list[tuple[str, str]]) -> None:
        if not items:
            return
        self.ensure_space(16)
        col_w = self.content_width() / max(1, len(items))
        y0 = self.get_y()
        for idx, (label, value) in enumerate(items):
            x = self.l_margin + idx * col_w
            self.set_xy(x, y0)
            self.set_font("Helvetica", "", 8)
            self.set_text_color(100, 116, 139)
            self.cell(col_w - 2, 4, _safe(label, limit=24))
            self.set_xy(x, y0 + 4)
            self.set_font("Helvetica", "B", 12)
            self.set_text_color(15, 23, 42)
            self.cell(col_w - 2, 6, _safe(value, limit=18))
        self.set_y(y0 + 12)
        self.ln(2)

    def count_rows(
        self,
        rows: list[tuple[str, int]],
        *,
        total: int | None = None,
    ) -> None:
        if not rows:
            self.body("No responses.")
            return
        denom = total if total is not None else sum(max(0, c) for _, c in rows)
        for label, count in rows:
            self.ensure_space(10)
            self.set_font("Helvetica", "", 9)
            self.set_text_color(30, 41, 59)
            self.multi_cell(0, 4.2, _safe(label, limit=100), new_x="LMARGIN", new_y="NEXT")
            self.set_font("Courier", "", 8)
            self.set_text_color(71, 85, 105)
            self.multi_cell(
                0,
                4,
                _safe(f"  {count} ({_pct(count, denom)})  {_bar(count, denom)}", limit=60),
                new_x="LMARGIN",
                new_y="NEXT",
            )
            self.ln(0.5)
        self.ln(1)

    def card_start(self) -> None:
        self.ensure_space(20)
        self.set_draw_color(226, 232, 240)
        self.set_line_width(0.2)
        y = self.get_y()
        self.line(self.l_margin, y, self.w - self.r_margin, y)
        self.ln(3)


def _choice_label(context: dict[str, Any], value: object) -> str:
    options = context.get("choiceOptions") if isinstance(context.get("choiceOptions"), list) else []
    raw = str(value if value is not None else "")
    for option in options:
        if isinstance(option, dict) and str(option.get("id")) == raw:
            label = option.get("label")
            if label:
                return _safe(label)
    return _humanize(raw)


def _primary_facet(context: dict[str, Any]) -> dict[str, Any] | None:
    facets = context.get("facets") if isinstance(context.get("facets"), list) else []
    for facet in facets:
        if isinstance(facet, dict) and facet.get("role") == "primary":
            return facet
    for facet in facets:
        if isinstance(facet, dict):
            return facet
    return None


def _is_survey_aggregation(contexts: list[Any], application_type: str | None) -> bool:
    if (application_type or "").lower() == "survey":
        return True
    return any(
        isinstance(ctx, dict) and ctx.get("contextType") == "question_response"
        for ctx in contexts
    )


def _coverage_metrics(coverage: dict[str, Any]) -> list[tuple[str, str]]:
    return [
        ("Trials", _fmt_num(coverage.get("trialCount"))),
        ("Completed", _fmt_num(coverage.get("completedTrials"))),
        ("Pending", _fmt_num(coverage.get("pendingTrials"))),
        ("Artifacts", _fmt_num(coverage.get("artifactReadyTrials"))),
    ]


def _job_meta_lines(job: dict[str, Any] | None, aggregation: dict[str, Any]) -> list[str]:
    job = job or {}
    launch = job.get("launch") if isinstance(job.get("launch"), dict) else {}
    result = job.get("result") if isinstance(job.get("result"), dict) else {}
    config = job.get("config") if isinstance(job.get("config"), dict) else {}
    reporting = aggregation.get("reporting") if isinstance(aggregation.get("reporting"), dict) else {}
    generated = aggregation.get("generatedAt") or datetime.now(timezone.utc).isoformat()

    status = launch.get("status")
    if not status:
        if result.get("finished_at"):
            status = "completed"
        elif result.get("started_at"):
            status = "running"
        else:
            status = "unknown"

    lines = [
        f"Generated: {_safe(generated)}",
        f"Status: {_safe(status)}"
        + (f" · exit {_safe(launch.get('exitCode'))}" if launch.get("exitCode") is not None else ""),
    ]
    if result.get("started_at") or result.get("finished_at"):
        lines.append(
            f"Run window: {_safe(result.get('started_at') or '-')} -> {_safe(result.get('finished_at') or '-')}"
        )
    if launch.get("configPath"):
        lines.append(f"Config: {_safe(launch.get('configPath'))}")
    agents = config.get("agents") if isinstance(config.get("agents"), list) else []
    if agents and isinstance(agents[0], dict) and agents[0].get("model_name"):
        lines.append(f"Agent model: {_safe(agents[0].get('model_name'))}")
    if reporting:
        status_r = _safe(reporting.get("status") or "-")
        if status_r not in ("-", "not_applicable"):
            model = f" · {_safe(reporting.get('model'))}" if reporting.get("model") else ""
            lines.append(f"LLM report: {status_r}{model}")
    return lines


def _render_facet_distribution(
    pdf: _ReportPDF,
    facet: dict[str, Any],
    *,
    context: dict[str, Any] | None = None,
) -> None:
    kind = str(facet.get("kind") or "")
    present = int(facet.get("presentCount") or 0)
    context = context or {}

    if kind == "categorical":
        categorical = facet.get("categorical") if isinstance(facet.get("categorical"), dict) else {}
        counts = categorical.get("counts") if isinstance(categorical.get("counts"), list) else []
        options = context.get("choiceOptions") if isinstance(context.get("choiceOptions"), list) else []
        by_id = {
            str(item.get("value")): int(item.get("count") or 0)
            for item in counts
            if isinstance(item, dict)
        }
        rows: list[tuple[str, int]] = []
        seen: set[str] = set()
        if options:
            for option in options:
                if not isinstance(option, dict):
                    continue
                oid = str(option.get("id") or "")
                seen.add(oid)
                rows.append((_choice_label(context, oid), by_id.get(oid, 0)))
            for value, count in by_id.items():
                if value not in seen:
                    rows.append((_humanize(value), count))
        else:
            rows = [
                (_choice_label(context, item.get("value")), int(item.get("count") or 0))
                for item in counts
                if isinstance(item, dict)
            ]
        pdf.muted(f"{present} responses · {len(rows)} categories")
        pdf.count_rows(rows, total=present or None)
        return

    if kind == "numerical":
        numerical = facet.get("numerical") if isinstance(facet.get("numerical"), dict) else {}
        scale_bits = []
        if context.get("scaleMin") is not None or facet.get("scaleMin") is not None:
            lo = context.get("scaleMin", facet.get("scaleMin"))
            hi = context.get("scaleMax", facet.get("scaleMax"))
            scale_bits.append(f"scale {_fmt_num(lo)}-{_fmt_num(hi)}")
        pdf.muted(
            "avg {avg} · min {min} · max {max} · n={n}{scale}".format(
                avg=_fmt_num(numerical.get("avg")),
                min=_fmt_num(numerical.get("min")),
                max=_fmt_num(numerical.get("max")),
                n=_fmt_num(numerical.get("count") or present),
                scale=(f" · {scale_bits[0]}" if scale_bits else ""),
            )
        )
        counts = numerical.get("counts") if isinstance(numerical.get("counts"), list) else []
        if counts:
            rows = [
                (_safe(item.get("value")), int(item.get("count") or 0))
                for item in counts
                if isinstance(item, dict)
            ]

            def _sort_key(row: tuple[str, int]) -> tuple[int, float | str]:
                try:
                    return (0, float(row[0]))
                except ValueError:
                    return (1, row[0])

            rows.sort(key=_sort_key)
            pdf.count_rows(rows, total=present or None)
        return

    if kind == "textual":
        textual = facet.get("textual") if isinstance(facet.get("textual"), dict) else {}
        if textual.get("summary"):
            pdf.body(str(textual.get("summary")), size=9)
        samples = textual.get("samples") if isinstance(textual.get("samples"), list) else []
        if samples:
            pdf.muted("Sample answers")
            for sample in samples[:6]:
                pdf.bullet(_safe(sample, limit=280))
        return

    pdf.kv_block(
        [
            ("Kind", kind or "-"),
            ("Present / missing", f"{facet.get('presentCount', 0)} / {facet.get('missingCount', 0)}"),
        ]
    )


def _render_question_context(pdf: _ReportPDF, context: dict[str, Any], *, index: int) -> None:
    pdf.card_start()
    label = context.get("label") or context.get("key") or f"Question {index}"
    qtype = _safe(context.get("questionType") or "question")
    pdf.h3(f"Q{index}. {_safe(label, limit=220)}")
    pdf.muted(qtype.replace("_", " "))
    facet = _primary_facet(context)
    if facet:
        _render_facet_distribution(pdf, facet, context=context)
    else:
        pdf.body("No response data for this question.")


def _render_generic_context(pdf: _ReportPDF, context: dict[str, Any]) -> None:
    pdf.card_start()
    label = context.get("label") or context.get("key") or "Context"
    bits = []
    if context.get("contextType"):
        bits.append(_safe(context.get("contextType")).replace("_", " "))
    if context.get("questionType"):
        bits.append(_safe(context.get("questionType")).replace("_", " "))
    pdf.h3(_safe(label, limit=220))
    if bits:
        pdf.muted(" · ".join(bits))
    facets = context.get("facets") if isinstance(context.get("facets"), list) else []
    for facet in facets[:8]:
        if not isinstance(facet, dict):
            continue
        facet_label = facet.get("label") or facet.get("key") or "Signal"
        if len(facets) > 1:
            pdf.muted(_safe(facet_label))
        _render_facet_distribution(pdf, facet, context=context)
    summaries = context.get("summaries") if isinstance(context.get("summaries"), list) else []
    for summary in summaries[:4]:
        if not isinstance(summary, dict):
            continue
        title = summary.get("title") or summary.get("id") or "Summary"
        pdf.muted(f"Summary · {_safe(title)}")
        overall = summary.get("overall") if isinstance(summary.get("overall"), dict) else {}
        if overall.get("summary"):
            pdf.body(str(overall.get("summary")), size=9)
        buckets = summary.get("buckets") if isinstance(summary.get("buckets"), list) else []
        for bucket in buckets[:6]:
            if not isinstance(bucket, dict):
                continue
            pdf.bullet(
                f"{_safe(bucket.get('bucket'))} (n={_fmt_num(bucket.get('count'))}): "
                f"{_safe(bucket.get('summary') or '', limit=280)}"
            )


def build_batch_report_pdf(
    *,
    job_name: str,
    job: dict[str, Any] | None,
    aggregation: dict[str, Any],
) -> bytes:
    job = job or {}
    coverage = aggregation.get("coverage") if isinstance(aggregation.get("coverage"), dict) else {}
    fields = aggregation.get("fields") if isinstance(aggregation.get("fields"), list) else []
    contexts = aggregation.get("contexts") if isinstance(aggregation.get("contexts"), list) else []
    trials = job.get("trials") if isinstance(job.get("trials"), list) else []
    application_type = job.get("applicationType")
    if not application_type:
        config = job.get("config") if isinstance(job.get("config"), dict) else {}
        agents = config.get("agents") if isinstance(config.get("agents"), list) else []
        if agents and isinstance(agents[0], dict):
            agent_name = str(agents[0].get("name") or "")
            if "survey" in agent_name:
                application_type = "survey"

    is_survey = _is_survey_aggregation(contexts, str(application_type) if application_type else None)
    questions = [
        ctx
        for ctx in contexts
        if isinstance(ctx, dict) and ctx.get("contextType") == "question_response"
    ]
    other_contexts = [
        ctx
        for ctx in contexts
        if isinstance(ctx, dict) and ctx.get("contextType") != "question_response"
    ]
    trial_summary = next(
        (
            ctx
            for ctx in other_contexts
            if isinstance(ctx, dict) and ctx.get("contextType") == "trial_summary"
        ),
        None,
    )
    detail_contexts = [
        ctx
        for ctx in other_contexts
        if not (isinstance(ctx, dict) and ctx.get("contextType") == "trial_summary")
    ]

    pdf = _ReportPDF()
    pdf.alias_nb_pages()
    pdf.cover(
        eyebrow="Batch report" + (" · Survey" if is_survey else ""),
        title=job_name,
        meta_lines=_job_meta_lines(job, aggregation),
    )

    pdf.section("Overview")
    pdf.metric_strip(_coverage_metrics(coverage))
    if is_survey and questions:
        type_counts: dict[str, int] = {}
        for ctx in questions:
            qtype = str(ctx.get("questionType") or "unknown").replace("_", " ")
            type_counts[qtype] = type_counts.get(qtype, 0) + 1
        mix = ", ".join(f"{count} {label}" for label, count in sorted(type_counts.items()))
        pdf.body(f"{len(questions)} questions · {mix}", size=9)

    if questions:
        pdf.section("Per-question report")
        for idx, ctx in enumerate(questions, start=1):
            _render_question_context(pdf, ctx, index=idx)
    elif detail_contexts:
        pdf.section("Contexts")
        for ctx in detail_contexts:
            _render_generic_context(pdf, ctx)
    elif fields:
        pdf.section("Aggregated fields")
        for field in fields:
            if not isinstance(field, dict):
                continue
            pdf.card_start()
            pdf.h3(_safe(field.get("label") or field.get("key") or "Field"))
            _render_facet_distribution(pdf, field)

    if detail_contexts and questions:
        pdf.section("Other contexts")
        for ctx in detail_contexts:
            _render_generic_context(pdf, ctx)

    if trial_summary and isinstance(trial_summary, dict):
        pdf.section("Run stats")
        facets = trial_summary.get("facets") if isinstance(trial_summary.get("facets"), list) else []
        rows: list[tuple[str, str]] = []
        for facet in facets:
            if not isinstance(facet, dict):
                continue
            label = _safe(facet.get("label") or facet.get("key") or "metric")
            numerical = facet.get("numerical") if isinstance(facet.get("numerical"), dict) else {}
            if numerical:
                rows.append(
                    (
                        label,
                        f"avg {_fmt_num(numerical.get('avg'))} · "
                        f"min {_fmt_num(numerical.get('min'))} · "
                        f"max {_fmt_num(numerical.get('max'))}",
                    )
                )
            else:
                rows.append((label, f"n={_fmt_num(facet.get('presentCount'))}"))
        pdf.kv_block(rows)

    if trials:
        pdf.section("Trials")
        for trial in trials:
            if not isinstance(trial, dict):
                continue
            persona = trial.get("personaName") or trial.get("personaId") or "-"
            status = "done" if trial.get("completed") else "pending"
            if trial.get("error") or trial.get("succeeded") is False:
                status = "failed"
            name = _safe(trial.get("trialName") or "trial", limit=48)
            line = f"{_safe(persona, limit=28)}  {status}  {name}"
            if trial.get("error"):
                line += f"  · {_safe(trial.get('error'), limit=80)}"
            pdf.ensure_space(6)
            pdf.set_font("Courier", "", 8)
            pdf.set_text_color(30, 41, 59)
            pdf.multi_cell(0, 4, _safe(line, limit=110), new_x="LMARGIN", new_y="NEXT")
        pdf.ln(1)

    return bytes(pdf.output())


def build_trial_report_pdf(
    *,
    job_name: str,
    trial_name: str,
    debrief: dict[str, Any],
) -> bytes:
    app_type = str(debrief.get("applicationType") or "chatbot")
    persona = debrief.get("persona") if isinstance(debrief.get("persona"), dict) else {}
    config = debrief.get("config") if isinstance(debrief.get("config"), dict) else {}
    created = debrief.get("createdAt") or ""

    pdf = _ReportPDF()
    pdf.alias_nb_pages()
    pdf.cover(
        eyebrow="Trial report",
        title=_safe(trial_name, limit=120),
        meta_lines=[
            f"Job: {_safe(job_name, limit=120)}",
            f"Application: {_safe(app_type)}",
            f"Created: {_safe(created) or '-'}",
            f"Persona: {_safe(persona.get('name') or persona.get('id') or '-')}",
            f"Task: {_safe(config.get('taskPath') or config.get('applicationId') or '-')}",
        ],
    )

    pdf.section("Persona")
    pdf.kv_block(
        [
            ("ID", _safe(persona.get("id"))),
            ("Name", _safe(persona.get("name"))),
            ("Source", _safe(persona.get("source"))),
        ]
    )
    dims = persona.get("dimensions") if isinstance(persona.get("dimensions"), dict) else {}
    if dims:
        pdf.body(
            ", ".join(f"{_safe(k)}={_safe(v)}" for k, v in list(dims.items())[:16]),
            size=9,
        )

    verifier = debrief.get("verifier") if isinstance(debrief.get("verifier"), dict) else {}
    feedback = (
        debrief.get("userFeedback") if isinstance(debrief.get("userFeedback"), dict) else {}
    )
    trial_eval = (
        debrief.get("trialEvaluation") if isinstance(debrief.get("trialEvaluation"), dict) else {}
    )
    if verifier or feedback or trial_eval:
        pdf.section("Evaluation")
        rows: list[tuple[str, str]] = []
        if verifier:
            rows.append(("Verifier reward", _fmt_num(verifier.get("reward"))))
            rows.append(("Verifier passed", _fmt_num(verifier.get("passed"))))
        if trial_eval:
            for key in ("overall", "score", "passed", "summary"):
                if key in trial_eval:
                    rows.append((key, _safe(trial_eval.get(key), limit=200)))
        if rows:
            pdf.kv_block(rows)
        if verifier.get("details"):
            pdf.body(_safe(verifier.get("details"), limit=800), size=9)
        if feedback:
            for key, value in list(feedback.items())[:20]:
                if key in ("schemaVersion",):
                    continue
                if isinstance(value, (dict, list)):
                    pdf.muted(_safe(key))
                    pdf.body(_safe(value, limit=400), size=9)
                else:
                    pdf.kv_block([(_safe(key), _safe(value))])

    if app_type == "survey":
        survey = debrief.get("surveyResult") if isinstance(debrief.get("surveyResult"), dict) else {}
        instrument = survey.get("instrument") if isinstance(survey.get("instrument"), dict) else {}
        pdf.section("Survey answers")
        pdf.kv_block(
            [
                ("Instrument", _safe(instrument.get("title") or instrument.get("id"))),
                ("Completed", _fmt_num(survey.get("completed"))),
            ]
        )
        answers = survey.get("answers") if isinstance(survey.get("answers"), list) else []
        questions = instrument.get("questions") if isinstance(instrument.get("questions"), list) else []
        labels = {
            str(q.get("id")): q.get("prompt") or q.get("label") or q.get("id")
            for q in questions
            if isinstance(q, dict) and q.get("id") is not None
        }
        for idx, answer in enumerate(answers, start=1):
            if not isinstance(answer, dict):
                continue
            qid = str(answer.get("questionId") or f"q{idx}")
            title = labels.get(qid) or qid
            pdf.card_start()
            pdf.h3(f"Q{idx}. {_safe(title, limit=200)}")
            pdf.body(f"Answer: {_safe(answer.get('value'), limit=500)}", size=9)
            if answer.get("rationale"):
                pdf.body(f"Rationale: {_safe(answer.get('rationale'), limit=600)}", size=9)

    elif app_type == "web":
        web = debrief.get("webResult") if isinstance(debrief.get("webResult"), dict) else {}
        pdf.section("Web result")
        rows = [
            (_safe(key), _safe(web.get(key), limit=240))
            for key in ("selection", "reason", "success", "score", "url")
            if key in web
        ]
        ratings = web.get("ratings") if isinstance(web.get("ratings"), dict) else {}
        rows.extend((_safe(k), _safe(v)) for k, v in list(ratings.items())[:12])
        pdf.kv_block(rows)

    elif app_type == "os-app":
        os_app = debrief.get("osAppResult") if isinstance(debrief.get("osAppResult"), dict) else {}
        pdf.section("OS app result")
        pdf.kv_block(
            [
                (_safe(key), _safe(os_app.get(key), limit=240))
                for key in ("success", "score", "summary", "artifactPath")
                if key in os_app
            ]
        )

    else:
        metrics = (
            debrief.get("metricScores") if isinstance(debrief.get("metricScores"), dict) else {}
        )
        if metrics:
            pdf.section("Metric scores")
            pdf.kv_block([(_safe(k), _safe(v)) for k, v in list(metrics.items())[:20]])
        questionnaire = (
            debrief.get("questionnaire") if isinstance(debrief.get("questionnaire"), dict) else {}
        )
        ratings = (
            questionnaire.get("ratings") if isinstance(questionnaire.get("ratings"), dict) else {}
        )
        if ratings:
            pdf.section("Self-report")
            pdf.kv_block([(_safe(k), _safe(v)) for k, v in list(ratings.items())[:20]])
        transcript = debrief.get("transcript") if isinstance(debrief.get("transcript"), list) else []
        if transcript:
            pdf.section("Transcript")
            for turn in transcript[:40]:
                if not isinstance(turn, dict):
                    continue
                role = turn.get("role") or turn.get("speaker") or "turn"
                text = turn.get("content") or turn.get("text") or turn.get("message") or ""
                pdf.body(f"[{_safe(role)}] {_safe(text, limit=700)}", size=9)

    return bytes(pdf.output())


def pdf_filename(*parts: str) -> str:
    cleaned = []
    for part in parts:
        token = "".join(ch if ch.isalnum() or ch in "-_" else "-" for ch in str(part).strip())
        token = token.strip("-_") or "report"
        cleaned.append(token[:80])
    return "-".join(cleaned) + ".pdf"
