# AICryptoProxy：AI 赋能 Web 加密流量渗透测试完全指南

> 基于 Claude Code + MCP 的智能加解密代理框架，让 AI 替你完成 JS 逆向全流程

---

## 目录

1. [加密流量的挑战与 AI 破局](#1-加密流量的挑战与-ai-破局)
2. [AICryptoProxy 是什么](#2-aicryptoproxy-是什么)
3. [技术原理：AI 如何自动化 JS 逆向 + 代理部署](#3-技术原理ai-如何自动化-js-逆向--代理部署)
4. [环境准备](#4-环境准备)
5. [模式 A：Direct Crypto——AI 直接逆向加解密](#5-模式-adirect-cryptoai-直接逆向加解密)
6. [模式 B：JSRPC Bridge——AI 零逆向桥接](#6-模式-bjsrpc-bridgeai-零逆向桥接)
7. [两模式对比与选型](#7-两模式对比与选型)
8. [常见问题与排错](#8-常见问题与排错)
9. [总结与展望](#9-总结与展望)

---

## 1. 加密流量的挑战与 AI 破局

### 1.1 传统渗透测试的加密困境

当目标 Web 应用使用前端加密（AES、RSA、SM4 等）时，Burp Suite 抓到的全是密文，测试流程被彻底阻断：

```
浏览器请求: POST /api/data  encryptedData=U2FsdGVkX1...  → 服务器
                                                          ↑
                                               Burp 看到的是密文
                                               无法修改、无法重放
```

传统解决路径只有一条——**JS 逆向**：

| 步骤 | 耗时 | 痛点 |
|------|------|------|
| 定位加密函数 | 30min - 2h | 需要读懂混淆代码、回溯调用栈 |
| 提取密钥算法 | 1 - 4h | 断点调试、分析加密参数 |
| Python 复现 | 1 - 3h | 扣代码 + 补环境，反复调试 |
| 编写代理脚本 | 30min - 1h | mitmproxy 脚本开发调试 |
| **总计** | **3 - 10h** | 精力消耗巨大，且每个目标重复一次 |

更糟的是，遇到动态 Key、自定义算法、深度混淆时，花费的时间还会翻倍。

### 1.2 AI 的破局思路

**AICryptoProxy** 的思路很简单：既然逆向分析本质上是「信息提取 + 模式识别」，那这正是 AI 擅长的。

核心转变：

```
传统模式: 人看代码 → 人分析 → 人写脚本
               ↓
AI 模式:   AI 看代码 → AI 分析 → AI 生成脚本 → 人只需启动
```

通过 Claude Code 的 MCP（Model Context Protocol）能力，AI 可以：
- 像人类一样**操作浏览器**（打开页面、搜索脚本、下断点、读变量）
- 像资深逆向工程师一样**分析加密逻辑**（识别算法、提取 Key、理解调用链）
- 像 Python 开发者一样**编写生产级 mitmproxy 脚本**
- 像技术支持一样**给出启动命令和排错建议**

---

## 2. AICryptoProxy 是什么

### 2.1 一句话定义

> **AICryptoProxy** 是一个基于 Claude Code + MCP 的智能渗透测试框架，通过 AI 自动完成 JS 逆向分析、加解密代理脚本生成、代理链路部署，让测试人员在 Burp Suite 中直接操作明文流量。

### 2.2 GitHub

> 项目地址：`https://github.com/yourusername/AICryptoProxy`（待上传）

```bash
git clone https://github.com/yourusername/AICryptoProxy
cd AICryptoProxy
```

### 2.3 两种工作模式

| 模式 | 名称 | 原理 | 适用场景 |
|------|------|------|---------|
| **A** | Direct Crypto | AI 逆向算法 → 提取 Key → 生成 Python 加解密脚本 | 标准算法、Key 固定 |
| **B** | JSRPC Bridge | AI 生成 JS 注入脚本 → 浏览器原生执行加解密 → JSRPC 桥接 | 算法复杂、Key 动态、混淆严重 |

两种模式共享同一套代理架构（downstream + upstream），区别仅在于加解密逻辑的实现方式。

### 2.4 核心优势

| 维度 | 传统手动逆向 | AICryptoProxy |
|------|------------|---------------|
| 平均耗时 | 3 - 10 小时 | 5 - 15 分钟 |
| 逆向经验要求 | 需要精通 JS 混淆 | 零门槛 |
| 动态 Key 支持 | 需要额外分析逻辑 | 模式 B 自动适配 |
| 自定义算法 | 极难复现 | 浏览器原生执行 |
| 可复现性 | 每个目标重复劳动 | AI 自动完成，人 supervise |

---

## 3. 技术原理：AI 如何自动化 JS 逆向 + 代理部署

### 3.1 三条核心能力链

AICryptoProxy 的能力建立在 Claude Code 的三条能力链之上：

#### 能力链一：MCP 浏览器调试

```
Claude Code ──MCP──→ js-reverse 服务 ──CDP──→ Chrome DevTools
                    ├── list_scripts     → 列出所有 JS
                    ├── search_in_sources → 搜索关键字
                    ├── hook_function     → 追踪函数调用
                    ├── breakpoint        → 设置断点
                    ├── get_paused_info   → 读取变量
                    ├── network_request   → 查看网络请求
                    └── evaluate_script   → 执行 JS
```

AI 通过 MCP 工具链直接操控浏览器，**完全替代人类手动操作 DevTools 的过程**。

#### 能力链二：Skill 工作流编排

```
用户指令("帮我分析这个网站的加密")
       ↓
mitm_proxy / jsrpc-mitm-auto Skill
       ↓
┌─────────────────────────────────┐
│  ① 观察阶段 (Observe)             │
│    - 打开目标网站                  │
│    - 收集所有 JS 脚本              │
│    - 识别加密相关关键字            │
├─────────────────────────────────┤
│  ② 捕获阶段 (Capture)             │
│    - 追踪加密函数调用              │
│    - 提取 Key / IV / 算法参数     │
│    - 捕获网络请求格式              │
├─────────────────────────────────┤
│  ③ 重建阶段 (Rebuild)             │
│    - 生成 Python 加解密代码        │
│    或 生成 JSRPC 注入脚本          │
│    - 生成 mitmproxy 代理脚本       │
├─────────────────────────────────┤
│  ④ 部署阶段 (Patch)               │
│    - 输出启动命令                  │
│    - 验证链路连通性                │
│    - 排错建议                     │
└─────────────────────────────────┘
```

#### 能力链三：双代理架构

AICryptoProxy 使用**两层 mitmproxy 夹 Burp** 的架构：

```
浏览器(密文)
   │
   ▼
┌─────────────────────────────────────┐
│ downstream_proxy (端口 8082)          │
│ 作用: 浏览器→Burp 方向解密密文请求     │
│      Burp→浏览器 方向加密明文响应     │
│ 启动: --mode upstream:http://127.0.0.1:8080 │
└────────────────┬────────────────────┘
                 │ 明文
                 ▼
        ┌────────────────┐
        │  Burp Suite    │  ← 在这里操作明文！
        │  端口 8080     │
        └───────┬────────┘
                │ 明文
                ▼
┌─────────────────────────────────────┐
│ upstream_proxy (端口 8083)           │
│ 作用: Burp→服务器 方向加密明文请求     │
│      服务器→Burp 方向解密密文响应     │
└────────────────┬────────────────────┘
                 │ 密文
                 ▼
           目标服务器
```

这个架构设计的精妙之处在于：
- **Burp 永远只看到明文**——可以自由修改、重放、扫描
- **浏览器和服务器之间始终是密文**——不会触发前端校验
- **下游代理必须用 `--mode upstream`**——否则流量不会经过 Burp

### 3.2 AI 自动化 vs 人工操作的对比

为了直观理解 AI 做了什么，这里以「模式 A：定位加密函数并提取 Key」为例：

| 步骤 | 传统人工操作 | AI 自动化操作 |
|------|------------|-------------|
| 1 | F12 打开 DevTools → Sources → 搜索 `encrypt` | `search_in_sources("encrypt")` → 自动扫描全部脚本 |
| 2 | 逐个文件翻阅搜索结果，判断哪一个是加密函数 | AI 自动理解代码语义，识别加密函数入口 |
| 3 | 在可疑函数处下断点 | `breakpoint.set(url, line)` |
| 4 | 点击页面触发请求，等断点命中 | `hook_function("encryptFunc")` 自动追踪 |
| 5 | 在 Scope 面板中查看变量值 | `evaluate_script("key.toString()")` 自动提取 |
| 6 | 手动记录 Key 和 IV | AI 自动记忆并写入生成的脚本 |
| 7 | 编写 Python 加解密函数 | AI 直接输出完整 `downstream_decrypt_proxy.py` |

> [图片: Claude Code 自动分析 JS 加密逻辑的终端截图，显示 AI 正在搜索脚本、提取 Key]

---

## 4. 环境准备

### 4.1 基础软件

```bash
# Python 3.8+
python --version

# mitmproxy
pip install mitmproxy

# 加密库（模式 A 需要）
pip install pycryptodome requests

# Burp Suite Community/Professional
# 官网下载：https://portswigger.net/burp
```

### 4.2 安装 Claude Code

```bash
# 方式一：npm 安装
npm install -g @anthropic-ai/claude-code

# 方式二：直接下载桌面版
# https://claude.ai/code

# 验证安装
claude --version
```

### 4.3 配置 MCP 服务

AICryptoProxy 依赖 `js-reverse` MCP 服务来操控浏览器：

```json
{
  "mcpServers": {
    "js-reverse": {
      "command": "node",
      "args": ["path/to/js-reverse-server.js"],
      "env": {
        "CHROME_PATH": "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
        "DEBUG_PORT": "9222"
      }
    }
  }
}
```

### 4.4 证书安装

两个 CA 证书需要被浏览器信任：

#### mitmproxy 证书

```bash
# 启动一次 mitmproxy 生成证书
mitmdump -p 8081

# 证书位置：
#   Windows: %USERPROFILE%\.mitmproxy\mitmproxy-ca-cert.p12
#   Linux/Mac: ~/.mitmproxy/mitmproxy-ca-cert.pem

# 浏览器访问 http://mitm.it 下载安装
```

> [图片: 浏览器访问 http://mitm.it 的证书下载页面截图]

#### Burp Suite 证书

```
Burp → Proxy → Options → Import/Export CA certificate
浏览器导入：设置 → 隐私与安全 → 证书管理 → 导入
```

### 4.5 JSRPC 服务端（模式 B 需要）

```bash
# 下载预编译二进制
# 项目地址：https://github.com/jxhczhl/JsRpc
# Releases 页面下载对应平台的版本

# Windows
rpc.exe

# Linux/Mac
chmod +x rpc && ./rpc

# 验证
curl http://127.0.0.1:12080/list
# {"status":"ok","data":[],"code":200,"msg":"success"}
```

> [图片: JSRPC 服务端启动成功的终端截图]

### 4.6 项目目录结构

```
AICryptoProxy/
├── README.md                         # 项目说明
├── requirements.txt                  # Python 依赖
│
├── proxy_scripts/                    # mitmproxy 代理脚本（由 AI 生成）
│   ├── downstream_decrypt_proxy.py   # [模式A] 下游解密代理
│   ├── upstream_encrypt_proxy.py     # [模式A] 上游加密代理
│   ├── downstream_jsrpc_proxy.py     # [模式B] 下游 JSRPC 代理
│   ├── upstream_jsrpc_proxy.py       # [模式B] 上游 JSRPC 代理
│   └── jsrpc_client.py              # JSRPC HTTP 调用封装
│
├── inject_scripts/                   # 浏览器注入脚本
│   └── jsrpc_inject.js               # [模式B] JSRPC 注入脚本
│
├── docs/
│   └── AICryptoProxy_完全指南.md      # 本文
│
└── test/                             # 测试输出
```

> [图片: 项目在 VS Code 中的目录结构截图]

---

## 5. 模式 A：Direct Crypto——AI 直接逆向加解密

### 5.1 适用场景

- 加密算法为标准算法（AES、RSA、SM4、DES 等）
- Key 固定或可在 JS 中定位到
- 需要稳定、高性能的加解密（不依赖浏览器）

### 5.2 AI 自动工作流

当你在 Claude Code 中输入指令后，**不需要手动做任何逆向操作**，AI 会自动执行以下流程：

#### Stage 1：观察 (Observe)

AI 通过 MCP 连接浏览器，自动收集信息：

```
[AI] 正在连接浏览器...
[AI] 已导航到 https://target.com
[AI] 正在搜索加密关键字...
[AI] 在以下文件中发现可疑加密代码:
  - /static/js/main.a1b2c3.js (匹配: encrypt, AES)
  - /static/js/vendor.d4e5f6.js (匹配: CryptoJS)
[AI] 检测到算法: AES-CBC-Pkcs7
```

**AI 自动执行的操作：**
- `new_page("https://target.com")` → 打开目标
- `search_in_sources("encrypt")` → 搜索加密关键字
- `list_scripts` → 列出所有加载的脚本
- `detect_crypto(code)` → 识别加密算法类型

#### Stage 2：捕获 (Capture)

AI 自动定位加密函数并提取 Key：

```
[AI] 正在追踪加密函数调用...
[AI] 在 main.a1b2c3.js:245 发现 encryptData 函数
[AI] 正在提取加密参数...
[AI] 已提取:
  - 算法: AES-CBC-Pkcs7
  - Key:  "1234567890123456" (16字节)
  - IV:   "1234567890123456" (16字节)
  - 编码: Base64
```

**AI 自动执行的操作：**
- `hook_function("encryptData")` → 追踪加密函数
- `get_hook_data(hookId)` → 捕获函数参数和返回值
- `evaluate_script("key")` → 提取 Key 值
- `network_request(action="list")` → 获取真实请求格式

> [图片: AI 自动追踪加密函数并提取 Key 的终端截图]

#### Stage 3：重建 (Rebuild)

AI 自动生成完整的加解密代码和代理脚本：

```python
# AI 自动生成的下游解密代理 (downstream_decrypt_proxy.py)
from mitmproxy import http
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad, pad
import base64, json, urllib.parse

# ↓↓↓ AI 自动提取的参数 ↓↓↓
AES_KEY = b'1234567890123456'
AES_IV = b'1234567890123456'
TARGET_DOMAINS = ['api.target.com']
TARGET_PATH = '/api/encrypt'
# ↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑

def aes_cbc_decrypt(ciphertext: str) -> str:
    """AES-CBC 解密"""
    raw = base64.b64decode(ciphertext)
    cipher = AES.new(AES_KEY, AES.MODE_CBC, AES_IV)
    return unpad(cipher.decrypt(raw), 16).decode('utf-8')

class DownstreamDecryptProxy:
    def request(self, flow):
        """浏览器→Burp: 解密请求"""
        if not any(d in flow.request.pretty_url for d in TARGET_DOMAINS):
            return
        if TARGET_PATH not in flow.request.pretty_url:
            return
        # ... AI 根据捕获的请求格式自动生成的解密逻辑 ...
        
addons = [DownstreamDecryptProxy()]
```

同时 AI 还会生成对应的上游加密代理脚本。

#### Stage 4：部署 (Patch)

AI 给出完整的启动命令：

```
[AI] 所有脚本已生成至 proxy_scripts/ 目录
[AI] 启动顺序：
  1. Burp Suite → 监听 :8080
  2. mitmdump -s proxy_scripts/downstream_decrypt_proxy.py \
             --mode upstream:http://127.0.0.1:8080 -p 8082
  3. mitmdump -s proxy_scripts/upstream_encrypt_proxy.py -p 8083
  4. 浏览器代理 → 127.0.0.1:8082
  5. Burp 上游代理 → 127.0.0.1:8083
```

> [图片: 三个终端窗口同时运行的截图——下游代理(8082)、Burp(8080)、上游代理(8083)]

### 5.3 实际效果

配置完成后，在 Burp Suite 中你会看到：

| 位置 | 原来（无代理） | 现在（AICryptoProxy） |
|------|-------------|-------------------|
| Burp Proxy | `encryptedData=U2FsdGVkX1...` | `{"userId":1001,"amount":500}` |
| Repeater | 只能转发密文 | 可随意修改 JSON 再自动加密 |
| Scanner | 扫描器看不懂密文 | 扫描器直接分析明文接口 |

> [图片: Burp Proxy 中显示解密后明文请求的对比截图]

---

## 6. 模式 B：JSRPC Bridge——AI 零逆向桥接

### 6.1 适用场景

- 加密算法复杂、混淆严重、不想花时间逆向
- Key 动态生成，每次请求都不同
- 自定义算法无法在 Python 中复现
- 想快速验证漏洞，几分钟内搭建好环境

### 6.2 AI 自动工作流

模式 B 更加激进——**完全不逆向算法**，而是让浏览器原生执行加解密，通过 WebSocket 桥接给 mitmproxy。

#### 核心原理

```
                    Python / mitmproxy 世界
┌──────────────────────────────────────────────────────────────┐
│                                                                │
│  mitmproxy 脚本                                                  │
│  → 需要解密时: 调 HTTP 接口 /go?action=decrypt¶m=密文         │
│  → 需要加密时: 调 HTTP 接口 /go?action=encrypt¶m=明文         │
│         ↓                                                        │
│  JSRPC 服务端 (:12080) — Go WebSocket Server                    │
└──────────────────────────┬───────────────────────────────────────┘
                           │ WebSocket
                           ▼
┌──────────────────────────────────────────────────────────────┐
│                      浏览器世界                                  │
│                                                                │
│  页面中注入的 HlClient (WebSocket Client)                        │
│  ├── regAction("encrypt", fn)  → 调用 CryptoJS.AES.encrypt    │
│  └── regAction("decrypt", fn)  → 调用 CryptoJS.AES.decrypt    │
│                                                                │
│  加解密完全在浏览器中执行，AI 不需要分析任何算法代码！              │
└──────────────────────────────────────────────────────────────┘
```

> [图片: JSRPC 原理架构图，展示 mitmproxy ↔ JSRPC服务端 ↔ 浏览器的调用链路]

#### Stage 1：AI 分析请求格式

模式 B 虽然不逆向算法，但仍然需要知道**请求格式**（数据在哪个字段、Content-Type 是什么）：

```
[AI] 正在分析目标请求格式...
[AI] 请求: POST https://api.target.com/encrypt/aes.php
[AI] Content-Type: application/x-www-form-urlencoded
[AI] 加密数据字段: encryptedData
[AI] 检测到页面使用了 CryptoJS
```

#### Stage 2：AI 生成注入脚本

AI 自动生成 `jsrpc_inject.js`——包含完整的 HlClient 类和加解密 action 注册：

```javascript
// AI 生成的 JSRPC 注入脚本（jsrpc_inject.js）
;(function() {
    // 1. HlClient 核心类 - WebSocket RPC 客户端
    var HlClient = function(wsURL) { /* ... */ };
    HlClient.prototype.regAction = function(name, fn) { /* ... */ };
    
    // 2. 等待 CryptoJS 加载完成后注册 action
    function waitForCrypto(callback, retries) {
        if (retries > 50) return;  // 最多等 10 秒
        if (typeof CryptoJS !== 'undefined' && CryptoJS.AES) {
            callback();
        } else {
            setTimeout(function() { 
                waitForCrypto(callback, retries + 1); 
            }, 200);
        }
    }
    
    function registerActions() {
        var client = new HlClient("ws://127.0.0.1:12080/ws?group=mitm");
        
        // 加密 action - 使用页面中的 CryptoJS
        client.regAction("encrypt", function(resolve, param) {
            var key = CryptoJS.enc.Utf8.parse('1234567890123456');
            var iv = CryptoJS.enc.Utf8.parse('1234567890123456');
            var encrypted = CryptoJS.AES.encrypt(param, key, {
                iv: iv, mode: CryptoJS.mode.CBC, padding: CryptoJS.pad.Pkcs7
            });
            resolve(encrypted.toString());
        });
        
        // 解密 action
        client.regAction("decrypt", function(resolve, param) {
            var key = CryptoJS.enc.Utf8.parse('1234567890123456');
            var iv = CryptoJS.enc.Utf8.parse('1234567890123456');
            var decrypted = CryptoJS.AES.decrypt(param, key, {
                iv: iv, mode: CryptoJS.mode.CBC, padding: CryptoJS.pad.Pkcs7
            });
            resolve(decrypted.toString(CryptoJS.enc.Utf8));
        });
    }
    
    waitForCrypto(registerActions);
})();
```

**注入方式**：在目标网站按 F12 打开开发者工具，Console 面板中粘贴上述完整脚本后回车。

> [图片: 浏览器 Console 面板显示 "[JSRPC] 连接成功" 和 "encrypt/decrypt 已注册" 的截图]

#### Stage 3：AI 生成 JSRPC 客户端和代理脚本

```python
# AI 生成的 JSRPC 调用封装（jsrpc_client.py）
import requests

JSRPC_BASE = "http://127.0.0.1:12080"
JSRPC_GROUP = "mitm"

def jsrpc_call(action: str, param: str) -> str:
    """调用 JSRPC 执行加密/解密"""
    url = f"{JSRPC_BASE}/go"
    params = {"group": JSRPC_GROUP, "action": action, "param": param}
    try:
        resp = requests.get(url, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json().get("data", "")
        return "" if data.startswith("ERROR") else data
    except Exception as e:
        print(f"[JSRPC] 调用失败 ({action}): {e}")
        return ""
```

AI 同时生成 `downstream_jsrpc_proxy.py` 和 `upstream_jsrpc_proxy.py`，逻辑上与模式 A 的脚本相同，区别是加解密改为调用 `jsrpc_call()`。

#### Stage 4：部署

```
[AI] 所有脚本已生成
[AI] 启动顺序：
  1. rpc.exe → 启动 JSRPC 服务端 (:12080)
  2. Burp Suite → 监听 :8080
  3. 浏览器 Console → 粘贴 inject_scripts/jsrpc_inject.js
  4. mitmdump -s proxy_scripts/downstream_jsrpc_proxy.py \
             --mode upstream:http://127.0.0.1:8080 -p 8082
  5. mitmdump -s proxy_scripts/upstream_jsrpc_proxy.py -p 8083
```

> [图片: 四个终端窗口——JSRPC 服务端、Burp、下游代理、上游代理 同时运行的截图]

### 6.3 动态 Key 场景

当加密 Key 不是固定的，而是在页面运行时动态生成时，模式 B 的注入脚本需要相应调整。AI 会自动处理以下三种情况：

#### 情况 A：加密函数是全局函数

```javascript
// AI 检测到 window 上有加密函数，直接注册
client.regAction("encrypt", function(resolve, param) {
    resolve(window.globalEncryptFunc(param));
});
```

#### 情况 B：加密函数在闭包中

```
[AI] 检测到加密函数在闭包中，无法直接访问
[AI] 建议：在 XHR 断点触发后执行以下代码将函数暴露到 window：
[AI]   window.myEncrypt = targetEncryptFunc;
```

#### 情况 C：Key 从服务端动态获取

```javascript
// AI 自动从全局状态中读取动态 Key
client.regAction("encrypt", function(resolve, param) {
    var key = window.someGlobalState.key;
    var iv = window.someGlobalState.iv;
    var encrypted = CryptoJS.AES.encrypt(param, key, { iv: iv });
    resolve(encrypted.toString());
});
```

> [图片: AI 分析动态 Key 场景并给出解决方案的终端截图]

---

## 7. 两模式对比与选型

### 7.1 详细对比

| 维度 | 模式 A：Direct Crypto | 模式 B：JSRPC Bridge |
|------|---------------------|---------------------|
| **AI 逆向工作量** | 需分析算法、提取 Key | 只需分析请求格式 |
| **生成的 Python 代码** | 包含完整加解密逻辑 | 只用 HTTP 调用 JSRPC |
| **依赖** | Python + mitmproxy | Python + mitmproxy + JSRPC Go |
| **浏览器** | 不需要保持打开 | **必须保持打开**（WS 连接） |
| **加解密速度** | 快（毫秒级 Python 计算） | 中（HTTP → WS → 浏览器 → 回传） |
| **动态 Key** | 需要分析 Key 生成逻辑 | 自动适配 |
| **自定义算法** | 需要逆向算法逻辑 | 浏览器原生执行 |
| **稳定性** | 高 | 依赖浏览器状态 |
| **AI 处理时间** | 3-5 分钟 | 1-2 分钟 |

### 7.2 选型决策树

```
加密请求格式已知?
├── 是 → Key 是否固定?
│   ├── 是 → ──→ ★ 模式 A (Direct Crypto) —— 稳定、快速
│   └── 否 → ──→ ★ 模式 B (JSRPC Bridge) —— 动态 Key 自动适配
└── 否 → 算法是否标准 (AES/RSA/SM4)?
        ├── 是 → ★ 模式 A —— 标准算法易提取
        └── 否 → ★ 模式 B —— 自定义算法直接让浏览器执行
```

### 7.3 进阶策略：组合使用

场景：先用模式 B 快速搭建环境开始测试，同时用 AI 分析算法准备模式 A。

```
第1小时: 模式 B 快速启动 → 开始测试（不影响进度）
第2小时: AI 后台分析 → 模式 A 脚本就绪（可选切换）
长期: 模式 A 稳定运行（不依赖浏览器）
```

---

## 8. 常见问题与排错

### 8.1 AI 无法连接到浏览器

> [图片: Claude Code 报无法连接浏览器的错误截图]

```
原因：Chrome 未以调试模式启动
解决：关闭所有 Chrome 进程，重新以调试模式启动：
  chrome.exe --remote-debugging-port=9222
  或用 MCP 的 new_page 方法让 AI 自动打开
```

### 8.2 AI 提取的 Key 不正确

```
原因：AI 追踪了错误的函数
解决：在指令中提供更多上下文，例如：
  "加密函数在 main.js 的 encryptData 方法中"
  "Key 是从 /api/key 接口获取的"
```

### 8.3 Burp 中看到的是密文

> [图片: Burp Proxy 中显示密文（错误示例）vs 显示明文（正确示例）的对比截图]

```
原因：下游代理的 --mode upstream 参数缺失
解决：确认启动命令包含 --mode upstream:http://127.0.0.1:8080
  ✅ 正确：mitmdump -s proxy_scripts/downstream_xxx.py \
             --mode upstream:http://127.0.0.1:8080 -p 8082
  ❌ 错误：mitmdump -s proxy_scripts/downstream_xxx.py -p 8082
```

### 8.4 JSRPC 连接失败

> [图片: 浏览器 Console 中 WebSocket 连接失败的报错截图]

```
检查点：
  1. rpc.exe 是否在运行？→ curl http://127.0.0.1:12080/list
  2. 浏览器 Console 是否有 [JSRPC] 连接成功？
  3. group 名称是否一致？（脚本和 URL 都要是 mitm）
  4. 浏览器页面是否还开着？
```

### 8.5 请求体格式不是 form-urlencoded

```
AI 自动判断 Content-Type 并生成对应代码：

# form-urlencoded 格式
params = urllib.parse.parse_qs(body)
encrypted = params.get('encryptedData', [None])[0]

# JSON 格式
data = json.loads(body)
encrypted = data.get('encryptedData')
```

### 8.6 Base64 中 + 号被解码为空格

```python
# 在 form-urlencoded 中拼 base64 时必须 URL 编码
enc_body = f'encryptedData={urllib.parse.quote(encrypted)}'  # ✅

# 或用 requests 自动处理
requests.post(url, data={"encryptedData": encrypted})  # ✅
```

### 8.7 请求不是 POST 方法

```
AI 已自动识别请求方法并生成对应的判断逻辑。
如遇特殊情况，可以手动在脚本中修改：
if flow.request.method != 'POST':
    return  # 跳过非 POST 请求
```

---

## 9. 总结与展望

### 9.1 AI 时代的渗透测试范式转变

AICryptoProxy 代表的不仅仅是一个工具，更是一种新的工作范式：

```
传统范式: 人做 → AI 辅助
    ↓
新范式:  AI 做 → 人 supervise
```

在传统流程中，JS 逆向是**人的核心工作**，AI 只能做辅助（比如代码补全、语法高亮）。而 AICryptoProxy 通过 MCP 让 AI 获得了**操作浏览器的能力**，从而能独立完成完整的逆向工作流。

### 9.2 关键要点回顾

1. **AI 替你动手**——定位函数、提取 Key、写脚本、启动代理，全由 AI 完成
2. **两种模式适配不同场景**——简单的标准算法走模式 A，复杂的动态算法走模式 B
3. **`--mode upstream` 不能忘**——这是下游代理流量经过 Burp 的关键
4. **模式 B 浏览器不能关**——JSRPC 依赖 WebSocket 长连接
5. **先抓包确认格式**——AI 会自动做，但你自己也要心里有数

### 9.3 完整工作链路图

```
人类:   一句话指令 ──→ Claude Code ──→ MCP 浏览器调试 ──→ 目标网站
                           │
                      AI 分析加密逻辑
                           │
                      AI 生成脚本 & 启动命令
                           │
人类:   执行启动命令 ──→ mitmproxy 代理启动 ──→ Burp 显示明文
                           │
                      [开始测试]
```

> [图片: AICryptoProxy 完整工作链路的架构图]

### 9.4 参考资料

#### 本文配套项目

- [AICryptoProxy](https://github.com/yourusername/AICryptoProxy) — 完整项目代码

#### 第三方依赖

- [JsRpc](https://github.com/jxhczhl/JsRpc) — JSRPC 远程调用浏览器方法
- [mitmproxy 官方文档](https://docs.mitmproxy.org/) — mitmproxy 脚本开发指南
- [Claude Code](https://claude.ai/code) — AI 编程助手
- [pycryptodome](https://pycryptodome.readthedocs.io/) — Python 加密库
- [Burp Suite](https://portswigger.net/burp) — Web 安全测试工具
