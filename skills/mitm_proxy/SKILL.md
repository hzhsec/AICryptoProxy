---
name: mitm_proxy
description: 全自动分析网站加密逻辑，利用 js-reverse MCP（浏览器调试）逆向 JS 加密函数并提取密钥，生成 mitmproxy 脚本，支持三种工作模式实现 Burp Suite 与加密流量的透明交互。
---

# mitm_proxy

## 描述

全自动分析网站加密逻辑，利用 **js-reverse MCP（浏览器调试）** 逆向 JS 加密函数并提取密钥，生成 mitmproxy 脚本，支持**三种工作模式**实现 Burp Suite 与加密流量的透明交互。

---

## 三种工作模式

### 模式 1: 双代理模式（全功能）
```
浏览器 → 下游mitmproxy(解密) → Burp(:8080) → 上游mitmproxy(加密) → 服务器
                 ↑                            ↓
            Burp 始终看到明文             自动加解密
```

- **请求方向**: 浏览器 JS 加密 → 下游解密 → Burp 明文 → 上游加密 → 服务器
- **响应方向**: 服务器密文 → 上游解密 → Burp 明文 → 下游加密 → 浏览器
- **优点**: Burp 全程明文，浏览器不报错，Intruder/Repeater 直接操作明文

### 模式 2: 仅解密模式（Observe Only）
```
浏览器/source → mitmproxy(解密) → Burp(:8080)
```
- 只解密响应/请求中已加密的字段
- 用于分析、查看加密数据内容，不做修改重发

### 模式 3: 仅加密模式（Attack Only）
```
Burp(:8080) → mitmproxy(加密) → 服务器
```
- Burp 中构造明文请求，mitmproxy 自动加密后发往服务器
- 用于 Intruder 爆破、SQL 注入、越权测试等场景

---

## 使用方法

```
skill: mitm_proxy https://target.com
```

AI 将依次执行：

1. **Phase 1 - JS 逆向分析**（js-reverse MCP + 浏览器调试）
2. **Phase 2 - 询问用户选择模式**
3. **Phase 3 - 生成对应模式的 mitmproxy 脚本**

---

## Phase 1: JS 逆向分析（js-reverse MCP）

### Step 1: 启动调试浏览器

使用下面的命令启动一个带远程调试端口的 Chrome 实例（js-reverse MCP 依赖端口 9222）：

```bash
"C:\Users\huangzonghui\AppData\Local\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir="C:\Users\huangzonghui\AppData\Local\Temp\chrome_debug_9222" --no-first-run --no-default-browser-check --new-window "https://target.com" &
```

验证连接:
```bash
curl -s http://127.0.0.1:9222/json/version
```

### Step 2: 连接到页面

```bash
# 列出页面 → 选择目标页面
# 使用 js-reverse MCP 工具:
mcp__js-reverse__list_pages
mcp__js-reverse__select_page(pageIdx=0)
```

### Step 3: 收集 JS 代码

使用 collect_code 自动收集页面所有 JS（包括动态加载的）：

```bash
mcp__js-reverse__collect_code(
  url="https://target.com",
  smartMode="full",
  includeInline=true,
  includeExternal=true,
  includeDynamic=true
)
```

如果文件过多，先用 `summary` 模式概览，再按需拉取。

### Step 4: 搜索加密关键词

在收集到的 JS 中搜索加密相关代码：

```bash
mcp__js-reverse__search_in_sources(
  query="encrypt|decrypt|CryptoJS|JSEncrypt|setPublicKey|setPrivateKey",
  urlFilter="target",
  maxResults=50
)
mcp__js-reverse__search_in_sources(
  query="AES|RSA|SM2|SM4|DES|pkcs1|pkcs7|padding|mode",
  urlFilter="target",
  maxResults=50
)
```

### Step 5: Hook 关键函数捕获参数

发现加密函数后，用 hook 记录每次调用的参数和返回值（不打断执行）：

```bash
# 例: hook 全局加密函数
mcp__js-reverse__hook_function(
  target="window.encryptData",  # 根据实际函数名修改
  logArgs=true,
  logResult=true,
  logStack=false
)

# 例: hook CryptoJS.AES.encrypt
mcp__js-reverse__hook_function(
  target="CryptoJS.AES.encrypt",
  logArgs=true,
  logResult=true
)
```

### Step 6: 触发加密请求 + 捕获数据

在浏览器中执行一次目标操作（登录/查询等），触发加密函数调用：

