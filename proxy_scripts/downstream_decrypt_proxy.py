#!/usr/bin/env python3
"""
下游解密代理 (Browser -> mitmproxy:8082 -> Burp:8080)
端口: 8082
功能: 解浏览器密文 -> 明文给Burp | 加密Burp明文 -> 密文回浏览器

启动方式: 必须使用 --mode upstream 将解密后的流量转发到 Burp
  mitmdump -s downstream_decrypt_proxy.py --mode upstream:http://127.0.0.1:8080 -p 8082
"""
from mitmproxy import http
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad, pad
import base64, json, urllib.parse

TARGET_DOMAINS = ['10.140.136.108:88']
AES_KEY = b'1234567890123456'
AES_IV = b'1234567890123456'
TARGET_PATH = '/encrypt/aes.php'


def aes_cbc_decrypt(ciphertext: str) -> str:
    """AES-CBC解密，返回明文字符串"""
    raw = base64.b64decode(ciphertext)
    cipher = AES.new(AES_KEY, AES.MODE_CBC, AES_IV)
    return unpad(cipher.decrypt(raw), 16).decode('utf-8')


def aes_cbc_encrypt(plaintext: str) -> str:
    """AES-CBC加密，返回base64字符串"""
    cipher = AES.new(AES_KEY, AES.MODE_CBC, AES_IV)
    return base64.b64encode(cipher.encrypt(pad(plaintext.encode('utf-8'), 16))).decode()


class DownstreamDecryptProxy:

    def request(self, flow: http.HTTPFlow) -> None:
        """浏览器 -> Burp: 解密密文请求 -> 转发明文"""
        if not any(d in flow.request.pretty_url for d in TARGET_DOMAINS):
            return
        if TARGET_PATH not in flow.request.pretty_url:
            return
        if flow.request.method != 'POST':
            return

        # 解析 form-urlencoded 中的加密数据
        body = flow.request.text
        params = urllib.parse.parse_qs(body)
        encrypted = params.get('encryptedData', [None])[0]
        if not encrypted:
            return

        try:
            decrypted_json = aes_cbc_decrypt(encrypted)
            decrypted_data = json.loads(decrypted_json)
            print(f'[下游解密] {flow.request.pretty_url}')
            for k, v in decrypted_data.items():
                print(f'    [请求解密] {k}: {v}')

            # 替换请求体为明文 JSON，让 Burp 看到明文
            flow.request.headers['Content-Type'] = 'application/json'
            flow.request.text = decrypted_json

            # 修复 Content-Length
            if 'Content-Length' in flow.request.headers:
                flow.request.headers['Content-Length'] = str(len(decrypted_json))

        except Exception as e:
            print(f'[下游解密] 解密失败: {e}')

    def response(self, flow: http.HTTPFlow) -> None:
        """Burp -> 浏览器: 加密明文响应 -> 转发密文给浏览器"""
        if not any(d in flow.request.pretty_url for d in TARGET_DOMAINS):
            return
        if TARGET_PATH not in flow.request.pretty_url:
            return

        # 此接口响应为明文 JSON，Burp 修改后也是明文，直接透传
        # 如果后续有加密响应需要处理，在此处添加加密逻辑
        print(f'[下游响应] {flow.request.pretty_url} -> {flow.response.text[:200]}')


addons = [DownstreamDecryptProxy()]
