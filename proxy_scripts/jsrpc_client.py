"""JSRPC 调用封装 - 供 mitmproxy 脚本调用"""
import requests
import urllib.parse

JSRPC_BASE = "http://127.0.0.1:12080"
JSRPC_GROUP = "mitm"


def jsrpc_call(action: str, param: str) -> str:
    """调用 JSRPC 执行加密/解密，返回结果字符串"""
    url = f"{JSRPC_BASE}/go"
    params = {
        "group": JSRPC_GROUP,
        "action": action,
        "param": param
    }
    try:
        resp = requests.get(url, params=params, timeout=15)
        resp.raise_for_status()
        result = resp.json()
        data = result.get("data", "")
        if data.startswith("ERROR"):
            print(f"[JSRPC] 调用返回错误 ({action}): {data}")
            return ""
        return data
    except Exception as e:
        print(f"[JSRPC] 调用失败 ({action}): {e}")
        return ""
