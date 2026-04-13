"""文件工具"""

import os
import pickle
import json
from pathlib import Path
from typing import Any, Optional
import pandas as pd


class FileUtils:
    """文件工具类"""

    @staticmethod
    def ensure_dir(path: str) -> str:
        """确保目录存在"""
        Path(path).mkdir(parents=True, exist_ok=True)
        return path

    @staticmethod
    def save_pickle(obj: Any, filepath: str):
        """保存pickle文件"""
        FileUtils.ensure_dir(os.path.dirname(filepath))
        with open(filepath, "wb") as f:
            pickle.dump(obj, f)

    @staticmethod
    def load_pickle(filepath: str) -> Any:
        """加载pickle文件"""
        with open(filepath, "rb") as f:
            return pickle.load(f)

    @staticmethod
    def save_json(obj: Any, filepath: str, indent: int = 2):
        """保存JSON文件"""
        FileUtils.ensure_dir(os.path.dirname(filepath))
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(obj, f, indent=indent, ensure_ascii=False)

    @staticmethod
    def load_json(filepath: str) -> Any:
        """加载JSON文件"""
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)

    @staticmethod
    def file_exists(filepath: str) -> bool:
        """检查文件是否存在"""
        return os.path.exists(filepath)

    @staticmethod
    def get_file_size(filepath: str) -> int:
        """获取文件大小"""
        return os.path.getsize(filepath) if os.path.exists(filepath) else 0
