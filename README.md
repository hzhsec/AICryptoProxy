
# AICryptoProxy

> **AI 驱动的 Web 加密流量渗透测试自动化代理框架**

[![Claude Code](https://img.shields.io/badge/Claude_Code-Skill-blue)](https://claude.ai/code)
[![Python](https://img.shields.io/badge/Python-3.12+-green)](https://python.org)
[![mitmproxy](https://img.shields.io/badge/mitmproxy-10+-orange)](https://mitmproxy.org)
[![License](https://img.shields.io/badge/License-MIT-red)](LICENSE)

---

## 概述

**AICryptoProxy** 是一个基于 [Claude Code](https://claude.ai/code) + [MCP](https://docs.claude.ai) 的智能渗透测试框架，专为解决前端加密 Web 应用的流量加解密问题而设计。

通过 Claude Code 的 MCP 技能系统，框架能够在**几十秒内**自动完成传统需要数小时的 JS 逆向分析工作，生成可直接使用的 mitmproxy 加解密代理，配合 Burp Suite 实现无缝的明文操作体验。

### 核心理念

```
用户输入目标URL → AI自动分析加密逻辑 → 生成加解密代理 → Burp中操作明文
     ↓                    ↓                      ↓                ↓
  一句话指令        MCP浏览器调试         mitmproxy脚本      无需任何手动处理
```

### 解决的问题

| 传统痛点 | AICryptoProxy 方案 |
|---------|-------------------|
| 手动定位加密函数耗时数小时 | AI 通过 MCP 自动搜索脚本、断点追踪 |
| 扣代码 + 补环境繁琐易错 | 自动提取 Key 生成 Python 代码 / 零逆向 JSRPC 桥接 |
| 动态 Key 需要额外处理逻辑 | JSRPC 模式让浏览器原生处理，自动适配动态 Key |
| 编写 mitmproxy 脚本需要调试 | 一键生成经过验证的生产级脚本 |

---

## 工作模式

AICryptoProxy 提供两种互补的工作模式，由 Claude Code 的 Skill 自动完成：

### 模式 A：Direct Crypto（直接加解密）

skill:**mitm_proxy**

适用于标准算法、Key 固定的场景。

```
浏览器 → mitmproxy(:8082)[自动解密] → Burp[:8080] → mitmproxy(:8083)[自动加密] → 服务器
         ↑                          ↑     ↑                             ↑
    AI 分析 JS 加密算法     操作明文请求  Burp 修改      AI 生成 Python 加密代码
    提取 Key 和 IV                      不需要改重放                             使用同密钥加密
```

**AI 自动完成：**
1. 通过 js-reverse MCP 连接浏览器
2. 搜索脚本中的加密关键字（encrypt、AES、RSA 等）
3. 在断点处自动提取 Key、IV、算法参数
4. 生成 `downstream_decrypt_proxy.py` + `upstream_encrypt_proxy.py`
5. 输出启动命令

### 模式 B：JSRPC Bridge（零逆向桥接）

skill:**jsrpc-mitm-auto**

适用于算法复杂、混淆严重、Key 动态生成的场景。

```
                     ┌─── JSRPC服务(:12080) ───┐
                     │     ↕ WebSocket           │
浏览器原生JS加密 ←──→│   浏览器标签页(保持打开) │←──→ mitmproxy 脚本
                     └──────────────────────────┘
```

**AI 自动完成：**
1. 自动生成 `jsrpc_inject.js`（含 HlClient + 加密/解密 action 注册）
2. 自动生成 `jsrpc_client.py`（HTTP 调用封装）
3. 自动生成 `downstream_jsrpc_proxy.py` + `upstream_jsrpc_proxy.py`
4. 提示用户在浏览器 Console 中粘贴注入脚本
5. 输出完整启动命令

---

## 快速开始

### 环境要求

```bash
# 1. Python 3.12+
python --version

# 2. 安装依赖
pip install mitmproxy pycryptodome requests

# 3. （模式 B 需要）下载 JSRPC 服务端
#    https://github.com/jxhczhl/JsRpc/releases

# 4. 安装 Claude Code
#    https://claude.ai/code

# 5. 安装 MCP 服务（js-reverse）
#    用于浏览器调试和 JS 逆向分析
```

### 使用流程

```bash
# 方式一：使用 Claude Code Skill 自动完成
# 在项目目录中运行 Claude Code，然后输入：

# 模式 A - 直接逆向：
"用 mitm_proxy 技能帮我分析 https://target.com 的加密逻辑，生成加解密代理"

# 模式 B - JSRPC 零逆向：
"用 jsrpc-mitm-auto 技能为 https://target.com 设置 JSRPC 加解密代理"

# Claude Code 会自动：
# 1. 启动浏览器并导航到目标
# 2. 分析 JS 加密逻辑
# 3. 生成对应的代理脚本
# 4. 提供完整的启动命令
```

### 手动启动

```bash
# ──── 模式 A：直接加解密 ────

# 终端 1：启动 Burp Suite（监听 :8080）

# 终端 2：启动下游解密代理
mitmdump -s proxy_scripts/downstream_decrypt_proxy.py \
         --mode upstream:http://127.0.0.1:8080 -p 8082

# 终端 3：启动上游加密代理
mitmdump -s proxy_scripts/upstream_encrypt_proxy.py -p 8083

# 配置浏览器代理为 127.0.0.1:8082
# 配置 Burp 上游代理 → 127.0.0.1:8083


# ──── 模式 B：JSRPC 零逆向 ────

# 终端 1：启动 JSRPC 服务端
jsrpc.exe

# 终端 2：启动 Burp Suite

# 在浏览器 Console 中粘贴 inject_scripts/jsrpc_inject.js

# 终端 3：启动下游代理
mitmdump -s proxy_scripts/downstream_jsrpc_proxy.py \
         --mode upstream:http://127.0.0.1:8080 -p 8082

# 终端 4：启动上游代理
mitmdump -s proxy_scripts/upstream_jsrpc_proxy.py -p 8083


#浏览器配置代理
使用插件将浏览器代理到本地的8082端口

#BurpSuite
配置上游代理到本地的8083端口

```

**最终实现**：

浏览器---->插件----->`mitmdump`解密----->`Burpsuite`修改数据包------>`mitmdump`加密

---

## 项目文件

```
AICryptoProxy/
├── README.md
├── requirements.txt              # Python 依赖
│
├── proxy_scripts/                # mitmproxy 代理脚本
│   ├── downstream_decrypt_proxy.py   # [模式A] 下游解密代理
│   ├── upstream_encrypt_proxy.py     # [模式A] 上游加密代理
│   ├── downstream_jsrpc_proxy.py     # [模式B] 下游 JSRPC 代理
│   ├── upstream_jsrpc_proxy.py       # [模式B] 上游 JSRPC 代理
│   └── jsrpc_client.py              # JSRPC HTTP 调用封装
|
|---skills  #mitm_proxy对于模式A，jsrpc-mitm-auto对应模式B
│
├── inject_scripts/               # 浏览器注入脚本
│   └── jsrpc_inject.js               # [模式B] JSRPC 注入脚本
│
├── docs/
│   └── AICryptoProxy_完全指南.md     # 完整使用文章
│
└── test/                          # 测试输出
```

---

## 工作流程对比

| 阶段 | 传统手动方式 | AICryptoProxy (AI) |
|------|------------|-------------------|
| 定位加密函数 | 手动搜索关键字、下断点、回溯调用栈 | AI 自动搜索脚本、追踪调用链 |
| 提取密钥 | 手动在 Watch/Console 中查看变量 | AI 自动捕获函数参数和返回值 |
| 算法分析 | 阅读混淆代码理解算法 | AI 自动识别算法类型（AES/RSA/SM4） |
| 编写脚本 | 手动写 Python 加解密代码 | AI 生成完整 mitmproxy 脚本 |
| 环境配置 | 手动安装配置每个组件 | 交互式引导，一键执行 |
| 故障排查 | 逐行看日志定位问题 | AI 分析错误并给出修复方案 |

---

## 架构设计

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Claude Code (AI 大脑)                         │
│  ┌─────────────┐  ┌──────────────┐  ┌───────────────────────────┐  │
│  │ MCP js-reverse│──│ 分析/提取/生成 │──│ Skill 指令引擎            │  │
│  │ (浏览器调试)  │  │ (决策引擎)    │  │ (工作流编排)              │  │
│  └─────────────┘  └──────────────┘  └───────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
         │                        │                          │
         ▼                        ▼                          ▼
  ┌──────────────┐    ┌──────────────────┐    ┌──────────────────────┐
  │ 浏览器调试    │    │ 生成代理脚本      │    │ JSRPC 桥接            │
  │ (搜索/断点/   │    │ (downstream_     │    │ (注入脚本 +          │
  │  提取Key)    │    │  upstream_.py)   │    │  jsrpc_client.py)    │
  └──────────────┘    └──────────────────┘    └──────────────────────┘
```

---

## 适用场景

- **渗透测试**：在 Burp Suite 中操作明文请求，自由修改和重放
- **安全审计**：快速理解加密 API 的请求/响应结构
- **漏洞挖掘**：绕过前端加密直接测试后端接口安全性
- **CTF 挑战**：快速分析并解决 Web 加密类题目

---

## 相关资源

- [JsRpc](https://github.com/jxhczhl/JsRpc) — JSRPC 远程调用浏览器方法
- [mitmproxy](https://docs.mitmproxy.org/) — 中间人代理框架
- [Claude Code](https://claude.ai/code) — AI 编程助手
- [pycryptodome](https://pycryptodome.readthedocs.io/) — Python 加密库
- [Burp Suite](https://portswigger.net/burp) — Web 安全测试工具
