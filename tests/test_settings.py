"""
配置管理测试
"""
import pytest
from pathlib import Path

from src.config.settings import Settings


def test_settings_initialization():
    """测试配置初始化"""
    settings = Settings()

    # 测试基本配置
    assert settings.PROJECT_ROOT.exists()
    assert settings.INPUT_DIR.exists()
    assert settings.OUTPUT_DIR.exists()
    assert settings.CACHE_DIR.exists()


def test_comfyui_base_url():
    """测试ComfyUI URL生成"""
    settings = Settings()

    expected_url = f"{settings.COMFYUI_PROTOCOL}://{settings.COMFYUI_HOST}:{settings.COMFYUI_PORT}"
    assert settings.comfyui_base_url == expected_url


def test_workflow_paths():
    """测试workflow路径获取"""
    settings = Settings()

    # 测试三个workflow路径
    for workflow_type in ["image_edit", "voice_clone", "digital_human"]:
        path = settings.get_workflow_path(workflow_type)
        assert isinstance(path, Path)
        # 注意：不测试文件是否存在，因为测试环境可能没有这些文件

    # 测试无效的workflow类型
    with pytest.raises(ValueError):
        settings.get_workflow_path("invalid_type")


def test_video_duration_constraints():
    """测试视频时长约束"""
    settings = Settings()

    assert settings.MIN_VIDEO_DURATION > 0
    assert settings.MAX_VIDEO_DURATION > settings.MIN_VIDEO_DURATION
    assert settings.INSERTION_POINT_AVOID_START >= 0
    assert settings.INSERTION_POINT_AVOID_END >= 0


def test_ad_script_length():
    """测试广告词长度配置"""
    settings = Settings()

    assert settings.AD_SCRIPT_MIN_LENGTH > 0
    assert settings.AD_SCRIPT_MAX_LENGTH >= settings.AD_SCRIPT_MIN_LENGTH
