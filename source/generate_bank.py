#!/usr/bin/env python3
# coding: utf-8
"""中南知了智慧教育产品经理模拟笔试题库，本地离线生成器。
不调用任何网络、第三方API、模型或外部服务。
"""
from __future__ import annotations
import collections
import csv
import hashlib
import json
from pathlib import Path
import random
import re
import sqlite3

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "source"
JSONL = ROOT / "中南知了_产品经理题库.jsonl"
CSV = ROOT / "中南知了_产品经理题库.csv"
SQLITE = ROOT / "中南知了_产品经理题库.sqlite"
MD_DIR = ROOT / "分章节Markdown"
TYPE_NAMES = {"S":"单选题", "M":"多选题", "J":"判断题", "W":"主观题", "P":"实操题"}
MODULE_WEIGHT = {
    "M01": 3, "M02": 3, "M03": 3, "M04": 3, "M05": 3,
    "M06": 3, "M07": 3, "M08": 3, "M09": 3, "M10": 2,
    "M11": 3, "M12": 3, "M13": 3, "M14": 3, "M15": 3,
    "M16": 2, "M17": 2, "M18": 3, "M19": 3, "M20": 2,
}
LETTER = "ABCDEF"
ITEMS = []

def parse_cases():
    modules = collections.OrderedDict()
    current = None
    for ln, raw in enumerate((SRC / "cases.txt").read_text("utf-8").splitlines(), 1):
        line = raw.strip()
        if not line:
            continue
        if line.startswith("#"):
            name = line[1:].strip()
            code, title = name.split("|", 1)
            assert re.fullmatch(r"M\d{2}", code), (ln, code)
            assert code not in modules
            modules[code] = {"title": title, "cases": []}
            current = modules[code]
            continue
        fields = line.split("|")
        assert current is not None and len(fields) == 9, (ln, len(fields))
        assert all(f.strip() for f in fields), ln
        keys = ["concept", "scene", "good1", "good2", "good3", "bad1", "bad2", "bad3", "metric"]
        current["cases"].append(dict(zip(keys, fields)))
    assert len(modules) == 20, len(modules)
    assert all(len(m["cases"]) == 10 for m in modules.values()), {k:len(v["cases"]) for k,v in modules.items()}
    return modules

MODULES = parse_cases()

def shuffled_options(qid, pairs):
    pairs = list(pairs)
    random.Random("ZL-20261113-" + qid).shuffle(pairs)
    return [x[0] for x in pairs], "".join(LETTER[i] for i,x in enumerate(pairs) if x[1])

def add(qid, mod, topic, t, question, options, answer, explanation, rubric=None, difficulty=None, duration=None):
    assert qid not in {x["id"] for x in ITEMS}, qid
    if t in ("S","M"):
        assert 4 <= len(options) <= 6
        assert len(set(options)) == len(options), (qid, options)
        assert answer and all(a in LETTER[:len(options)] for a in answer), (qid, answer)
        if t == "S":
            assert len(answer) == 1, qid
        else:
            assert len(answer) >= 2, qid
    if t == "J":
        assert answer in ("正确", "错误")
    if t in ("W", "P"):
        assert rubric and answer == "见参考作答与评分要点"
    assert len(question) >= 25 and len(explanation) >= 25
    ITEMS.append({
        "id": qid,
        "module_code": mod,
        "module": MODULES[mod]["title"],
        "topic": topic,
        "type": TYPE_NAMES[t],
        "type_code": t,
        "difficulty": difficulty or ("基础" if t=="J" else "进阶" if t in ("S","M") else "综合"),
        "priority": "高" if MODULE_WEIGHT[mod] == 3 else "中",
        "question": question,
        "options": options,
        "answer": answer,
        "explanation": explanation,
        "rubric": rubric or [],
        "suggested_minutes": duration if duration else (1 if t=="J" else 2 if t=="S" else 3 if t=="M" else 15 if t=="W" else 45),
        "origin": ("依据2026年上市公司公告及公司招聘资料核对编写，非官方真题"
                   if mod == "M21" else "基于中南知了岗位JD及教育产品案例原创编写，非官方真题"),
    })

