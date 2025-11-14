"""
配置管理模块

从.env文件加载配置，并提供全局配置对象
"""
import os
from pathlib import Path
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """全局配置类"""

    # ==============================================================================
    # 项目路径
    # ==============================================================================
    PROJECT_ROOT: Path = Field(default_factory=lambda: Path(__file__).parent.parent.parent)
    INPUT_DIR: Path = Field(default_factory=lambda: Path(__file__).parent.parent.parent / "input")
    OUTPUT_DIR: Path = Field(default_factory=lambda: Path(__file__).parent.parent.parent / "output")
    CACHE_DIR: Path = Field(default_factory=lambda: Path(__file__).parent.parent.parent / "cache")
    DOCS_DIR: Path = Field(default_factory=lambda: Path(__file__).parent.parent.parent / "docs")

    # ==============================================================================
    # LLM API配置
    # ==============================================================================
    OPENAI_API_KEY: str
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    OPENAI_MODEL: str = "gpt-4o-mini"

    # ==============================================================================
    # ComfyUI API配置
    # ==============================================================================
    COMFYUI_HOST: str = "103.231.86.148"
    COMFYUI_PORT: int = 9000
    COMFYUI_PROTOCOL: str = "http"

    # Workflow配置文件路径
    WORKFLOW_IMAGE_EDIT: str = "docs/workflow/qwen_image_edit-api-1114.json"
    WORKFLOW_VOICE_CLONE: str = "docs/workflow/index TTS2-1114-API.json"
    WORKFLOW_DIGITAL_HUMAN: str = "docs/workflow/InfiniteTalk数字人-图生视频-API-1114.json"

    # ==============================================================================
    # 日志配置
    # ==============================================================================
    LOG_LEVEL: str = "INFO"
    LOG_FILE: Optional[str] = None  # 如果设置，日志会输出到文件

    # ==============================================================================
    # 性能配置
    # ==============================================================================
    MAX_CONCURRENT_DOWNLOADS: int = 50
    MAX_CONCURRENT_TTS: int = 5
    MAX_CONCURRENT_COMFYUI: int = 2

    # ==============================================================================
    # Whisper配置
    # ==============================================================================
    WHISPER_MODEL: str = "large-v3"  # tiny, base, small, medium, large-v3
    WHISPER_DEVICE: str = "cuda"  # cuda, cpu
    WHISPER_LANGUAGE: str = "zh"  # 中文

    # ==============================================================================
    # 视频处理配置
    # ==============================================================================
    MIN_VIDEO_DURATION: float = 15.0  # 最小视频时长（秒）
    MAX_VIDEO_DURATION: float = 300.0  # 最大视频时长（秒）
    INSERTION_POINT_AVOID_START: float = 3.0  # 避免在开头N秒插入
    INSERTION_POINT_AVOID_END: float = 5.0  # 避免在结尾N秒插入

    # ==============================================================================
    # 广告配置
    # ==============================================================================
    AD_PRODUCT: str = "NVIDIA算力"
    AD_SCRIPT_MIN_LENGTH: int = 15  # 广告词最小字数
    AD_SCRIPT_MAX_LENGTH: int = 20  # 广告词最大字数
    AD_VIDEO_MIN_DURATION: float = 3.0  # 广告视频最小时长（秒）
    AD_VIDEO_MAX_DURATION: float = 5.0  # 广告视频最大时长（秒）

    # ==============================================================================
    # 文件清理配置
    # ==============================================================================
    KEEP_TEMP_FILES_ON_ERROR: bool = True  # 错误时保留临时文件用于调试
    TEMP_FILES_TTL: int = 86400  # 临时文件过期时间（秒），默认24小时

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "ignore"  # 忽略.env中未定义的字段

    @property
    def comfyui_base_url(self) -> str:
        """ComfyUI完整URL"""
        return f"{self.COMFYUI_PROTOCOL}://{self.COMFYUI_HOST}:{self.COMFYUI_PORT}"

    def get_workflow_path(self, workflow_type: str) -> Path:
        """
        获取workflow配置文件的完整路径

        Args:
            workflow_type: "image_edit" | "voice_clone" | "digital_human"

        Returns:
            Path: workflow文件的完整路径
        """
        workflow_map = {
            "image_edit": self.WORKFLOW_IMAGE_EDIT,
            "voice_clone": self.WORKFLOW_VOICE_CLONE,
            "digital_human": self.WORKFLOW_DIGITAL_HUMAN,
        }

        if workflow_type not in workflow_map:
            raise ValueError(f"Unknown workflow type: {workflow_type}")

        relative_path = workflow_map[workflow_type]
        return self.PROJECT_ROOT / relative_path

    def ensure_directories(self):
        """确保所有必要的目录存在"""
        directories = [
            self.INPUT_DIR,
            self.OUTPUT_DIR / "processed",
            self.OUTPUT_DIR / "debug",
            self.OUTPUT_DIR / "logs",
            self.CACHE_DIR / "audio",
            self.CACHE_DIR / "keyframes",
            self.CACHE_DIR / "transcriptions",
            self.CACHE_DIR / "ad_materials",
        ]

        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)


# 全局配置对象
settings = Settings()

# 确保目录存在
settings.ensure_directories()
