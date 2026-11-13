#!/usr/bin/env python3
# coding: utf-8
"""专业单选升级版质检：题量、内容、答案分布、公司来源、历史兼容。"""
from pathlib import Path
import collections
import hashlib
import json
import re
import sqlite3
ROOT=Path(__file__).resolve().parent.parent
rows=[json.loads(x) for x in (ROOT/"中南知了_产品经理题库.jsonl").read_text().splitlines() if x.strip()]
old=[json.loads(x) for x in (ROOT/"升级前备份/20261113_单选进阶升级前/中南知了_产品经理题库.jsonl").read_text().splitlines() if x.strip()]
by_id={q["id"]:q for q in rows}
old_by_id={q["id"]:q for q in old}
assert len(rows)==1264,len(rows)
assert len({q["module_code"] for q in rows})==21
types=collections.Counter(q["type"] for q in rows)
assert types=={"单选题":604,"多选题":200,"判断题":200,"主观题":200,"实操题":60},types
codes=collections.Counter("H" if re.search(r"-H[12]$",q["id"]) else
                          "curated" if re.search(r"-C\d+$",q["id"]) and q["module_code"]!="M21" else
                          "company" if q["module_code"]=="M21" else
                          "numeric" if q["id"].startswith("ZL-N") else "other"
                          for q in rows if q["type"]=="单选题")
assert codes=={"H":400,"curated":162,"company":24,"numeric":18},codes
assert all(not q["id"].endswith("-S1") and not q["id"].endswith("-S2") for q in rows)
assert len({q["id"] for q in rows})==len(rows)
assert len({q["question"].strip() for q in rows})==len(rows)
for q in rows:
    assert q["answer"] and q["explanation"],q["id"]
    if q["type"]=="单选题":
        assert len(q["options"])==4 and len(set(q["options"]))==4,q["id"]
        assert q["answer"] in "ABCD",q["id"]
        assert len(q["question"])>=25,q["id"]
        assert len(q["explanation"])>=55 or q["id"].startswith("ZL-N"),q["id"]
    if q["module_code"]=="M21":
        assert "https://" in q["explanation"],q["id"]
        assert "不代表招聘单位真题" in q["explanation"],q["id"]
for q in rows:
    if q["type"]=="单选题":
        continue
    prior=old_by_id[q["id"]]
    for f in ("question","options","answer","rubric"):
        assert q[f]==prior[f],(q["id"],f)
for q in rows:
    if q["id"].startswith("ZL-N"):
        prior=old_by_id[q["id"]]
        for f in ("question","options","answer"):
            assert q[f]==prior[f],q["id"]
c=collections.Counter(q["answer"] for q in rows if q["type"]=="单选题")
assert all(v>90 for v in c.values()),c
with sqlite3.connect(ROOT/"中南知了_产品经理题库.sqlite") as db:
    assert db.execute("select count(*) from questions").fetchone()[0]==1264
    for q in rows:
        dbrow=db.execute("select question,answer from questions where id=?",(q["id"],)).fetchone()
        assert dbrow==(q["question"],q["answer"]),q["id"]
print(json.dumps({"总题数":len(rows),"题型":dict(types),"单选来源":dict(codes),
                  "单选正确答案分布":dict(c),
                  "题干重复":0,"多选判断主观实操题与旧版一致":"通过",
                  "旧400基础单选是否仍混入新题库":"否，备份可恢复",
                  "公司官方资料题源":"24题均包含链接"},ensure_ascii=False,indent=2))
