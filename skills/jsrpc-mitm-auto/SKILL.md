---
name: jsrpc-mitm-auto
description: 结合 JSRPC + mitmproxy，零逆向自动加解密。无需分析算法、提取 Key，直接让浏览器原生 JS 函数处理加解密，通过 JSRPC 桥接给 mitmproxy 调用。
---

# jsrpc-mitm-auto — 零逆向自动加解密

## 核心理念

**不需要逆向分析加密算法、提取 Key、阅读混淆代码。**

```
浏览器(注入HlClient) ←WS→ JSRPC服务端(:12080) ←HTTP→ mitmproxy ←→ Burp
```

浏览器里本来就运行着完整的加解密函数，JSRPC 让 mitmproxy 可以直接调它们。  
mitmproxy 脚本里**一行加解密代码都不用写**。

---

## 完整链路

```
浏览器(设代理:8082)
  → 下游mitmproxy(:8082)
      → 调 JSRPC "decrypt" 解密请求
      → 明文转发给 Burp(:8080)
  → Burp 看明文、改明文
  → 上游mitmproxy(:8083)
      → 调 JSRPC "encrypt" 加密请求
      → 密文发送给服务器
```

---

## 工作流程

### Phase 0: 检查 JSRPC 服务端

```bash
# 如果没启动，先启动
"F:\JSReverser-MCP\JSRPC\window_amd64.exe" -c "F:\JSReverser-MCP\JSRPC\config.yaml"

# 验证
curl http://127.0.0.1:12080/go
# → {"data":"请传入action来调用客户端方法","status":200}
```

### Phase 1: 启动浏览器 + 连接 js-reverse MCP

```bash
# 启动 Chrome（如果需要）
"C:\Users\huangzonghui\AppData\Local\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir="C:\Users\huangzonghui\AppData\Local\Temp\chrome_debug_9222" --no-first-run --no-default-browser-check --new-window "https://target.com"
```

用 js-reverse MCP 连接页面。

### Phase 2: 定位加密函数入口

使用 `search_in_sources` 搜索加密关键词，找到目标函数在 window 下的路径。

**常见模式：**

| 情况 | 做法 |
|------|------|
| CryptoJS 全局可用 | 注册时直接调用 `CryptoJS.AES.encrypt/decrypt` |
| 全局函数 | 如 `window.encryptData`，直接注册 |
| 对象方法 | 如 `window.app.crypto.sign`，通过路径获取 |
| 闭包内函数 | 用 `search_in_sources` 找到函数名，通过 `trace_function` 定位 |
| 固定 Key/IV | 可从源码或 JS 变量中提取后写进 action |
| 动态 Key | action 中调用页面原有的加密函数（而非重新实现） |

**判断 CryptoJS 是否可用：**
```javascript
typeof CryptoJS !== 'undefined' && CryptoJS.AES
```

### Phase 3: 生成注入 JS 文件

根据函数定位结果，生成完整的 `jsrpc_inject.js` 文件。  
**核心模板如下，按需修改 CryptoJS 的 key/iv 或替换为实际的函数调用：**

```javascript
// ============================================================
// JSRPC 浏览器端注入脚本 - 自动连接并注册 encrypt/decrypt
// 用法: 控制台执行 / Tampermonkey / inject_preload_script
// ============================================================
;(function() {
    // ===== 1. HlClient 核心类 =====
    // (直接嵌入完整客户端，不依赖外部文件)
    var rpc_client_id;
    var HlClient = function (wsURL) { /* ... 完整 HlClient 实现 ... */ };
    // 原型方法: connect, send, regAction, _reportActions, handlerRequest, sendResult
    // 具体实现见 F:\JSReverser-MCP\JSRPC\客户端注入.js.yaml

    // ===== 2. 等待目标库就绪 =====
    // 必须等目标加密库加载完再注册 action，否则 CryptoJS 等为 undefined
    function waitForLib(callback, retries) {
        retries = retries || 0;
        if (retries > 50) {  // 最多等 10 秒
            console.log('[JSRPC] 目标库未加载，跳过自动注册');
            return;
        }
        if (typeof CryptoJS !== 'undefined' && CryptoJS.AES) {
            callback();
        } else {
            setTimeout(function() { waitForLib(callback, retries + 1); }, 200);
        }
    }

    // ===== 3. 注册 action =====
    function registerActions() {
        try {
            var client = new HlClient("ws://127.0.0.1:12080/ws?group=mitm&name=page");

            // 加密 action — 替换为实际加密逻辑
            client.regAction("encrypt", function(resolve, param) {
                try {
                    // ★★★ 从这里开始根据实际情况修改 ★★★
                    var key = CryptoJS.enc.Utf8.parse('1234567890123456');
                    var iv = CryptoJS.enc.Utf8.parse('1234567890123456');
                    var input = typeof param === 'object' ? JSON.stringify(param) : param;
                    var encrypted = CryptoJS.AES.encrypt(input, key, {
                        iv: iv,
                        mode: CryptoJS.mode.CBC,
                        padding: CryptoJS.pad.Pkcs7
                    });
                    resolve(encrypted.toString());
                } catch(e) {
                    resolve("ERROR: " + e.message);
                }
            });

            // 解密 action — 与 encrypt 对应
            client.regAction("decrypt", function(resolve, param) {
                try {
                    // ★★★ 从这里开始根据实际情况修改 ★★★
                    var key = CryptoJS.enc.Utf8.parse('1234567890123456');
                    var iv = CryptoJS.enc.Utf8.parse('1234567890123456');
                    var input = typeof param === 'object' ? param.toString() : param;
                    var decrypted = CryptoJS.AES.decrypt(input, key, {
                        iv: iv,
                        mode: CryptoJS.mode.CBC,
                        padding: CryptoJS.pad.Pkcs7
                    });
                    resolve(decrypted.toString(CryptoJS.enc.Utf8));
                } catch(e) {
                    resolve("ERROR: " + e.message);
                }
            });

            console.log('[JSRPC] encrypt/decrypt 已注册');
        } catch(e) {
            console.log('[JSRPC] 注册失败:', e.message);
        }
    }

    // ===== 4. 页面加载完成后执行 =====
    if (document.readyState === 'complete') {
        waitForLib(registerActions);
    } else {
        window.addEventListener('load', function() {
            waitForLib(registerActions);
        });
    }
})();
```

