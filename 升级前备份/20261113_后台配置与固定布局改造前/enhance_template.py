#!/usr/bin/env python3
# coding: utf-8
"""增量构建：保持旧版页面配色与布局，只增加错题二刷和AI设置控件。"""
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent
backup=(ROOT/"升级前备份/index_template_原版.html").read_text(encoding="utf-8")
logic=(ROOT/"source/updated_app.js").read_text(encoding="utf-8")
assert "/*__QUESTION_DATA__*/" in logic

style=r"""
.aiSettings{margin-top:16px;border:1px solid var(--line);border-radius:10px;padding:10px;background:#fbfdff}
.aiSettings summary{font-weight:700;color:#205083;cursor:pointer}
.aiSettings .settingsHelp{font-size:12px;color:var(--muted);line-height:1.6;margin:7px 0}
.aiSettings input{width:100%;padding:9px 11px;border:1px solid #cdd8e6;border-radius:8px;font:inherit}
.aiSettings .label{margin:9px 0 3px}
.aiSettings .settingsButtons{display:flex;gap:6px;margin:10px 0}
.aiSettings .settingsButtons button{flex:1}
.aiReview{margin-top:12px;padding:12px;background:#f6f9fe;border-radius:9px}
.gradeHistory{margin:9px 0;border:1px solid var(--line);border-radius:8px;padding:9px;background:#fff}
.gradeHistory summary{cursor:pointer}
.gradeHistory p{margin:8px 0}
.miniHistory{background:#f9fbff;padding:10px 12px;border-radius:8px;line-height:2}
#diskHint{margin-top:6px}
"""
base=backup.replace("</style>",style+"\n</style>",1)
base=base.replace('<button id="wrongBtn">只看错题</button>',
                  '<button id="wrongBtn">错题集</button><button id="masteredBtn">已掌握错题</button>',1)
ai_panel="""<details class="aiSettings" id="aiSettings">
<summary>AI 判分设置（自有API）</summary>
<div id="aiStatus" class="settingsHelp">正在检测本机AI评分服务…</div>
<label class="label" for="aiBase">API Base URL</label>
<input id="aiBase" value="https://api.siliconflow.cn/v1" spellcheck="false" autocomplete="off">
<label class="label" for="aiModel">模型名称</label>
<input id="aiModel" value="deepseek-ai/DeepSeek-V3.2" spellcheck="false" autocomplete="off">
<label class="label" for="aiKey">API Key（密码输入框）</label>
<input id="aiKey" type="password" placeholder="只在这台Mac本地输入，留空不修改已存Key" autocomplete="new-password" spellcheck="false">
<div class="settingsButtons"><button id="saveAiConfigBtn" class="primary">保存配置</button><button id="deleteKeyBtn">清除Key</button></div>
<p class="settingsHelp">密钥写入macOS钥匙串，**不写进题库或浏览器本地存储**。仅在你点击AI判分并确认后，才把题目、参考答案、评分标准及你的作答发送到所选模型服务；可能产生API费用。</p>
</details><div id="diskHint" class="small">浏览器本地记录，可随时导出进度</div>
"""
# HTML视图内纯文本不能用Markdown**；改成普通句子
ai_panel=ai_panel.replace("**","")
base=base.replace('<div id="notify" role="status"></div>',ai_panel+'<div id="notify" role="status"></div>',1)
base=base.replace(
 '<footer>本页面无登录、无上传、不调用外部模型或网络。进度尽力保存在浏览器本地存储；建议定期点击“导出进度”备份。Mac如限制 file:// 的持久化，题库文件本身仍可离线使用。</footer>',
 '<footer>不使用AI时可完全离线刷题。仅在你主动点击AI判分并确认后，才通过本地服务向已设置的第三方模型发送该题与作答；进度保存在本机，建议定期导出JSON备份。</footer>',
 1
)
start=base.index("<script>")
end=base.index("</script>",start)+len("</script>")
base=base[:start]+"<script>\n"+logic+"\n</script>"+base[end:]
checks=["id=\"masteredBtn\"","id=\"aiSettings\"","id=\"aiScoreBtn\"","/*__QUESTION_DATA__*/"]
assert base.count("/*__QUESTION_DATA__*/")==1
assert all(x in base for x in checks[:2])
(ROOT/"source/index_template.html").write_text(base,encoding="utf-8")
print("升级模板已生成，字节数",len(base.encode("utf-8")))
