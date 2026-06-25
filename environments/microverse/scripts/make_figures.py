"""Publication-grade figure generation for the MircoVerse workshop paper.

Reads the run artifacts the experiment pipeline already produces and renders the paper's figures with
matplotlib/seaborn. It is deliberately TOLERANT of missing data: every figure that lacks its input is
skipped with a printed note (so the script runs end-to-end before AND after the real sweep), and each
figure that DOES render also writes the tidy dataframe it plotted to a CSV next to the PNG, so the
numbers behind every figure are inspectable and the team can restyle in their own tooling.

INPUTS (any subset; globs ok):
  * data/results/threshold_sweep_seed<N>.json   — the NEW reflection-threshold sweep (per-agent
        engine-measured drift TRAJECTORIES). Produced by scripts/exp_threshold_sweep.py.
  * data/runs/<arm>_seed<N>.json                — per-run drift artifacts (pilot + sweep arms).
        Produced by scripts/run_three_settings.py / exp_threshold_sweep.py.

FIGURES:
  F1  Drift trajectory: mean # moral_boundaries vs tick, one line per reflection-threshold arm
      (engine_measurement series). The headline "does a lower gate drift earlier/more" figure.
  F2  Revision incidence + first-revision timing by threshold (bars).
  F3  Net guardrail change by persona band × arm (paraphrase-aware, from analyze_drift if a codes file
      is present; else the lexical net as a labelled upper bound). The H6 read.
  F4  Survival curve proxy: survivors vs arm; and identity-changed share by band.

USAGE:
    .venv/Scripts/python.exe scripts/make_figures.py                      # auto-discover defaults
    .venv/Scripts/python.exe scripts/make_figures.py --sweep data/results/threshold_sweep_seed1.json \\
        --runs "data/runs/thresh*_seed1.json" --outdir paper/figures
    .venv/Scripts/python.exe scripts/make_figures.py --runs "data/runs/*.json"   # pilot arms only

DEPENDENCIES: matplotlib, seaborn, pandas (install into the venv:
    .venv/Scripts/python.exe -m pip install matplotlib seaborn pandas).
The script degrades LOUDLY (clear message, exit 0) if a plotting dep is missing, so it never blocks a
run; install the deps and re-run to get the PNGs.
"""

from __future__ import annotations

import argparse
import glob
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

# Reuse the persona-band ground truth so figures never duplicate the axis definition.
try:
    from scripts.evaluate_runs import band_of, BAND_ORDER
except Exception:  # pragma: no cover - evaluate_runs import is best-effort
    BAND_ORDER = ["deeply-helpful", "helpful-pragmatic", "neutral-survivor", "self-interested", "ruthless"]
    def band_of(_name: str) -> str:  # type: ignore
        return "unknown"


def _need_plotting():
    """Import the plotting stack, or print install guidance and exit cleanly."""
    try:
        import matplotlib
        matplotlib.use("Agg")  # headless, deterministic file output
        import matplotlib.pyplot as plt
        import pandas as pd
        try:
            import seaborn as sns
            sns.set_theme(style="whitegrid", context="paper", font_scale=1.05)
        except Exception:
            sns = None
        return plt, pd, sns
    except Exception as exc:
        print("  ! plotting dependencies missing "
              f"({exc!r}).\n    Install them with:\n"
              "      .venv/Scripts/python.exe -m pip install matplotlib seaborn pandas\n"
              "    then re-run. (No figures written; this is not a hard error.)")
        sys.exit(0)


# Locked palette (mirrors the UI / paper tokens) — keep figures on-brand.
PALETTE = {
    "control": "#7fae8a", "mild": "#c79a64", "acute": "#c47b73",
    40: "#8aa6b4", 80: "#c79a64", 150: "#9a7fae",
}
BAND_COLORS = {
    "deeply-helpful": "#7fae8a", "helpful-pragmatic": "#9ab0a0",
    "neutral-survivor": "#b6b1a7", "self-interested": "#c79a64", "ruthless": "#c47b73",
}


def _load_all(paths: list[str]) -> list[dict]:
    out = []
    for p in paths:
        for hit in (glob.glob(p) or [p]):
            try:
                out.append({"_path": hit, **json.loads(Path(hit).read_text(encoding="utf-8"))})
            except FileNotFoundError:
                continue
    return out


# ── F1 + F2 : reflection-threshold sweep (engine-measured trajectories) ──────────────────────────

