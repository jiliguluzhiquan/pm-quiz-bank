"use strict";
const BANK = /*__QUESTION_DATA__*/;
const STORAGE_KEY = "ZL_EDU_PM_BANK_20261113_V1";
const LETTERS = "ABCDEF";
const SERVICE = (location.protocol === "http:" && location.hostname === "127.0.0.1" && location.port === "18765");
let progress={};
try {progress=JSON.parse(localStorage.getItem(STORAGE_KEY)||"{}");} catch(_){progress={};}
if(!progress || typeof progress!=="object" || Array.isArray(progress))progress={};
let view=BANK.slice(), pointer=0, mode="all", revealed=false;
let saveTimer=null, saveChain=Promise.resolve(), aiBusy=false, ready=false;
let lastRenderedQuestionId=null;
const $=id=>document.getElementById(id);
const fmtTime=s=>s?new Date(s).toLocaleString("zh-CN",{hour12:false}):"历史记录";
function html(s){return String(s==null?"":s).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;");}
function note(s){$("notify").textContent=s;if($("answerNotice"))$("answerNotice").textContent=s;setTimeout(()=>{if($("notify").textContent===s)$("notify").textContent="";if($("answerNotice")&&$("answerNotice").textContent===s)$("answerNotice").textContent="";},6000);}
function state(q){
 let p=progress[q.id];
 if(!p || typeof p!=="object" || Array.isArray(p)){p={};progress[q.id]=p;}
 if(!Array.isArray(p.answers))p.answers=[];
 if(!Array.isArray(p.attempts))p.attempts=[];
 if(!Array.isArray(p.aiGrades))p.aiGrades=[];
 if(typeof p.fav!=="boolean")p.fav=false;
 if(typeof p.draft!=="string")p.draft="";
 if(typeof p.reviewed!=="boolean")p.reviewed=false;
 if(typeof p.checked!=="boolean")p.checked=false;
 if(typeof p.correct!=="boolean")p.correct=false;
 if(typeof p.everWrong!=="boolean")p.everWrong=false;
 if(typeof p.mastered!=="boolean")p.mastered=false;
 // 兼容2026-11-13第一版的旧进度：保留第一次提交的结果，而不是重置
 if(!p.attempts.length && p.checked && ["单选题","多选题","判断题"].includes(q.type)){
   p.attempts=[{answers:p.answers.slice(),correct:p.correct,at:null,fromOldVersion:true}];
   if(!p.correct)p.everWrong=true;
   if(p.everWrong && p.correct)p.mastered=true;
 }
 if(p.attempts.some(x=>x.correct===false))p.everWrong=true;
 if(p.everWrong && p.attempts.length){
   const last=p.attempts[p.attempts.length-1];
   if(!p.repeating)p.mastered=!!last.correct;
 }
 return p;
}
function syncLocal(){try{localStorage.setItem(STORAGE_KEY,JSON.stringify(progress));}catch(_){$("notify").textContent="本地存储空间不足，请先导出进度备份";}}
function syncDisk(){
 if(!SERVICE)return;
 const snapshot=JSON.stringify({progress});
 // 串行写入，避免连续输入导致的旧数据覆盖新数据
 saveChain=saveChain.catch(()=>{}).then(async()=>{
   try{
     const response=await fetch("/api/progress",{method:"POST",headers:{"Content-Type":"application/json"},body:snapshot});
     if(!response.ok)throw Error("本机磁盘保存失败");
   }catch(_){$("diskHint").textContent="浏览器进度已保存；本机备份暂不可用，请导出JSON。";}
 });
}
function store(){
 syncLocal();
 if(SERVICE){clearTimeout(saveTimer);saveTimer=setTimeout(syncDisk,650);}
}
function pendingWrong(q){const p=progress[q.id];return !!(p&&p.everWrong&&!p.mastered);}
function solvedWrong(q){const p=progress[q.id];return !!(p&&p.everWrong&&p.mastered);}
function filterList(){
 const term=$("search").value.trim().toLowerCase(), mod=$("moduleSel").value, typ=$("typeSel").value, level=$("levelSel").value;
 return BANK.filter(q=>{
   if(mod&&q.module_code!==mod)return false;
   if(typ&&q.type!==typ)return false;
   if(level&&q.difficulty!==level)return false;
   if(mode==="wrong"&&!pendingWrong(q))return false;
   if(mode==="mastered"&&!solvedWrong(q))return false;
   if(mode==="fav"&&!(progress[q.id]&&progress[q.id].fav))return false;
   if(!term)return true;
   return [q.id,q.module,q.topic,q.question,q.answer,q.explanation].concat(q.options||[]).join(" ").toLowerCase().includes(term);
 });
}
function refresh(){if(mode!=="mock")view=filterList();pointer=0;revealed=false;render();}
function shuffle(items){const a=items.slice();for(let i=a.length-1;i>0;i--){const j=Math.floor(Math.random()*(i+1));[a[i],a[j]]=[a[j],a[i]];}return a;}
function startMock(){
 const count={"单选题":30,"多选题":15,"判断题":10,"主观题":4,"实操题":1}, chosen=[];
 Object.keys(count).forEach(t=>chosen.push(...shuffle(BANK.filter(q=>q.type===t)).slice(0,count[t])));
 view=shuffle(chosen);mode="mock";pointer=0;revealed=false;render();
 note("已抽取60道题；客观题自动判分，主观与实操题可AI评分或自评。");
}
function calcStats(){
 const attempts=BANK.filter(q=>progress[q.id] && (progress[q.id].checked || (progress[q.id].attempts||[]).length || progress[q.id].reviewed || (progress[q.id].aiGrades||[]).length));
 const objective=BANK.filter(q=>["单选题","多选题","判断题"].includes(q.type)&&progress[q.id]&&(progress[q.id].attempts||[]).length);
 const latestCorrect=objective.filter(q=>progress[q.id].attempts.at(-1).correct).length;
 const wrong=BANK.filter(pendingWrong).length, mastered=BANK.filter(solvedWrong).length;
 $("statline").textContent="已练 "+attempts.length+" / "+BANK.length+
   " · 最近一次答对 "+latestCorrect+"/"+objective.length+
   " · 待复习错题 "+wrong+" · 已掌握错题 "+mastered+
   " · 当前 "+view.length+" 道";
 $("meterfill").style.width=(100*attempts.length/BANK.length)+"%";
 $("headline").textContent="已完成 "+attempts.length+" 道 / "+BANK.length+" 道";
 $("wrongBtn").textContent="错题集（"+wrong+"）";
 $("masteredBtn").textContent="已掌握错题（"+mastered+"）";
}
function renderList(){
 const el=$("qList");el.innerHTML="";
 if(!view.length)return;
 const start=Math.max(0,pointer-30),subset=view.length>95?view.slice(start,Math.min(view.length,pointer+65)):view;
 subset.forEach((q,i)=>{
   const pos=(view.length>95?start:0)+i,p=progress[q.id]||{};
   const b=document.createElement("button");b.className="jump"+(pos===pointer?" on":"");
   b.textContent=(pos+1)+". "+q.type+" | "+q.topic+(p.everWrong? (p.mastered?" ✓":" ×"):"")+(p.fav?" ★":"");
   b.title=q.question.slice(0,75);
   b.onclick=()=>{pointer=pos;revealed=false;render();window.scrollTo({top:0,behavior:"smooth"});};
   el.appendChild(b);
 });
}
function renderHistory(p){
 if(!p.attempts || !p.attempts.length)return "";
 const lines=p.attempts.map((a,i)=>'<span class="tag '+(a.correct?"accent":"high")+'">第'+(i+1)+'次：'+(a.correct?"正确":"错误")+(a.at?" · "+html(fmtTime(a.at)):"")+'</span>').join(" ");
 return '<div class="miniHistory"><strong>历史作答：</strong> '+lines+'</div>';
}
function renderAiHistory(p){
 if(!p.aiGrades.length)return '<div class="small">尚无AI评分记录，按现有100分评分标准进行练习。</div>';
 let s='<div class="aiReview"><strong>AI评分记录（最新优先，非官方成绩）</strong>';
 p.aiGrades.slice().reverse().forEach(g=>{
   s+='<details class="gradeHistory"><summary><strong>'+html(g.score)+'/100分</strong> · '+html(g.model||"AI")+' · '+html(fmtTime(g.scored_at))+'</summary>';
   s+='<p class="small">评分时作答摘要：'+html(g.answer_excerpt||"")+'</p>';
   s+='<p>'+html(g.summary||"")+'</p>';
   if(g.dimension_scores&&g.dimension_scores.length){
     s+='<ol class="rubric">'+g.dimension_scores.map(d=>'<li><strong>'+html(d.point)+'：'+html(d.score)+'/'+html(d.max)+'分</strong> · '+html(d.reason)+'</li>').join("")+'</ol>';
   }
   if(g.strengths&&g.strengths.length)s+='<p><strong>做得好的：</strong>'+html(g.strengths.join("；"))+'</p>';
   if(g.improvements&&g.improvements.length)s+='<p><strong>改进建议：</strong>'+html(g.improvements.join("；"))+'</p>';
   s+='</details>';
 });
 return s+'</div>';
}
function render(){
 calcStats();renderList();$("solutions").innerHTML="";
 if(!view.length){$("qcard").innerHTML="<h2>没有符合条件的题目</h2><p>可返回全题库，或改用其他筛选项。</p>";return;}
 pointer=Math.min(Math.max(0,pointer),view.length-1);
 const q=view[pointer],p=state(q),isObj=["单选题","多选题","判断题"].includes(q.type),many=q.type==="多选题";
 if(lastRenderedQuestionId!==q.id){if($("answerScroll"))$("answerScroll").scrollTop=0;lastRenderedQuestionId=q.id;}
 let text='<div class="tags"><span class="tag accent">'+html(q.module_code+" · "+q.module)+'</span><span class="tag">'+html(q.type)+'</span><span class="tag">'+html(q.difficulty)+'</span>'+(q.priority==="高"?'<span class="tag high">重点</span>':'')+'<span class="tag">'+(pointer+1)+' / '+view.length+'</span><span class="tag">建议'+q.suggested_minutes+'分钟</span></div>';
 text+='<h2>'+html(q.topic)+'</h2><div class="scene">'+html(q.question)+'</div>';
 if(isObj){
   const opts=q.type==="判断题"?["正确","错误"]:q.options;
   text+='<div id="choices">';
   opts.forEach((o,i)=>{
     const code=q.type==="判断题"?o:LETTERS[i],selected=p.answers.includes(code);
     text+='<label class="option"><input type="'+(many?"checkbox":"radio")+'" name="ans" value="'+html(code)+'" '+(selected?"checked":"")+' '+(p.checked?"disabled":"")+'><span><strong>'+(q.type==="判断题"?"":code+". ")+'</strong>'+html(o)+'</span></label>';
   });
   text+='</div><div class="actionrow"><button class="primary" id="submitBtn" '+(p.checked?"disabled":"")+'>提交答案并判分</button>';
   if(p.attempts.length||p.checked)text+='<button id="redoBtn">↻ 重新作答</button>';
   if(p.checked)text+='<span class="grade '+(p.correct?"good":"bad")+'">'+(p.correct?"已答对 ✓":"已答错 ×")+'</span>';
   if(p.everWrong)text+='<span class="tag '+(p.mastered?"accent":"high")+'">'+(p.mastered?"已掌握 · 保留记录":"待复习错题")+'</span>';
   text+='</div>'+renderHistory(p);
 }else{
   text+='<h3>请在这里记录你的解题思路或交付结构</h3><textarea id="draft" placeholder="可写PRD摘要、业务流程、方案取舍、计算或伪代码；不会在未点击AI判分时上传任何答案。">'+html(p.draft)+'</textarea>';
   text+='<div class="actionrow"><button id="reviewBtn" class="primary">'+(p.reviewed?"已标记完成 ✓":"标记已完成")+'</button><button id="aiScoreBtn">AI判分（自有API）</button><span class="small">AI按本题100分评分要点打分，可重复提交、比较提升。</span></div>';
   text+='<div id="aiResult">'+renderAiHistory(p)+'</div>';
 }
 $("qcard").innerHTML=text;
 const inputs=document.querySelectorAll("#choices input");
 inputs.forEach(node=>node.addEventListener("change",()=>{
   if(p.checked)return;
   p.answers=Array.from(document.querySelectorAll("#choices input:checked")).map(x=>x.value);
   store();
 }));
 if(isObj){
   $("submitBtn").onclick=()=>{
     const chosen=(p.answers||[]).slice().sort().join("");
     if(!chosen){note("请先选择答案");return;}
     const correct=q.type==="判断题"
       ?(p.answers.length===1 && p.answers[0]===q.answer)
       :(chosen===q.answer.split("").sort().join(""));
     p.checked=true;p.correct=correct;
     const stamp=new Date().toISOString();
     p.lastAttemptAt=stamp;
     p.attempts.push({answers:p.answers.slice(),correct,at:stamp});
     if(!correct)p.everWrong=true;
     if(p.everWrong)p.mastered=correct;
     p.repeating=false;
     store();revealed=true;render();
   };
   if($("redoBtn"))$("redoBtn").onclick=()=>{
     if(!window.confirm("重新作答不会删除历史成绩，确定继续？"))return;
     p.checked=false;p.answers=[];p.repeating=true;p.correct=false;
     if(p.everWrong)p.mastered=false;
     store();revealed=false;render();note("已进入重练，请重新选择并提交答案");
   };
 }else{
   $("draft").oninput=e=>{p.draft=e.target.value;store();};
   $("reviewBtn").onclick=()=>{p.reviewed=true;store();render();};
   $("aiScoreBtn").onclick=()=>scoreWithAI(q,p);
 }
 $("bookBtn").textContent=p.fav?"★ 已收藏":"☆ 收藏";
 if(revealed||p.checked)showSolution(q);
}
function showSolution(q){
 let s='<div class="answer"><h3>参考答案与解析</h3>';
 if(q.options.length||q.type==="判断题")s+='<p><strong>正确答案：</strong>'+html(q.answer)+'</p>';
 s+='<div class="answerBody">'+html(q.explanation)+'</div>';
 if(q.rubric&&q.rubric.length){
   s+='<h3>评分标准（共100分）</h3><ol class="rubric">'+q.rubric.map(x=>'<li><strong>'+html(x.point)+'（'+x.score+'分）</strong>：'+html(x.hint)+'</li>').join("")+'</ol>';
 }
 s+='<p class="small">模拟题参考答案不代表中南知了官方标准，也不是唯一可行解。</p></div>';
 $("solutions").innerHTML=s;
}
async function api(path,payload){
 const r=await fetch(path,{method:payload?"POST":"GET",headers:payload?{"Content-Type":"application/json"}:{},body:payload?JSON.stringify(payload):undefined,credentials:"omit"});
 let response={};
 try{response=await r.json();}catch(_){throw Error("本机服务没有返回有效JSON");}
 if(!r.ok||response.error)throw Error(response.error||"请求失败，状态码"+r.status);
 return response;
}
async function scoreWithAI(q,p){
 if(!SERVICE){note("AI判分需通过“开始刷题.command”打开的本机页面使用。");return;}
 const draft=$("draft").value.trim();
 if(draft.length<20){note("请先写至少20字的完整作答，再调用AI判分");return;}
 if(aiBusy)return;
 if(!window.confirm("本次AI判分会将题目、参考评分标准和你的作答发送到所设置的第三方模型服务，可能产生API费用。确定提交？"))return;
 p.draft=draft;store();aiBusy=true;
 const button=$("aiScoreBtn");button.disabled=true;button.textContent="AI正在评分…";
 try{
   const payload=await api("/api/ai/score",{id:q.id,draft});
   const grade={...payload.result,answer_excerpt:draft.slice(0,400),answer_length:draft.length};
   if(!Array.isArray(p.aiGrades))p.aiGrades=[];
   p.aiGrades.push(grade);
   if(p.aiGrades.length>20)p.aiGrades=p.aiGrades.slice(-20);
   p.reviewed=true;store();
   if(view[pointer]&&view[pointer].id===q.id)render();
   note("AI评分完成："+grade.score+"/100分；可在评分记录展开查看各项扣分");
 }catch(e){note("AI评分未完成："+e.message);}
 finally{
   aiBusy=false;
   if($("aiScoreBtn")){$("aiScoreBtn").disabled=false;$("aiScoreBtn").textContent="AI判分（自有API）";}
 }
}
function mergeProgress(remote,local){
 const result={...remote};
 for(const [id,p] of Object.entries(local)){
   if(!BANK_IDS.has(id))continue;
   const a=result[id];
   if(!a){result[id]=p;continue;}
   const scoreA=(a.attempts||[]).length+(a.aiGrades||[]).length;
   const scoreB=(p.attempts||[]).length+(p.aiGrades||[]).length;
   const la=a.lastAttemptAt||"",lb=p.lastAttemptAt||"";
   let chosen=(scoreB>scoreA || (scoreB===scoreA&&lb>la))?p:a;
   chosen={...chosen,fav:!!(a.fav||p.fav),reviewed:!!(a.reviewed||p.reviewed)};
   result[id]=chosen;
 }
 return result;
}
const BANK_IDS=new Set(BANK.map(q=>q.id));
async function hydrateProgress(){
 if(!SERVICE)return;
 try{
   const res=await api("/api/progress");
   const remote=res.progress&&typeof res.progress==="object"?res.progress:{};
   progress=mergeProgress(remote,progress);
   syncLocal();render();
   syncDisk();
   $("diskHint").textContent="进度同步至浏览器及Mac本地备份";
 }catch(_){$("diskHint").textContent="本机进度同步不可用；仍可使用浏览器保存和手动导出";}
}
$("moduleSel").innerHTML='<option value="">所有知识模块</option>'+Object.keys(BANK.reduce((a,q)=>(a[q.module_code]=q.module,a),{})).sort().map(k=>'<option value="'+k+'">'+k+" · "+html(BANK.find(q=>q.module_code===k).module)+'</option>').join("");
$("allcount").textContent=BANK.length;
["search","moduleSel","typeSel","levelSel"].forEach(id=>$(id).addEventListener(id==="search"?"input":"change",()=>{mode="all";refresh();}));
$("allBtn").onclick=()=>{mode="all";refresh();};
$("mockBtn").onclick=startMock;
$("wrongBtn").onclick=()=>{mode="wrong";refresh();};
$("masteredBtn").onclick=()=>{mode="mastered";refresh();};
$("favBtn").onclick=()=>{mode="fav";refresh();};
$("clearBtn").onclick=()=>{$("search").value="";["moduleSel","typeSel","levelSel"].forEach(id=>$(id).value="");mode="all";refresh();};
$("shuffleBtn").onclick=()=>{if(!view.length)return;pointer=Math.floor(Math.random()*view.length);revealed=false;render();};
$("prevBtn").onclick=()=>{if(pointer>0){pointer--;revealed=false;render();window.scrollTo(0,0);}};
$("nextBtn").onclick=()=>{if(pointer<view.length-1){pointer++;revealed=false;render();window.scrollTo(0,0);}};
$("revealBtn").onclick=()=>{if(!view.length)return;revealed=!revealed;render();};
$("bookBtn").onclick=()=>{if(!view.length)return;const p=state(view[pointer]);p.fav=!p.fav;store();render();};
$("exportBtn").onclick=()=>{
 const blob=new Blob([JSON.stringify({date:new Date().toISOString(),version:2,progress},null,2)],{type:"application/json"});
 const url=URL.createObjectURL(blob),a=document.createElement("a");a.href=url;a.download="中南知了_刷题进度备份.json";document.body.appendChild(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);note("进度已导出；不包含API Key");
};
$("importBtn").onclick=()=>$("importFile").click();
$("importFile").onchange=async e=>{
 const file=e.target.files[0];if(!file)return;
 try{
   const data=JSON.parse(await file.text());
   if(!data.progress||typeof data.progress!=="object"||Array.isArray(data.progress))throw Error("找不到progress字段");
   if(!window.confirm("导入会与现有进度合并；重叠题目尽量保留作答次数更多的记录。确定导入？"))return;
   progress=mergeProgress(progress,data.progress);
   syncLocal();syncDisk();refresh();note("进度导入成功，旧版记录已兼容");
 }catch(err){note("导入失败："+err.message);}finally{e.target.value="";}
};
document.addEventListener("keydown",e=>{
 if(["INPUT","TEXTAREA","SELECT"].includes(document.activeElement.tagName))return;
 if(e.key==="ArrowRight")$("nextBtn").click();
 if(e.key==="ArrowLeft")$("prevBtn").click();
});
window.addEventListener("pagehide",()=>{if(SERVICE){clearTimeout(saveTimer);syncDisk();}});
BANK.forEach(q=>{if(progress[q.id])state(q);});
render();
hydrateProgress().then(()=>{BANK.forEach(q=>{if(progress[q.id])state(q);});refresh();});