**写成 JS 文件写入磁盘**，路径如 `output/jsrpc_inject.js`。

### Phase 4: 注入到页面

方式一：**js-reverse preload 注入**（调试浏览器，刷新自动生效）

```
mcp__js-reverse__inject_preload_script(script="<文件内容>")
```

方式二：**控制台执行**（一次性，适合任何浏览器）

```javascript
// 将生成的 jsrpc_inject.js 全部内容粘贴到控制台回车
```

方式三：**Tampermonkey 脚本**（持久化，适合普通浏览器）

### Phase 5: 验证 JSRPC 调用

```bash
python3 -c "
import requests, json

# 测试加密
resp = requests.get('http://127.0.0.1:12080/go', params={
    'group': 'mitm', 'action': 'encrypt',
    'param': json.dumps({'username':'admin','password':'123456'})
})
print('加密:', resp.json())

# 测试解密
enc = resp.json().get('data', '')
resp2 = requests.get('http://127.0.0.1:12080/go', params={
    'group': 'mitm', 'action': 'decrypt', 'param': enc
})
print('解密:', resp2.json())
"
```

如果报错，打开浏览器 F12 Console 看 JSRPC 连接日志。

### Phase 5.5: 抓包确认加密请求的原始格式（关键！）

**不要猜测加密请求的格式。** 先用浏览器触发一次真实请求，用 js-reverse 抓包看请求体长什么样：

```bash
# 1. 在浏览器中操作触发目标请求
# 2. 列出网络请求
mcp__js-reverse__network_request(action="list")

# 3. 查看具体的请求详情（找到 reqid）
mcp__js-reverse__network_request(action="get", reqid=1)
```

**重点观察：**
- Content-Type 是 `application/json` 还是 `application/x-www-form-urlencoded`？
- 加密数据放在哪个字段？常见格式举例：

| 格式类型 | 原始请求体示例 |
|---------|---------------|
| form body 单字段 | `data=Abc...123==` |
| form body 多字段独立加密 | `username=EncA...==&password=EncB...==` |
| JSON 嵌套密文 | `{"cipher":"Abc...==","iv":"xxx"}` |
| JSON 字段直接替换 | `{"username":"Enc...==","password":"Enc...=="}` |

**拿到真实格式后再写脚本**，而不是猜。

---

### Phase 6: 生成双代理脚本

生成 `jsrpc_client.py`、`downstream_jsrpc_proxy.py`、`upstream_jsrpc_proxy.py` 三个文件。

**jsrpc_client.py（JSRPC 调用封装）：**

```python
"""JSRPC 调用封装 - 供 mitmproxy 脚本调用"""
import requests
JSRPC_BASE = "http://127.0.0.1:12080"
JSRPC_GROUP = "mitm"

def jsrpc_call(action: str, param: str) -> str:
    url = f"{JSRPC_BASE}/go"
    try:
        resp = requests.get(url, params={
            "group": JSRPC_GROUP,
            "action": action,
            "param": param
        }, timeout=15)
        resp.raise_for_status()
        data = resp.json().get("data", "")
        if data.startswith("ERROR"):
            print(f"[JSRPC] 错误 ({action}): {data}")
            return ""
        return data
    except Exception as e:
        print(f"[JSRPC] 调用失败 ({action}): {e}")
        return ""
```

