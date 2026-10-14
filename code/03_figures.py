# -*- coding: utf-8 -*-
"""
03_figures.py
科研前沿雷达 · 可视化 (4 张报告级图表)
"""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib import font_manager

ROOT = Path(__file__).resolve().parent.parent
DATA, FIG = ROOT / "data", ROOT / "figures"
FIG.mkdir(exist_ok=True)

# ---- 中文字体 ----
for name in ("PingFang SC", "Hiragino Sans GB", "Arial Unicode MS", "Heiti SC"):
    if any(name.lower() in f.name.lower() for f in font_manager.fontManager.ttflist):
        plt.rcParams["font.family"] = name
        break
plt.rcParams["axes.unicode_minus"] = False

YEARS = list(range(2010, 2026))
panel = json.loads((DATA / "topic_year_panel.json").read_text())
df = pd.DataFrame([{ "topic_id": m["topic_id"], "topic_name": m["topic_name"],
                     **{y: int(m["panel"].get(str(y), 0)) for y in YEARS}}
                   for m in panel]).set_index("topic_id")
now = pd.read_csv(DATA / "topic_signals_nowcast.csv", index_col=0)
metrics = json.loads((DATA / "backtest_metrics.json").read_text())
bt = pd.read_csv(DATA / "backtest_detail.csv", index_col=0)

STAGE_COLOR = {"萌芽期": "#e74c3c", "成长期": "#e67e22", "成熟期": "#2980b9", "衰退期": "#95a5a6"}

# ---------- 图1: 前沿雷达四象限气泡图 ----------
fig, ax = plt.subplots(figsize=(11, 7.5))
for stage, g in now.groupby("stage"):
    ax.scatter(g["share_gain"], g["cagr_recent"] * 100,
               s=np.sqrt(g["scale_now"]) * 6, alpha=0.75,
               color=STAGE_COLOR.get(stage, "#333"), label=stage, edgecolors="white", linewidths=0.6)
for tid, r in now.head(10).iterrows():
    short = r["topic_name"] if len(r["topic_name"]) <= 34 else r["topic_name"][:33] + "…"
    ax.annotate(short, (r["share_gain"], r["cagr_recent"] * 100),
                textcoords="offset points", xytext=(8, 6), fontsize=8.5, color="#222")
ax.axvline(0, color="#bbb", lw=1, ls="--"); ax.axhline(0, color="#bbb", lw=1, ls="--")
ax.set_xlabel("领域内份额变化 2021→2025（百分点）")
ax.set_ylabel("近 4 年复合增速 CAGR（%）")
ax.set_title("图1  管理科学/信息系统领域研究主题前沿雷达（2010–2025，n=68）\n气泡大小 = 2025 年发文量；右上方 = 高动量新兴主题", fontsize=12)
ax.legend(title="生命周期阶段", loc="upper left")
ax.grid(alpha=0.25)
fig.tight_layout(); fig.savefig(FIG / "fig1_radar.png", dpi=200); plt.close(fig)

# ---------- 图2: Top 新兴主题发文曲线 ----------
top_ids = list(now.head(6).index)
fig, ax = plt.subplots(figsize=(11, 6.5))
cmap = plt.cm.tab10
for i, tid in enumerate(top_ids):
    r = df.loc[tid]
    ax.plot(YEARS, r[YEARS].values, marker="o", ms=3.5, lw=1.8, color=cmap(i),
            label=f"{r['topic_name'][:38]}")
ax.set_title("图2  综合得分 Top 6 新兴主题的年度发文量轨迹（2010–2025）", fontsize=12)
ax.set_xlabel("年份"); ax.set_ylabel("年发文量（篇）")
ax.legend(fontsize=8.5); ax.grid(alpha=0.25)
ax.set_xticks(YEARS); ax.set_xticklabels(YEARS, rotation=45)
fig.tight_layout(); fig.savefig(FIG / "fig2_top_trajectories.png", dpi=200); plt.close(fig)

