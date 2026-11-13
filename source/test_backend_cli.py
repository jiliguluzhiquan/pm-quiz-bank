#!/usr/bin/env python3
# coding: utf-8
"""后台模型CLI回归测试：不访问真实密钥/用户配置，无外网请求。"""
import builtins
import contextlib
import getpass
import importlib.util
import io
from pathlib import Path
import sys
import tempfile

SCRIPT=Path(__file__).parent/"configure_ai.py"
spec=importlib.util.spec_from_file_location("zhiliao_config_test",SCRIPT)
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

class FakeKeychain:
    secret=None
    def get(self):return self.secret
    def save(self,value):self.secret=value
    def erase(self):self.secret=None

with tempfile.TemporaryDirectory(prefix="zl-config-test-") as d:
    mod.server.DATA_DIR=Path(d)
    mod.server.CONF_PATH=Path(d)/"settings.json"
    mod.server.PROGRESS_PATH=Path(d)/"progress.json"
    kc=FakeKeychain()
    mod.server.KC=kc
    actual_input=builtins.input
    actual_getpass=getpass.getpass
    actual_argv=sys.argv
    out=io.StringIO()
    try:
        def prompt(prompt_text):
            if "API Base URL" in prompt_text:return "https://api.siliconflow.cn/v1"
            if "模型名称" in prompt_text:return "Qwen/Qwen3-32B"
            if prompt_text.startswith("确定清除"):return "YES"
            raise AssertionError("Unexpected prompt: "+prompt_text)
        builtins.input=prompt
        getpass.getpass=lambda prompt="": "local-test-secret-never-log"
        sys.argv=["configure_ai.py"]
        with contextlib.redirect_stdout(out):
            result=mod.main()
        assert result==0, out.getvalue()
        assert kc.secret=="local-test-secret-never-log"
        assert mod.server.get_config()["model"]=="Qwen/Qwen3-32B"
        assert "local-test-secret-never-log" not in mod.server.CONF_PATH.read_text()
        assert "local-test-secret-never-log" not in out.getvalue()
        print("BACKEND_SETUP_OK, KEY_NOT_IN_JSON_OR_TERMINAL_OUTPUT")

        # 第二次配置空密钥则保留之前保存的钥匙串记录
        kc_before=kc.secret
        builtins.input=lambda t:""
        getpass.getpass=lambda t:""
        with contextlib.redirect_stdout(out):
            result=mod.main()
        assert result==0 and kc.secret==kc_before
        print("ONCE_CONFIGURED_PERSISTS_WITHOUT_REINPUT_OK")

        # CLI显示状态不能暴露明文Key
        sys.argv=["configure_ai.py","--show"]
        buf=io.StringIO()
        with contextlib.redirect_stdout(buf):
            result=mod.main()
        assert result==0
        assert "local-test-secret-never-log" not in buf.getvalue()
        assert "Qwen/Qwen3-32B" in buf.getvalue()
        print("CLI_SHOW_NO_KEY_DISCLOSURE_OK")

        sys.argv=["configure_ai.py","--remove-key"]
        builtins.input=lambda t:"YES"
        with contextlib.redirect_stdout(out):
            result=mod.main()
        assert result==0 and kc.secret is None
        print("CLI_REMOVE_KEY_OK")
    finally:
        builtins.input=actual_input
        getpass.getpass=actual_getpass
        sys.argv=actual_argv
print("TEST_COMPLETE_NO_REAL_KEY_NO_EXTERNAL_REQUEST")