def fig_threshold_trajectories(sweep: dict, plt, pd, sns, outdir: Path) -> None:
    arms = sweep.get("arms") or []
    rows = []
    for arm in arms:
        thr = arm.get("reflection_threshold")
        for ag in arm.get("trajectories") or []:
            for s in ag.get("series") or []:
                if s.get("trigger") != "engine_measurement":
                    continue  # F1 uses the UNIFORM series only
                rows.append({
                    "threshold": thr, "tick": s.get("tick"),
                    "n_boundaries": s.get("n_boundaries"), "agent": ag.get("name"),
                })
    if not rows:
        print("  - F1/F2 skipped: no engine_measurement trajectories in the sweep "
              "(run scripts/exp_threshold_sweep.py with --snapshot-cadence > 0 first).")
        return
    df = pd.DataFrame(rows)
    df.to_csv(outdir / "F1_trajectory.csv", index=False)

    # F1 — mean boundary count vs tick, one line per threshold (CI band if seaborn present).
    fig, ax = plt.subplots(figsize=(7.2, 4.4))
    if sns is not None:
        sns.lineplot(data=df, x="tick", y="n_boundaries", hue="threshold",
                     palette="viridis", errorbar=("ci", 95), ax=ax, marker="o")
    else:
        for thr, g in df.groupby("threshold"):
            m = g.groupby("tick")["n_boundaries"].mean()
            ax.plot(m.index, m.values, marker="o", label=f"threshold {thr}")
        ax.legend(title="threshold")
    ax.set_title("F1 · Identity drift trajectory by reflection threshold\n"
                 "mean # moral boundaries per agent (engine_measurement, every N ticks)")
    ax.set_xlabel("tick"); ax.set_ylabel("mean moral_boundaries")
    fig.tight_layout(); fig.savefig(outdir / "F1_drift_trajectory.png", dpi=200); plt.close(fig)
    print(f"  ✓ F1_drift_trajectory.png  ({len(df)} engine_measurement points)")

    # F2 — revisions per agent + first-revision tick, by threshold.
    f2 = []
    for arm in arms:
        thr = arm.get("reflection_threshold")
        for ag in arm.get("trajectories") or []:
            f2.append({"threshold": thr, "n_revisions": ag.get("n_revisions", 0),
                       "first_revision_tick": ag.get("first_revision_tick")})
    f2df = pd.DataFrame(f2)
    f2df.to_csv(outdir / "F2_revisions.csv", index=False)
    fig, axes = plt.subplots(1, 2, figsize=(9.2, 4.2))
    agg = f2df.groupby("threshold")["n_revisions"].mean()
    axes[0].bar([str(t) for t in agg.index], agg.values, color="#c79a64")
    axes[0].set_title("F2a · mean identity revisions / agent"); axes[0].set_xlabel("reflection threshold")
    axes[0].set_ylabel("revisions / agent")
    ft = f2df.dropna(subset=["first_revision_tick"]).groupby("threshold")["first_revision_tick"].mean()
    if len(ft):
        axes[1].bar([str(t) for t in ft.index], ft.values, color="#8aa6b4")
    axes[1].set_title("F2b · mean first-revision tick"); axes[1].set_xlabel("reflection threshold")
    axes[1].set_ylabel("tick of first revision")
    fig.tight_layout(); fig.savefig(outdir / "F2_revision_incidence.png", dpi=200); plt.close(fig)
    print(f"  ✓ F2_revision_incidence.png")


# ── F3 + F4 : per-run drift artifacts (pilot or sweep arms) ──────────────────────────────────────

def _norm_set(items):
    return {str(x).strip().lower() for x in (items or []) if str(x).strip()}