# ---------- 图3: 回测 Precision@K + 组合收益 ----------
ks = [5, 10, 15, 20]
comp = [metrics[f"P@{k}_composite_score"] for k in ks]
bsize = [metrics[f"P@{k}_baseline_size"] for k in ks]
bcagr = [metrics[f"P@{k}_baseline_cagr_only"] for k in ks]
prev = metrics["prevalence"]
x = np.arange(len(ks)); w = 0.26
fig, (ax, ax2) = plt.subplots(1, 2, figsize=(14, 6))
ax.bar(x - w, comp, w, label="本模型综合得分", color="#c0392b")
ax.bar(x, bcagr, w, label="基线：仅按近期增速", color="#2980b9")
ax.bar(x + w, bsize, w, label="基线：按主题规模", color="#7f8c8d")
ax.axhline(prev, color="#e67e22", ls="--", lw=1.5, label=f"随机期望（{prev:.0%}）")
for xi, v in zip(x - w, comp):
    ax.text(xi, v + 0.015, f"{v:.0%}", ha="center", fontsize=9, color="#c0392b")
ax.set_xticks(x); ax.set_xticklabels([f"P@{k}" for k in ks])
ax.set_ylim(0, 0.9); ax.set_ylabel("命中率（Top-K 中真实爆发占比）")
ax.set_title("(a) 样本外命中率 Precision@K\n"
             f"综合得分 Spearman ρ = {metrics['spearman_score_vs_realized']:.2f}（p = {metrics['spearman_pvalue']:.3f}）",
             fontsize=11)
ax.legend(fontsize=9); ax.grid(axis="y", alpha=0.25)

# (b) Top10 组合的真实份额增益
port = {}
for name, col in [("综合得分", "score"), ("仅近期增速", "cagr_recent"), ("按规模", "scale_now")]:
    port[name] = bt.sort_values(col, ascending=False).head(10)["real_share_gain"].mean()
allmean = bt["real_share_gain"].mean()
bars = ax2.bar(port.keys(), port.values(), color=["#c0392b", "#2980b9", "#7f8c8d"], width=0.55)
ax2.axhline(allmean, color="#e67e22", ls="--", lw=1.5, label=f"全场平均（{allmean:.2f} pp）")
for b, v in zip(bars, port.values()):
    ax2.text(b.get_x() + b.get_width() / 2, v + 0.02, f"+{v:.2f}" if v >= 0 else f"{v:.2f}",
             ha="center", fontsize=10)
ax2.set_ylabel("预测 Top10 组合的平均真实份额变化（百分点）")
ax2.set_title("(b) 组合视角：按各方法 2020 年预测买入 Top10\n持有至 2025 的平均真实份额增益", fontsize=11)
ax2.legend(fontsize=9); ax2.grid(axis="y", alpha=0.25)
fig.suptitle("图3  样本外回测：仅用 2010–2020 数据打分排序，检验 2021–2025 真实表现", fontsize=12.5)
fig.tight_layout(); fig.savefig(FIG / "fig3_backtest.png", dpi=200); plt.close(fig)
metrics["portfolio_top10_mean_real_share_gain"] = {k: float(v) for k, v in port.items()}
metrics["portfolio_field_mean"] = float(allmean)
(DATA / "backtest_metrics.json").write_text(json.dumps(metrics, ensure_ascii=False, indent=1))

# ---------- 图4: 生命周期 × 份额变化全景 ----------
fig, ax = plt.subplots(figsize=(11, 6.5))
order = ["萌芽期", "成长期", "成熟期", "衰退期"]
data_box, labels, colors = [], [], []
for st in order:
    g = now[now["stage"] == st]["share_gain"].dropna()
    data_box.append(g.values); labels.append(f"{st}\n(n={len(g)})")
    colors.append(STAGE_COLOR[st])
bp = ax.boxplot(data_box, tick_labels=labels, patch_artist=True, showmeans=True, widths=0.5)
for patch, c in zip(bp["boxes"], colors):
    patch.set_facecolor(c); patch.set_alpha(0.55)
for i, vals in enumerate(data_box):
    jitter = np.random.default_rng(42 + i).normal(0, 0.06, len(vals))
    ax.scatter(np.full(len(vals), i + 1) + jitter, vals, s=14, alpha=0.55, color="#222")
ax.axhline(0, color="#bbb", ls="--", lw=1)
ax.set_ylabel("领域内份额变化 2021→2025（百分点）")
ax.set_title("图4  生命周期阶段与份额变化：萌芽/成长期主题份额显著提升\n"
             f"（阶段由 Logistic S 曲线拟合累计发文量判定；n={len(now)} 个主题）", fontsize=12)
ax.grid(axis="y", alpha=0.25)
fig.tight_layout(); fig.savefig(FIG / "fig4_lifecycle.png", dpi=200); plt.close(fig)

print("figures saved:", sorted(p.name for p in FIG.glob("*.png")))
