"""
LLM服务模块

使用OpenAI API进行视频内容分析、插入点检测和广告词生成
"""
from typing import List, Dict, Optional, Any
from openai import OpenAI
from pydantic import BaseModel
import json

from src.config.settings import settings
from src.config.ads import AdConfig
from src.utils.logger import logger


class InsertionPoint(BaseModel):
    """广告插入点"""
    time: float  # 插入时间点（秒）
    priority: int  # 优先级 (1=最高)
    reason: str  # 选择理由
    context_before: str  # 前文（2-3句）
    context_after: str  # 后文（1-2句）
    transition_hint: str  # 过渡提示


class VideoAnalysis(BaseModel):
    """视频分析结果"""
    theme: str  # 视频主题
    category: str  # 内容类别（如：科技、教育、生活等）
    key_points: List[str]  # 关键要点
    tone: str  # 语气风格（如：正式、轻松、幽默等）
    target_audience: str  # 目标受众
    insertion_points: List[InsertionPoint]  # 推荐的插入点（按优先级排序）


class LLMService:
    """LLM服务"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None
    ):
        """
        初始化LLM服务

        Args:
            api_key: OpenAI API密钥（默认从settings读取）
            base_url: API基础URL（默认从settings读取）
            model: 模型名称（默认从settings读取）
        """
        self.api_key = api_key or settings.OPENAI_API_KEY
        self.base_url = base_url or settings.OPENAI_BASE_URL
        self.model = model or settings.OPENAI_MODEL

        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url
        )

        logger.info(f"LLM服务初始化: model={self.model}")

    def analyze_video_content(
        self,
        transcription_segments: List[Dict[str, Any]],
        video_duration: float,
        avoid_start: float = 5.0,
        avoid_end: float = 5.0,
        num_candidates: int = 3
    ) -> VideoAnalysis:
        """
        分析视频内容并推荐广告插入点

        Args:
            transcription_segments: 转录片段列表 [{"text": "...", "start": 0.0, "end": 1.5}, ...]
            video_duration: 视频总时长（秒）
            avoid_start: 避开开头的时长（秒）
            avoid_end: 避开结尾的时长（秒）
            num_candidates: 返回候选插入点数量

        Returns:
            视频分析结果
        """
        logger.info("开始LLM内容分析...")

        # 构建完整文本
        full_text = " ".join(seg["text"] for seg in transcription_segments)

        # 构建提示词
        system_prompt = """你是一个专业的视频内容分析师，专门负责分析短视频内容并推荐合适的广告插入点。

你的任务是：
1. 分析视频的主题、类别、关键要点、语气风格和目标受众
2. 找出3个最适合插入广告的时间点，要求：
   - 避开视频开头和结尾
   - 选择自然的过渡位置（如话题转换、段落结束等）
   - 确保插入后不会破坏内容连贯性
   - 提供每个插入点前后的上下文（前2-3句，后1-2句）

请以JSON格式返回分析结果。"""

        user_prompt = f"""请分析以下视频转录内容：

视频时长: {video_duration:.1f}秒
避开区间: 开头{avoid_start}秒, 结尾{avoid_end}秒

转录内容:
{self._format_transcription(transcription_segments)}

---