ESSAY_STEMS = [
    "请从用户任务和MVP角度提出解决方案，画出关键业务步骤，说明不做什么及如何验收。",
    "请诊断问题可能的成因，提出至少两项可验证假设，列出实验方式与失败兜底。",
    "请说明应收集哪些关键证据、涉及哪些用户角色与业务边界，提出可执行方案，并给出风险控制和验收指标。",
    "请规划上线前后的评测和数据监控，重点说明如何判断效果改善而非虚假增长。",
    "请解释至少两种方案的取舍，结合时间、成本、教学效果与合规风险作出建议。",
]

for mod, desc in MODULES.items():
    for i, case in enumerate(desc["cases"], 1):
        concept = case["concept"]
        scene = case["scene"]
        g1, g2, g3 = case["good1"], case["good2"], case["good3"]
        b1, b2, b3 = case["bad1"], case["bad2"], case["bad3"]
        metric = case["metric"]
        tag = f"ZL-{mod}-{i:03d}"
        # 旧版明显错误干扰项S1/S2已停用；由advanced_single_generator独立生成新ID H1/H2。
        positives = [(g1,True),(g2,True)]
        negatives = [(b1,False),(b2,False)]
        if i%3 == 0:
            positives.append((g3, True))
            negatives.append((b3, False))
        choices, ans = shuffled_options(tag+"-M", positives+negatives)
        add(tag+"-M", mod, concept, "M",
            f"【{concept}｜多选】在“{scene}”的情境下，下列哪些措施值得纳入合理的产品方案？（多选，少选、错选均不得满分）",
            choices, ans,
            f"合理措施包括：{g1}；{g2}" + (f"；{g3}" if i%3==0 else "")+
            f"。不当措施包括：{b1}；{b2}" + (f"；{b3}" if i%3==0 else "") +
            f"。判断时应联系目标结果“{metric}”，而不是只看功能或模型输出。")
        correct = (i%2 == 0)
        claim = g3 if correct else b2
        add(tag+"-J", mod, concept, "J",
            f"【{concept}｜判断】场景：{scene}。判断下述产品主张是否正确：“{claim}”。",
            [], "正确" if correct else "错误",
            (f"正确。{g3}有助于形成符合该场景的解决路径；仍应落实“{g1}”与“{g2}”，并观察“{metric}”。"
             if correct else
             f"错误。“{b2}”忽略了本场景的关键约束。更合理的方案是“{g1}”，并落实“{g2}”“{g3}”，用“{metric}”验证。"))
        rubric = [
            {"point":"指出特定用户/业务约束和问题定义", "score":20, "hint":scene},
            {"point":"给出首要方案及业务流程", "score":25, "hint":g1},
            {"point":"配套实施步骤和质量控制", "score":20, "hint":g2},
            {"point":"说明风险、边界或验证机制", "score":20, "hint":g3+"；避免："+b1},
            {"point":"提出具体数据指标与验收方法", "score":15, "hint":metric},
        ]
        answer_text = (f"【问题与目标】{scene}。\n"
                       f"【核心方案】{g1}。\n"
                       f"【实施与协作】{g2}。\n"
                       f"【风险控制】{g3}；明确避免“{b1}”“{b2}”等捷径。\n"
                       f"【验证标准】围绕“{metric}”定义分母、统计窗口、基线与改进目标；"
                       f"必要时做试点或人工复核。")
        add(tag+"-W", mod, concept, "W",
            f"【{concept}｜情景主观题】{scene}。\n"+ESSAY_STEMS[(i-1)%len(ESSAY_STEMS)],
            [], "见参考作答与评分要点", answer_text, rubric, "综合", 20)

