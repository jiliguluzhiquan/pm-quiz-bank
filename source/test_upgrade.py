#!/usr/bin/env python3
# coding: utf-8
"""本地服务验证，不联网、不使用用户真实API Key或用户答题进度。"""
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import threading
import urllib.error
import urllib.request

ROOT=Path(__file__).resolve().parent.parent
spec=importlib.util.spec_from_file_location("zhiliao_ai",ROOT/"本地AI评分服务.py")
srv=importlib.util.module_from_spec(spec)
spec.loader.exec_module(srv)

class MemoryKeychain:
    value=None
    def get(self):return self.value
    def save(self,v):self.value=v
    def erase(self):self.value=None

class FakeResponse:
    def __init__(self,body):self.body=body
    def __enter__(self):return self
    def __exit__(self,*args):return False
    def read(self,n=-1):return self.body[:n]

with tempfile.TemporaryDirectory(prefix="zl-pm-test-") as temp:
    srv.DATA_DIR=Path(temp)
    srv.PROGRESS_PATH=Path(temp)/"progress.json"
    srv.CONF_PATH=Path(temp)/"settings.json"
    test_keychain=MemoryKeychain()
    test_keychain.value="safe-dummy-key"  # 仅测试内存假密钥，不访问用户钥匙串
    srv.KC=test_keychain
    server=srv.ThreadingHTTPServer(("127.0.0.1",0),srv.Handler)
    port=server.server_address[1]
    srv.PORT=port
    srv.ORIGIN=f"http://127.0.0.1:{port}"
    origin=srv.ORIGIN
    t=threading.Thread(target=server.serve_forever,daemon=True)
    t.start()
    def req(method,path,payload=None,request_origin=None):
        headers={}
        if payload is not None:
            headers["Content-Type"]="application/json"
            headers["Origin"]=request_origin or origin
        data=None if payload is None else json.dumps(payload).encode("utf-8")
        request=urllib.request.Request(origin+path,data=data,headers=headers,method=method)
        try:
            with urllib.request.urlopen(request,timeout=3) as r:
                return r.status,json.loads(r.read())
        except urllib.error.HTTPError as e:
            return e.code,json.loads(e.read())
    try:
        status,body=req("GET","/api/health")
        assert status==200 and body["ok"]
        status,body=req("GET","/api/ai/config")
        assert status==404,("后台配置接口不应对网页开放",status)
        status,body=req("POST","/api/ai/config",{"model":"deepseek-ai/DeepSeek-V3.2",
            "base_url":"https://api.siliconflow.cn/v1","api_key":"safe-dummy-key"})
        assert status==404,("后台配置接口不应接受网页写入",status)
        assert test_keychain.get()=="safe-dummy-key"
        srv.atomic_json(srv.CONF_PATH,srv.validate_config("https://api.siliconflow.cn/v1","deepseek-ai/DeepSeek-V3.2"))
        assert "safe-dummy-key" not in srv.CONF_PATH.read_text()
        status,body=req("POST","/api/progress",{"progress":{
            "ZL-M01-001-S1":{"checked":True,"correct":False,"attempts":[{"correct":False}],
                             "everWrong":True,"draft":"","fav":False}}})
        assert status==200 and body["count"]==1
        assert "api_key" not in srv.PROGRESS_PATH.read_text()
        status,body=req("GET","/api/progress")
        assert status==200 and "ZL-M01-001-S1" in body["progress"]

        real_score=srv.score_from_model
        def fake_score(q,answer,cfg,key):
            assert q["type"] in ("主观题","实操题") and key=="safe-dummy-key"
            assert len(answer)>20
            return {"score":72,"max_score":100,"dimension_scores":[],"model":cfg["model"],
                    "summary":"模拟阅卷已成功","scored_at":srv.now()}
        srv.score_from_model=fake_score
        status,body=req("POST","/api/ai/score",{"id":"ZL-M01-001-W",
            "draft":"首先定义面向学生和家长的差异化需求，并建立核心功能和量化验收标准。"})
        assert status==200 and body["result"]["score"]==72,(status,body)
        status,body=req("POST","/api/ai/score",{"id":"ZL-M01-001-S1",
            "draft":"本题不应允许单选题调用大模型评分。"})
        assert status==400
        status,body=req("POST","/api/ai/score",{"id":"ZL-M01-001-W",
            "draft":"我没有满足二十字要求。"}, request_origin="https://attacker.example")
        assert status==403,(status,body)
        print("HTTP_ENDPOINTS_PASS: health / progress / grade / config-blocked / same-origin")
        srv.score_from_model=real_score

        # 验证模型响应内容解析与五维评分汇总，不向外部实际发请求
        q=srv.BANK["ZL-M01-001-W"]
        def mocked_urlopen(request,timeout,**kwargs):
            assert request.get_header("Authorization")=="Bearer safe-dummy-key"
            assert request.full_url=="https://api.siliconflow.cn/v1/chat/completions"
            answer={"dimension_scores":[
                {"point":x["point"],"score":int(x["score"]*0.8),"reason":"符合主要评分点"}
                for x in q["rubric"]],
                "strengths":["问题定位清楚"],"improvements":["需要量化验收指标"],
                "summary":"总体合理，部分细节可完善"}
            payload={"choices":[{"message":{"content":json.dumps(answer,ensure_ascii=False)}}]}
            return FakeResponse(json.dumps(payload,ensure_ascii=False).encode("utf-8"))
        original=srv.urllib.request.urlopen
        srv.urllib.request.urlopen=mocked_urlopen
        try:
            grade=srv.score_from_model(q,
                "我先定义学生与家长各自的关键任务，再设计可落地MVP以及上线后效果评估。",
                srv.get_config(),"safe-dummy-key")
        finally:srv.urllib.request.urlopen=original
        assert grade["score"]==80 and len(grade["dimension_scores"])==5,grade
        print("AI_RUBRIC_PARSING_PASS: 5维自动汇总80/100")
        test_keychain.erase()
        assert test_keychain.get() is None
        print("BACKEND_MEMORY_KEYCHAIN_ERASE_PASS")
    finally:
        server.shutdown()
        server.server_close()

print("TEST_COMPLETE_NO_REAL_API_REQUEST")
