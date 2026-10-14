# -*- coding: utf-8 -*-
"""终检：报告/README 中引用的全部关键数字 vs 数据文件，逐项断言。"""
import json
import pandas as pd

ok = fail = 0
def check(name, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1
        print(f"  PASS  {name}")
    else:
        fail += 1
        print(f"  FAIL  {name}  {detail}")

panel = json.loads(open("data/topic_year_panel.json").read())
now = pd.read_csv("data/topic_signals_nowcast.csv", index_col=0)
bt = pd.read_csv("data/backtest_detail.csv", index_col=0)
m = json.loads(open("data/backtest_metrics.json").read())
YEARS = list(range(2010, 2027))

print("== 基本面板 ==")
check("81 个主题", len(panel) == 81, f"actual {len(panel)}")
tot10 = sum(int(x["panel"]["2010"]) for x in panel)
tot25 = sum(int(x["panel"]["2025"]) for x in panel)
check("2010 总量 12.5 万", abs(tot10 - 125316) < 500, str(tot10))
check("2025 总量 20.9 万", abs(tot25 - 208804) < 500, str(tot25))
check("面板覆盖 2010-2026 共 17 年", all(all(str(y) in x["panel"] for y in YEARS) for x in panel))

print("== 4.1 榜单 ==")
t1 = now.iloc[0]
check("Top1 = T14260", now.index[0] == "T14260")
check("Top1 得分 3.22", abs(t1["score"] - 3.218) < 0.005, str(t1["score"]))
check("Top1 CAGR 66.7%", abs(t1["cagr_recent"] - 0.667) < 0.005)
check("Top1 突发 18.8", abs(t1["burst_z"] - 18.782) < 0.05)
check("Top1 2025 发文 4766", t1["scale_now"] == 4766)
t14260 = [x for x in panel if x["topic_id"] == "T14260"][0]
check("T14260: 2019=374", int(t14260["panel"]["2019"]) == 374)
check("6 年 12.7 倍", abs(4766 / 374 - 12.7) < 0.1)
check("榜单第 10 名得分 1.01", abs(now.iloc[9]["score"] - 1.014) < 0.005)

print("== 领域发现 ==")
dea = now[now["topic_name"].str.contains("DEA")]
decl = now[now["stage"] == "衰退期"]
check("DEA -0.95pp 且为衰退期主题中跌幅最大", abs(dea["share_gain"].iloc[0] + 0.950) < 0.01
      and decl["share_gain"].min() == dea["share_gain"].iloc[0])
mcdm = now[now["topic_name"].str.contains("Multi-Criteria")]
dss = now[now["topic_name"].str.contains("Decision Support")]
check("MCDM -1.19pp / DSS -0.98pp 跌幅居前", abs(mcdm["share_gain"].iloc[0] + 1.193) < 0.01
      and abs(dss["share_gain"].iloc[0] + 0.982) < 0.01)
bdt = now[now["topic_name"].str.contains("Big Data Technologies")]
check("大数据技术与应用 -0.36pp 衰退", abs(bdt["share_gain"].iloc[0] + 0.363) < 0.01
      and bdt["stage"].iloc[0] == "衰退期")
for kw in ["Queuing", "Grey System", "Simulation"]:
    r = now[now["topic_name"].str.contains(kw)]
    check(f"{kw} 处于衰退期", len(r) > 0 and r["stage"].iloc[0] == "衰退期")

print("== 4.2 回测 ==")
check("P@5=60%", abs(m["P@5_composite_score"] - 0.6) < 1e-9)
check("P@10=60% / 基线增速70% / 规模20%", (m["P@10_composite_score"], m["P@10_baseline_cagr_only"], m["P@10_baseline_size"]) == (0.6, 0.7, 0.2))
check("P@20=55%", abs(m["P@20_composite_score"] - 0.55) < 1e-9)
check("随机期望 26.5%", abs(m["prevalence"] - 0.2647) < 0.001)
check("68 主题 / 18 个实际新兴", m["n_topics_scored"] == 68 and int(bt["actual_emerging"].sum()) == 18,
      f'{m["n_topics_scored"]} / {int(bt["actual_emerging"].sum())}')
check("Spearman 0.29 p=0.016", abs(m["spearman_score_vs_realized"] - 0.29) < 0.005 and m["spearman_pvalue"] < 0.05)
check("组合 +0.52/+0.64/-0.32", abs(m["portfolio_top10_mean_real_share_gain"]["综合得分"] - 0.516) < 0.01
      and abs(m["portfolio_top10_mean_real_share_gain"]["仅近期增速"] - 0.636) < 0.01
      and abs(m["portfolio_top10_mean_real_share_gain"]["按规模"] + 0.320) < 0.01)
check("2.3 倍于随机", abs(0.6 / m["prevalence"] - 2.3) < 0.1)
check("2020 回测 Top1 = T14260 且实际新兴",
      bt.sort_values("score", ascending=False).index[0] == "T14260"
      and bool(bt.loc["T14260", "actual_emerging"]))
for fp in ["T13607", "T12101"]:
    check(f"误报案例 {fp} 在预测 Top10 且未爆发",
          fp in list(bt.sort_values("score", ascending=False).head(10).index)
          and not bool(bt.loc[fp, "actual_emerging"]))

print("== 4.3 生命周期 ==")
vc = now["stage"].value_counts()
check("萌芽4/成长5/成熟49/衰退10", (vc.get("萌芽期"), vc.get("成长期"), vc.get("成熟期"), vc.get("衰退期")) == (4, 5, 49, 10))
mg = now[now["stage"] == "萌芽期"]["share_gain"].mean()
dg = now[now["stage"] == "衰退期"]["share_gain"].mean()
check("萌芽均 +1.13pp", abs(mg - 1.13) < 0.01, f"{mg:.4f}")
check("衰退均 -0.36pp", abs(dg + 0.36) < 0.01, f"{dg:.4f}")
check("阶段与份额变化单调(萌芽>成长>成熟>衰退)",
      mg > now[now["stage"] == "成长期"]["share_gain"].mean()
      > now[now["stage"] == "成熟期"]["share_gain"].mean() > dg)

print(f"\n结果: {ok} PASS, {fail} FAIL")
raise SystemExit(1 if fail else 0)
