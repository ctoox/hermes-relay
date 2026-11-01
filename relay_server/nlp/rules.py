"""
Hermes Relay - NLP 规则引擎
提供基于正则表达式的规则匹配
"""

from __future__ import annotations

import re
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class Rule:
    """NLP 规则"""
    patterns: List[str]                   # 匹配模式列表 (正则表达式)
    command: str                          # 生成的命令模板
    description: str = ""                 # 规则描述
    extract_args: bool = False            # 是否提取参数
    require_approval: bool = False        # 是否需要审批
    special_action: str = ""              # 特殊动作
    priority: int = 0                     # 优先级 (越高越先匹配)
    
    # 编译后的正则表达式
    _compiled_patterns: List[re.Pattern] = field(default_factory=list, init=False)
    
    def __post_init__(self):
        """编译正则表达式"""
        for pattern in self.patterns:
            try:
                self._compiled_patterns.append(
                    re.compile(pattern, re.IGNORECASE | re.UNICODE)
                )
            except re.error as e:
                logger.error("[Rule] Invalid pattern '%s': %s", pattern, e)
    
    def match(self, text: str) -> Optional[Tuple[str, Dict[str, any]]]:
        """
        尝试匹配文本
        
        Args:
            text: 输入文本
        
        Returns:
            匹配成功返回 (命令, 元数据)，否则返回 None
        """
        for pattern in self._compiled_patterns:
            match = pattern.search(text)
            if match:
                # 提取参数
                args = match.groups() if self.extract_args else ()
                
                # 生成命令
                try:
                    command = self.command.format(*args) if args else self.command
                except (IndexError, KeyError):
                    command = self.command
                
                # 构建元数据
                metadata = {
                    "description": self.description,
                    "require_approval": self.require_approval,
                    "special_action": self.special_action,
                    "matched_pattern": pattern.pattern,
                    "args": args,
                }
                
                return command, metadata
        
        return None


class RuleEngine:
    """
    规则引擎
    
    管理和执行一组规则，按优先级顺序匹配
    """
    
    def __init__(self):
        self._rules: List[Rule] = []
        self._sorted = False
    
    def add_rule(self, rule: Rule) -> None:
        """添加规则"""
        self._rules.append(rule)
        self._sorted = False
    
    def remove_rule(self, description: str) -> bool:
        """移除规则"""
        for i, rule in enumerate(self._rules):
            if rule.description == description:
                self._rules.pop(i)
                return True
        return False
    
    def _ensure_sorted(self) -> None:
        """确保规则按优先级排序"""
        if not self._sorted:
            self._rules.sort(key=lambda r: r.priority, reverse=True)
            self._sorted = True
    
    def match(self, text: str) -> Optional[Tuple[str, Dict[str, any]]]:
        """
        匹配文本
        
        Args:
            text: 输入文本
        
        Returns:
            匹配成功返回 (命令, 元数据)，否则返回 None
        """
        self._ensure_sorted()
        
        for rule in self._rules:
            result = rule.match(text)
            if result:
                return result
        
        return None
    
    def get_rules(self) -> List[Rule]:
        """获取所有规则"""
        self._ensure_sorted()
        return self._rules.copy()
    
    def clear_rules(self) -> None:
        """清除所有规则"""
        self._rules.clear()
        self._sorted = False
