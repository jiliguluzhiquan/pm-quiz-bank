#!/usr/bin/env python3
# coding: utf-8
"""最新HTML的错题二刷回归测试，不影响用户真实进度。"""
from pathlib import Path
import html
import re
import subprocess
import tempfile

ROOT=Path(__file__).resolve().parent.parent
PAGE=(ROOT/"打开刷题系统.html").read_text(encoding="utf-8")
SCRIPT=r"""
<script>
window.addEventListener("load",function(){
 const res=[];
 try{
  window.confirm=()=>true;
  view=BANK.filter(x=>x.type==="单选题");pointer=0;revealed=false;render();
  const q=view[0], wrong=LETTERS.split("").find(x=>x!==q.answer);
  let btn=Array.from(document.querySelectorAll("#choices input")).find(x=>x.value===wrong);
  btn.click();document.getElementById("submitBtn").click();
  res.push("FIRST_WRONG:"+state(q).everWrong+":"+state(q).attempts.length);
  document.getElementById("wrongBtn").click();
  res.push("IN_WRONG:"+view.some(x=>x.id===q.id));
  document.getElementById("redoBtn").click();
  btn=Array.from(document.querySelectorAll("#choices input")).find(x=>x.value===q.answer);
  btn.click();document.getElementById("submitBtn").click();
  res.push("MASTERED:"+state(q).mastered+":"+state(q).attempts.length);
  document.getElementById("masteredBtn").click();
  res.push("IN_MASTERED:"+view.some(x=>x.id===q.id));
  document.getElementById("redoBtn").click();
  btn=Array.from(document.querySelectorAll("#choices input")).find(x=>x.value===wrong);
  btn.click();document.getElementById("submitBtn").click();
  document.getElementById("wrongBtn").click();
  res.push("RETURNED_WRONG:"+view.some(x=>x.id===q.id)+":"+state(q).attempts.length);
  res.push("ALL_ATTEMPTS_RETAINED:"+state(q).attempts.every(x=>typeof x.correct==="boolean"));
  document.body.setAttribute("data-wrongbook",res.join(";"));
 }catch(error){document.body.setAttribute("data-wrongbook-error",String(error.stack||error));}
});
</script>
"""
with tempfile.TemporaryDirectory(prefix="zl-wrongbook-") as d:
    test=Path(d)/"test.html"
    test.write_text(PAGE.replace("</body>",SCRIPT+"</body>"),encoding="utf-8")
    run=subprocess.run([
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "--headless=new","--no-first-run","--disable-gpu","--disable-background-networking",
        "--user-data-dir="+d+"/profile","--virtual-time-budget=2300",
        "--dump-dom",test.as_uri()
    ],capture_output=True,text=True,timeout=55)
    a=re.search(r'data-wrongbook="([^"]+)"',run.stdout)
    err=re.search(r'data-wrongbook-error="([^"]+)"',run.stdout)
    if err:raise RuntimeError(html.unescape(err.group(1)[:600]))
    assert a,run.stderr[-500:]
    result=html.unescape(a.group(1))
    print("WRONGBOOK",result)
    for value in ["FIRST_WRONG:true:1","IN_WRONG:true","MASTERED:true:2",
                  "IN_MASTERED:true","RETURNED_WRONG:true:3","ALL_ATTEMPTS_RETAINED:true"]:
        assert value in result,value
print("WRONGBOOK_REGRESSION_PASS")
