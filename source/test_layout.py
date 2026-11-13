#!/usr/bin/env python3
# coding: utf-8
"""在用户Mac Chrome真实渲染检查：桌面/窄屏、左侧滚动不影响右侧、右答题区自滚动。"""
from pathlib import Path
import json
import re
import subprocess
import tempfile

ROOT=Path(__file__).resolve().parent.parent
HTML=(ROOT/"打开刷题系统.html").read_text(encoding="utf-8")
CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
script=r"""
<script>
window.addEventListener("load",function(){
 try{
  const aside=document.querySelector("aside");
  const paper=document.querySelector(".paper");
  const answer=document.getElementById("answerScroll");
  const main=document.querySelector("main");
  const fixed=paper.getBoundingClientRect();
  const asideBefore=aside.scrollTop;
  aside.scrollTop=500;
  const moved=aside.scrollTop;
  const after=paper.getBoundingClientRect();
  const count=view.length;
  const q=BANK.find(x=>x.type==="主观题");
  pointer=BANK.indexOf(q);
  view=BANK.slice();mode="all";revealed=true;
  render();
  const fixedBottom=document.querySelector(".paper>.actionrow").getBoundingClientRect().top;
  const beforeAnswerTop=answer.scrollTop;
  const injected=document.createElement("div");injected.style.height="1600px";injected.setAttribute("id","layoutSpacer");
  answer.appendChild(injected);
  answer.scrollTop=600;
  const answerMoved=answer.scrollTop;
  const afterScrollAside=aside.scrollTop;
  const afterBottom=document.querySelector(".paper>.actionrow").getBoundingClientRect().top;
  const metrics={
    viewport:[innerWidth,innerHeight],
    mainHeight:Math.round(main.getBoundingClientRect().height),
    bodyScroll:Math.round(document.documentElement.scrollHeight-document.documentElement.clientHeight),
    sidebarHeight:Math.round(aside.clientHeight), sidebarContent:aside.scrollHeight,
    sidebarScrollable:moved>0,
    rightY:Math.round(fixed.top), rightYAfter:Math.round(after.top),
    fixedRight:Math.abs(fixed.top-after.top)<1,
    answerHeight:Math.round(answer.clientHeight), answerScrolled:answerMoved>0,
    leftUnchanged:afterScrollAside===moved,
    actionBarFixed:Math.abs(afterBottom-fixedBottom)<1,
    type:"主观题", count,
    bodyOverflow:getComputedStyle(document.body).overflowY,
    sideOverflow:getComputedStyle(aside).overflowY,
    answerOverflow:getComputedStyle(answer).overflowY,
    mainWidth:Math.round(main.getBoundingClientRect().width),
    paperWidth:Math.round(paper.getBoundingClientRect().width),
    desktopColumns:getComputedStyle(main).gridTemplateColumns,
    gridRows:getComputedStyle(main).gridTemplateRows,
    menuHeight:Math.round(aside.getBoundingClientRect().height)
  };
  document.body.setAttribute("data-layout",JSON.stringify(metrics));
 }catch(error){document.body.setAttribute("data-layout-error",String(error.stack||error));}
});
</script>
"""
assert HTML.count("</body>")==1
with tempfile.TemporaryDirectory(prefix="zl-layout-browser-") as temp:
    page=Path(temp)/"test.html"
    page.write_text(HTML.replace("</body>",script+"</body>"),encoding="utf-8")
    for w,h in ((1400,900),(800,760),(390,844)):
        args=[
            CHROME,"--headless=new","--no-first-run","--disable-gpu",
            "--disable-background-networking",
            "--user-data-dir="+str(Path(temp)/("profile-"+str(w))),
            "--window-size="+str(w)+","+str(h),
            "--virtual-time-budget=3000","--dump-dom",
            page.as_uri()
        ]
        run=subprocess.run(args,capture_output=True,text=True,timeout=55)
        m=re.search(r'data-layout="([^"]+)"',run.stdout)
        e=re.search(r'data-layout-error="([^"]+)',run.stdout)
        if e:raise RuntimeError("Chrome error: "+e.group(1)[:600])
        assert m is not None,("Chrome did not set test metrics",w,run.stderr[-600:])
        import html
        v=json.loads(html.unescape(m.group(1)))
        print("LAYOUT",json.dumps(v,ensure_ascii=False))
        assert v["bodyOverflow"]=="hidden"
        assert v["bodyScroll"]<=1,("full document unexpectedly scrollable",v)
        assert v["sidebarScrollable"] and v["fixedRight"] and v["leftUnchanged"],v
        assert v["answerScrolled"] and v["actionBarFixed"],v
        assert v["answerOverflow"]=="auto",v
        assert v["paperWidth"]>270 and v["mainWidth"]>0,v
print("RESPONSIVE_FIXED_LAYOUT_TESTS_PASS")