practical_rows = []
for ln, raw in enumerate((SRC/"practicals.txt").read_text("utf-8").splitlines(), 1):
    if not raw.strip():
        continue
    fields = raw.split("|")
    assert len(fields) == 6, ("practicals",ln,len(fields))
    mod, idx, title, task, deliverables, focus = fields
    assert mod in MODULES and idx.isdigit() and 1 <= int(idx) <= 10, (ln, fields[:2])
    practical_rows.append((mod, int(idx), title, task, deliverables, focus))
assert len(practical_rows) == 60
assert all(sum(p[0]==m for p in practical_rows)==3 for m in MODULES)
for mod in MODULES:
    picks = [r for r in practical_rows if r[0] == mod]
    for n, (_, idx, title, task, deliverables, focus) in enumerate(picks, 1):
        c = MODULES[mod]["cases"][idx-1]
        rubric = [
            {"point":"完成要求的交付物与结构", "score":30, "hint":deliverables},
            {"point":"结合输入场景提出可执行的产品方案", "score":25, "hint":c["good1"]},
            {"point":"覆盖异常、边界、安全与校验", "score":20, "hint":c["good2"]+"；"+c["good3"]},
            {"point":"给出可量化的验收与评测", "score":15, "hint":c["metric"]},
            {"point":"识别不当假设并清晰说明取舍", "score":10, "hint":focus},
        ]
        add(f"ZL-{mod}-P{n:02d}", mod, title, "P",
            f"【{title}｜实操题】\n业务背景：{c['scene']}。\n任务说明：{task}。\n"
            f"要求提交：{deliverables}。\n限制条件与关注点：{focus}。\n"
            f"建议控制在45分钟内，可用文字流程图、表格、PRD片段、伪代码等方式答题。",
            [], "见参考作答与评分要点",
            f"参考交付框架：\n1. 明确问题和目标：{c['scene']}。\n"
            f"2. 按要求形成：{deliverables}。\n3. 核心解决方向：{c['good1']}。\n"
            f"4. 工程与运营机制：{c['good2']}。\n5. 异常与风险：{c['good3']}。\n"
            f"6. 关键评分点：{focus}。\n7. 验收指标：{c['metric']}。\n"
            "注意：部分实操题涉及数值计算，需单独列明计算公式、口径与必要假设。",
            rubric, "综合", 45)

