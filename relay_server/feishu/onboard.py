"""
Hermes Relay - 飞书扫码注册模块
通过扫描二维码自动创建飞书机器人应用

流程:
1. 调用飞书注册接口开始设备码流程
2. 生成二维码 URL
3. 用户用飞书扫码
4. 飞书自动创建应用并返回 app_id/app_secret
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any, Dict, Optional
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

logger = logging.getLogger(__name__)

# 飞书/Lark 端点
_ACCOUNTS_URLS = {
    "feishu": "https://accounts.feishu.cn",
    "lark": "https://accounts.larksuite.com",
}
_OPEN_URLS = {
    "feishu": "https://open.feishu.cn",
    "lark": "https://open.larksuite.com",
}
_REGISTRATION_PATH = "/oauth/v1/app/registration"
_REQUEST_TIMEOUT = 10


def _accounts_base_url(domain: str) -> str:
    return _ACCOUNTS_URLS.get(domain, _ACCOUNTS_URLS["feishu"])


def _open_base_url(domain: str) -> str:
    return _OPEN_URLS.get(domain, _OPEN_URLS["feishu"])


def _post_registration(base_url: str, body: Dict[str, str]) -> dict:
    """POST 到注册端点"""
    url = f"{base_url}{_REGISTRATION_PATH}"
    data = urlencode(body).encode("utf-8")
    req = Request(url, data=data, headers={"Content-Type": "application/x-www-form-urlencoded"})
    try:
        with urlopen(req, timeout=_REQUEST_TIMEOUT) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except HTTPError as exc:
        body_bytes = exc.read()
        if body_bytes:
            try:
                return json.loads(body_bytes.decode("utf-8"))
            except (ValueError, json.JSONDecodeError):
                raise exc from None
        raise


def _init_registration(domain: str = "feishu") -> None:
    """验证环境支持 client_secret 认证"""
    base_url = _accounts_base_url(domain)
    res = _post_registration(base_url, {"action": "init"})
    methods = res.get("supported_auth_methods") or []
    if "client_secret" not in methods:
        raise RuntimeError(
            f"飞书/Lark 注册环境不支持 client_secret 认证。支持的方法: {methods}"
        )


def _begin_registration(domain: str = "feishu") -> dict:
    """
    开始设备码流程
    
    调用飞书注册接口，返回:
    - device_code: 设备码
    - qr_url: 二维码 URL (用户扫码用)
    - user_code: 用户码
    - interval: 轮询间隔
    - expire_in: 过期时间
    """
    base_url = _accounts_base_url(domain)
    res = _post_registration(base_url, {
        "action": "begin",
        "archetype": "PersonalAgent",  # 关键: 创建个人代理类型的应用
        "auth_method": "client_secret",
        "request_user_info": "open_id",
    })
    
    device_code = res.get("device_code")
    if not device_code:
        raise RuntimeError("飞书/Lark 注册未返回 device_code")
    
    qr_url = res.get("verification_uri_complete", "")
    if "?" in qr_url:
        qr_url += "&from=hermes-relay&tp=hermes-relay"
    else:
        qr_url += "?from=hermes-relay&tp=hermes-relay"
    
    return {
        "device_code": device_code,
        "qr_url": qr_url,
        "user_code": res.get("user_code", ""),
        "interval": res.get("interval") or 5,
        "expire_in": res.get("expire_in") or 600,
    }


def _poll_registration(
    device_code: str,
    interval: int,
    expire_in: int,
    domain: str = "feishu",
    callback=None,
) -> Optional[dict]:
    """
    轮询直到用户扫码
    
    成功返回:
    - app_id: 应用 ID
    - app_secret: 应用密钥
    - domain: 域名 (feishu/lark)
    - open_id: 用户 open_id
    """
    deadline = time.monotonic() + expire_in
    current_domain = domain
    domain_switched = False
    poll_count = 0

    while time.monotonic() < deadline:
        base_url = _accounts_base_url(current_domain)
        try:
            res = _post_registration(base_url, {
                "action": "poll",
                "device_code": device_code,
                "tp": "ob_app",
            })
        except (URLError, OSError, json.JSONDecodeError):
            time.sleep(interval)
            continue

        poll_count += 1
        
        # 回调通知进度
        if callback:
            callback("polling", poll_count)

        # 域名自动检测 (如果用户用的是 Lark 国际版)
        user_info = res.get("user_info") or {}
        tenant_brand = user_info.get("tenant_brand")
        if tenant_brand == "lark" and not domain_switched:
            current_domain = "lark"
            domain_switched = True

        # 成功: 返回了 client_id 和 client_secret
        if res.get("client_id") and res.get("client_secret"):
            if callback:
                callback("success", 0)
            return {
                "app_id": res["client_id"],
                "app_secret": res["client_secret"],
                "domain": current_domain,
                "open_id": user_info.get("open_id"),
            }

        # 终止错误
        error = res.get("error", "")
        if error in {"access_denied", "expired_token"}:
            if callback:
                callback("denied", 0)
            logger.warning("[Feishu] 注册 %s", error)
            return None

        # authorization_pending 或未知 - 继续轮询
        time.sleep(interval)

    if callback:
        callback("timeout", 0)
    logger.warning("[Feishu] 轮询超时 (%ds)", expire_in)
    return None


def _render_qr_terminal(url: str) -> bool:
    """尝试在终端渲染二维码"""
    try:
        import qrcode
        qr = qrcode.QRCode(
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=1,
            border=1,
        )
        qr.add_data(url)
        qr.make(fit=True)
        qr.print_ascii(invert=True)
        return True
    except ImportError:
        return False
    except Exception:
        return False


def probe_bot(app_id: str, app_secret: str, domain: str) -> Optional[dict]:
    """
    验证 bot 连接性
    
    调用 /open-apis/bot/v3/info 获取 bot 信息
    """
    base_url = _open_base_url(domain)
    try:
        # 获取 tenant_access_token
        token_data = json.dumps({
            "app_id": app_id,
            "app_secret": app_secret,
        }).encode("utf-8")
        token_req = Request(
            f"{base_url}/open-apis/auth/v3/tenant_access_token/internal",
            data=token_data,
            headers={"Content-Type": "application/json"},
        )
        with urlopen(token_req, timeout=_REQUEST_TIMEOUT) as resp:
            token_res = json.loads(resp.read().decode("utf-8"))

        access_token = token_res.get("tenant_access_token")
        if not access_token:
            return None

        # 获取 bot 信息
        bot_req = Request(
            f"{base_url}/open-apis/bot/v3/info",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            },
        )
        with urlopen(bot_req, timeout=_REQUEST_TIMEOUT) as resp:
            bot_res = json.loads(resp.read().decode("utf-8"))

        if bot_res.get("code") != 0:
            return None
        
        bot = bot_res.get("bot") or bot_res.get("data", {}).get("bot") or {}
        return {
            "bot_name": bot.get("app_name") or bot.get("bot_name"),
            "bot_open_id": bot.get("open_id"),
        }
    except (URLError, OSError, KeyError, json.JSONDecodeError) as exc:
        logger.debug("[Feishu] Bot 探测失败: %s", exc)
        return None


def qr_register(
    initial_domain: str = "feishu",
    timeout_seconds: int = 600,
    callback=None,
) -> Optional[dict]:
    """
    运行飞书/Lark 扫码注册流程
    
    扫码后会自动创建一个新的 bot 应用，返回:
    {
        "app_id": str,        # 新创建的应用 ID
        "app_secret": str,    # 新创建的应用密钥
        "domain": "feishu" | "lark",
        "open_id": str | None,
        "bot_name": str | None,
        "bot_open_id": str | None,
    }
    
    失败返回 None
    """
    try:
        return _qr_register_inner(
            initial_domain=initial_domain,
            timeout_seconds=timeout_seconds,
            callback=callback,
        )
    except (RuntimeError, URLError, OSError, json.JSONDecodeError) as exc:
        logger.warning("[Feishu] 注册失败: %s", exc)
        if callback:
            callback("error", str(exc))
        return None


def _qr_register_inner(
    initial_domain: str,
    timeout_seconds: int,
    callback=None,
) -> Optional[dict]:
    """执行 init -> begin -> poll -> probe 流程"""
    
    # 步骤 1: 初始化
    if callback:
        callback("init", 0)
    _init_registration(initial_domain)
    
    # 步骤 2: 开始注册 (获取二维码)
    if callback:
        callback("begin", 0)
    begin = _begin_registration(initial_domain)
    
    # 步骤 3: 显示二维码
    qr_url = begin["qr_url"]
    if callback:
        callback("qr_url", qr_url)
    
    # 步骤 4: 轮询等待扫码
    if callback:
        callback("waiting", 0)
    
    result = _poll_registration(
        device_code=begin["device_code"],
        interval=begin["interval"],
        expire_in=min(begin["expire_in"], timeout_seconds),
        domain=initial_domain,
        callback=callback,
    )
    
    if not result:
        return None

    # 步骤 5: 探测 bot 信息
    if callback:
        callback("probing", 0)
    
    bot_info = probe_bot(result["app_id"], result["app_secret"], result["domain"])
    if bot_info:
        result["bot_name"] = bot_info.get("bot_name")
        result["bot_open_id"] = bot_info.get("bot_open_id")
    else:
        result["bot_name"] = None
        result["bot_open_id"] = None

    if callback:
        callback("complete", result)
    
    return result


def print_setup_result(result: dict) -> None:
    """打印设置结果"""
    print()
    print("=" * 55)
    print("✅ 飞书机器人创建成功!")
    print("=" * 55)
    print(f"  App ID:     {result['app_id']}")
    print(f"  App Secret: {result['app_secret'][:8]}...")
    print(f"  Domain:     {result['domain']}")
    if result.get("bot_name"):
        print(f"  Bot 名称:   {result['bot_name']}")
    if result.get("open_id"):
        print(f"  Open ID:    {result['open_id']}")
    print("=" * 55)
    print()
    print("已自动保存配置，可以直接启动服务端。")
    print()


def get_qr_url(domain: str = "feishu") -> Optional[str]:
    """
    仅获取二维码 URL (不等待扫码)
    
    用于 TUI/GUI 显示二维码
    """
    try:
        _init_registration(domain)
        begin = _begin_registration(domain)
        return begin["qr_url"]
    except Exception as e:
        logger.error("[Feishu] 获取二维码失败: %s", e)
        return None
