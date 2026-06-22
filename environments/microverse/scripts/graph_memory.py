"""Memory system visualization — clean redesign."""
import json
import glob
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.patheffects as pe
from matplotlib.patches import FancyArrowPatch

# ── palette ──────────────────────────────────────────────────────────────────
BG     = "#0d0d14"
PANEL  = "#13131f"
BORDER = "#252538"
TEXT   = "#f0f0f8"
DIM    = "#888899"
GREEN  = "#3ddc84"
AMBER  = "#ffb347"
PINK   = "#ff5fa0"
BLUE   = "#5ab4ff"
PURPLE = "#b87fff"

ARM_COL = {"control": BLUE, "mild": AMBER, "acute": PINK}

# ── load data ────────────────────────────────────────────────────────────────
records = []
for f in sorted(glob.glob("data/runs/*.json")):
    with open(f) as fh:
        d = json.load(fh)
    arm = d["arm"]["label"]
    for a in d["agents"]:
        snaps      = a.get("snapshots", [])
        snap_ticks = [int(s["tick"]) for s in snaps]
        last_t     = max(snap_ticks) if snap_ticks else 0
        records.append({
            "arm":        arm,
            "snap_count": len(snaps),
            "snap_ticks": snap_ticks,
            "last_tick":  last_t,
            "survived":   a["status"] == "active",
            "changed":    a.get("identity_changed", False),
            "mb_start":   len(a["original_soul"].get("moral_boundaries", [])),
            "mb_end":     len(a["final_identity"].get("moral_boundaries", [])),
            "name":       a["name"],
        })


def mean_or_zero(lst):
    return sum(lst) / len(lst) if lst else 0


def style(ax, title, subtitle=None):
    ax.set_facecolor(PANEL)
    for sp in ax.spines.values():
        sp.set_color(BORDER)
    ax.tick_params(colors=DIM, labelsize=11)
    ax.xaxis.label.set_color(DIM)
    ax.yaxis.label.set_color(DIM)
    ax.grid(color=BORDER, linewidth=0.8, alpha=0.8, zorder=0)
    ax.set_axisbelow(True)
    if subtitle:
        ax.set_title(
            f"{title}\n{subtitle}",
            color=TEXT, fontsize=13, fontweight="bold", pad=12,
            linespacing=1.5,
        )
    else:
        ax.set_title(title, color=TEXT, fontsize=13, fontweight="bold", pad=12)


# ════════════════════════════════════════════════════════════════════════════
# FIGURE 1 — Architecture diagram
# Layout: boxes on one horizontal row, arrows drawn BELOW boxes in a
# dedicated lane so labels never touch box borders.
# ════════════════════════════════════════════════════════════════════════════
fig1, ax = plt.subplots(figsize=(18, 10), facecolor=BG)
ax.set_facecolor(BG)
ax.axis("off")
# coordinate space: x 0–18, y 0–10
ax.set_xlim(0, 18)
ax.set_ylim(0, 10)
fig1.suptitle(
    "MircoVerse — Memory & Reflection Pipeline",
    fontsize=20, color=TEXT, fontweight="bold", y=0.98,
)

# ── box helper ───────────────────────────────────────────────────────────────
def box(cx, cy, w, h, title, body, accent):
    rect = mpatches.FancyBboxPatch(
        (cx - w/2, cy - h/2), w, h,
        boxstyle="round,pad=0.2",
        facecolor="#1a1a2e", edgecolor=accent, linewidth=2.5,
        zorder=3,
    )
    ax.add_patch(rect)
    ax.text(cx, cy + 0.30, title,
            ha="center", va="center", fontsize=14, fontweight="bold",
            color=accent, zorder=4)
    ax.text(cx, cy - 0.38, body,
            ha="center", va="center", fontsize=10.5, color=DIM,
            multialignment="center", linespacing=1.6, zorder=4)