```bash
# 用 js-reverse 在浏览器中触发操作，或者让用户手动操作
# 然后查看 hook 捕获的数据:
mcp__js-reverse__get_hook_data(hookId="CryptoJS.AES.encrypt", view="raw")
```

从 hook 结果中提取：
- **加密算法**（AES-CBC / AES-ECB / RSA / SM2/SM4）
- **密钥 Key / IV**
- **模式 Mode 和填充 Padding**
- **需要加密的字段名**

### Step 7: 如果 JS 高度混淆

尝试使用 AI 反混淆：

```bash
mcp__js-reverse__deobfuscate_code(code="...混淆代码...", aggressive=true)
```

或用 `browser-reverse` / `code-obfuscation-deobfuscation` skill 辅助分析。

---

## Phase 2: 选择工作模式

完成 JS 分析后，向用户展示发现的加密信息并询问模式：

```
[+] 加密分析完成
    算法: AES-256-CBC
    Key:  xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
    IV:   xxxxxxxxxxxxxxxxxxxxxxxx
    加密字段: username, password, data
    解密函数: decryptResponse(data)

请选择工作模式:
1) 双代理模式（全功能，Burp 始终明文）
2) 仅解密模式（只解密查看）
3) 仅加密模式（只加密发送，用于攻击）
```

---

## Phase 3: 生成脚本

根据用户选择的模式生成对应脚本。

### 关键前置步骤: 抓包确认加密请求的原始格式

**不要猜测加密请求的格式。** 在写脚本之前，先用浏览器触发一次真实请求，抓包看清请求体：

1. 浏览器中操作触发目标请求
2. 用 js-reverse 列出网络请求:
   ```
   mcp__js-reverse__network_request(action="list")
   ```
3. 查看具体请求详情:
   ```
   mcp__js-reverse__network_request(action="get", reqid=1)
   ```

**重点确认：**
- Content-Type: `application/json` 还是 `application/x-www-form-urlencoded`？
- 加密数据放在哪个字段？
- 是单字段密文还是多字段独立加密？

**常见格式对照表：**

| Content-Type | 请求体示例 | 脚本处理方法 |
|-------------|-----------|-------------|
| `x-www-form-urlencoded` | `data=Abc...==` | `parse_qs` 提取 → `quote()` 拼接回去 |
| `x-www-form-urlencoded` | `u=EncA...&p=EncB...` | 每个字段独立处理 |
| `application/json` | `{"cipher":"Abc...=="}` | `json.loads` + `json.dumps` |
| `application/json` | `{"data":{"user":"Enc..."}}` | 深层字段替换 |

**拿到真实格式后再写脚本，模板中的加解密处理部分必须按实际格式修改。**

---

## 模式 1: 双代理脚本模板

### 下游代理脚本（decrypt proxy）— 放在浏览器和 Burp 之间

```python
#!/usr/bin/env python3
"""
{TARGET_DOMAIN} 下游解密代理 (Browser → mitmproxy → Burp)
端口: 8082
功能: 解浏览器密文 → 明文给Burp | 加密Burp明文 → 密文回浏览器
"""
from mitmproxy import http
import json, base64, re

class DownstreamDecryptProxy:
    """下游代理: 解密浏览器请求 / 加密响应回浏览器"""

    def __init__(self):
        self.target_domains = ['{TARGET_DOMAIN}']
        # ---- AI 提取的密钥和算法 ----
        # {CRYPTO_CONFIG}
        self._init_crypto()

    def _init_crypto(self):
        # 由 AI 根据分析结果填充
        pass

    def decrypt_request(self, ciphertext: str) -> str:
        """解密函数 - AI 根据 JS 逆向结果生成"""
        # e.g. AES decryption
        # from Crypto.Cipher import AES
        # from Crypto.Util.Padding import unpad
        # cipher = AES.new(self.key, AES.MODE_CBC, self.iv)
        # return unpad(cipher.decrypt(base64.b64decode(ciphertext)), 16).decode('utf-8')
        raise NotImplementedError()

    def encrypt_response(self, plaintext: str) -> str:
        """加密函数 - AI 根据 JS 逆向结果生成"""
        # 与浏览器 JS 加密方式保持一致
        raise NotImplementedError()

    def request(self, flow: http.HTTPFlow) -> None:
        """浏览器→Burp: 解密密文请求 → 转发明文"""
        if not any(d in flow.request.pretty_url for d in self.target_domains):
            return
        # 检测请求体中的加密字段，解密后发给 Burp
        # ... (AI 根据实际字段结构生成)

    def response(self, flow: http.HTTPFlow) -> None:
        """Burp→浏览器: 加密明文响应 → 转发密文给浏览器"""
        if not any(d in flow.request.pretty_url for d in self.target_domains):
            return
        # 检测响应体中的明文，加密后发给浏览器
        # ... (AI 根据实际字段结构生成)

addons = [DownstreamDecryptProxy()]
```

