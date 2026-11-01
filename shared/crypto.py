"""
Hermes Relay - 加密工具
提供消息加密、签名和验证功能
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import base64
from typing import Any, Dict, Optional, Tuple

try:
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    from cryptography.hazmat.primitives import padding
    from cryptography.hazmat.backends import default_backend
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False


def generate_key() -> bytes:
    """生成随机加密密钥 (32字节 = 256位)"""
    return os.urandom(32)


def generate_hmac_key() -> bytes:
    """生成HMAC签名密钥"""
    return os.urandom(32)


def encrypt_message(message: Dict[str, Any], key: bytes) -> str:
    """
    加密消息
    
    Args:
        message: 要加密的消息字典
        key: 32字节加密密钥
    
    Returns:
        Base64编码的加密消息
    """
    if not CRYPTO_AVAILABLE:
        # 如果没有cryptography库，使用简单的base64编码
        return base64.b64encode(json.dumps(message).encode()).decode()
    
    # 将消息转换为JSON
    plaintext = json.dumps(message, ensure_ascii=False).encode('utf-8')
    
    # 添加PKCS7填充
    padder = padding.PKCS7(128).padder()
    padded_data = padder.update(plaintext) + padder.finalize()
    
    # 生成随机IV
    iv = os.urandom(16)
    
    # 使用AES-256-CBC加密
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
    encryptor = cipher.encryptor()
    ciphertext = encryptor.update(padded_data) + encryptor.finalize()
    
    # 组合IV和密文，然后Base64编码
    encrypted = iv + ciphertext
    return base64.b64encode(encrypted).decode('utf-8')


def decrypt_message(encrypted: str, key: bytes) -> Dict[str, Any]:
    """
    解密消息
    
    Args:
        encrypted: Base64编码的加密消息
        key: 32字节加密密钥
    
    Returns:
        解密后的消息字典
    """
    if not CRYPTO_AVAILABLE:
        # 如果没有cryptography库，解码base64
        return json.loads(base64.b64decode(encrypted).decode())
    
    # Base64解码
    encrypted_bytes = base64.b64decode(encrypted)
    
    # 提取IV和密文
    iv = encrypted_bytes[:16]
    ciphertext = encrypted_bytes[16:]
    
    # 使用AES-256-CBC解密
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
    decryptor = cipher.decryptor()
    padded_data = decryptor.update(ciphertext) + decryptor.finalize()
    
    # 移除PKCS7填充
    unpadder = padding.PKCS7(128).unpadder()
    plaintext = unpadder.update(padded_data) + unpadder.finalize()
    
    return json.loads(plaintext.decode('utf-8'))


def sign_message(message: Dict[str, Any], hmac_key: bytes) -> str:
    """
    对消息进行HMAC签名
    
    Args:
        message: 要签名的消息字典
        hmac_key: HMAC密钥
    
    Returns:
        Hex编码的签名
    """
    # 将消息转换为规范化的JSON字符串
    content = json.dumps(message, sort_keys=True, ensure_ascii=False).encode('utf-8')
    
    # 计算HMAC-SHA256签名
    signature = hmac.new(hmac_key, content, hashlib.sha256).hexdigest()
    
    return signature


def verify_signature(message: Dict[str, Any], signature: str, hmac_key: bytes) -> bool:
    """
    验证消息签名
    
    Args:
        message: 消息字典
        signature: 要验证的签名
        hmac_key: HMAC密钥
    
    Returns:
        签名是否有效
    """
    expected = sign_message(message, hmac_key)
    return hmac.compare_digest(expected, signature)


def hash_password(password: str, salt: Optional[bytes] = None) -> Tuple[str, str]:
    """
    哈希密码 (用于设备认证)
    
    Args:
        password: 明文密码
        salt: 盐值 (可选)
    
    Returns:
        (哈希值, 盐值) 的元组
    """
    if salt is None:
        salt = os.urandom(32)
    
    # 使用PBKDF2进行密码哈希
    key = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt,
        iterations=100000,
        dklen=32
    )
    
    return base64.b64encode(key).decode('utf-8'), base64.b64encode(salt).decode('utf-8')


def verify_password(password: str, hash_value: str, salt: str) -> bool:
    """
    验证密码
    
    Args:
        password: 明文密码
        hash_value: 存储的哈希值
        salt: 存储的盐值
    
    Returns:
        密码是否匹配
    """
    salt_bytes = base64.b64decode(salt)
    computed_hash, _ = hash_password(password, salt_bytes)
    return hmac.compare_digest(computed_hash, hash_value)


def generate_device_token() -> str:
    """生成设备认证令牌"""
    return base64.b64encode(os.urandom(48)).decode('utf-8')


def generate_session_id() -> str:
    """生成会话ID"""
    return base64.urlsafe_b64encode(os.urandom(24)).decode('utf-8')
