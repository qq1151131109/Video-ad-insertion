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
        transition_hint: Optional[str] = None,
        language: str = "zh"
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
            language: 视频语言（zh/en/ja等，默认中文）

        Returns:
            生成的广告词
        """
        logger.info(f"生成广告词: 产品={ad_config.product}, 语言={language}")

        # 获取适合的模板
        template = ad_config.get_template(video_category)

        # 根据语言设置长度要求
        if language.startswith("zh") or language.startswith("cn"):
            length_requirement = "15-30字"
            language_name = "中文"
        elif language.startswith("en"):
            length_requirement = "5-15 words"
            language_name = "English"
        elif language.startswith("ja"):
            length_requirement = "15-30文字"
            language_name = "日本語"
        elif language.startswith("ko"):
            length_requirement = "15-30자"
            language_name = "한국어"
        else:
            # 默认按中文处理
            length_requirement = "15-30字"
            language_name = language

        # 构建提示词
        system_prompt = f"""You are a creative ad copywriter who excels at creating humorous, contextual soft advertisements in {language_name}.

Your specialty is making ads that:
1. Seamlessly blend with the video content (viewers barely notice it's an ad)
2. Use clever wordplay, humor, or wit related to the video topic
3. Create a natural transition that feels like part of the conversation
4. Are engaging and entertaining, not salesy or pushy
5. Highlight product benefits in a fun, relatable way

Style guidelines:
- Be conversational and friendly
- Use humor when appropriate (puns, clever analogies, playful language)
- Reference the video context directly
- Make it feel like a natural aside or helpful tip from a friend
- Avoid corporate jargon or overly formal language"""

        user_prompt = f"""Video Context:
- Theme: {video_theme}
- Category: {video_category}
- Tone: {video_tone}
- Target Audience: {ad_config.product} users

What was just said (before insertion point):
"{context_before}"

What comes next (after insertion point):
"{context_after}"

{f'Suggested transition approach: {transition_hint}' if transition_hint else ''}

Product to mention:
- Name: {ad_config.product}
- Key Benefits: {ad_config.get_selling_points_text()}

---

Create a humorous, contextual ad script that:
1. References something from the "before" context to create a smooth transition
2. Adds humor, wit, or a clever connection to the video topic
3. Naturally introduces {ad_config.product} as a solution or enhancement
4. Keeps the tone consistent with the video ({video_tone})
5. Length: {length_requirement}
6. Language: {language_name} ONLY

Example approach: "Speaking of [topic from video]... you know what would make this even better? [Product benefit with a playful twist]"

Return ONLY the ad script - no explanations, markers, or meta-commentary."""

        try:
            # 调用OpenAI API
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.9,  # 提高创造力，生成更幽默的内容
                max_tokens=16384  # gpt-4o-mini最大支持16384 tokens（约12288个汉字或49152个英文字符）
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