# 额外的数值客观题（从实操数据中独立构题；无外部隐含前提）。
NUMERICAL = [
("M02","RICE排序","需求A的Reach=500、Impact=3、Confidence=80%、Effort=8人周。RICE分数是多少？",
 ["80","120","150","180"],"150","500×3×0.8÷8=150。先统一单位，再考虑合规门槛。"),
("M02","RICE排序","需求B的Reach=300、Impact=2、Confidence=90%、Effort=3人周。RICE分数是多少？",
 ["180","90","120","300"],"180","300×2×0.9÷3=180。数值排序并不能替代安全合规决策。"),
("M04","付费漏斗","会员页曝光10000人，付费成功360人。曝光到成功付费的转化率是多少？",
 ["3.6%","36%","0.36%","6.3%"],"3.6%","360÷10000×100%=3.6%；需确认均按去重人数统计。"),
("M04","会员页面点击率","会员页曝光10000人，点击4800人。曝光点击转化率是多少？",
 ["48%","4.8%","52%","20.8%"],"48%","4800÷10000×100%=48%。"),
("M04","留存分析","周一注册200名新用户，次日有60人回访。该批次次日留存率是多少？",
 ["12%","30%","60%","40%"],"30%","60÷200×100%=30%，注意同批次与同定义。"),
("M04","实验分析","A组有1000人，其中420人完成独立练习。该组任务完成率是多少？",
 ["4.2%","42%","58%","0.42%"],"42%","420÷1000=42%，还需将其他质量指标作为护栏。"),
("M05","CAC获客成本","渠道A花费20000元获取200名有效付费用户，CAC是多少？",
 ["200元","120元","100元","20元"],"100元","20000÷200=100元/有效付费用户，需核实获客成本范围。"),
("M05","CAC获客成本","渠道B花费12000元获取100名有效付费用户，CAC是多少？",
 ["120元","12元","100元","150元"],"120元","12000÷100=120元/有效付费用户。"),
("M05","单期贡献","渠道A获取200名付费用户，每人已实现净贡献120元，投放花费20000元。扣除投放后的已实现贡献是多少？",
 ["4000元","24000元","20000元","-4000元"],"4000元","200×120−20000=4000元；这不是用户完整生命周期价值。"),
("M10","OCR纠正率","100道题中有20道识别错误，用户成功修正其中15道；其余保持不变。最终正确题数占比是多少？",
 ["80%","85%","95%","99%"],"95%","原本80道正确，加上15道修正，最终95/100=95%。"),
("M12","检索Recall@5","一个测试集有20个问题，其中16个问题在Top5结果找到至少一条正确证据。以该题设的查询命中口径，Top5命中率是多少？",
 ["16%","55%","80%","95%"],"80%","16÷20=80%；这衡量查询层命中率，不等于逐证据的标准Recall@K。"),
("M12","检索Top1命中","同一测试集有20个问题，其中11个问题在Top1结果找到正确证据。查询层Top1命中率是多少？",
 ["45%","55%","80%","11%"],"55%","11÷20=55%；要区分Hit@1与多相关证据情况下的Recall@1。"),
("M13","Agent任务恢复","批量生成并发布25道题，前10道已确认发布，其余尚未发布。恢复任务时待发布题数是多少？",
 ["10道","15道","25道","35道"],"15道","25−10=15；须通过幂等状态核验确认前10道已发布。"),
("M14","模型错误数","人工标注1000道题，模型总体正确率为94%。错误题数是多少？",
 ["6道","94道","60道","940道"],"60道","1000×(1−0.94)=60；还要分学段、题型查看错误集中情况。"),
("M15","Token成本","输入100万Token价格2元、输出100万Token价格8元，一次请求输入4000Token输出1000Token。仅模型费用是多少？",
 ["0.016元","0.004元","0.16元","0.048元"],"0.016元","4000/1000000×2＋1000/1000000×8=0.016元。"),
("M15","Token任务成本","一次模型调用成本0.016元，一个任务平均调用3次，忽略重试和其他费用，单任务模型费用是多少？",
 ["0.016元","0.048元","0.0048元","0.48元"],"0.048元","0.016×3=0.048元，生产环境还应计入检索、OCR及失败重试费用。"),
("M15","峰值并发估算","请求达到每分钟600个，每个请求平均占用模型通道12秒，忽略额外开销。按Little定律最低平均在途请求数约是多少？",
 ["12","60","120","600"],"120","到达率10次/秒×平均服务时间12秒=120，实际容量还应留冗余。"),
("M20","学校规模复制","按每校需要20人日交付计算，20所新学校在完全不复用的情形下至少需要多少交付人日？",
 ["20人日","100人日","200人日","400人日"],"400人日","20×20=400人日，这是不复用的粗略工作量，不含协调损耗。"),
]
for i, (mod, topic, prompt, opts, result, expl) in enumerate(NUMERICAL, 1):
    pairs = [(o, o == result) for o in opts]
    assert sum(c for _,c in pairs)==1
    options, ans = shuffled_options(f"ZL-N{i:03d}", pairs)
    add(f"ZL-N{i:03d}",mod,topic,"S",f"【数据与计算｜{topic}】{prompt}", options,ans,
        f"{expl} 相关产品决策还需检查口径和业务风险。",
        difficulty="基础" if i < 11 else "进阶")

