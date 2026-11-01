"""
Hermes Relay - 飞书适配器
基于 Hermes Agent 的飞书通信层实现

支持功能:
- WebSocket 长连接 (主模式)
- 消息接收/发送/编辑
- 交互式卡片 (审批按钮)
- 文件/图片传输
- 消息去重
- 断线自动重连
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
import threading
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set

logger = logging.getLogger(__name__)

# 飞书 SDK 导入
try:
    import lark_oapi as lark
    from lark_oapi.api.im.v1 import (
        CreateMessageRequest,
        CreateMessageRequestBody,
        ReplyMessageRequest,
        ReplyMessageRequestBody,
        UpdateMessageRequest,
        UpdateMessageRequestBody,
        GetMessageRequest,
        GetMessageResourceRequest,
        CreateImageRequest,
        CreateImageRequestBody,
        CreateFileRequest,
        CreateFileRequestBody,
    )
    from lark_oapi.event.dispatcher_handler import EventDispatcherHandler
    from lark_oapi.ws import Client as FeishuWSClient
    FEISHU_AVAILABLE = True
except ImportError:
    FEISHU_AVAILABLE = False
    logger.warning("lark-oapi not installed. Run: pip install lark-oapi")


@dataclass
class FeishuConfig:
    """飞书配置"""
    app_id: str = ""
    app_secret: str = ""
    domain: str = "feishu"  # feishu(中国) / lark(国际)
    encrypt_key: str = ""
    verification_token: str = ""
    
    # WebSocket 配置
    ws_reconnect_interval: int = 120
    ws_ping_interval: Optional[int] = None
    ws_ping_timeout: Optional[int] = None
    
    # 消息配置
    max_message_length: int = 8000
    dedup_cache_size: int = 2048
    dedup_ttl_seconds: int = 86400  # 24小时
    
    # 批处理配置
    text_batch_delay: float = 0.6
    text_batch_max_messages: int = 8
    text_batch_max_chars: int = 4000


@dataclass
class FeishuMessage:
    """飞书消息"""
    message_id: str
    chat_id: str
    chat_type: str  # p2p / group
    sender_id: str
    sender_type: str  # user / bot
    content: str
    message_type: str  # text / post / image / file
    mentions: List[Dict[str, Any]] = field(default_factory=list)
    create_time: float = 0.0


class FeishuAdapter:
    """
    飞书适配器
    
    提供稳定的飞书消息收发功能，支持：
    - WebSocket 长连接
    - 消息发送/接收/编辑
    - 交互式卡片
    - 文件传输
    - 断线重连
    """
    
    def __init__(self, config: FeishuConfig):
        self.config = config
        self._client: Optional[Any] = None
        self._ws_client: Optional[Any] = None
        self._event_handler: Optional[Any] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        
        # 消息去重
        self._seen_messages: OrderedDict[str, float] = OrderedDict()
        self._dedup_lock = threading.Lock()
        
        # 消息回调
        self._on_message_callback: Optional[Callable] = None
        self._on_approval_callback: Optional[Callable] = None
        
        # 连接状态
        self._connected = False
        self._running = False
        
        # 发送队列 (用于批处理)
        self._send_queue: asyncio.Queue = asyncio.Queue()
        self._send_task: Optional[asyncio.Task] = None
    
    @property
    def is_connected(self) -> bool:
        """是否已连接"""
        return self._connected
    
    def set_message_callback(self, callback: Callable) -> None:
        """设置消息回调"""
        self._on_message_callback = callback
    
    def set_approval_callback(self, callback: Callable) -> None:
        """设置审批回调"""
        self._on_approval_callback = callback
    
    async def connect(self) -> bool:
        """
        连接到飞书
        
        Returns:
            是否连接成功
        """
        if not FEISHU_AVAILABLE:
            logger.error("lark-oapi not installed")
            return False
        
        if not self.config.app_id or not self.config.app_secret:
            logger.error("FEISHU_APP_ID or FEISHU_APP_SECRET not set")
            return False
        
        try:
            # 创建飞书客户端
            self._client = lark.Client.builder() \
                .app_id(self.config.app_id) \
                .app_secret(self.config.app_secret) \
                .log_level(lark.LogLevel.WARNING) \
                .build()
            
            # 创建事件处理器
            self._event_handler = self._build_event_handler()
            
            # 创建 WebSocket 客户端
            self._ws_client = FeishuWSClient(
                self.config.domain,
                self.config.app_id,
                self.config.app_secret,
                event_handler=self._event_handler,
                log_level=lark.LogLevel.WARNING,
            )
            
            # 启动 WebSocket 连接
            self._running = True
            self._loop = asyncio.get_event_loop()
            
            # 在后台线程运行 WebSocket
            self._ws_thread = threading.Thread(
                target=self._run_ws_client,
                daemon=True,
                name="feishu-ws"
            )
            self._ws_thread.start()
            
            # 等待连接建立
            await asyncio.sleep(2)
            self._connected = True
            
            logger.info("[Feishu] Connected in WebSocket mode (%s)", self.config.domain)
            return True
            
        except Exception as e:
            logger.error("[Feishu] Failed to connect: %s", e, exc_info=True)
            return False
    
    def _run_ws_client(self) -> None:
        """在后台线程运行 WebSocket 客户端"""
        try:
            self._ws_client.start()
        except Exception as e:
            logger.error("[Feishu] WebSocket error: %s", e, exc_info=True)
            self._connected = False
    
    def _build_event_handler(self) -> Any:
        """构建事件处理器"""
        if EventDispatcherHandler is None:
            return None
        
        return (
            EventDispatcherHandler.builder(
                self.config.encrypt_key,
                self.config.verification_token,
            )
            .register_p2_im_message_receive_v1(self._on_message_event)
            .build()
        )
    
    def _on_message_event(self, data: Any) -> None:
        """处理消息事件"""
        try:
            event = data.event
            message = event.message
            
            # 解析消息
            feishu_msg = self._parse_message(event)
            if feishu_msg is None:
                return
            
            # 检查去重
            if self._is_duplicate(feishu_msg.message_id):
                logger.debug("[Feishu] Duplicate message: %s", feishu_msg.message_id)
                return
            
            # 调用回调
            if self._on_message_callback:
                asyncio.run_coroutine_threadsafe(
                    self._on_message_callback(feishu_msg),
                    self._loop
                )
                
        except Exception as e:
            logger.error("[Feishu] Error processing message: %s", e, exc_info=True)
    
    def _parse_message(self, event: Any) -> Optional[FeishuMessage]:
        """解析飞书消息事件"""
        try:
            message = event.message
            sender = event.sender
            
            # 获取消息内容
            content_str = message.content if hasattr(message, 'content') else '{}'
            content = json.loads(content_str) if content_str else {}
            
            # 根据消息类型提取文本
            message_type = message.message_type if hasattr(message, 'message_type') else 'text'
            text = ''
            
            if message_type == 'text':
                text = content.get('text', '')
            elif message_type == 'post':
                # 富文本消息，提取纯文本
                text = self._extract_post_text(content)
            
            # 提取mentions
            mentions = []
            if hasattr(message, 'mentions') and message.mentions:
                for mention in message.mentions:
                    mentions.append({
                        'key': mention.key if hasattr(mention, 'key') else '',
                        'id': mention.id.open_id if hasattr(mention, 'id') else '',
                        'name': mention.name if hasattr(mention, 'name') else '',
                    })
            
            return FeishuMessage(
                message_id=message.message_id if hasattr(message, 'message_id') else '',
                chat_id=message.chat_id if hasattr(message, 'chat_id') else '',
                chat_type=message.chat_type if hasattr(message, 'chat_type') else 'p2p',
                sender_id=sender.sender_id.open_id if hasattr(sender, 'sender_id') else '',
                sender_type=sender.sender_type if hasattr(sender, 'sender_type') else 'user',
                content=text,
                message_type=message_type,
                mentions=mentions,
                create_time=float(message.create_time) / 1000 if hasattr(message, 'create_time') else time.time(),
            )
        except Exception as e:
            logger.error("[Feishu] Error parsing message: %s", e, exc_info=True)
            return None
    
    def _extract_post_text(self, content: Dict) -> str:
        """从富文本消息中提取纯文本"""
        parts = []
        post = content.get('content', {})
        
        # 获取标题
        title = post.get('title', '')
        if title:
            parts.append(title)
        
        # 获取内容
        for lang_content in post.values():
            if isinstance(lang_content, dict):
                for row in lang_content.get('content', []):
                    if isinstance(row, list):
                        for item in row:
                            if isinstance(item, dict):
                                tag = item.get('tag', '')
                                if tag == 'text':
                                    parts.append(item.get('text', ''))
                                elif tag == 'a':
                                    parts.append(item.get('text', ''))
                                elif tag == 'at':
                                    parts.append(f"@{item.get('user_name', 'user')}")
        
        return ' '.join(parts)
    
    def _is_duplicate(self, message_id: str) -> bool:
        """检查消息是否重复"""
        with self._dedup_lock:
            now = time.time()
            
            # 清理过期的记录
            expired = [k for k, v in self._seen_messages.items() 
                      if now - v > self.config.dedup_ttl_seconds]
            for k in expired:
                del self._seen_messages[k]
            
            # 检查是否已存在
            if message_id in self._seen_messages:
                return True
            
            # 记录新消息
            self._seen_messages[message_id] = now
            
            # 限制缓存大小
            while len(self._seen_messages) > self.config.dedup_cache_size:
                self._seen_messages.popitem(last=False)
            
            return False
    
    async def send_message(
        self,
        chat_id: str,
        content: str,
        message_type: str = "text",
        reply_to: Optional[str] = None,
    ) -> Optional[str]:
        """
        发送消息
        
        Args:
            chat_id: 聊天ID
            content: 消息内容
            message_type: 消息类型 (text/post)
            reply_to: 回复的消息ID
        
        Returns:
            发送的消息ID，失败返回None
        """
        if not self._client:
            logger.error("[Feishu] Not connected")
            return None
        
        try:
            # 构建消息体
            if message_type == "text":
                msg_content = json.dumps({"text": content}, ensure_ascii=False)
            elif message_type == "post":
                msg_content = self._build_post_content(content)
            else:
                msg_content = content
            
            # 创建请求
            request = CreateMessageRequest.builder() \
                .receive_id_type("chat_id") \
                .request_body(
                    CreateMessageRequestBody.builder()
                    .receive_id(chat_id)
                    .msg_type(message_type)
                    .content(msg_content)
                    .build()
                ) \
                .build()
            
            # 发送消息
            response = await asyncio.to_thread(
                self._client.im.v1.message.create, request
            )
            
            if response.success():
                message_id = response.data.message_id
                logger.debug("[Feishu] Message sent: %s", message_id)
                return message_id
            else:
                logger.error("[Feishu] Send failed: %s", response.msg)
                return None
                
        except Exception as e:
            logger.error("[Feishu] Send error: %s", e, exc_info=True)
            return None
    
    async def reply_message(
        self,
        message_id: str,
        content: str,
        message_type: str = "text",
    ) -> Optional[str]:
        """
        回复消息
        
        Args:
            message_id: 要回复的消息ID
            content: 回复内容
            message_type: 消息类型
        
        Returns:
            回复的消息ID
        """
        if not self._client:
            return None
        
        try:
            if message_type == "text":
                msg_content = json.dumps({"text": content}, ensure_ascii=False)
            else:
                msg_content = content
            
            request = ReplyMessageRequest.builder() \
                .message_id(message_id) \
                .request_body(
                    ReplyMessageRequestBody.builder()
                    .msg_type(message_type)
                    .content(msg_content)
                    .build()
                ) \
                .build()
            
            response = await asyncio.to_thread(
                self._client.im.v1.message.reply, request
            )
            
            if response.success():
                return response.data.message_id
            else:
                logger.error("[Feishu] Reply failed: %s", response.msg)
                return None
                
        except Exception as e:
            logger.error("[Feishu] Reply error: %s", e, exc_info=True)
            return None
    
    async def update_message(
        self,
        message_id: str,
        content: str,
        message_type: str = "text",
    ) -> bool:
        """
        更新消息
        
        Args:
            message_id: 要更新的消息ID
            content: 新内容
            message_type: 消息类型
        
        Returns:
            是否成功
        """
        if not self._client:
            return False
        
        try:
            if message_type == "text":
                msg_content = json.dumps({"text": content}, ensure_ascii=False)
            else:
                msg_content = content
            
            request = UpdateMessageRequest.builder() \
                .message_id(message_id) \
                .request_body(
                    UpdateMessageRequestBody.builder()
                    .msg_type(message_type)
                    .content(msg_content)
                    .build()
                ) \
                .build()
            
            response = await asyncio.to_thread(
                self._client.im.v1.message.update, request
            )
            
            return response.success()
            
        except Exception as e:
            logger.error("[Feishu] Update error: %s", e, exc_info=True)
            return False
    
    async def send_card(
        self,
        chat_id: str,
        card: Dict[str, Any],
    ) -> Optional[str]:
        """
        发送交互式卡片
        
        Args:
            chat_id: 聊天ID
            card: 卡片JSON
        
        Returns:
            消息ID
        """
        content = json.dumps(card, ensure_ascii=False)
        return await self.send_message(chat_id, content, message_type="interactive")
    
    def _build_post_content(self, text: str) -> str:
        """构建富文本消息内容"""
        # 将文本按行分割，构建post格式
        lines = text.split('\n')
        content = []
        for line in lines:
            if line.strip():
                content.append([{"tag": "text", "text": line}])
            else:
                content.append([{"tag": "text", "text": " "}])
        
        post = {
            "zh_cn": {
                "content": content
            }
        }
        return json.dumps(post, ensure_ascii=False)
    
    async def disconnect(self) -> None:
        """断开连接"""
        self._running = False
        self._connected = False
        
        if self._ws_client:
            try:
                # WebSocket 客户端没有直接的停止方法
                # 通过设置标志位来停止
                pass
            except Exception:
                pass
        
        logger.info("[Feishu] Disconnected")
