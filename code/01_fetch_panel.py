# -*- coding: utf-8 -*-
"""
01_fetch_panel.py
科研前沿雷达 · 数据采集
数据源: OpenAlex (https://openalex.org) —— 2.5亿+ 文献的开放书目库
目标: 采集「管理科学与工程/信息管理」核心子领域的全部研究主题 × 2010-2026 年度发文量面板
"""
import json
import time
from pathlib import Path

import requests

BASE = "https://api.openalex.org"
MAILTO = "research-radar@example.com"  # OpenAlex 礼貌池
HEADERS = {"User-Agent": f"research-radar/1.0 (mailto:{MAILTO})"}

# 管科/信管核心子领域 (OpenAlex subfield taxonomy)
SUBFIELDS = {
    "1802": "Information Systems and Management",
    "1803": "Management Science and Operations Research",
    "1404": "Management Information Systems",
    "1405": "Management of Technology and Innovation",
}

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
DATA.mkdir(exist_ok=True)

S = requests.Session()
S.headers.update(HEADERS)


def get(url, **params):
    params["mailto"] = MAILTO
    for attempt in range(4):
        try:
            r = S.get(url, params=params, timeout=60)
            if r.status_code == 200:
                return r.json()
            if r.status_code in (429, 500, 502, 503):
                time.sleep(2 * (attempt + 1))
                continue
            r.raise_for_status()
        except requests.RequestException:
            time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"failed after retries: {url} {params}")


def fetch_subfield_topics():
    """抓取各子领域 taxonomy 中的主题清单(含总发文量), 取并集."""
    topics = {}  # topic_id -> meta
    for sid, sname in SUBFIELDS.items():
        d = get(f"{BASE}/subfields/{sid}")
        for t in d.get("topics", []):
            tid = t["id"].rsplit("/", 1)[-1]
            if tid not in topics:
                topics[tid] = {
                    "topic_id": tid,
                    "topic_name": t["display_name"],
                    "subfields": [],
                    "works_count_total": t.get("works_count"),
                }
            topics[tid]["subfields"].append(f"{sid}:{sname}")
    return topics


def fetch_year_panel(topic_id):
    """单个主题的逐年发文量 (primary_topic 口径, 避免重复计数)."""
    d = get(
        f"{BASE}/works",
        filter=f"primary_topic.id:{topic_id},publication_year:2010-2026",
        group_by="publication_year",
    )
    return {int(g["key"]): g["count"] for g in d.get("group_by", []) if g["key"].isdigit()}


def main():
    t0 = time.time()
    topics = fetch_subfield_topics()
    print(f"主题并集: {len(topics)} 个")

    rows = []
    for i, (tid, meta) in enumerate(sorted(topics.items()), 1):
        panel = fetch_year_panel(tid)
        meta["panel"] = {str(y): panel.get(y, 0) for y in range(2010, 2027)}
        rows.append(meta)
        if i % 20 == 0 or i == len(topics):
            print(f"  [{i}/{len(topics)}] elapsed {time.time()-t0:.0f}s")
        time.sleep(0.12)  # 礼貌限速 ~8 req/s

    out = DATA / "topic_year_panel.json"
    out.write_text(json.dumps(rows, ensure_ascii=False, indent=1))
    print(f"保存 -> {out}")

    # 同时导出宽表 CSV: 每行一个主题, 每列一年
    import csv
    with open(DATA / "topic_year_panel.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        years = list(range(2010, 2027))
        w.writerow(["topic_id", "topic_name", "subfields"] + [str(y) for y in years])
        for m in rows:
            w.writerow([m["topic_id"], m["topic_name"], " | ".join(m["subfields"])]
                       + [m["panel"][str(y)] for y in years])
    print(f"保存 -> {DATA/'topic_year_panel.csv'}")


if __name__ == "__main__":
    main()