### 上游代理脚本（encrypt proxy）— 放在 Burp 和服务器之间

```python
#!/usr/bin/env python3
"""
{TARGET_DOMAIN} 上游加密代理 (Burp → mitmproxy → Server)
端口: 8083
功能: 加密Burp明文 → 密文给服务器 | 解密服务器密文 → 明文回Burp
"""
from mitmproxy import http
import json, base64, re

class UpstreamEncryptProxy:
    """上游代理: 加密Burp请求 / 解密服务器响应"""

    def __init__(self):
        self.target_domains = ['{TARGET_DOMAIN}']
        # ---- AI 提取的密钥和算法 ----
        # {CRYPTO_CONFIG}
        self._init_crypto()

    def _init_crypto(self):
        pass

    def encrypt(self, plaintext: str) -> str:
        """加密函数 - AI 生成"""
        raise NotImplementedError()

    def decrypt(self, ciphertext: str) -> str:
        """解密函数 - AI 生成"""
        raise NotImplementedError()

    def request(self, flow: http.HTTPFlow) -> None:
        """Burp→Server: 加密明文请求"""
        if not any(d in flow.request.pretty_url for d in self.target_domains):
            return
        # 加密请求体中的明文字段
        # ...

    def response(self, flow: http.HTTPFlow) -> None:
        """Server→Burp: 解密密文响应"""
        if not any(d in flow.request.pretty_url for d in self.target_domains):
            return
        # 解密响应体中的密文字段
        # ...

addons = [UpstreamEncryptProxy()]
```

**双代理启动命令：**

```bash
# 终端 1: 启动上游代理 (Burp → Server, 加密)，普通模式
mitmdump -s {domain}_upstream_proxy.py -p 8083

# 终端 2: 启动下游代理 (Browser → Burp, 解密)，必须用 --mode upstream 指向 Burp
mitmdump -s {domain}_downstream_proxy.py --mode upstream:http://127.0.0.1:8080 -p 8082

# Burp Suite 配置:
# Settings → Proxy → Upstream Proxy Servers
# 规则1: *{domain}* → 127.0.0.1:8083  (上游加密)

# 浏览器代理配置:
# HTTP/HTTPS → 127.0.0.1:8082  (下游解密)
```

---

## 模式 2: 仅解密脚本模板

```python
#!/usr/bin/env python3
"""
{TARGET_DOMAIN} 仅解密代理
端口: 8082
功能: 只解密响应/请求中的加密字段，Burp 看到明文
"""
from mitmproxy import http
import json, base64, re

class DecryptOnlyProxy:
    def __init__(self):
        self.target_domains = ['{TARGET_DOMAIN}']
        # {CRYPTO_CONFIG}
        self._init_crypto()

    def _init_crypto(self):
        pass

    def decrypt(self, ciphertext: str) -> str:
        """解密函数 - AI 生成"""
        raise NotImplementedError()

    def response(self, flow: http.HTTPFlow) -> None:
        """仅解密服务器响应"""
        if not any(d in flow.request.pretty_url for d in self.target_domains):
            return
        # 解密响应体中的加密字段
        # ...

addons = [DecryptOnlyProxy()]
```

```bash
# 启动
mitmdump -s {domain}_decrypt_only.py -p 8082

# 浏览器代理 → 127.0.0.1:8082
# 或 Burp 上游代理 → 127.0.0.1:8082
```

---

## 模式 3: 仅加密脚本模板

```python
#!/usr/bin/env python3
"""
{TARGET_DOMAIN} 仅加密代理
端口: 8083
功能: 加密 Burp 的明文请求后发送给服务器
"""
from mitmproxy import http
import json, base64, re

class EncryptOnlyProxy:
    def __init__(self):
        self.target_domains = ['{TARGET_DOMAIN}']
        # {CRYPTO_CONFIG}
        self._init_crypto()

    def _init_crypto(self):
        pass

    def encrypt(self, plaintext: str) -> str:
        """加密函数 - AI 生成"""
        raise NotImplementedError()

    def request(self, flow: http.HTTPFlow) -> None:
        """加密 Burp 明文请求"""
        if not any(d in flow.request.pretty_url for d in self.target_domains):
            return
        # 加密请求体中的明文字段
        # ...

addons = [EncryptOnlyProxy()]
```