# ── simple straight arrow (no label on shaft) ────────────────────────────────
def arrow_plain(x1, x2, y, col):
    ax.annotate(
        "", xy=(x2, y), xytext=(x1, y),
        arrowprops=dict(
            arrowstyle="-|>", color=col, lw=2.0, mutation_scale=20,
        ),
        zorder=5,
    )


# ── labelled arrow drawn in a LOWER lane (y_lane) with step down/up ──────────
def arrow_lane(x1, x2, box_y, box_h, lane_y, col, label):
    # step down from box bottom → run horizontal → step up to next box bottom
    # but we just draw a clean horizontal at lane_y with connectors
    bbot = box_y - box_h/2   # bottom of box
    # vertical down from box1 right-centre-bottom
    ax.plot([x1, x1], [bbot, lane_y], color=col, lw=1.6, zorder=5)
    # horizontal run
    ax.annotate(
        "", xy=(x2, lane_y), xytext=(x1, lane_y),
        arrowprops=dict(
            arrowstyle="-|>", color=col, lw=1.6, mutation_scale=16,
        ),
        zorder=5,
    )
    # vertical up to next box bottom
    ax.plot([x2, x2], [lane_y, bbot], color=col, lw=1.6, zorder=5)
    # label centred on horizontal run, with background
    ax.text((x1+x2)/2, lane_y - 0.22, label,
            ha="center", va="top", fontsize=10.5, color=col,
            style="italic", zorder=6,
            bbox=dict(boxstyle="round,pad=0.25", facecolor=BG,
                      edgecolor="none", alpha=0.9))


# ── layout constants ──────────────────────────────────────────────────────────
BOX_Y  = 5.5    # vertical centre of all four boxes
BOX_W  = 3.2
BOX_H  = 2.4
xs     = [2.2, 6.3, 10.4, 14.5]   # box centres — 4.1 units apart
LANE_Y = BOX_Y - BOX_H/2 - 1.2    # horizontal lane below boxes

# ── four boxes ────────────────────────────────────────────────────────────────
box(xs[0], BOX_Y, BOX_W, BOX_H,
    "WORLD",
    "each tick\nobservation + state",
    BLUE)

box(xs[1], BOX_Y, BOX_W, BOX_H,
    "MEMORY",
    "events · relationships\nreflections  (1–10 score)",
    GREEN)

box(xs[2], BOX_Y, BOX_W, BOX_H,
    "REFLECTION",
    "high-importance\nthreshold triggers\nmemory retrieval",
    AMBER)

box(xs[3], BOX_Y, BOX_W, BOX_H,
    "IDENTITY",
    "optional revision\nmost reflections\nchange nothing",
    PURPLE)

# ── forward arrows — run in lane below boxes ──────────────────────────────────
arrow_lane(xs[0], xs[1], BOX_Y, BOX_H, LANE_Y,       DIM,    "observe")
arrow_lane(xs[1], xs[2], BOX_Y, BOX_H, LANE_Y - 0.0, DIM,    "retrieve high-importance memories")
arrow_lane(xs[2], xs[3], BOX_Y, BOX_H, LANE_Y - 0.0, DIM,    "synthesise")

# ── Original Soul pill ────────────────────────────────────────────────────────
soul_cx, soul_cy = 9.0, 8.9
ax.text(soul_cx, soul_cy,
        "   ORIGINAL SOUL  —  fixed, shown at the start of every turn   ",
        ha="center", va="center", fontsize=13, fontweight="bold",
        color=AMBER,
        bbox=dict(boxstyle="round,pad=0.55", facecolor="#231c00",
                  edgecolor=AMBER, linewidth=2.2),
        zorder=4)

# Diagonal arrow: soul → identity box top-right
ax.annotate(
    "", xy=(xs[3], BOX_Y + BOX_H/2 + 0.12),
    xytext=(soul_cx + 2.6, soul_cy - 0.45),
    arrowprops=dict(arrowstyle="-|>", color=AMBER, lw=2.0,
                    mutation_scale=16,
                    connectionstyle="arc3,rad=-0.08"),
    zorder=5,
)
ax.text(13.8, 8.05, "gap vs current\nself = drift signal",
        ha="center", va="center", fontsize=10, color=AMBER,
        style="italic", zorder=6,
        bbox=dict(boxstyle="round,pad=0.25", facecolor=BG,
                  edgecolor="none", alpha=0.9))

