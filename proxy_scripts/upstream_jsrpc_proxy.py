#!/usr/bin/env python3
"""
上游加密代理 (Burp:8080 -> mitmproxy -> Server)
端口: 8083
功能: 调 JSRPC 加密 Burp 明文请求 -> 密文给服务器
启动: mitmdump -s upstream_jsrpc_proxy.py -p 8083
"""
from mitmproxy import http
from jsrpc_client import jsrpc_call
import urllib.parse

TARGET_DOMAINS = ['10.140.136.108:88']
TARGET_PATHS = ['/encrypt/aes.php']


class UpstreamJSRPCProxy:

    def request(self, flow: http.HTTPFlow) -> None:
        """Burp -> Server: 调 JSRPC 加密请求"""
        if not any(d in flow.request.pretty_url for d in TARGET_DOMAINS):
            return
        if not any(p in flow.request.pretty_url for p in TARGET_PATHS):
            return
        if flow.request.method != 'POST':
            return

        plaintext = flow.request.text
        if not plaintext:
            return

        print(f'[上游JSRPC] 加密请求: {flow.request.pretty_url}')
        print(f'[上游JSRPC] 明文: {plaintext}')

        encrypted = jsrpc_call('encrypt', plaintext)
        if not encrypted:
            print(f'[上游JSRPC] 加密失败')
            return

        enc_body = f'encryptedData={urllib.parse.quote(encrypted)}'
        print(f'[上游JSRPC] 密文: {encrypted}')

        # 替换为加密后的 form-urlencoded
        flow.request.headers['Content-Type'] = 'application/x-www-form-urlencoded; charset=utf-8'
        flow.request.text = enc_body
        if 'Content-Length' in flow.request.headers:
            flow.request.headers['Content-Length'] = str(len(enc_body))

    def response(self, flow: http.HTTPFlow) -> None:
        """Server -> Burp: 透传服务器响应"""
        pass


addons = [UpstreamJSRPCProxy()]
