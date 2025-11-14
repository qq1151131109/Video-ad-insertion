"""
广告配置管理测试
"""
import pytest
import json
from pathlib import Path
import tempfile

from src.config.ads import AdsManager, AdConfig


def test_ad_config_creation():
    """测试广告配置创建"""
    ad = AdConfig(
        id="test_ad",
        name="测试广告",
        product="测试产品",
        category="测试类别",
        enabled=True,
        priority=1,
        selling_points=["卖点1", "卖点2"],
        target_scenarios=["场景1"],
        templates={"通用": ["模板1"]}
    )

    assert ad.id == "test_ad"
    assert ad.name == "测试广告"
    assert ad.enabled is True
    assert len(ad.selling_points) == 2


def test_ad_get_selling_points_text():
    """测试卖点文本生成"""
    ad = AdConfig(
        id="test",
        name="测试",
        product="产品",
        category="类别",
        selling_points=["卖点A", "卖点B", "卖点C"]
    )

    text = ad.get_selling_points_text()
    assert text == "卖点A、卖点B、卖点C"


def test_ad_get_template():
    """测试模板获取"""
    ad = AdConfig(
        id="test",
        name="测试",
        product="产品",
        category="类别",
        templates={
            "科技类": ["科技模板"],
            "通用": ["通用模板"]
        }
    )

    # 获取存在的模板
    assert ad.get_template("科技类") == "科技模板"

    # 获取不存在的模板，应该fallback到通用
    assert ad.get_template("教育类") == "通用模板"


def test_ads_manager_initialization():
    """测试广告管理器初始化"""
    # 创建临时配置文件
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        config = {
            "ads": [
                {
                    "id": "ad1",
                    "name": "广告1",
                    "product": "产品1",
                    "category": "类别1",
                    "enabled": True,
                    "priority": 1,
                    "selling_points": ["卖点"],
                    "target_scenarios": ["场景"],
                    "templates": {"通用": ["模板"]}
                },
                {
                    "id": "ad2",
                    "name": "广告2",
                    "product": "产品2",
                    "category": "类别2",
                    "enabled": False,  # 禁用
                    "priority": 2,
                    "selling_points": [],
                    "target_scenarios": [],
                    "templates": {}
                }
            ],
            "settings": {
                "ad_script_style": "自然",
                "context_awareness": True
            }
        }
        json.dump(config, f)
        temp_path = f.name

    try:
        # 加载配置
        manager = AdsManager(config_path=temp_path)

        # 测试广告加载
        assert len(manager.ads) == 2
        assert manager.ads[0].id == "ad1"
        assert manager.ads[1].id == "ad2"

        # 测试设置加载
        assert manager.settings.ad_script_style == "自然"
        assert manager.settings.context_awareness is True

    finally:
        # 清理临时文件
        Path(temp_path).unlink()


def test_get_enabled_ads():
    """测试获取启用的广告"""
    manager = AdsManager()  # 使用默认配置

    enabled_ads = manager.get_enabled_ads()
    assert isinstance(enabled_ads, list)
    assert all(ad.enabled for ad in enabled_ads)


def test_get_primary_ad():
    """测试获取主要广告"""
    manager = AdsManager()

    primary = manager.get_primary_ad()
    if primary:
        assert primary.enabled is True
        # 主要广告应该是优先级最高的（数字最小）
        enabled = manager.get_enabled_ads()
        if enabled:
            assert primary.priority == min(ad.priority for ad in enabled)


def test_select_ad_for_video():
    """测试根据视频主题选择广告"""
    # 创建测试配置
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        config = {
            "ads": [
                {
                    "id": "tech_ad",
                    "name": "科技广告",
                    "product": "科技产品",
                    "category": "科技",
                    "enabled": True,
                    "priority": 1,
                    "selling_points": [],
                    "target_scenarios": ["AI开发", "编程"],
                    "templates": {}
                },
                {
                    "id": "general_ad",
                    "name": "通用广告",
                    "product": "通用产品",
                    "category": "通用",
                    "enabled": True,
                    "priority": 2,
                    "selling_points": [],
                    "target_scenarios": [],
                    "templates": {}
                }
            ]
        }
        json.dump(config, f)
        temp_path = f.name

    try:
        manager = AdsManager(config_path=temp_path)

        # 匹配场景
        ad = manager.select_ad_for_video("AI开发教程")
        assert ad.id == "tech_ad"

        # 不匹配场景，应该返回主要广告
        ad = manager.select_ad_for_video("美食视频")
        assert ad.id == "tech_ad"  # 因为priority=1

    finally:
        Path(temp_path).unlink()
