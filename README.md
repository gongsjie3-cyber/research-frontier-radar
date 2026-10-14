# 科研前沿雷达（Research Frontier Radar）

> Early detection of emerging research topics and lifecycle assessment, built on OpenAlex (250M+ works).
> Covers 81 research topics in Management Science / Information Systems (2010–2025), with a strictly
> out-of-sample backtest (train ≤2020 → validate 2021–2025): Precision@10 = 60% vs. 26.5% random baseline,
> Spearman ρ = 0.29 (p = 0.016). All pipelines are reproducible end-to-end (see below).

新兴研究主题早期识别与生命周期研判 —— 基于 OpenAlex 2.5 亿+ 文献数据，覆盖管理科学/信息系统领域 81 个研究主题（2010–2025）。

## 目录结构

```
code/
  01_fetch_panel.py   数据采集：OpenAlex API -> 主题×年度面板
  02_analyze.py       信号体系 + Logistic 生命周期 + 样本外回测
  03_figures.py       4 张报告级图表
data/
  topic_year_panel.csv|json   原始面板（81 主题 × 2010-2026）
  topic_signals_nowcast.csv   当下研判：全部信号/得分/排名/生命周期
  backtest_detail.csv         回测明细（2020 预测 vs 2021-2025 实际）
  backtest_metrics.json       回测指标汇总
figures/                      fig1 雷达图 / fig2 轨迹 / fig3 回测 / fig4 生命周期
report/
  项目报告.md                 完整方法、结果、局限与复现指南
  简历描述.md                 三档简历文案 + 面试应答要点
```

## 一分钟复现

```bash
pip install requests pandas numpy scipy matplotlib
python3 code/01_fetch_panel.py && python3 code/02_analyze.py && python3 code/03_figures.py
```

## 核心结果

- 2025 新兴主题 Top1：AI 与大数据对商业与社会的影响（6 年发文 12.7×）
- 回测：Precision@10 = 60%（随机基线 26.5%），Spearman ρ = 0.29（p = 0.016）
- 衰退信号：DEA、排队论、系统仿真等经典方法主题份额持续下滑