```bash
# 启动
mitmdump -s {domain}_encrypt_only.py -p 8083

# Burp → Upstream Proxy: *{domain}* → 127.0.0.1:8083
```

---

## AI 生成加解密函数参考

### AES (CryptoJS 兼容)

```python
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
import base64

def aes_cbc_encrypt(plaintext: str, key: bytes, iv: bytes) -> str:
    cipher = AES.new(key, AES.MODE_CBC, iv)
    return base64.b64encode(cipher.encrypt(pad(plaintext.encode('utf-8'), 16))).decode()

def aes_cbc_decrypt(ciphertext: str, key: bytes, iv: bytes) -> str:
    cipher = AES.new(key, AES.MODE_CBC, iv)
    return unpad(cipher.decrypt(base64.b64decode(ciphertext)), 16).decode('utf-8')

def aes_ecb_encrypt(plaintext: str, key: bytes) -> str:
    cipher = AES.new(key, AES.MODE_ECB)
    return base64.b64encode(cipher.encrypt(pad(plaintext.encode('utf-8'), 16))).decode()

def aes_ecb_decrypt(ciphertext: str, key: bytes) -> str:
    cipher = AES.new(key, AES.MODE_ECB)
    return unpad(cipher.decrypt(base64.b64decode(ciphertext)), 16).decode('utf-8')
```

### RSA (JSEncrypt 兼容)

```python
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_v1_5
import base64

def rsa_encrypt(plaintext: str, public_key: str) -> str:
    key = RSA.import_key(public_key)
    cipher = PKCS1_v1_5.new(key)
    return base64.b64encode(cipher.encrypt(plaintext.encode('utf-8'))).decode()

def rsa_decrypt(ciphertext: str, private_key: str) -> str:
    key = RSA.import_key(private_key)
    cipher = PKCS1_v1_5.new(key)
    return cipher.decrypt(base64.b64decode(ciphertext), None).decode('utf-8')
```

### 国密 SM4

```python
from gmssl.sm4 import CryptSM4, SM4_ENCRYPT, SM4_DECRYPT
import base64

def sm4_encrypt(plaintext: str, key: bytes) -> str:
    crypt = CryptSM4()
    crypt.set_key(key, SM4_ENCRYPT)
    return base64.b64encode(crypt.crypt_ecb(plaintext.encode('utf-8'))).decode()

def sm4_decrypt(ciphertext: str, key: bytes) -> str:
    crypt = CryptSM4()
    crypt.set_key(key, SM4_DECRYPT)
    return crypt.crypt_ecb(base64.b64decode(ciphertext)).decode('utf-8')
```

---

## 输出文件结构

```
{target_domain}/
├── ANALYSIS_REPORT.md              # 详细分析报告
├── js/                             # 下载的 JS 文件
├── hook_data/                      # Hook 捕获的参数样本
├── downstream_decrypt_proxy.py     # [模式1] 下游解密代理脚本
├── upstream_encrypt_proxy.py       # [模式1] 上游加密代理脚本
├── decrypt_only_proxy.py           # [模式2] 仅解密代理脚本
└── encrypt_only_proxy.py           # [模式3] 仅加密代理脚本
```

---

## 完成通知（重要）

脚本生成后，AI **必须主动** 在对话中输出以下内容（不要只写在文件里，要让用户直接看到）：

### 1. 快速启动命令

按模式输出对应的启动方式：

**双代理模式：**
```bash
# 终端 1 - 上游加密代理 (Burp → Server)
mitmdump -s {domain}_upstream_proxy.py -p 8083

# 终端 2 - 下游解密代理 (Browser → Burp)
mitmdump -s {domain}_downstream_proxy.py -p 8082
```

**仅解密模式：**
```bash
mitmdump -s {domain}_decrypt_only.py -p 8082
```

**仅加密模式：**
```bash
mitmdump -s {domain}_encrypt_only.py -p 8083
```

### 2. 代理配置说明

明确告知用户每层的代理怎么设：

```
Burp Suite 配置:
  Settings → Proxy → Upstream Proxy Servers → 添加:
    *{domain}* → 127.0.0.1:8083   (转发给上游加密代理)

浏览器代理配置:
  HTTP/HTTPS → 127.0.0.1:8082   (双代理模式的下游解密代理)
  或 → 127.0.0.1:8080           (其他模式，Burp 默认端口)
```

### 3. 验证步骤

告诉用户如何验证加解密是否正常工作：

```
1. 浏览器访问 https://{domain}，触发一个加密请求
2. 观察 mitmproxy 终端日志，确认输出类似:
   [下游解密] POST /login
       [请求解密] password: ...密文... -> 明文
3. 到 Burp 中查看，确认请求/响应已变为明文
4. 如果解密失败，检查日志中的具体错误信息
```

