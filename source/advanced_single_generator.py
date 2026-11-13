#!/usr/bin/env python3
# coding: utf-8
"""为中南知了智慧教育产品经理单选题生成有区分度的新题。
只使用编辑过的本地业务案例 + 人工编写的进阶单选 + 已核实公司资料。
原400道单选在独立历史备份中，改版使用新ID避免旧作答记录与新题错配。
"""
from __future__ import annotations
from collections import Counter
from pathlib import Path
import re

def _seed_singles(modules, add, shuffled_options):
    """200个场景×2个不同阶段的问题，正确项在策略、实施、验证之间轮换。"""
    angles=[
        ("启动与关键行动",
         [
          "团队正在启动这项业务任务，要求先确定解决该场景问题的核心行动，不展开随后的实施细节或质量复盘。",
          "当前尚未选定应当如何切入该具体问题，负责人希望明确第一项最有针对性的处理方案。",
          "利益相关方提出多项看似可行的行动，但尚未建立本题问题的初始解决路径；哪项更应先落实？",
          "项目仍处于启动阶段，当前需要先确定如何正面回应题设痛点，而不是抢先开展后续评估。"
         ],
         ["偏执行步骤，并不回答当前核心方向",
          "偏验证、风险或后续约束；仍需先有方案主体",
          "当前场景的方向性路径最匹配明确任务（应选）"]),
        ("实施机制",
         [
          "产品方向已经确认，本轮研发评审最需要形成可交付的工作规则、业务流程或协作动作。",
          "现在已有业务假设和方案范围，接下来要把它转成工程和运营可落实的步骤，而非重复讨论目标。",
          "团队认同产品价值主张，但具体谁做什么、如何执行仍不明确；以下哪项能直接补上落地设计？",
          "这轮会议不再选择产品方向，也暂不讨论上线复盘，而要形成当前可执行的机制与动作。"
         ],
         ["偏战略选择，当前阶段已有明确方向",
          "偏风险/效果校验，仍需先定义实施动作",
          "将已定目标细化为可执行、可验证动作（应选）"]),
        ("风险与证据",
         [
          "首版目标和核心执行方案已有共识，发布评审要求优先补足该场景的风险控制、证据与复核机制。",
          "现在最担心方案看似成立却留下隐私、准确性或价值验证漏洞；应加强什么控制措施？",
          "功能流程已经设计完成，本轮重点是确认业务效果、质量边界与异常结果处理，哪项最匹配？",
          "产品进入验收准备阶段，团队需要避免把方案假设当成已经证实的结论；应该优先做什么？"
         ],
         ["更接近价值与主线方案，并非本轮最需要的证据/风控设计",
          "更偏具体流程执行，但质量边界仍然需要单独确定",
          "补齐质量校验、证据或边界控制（应选）"])
    ]
    total=0
    codes=list(modules.keys())
    for imod,(code,desc) in enumerate(list(modules.items())):
        cases=desc["cases"]
        for i,c in enumerate(cases,1):
            # 策略/实施/风险不同阶段的建议都是合理的，题目新增条件限定选出最适配的一项
            for j, suffix in enumerate(("H1","H2")):
                stage=(imod+i+j)%3
                stage_label,stems,reasons=angles[stage]
                other=cases[(i+2+j)%len(cases)]
                other_option=other[("good1","good2","good3")[stage]]
                correct=c[("good1","good2","good3")[stage]]
                pairs=[
                    (c["good1"],stage==0),
                    (c["good2"],stage==1),
                    (c["good3"],stage==2),
                    (other_option,False)
                ]
                qid=f"ZL-{code}-{i:03d}-{suffix}"
                opts,ans=shuffled_options(qid,pairs)
                reason_map={
                    c["good1"]:reasons[2] if stage==0 else reasons[0] if stage==1 else reasons[0],
                    c["good2"]:reasons[2] if stage==1 else reasons[0] if stage==0 else reasons[1],
                    c["good3"]:reasons[2] if stage==2 else reasons[1],
                    other_option:"专业上可能成立，但对应的是同一领域的另一业务问题，未解决本题指定约束"
                }
                assert len(set(reason_map))==4,(code,i,stage)
                explanation="；".join(f"{chr(65+k)}项：{reason_map[o]}" for k,o in enumerate(opts))
                stem=stems[(i*2+imod+j)%len(stems)]
                qtext=(f"【{c['concept']}｜{stage_label}】情境：{c['scene']}。"
                    f"{stem}四个选项均属于教育产品团队可能采用的专业措施，"
                    "但请基于当前阶段的约束选出最直接且最优先的一项。")
                add(qid,code,c["concept"],"S",qtext,opts,ans,
                    f"当前目标：{stage_label}，优选“{correct}”。"
                    f"逐项辨析：{explanation}。"
                    f"后续应以“{c['metric']}”等结果评价，而不是仅看方案是否完成。",
                    difficulty="进阶" if stage!=2 else "综合",duration=3)
                total+=1
    assert total==400,total
    return total

def _curated_singles(path, modules, add, shuffled_options):
    all_lines=[s.strip() for s in path.read_text(encoding="utf-8").splitlines() if s.strip() and not s.startswith("#")]
    counts=Counter()
    for ln,line in enumerate(all_lines,1):
        fields=line.split("|")
        assert len(fields)==8,(ln,len(fields))
        mod,topic,stem,correct,w1,w2,w3,explain=fields
        assert mod in modules,(ln,mod)
        assert all(x.strip() for x in fields),(ln,"空字段")
        counts[mod]+=1
        qid=f"ZL-{mod}-C{counts[mod]:02d}"
        opts,ans=shuffled_options(qid,[(correct,True),(w1,False),(w2,False),(w3,False)])
        explain=f"本题答案：{correct}。{explain} 其他选项虽然可能涉及相关概念，但与本题约束或统计口径不符。"
        add(qid,mod,topic,"S",
            f"【{topic}｜专业单选】{stem}",opts,ans,explain,difficulty="综合",duration=3)
    assert len(all_lines)>=160,len(all_lines)
    assert len(counts)==20 and all(x>=8 for x in counts.values()),counts
    return len(all_lines)

def _company_singles(path, modules, add, shuffled_options, module_weight):
    modules["M21"]={"title":"中南知了与出版集团背景（官方资料核实）","cases":[]}
    module_weight["M21"]=2
    lines=[s.strip() for s in path.read_text(encoding="utf-8").splitlines() if s.strip() and not s.startswith("#")]
    for i,line in enumerate(lines,1):
        fields=line.split("|")
        assert len(fields)==8,(i,len(fields))
        topic,stem,correct,w1,w2,w3,explain,url=fields
        assert url.startswith("https://"),(i,url)
        opts,ans=shuffled_options(f"ZL-M21-C{i:02d}",[(correct,True),(w1,False),(w2,False),(w3,False)])
        add(f"ZL-M21-C{i:02d}","M21",topic,"S",
            f"【公司背景与出版业务｜官方依据题】{stem}",
            opts,ans,f"答案：{correct}。{explain}【核验依据】{url}。"
            " 本题依据2026年11月13日前可核实公开资料，不代表招聘单位真题。",
            difficulty="进阶",duration=2)
    assert 20<=len(lines)<=40,len(lines)
    return len(lines)

def add_all(src,modules,add,shuffled_options,module_weight):
    stage=_seed_singles(modules,add,shuffled_options)
    curated=_curated_singles(src/"advanced_single_choice.txt",modules,add,shuffled_options)
    company=_company_singles(src/"verified_company_questions.txt",modules,add,shuffled_options,module_weight)
    return {"rewritten":stage,"curated":curated,"company":company}
