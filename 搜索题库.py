#!/usr/bin/env python3
# coding: utf-8
"""离线关键词搜索（短中文词适用）。"""
import argparse
from pathlib import Path
import sqlite3

parser = argparse.ArgumentParser(description="中南知了产品经理题库：关键词检索")
parser.add_argument("keyword", nargs="?", default="", help="关键词，例如 RAG、错题、模型")
parser.add_argument("--type", default="", choices=["","单选题","多选题","判断题","主观题","实操题"])
parser.add_argument("--module", default="", help="例如 M18")
parser.add_argument("--limit", type=int, default=20)
args = parser.parse_args()
db = sqlite3.connect(Path(__file__).parent / "中南知了_产品经理题库.sqlite")
sql = "SELECT id,module_code,topic,type,question,answer FROM questions WHERE 1=1"
params = []
if args.keyword:
    sql += " AND (question LIKE ? OR topic LIKE ? OR explanation LIKE ? OR module LIKE ?)"
    key = "%" + args.keyword + "%"
    params += [key]*4
if args.type:
    sql += " AND type=?"
    params.append(args.type)
if args.module:
    sql += " AND module_code=?"
    params.append(args.module.upper())
sql += " ORDER BY module_code,id LIMIT ?"
params.append(max(1,min(args.limit,300)))
rows = db.execute(sql,params).fetchall()
print(f"共展示 {len(rows)} 道；关键词={args.keyword or '全部'}；题型={args.type or '全部'}；模块={args.module or '全部'}")
for qid,mod,topic,typ,q,ans in rows:
    print(f"\n{qid} | {mod} | {typ} | {topic}\n{q[:220]}\n参考答案：{ans}")
db.close()
