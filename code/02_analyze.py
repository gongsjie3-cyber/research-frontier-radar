# -*- coding: utf-8 -*-
"""
02_analyze.py
科研前沿雷达 · 信号体系 / 生命周期建模 / 回测验证

信号体系(全部由主题×年度发文面板导出, 不含任何主观打分):
  share_gain   领域内份额变化(百分点) —— 剔除学科整体膨胀, 情报学标准口径
  cagr_recent  近窗复合增速
  accel        加速度 = 近窗增速 - 前窗增速 (二阶信号)
  burst_z      突发强度 = 近3年计数相对历史基线的最大 z 值 (Kleinberg 思想简化实现)
生命周期:
  对累计发文量拟合 Logistic S 曲线, 按当前容量占比划分 萌芽/成长/成熟/衰退
回测:
  仅用 <=2020 的数据重算全部信号并打分排序, 用 2021-2025 真实份额变化做 ground truth,
  报告 Precision@K / Spearman 相关, 并与「按规模选」「按单纯增速选」两个朴素基线对比
"""
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import curve_fit
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
YEARS = list(range(2010, 2026))  # 2026 为不完整年, 仅描述不建模
MIN_SCALE = 200                  # 噪声过滤: 当年发文量下限

panel = json.loads((DATA / "topic_year_panel.json").read_text())
df = pd.DataFrame([{ "topic_id": m["topic_id"], "topic_name": m["topic_name"],
                     "subfields": " | ".join(m["subfields"]),
                     **{y: int(m["panel"].get(str(y), 0)) for y in YEARS}}
                   for m in panel])
df = df.set_index("topic_id")

field_total = df[YEARS].sum(axis=0)          # 领域年度总量(用于份额)
share = df[YEARS].div(field_total, axis=1)   # 主题份额矩阵


def cagr(v0, v1, n):
    v0, v1 = max(v0, 1), max(v1, 1)
    return (v1 / v0) ** (1.0 / n) - 1.0


def logistic(t, K, r, t0):
    return K / (1.0 + np.exp(-r * (t - t0)))


def lifecycle_stage(row, current_year=2025):
    """Logistic 拟合累计曲线 -> 生命周期阶段; 拟合失败则用增速符号回退."""
    t = np.array(YEARS, dtype=float)
    c = row[YEARS].astype(float).cumsum().values
    try:
        p0 = [c[-1] * 1.5, 0.3, 2018.0]
        bounds = ([c[-1] * 1.001, 0.01, 2010.0], [c[-1] * 50, 3.0, 2045.0])
        (K, r, t0), _ = curve_fit(logistic, t, c, p0=p0, bounds=bounds, maxfev=20000)
        pos = c[-1] / K
        y = row[YEARS].astype(float).values
        recent_slope = np.polyfit(t[-5:], y[-5:], 1)[0]
        if pos < 0.25:
            stage = "萌芽期"
        elif pos < 0.70:
            stage = "成长期"
        elif recent_slope <= 0:
            stage = "衰退期"
        else:
            stage = "成熟期"
        return stage, pos, r, t0
    except Exception:
        g = cagr(row[2021], row[2025], 4)
        stage = "成长期" if g > 0.05 else ("衰退期" if g < -0.02 else "成熟期")
        return stage, np.nan, np.nan, np.nan


