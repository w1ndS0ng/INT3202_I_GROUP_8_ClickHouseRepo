"""Verifier and 450-DPI figure generator for chapter-3/3.4.3 (E2 — Kết quả loại bỏ granule, thời gian truy vấn và dung lượng chỉ mục)."""
import argparse
import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
RESULTS = Path(__file__).resolve().parents[1] / "results"
SUMMARY_DIR = RESULTS / "ver2_formal_30m" / "summary"
FIG_DIR = RESULTS / "ver2_formal_30m" / "figures"
DOCS_FIG_DIR = ROOT / "docs" / "figures"


def fmt_vi(val: float, decimals: int = 1) -> str:
    return f"{val:.{decimals}f}".replace(".", ",")


def make_capped_eb_handle(color: str = "#64748B"):
    from matplotlib.collections import LineCollection
    from matplotlib.container import ErrorbarContainer
    from matplotlib.lines import Line2D

    line_center = Line2D([0], [0], linestyle="none", marker="none")
    cap_bot = Line2D([0], [0], color=color, marker="_", markersize=8.0, markeredgewidth=1.4, linestyle="none")
    cap_top = Line2D([0], [0], color=color, marker="_", markersize=8.0, markeredgewidth=1.4, linestyle="none")
    barline = LineCollection([[(0, 0), (0, 1)]], colors=[color], linewidths=1.5)
    return ErrorbarContainer((line_center, (cap_bot, cap_top), (barline,)), has_xerr=False, has_yerr=True)