**下游代理脚本（downstream_jsrpc_proxy.py）：**

```python
#!/usr/bin/env python3
"""下游解密代理 - 调 JSRPC 解密浏览器请求"""
from mitmproxy import http
from jsrpc_client import jsrpc_call
import urllib.parse

TARGET_DOMAINS = ['target.com']
TARGET_PATHS = ['/api/endpoint']   # 修改为实际路径

class DownstreamJSRPCProxy:
    def request(self, flow: http.HTTPFlow) -> None:
        if not any(d in flow.request.pretty_url for d in TARGET_DOMAINS):
            return
        if not any(p in flow.request.pretty_url for p in TARGET_PATHS):
            return
        body = flow.request.text

        # ★★★ 根据 Phase 5.5 抓包结果修改这里的提取逻辑 ★★★
        # 示例 A: form body 单字段 data=<base64>
        # params = urllib.parse.parse_qs(body)
        # encrypted = params.get('data', [None])[0]
        #
        # 示例 B: form body 多字段独立加密
        # params = urllib.parse.parse_qs(body)
        # plain_username = jsrpc_call('decrypt', params.get('username', [None])[0])
        # plain_password = jsrpc_call('decrypt', params.get('password', [None])[0])
        #
        # 示例 C: JSON body {"cipher": "<base64>", "iv": "..."}
        # import json
        # parsed = json.loads(body)
        # encrypted = parsed.get('cipher', '')

        params = urllib.parse.parse_qs(body)
        encrypted = params.get('encryptedData', [None])[0]
        if not encrypted:
            return
        plaintext = jsrpc_call('decrypt', encrypted)
        if not plaintext:
            return
        print(f'[下游JSRPC] 解密: {flow.request.pretty_url} -> {plaintext}')
        flow.request.headers['Content-Type'] = 'application/json'
        flow.request.text = plaintext

    def response(self, flow: http.HTTPFlow) -> None:
        pass  # 如需加密响应回浏览器，在 response 中调 jsrpc_call('encrypt', ...)

addons = [DownstreamJSRPCProxy()]
```

**上游代理脚本（upstream_jsrpc_proxy.py）：**

```python
#!/usr/bin/env python3
"""上游加密代理 - 调 JSRPC 加密 Burp 明文请求"""
from mitmproxy import http
from jsrpc_client import jsrpc_call
import urllib.parse

TARGET_DOMAINS = ['target.com']
TARGET_PATHS = ['/api/endpoint']

class UpstreamJSRPCProxy:
    def request(self, flow: http.HTTPFlow) -> None:
        if not any(d in flow.request.pretty_url for d in TARGET_DOMAINS):
            return
        if not any(p in flow.request.pretty_url for p in TARGET_PATHS):
            return
        plaintext = flow.request.text
        if not plaintext:
            return
        encrypted = jsrpc_call('encrypt', plaintext)
        if not encrypted:
            return
        print(f'[上游JSRPC] 加密: {flow.request.pretty_url}')

        # ★★★ 根据 Phase 5.5 抓包结果修改这里的拼接逻辑 ★★★
        # 示例 A: form body 单字段 data=<base64>
        # from urllib.parse import quote
        # enc_body = f"data={quote(encrypted)}"
        # flow.request.headers['Content-Type'] = 'application/x-www-form-urlencoded'
        #
        # 示例 B: form body 多字段独立加密
        # enc_body = f"username={quote(enc_u)}&password={quote(enc_p)}"
        #
        # 示例 C: JSON body {"cipher": "<base64>"}
        # import json
        # enc_body = json.dumps({"cipher": encrypted})
        # flow.request.headers['Content-Type'] = 'application/json'
        #
        # 关键: 必须和原始请求的 Content-Type + 字段名完全一致

        enc_body = f'encryptedData={urllib.parse.quote(encrypted)}'
        flow.request.headers['Content-Type'] = 'application/x-www-form-urlencoded; charset=utf-8'
        flow.request.text = enc_body

    def response(self, flow: http.HTTPFlow) -> None:
        pass

addons = [UpstreamJSRPCProxy()]
```

---

## 输出文件结构

```
output/
├── jsrpc_inject.js              # 浏览器端注入 JS（HlClient + action 注册）
├── jsrpc_client.py              # JSRPC HTTP API 封装
├── downstream_jsrpc_proxy.py    # 下游解密代理
└── upstream_jsrpc_proxy.py      # 上游加密代理
```

---

## 启动命令

```bash
# 1. JSRPC 服务端
"F:\JSReverser-MCP\JSRPC\window_amd64.exe" -c "F:\JSReverser-MCP\JSRPC\config.yaml"

# 2. 下游解密代理（必须 --mode upstream 指向 Burp）
mitmdump -s output/downstream_jsrpc_proxy.py --mode upstream:http://127.0.0.1:8080 -p 8082

# 3. 上游加密代理
mitmdump -s output/upstream_jsrpc_proxy.py -p 8083
```