from advanced_single_generator import add_all
advanced_counts=add_all(SRC,MODULES,add,shuffled_options,MODULE_WEIGHT)
# 以知识模块→单选/多选/判断/主观/实操排序，用户打开题库先看到进阶单选。
order={"S":0,"M":1,"J":2,"W":3,"P":4}
ITEMS.sort(key=lambda q:(q["module_code"],order[q["type_code"]],q["id"]))

# ---- 数据完整性检查 ----
counts = collections.Counter(q["type"] for q in ITEMS)
expected = {"单选题":418+advanced_counts["curated"]+advanced_counts["company"],"多选题":200,"判断题":200,"主观题":200,"实操题":60}
assert advanced_counts["rewritten"]==400
assert dict(counts) == expected, (counts,expected)
assert len(ITEMS) == 1078+advanced_counts["curated"]+advanced_counts["company"]
assert len({q["id"] for q in ITEMS}) == len(ITEMS)
texts = [re.sub(r"\s+", "", q["question"]) for q in ITEMS]
assert len(set(texts)) == len(texts), "发现重复题干"
assert all(q["explanation"] and (q["answer"] or q["rubric"]) for q in ITEMS)
assert all(q["module"] and q["topic"] and q["priority"] for q in ITEMS)

ROOT.mkdir(parents=True, exist_ok=True)
MD_DIR.mkdir(exist_ok=True)
with JSONL.open("w",encoding="utf-8") as f:
    for q in ITEMS:
        f.write(json.dumps(q, ensure_ascii=False)+"\n")
with CSV.open("w",encoding="utf-8-sig",newline="") as f:
    fields=["id","module_code","module","topic","type","difficulty","priority","question",
            "A","B","C","D","E","F","answer","explanation","rubric","suggested_minutes","origin"]
    w=csv.DictWriter(f,fieldnames=fields)
    w.writeheader()
    for q in ITEMS:
        row={k:q.get(k,"") for k in fields}
        row["rubric"]=json.dumps(q["rubric"],ensure_ascii=False)
        for i, choice in enumerate(q["options"]):
            row[LETTER[i]]=choice
        w.writerow(row)

def md_question(q):
    out=[f"### {q['id']}｜{q['type']}｜{q['topic']}", "", q["question"], ""]
    for i,o in enumerate(q["options"]):
        out.append(f"- **{LETTER[i]}.** {o}")
    if q["options"]:
        out.append("")
    out += [f"**答案：{q['answer']}**", "", "**解析或参考作答：**", "", q["explanation"], ""]
    if q["rubric"]:
        out += ["**评分标准（总分100）：**", ""]
        for item in q["rubric"]:
            out.append(f"- {item['point']}（{item['score']}分）：{item['hint']}")
        out.append("")
    return "\n".join(out)

all_md = [
    "# 中南知了｜智慧教育产品经理专业笔试模拟题库",
    "",
    f"> 依据BOSS直聘岗位JD原创编写；共{len(ITEMS)}题，非官方笔试真题。知识与合规条款应以实际考试通知和权威现行文件为准。",
    "",
    "题型统计："+"；".join(f"{t}{counts[t]}" for t in TYPE_NAMES.values()),
    "",
]
for mod, desc in MODULES.items():
    items = [x for x in ITEMS if x["module_code"] == mod]
    chunk = [f"# {mod}｜{desc['title']}", "",
             f"本模块{len(items)}题：{dict(collections.Counter(x['type'] for x in items))}", ""]
    for typecode in ("S","M","J","W","P"):
        selected = [q for q in items if q["type_code"]==typecode]
        chunk += [f"## {TYPE_NAMES[typecode]}（{len(selected)}道）", ""]
        for q in selected:
            chunk.append(md_question(q))
    (MD_DIR/(mod+"_"+desc["title"].replace("/","_")+".md")).write_text("\n".join(chunk),encoding="utf-8")
    all_md.extend(chunk)
(ROOT/"全部题目与答案.md").write_text("\n".join(all_md),encoding="utf-8")