> **关键**: 必须输出完整的启动命令和配置说明，不能只生成文件就结束。用户需要直接看到 "复制这条命令就能跑" 的信息。

---

## 使用场景

### 登录爆破（推荐模式1或3）
1. 浏览器 JS 加密登录 → 下游代理解密 → Burp 看到明文密码字段
2. Intruder 填入明文 payload → 上游代理加密 → 服务器收到正确密文

### SQL 注入测试（推荐模式1或3）
1. Burp 中直接修改参数为 `admin' OR '1'='1`
2. 上游代理自动加密后发送 → 观察响应

### 接口逆向分析（推荐模式2）
1. 仅解密模式下观察所有加密接口的原始数据结构
2. 理解业务逻辑和参数含义

---

## 日志输出示例

```
[下游解密] POST https://api.target.com/login
    [请求解密] username: ZkeeMKHSfeofC+... -> admin
    [请求解密] password: eQa0WyHx5H1yO9jW... -> 123456
[+] 请求明文已转发至 Burp

[上游加密] POST https://api.target.com/login
    [加密] username: admin -> ZkeeMKHSfeofC+...
    [加密] password: 123456 -> eQa0WyHx5H1yO9jW...
[+] 请求密文已发送至服务器

[上游解密] GET https://api.target.com/user/info
    [解密] data
[+] 响应明文已转发至 Burp

[下游加密] GET https://api.target.com/user/info
    [加密] data
[+] 响应密文已返回浏览器
```

---

---

## ⚠️ 核心原则: 先抓包确认格式，再写脚本

**最容易犯的错误：** 想当然地假设加密请求的格式是 `data=<密文>`，不验证就直接写。

**正确做法：**
1. 浏览器触发真实请求
2. js-reverse 抓包看请求体和 Content-Type
3. 按实际格式写加解密处理逻辑

**关于 base64：** 只有 `x-www-form-urlencoded` 且手动拼字符串时，值才需要 `quote()`。JSON body 不需要。

---

## 故障排除

### js-reverse MCP 连接失败
- 确认 Chrome 已用 `--remote-debugging-port=9222` 启动
- 验证: `curl -s http://127.0.0.1:9222/json/version`
- 检查 `~/.claude/.claude.json` 中 js-reverse 配置是否正确

### Hook 没有捕获到数据
- 加密函数可能不在全局作用域（在 IIFE/模块内）
- 尝试用 `trace_function(functionName=...)` 搜索源代码中的函数
- 或在 `search_in_sources` 中搜索更精确的函数名

### 有弹窗（Modal）的页面无法直接执行 JS
- 必须操作页面元素触发弹窗，再点击弹窗按钮，不能用 `evaluate_script` 直接执行加密函数
- 正确流程: `type_text` 填表单 → `click_element` 点登录 → 弹窗出现 → `click_element` 点对应按钮
- 用 `find_clickable_elements` 查看页面上所有可点击元素（包含不可见的弹窗按钮）

### Fetch Hook 无法完整记录参数
- `hook_function(target="fetch")` 虽然能捕获调用，但 URL、请求体等参数可能为空
- 应优先使用 `network_request` 查看实际网络请求:
  - `network_request(action="list")` 列出请求 → 记录 `reqid`
  - `network_request(action="get", reqid=N)` 查看请求/响应详情

### 动态密钥
- 密钥可能从服务端 API 获取 → 分析网络请求找到密钥接口
- 密钥可能由 JS 动态生成 → 检查生成逻辑并在 Python 中复现
- 密钥可能随时间或会话变化 → 脚本中需要每次从接口获取

### 加解密不一致
- 检查编码: Python 用 `utf-8`，但网页可能用 `gbk`/`gb2312`
- 检查 Base64 变体: 标准 vs URL-safe
- 检查填充: PKCS7 vs ZeroPadding vs NoPadding, 确认 CryptoJS 的默认行为

---

## 依赖

```bash
pip install mitmproxy pycryptodome
pip install gmssl                          # 国密支持
pip install requests                        # 动态密钥获取
```

---

## 安全注意事项

- **仅用于授权的安全测试**
- 安全存储提取的密钥
- 测试后清除日志和密钥文件
- 不要将密钥提交到版本控制

---

*本 Skill 使用 js-reverse MCP 深度分析前端加密，支持三种灵活模式。输入 URL 即可从 JS 逆向到 mitmproxy 脚本全自动生成。*
