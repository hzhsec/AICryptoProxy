// ============================================================
// JSRPC 浏览器端注入脚本
// 用法: 在浏览器控制台执行整个脚本，或 inject_preload_script 注入
// 连接后自动注册 encrypt / decrypt 两个 action
// ============================================================

;(function() {
    // ===== 1. HlClient 核心类 =====
    var rpc_client_id;
    var HlClient = function (wsURL) {
        this.wsURL = wsURL;
        this.handlers = {
            _execjs: function (resolve, param) {
                try {
                    var fn = new Function('return (async () => { ' + param + ' })()');
                    var result = fn();
                    if (result && typeof result.then === 'function') {
                        result.then(function(res) {
                            resolve(res !== undefined ? res : "执行成功(无返回值)");
                        }).catch(function(err) {
                            resolve("执行错误: " + (err.message || err));
                        });
                    } else {
                        resolve(result !== undefined ? result : "执行成功(无返回值)");
                    }
                } catch (err) {
                    resolve("语法错误: " + (err.message || err));
                }
            }
        };
        this.socket = undefined;
        if (!wsURL) {
            throw new Error('wsURL can not be empty!!');
        }
        this.connect();
    };
    HlClient.prototype.connect = function () {
        if (this.wsURL.indexOf("clientId=") === -1 && rpc_client_id) {
            this.wsURL += "&clientId=" + rpc_client_id;
        }
        console.log('[JSRPC] begin of connect to wsURL: ' + this.wsURL);
        var _this = this;
        try {
            this.socket = new WebSocket(this.wsURL);
            this.socket.onmessage = function (e) {
                _this.handlerRequest(e.data);
            };
        } catch (e) {
            console.log('[JSRPC] connection failed, reconnect after 10s');
            setTimeout(function () {
                _this.connect();
            }, 10000);
        }
        this.socket.onclose = function () {
            console.log('[JSRPC] rpc已关闭');
            setTimeout(function () {
                _this.connect();
            }, 10000);
        };
        this.socket.addEventListener('open', function (event) {
            console.log('[JSRPC] rpc连接成功');
            _this._reportActions();
        });
        this.socket.addEventListener('error', function (event) {
            console.error('[JSRPC] rpc连接出错:', event.error);
        });
    };
    HlClient.prototype.send = function (msg) {
        this.socket.send(msg);
    };
    HlClient.prototype.regAction = function (func_name, func) {
        if (typeof func_name !== 'string') {
            throw new Error("an func_name must be string");
        }
        if (typeof func !== 'function') {
            throw new Error("must be function");
        }
        console.log('[JSRPC] register func_name: ' + func_name);
        this.handlers[func_name] = func;
        this._reportActions();
        return true;
    };
    HlClient.prototype._reportActions = function () {
        var actions = Object.keys(this.handlers);
        if (this.socket && this.socket.readyState === WebSocket.OPEN) {
            this.send(JSON.stringify({
                "action": "_registerActions",
                "message_id": "",
                "response_data": JSON.stringify(actions)
            }));
        }
    };
    HlClient.prototype.handlerRequest = function (requestJson) {
        var _this = this;
        try {
            var result = JSON.parse(requestJson);
        } catch (error) {
            console.log('[JSRPC] 请求信息解析错误', requestJson);
            return;
        }
        if (result["registerId"]) {
            rpc_client_id = result['registerId'];
            return;
        }
        if (!result['action'] || !result["message_id"]) {
            console.warn('[JSRPC] 没有方法或者消息id,不处理');
            return;
        }
        var action = result["action"], message_id = result["message_id"];
        var theHandler = this.handlers[action];
        if (!theHandler) {
            this.sendResult(action, message_id, 'action没找到');
            return;
        }
        try {
            if (!result["param"]) {
                const async_result = theHandler(function (response) {
                    _this.sendResult(action, message_id, response);
                });
                if (async_result && typeof async_result.then === "function") {
                    async_result.catch(e => {
                        _this.sendResult(action, message_id, "" + e);
                    });
                }
                return;
            }
            var param = result["param"];
            try {
                param = JSON.parse(param);
            } catch (e) {}
            theHandler(function (response) {
                _this.sendResult(action, message_id, response);
            }, param);
        } catch (e) {
            console.log('[JSRPC] error: ' + e);
            _this.sendResult(action, message_id, "" + e);
        }
    };
    HlClient.prototype.sendResult = function (action, message_id, e) {
        if (typeof e === 'object' && e !== null) {
            try {
                e = JSON.stringify(e);
            } catch (v) {
                console.log(v);
            }
        }
        this.send(JSON.stringify({"action": action, "message_id": message_id, "response_data": e}));
    };

    // ===== 2. 等待 CryptoJS 就绪并注册 action =====
    function waitForCrypto(callback, retries) {
        retries = retries || 0;
        if (retries > 50) {  // 最多等 10 秒
            console.log('[JSRPC] CryptoJS 未加载，跳过自动注册');
            return;
        }
        if (typeof CryptoJS !== 'undefined' && CryptoJS.AES) {
            callback();
        } else {
            setTimeout(function() { waitForCrypto(callback, retries + 1); }, 200);
        }
    }

    function registerActions() {
        try {
            var client = new HlClient("ws://127.0.0.1:12080/ws?group=mitm&name=page");

            // 加密 action
            client.regAction("encrypt", function(resolve, param) {
                try {
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

            // 解密 action
            client.regAction("decrypt", function(resolve, param) {
                try {
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

    // ===== 3. 页面加载完成后开始 =====
    if (document.readyState === 'complete') {
        waitForCrypto(registerActions);
    } else {
        window.addEventListener('load', function() {
            waitForCrypto(registerActions);
        });
    }
})();