请返回JSON格式的分析结果，包含以下字段：
{{
    "theme": "视频主题的一句话描述",
    "category": "内容类别（如：科技、教育、生活、娱乐等）",
    "key_points": ["要点1", "要点2", "要点3"],
    "tone": "语气风格（如：正式、轻松、幽默、专业等）",
    "target_audience": "目标受众描述",
    "insertion_points": [
        {{
            "time": 插入时间点（秒，浮点数）,
            "priority": 优先级（1=最高，2=次高，3=第三）,
            "reason": "选择此时间点的理由",
            "context_before": "插入点前面的2-3句话",
            "context_after": "插入点后面的1-2句话",
            "transition_hint": "建议如何自然过渡到广告"
        }},
        // ... 共{num_candidates}个插入点
    ]
}}"""

        try:
            # 调用OpenAI API
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.7
            )

            # 解析响应
            result_text = response.choices[0].message.content
            result_data = json.loads(result_text)

            # 验证并构建结果
            analysis = VideoAnalysis(**result_data)

            logger.success(f"✓ 内容分析完成: 主题={analysis.theme}, 类别={analysis.category}")
            logger.info(f"找到{len(analysis.insertion_points)}个插入点候选")

            return analysis

        except Exception as e:
            logger.error(f"LLM内容分析失败: {e}")
            raise

    def generate_ad_script(
        self,
        video_theme: str,
        video_category: str,
        video_tone: str,
        context_before: str,
        context_after: str,
        ad_config: AdConfig,
        transition_hint: Optional[str] = None
    ) -> str:
        """
        根据视频上下文生成广告词

        Args:
            video_theme: 视频主题
            video_category: 视频类别
            video_tone: 视频语气风格
            context_before: 插入点前文
            context_after: 插入点后文
            ad_config: 广告配置
            transition_hint: 过渡提示

        Returns:
            生成的广告词
        """
        logger.info(f"生成广告词: 产品={ad_config.product}")

        # 获取适合的模板
        template = ad_config.get_template(video_category)

        # 构建提示词
        system_prompt = """你是一个专业的广告文案撰写师，擅长创作自然、不突兀的软性广告。

你的任务是：
1. 根据视频的上下文，生成一段广告词
2. 广告词要自然融入视频内容，不能让人感觉突兀
3. 要体现产品的核心卖点
4. 保持与视频相同的语气风格
5. 长度控制在15-30字"""

        user_prompt = f"""视频信息：
- 主题: {video_theme}
- 类别: {video_category}
- 语气: {video_tone}

广告产品：
- 名称: {ad_config.product}
- 卖点: {ad_config.get_selling_points_text()}

插入点上下文：
前文: {context_before}
后文: {context_after}
{f'过渡提示: {transition_hint}' if transition_hint else ''}

参考模板（可调整）：
{template}

---

请生成一段自然的广告词，要求：
1. 长度15-30字
2. 与上下文自然衔接
3. 突出产品卖点
4. 保持视频的语气风格

请只返回广告词文本，不要包含任何解释或标记。"""

        try:
            # 调用OpenAI API
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.8,
                max_tokens=100
            )

            # 提取广告词
            ad_script = response.choices[0].message.content.strip()

            # 验证长度
            if len(ad_script) < settings.AD_SCRIPT_MIN_LENGTH:
                logger.warning(f"广告词过短({len(ad_script)}字)，使用模板")
                ad_script = template
            elif len(ad_script) > settings.AD_SCRIPT_MAX_LENGTH:
                logger.warning(f"广告词过长({len(ad_script)}字)，截断")
                ad_script = ad_script[:settings.AD_SCRIPT_MAX_LENGTH]

            logger.success(f"✓ 广告词生成完成: {ad_script}")

            return ad_script

        except Exception as e:
            logger.error(f"广告词生成失败: {e}")
            # 失败时使用模板
            logger.info("使用默认模板")
            return template

    def _format_transcription(self, segments: List[Dict[str, Any]]) -> str:
        """
        格式化转录内容为可读文本

        Args:
            segments: 转录片段列表

        Returns:
            格式化的文本
        """
        lines = []
        for seg in segments:
            timestamp = f"[{seg['start']:.1f}s - {seg['end']:.1f}s]"
            text = seg['text'].strip()
            lines.append(f"{timestamp} {text}")

        return "\n".join(lines)

    @staticmethod
    def check_api_key() -> bool:
        """
        检查OpenAI API密钥是否已配置

        Returns:
            是否已配置
        """
        if not settings.OPENAI_API_KEY:
            logger.error("✗ OpenAI API密钥未配置")
            logger.info("请在.env文件中设置: OPENAI_API_KEY=your_key")
            return False

        logger.info("✓ OpenAI API密钥已配置")
        return True
