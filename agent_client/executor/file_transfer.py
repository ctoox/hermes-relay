"""
Hermes Relay - 文件传输模块
提供文件上传、下载、管理功能
"""

from __future__ import annotations

import base64
import hashlib
import logging
import os
import shutil
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class FileTransfer:
    """
    文件传输管理器
    
    提供功能:
    - 文件上传/下载
    - 文件分片传输
    - 文件管理 (列表、删除、移动)
    - 文件哈希校验
    """
    
    def __init__(self, base_dir: str = "file_storage"):
        self._base_dir = Path(base_dir)
        self._base_dir.mkdir(parents=True, exist_ok=True)
        
        # 上传目录
        self._upload_dir = self._base_dir / "uploads"
        self._upload_dir.mkdir(parents=True, exist_ok=True)
        
        # 下载目录
        self._download_dir = self._base_dir / "downloads"
        self._download_dir.mkdir(parents=True, exist_ok=True)
    
    # =========================================================================
    # 文件传输
    # =========================================================================
    
    def prepare_upload(self, file_path: str) -> Dict[str, Any]:
        """
        准备上传文件
        
        Args:
            file_path: 文件路径
        
        Returns:
            文件信息 (包含分片信息)
        """
        path = Path(file_path)
        if not path.exists():
            return {"error": "File not found"}
        
        stat = path.stat()
        file_hash = self._calculate_hash(file_path)
        
        # 计算分片 (每片 1MB)
        chunk_size = 1024 * 1024
        total_chunks = max(1, (stat.st_size + chunk_size - 1) // chunk_size)
        
        return {
            "file_name": path.name,
            "file_path": str(path.absolute()),
            "file_size": stat.st_size,
            "file_hash": file_hash,
            "chunk_size": chunk_size,
            "total_chunks": total_chunks,
            "mime_type": self._get_mime_type(path.suffix),
        }
    
    def read_chunk(self, file_path: str, chunk_index: int, chunk_size: int = 1024 * 1024) -> Dict[str, Any]:
        """
        读取文件分片
        
        Args:
            file_path: 文件路径
            chunk_index: 分片索引
            chunk_size: 分片大小
        
        Returns:
            分片数据 (base64 编码)
        """
        path = Path(file_path)
        if not path.exists():
            return {"error": "File not found"}
        
        file_size = path.stat().st_size
        offset = chunk_index * chunk_size
        length = min(chunk_size, file_size - offset)
        
        if offset >= file_size:
            return {"error": "Chunk index out of range"}
        
        with open(file_path, "rb") as f:
            f.seek(offset)
            data = f.read(length)
        
        return {
            "chunk_index": chunk_index,
            "data": base64.b64encode(data).decode("utf-8"),
            "size": len(data),
            "is_last": (offset + length) >= file_size,
        }
    
    def write_chunk(
        self,
        file_name: str,
        chunk_index: int,
        data_b64: str,
        total_chunks: int,
    ) -> Dict[str, Any]:
        """
        写入文件分片
        
        Args:
            file_name: 文件名
            chunk_index: 分片索引
            data_b64: 分片数据 (base64)
            total_chunks: 总分片数
        
        Returns:
            写入结果
        """
        # 临时文件路径
        temp_dir = self._upload_dir / "temp" / file_name
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        chunk_path = temp_dir / f"chunk_{chunk_index:04d}"
        
        # 写入分片
        data = base64.b64decode(data_b64)
        with open(chunk_path, "wb") as f:
            f.write(data)
        
        # 检查是否所有分片都已写入
        existing_chunks = len(list(temp_dir.glob("chunk_*")))
        is_complete = existing_chunks >= total_chunks
        
        if is_complete:
            # 合并分片
            output_path = self._upload_dir / file_name
            self._merge_chunks(temp_dir, output_path, total_chunks)
            
            # 清理临时文件
            shutil.rmtree(temp_dir)
            
            return {
                "status": "complete",
                "file_path": str(output_path),
                "file_size": output_path.stat().st_size,
            }
        
        return {
            "status": "partial",
            "chunks_received": existing_chunks,
            "total_chunks": total_chunks,
        }
    
    def _merge_chunks(self, chunk_dir: Path, output_path: Path, total_chunks: int) -> None:
        """合并文件分片"""
        with open(output_path, "wb") as out_f:
            for i in range(total_chunks):
                chunk_path = chunk_dir / f"chunk_{i:04d}"
                if chunk_path.exists():
                    with open(chunk_path, "rb") as in_f:
                        out_f.write(in_f.read())
    
    # =========================================================================
    # 文件管理
    # =========================================================================
    
    def list_files(self, directory: str = "") -> List[Dict[str, Any]]:
        """
        列出目录下的文件
        
        Args:
            directory: 目录路径 (相对于 base_dir)
        
        Returns:
            文件列表
        """
        target_dir = self._base_dir / directory if directory else self._base_dir
        
        if not target_dir.exists():
            return []
        
        files = []
        for item in target_dir.iterdir():
            stat = item.stat()
            files.append({
                "name": item.name,
                "path": str(item.relative_to(self._base_dir)),
                "size": stat.st_size,
                "modified": stat.st_mtime,
                "is_file": item.is_file(),
                "is_dir": item.is_dir(),
            })
        
        # 按修改时间排序
        files.sort(key=lambda x: x["modified"], reverse=True)
        return files
    
    def delete_file(self, file_path: str) -> bool:
        """
        删除文件
        
        Args:
            file_path: 文件路径 (相对于 base_dir)
        
        Returns:
            是否成功
        """
        path = self._base_dir / file_path
        
        if not path.exists():
            return False
        
        try:
            if path.is_file():
                path.unlink()
            elif path.is_dir():
                shutil.rmtree(path)
            return True
        except Exception as e:
            logger.error("[File] Delete failed: %s", e)
            return False
    
    def move_file(self, src: str, dst: str) -> bool:
        """
        移动/重命名文件
        
        Args:
            src: 源路径
            dst: 目标路径
        
        Returns:
            是否成功
        """
        src_path = self._base_dir / src
        dst_path = self._base_dir / dst
        
        if not src_path.exists():
            return False
        
        try:
            dst_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src_path), str(dst_path))
            return True
        except Exception as e:
            logger.error("[File] Move failed: %s", e)
            return False
    
    def copy_file(self, src: str, dst: str) -> bool:
        """
        复制文件
        
        Args:
            src: 源路径
            dst: 目标路径
        
        Returns:
            是否成功
        """
        src_path = self._base_dir / src
        dst_path = self._base_dir / dst
        
        if not src_path.exists():
            return False
        
        try:
            dst_path.parent.mkdir(parents=True, exist_ok=True)
            if src_path.is_file():
                shutil.copy2(str(src_path), str(dst_path))
            elif src_path.is_dir():
                shutil.copytree(str(src_path), str(dst_path))
            return True
        except Exception as e:
            logger.error("[File] Copy failed: %s", e)
            return False
    
    # =========================================================================
    # 工具函数
    # =========================================================================
    
    def _calculate_hash(self, file_path: str) -> str:
        """计算文件 SHA256 哈希"""
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)
        return sha256.hexdigest()
    
    def _get_mime_type(self, suffix: str) -> str:
        """获取文件 MIME 类型"""
        mime_map = {
            ".txt": "text/plain",
            ".pdf": "application/pdf",
            ".doc": "application/msword",
            ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ".xls": "application/vnd.ms-excel",
            ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".gif": "image/gif",
            ".mp4": "video/mp4",
            ".mp3": "audio/mpeg",
            ".zip": "application/zip",
            ".rar": "application/x-rar-compressed",
            ".7z": "application/x-7z-compressed",
        }
        return mime_map.get(suffix.lower(), "application/octet-stream")
    
    def get_storage_info(self) -> Dict[str, Any]:
        """获取存储信息"""
        total_size = 0
        file_count = 0
        
        for item in self._base_dir.rglob("*"):
            if item.is_file():
                total_size += item.stat().st_size
                file_count += 1
        
        return {
            "base_dir": str(self._base_dir),
            "file_count": file_count,
            "total_size": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
        }


# 全局实例
_transfer: Optional[FileTransfer] = None


def get_transfer() -> FileTransfer:
    """获取全局文件传输实例"""
    global _transfer
    if _transfer is None:
        _transfer = FileTransfer()
    return _transfer
