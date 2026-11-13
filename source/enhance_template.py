#!/usr/bin/env python3
# coding: utf-8
"""根据原始页面构建：后台AI配置 + 视口固定 + 左右独立滚动。"""
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent
base=(ROOT/"升级前备份/index_template_原版.html").read_text(encoding="utf-8")
logic=(ROOT/"source/updated_app.js").read_text(encoding="utf-8")
assert base.count("/*__QUESTION_DATA__*/")==1 and logic.count("/*__QUESTION_DATA__*/")==1

style=r"""
/* 整个页面不滚动；左右内容只在各自区域内滚动 */
html,body{height:100%;width:100%;overflow:hidden}
body{height:100vh;height:100dvh;min-height:0;display:flex;flex-direction:column}
header{flex:0 0 auto}
main{flex:1 1 auto;min-height:0;height:0;width:100%;max-width:1450px;
  margin:0 auto;padding:14px 18px;display:grid;
  grid-template-columns:minmax(245px,300px) minmax(0,1fr);
  align-items:stretch;gap:18px;overflow:hidden}
aside{position:relative;top:auto;height:100%;min-height:0;max-height:none;
  overflow-y:auto;overflow-x:hidden;overscroll-behavior:contain}
#qList{max-height:none;overflow:visible}
.paper{height:100%;min-height:0;max-height:100%;min-width:0;overflow:hidden;
  display:flex;flex-direction:column;padding:18px 26px 10px}
.answerScroll{flex:1 1 auto;min-height:0;min-width:0;overflow-y:auto;
  overflow-x:hidden;overscroll-behavior:contain;overflow-wrap:anywhere;
  padding-right:8px;scrollbar-gutter:stable}
.paper>.actionrow{flex:0 0 auto;margin:0;padding:10px 0 4px;
  border-top:1px solid var(--line)}
#answerNotice{flex:0 0 auto;max-height:36px;min-height:0;
  color:var(--brand);font-size:12px;overflow:hidden}
footer{flex:0 0 auto;max-width:100%;margin:0 auto 8px;padding:0 18px;
  overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.aiReview{margin-top:12px;padding:12px;background:#f6f9fe;border-radius:9px}
.gradeHistory{margin:9px 0;border:1px solid var(--line);border-radius:8px;
  padding:9px;background:#fff}
.gradeHistory summary{cursor:pointer}
.gradeHistory p{margin:8px 0}
.miniHistory{background:#f9fbff;padding:10px 12px;border-radius:8px;line-height:2}
#diskHint{margin-top:6px}
/* 窄屏：菜单在上、答题在下，两块仍然分别滚动 */
@media(max-width:850px){
 main{grid-template-columns:minmax(0,1fr);
  grid-template-rows:minmax(130px,min(30dvh,285px)) minmax(0,1fr);
  padding:9px 12px;gap:9px}
 aside{position:relative;height:100%;min-height:0;padding:14px}
 .paper{height:100%;min-height:0;padding:14px 18px 8px}
}
@media(max-width:520px){
 header{padding:8px 12px;gap:4px}
 header h1{font-size:16px}
 header p{display:none}
 #headline{font-size:11px}
 main{grid-template-rows:minmax(120px,min(27dvh,210px)) minmax(0,1fr);
  padding:6px 8px;gap:7px}
 aside{padding:10px}
 .paper{padding:12px 13px 7px}
 .paper h2{font-size:18px}
 .paper>.actionrow{gap:5px;padding:6px 0 3px}
 .paper>.actionrow button{font-size:12px;padding:7px 9px}
 footer{display:none}
}
@media print{
 html,body{overflow:visible;height:auto}
 body{height:auto;display:block}
 main{display:block;height:auto;overflow:visible}
 aside{display:none}
 .paper,.answerScroll{overflow:visible;height:auto;max-height:none}
 footer{display:none}
}
"""
base=base.replace("</style>",style+"\n</style>",1)
assert base.count('id="wrongBtn"')==1
base=base.replace('<button id="wrongBtn">只看错题</button>',
                  '<button id="wrongBtn">错题集</button><button id="masteredBtn">已掌握错题</button>',1)
assert base.count('<div id="notify" role="status"></div>')==1
base=base.replace('<div id="notify" role="status"></div>',
 '<div id="diskHint" class="small">进度保存在本机，可手动导出备份</div>'
 '<div id="notify" role="status"></div>',1)
assert base.count('<section class="paper">')==1
base=base.replace('<section class="paper">\n<div id="qcard"></div>\n<div class="actionrow">',
 '<section class="paper">\n<div id="answerScroll" class="answerScroll">'
 '<div id="qcard"></div><div id="solutions"></div></div>\n<div class="actionrow">',1)
assert base.count('<div id="solutions"></div>')==2
base=base.replace('</div>\n<div id="solutions"></div>\n</section>',
 '</div>\n<div id="answerNotice" role="status" aria-live="polite"></div>\n</section>',1)
assert base.count('<div id="solutions"></div>')==1
base=base.replace(
 '<footer>本页面无登录、无上传、不调用外部模型或网络。进度尽力保存在浏览器本地存储；建议定期点击“导出进度”备份。Mac如限制 file:// 的持久化，题库文件本身仍可离线使用。</footer>',
 '<footer>普通刷题可离线使用。只有主动请求AI判分并确认后，才会调用本机预先配置的模型服务；进度保存在本机，请定期备份。</footer>',
 1
)
start=base.index("<script>")
end=base.index("</script>",start)+len("</script>")
base=base[:start]+"<script>\n"+logic+"\n</script>"+base[end:]
assert all(f'id="{name}"' not in base for name in ("aiSettings","aiKey","aiBase","aiModel","saveAiConfigBtn"))
assert "id=\"answerScroll\"" in base and "id=\"masteredBtn\"" in base
assert base.count("/*__QUESTION_DATA__*/")==1
(ROOT/"source/index_template.html").write_text(base,encoding="utf-8")
print("新版模板已生成：无前端AI配置，固定视口，左右独立滚动")
