#!/usr/bin/env python3
"""
下游解密代理 (Browser -> mitmproxy -> Burp:8080)
端口: 8082
功能: 调 JSRPC 解密浏览器请求 -> 明文给Burp | 调 JSRPC 加密Burp响应 -> 密文回浏览器
启动: mitmdump -s downstream_jsrpc_proxy.py --mode upstream:http://127.0.0.1:8080 -p 8082
"""
from mitmproxy import http
from jsrpc_client import jsrpc_call
import urllib.parse

TARGET_DOMAINS = ['10.140.136.108:88']
TARGET_PATHS = ['/encrypt/aes.php']


class DownstreamJSRPCProxy:

    def request(self, flow: http.HTTPFlow) -> None:
        """浏览器 -> Burp: 调 JSRPC 解密请求"""
        if not any(d in flow.request.pretty_url for d in TARGET_DOMAINS):
            return
        if not any(p in flow.request.pretty_url for p in TARGET_PATHS):
            return
        if flow.request.method != 'POST':
            return

        # 解析 form-urlencoded 中的加密数据
        body = flow.request.text
        params = urllib.parse.parse_qs(body)
        encrypted = params.get('encryptedData', [None])[0]
        if not encrypted:
            return

        print(f'[下游JSRPC] 解密请求: {flow.request.pretty_url}')
        plaintext = jsrpc_call('decrypt', encrypted)
        if not plaintext:
            print(f'[下游JSRPC] 解密失败')
            return

        print(f'[下游JSRPC] 解密结果: {plaintext}')
        # 替换为明文 JSON 转发给 Burp
        flow.request.headers['Content-Type'] = 'application/json'
        flow.request.text = plaintext
        if 'Content-Length' in flow.request.headers:
            flow.request.headers['Content-Length'] = str(len(plaintext))

    def response(self, flow: http.HTTPFlow) -> None:
        """Burp -> 浏览器: 调 JSRPC 加密响应（如需）"""
        # 此接口响应是明文 JSON，直接透传
        pass


addons = [DownstreamJSRPCProxy()]
