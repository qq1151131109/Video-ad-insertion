"""
广告配置管理模块

从config/ads.json加载广告配置，支持多个广告产品
"""
import json
from pathlib import Path
from typing import List, Optional, Dict, Any

from pydantic import BaseModel, Field

from src.utils.logger import logger


class AdTemplate(BaseModel):
    """广告模板"""
    科技类: List[str] = Field(default_factory=list)
    教育类: List[str] = Field(default_factory=list)
    创作类: List[str] = Field(default_factory=list)
    通用: List[str] = Field(default_factory=list)


class AdConfig(BaseModel):
    """单个广告配置"""
    id: str
    name: str
    product: str
    category: str
    enabled: bool = True
    priority: int = 1
    description: str = ""
    selling_points: List[str] = Field(default_factory=list)
    target_scenarios: List[str] = Field(default_factory=list)
    templates: Dict[str, List[str]] = Field(default_factory=dict)

    def get_selling_points_text(self) -> str:
        """获取卖点文本（用于LLM Prompt）"""
        return "、".join(self.selling_points)

    def get_template(self, category: str = "通用") -> Optional[str]:
        """
        获取模板文案

        Args:
            category: 类别（科技类、教育类、创作类、通用）

        Returns:
            模板文案，如果没有则返回None
        """
        templates = self.templates.get(category, [])
        if templates:
            return templates[0]  # 返回第一个模板

        # 尝试通用模板
        if category != "通用":
            return self.get_template("通用")

        return None


class AdsSettings(BaseModel):
    """广告系统设置"""
    ad_script_style: str = "自然"
    ad_script_tone: str = "专业"
    context_awareness: bool = True
    auto_select_template: bool = True
    fallback_to_llm: bool = True


class AdsManager:
    """广告管理器"""

    def __init__(self, config_path: Optional[str] = None):
        """
        初始化广告管理器

        Args:
            config_path: 配置文件路径（可选，默认使用config/ads.json）
        """
        if config_path is None:
            # 默认配置文件路径
            project_root = Path(__file__).parent.parent.parent
            config_path = project_root / "config" / "ads.json"

        self.config_path = Path(config_path)
        self.ads: List[AdConfig] = []
        self.settings: AdsSettings = AdsSettings()

        self._load_config()

    def _load_config(self):
        """加载配置文件"""
        if not self.config_path.exists():
            logger.warning(f"广告配置文件不存在: {self.config_path}")
            logger.warning("使用默认配置（NVIDIA算力）")
            # 使用默认配置
            self._create_default_config()
            return

        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)

            # 加载广告配置
            for ad_data in config_data.get('ads', []):
                ad = AdConfig(**ad_data)
                self.ads.append(ad)

            # 加载系统设置
            if 'settings' in config_data:
                self.settings = AdsSettings(**config_data['settings'])

            logger.info(f"已加载 {len(self.ads)} 个广告配置")
            enabled_ads = [ad for ad in self.ads if ad.enabled]
            logger.info(f"启用的广告: {', '.join([ad.name for ad in enabled_ads])}")

        except Exception as e:
            logger.error(f"加载广告配置失败: {e}")
            self._create_default_config()

    def _create_default_config(self):
        """创建默认配置（NVIDIA算力）"""
        default_ad = AdConfig(
            id="nvidia_gpu",
            name="NVIDIA算力",
            product="NVIDIA GPU",
            category="科技/算力",
            enabled=True,
            priority=1,
            selling_points=["高性能AI算力", "深度学习加速", "训练速度提升"],
            target_scenarios=["AI开发", "深度学习", "科技教程"],
            templates={
                "通用": ["NVIDIA算力，性能强劲"]
            }
        )
        self.ads = [default_ad]

    def get_enabled_ads(self) -> List[AdConfig]:
        """获取所有启用的广告"""
        return [ad for ad in self.ads if ad.enabled]

    def get_ad_by_id(self, ad_id: str) -> Optional[AdConfig]:
        """根据ID获取广告配置"""
        for ad in self.ads:
            if ad.id == ad_id:
                return ad
        return None

    def get_primary_ad(self) -> Optional[AdConfig]:
        """
        获取主要广告（优先级最高且启用的）

        Returns:
            AdConfig或None
        """
        enabled_ads = self.get_enabled_ads()
        if not enabled_ads:
            return None

        # 按优先级排序，返回最高优先级的
        enabled_ads.sort(key=lambda x: x.priority)
        return enabled_ads[0]

    def select_ad_for_video(self, video_theme: str = "") -> Optional[AdConfig]:
        """
        根据视频主题选择合适的广告

        Args:
            video_theme: 视频主题/类型

        Returns:
            选中的广告配置
        """
        enabled_ads = self.get_enabled_ads()
        if not enabled_ads:
            logger.warning("没有启用的广告")
            return None

        # 简单策略：匹配target_scenarios
        for ad in enabled_ads:
            if any(scenario in video_theme for scenario in ad.target_scenarios):
                logger.info(f"根据主题'{video_theme}'选择广告: {ad.name}")
                return ad

        # 没有匹配，返回主要广告
        primary = self.get_primary_ad()
        logger.info(f"使用主要广告: {primary.name}")
        return primary

    def get_ad_prompt_context(self, ad: AdConfig) -> str:
        """
        获取广告的Prompt上下文（用于LLM生成广告词）

        Args:
            ad: 广告配置

        Returns:
            Prompt文本
        """
        context = f"""
产品名称: {ad.product}
产品类别: {ad.category}
核心卖点: {ad.get_selling_points_text()}
风格要求: {self.settings.ad_script_style}、{self.settings.ad_script_tone}
        """.strip()

        return context

    def reload(self):
        """重新加载配置"""
        self.ads = []
        self._load_config()


# 全局广告管理器
ads_manager = AdsManager()
