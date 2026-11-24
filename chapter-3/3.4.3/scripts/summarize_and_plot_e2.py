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

    fig = plt.figure(figsize=(6.5, 6.45))
    gs = fig.add_gridspec(
        3, 2,
        height_ratios=[0.42, 1.0, 1.0],
        hspace=0.44,
        wspace=0.28,
        left=0.085,
        right=0.98,
        top=0.975,
        bottom=0.085,
    )

    leg_ax = fig.add_subplot(gs[0, :])
    leg_ax.axis("off")

    ax_a = fig.add_subplot(gs[1, 0])
    ax_b = fig.add_subplot(gs[1, 1])
    ax_c = fig.add_subplot(gs[2, 0])
    ax_d = fig.add_subplot(gs[2, 1])
    axes = [ax_a, ax_b, ax_c, ax_d]

    styles = {
        "w1": {"marker": "o", "ls": "-",  "color": "#1B4F72", "ms": 7.0, "label": "W1"},
        "w2": {"marker": "s", "ls": "--", "color": "#A93226", "ms": 6.6, "label": "W2"},
        "w3": {"marker": "^", "ls": ":",  "color": "#117864", "ms": 7.4, "label": "W3"},
    }
    offsets = {"w1": -0.15, "w2": 0.0, "w3": 0.15}
    q_gray = "#7A7A7A"
    label_halo = dict(boxstyle="round,pad=0.08", facecolor="white", edgecolor="none", alpha=0.88)

    for case in ["w1", "w2", "w3"]:
        st = styles[case]
        group = [next(r for r in query_rows if r["variant"] == v and r["case"] == case) for v in variants]
        med = [float(r["client_ms_median"]) for r in group]
        q1 = [float(r["client_ms_q1"]) for r in group]
        q3 = [float(r["client_ms_q3"]) for r in group]
        pos = [xi + offsets[case] for xi in x]
        for px, y1, y3 in zip(pos, q1, q3):
            ax_a.plot([px, px], [y1, y3], color=q_gray, linewidth=2.0, solid_capstyle="butt", zorder=2)
        ax_a.plot(
            pos, med,
            linestyle="none",
            marker=st["marker"],
            markersize=st["ms"],
            markerfacecolor="white",
            markeredgecolor=st["color"],
            markeredgewidth=1.65,
            zorder=4,
        )

    ax_a.set_yscale("log")
    ax_a.set_ylim(2.3, 52)
    ax_a.set_yticks([3, 5, 10, 20, 40])
    ax_a.set_yticklabels(["3", "5", "10", "20", "40"])
    ax_a.minorticks_off()
    ax_a.set_title("(a) Độ trễ client_ms (ms, log)", pad=8)

    for case in ["w1", "w3"]:
        st = styles[case]
        group = [next(r for r in query_rows if r["variant"] == v and r["case"] == case) for v in variants]
        pruning = [100.0 * float(r["pruning_ratio"]) for r in group]
        ax_b.plot(
            x, pruning,
            linestyle=st["ls"],
            linewidth=1.6,
            color=st["color"],
            marker=st["marker"],
            markersize=st["ms"],
            markerfacecolor="white",
            markeredgecolor=st["color"],
            markeredgewidth=1.65,
            zorder=4,
        )
        for xi, val in zip(x, pruning):
            dy = 8 if case == "w3" else -15
            ax_b.annotate(
                fmt_vi(val, 2),
                (xi, val),
                xytext=(0, dy),
                textcoords="offset points",
                ha="center",
                fontsize=10.5,
                color=st["color"],
                bbox=label_halo,
                zorder=5,
            )
    ax_b.set_ylim(99.58, 100.09)
    ax_b.set_yticks([99.6, 99.8, 100.0])
    ax_b.set_yticklabels(["99,6", "99,8", "100,0"])
    ax_b.set_title("(b) Pruning W1, W3 (%)", pad=8)

    st_w2 = styles["w2"]
    group_w2 = [next(r for r in query_rows if r["variant"] == v and r["case"] == "w2") for v in variants]
    pruning_w2 = [100.0 * float(r["pruning_ratio"]) for r in group_w2]
    ax_c.plot(
        x, pruning_w2,
        linestyle=st_w2["ls"],
        linewidth=1.6,
        color=st_w2["color"],
        marker=st_w2["marker"],
        markersize=st_w2["ms"],
        markerfacecolor="white",
        markeredgecolor=st_w2["color"],
        markeredgewidth=1.65,
        zorder=4,
    )
    for xi, val in zip(x, pruning_w2):
        ax_c.annotate(
            fmt_vi(val, 1),
            (xi, val),
            xytext=(0, 8),
            textcoords="offset points",
            ha="center",
            fontsize=11,
            color=st_w2["color"],
            bbox=label_halo,
            zorder=5,
        )
    ax_c.set_ylim(0, 100)
    ax_c.set_yticks([0, 50, 100])
    ax_c.set_yticklabels(["0", "50", "100"])
    ax_c.set_title("(c) Pruning W2 (%)", pad=8)
    ax_c.set_xlabel("index_granularity (g)")

    pk_kib = [float(r["primary_key_bytes_in_memory"]) / 1024.0 for r in costs]
    mk_kib = [float(r["marks_bytes"]) / 1024.0 for r in costs]
    bar_w = 0.35
    bars_pk = ax_d.bar(
        [xi - bar_w / 2 for xi in x],
        pk_kib,
        width=bar_w,
        facecolor="#D6E6F4",
        edgecolor="#1B4F72",
        linewidth=1.1,
        hatch="///",
        zorder=3,
    )
    bars_mk = ax_d.bar(
        [xi + bar_w / 2 for xi in x],
        mk_kib,
        width=bar_w,
        facecolor="#FAE5D3",
        edgecolor="#873600",
        linewidth=1.1,
        hatch="..",
        zorder=3,
    )
    for bar, val, col in [(b, v, "#1B4F72") for b, v in zip(bars_pk, pk_kib)] + [
        (b, v, "#873600") for b, v in zip(bars_mk, mk_kib)
    ]:
        ax_d.annotate(
            fmt_vi(val, 1),
            (bar.get_x() + bar.get_width() / 2, val),
            xytext=(0, 3),
            textcoords="offset points",
            ha="center",
            va="bottom",
            fontsize=10.5,
            color=col,
            bbox=label_halo,
            zorder=5,
        )
    ax_d.set_ylim(0, 288)
    ax_d.set_yticks([0, 125, 250])
    ax_d.set_yticklabels(["0", "125", "250"])
    ax_d.set_title("(d) Chỉ mục & marks (KiB)", pad=8)
    ax_d.set_xlabel("index_granularity (g)")

    for ax in axes:
        ax.set_xticks(x, x_labels)
        ax.set_xlim(-0.52, len(variants) - 0.48)
        ax.grid(axis="y", color="#D5D8DC", linewidth=0.7, alpha=0.85, zorder=0)

    row1_handles = [
        Line2D(
            [], [],
            color=styles[c]["color"],
            linestyle=styles[c]["ls"],
            linewidth=1.6,
            marker=styles[c]["marker"],
            markersize=styles[c]["ms"],
            markerfacecolor="white",
            markeredgecolor=styles[c]["color"],
            markeredgewidth=1.65,
            label=styles[c]["label"],
        )
        for c in ["w1", "w2", "w3"]
    ]
    row1_handles.append(
        Line2D([], [], color=q_gray, linestyle="none", marker="|", markersize=12, markeredgewidth=2.0, label="Khoảng Q1–Q3")
    )
    row2_handles = [
        Patch(facecolor="#D6E6F4", edgecolor="#1B4F72", linewidth=1.1, hatch="///", label="Primary index (RAM)"),
        Patch(facecolor="#FAE5D3", edgecolor="#873600", linewidth=1.1, hatch="..",  label="Marks (đĩa)"),
    ]

    leg1 = leg_ax.legend(
        handles=row1_handles,
        loc="center",
        bbox_to_anchor=(0.5, 0.73),
        ncol=4,
        frameon=False,
        columnspacing=1.8,
        handlelength=2.1,
        handletextpad=0.5,
        fontsize=12,
    )
    leg_ax.add_artist(leg1)
    leg_ax.legend(
        handles=row2_handles,
        loc="center",
        bbox_to_anchor=(0.5, 0.27),
        ncol=2,
        frameon=False,
        columnspacing=2.4,
        handlelength=2.0,
        handletextpad=0.55,
        fontsize=12,
    )
    leg_ax.add_patch(
        FancyBboxPatch(
            (0.01, 0.04), 0.98, 0.92,
            transform=leg_ax.transAxes,
            boxstyle="round,pad=0.015,rounding_size=0.03",
            facecolor="#F8FAFC",
            edgecolor="#CBD5E1",
            linewidth=0.9,
            zorder=-1,
            clip_on=False,
        )
    )

    DOCS_FIG_DIR.mkdir(parents=True, exist_ok=True)
    for ext, dpi_val in [("png", 450), ("svg", None), ("pdf", None)]:
        out1 = FIG_DIR / f"e2_granularity_tradeoff_v6_ver3.{ext}"
        out2 = DOCS_FIG_DIR / f"fig_3_1_e2_450dpi.{ext}"
        fig.savefig(out1, dpi=dpi_val, bbox_inches="tight", pad_inches=0.06)
        fig.savefig(out2, dpi=dpi_val, bbox_inches="tight", pad_inches=0.06)
    plt.close(fig)
    print("Regenerated E2 v6_ver3 (450 DPI) figure files.")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plot", action="store_true", help="Regenerate 450-DPI Figure 3.1 (v6_ver3)")
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
