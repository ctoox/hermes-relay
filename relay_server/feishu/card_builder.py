"""
Hermes Relay - 飞书卡片构建器
构建交互式卡片用于审批、设备列表展示等
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional


class CardBuilder:
    """
    飞书交互式卡片构建器
    
    用于构建各种类型的卡片：
    - 审批卡片
    - 设备列表卡片
    - 命令结果卡片
    - 错误提示卡片
    """
    
    @staticmethod
    def build_approval_card(
        approval_id: str,
        command: str,
        device_name: str,
        risk_level: str = "medium",
        reason: str = "",
        timeout: int = 300,
    ) -> Dict[str, Any]:
        """
        构建审批卡片
        
        Args:
            approval_id: 审批ID
            command: 待审批的命令
            device_name: 设备名称
            risk_level: 风险等级 (low/medium/high/critical)
            reason: 审批原因
            timeout: 审批超时时间
        
        Returns:
            卡片JSON
        """
        # 风险等级颜色映射
        risk_colors = {
            "low": "green",
            "medium": "orange",
            "high": "red",
            "critical": "red",
        }
        
        # 风险等级图标
        risk_icons = {
            "low": "ℹ️",
            "medium": "⚠️",
            "high": "🔴",
            "critical": "🚨",
        }
        
        color = risk_colors.get(risk_level, "orange")
        icon = risk_icons.get(risk_level, "⚠️")
        
        # 截断命令显示
        cmd_display = command[:500] + "..." if len(command) > 500 else command
        
        card = {
            "config": {"wide_screen_mode": True},
            "header": {
                "title": {
                    "content": f"{icon} 命令审批请求",
                    "tag": "plain_text"
                },
                "template": color
            },
            "elements": [
                {
                    "tag": "div",
                    "fields": [
                        {
                            "is_short": True,
                            "text": {
                                "tag": "lark_md",
                                "content": f"**设备:** {device_name}"
                            }
                        },
                        {
                            "is_short": True,
                            "text": {
                                "tag": "lark_md",
                                "content": f"**风险等级:** {risk_level.upper()}"
                            }
                        }
                    ]
                },
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": f"**命令:**\n```\n{cmd_display}\n```"
                    }
                },
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": f"**原因:** {reason or '用户执行的命令需要审批'}"
                    }
                },
                {
                    "tag": "note",
                    "elements": [
                        {
                            "tag": "plain_text",
                            "content": f"审批将在 {timeout} 秒后自动超时"
                        }
                    ]
                },
                {
                    "tag": "hr"
                },
                {
                    "tag": "action",
                    "actions": [
                        {
                            "tag": "button",
                            "text": {
                                "tag": "plain_text",
                                "content": "✅ 允许一次"
                            },
                            "type": "primary",
                            "value": {
                                "action": "allow_once",
                                "approval_id": approval_id
                            }
                        },
                        {
                            "tag": "button",
                            "text": {
                                "tag": "plain_text",
                                "content": "✅ 本次会话"
                            },
                            "type": "default",
                            "value": {
                                "action": "allow_session",
                                "approval_id": approval_id
                            }
                        },
                        {
                            "tag": "button",
                            "text": {
                                "tag": "plain_text",
                                "content": "✅ 永久允许"
                            },
                            "type": "default",
                            "value": {
                                "action": "allow_always",
                                "approval_id": approval_id
                            }
                        },
                        {
                            "tag": "button",
                            "text": {
                                "tag": "plain_text",
                                "content": "❌ 拒绝"
                            },
                            "type": "danger",
                            "value": {
                                "action": "deny",
                                "approval_id": approval_id
                            }
                        }
                    ]
                }
            ]
        }
        
        return card
    
    @staticmethod
    def build_device_list_card(
        devices: List[Dict[str, Any]],
        group_name: str = "",
    ) -> Dict[str, Any]:
        """
        构建设备列表卡片
        
        Args:
            devices: 设备列表
            group_name: 设备组名称
        
        Returns:
            卡片JSON
        """
        if not devices:
            return CardBuilder.build_info_card(
                "设备列表",
                "暂无在线设备"
            )
        
        # 构建设备列表
        device_lines = []
        for i, device in enumerate(devices, 1):
            status_icon = "🟢" if device.get('status') == 'online' else "🔴"
            name = device.get('name', 'Unknown')
            group = device.get('group', 'default')
            ip = device.get('ip', 'N/A')
            cpu = device.get('cpu_usage', 0)
            mem = device.get('memory_usage', 0)
            
            device_lines.append(
                f"{status_icon} **{name}** ({group})\n"
                f"   IP: {ip} | CPU: {cpu:.1f}% | 内存: {mem:.1f}%"
            )
        
        title = f"设备列表 - {group_name}" if group_name else "设备列表"
        content = "\n\n".join(device_lines)
        
        return CardBuilder.build_info_card(title, content)
    
    @staticmethod
    def build_command_result_card(
        command: str,
        device_name: str,
        status: str,
        output: str,
        execution_time: float = 0.0,
    ) -> Dict[str, Any]:
        """
        构建命令结果卡片
        
        Args:
            command: 执行的命令
            device_name: 设备名称
            status: 执行状态
            output: 命令输出
            execution_time: 执行时间
        
        Returns:
            卡片JSON
        """
        status_icon = "✅" if status == "success" else "❌"
        status_text = "成功" if status == "success" else "失败"
        
        # 截断输出
        output_display = output[:2000] + "..." if len(output) > 2000 else output
        
        card = {
            "config": {"wide_screen_mode": True},
            "header": {
                "title": {
                    "content": f"{status_icon} 命令执行{status_text}",
                    "tag": "plain_text"
                },
                "template": "green" if status == "success" else "red"
            },
            "elements": [
                {
                    "tag": "div",
                    "fields": [
                        {
                            "is_short": True,
                            "text": {
                                "tag": "lark_md",
                                "content": f"**设备:** {device_name}"
                            }
                        },
                        {
                            "is_short": True,
                            "text": {
                                "tag": "lark_md",
                                "content": f"**耗时:** {execution_time:.2f}s"
                            }
                        }
                    ]
                },
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": f"**命令:**\n```\n{command}\n```"
                    }
                },
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": f"**输出:**\n```\n{output_display}\n```"
                    }
                }
            ]
        }
        
        return card
    
    @staticmethod
    def build_info_card(
        title: str,
        content: str,
        color: str = "blue",
    ) -> Dict[str, Any]:
        """
        构建信息卡片
        
        Args:
            title: 标题
            content: 内容
            color: 颜色 (blue/green/orange/red)
        
        Returns:
            卡片JSON
        """
        return {
            "config": {"wide_screen_mode": True},
            "header": {
                "title": {
                    "content": title,
                    "tag": "plain_text"
                },
                "template": color
            },
            "elements": [
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": content
                    }
                }
            ]
        }
    
    @staticmethod
    def build_error_card(
        title: str,
        error_message: str,
        details: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        构建错误卡片
        
        Args:
            title: 标题
            error_message: 错误信息
            details: 错误详情
        
        Returns:
            卡片JSON
        """
        elements = [
            {
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": f"❌ {error_message}"
                }
            }
        ]
        
        if details:
            elements.append({
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": f"**详情:**\n```\n{details}\n```"
                }
            })
        
        return {
            "config": {"wide_screen_mode": True},
            "header": {
                "title": {
                    "content": f"❌ {title}",
                    "tag": "plain_text"
                },
                "template": "red"
            },
            "elements": elements
        }
    
    @staticmethod
    def build_help_card() -> Dict[str, Any]:
        """
        构建帮助卡片
        
        Returns:
            卡片JSON
        """
        help_text = """
**可用命令:**

🔹 **设备管理**
• `设备列表` / `devices` - 查看所有设备
• `设备状态 <名称>` - 查看设备详情
• `设备分组` - 查看设备分组

🔹 **命令执行**
• `<命令>` - 直接执行命令
• `在 <设备> 上执行 <命令>` - 指定设备执行
• `群控 <命令>` - 所有设备执行

🔹 **自然语言**
• `打开记事本` → start notepad
• `查看IP` → ipconfig
• `查看进程` → tasklist
• `截图` → 截取屏幕

🔹 **系统**
• `帮助` / `help` - 显示此帮助
• `状态` / `status` - 查看系统状态
"""
        
        return CardBuilder.build_info_card("帮助", help_text, "blue")