def fig_run_artifacts(runs: list[dict], plt, pd, sns, outdir: Path) -> None:
    if not runs:
        print("  - F3/F4 skipped: no run artifacts found.")
        return

    # F4 — survivors by arm + identity-changed share by band.
    surv = [{"arm": r.get("setting"), "survivors": r.get("survivors"),
             "n_agents": r.get("n_agents")} for r in runs]
    sdf = pd.DataFrame(surv)
    sdf.to_csv(outdir / "F4_survival.csv", index=False)

    band_rows = []
    guard_rows = []
    for r in runs:
        arm = r.get("setting")
        for a in r.get("agents") or []:
            b = band_of(a["name"])
            ob, fb = _norm_set((a["original_soul"] or {}).get("moral_boundaries")), \
                     _norm_set((a["final_identity"] or {}).get("moral_boundaries"))
            band_rows.append({"arm": arm, "band": b, "name": a["name"],
                              "changed": bool(a.get("identity_changed")),
                              "survived": a.get("status") == "active"})
            guard_rows.append({"arm": arm, "band": b,
                               "net_boundaries": len(fb) - len(ob)})
    bdf = pd.DataFrame(band_rows)
    gdf = pd.DataFrame(guard_rows)
    bdf.to_csv(outdir / "F4_band.csv", index=False)
    gdf.to_csv(outdir / "F3_net_boundaries.csv", index=False)

    fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.4))
    sdf2 = sdf.dropna(subset=["arm"]).set_index("arm")
    colors = [PALETTE.get(a, "#b6b1a7") for a in sdf2.index]
    axes[0].bar(sdf2.index.astype(str), sdf2["survivors"], color=colors)
    axes[0].set_title("F4a · survivors by arm"); axes[0].set_ylabel("survivors @ end")
    chg = bdf.groupby("band")["changed"].mean().reindex(BAND_ORDER).dropna()
    axes[1].bar(chg.index, (chg.values * 100), color=[BAND_COLORS.get(b, "#b6b1a7") for b in chg.index])
    axes[1].set_title("F4b · % identities changed, by persona band"); axes[1].set_ylabel("% changed")
    axes[1].tick_params(axis="x", rotation=30)
    fig.tight_layout(); fig.savefig(outdir / "F4_survival_and_change.png", dpi=200); plt.close(fig)
    print(f"  ✓ F4_survival_and_change.png  ({len(runs)} run artifact(s))")

    # F3 — net boundary change (lexical upper bound) by band × arm. The H6-relevant direction.
    # NOTE: this is the LEXICAL net (paraphrase-inflated). For the de-confounded guardrail-toward-others
    # number, run scripts/analyze_drift.py with --codes and plot net_guardrail_toward_others; this figure
    # prints a caption to that effect so a reviewer is not misled.
    piv = gdf.groupby(["band", "arm"])["net_boundaries"].sum().unstack(fill_value=0)
    piv = piv.reindex([b for b in BAND_ORDER if b in piv.index])
    fig, ax = plt.subplots(figsize=(8.6, 4.6))
    if sns is not None:
        import numpy as np  # local — only needed here
        sns.heatmap(piv, annot=True, fmt="+d", center=0, cmap="vlag", ax=ax,
                    cbar_kws={"label": "net Δ boundaries (lexical)"})
    else:
        ax.imshow(piv.values, cmap="coolwarm"); ax.set_xticks(range(len(piv.columns)))
        ax.set_xticklabels(piv.columns); ax.set_yticks(range(len(piv.index)))
        ax.set_yticklabels(piv.index)
    ax.set_title("F3 · net moral-boundary change by band × arm (LEXICAL upper bound)\n"
                 "+ = acquired guardrails (H6 restoring-force candidate); − = erosion (H1)")
    fig.tight_layout(); fig.savefig(outdir / "F3_net_boundaries.png", dpi=200); plt.close(fig)
    print(f"  ✓ F3_net_boundaries.png  (caption: lexical; use analyze_drift --codes for guardrail-only)")


def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
    except Exception:
        pass
    ap = argparse.ArgumentParser(description="Render MircoVerse paper figures from run artifacts")
    ap.add_argument("--sweep", default="data/results/threshold_sweep_seed*.json",
                    help="reflection-threshold sweep artifact(s) (glob ok)")
    ap.add_argument("--runs", default="data/runs/*.json",
                    help="per-run drift artifact(s) (glob ok)")
    ap.add_argument("--outdir", default="paper/figures", help="where to write PNGs + CSVs")
    args = ap.parse_args()

    plt, pd, sns = _need_plotting()
    outdir = (_ROOT / args.outdir) if not Path(args.outdir).is_absolute() else Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    print(f"writing figures to {outdir}")

    sweeps = _load_all([args.sweep])
    if sweeps:
        # If multiple sweep files, just use the first (one seed per file); note the rest.
        if len(sweeps) > 1:
            print(f"  (found {len(sweeps)} sweep files; plotting {sweeps[0]['_path']})")
        fig_threshold_trajectories(sweeps[0], plt, pd, sns, outdir)
    else:
        print(f"  - no sweep artifact matched {args.sweep} — F1/F2 skipped (run exp_threshold_sweep.py).")

    runs = _load_all([args.runs])
    fig_run_artifacts(runs, plt, pd, sns, outdir)

    print("done.")


if __name__ == "__main__":
    main()