def redraw_e2_figure() -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib import font_manager
    from matplotlib.lines import Line2D
    from matplotlib.patches import FancyBboxPatch, Patch

    for font_dir in [Path("/mnt/c/Windows/Fonts"), Path("C:/Windows/Fonts")]:
        if font_dir.exists():
            for p in font_dir.glob("times*.ttf"):
                font_manager.fontManager.addfont(str(p))

    plt.rcParams.update({
        "font.family": "Times New Roman",
        "font.size": 12.5,
        "axes.titlesize": 13,
        "axes.titleweight": "bold",
        "axes.labelsize": 12.5,
        "legend.fontsize": 12,
        "xtick.labelsize": 12,
        "ytick.labelsize": 12,
        "axes.linewidth": 0.9,
        "xtick.major.width": 0.9,
        "ytick.major.width": 0.9,
        "svg.fonttype": "none",
    })

    with (SUMMARY_DIR / "granularity_cost_ver2.csv").open(encoding="utf-8-sig") as f:
        costs = sorted(
            [r for r in csv.DictReader(f) if r["scale"] == "30m"],
            key=lambda r: int(r["variant"][1:]),
        )
    with (SUMMARY_DIR / "queries_ver2.csv").open(encoding="utf-8-sig") as f:
        query_rows = [
            r for r in csv.DictReader(f)
            if r["experiment"] == "granularity" and r["scale"] == "30m"
        ]

    variants = [r["variant"] for r in costs]
    x_labels = [v[1:] for v in variants]
    x = list(range(len(variants)))

    fig = plt.figure(figsize=(6.5, 6.55))
    gs = fig.add_gridspec(
        3, 2,
        height_ratios=[0.42, 1.08, 1.0],
        hspace=0.44,
        wspace=0.28,
        left=0.095,
        right=0.98,
        top=0.975,
        bottom=0.085,
    )

    leg_ax = fig.add_subplot(gs[0, :])
    leg_ax.axis("off")

    top_ratio, bot_ratio = 0.85, 1.15
    gs_a = gs[1, 0].subgridspec(2, 1, height_ratios=[top_ratio, bot_ratio], hspace=0.15)
    ax_a_top = fig.add_subplot(gs_a[0])
    ax_a_bot = fig.add_subplot(gs_a[1], sharex=ax_a_top)

    ax_b = fig.add_subplot(gs[1, 1])
    ax_c = fig.add_subplot(gs[2, 0])
    ax_d = fig.add_subplot(gs[2, 1])

    styles = {
        "w1": {"marker": "o", "ls": "-",  "color": "#1B4F72", "ms": 5.0, "label": "W1"},
        "w2": {"marker": "s", "ls": "--", "color": "#A93226", "ms": 5.0, "label": "W2"},
        "w3": {"marker": "^", "ls": ":",  "color": "#117864", "ms": 5.2, "label": "W3"},
    }
    q_gray = "#64748B"
    halo = dict(boxstyle="round,pad=0.08", facecolor="white", edgecolor="none", alpha=0.88)

    # --- Panel (a) Top band: W2 ---
    st_w2 = styles["w2"]
    g_w2 = [next(r for r in query_rows if r["variant"] == v and r["case"] == "w2") for v in variants]
    med_w2 = [float(r["client_ms_median"]) for r in g_w2]
    q1_w2 = [float(r["client_ms_q1"]) for r in g_w2]
    q3_w2 = [float(r["client_ms_q3"]) for r in g_w2]
    err_w2 = [[m - l for m, l in zip(med_w2, q1_w2)], [h - m for m, h in zip(med_w2, q3_w2)]]

    ax_a_top.plot(x, med_w2, linestyle=st_w2["ls"], linewidth=1.25, color=st_w2["color"], alpha=0.85, zorder=2)
    ax_a_top.errorbar(
        x, med_w2, yerr=err_w2,
        fmt="none", ecolor=q_gray, elinewidth=1.5, capsize=4.0, capthick=1.35, zorder=3.5,
    )
    ax_a_top.plot(
        x, med_w2, linestyle="none", marker=st_w2["marker"], markersize=st_w2["ms"],
        markerfacecolor="white", markeredgecolor=st_w2["color"], markeredgewidth=1.55, zorder=4,
    )
    ax_a_top.set_ylim(29.0, 44.0)
    ax_a_top.set_yticks([30, 36, 42])
    ax_a_top.set_yticklabels(["30", "36", "42"])
    ax_a_top.spines["bottom"].set_visible(False)
    ax_a_top.tick_params(axis="x", which="both", bottom=False, top=False, labelbottom=False)
    ax_a_top.set_title("(a) Độ trễ client_ms W1–W3 (ms)", pad=8)

    # --- Panel (a) Bottom band: W1 & W3 ---
    offsets = {"w1": -0.13, "w3": 0.13}
    for case in ["w1", "w3"]:
        st = styles[case]
        group = [next(r for r in query_rows if r["variant"] == v and r["case"] == case) for v in variants]
        med = [float(r["client_ms_median"]) for r in group]
        q1 = [float(r["client_ms_q1"]) for r in group]
        q3 = [float(r["client_ms_q3"]) for r in group]
        err = [[m - l for m, l in zip(med, q1)], [h - m for m, h in zip(med, q3)]]
        pos = [xi + offsets[case] for xi in x]

        ax_a_bot.plot(pos, med, linestyle=st["ls"], linewidth=1.25, color=st["color"], alpha=0.85, zorder=2)
        ax_a_bot.errorbar(
            pos, med, yerr=err,
            fmt="none", ecolor=q_gray, elinewidth=1.5, capsize=4.0, capthick=1.35, zorder=3.5,
        )
        ax_a_bot.plot(
            pos, med, linestyle="none", marker=st["marker"], markersize=st["ms"],
            markerfacecolor="white", markeredgecolor=st["color"], markeredgewidth=1.55, zorder=4,
        )

    ax_a_bot.set_ylim(2.50, 4.85)
    ax_a_bot.set_yticks([2.8, 3.6, 4.4])
    ax_a_bot.set_yticklabels(["2,8", "3,6", "4,4"])
    ax_a_bot.spines["top"].set_visible(False)

    # Parallel diagonal break marks (//)
    dx = 0.024
    dy_base = 0.032
    dy_top = dy_base * (bot_ratio / top_ratio)
    dy_bot = dy_base
    kwargs_break = dict(color="black", linewidth=0.95, clip_on=False, zorder=10)
    for x0 in (0.0, 1.0):
        for shift in (-0.014, 0.014):
            ax_a_top.plot((x0 - dx, x0 + dx), (shift - dy_top, shift + dy_top), transform=ax_a_top.transAxes, **kwargs_break)
            ax_a_bot.plot((x0 - dx, x0 + dx), (1.0 + shift - dy_bot, 1.0 + shift + dy_bot), transform=ax_a_bot.transAxes, **kwargs_break)

    # --- Panel (b): Pruning W1, W3 (%) ---
    for case in ["w1", "w3"]:
        st = styles[case]
        group = [next(r for r in query_rows if r["variant"] == v and r["case"] == case) for v in variants]
        pruning = [100.0 * float(r["pruning_ratio"]) for r in group]
        ax_b.plot(
            x, pruning, linestyle=st["ls"], linewidth=1.6, color=st["color"],
            marker=st["marker"], markersize=7.0 if case == "w1" else 7.4,
            markerfacecolor="white", markeredgecolor=st["color"], markeredgewidth=1.65, zorder=4,
        )
        for xi, val in zip(x, pruning):
            dy = 8 if case == "w3" else -15
            ax_b.annotate(
                fmt_vi(val, 2), (xi, val), xytext=(0, dy), textcoords="offset points",
                ha="center", fontsize=10.5, color=st["color"], bbox=halo, zorder=5,
            )
    ax_b.set_ylim(99.58, 100.09)
    ax_b.set_yticks([99.6, 99.8, 100.0])
    ax_b.set_yticklabels(["99,6", "99,8", "100,0"])
    ax_b.set_title("(b) Pruning W1, W3 (%)", pad=8)

    # --- Panel (c): Pruning W2 (%) ---
    pruning_w2 = [100.0 * float(r["pruning_ratio"]) for r in g_w2]
    ax_c.plot(
        x, pruning_w2, linestyle=st_w2["ls"], linewidth=1.6, color=st_w2["color"],
        marker=st_w2["marker"], markersize=6.6,
        markerfacecolor="white", markeredgecolor=st_w2["color"], markeredgewidth=1.65, zorder=4,
    )
    for xi, val in zip(x, pruning_w2):
        ax_c.annotate(
            fmt_vi(val, 1), (xi, val), xytext=(0, 8), textcoords="offset points",
            ha="center", fontsize=11, color=st_w2["color"], bbox=halo, zorder=5,
        )
    ax_c.set_ylim(0, 100)
    ax_c.set_yticks([0, 50, 100])
    ax_c.set_yticklabels(["0", "50", "100"])
    ax_c.set_title("(c) Pruning W2 (%)", pad=8)
    ax_c.set_xlabel("index_granularity (g)")

    # --- Panel (d): Primary index & marks (KiB) ---
    pk_kib = [float(r["primary_key_bytes_in_memory"]) / 1024.0 for r in costs]
    mk_kib = [float(r["marks_bytes"]) / 1024.0 for r in costs]
    bar_w = 0.35
    bars_pk = ax_d.bar(
        [xi - bar_w / 2 for xi in x], pk_kib, width=bar_w,
        facecolor="#D6E6F4", edgecolor="#1B4F72", linewidth=1.1, hatch="///", zorder=3,
    )
    bars_mk = ax_d.bar(
        [xi + bar_w / 2 for xi in x], mk_kib, width=bar_w,
        facecolor="#FAE5D3", edgecolor="#873600", linewidth=1.1, hatch="..", zorder=3,
    )
    for bar, val, col in [(b, v, "#1B4F72") for b, v in zip(bars_pk, pk_kib)] + [
        (b, v, "#873600") for b, v in zip(bars_mk, mk_kib)
    ]:
        ax_d.annotate(
            fmt_vi(val, 1), (bar.get_x() + bar.get_width() / 2, val), xytext=(0, 3),
            textcoords="offset points", ha="center", va="bottom",
            fontsize=10.5, color=col, bbox=halo, zorder=5,
        )
    ax_d.set_ylim(0, 288)
    ax_d.set_yticks([0, 125, 250])
    ax_d.set_yticklabels(["0", "125", "250"])
    ax_d.set_title("(d) Chỉ mục & marks (KiB)", pad=8)
    ax_d.set_xlabel("index_granularity (g)")

    for ax in [ax_a_top, ax_a_bot, ax_b, ax_c, ax_d]:
        ax.set_xlim(-0.52, len(variants) - 0.48)
        ax.grid(axis="y", color="#D5D8DC", linewidth=0.7, alpha=0.85, zorder=0)
    for ax in [ax_a_bot, ax_b, ax_c, ax_d]:
        ax.set_xticks(x, x_labels)

    row1_handles = [
        Line2D(
            [], [], color=styles[c]["color"], linestyle=styles[c]["ls"], linewidth=1.6,
            marker=styles[c]["marker"], markersize=6.6 if c == "w2" else 7.0,
            markerfacecolor="white", markeredgecolor=styles[c]["color"], markeredgewidth=1.65,
            label=styles[c]["label"],
        )
        for c in ["w1", "w2", "w3"]
    ]
    row1_handles.append(make_capped_eb_handle(q_gray))
    row1_labels = ["W1", "W2", "W3", "Khoảng Q1–Q3"]

    row2_handles = [
        Patch(facecolor="#D6E6F4", edgecolor="#1B4F72", linewidth=1.1, hatch="///", label="Primary index (RAM)"),
        Patch(facecolor="#FAE5D3", edgecolor="#873600", linewidth=1.1, hatch="..",  label="Marks (đĩa)"),
    ]

    leg1 = leg_ax.legend(
        row1_handles, row1_labels,
        loc="center", bbox_to_anchor=(0.5, 0.73), ncol=4, frameon=False,
        columnspacing=1.8, handlelength=2.1, handletextpad=0.5, fontsize=12,
    )
    leg_ax.add_artist(leg1)
    leg_ax.legend(
        handles=row2_handles,
        loc="center", bbox_to_anchor=(0.5, 0.27), ncol=2, frameon=False,
        columnspacing=2.4, handlelength=2.0, handletextpad=0.55, fontsize=12,
    )
    leg_ax.add_patch(
        FancyBboxPatch(
            (0.01, 0.04), 0.98, 0.92, transform=leg_ax.transAxes,
            boxstyle="round,pad=0.015,rounding_size=0.03",
            facecolor="#F8FAFC", edgecolor="#CBD5E1", linewidth=0.9,
            zorder=-1, clip_on=False,
        )
    )

    DOCS_FIG_DIR.mkdir(parents=True, exist_ok=True)
    for ext, dpi_val in [("png", 450), ("svg", None), ("pdf", None)]:
        out1 = FIG_DIR / f"e2_granularity_tradeoff_v7_ver4.{ext}"
        out2 = DOCS_FIG_DIR / f"fig_3_1_e2_450dpi.{ext}"
        fig.savefig(out1, dpi=dpi_val, bbox_inches="tight", pad_inches=0.06)
        fig.savefig(out2, dpi=dpi_val, bbox_inches="tight", pad_inches=0.06)
    plt.close(fig)
    print("Regenerated E2 v7_ver4 (450 DPI) figure files.")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plot", action="store_true", help="Regenerate 450-DPI Figure 3.1 (v7_ver4)")
    args = parser.parse_args()
    if args.plot:
        redraw_e2_figure()

    manifest = json.loads((RESULTS / "files.sha256.json").read_text(encoding="utf-8"))
    files = sorted(
        p.relative_to(RESULTS).as_posix()
        for p in RESULTS.rglob("*")
        if p.is_file() and p.name != "files.sha256.json"
    )
    assert files == sorted(manifest.keys()), "File list mismatch against files.sha256.json!"
    for rel in files:
        digest = hashlib.sha256((RESULTS / rel).read_bytes()).hexdigest()
        assert digest == manifest[rel], f"SHA-256 mismatch for {rel}"
    print(f"[chapter-3/3.4.3] Verified {len(files)} result files (SHA-256 PASS).")


if __name__ == "__main__":
    main()