db = sqlite3.connect(SQLITE)
db.executescript("""
DROP TABLE IF EXISTS questions;
DROP TABLE IF EXISTS questions_fts;
CREATE TABLE questions (
 id TEXT PRIMARY KEY, module_code TEXT NOT NULL, module TEXT NOT NULL, topic TEXT NOT NULL,
 type TEXT NOT NULL, difficulty TEXT NOT NULL, priority TEXT NOT NULL,
 question TEXT NOT NULL, options_json TEXT NOT NULL, answer TEXT NOT NULL,
 explanation TEXT NOT NULL, rubric_json TEXT NOT NULL, suggested_minutes INTEGER NOT NULL
);
CREATE INDEX idx_q_module_type ON questions(module_code,type);
""")
for q in ITEMS:
    db.execute("INSERT INTO questions VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
       (q["id"],q["module_code"],q["module"],q["topic"],q["type"],q["difficulty"],
        q["priority"],q["question"],json.dumps(q["options"],ensure_ascii=False),
        q["answer"],q["explanation"],json.dumps(q["rubric"],ensure_ascii=False),
        q["suggested_minutes"]))
# 采用trigram分词让中文关键词可局部检索；无trigram时LIKE脚本仍可用。
try:
    db.execute("CREATE VIRTUAL TABLE questions_fts USING fts5(id UNINDEXED, module,topic,question,explanation,tokenize='trigram')")
    db.executemany("INSERT INTO questions_fts(id,module,topic,question,explanation) VALUES(?,?,?,?,?)",
        [(q["id"],q["module"],q["topic"],q["question"],q["explanation"]) for q in ITEMS])
    fts_status = "FTS5 trigram 中文全文索引"
except sqlite3.OperationalError:
    fts_status = "SQLite LIKE 中文检索（平台暂不支持trigram）"
db.commit()
assert db.execute("SELECT count(*) FROM questions").fetchone()[0]==len(ITEMS)
db.close()

template=(SRC/"index_template.html").read_text("utf-8")
packed=json.dumps(ITEMS,ensure_ascii=False,separators=(",",":")).replace("</","<\\/")
result_html=template.replace("/*__QUESTION_DATA__*/", packed)
assert "/*__QUESTION_DATA__*/" not in result_html
(ROOT/"打开刷题系统.html").write_text(result_html,encoding="utf-8")

stats={
 "date":"2026-11-13", "total":len(ITEMS),"modules":len(MODULES),
 "seed_cases":sum(len(v["cases"]) for v in MODULES.values()),
 "advanced_singles":advanced_counts,
 "difficulty_upgrade":"已替换400道基础单选为H1/H2新ID，新增人工进阶与核实企业题；旧S1/S2备份保留，避免旧答题记录错配",
 "types":dict(counts), "fts":fts_status,
 "duplicates":len(texts)-len(set(texts)),
 "sources":["用户提供的2026年11月BOSS直聘JD截图与正式公告截图",
            "https://www.cac.gov.cn/2023-07/13/c_1690898327029107.htm",
            "https://app.www.gov.cn/govdata/gov/202310/24/508651/article.html",
            "https://www.moe.gov.cn/srcsite/A16/s3342/201911/t20191122_409333.html",
            "https://www.cse.edu.cn/index/detail.html?category=31&id=4240",
            "https://www.gaoxiaojob.com/announcement/detail/440318.html",
            "https://epaper.cs.com.cn/zgzqb/html/2026-09/15/nw.D110000zgzqb_20260915_4-B064.htm",
            "https://epaper.cs.com.cn/zgzqb/html/2026-10/08/nw.D110000zgzqb_20261008_4-B013.htm"],
}
(ROOT/"题库质量报告.json").write_text(json.dumps(stats,ensure_ascii=False,indent=2),encoding="utf-8")
print(json.dumps(stats,ensure_ascii=False,indent=2))

