#!/usr/bin/env python3
"""
上游加密代理 (Burp:8080 -> mitmproxy:8083 -> Server)
端口: 8083
功能: 加密Burp明文请求 -> 密文给服务器 | 解密服务器密文 -> 明文回Burp
"""
from mitmproxy import http
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
import base64, json, urllib.parse

TARGET_DOMAINS = ['10.140.136.108:88']
AES_KEY = b'1234567890123456'
AES_IV = b'1234567890123456'
TARGET_PATH = '/encrypt/aes.php'


def aes_cbc_encrypt(plaintext: str) -> str:
    """AES-CBC加密，返回base64字符串"""
    cipher = AES.new(AES_KEY, AES.MODE_CBC, AES_IV)
    return base64.b64encode(cipher.encrypt(pad(plaintext.encode('utf-8'), 16))).decode()


def aes_cbc_decrypt(ciphertext: str) -> str:
    """AES-CBC解密，返回明文字符串"""
    raw = base64.b64decode(ciphertext)
    cipher = AES.new(AES_KEY, AES.MODE_CBC, AES_IV)
    return unpad(cipher.decrypt(raw), 16).decode('utf-8')


class UpstreamEncryptProxy:

    def request(self, flow: http.HTTPFlow) -> None:
        """Burp -> Server: 加密明文请求"""
        if not any(d in flow.request.pretty_url for d in TARGET_DOMAINS):
            return
        if TARGET_PATH not in flow.request.pretty_url:
            return
        if flow.request.method != 'POST':
            return

        # Burp 修改后的请求体应该是明文 JSON
        plaintext = flow.request.text
        if not plaintext:
            return

        try:
            # 验证是合法 JSON
            json.loads(plaintext)
            encrypted = aes_cbc_encrypt(plaintext)
            enc_body = f'encryptedData={urllib.parse.quote(encrypted)}'
            print(f'[上游加密] {flow.request.pretty_url}')
            print(f'    [加密] {plaintext} -> {encrypted}')

            # 替换请求体为加密后的 form-urlencoded
            flow.request.headers['Content-Type'] = 'application/x-www-form-urlencoded; charset=utf-8'
            flow.request.text = enc_body

            # 修复 Content-Length
            if 'Content-Length' in flow.request.headers:
                flow.request.headers['Content-Length'] = str(len(enc_body))

        except json.JSONDecodeError:
            print(f'[上游加密] 请求体不是合法JSON，跳过: {plaintext[:100]}')
        except Exception as e:
            print(f'[上游加密] 加密失败: {e}')

    def response(self, flow: http.HTTPFlow) -> None:
        """Server -> Burp: 解密密文响应"""
        if not any(d in flow.request.pretty_url for d in TARGET_DOMAINS):
            return
        if TARGET_PATH not in flow.request.pretty_url:
            return

        # 此接口响应为明文 JSON，直接透传
        # 如果有加密响应，在此处添加解密逻辑
        print(f'[上游响应] {flow.request.pretty_url} -> {flow.response.text[:200]}')


addons = [UpstreamEncryptProxy()]
