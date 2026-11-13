#!/usr/bin/env python3
# coding: utf-8
"""Mac Keychain minimal bridge: API keys never go through shell arguments or JS storage."""
import ctypes as C
from pathlib import Path

ERR_NOT_FOUND = -25300
ERR_DUPLICATE = -25299
LIB = C.CDLL("/System/Library/Frameworks/Security.framework/Security")
CF = C.CDLL("/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation")
V = C.c_void_p
I = C.c_uint32
LIB.SecKeychainAddGenericPassword.argtypes = [V, I, C.c_char_p, I, C.c_char_p, I, V, C.POINTER(V)]
LIB.SecKeychainAddGenericPassword.restype = C.c_int32
LIB.SecKeychainFindGenericPassword.argtypes = [V,I,C.c_char_p,I,C.c_char_p,C.POINTER(I),C.POINTER(V),C.POINTER(V)]
LIB.SecKeychainFindGenericPassword.restype = C.c_int32
LIB.SecKeychainItemModifyAttributesAndData.argtypes = [V,V,I,V]
LIB.SecKeychainItemModifyAttributesAndData.restype = C.c_int32
LIB.SecKeychainItemDelete.argtypes = [V]
LIB.SecKeychainItemDelete.restype = C.c_int32
LIB.SecKeychainItemFreeContent.argtypes = [V,V]
LIB.SecKeychainItemFreeContent.restype = C.c_int32
CF.CFRelease.argtypes=[V]
CF.CFRelease.restype=None

SERVICE = b"cn.zhiliao.edu-pm-bank.ai-key.v1"
ACCOUNT = b"local-quiz-grading"

class KeychainError(RuntimeError):
    pass

def _lookup():
    ln=I(0);ptr=V();item=V()
    rc=LIB.SecKeychainFindGenericPassword(None,len(SERVICE),SERVICE,len(ACCOUNT),ACCOUNT,C.byref(ln),C.byref(ptr),C.byref(item))
    if rc==ERR_NOT_FOUND:
        return None,None
    if rc!=0:
        raise KeychainError(f"macOS钥匙串读取失败：错误码 {rc}，可先在系统中解锁登录钥匙串。")
    try:
        key=C.string_at(ptr,ln.value).decode("utf-8")
    finally:
        if ptr:LIB.SecKeychainItemFreeContent(None,ptr)
    return key,item

def get():
    k,ref=_lookup()
    if ref: CF.CFRelease(ref)
    return k

def save(value):
    if not isinstance(value,str) or not value.strip():
        raise ValueError("API Key 不能为空")
    data=value.strip().encode("utf-8")
    if len(data)>4096:raise ValueError("API Key 长度超限")
    existing,ref=_lookup()
    buf=C.create_string_buffer(data)
    if ref:
        try:
            rc=LIB.SecKeychainItemModifyAttributesAndData(ref,None,len(data),C.cast(buf,V))
        finally:
            CF.CFRelease(ref)
    else:
        item=V()
        rc=LIB.SecKeychainAddGenericPassword(None,len(SERVICE),SERVICE,len(ACCOUNT),ACCOUNT,len(data),C.cast(buf,V),C.byref(item))
        if item:CF.CFRelease(item)
    if rc!=0:raise KeychainError(f"macOS钥匙串保存失败：错误码 {rc}")
    return True

def erase():
    existing,ref=_lookup()
    if not ref:return True
    try:
        rc=LIB.SecKeychainItemDelete(ref)
        if rc!=0:raise KeychainError(f"macOS钥匙串删除失败：错误码 {rc}")
    finally:
        CF.CFRelease(ref)
    return True