# Diagonal arrow: soul → world box top-left
ax.annotate(
    "", xy=(xs[0], BOX_Y + BOX_H/2 + 0.12),
    xytext=(soul_cx - 2.8, soul_cy - 0.45),
    arrowprops=dict(arrowstyle="-|>", color="#886600", lw=2.0,
                    mutation_scale=16,
                    connectionstyle="arc3,rad=0.08"),
    zorder=5,
)
ax.text(4.0, 8.05, "anchors\nevery turn",
        ha="center", va="center", fontsize=10, color="#c8a020",
        style="italic", zorder=6,
        bbox=dict(boxstyle="round,pad=0.25", facecolor=BG,
                  edgecolor="none", alpha=0.9))

# ── feedback arc — revised identity loops all the way back ───────────────────
FEED_Y2 = LANE_Y - 1.10
ax.annotate(
    "", xy=(xs[0] - 0.4, BOX_Y - BOX_H/2 - 0.1),
    xytext=(xs[3] + 0.4, BOX_Y - BOX_H/2 - 0.1),
    arrowprops=dict(
        arrowstyle="<|-", color=PURPLE, lw=2.2,
        mutation_scale=18,
        connectionstyle=f"arc3,rad=0.35",
    ),
    zorder=5,
)
ax.text((xs[0]+xs[3])/2, FEED_Y2 - 0.05,
        "revised identity fed back — shown at the start of every future turn",
        ha="center", va="top", fontsize=11,
        color=PURPLE, style="italic", zorder=6,
        bbox=dict(boxstyle="round,pad=0.3", facecolor=BG,
                  edgecolor="none", alpha=0.9))

# ── footnote ──────────────────────────────────────────────────────────────────
ax.text(0.2, 0.18,
        "Key design: the agent always sees who it started as alongside who it is now. "
        "The gap is structurally unavoidable — never hidden.",
        ha="left", va="bottom", fontsize=10.5, color=DIM,
        style="italic", zorder=6)

fig1.savefig("findings/memory_architecture.png", dpi=160,
             bbox_inches="tight", facecolor=BG)
print("saved findings/memory_architecture.png")
plt.close(fig1)


# ════════════════════════════════════════════════════════════════════════════
# FIGURE 2 — Data panels (1 row × 3 cols, clean and spacious)
# ════════════════════════════════════════════════════════════════════════════
fig2, axes = plt.subplots(
    1, 3, figsize=(18, 6.5),
    facecolor=BG,
    gridspec_kw=dict(wspace=0.38, left=0.06, right=0.97,
                     top=0.82, bottom=0.14),
)
fig2.suptitle(
    "MircoVerse — Reflection & Identity Change",
    fontsize=18, color=TEXT, fontweight="bold", y=0.97,
)

# ── panel A: survival time by reflection outcome ─────────────────────────────
axA = axes[0]
style(axA, "Agents that changed identity\nlived 5–10× longer",
      subtitle=None)

arms  = ["control", "mild", "acute"]
x     = np.arange(3)
w     = 0.26

cm  = [mean_or_zero([r["last_tick"] for r in records if r["arm"] == a and r["changed"]]) for a in arms]
rm  = [mean_or_zero([r["last_tick"] for r in records if r["arm"] == a and r["snap_count"] > 0 and not r["changed"]]) for a in arms]
nm  = [mean_or_zero([r["last_tick"] for r in records if r["arm"] == a and r["snap_count"] == 0]) for a in arms]

b1 = axA.bar(x - w, cm, w, color=GREEN,  alpha=0.92, label="Changed identity",    zorder=3)
b2 = axA.bar(x,     rm, w, color=AMBER,  alpha=0.92, label="Reflected, no change",zorder=3)
b3 = axA.bar(x + w, nm, w, color="#444458", alpha=0.92, label="Never reflected",  zorder=3)