### 代理配置

```
浏览器代理 -> 127.0.0.1:8082
Burp 上游代理 -> *target.com* → 127.0.0.1:8083
```

---

## 常见场景注入示例

### 场景 A: 全局加密函数（无库依赖）

```javascript
// 注册的 action 中直接调页面已有的加密函数
client.regAction("encrypt", function(resolve, param) {
    try {
        var result = window.encryptData(param);
        resolve(result);
    } catch(e) { resolve("ERROR: " + e.message); }
});

client.regAction("decrypt", function(resolve, param) {
    try {
        var result = window.decryptData(param);
        resolve(result);
    } catch(e) { resolve("ERROR: " + e.message); }
});
```

### 场景 B: 对象方法 + this 绑定

```javascript
client.regAction("encrypt", function(resolve, param) {
    try {
        var result = window.app.crypto.encrypt.call(window.app.crypto, param);
        resolve(result);
    } catch(e) { resolve("ERROR: " + e.message); }
});
```

### 场景 C: 需动态定位的函数

先通过 `search_in_sources` 找到函数名，再通过 `evaluate_script` 测试调用：

```javascript
client.regAction("encrypt", function(resolve, param) {
    try {
        // 用 search_in_sources 确认路径后替换
        var fn = window['a1b2c3'] || window['encryptData'];
        var result = fn(param);
        resolve(result);
    } catch(e) { resolve("ERROR: " + e.message); }
});
```

### 场景 D: Promise 异步函数

```javascript
client.regAction("encrypt", function(resolve, param) {
    window.asyncEncrypt(param).then(function(result) {
        resolve(result);
    }).catch(function(e) {
        resolve("ERROR: " + e.message);
    });
});
```

---

## waitForLib 时序说明

为什么需要 `waitForLib`：

1. `inject_preload_script` 注入的脚本在页面**最早期执行**
2. 此时 `<script src="crypto-js.min.js">` **可能还没加载完**
3. 直接执行 `CryptoJS.AES.encrypt` 会报 `undefined`
4. `waitForLib` 每 200ms 轮询一次，最多等 10 秒
5. 等目标库可用后再注册 action

如果目标库不是 CryptoJS，修改 `waitForLib` 中的判断条件即可。

---

---

## ⚠️ 核心原则: 先抓包确认格式，再写脚本

**最容易犯的错误：** 想当然地假设加密请求的格式，不验证就直接写 `data=<密文>` 或 `encryptedData=<密文>`。

**正确的做法（写在 Phase 5.5）：**

```
1. 浏览器触发真实请求
2. js-reverse 抓包看请求体
3. 确认:
   - Content-Type 是什么？
   - 加密数据放在哪个字段？
   - 是单个字段还是多字段独立加密？
   - 是 form body 还是 JSON body？
4. 按真实格式写脚本
```

**常见格式速查：**

| Content-Type | 请求体示例 | 脚本处理方法 |
|-------------|-----------|-------------|
| `x-www-form-urlencoded` | `data=Abc...==` | `parse_qs` 提取 → `quote()` 拼接回去 |
| `x-www-form-urlencoded` | `u=EncA...==&p=EncB...==` | 每个字段独立解密/加密 |
| `application/json` | `{"cipher":"Abc...=="}` | `json.loads` + `json.dumps` |
| `application/json` | `{"data":{"username":"Enc...=="}}` | 深层字段替换 |

**关于 base64：** 当且仅当格式是 `x-www-form-urlencoded` 且手动拼字符串时，才需要 `quote()`。用 `requests` 的 `data=dict` 参数或者 JSON body 都不需要担心这个。

---

## 故障排除

### JSRPC 服务端无法启动
- 检查端口是否被占用：`netstat -ano | grep 12080`
- 检查 config.yaml 路径是否正确

### HlClient 注入失败
- 确认 `HlClient` 类完整注入: `typeof HlClient !== 'undefined'`
- 查看浏览器 Console 日志是否有 `rpc连接成功` 或 `rpc连接出错`

### 浏览器 Console 显示"rpc连接成功"但 curl 调用报错
- 检查 JSRPC 服务端日志，看 action 是否注册成功
- 确认 curl 的 group 和 action 参数与注册时一致

### JSRPC 调用超时
- 默认 30 秒超时（config.yaml 中 `DefaultTimeOut`）
- 检查浏览器是否被弹窗/断点阻塞
- 异步函数需要在 action 中 await 或 then

### JSRPC 调用返回 "action没找到"
- 确认 HlClient 的 `_reportActions` 正常上报
- 可能是 WS 重连后未重新注册 action，刷新页面重试

---