def compute_signals(now_year, recent_n=4, prior_n=5, burst_n=3):
    """以 now_year 为'当下'重算全部信号(回测时 now_year=2020)."""
    y0, y1 = now_year - recent_n, now_year
    p0 = now_year - recent_n - prior_n
    base_end = now_year - burst_n
    rows = {}
    yidx = {y: i for i, y in enumerate(YEARS)}
    for tid, row in df.iterrows():
        v = row[YEARS].astype(float).values        # 位置索引, 与 YEARS 对齐
        rec_cagr = cagr(v[yidx[y0]], v[yidx[y1]], recent_n)
        pri_cagr = cagr(v[yidx[p0]], v[yidx[y0]], prior_n)
        hist = v[yidx[2010]:yidx[base_end] + 1]
        mu = hist.mean()
        sd = max(hist.std(ddof=1) if len(hist) > 1 else 0.0, 1e-9)
        burst_z = float(np.max((v[yidx[base_end] + 1:yidx[now_year] + 1] - mu) / sd))
        sg = float(share.loc[tid, y1] - share.loc[tid, y0]) * 100  # 百分点
        rows[tid] = dict(
            topic_name=row["topic_name"], subfields=row["subfields"],
            scale_now=float(v[yidx[y1]]), cagr_recent=rec_cagr, cagr_prior=pri_cagr,
            accel=rec_cagr - pri_cagr, burst_z=burst_z, share_gain=sg,
            share_now=float(share.loc[tid, y1]) * 100,
        )
    sig = pd.DataFrame(rows).T
    num_cols = ["scale_now", "cagr_recent", "cagr_prior", "accel",
                "burst_z", "share_gain", "share_now"]
    sig[num_cols] = sig[num_cols].astype(float)
    sig = sig[sig["scale_now"] >= MIN_SCALE].copy()   # 噪声过滤
    # 综合得分: 四项信号 z 标准化加权 (份额变化权重最高 —— 最稳健)
    W = dict(share_gain=0.30, accel=0.25, burst_z=0.25, cagr_recent=0.20)
    score = 0.0
    for k, w in W.items():
        z = (sig[k] - sig[k].mean()) / max(sig[k].std(ddof=0), 1e-9)
        score = score + w * z
    sig["score"] = score
    return sig.sort_values("score", ascending=False)


# ---------- 1) 当下研判 (now=2025) ----------
now = compute_signals(2025)
stages = df.apply(lifecycle_stage, axis=1, result_type="expand")
stages.columns = ["stage", "capacity_pos", "logi_r", "logi_t0"]
now = now.join(stages[["stage", "capacity_pos"]], how="left")
now.insert(0, "rank", range(1, len(now) + 1))
now.to_csv(DATA / "topic_signals_nowcast.csv", encoding="utf-8-sig")

# ---------- 2) 回测 (now=2020 -> 检验 2021-2025) ----------
bt = compute_signals(2020)
realized = pd.DataFrame({
    "real_share_gain": (share[2025] - share[2021]) * 100,
    "real_cagr": [cagr(r[2021], r[2025], 4) for _, r in df.iterrows()],
    "scale_2025": df[2025].astype(float),
})
bt = bt.join(realized, how="left")
# ground truth: 2021-2025 份额变化处于全场前 25% 且 2025 仍有规模
thresh = realized["real_share_gain"].quantile(0.75)
bt["actual_emerging"] = (bt["real_share_gain"] >= thresh) & (bt["scale_2025"] >= MIN_SCALE)

prevalence = bt["actual_emerging"].mean()
metrics = {"n_topics_scored": int(len(bt)), "prevalence": float(prevalence),
           "threshold_real_share_gain_pp": float(thresh)}
pred_sets = {
    "composite_score": bt.sort_values("score", ascending=False),
    "baseline_size": bt.sort_values("scale_now", ascending=False),
    "baseline_cagr_only": bt.sort_values("cagr_recent", ascending=False),
}
for name, ranked in pred_sets.items():
    for K in (5, 10, 15, 20):
        hit = ranked.head(K)["actual_emerging"].mean()
        metrics[f"P@{K}_{name}"] = float(hit)
rho, pval = spearmanr(bt["score"], bt["real_share_gain"])
metrics["spearman_score_vs_realized"] = float(rho)
metrics["spearman_pvalue"] = float(pval)

bt_out = bt[["topic_name", "score", "cagr_recent", "scale_now",
             "real_share_gain", "real_cagr", "actual_emerging"]]
bt_out.to_csv(DATA / "backtest_detail.csv", encoding="utf-8-sig")
(DATA / "backtest_metrics.json").write_text(json.dumps(metrics, ensure_ascii=False, indent=1))

# ---------- 3) 控制台摘要 ----------
pd.set_option("display.width", 200)
print("=== 当下(2025) Top15 新兴主题 ===")
print(now.head(15)[["topic_name", "score", "share_gain", "cagr_recent",
                    "accel", "burst_z", "scale_now", "stage"]].round(3).to_string())
print("\n=== 生命周期分布(全部81主题中有规模的) ===")
print(now["stage"].value_counts().to_string())
print("\n=== 回测指标 ===")
print(json.dumps(metrics, ensure_ascii=False, indent=1))
print("\n=== 回测: 2020年预测的 Top10 vs 实际表现 ===")
cols = ["topic_name", "score", "real_share_gain", "actual_emerging"]
print(bt.sort_values("score", ascending=False).head(10)[cols].round(3).to_string())