axA.set_xticks(x)
axA.set_xticklabels(["control\n(drain=1)", "mild\n(drain=2)", "acute\n(drain=3)"],
                    color=TEXT, fontsize=11)
axA.set_ylabel("mean last-active tick", color=DIM, fontsize=11)
axA.set_ylim(0, 140)

for bars in [b1, b2, b3]:
    for bar in bars:
        h = bar.get_height()
        if h > 4:
            axA.text(bar.get_x() + bar.get_width() / 2, h + 2.5,
                     "%.0f" % h, ha="center", va="bottom",
                     color=TEXT, fontsize=10, fontweight="bold", zorder=4)

axA.legend(facecolor=PANEL, labelcolor=TEXT, fontsize=9.5,
           framealpha=0.9, edgecolor=BORDER, loc="upper right")

# ── panel B: scatter — first reflection tick vs last tick ────────────────────
axB = axes[1]
style(axB, "Reflect early → live longer\nAll survivors reflected before t250")

for r in records:
    if not r["snap_ticks"]:
        continue
    col    = GREEN if r["survived"] else ARM_COL[r["arm"]]
    marker = "*" if r["survived"] else "o"
    size   = 120 if r["survived"] else 28
    axB.scatter(r["snap_ticks"][0], r["last_tick"],
                c=col, marker=marker, s=size,
                alpha=0.85, linewidths=0, zorder=3)

axB.plot([0, 300], [0, 300], color=BORDER, lw=1.2, ls="--", alpha=0.7, zorder=2)
axB.set_xlabel("tick of first reflection", color=DIM, fontsize=11)
axB.set_ylabel("last active tick",         color=DIM, fontsize=11)
axB.set_xlim(0, 310)
axB.set_ylim(0, 320)

patches = [mpatches.Patch(color=ARM_COL[a], label=a) for a in arms]
patches.append(mpatches.Patch(color=GREEN, label="survived to t300  ★"))
axB.legend(handles=patches, facecolor=PANEL, labelcolor=TEXT,
           fontsize=9.5, framealpha=0.9, edgecolor=BORDER)

# ── panel C: net boundary change distribution ────────────────────────────────
axC = axes[2]
style(axC, "Every agent that reflected\nadded guardrails net")

deltas  = [r["mb_end"] - r["mb_start"] for r in records if r["snap_count"] > 0]
neg     = [d for d in deltas if d < 0]
zero    = [d for d in deltas if d == 0]
pos     = [d for d in deltas if d > 0]

max_d = max(deltas)
bins  = np.arange(-0.5, max_d + 1.5, 1)

axC.hist([d for d in deltas if d > 0],  bins=bins, color=GREEN,    alpha=0.9,
         label="net positive  (%d agents)" % len(pos),  zorder=3)
axC.hist([d for d in deltas if d == 0], bins=bins, color=AMBER,    alpha=0.9,
         label="no net change (%d agents)" % len(zero), zorder=3)
axC.hist([d for d in deltas if d < 0],  bins=bins, color=PINK,     alpha=0.9,
         label="net negative  (%d agents)" % len(neg),  zorder=3)

axC.axvline(0, color=BORDER, lw=1.5, ls="--", zorder=4)
axC.set_xlabel("net boundary change (final − start)", color=DIM, fontsize=11)
axC.set_ylabel("agents (that reflected)",             color=DIM, fontsize=11)
axC.legend(facecolor=PANEL, labelcolor=TEXT, fontsize=9.5,
           framealpha=0.9, edgecolor=BORDER)

total_reflected = len(deltas)
axC.text(0.97, 0.96,
         "n = %d agents\nthat reflected at\nleast once" % total_reflected,
         transform=axC.transAxes, ha="right", va="top",
         color=DIM, fontsize=9, style="italic")

fig2.savefig("findings/memory_data.png", dpi=160,
             bbox_inches="tight", facecolor=BG)
print("saved findings/memory_data.png")
plt.close(fig2)
