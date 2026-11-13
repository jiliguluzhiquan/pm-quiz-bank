#!/usr/bin/env python3
# coding: utf-8
"""使用本机Chrome对 localhost 页面、配置、主观AI判分、本地存盘进行端到端测试。不会调用真实模型。"""
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import tempfile
import threading

ROOT=Path(__file__).resolve().parent.parent
spec=importlib.util.spec_from_file_location("zl_browser_tests", ROOT/"本地AI评分服务.py")
srv=importlib.util.module_from_spec(spec)
spec.loader.exec_module(srv)

class DummyKC:
    value=None
    def get(self):return self.value
    def save(self,key):self.value=key
    def erase(self):self.value=None

def simulated_score(q,draft,cfg,key):
    assert key=="fake-test-only"
    return {
        "score":86,"max_score":100,
        "dimension_scores":[{"point":x["point"],"score":x["score"],"max":x["score"],
                            "reason":"本地测试模拟正确答案"}
                            for x in q["rubric"]],
        "strengths":["本地模拟评测"],"improvements":["继续完善产品验收指标"],
        "summary":"测试模式：模拟AI判分，不调用外部网络。",
        "scored_at":srv.now(),"model":cfg["model"]
    }

# 子页面用同一个HTTP来源加载（只存在于测试进程，不写入正式产品）
test_script=r"""
<script>
window.addEventListener("load",async function(){
 const out=[];
 const sleep=(ms)=>new Promise(res=>setTimeout(res,ms));
 try{
  window.confirm=()=>true;
  await sleep(500);
  out.push("NO_SETTINGS:"+!document.getElementById("aiSettings"));
  out.push("NO_KEY_FIELD:"+!document.getElementById("aiKey"));
  const typ=document.getElementById("typeSel");
  typ.value="主观题";
  typ.dispatchEvent(new Event("change"));
  const q=view[0];
  document.getElementById("draft").value="我会先调查学生和家长的真实需求，确定核心任务，写出MVP流程和验收标准，并做A/B测试验证学习效果。";
  document.getElementById("draft").dispatchEvent(new Event("input"));
  document.getElementById("aiScoreBtn").click();
  for(let i=0;i<70 && state(q).aiGrades.length===0;i++)await sleep(80);
  out.push("AI_GRADE:"+((state(q).aiGrades[0]||{}).score));
  out.push("AI_SAVED:"+state(q).reviewed);
  await sleep(1300);
  const resp=await fetch("/api/progress");
  const saved=await resp.json();
  out.push("DISK_SYNC:"+!!(saved.progress[q.id]&&saved.progress[q.id].aiGrades.length));
  out.push("HISTORY_UI:"+document.getElementById("aiResult").textContent.includes("86/100分"));
  document.body.setAttribute("data-e2e",out.join(";"));
 }catch(e){document.body.setAttribute("data-e2e-error",String(e.stack||e));}
});
</script>
"""
chrome="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
assert Path(chrome).exists(), "本机没有Chrome"
with tempfile.TemporaryDirectory(prefix="zl-ai-browser-e2e-") as temp:
    srv.DATA_DIR=Path(temp)
    srv.CONF_PATH=Path(temp)/"settings.json"
    srv.PROGRESS_PATH=Path(temp)/"progress.json"
    srv.KC=DummyKC()
    srv.KC.value="fake-test-only"  # 后台已经配置过的假密钥，仅在内存中
    srv.score_from_model=simulated_score
    source=(ROOT/"打开刷题系统.html").read_text()
    # 页面源代码本身仅在测试时改变端口识别，其余与正式文件相同
    http=srv.ThreadingHTTPServer((srv.HOST,0),type("TestHandler",(srv.Handler,),{
        "do_GET":lambda self: self._send(200, test_html.encode("utf-8"),"text/html; charset=utf-8")
            if self.path=="/test" else srv.Handler.do_GET(self)
    }))
    port=http.server_address[1]
    srv.PORT=port
    srv.ORIGIN=f"http://127.0.0.1:{port}"
    test_html=source.replace('location.port === "18765"',f'location.port === "{port}"')
    test_html=test_html.replace("</body>",test_script+"</body>")
    runner=threading.Thread(target=http.serve_forever,daemon=True)
    runner.start()
    try:
        result=subprocess.run([
            chrome,"--headless=new","--no-first-run","--disable-gpu",
            "--disable-background-networking",
            "--user-data-dir="+temp+"/chrome-profile",
            "--virtual-time-budget=8000","--dump-dom",
            f"http://127.0.0.1:{port}/test"
        ],capture_output=True,text=True,timeout=50)
        m=re.search(r'data-e2e="([^"]+)"',result.stdout)
        err=re.search(r'data-e2e-error="([^"]+)"',result.stdout)
        print("BROWSER_RESULT",m.group(1) if m else "NONE")
        print("BROWSER_ERROR",err.group(1)[:300] if err else "NONE")
        assert m and all(x in m.group(1) for x in [
            "NO_SETTINGS:true","NO_KEY_FIELD:true","AI_GRADE:86","AI_SAVED:true","DISK_SYNC:true","HISTORY_UI:true"
        ]), "Chrome 本机API与判分交互测试未通过"
        assert not srv.CONF_PATH.exists() or "fake-test-only" not in srv.CONF_PATH.read_text(), "Key被写入配置文件"
        assert "fake-test-only" not in srv.PROGRESS_PATH.read_text(), "Key被写入答题进度"
        print("BROWSER_SAME_ORIGIN_AI_PASS; NO_REAL_API_CALL")
    finally:
        http.shutdown()
        http.server_close()
