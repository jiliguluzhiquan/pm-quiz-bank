#!/usr/bin/env python3
# coding: utf-8
"""一次性后端模型配置。Key只通过Mac终端隐藏输入并保存在钥匙串。
没有Web表单，不接受通过命令行参数传入Key，也不输出Key。
"""
from __future__ import annotations

import argparse
import getpass
import importlib.util
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parent.parent
spec=importlib.util.spec_from_file_location("zhiliao_exam_backend",ROOT/"本地AI评分服务.py")
server=importlib.util.module_from_spec(spec)
spec.loader.exec_module(server)

def status():
    cfg=server.get_config()
    try:has_key=server.KC.get() is not None
    except Exception as e:
        print("无法读取macOS钥匙串状态，请先解锁登录钥匙串。")
        return False
    print("API Base URL：",cfg["base_url"])
    print("模型名称：",cfg["model"])
    print("API Key：", "已保存在macOS钥匙串（不会显示密钥）" if has_key else "尚未设置")
    return has_key

def main():
    p=argparse.ArgumentParser(description="中南知了AI判分后台配置：不会在网页显示API设置")
    p.add_argument("--show",action="store_true",help="只显示非敏感配置及是否已保存Key")
    p.add_argument("--remove-key",action="store_true",help="清除本题库在Mac钥匙串中的Key")
    args=p.parse_args()
    print("\n中南知了｜AI判分后台配置")
    print("────────────────────────")
    if args.show:
        status();return 0
    if args.remove_key:
        answer=input("确定清除本题库的API Key？请输入 YES 确认：").strip()
        if answer=="YES":
            server.KC.erase()
            print("本题库的API Key已从钥匙串清除。")
        else:print("未修改任何配置。")
        return 0
    current=server.get_config()
    status()
    print("\n请在Mac终端完成一次性配置。直接回车会保留已存在的值。")
    print("配置仅写入本机；请勿在聊天里发送任何API Key。")
    try:
        url=input(f"\nAPI Base URL [{current['base_url']}]: ").strip() or current["base_url"]
        model=input(f"模型名称 [{current['model']}]: ").strip() or current["model"]
        config=server.validate_config(url,model)
        key=getpass.getpass("API Key（输入时不会显示；回车保持原密钥）: ").strip()
        if key:
            server.KC.save(key)
        server.atomic_json(server.CONF_PATH,config)
        print("\n后台配置已保存。")
        status()
        print("以后只需双击“开始刷题.command”，无需再配置。")
        print("重新更换模型或密钥时，再运行一次“配置AI.command”。")
        return 0
    except (EOFError,KeyboardInterrupt):
        print("\n已取消配置，不显示或保存任何新密钥。")
        return 130
    except Exception as e:
        print(f"\n配置未成功：{type(e).__name__}。请检查网络无关的输入格式和Mac钥匙串访问权限。")
        return 1

if __name__=="__main__":
    sys.exit(main())
