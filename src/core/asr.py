"""
语音识别模块

使用OpenAI Whisper进行高精度语音识别，返回带时间戳的文本
"""
import whisper
from pathlib import Path
from typing import Optional, List, Dict, Any
import torch

from src.utils.logger import logger


class TranscriptionSegment:
    """转录片段"""

    def __init__(self, text: str, start: float, end: float, words: Optional[List[Dict]] = None):
        """
        初始化转录片段

        Args:
            text: 文本内容
            start: 开始时间（秒）
            end: 结束时间（秒）
            words: 词级时间戳列表
        """
        self.text = text.strip()
        self.start = start
        self.end = end
        self.words = words or []

    @property
    def duration(self) -> float:
        """片段时长"""
        return self.end - self.start

    def __repr__(self) -> str:
        return f"[{self.start:.2f}s - {self.end:.2f}s] {self.text}"


class TranscriptionResult:
    """转录结果"""

    def __init__(self, segments: List[TranscriptionSegment], language: str, full_text: str):
        """
        初始化转录结果

        Args:
            segments: 片段列表
            language: 检测到的语言
            full_text: 完整文本
        """
        self.segments = segments
        self.language = language
        self.full_text = full_text

    def get_text_at_time(self, time: float, window: float = 0) -> str:
        """
        获取指定时间点的文本

        Args:
            time: 时间点（秒）
            window: 时间窗口（秒），0表示精确匹配片段

        Returns:
            文本内容
        """
        for segment in self.segments:
            if window == 0:
                if segment.start <= time <= segment.end:
                    return segment.text
            else:
                if segment.start - window <= time <= segment.end + window:
                    return segment.text
        return ""

    def get_context(
        self,
        time: float,
        before_sentences: int = 2,
        after_sentences: int = 1
    ) -> tuple[str, str]:
        """
        获取指定时间点的上下文

        Args:
            time: 时间点（秒）
            before_sentences: 前面几句话
            after_sentences: 后面几句话

        Returns:
            (前文, 后文) 元组
        """
        # 找到时间点所在的片段索引
        current_idx = None
        for i, segment in enumerate(self.segments):
            if segment.start <= time <= segment.end:
                current_idx = i
                break

        if current_idx is None:
            # 如果没找到精确匹配，找最近的
            current_idx = min(
                range(len(self.segments)),
                key=lambda i: abs((self.segments[i].start + self.segments[i].end) / 2 - time)
            )

        # 获取前文
        before_start = max(0, current_idx - before_sentences)
        before_text = " ".join(
            seg.text for seg in self.segments[before_start:current_idx]
        )

        # 获取后文
        after_end = min(len(self.segments), current_idx + after_sentences + 1)
        after_text = " ".join(
            seg.text for seg in self.segments[current_idx + 1:after_end]
        )

        return before_text, after_text

    def to_srt(self) -> str:
        """
        转换为SRT字幕格式

        Returns:
            SRT格式字符串
        """
        srt_lines = []
        for i, segment in enumerate(self.segments, 1):
            # 格式化时间戳
            start = self._format_timestamp(segment.start)
            end = self._format_timestamp(segment.end)

            srt_lines.append(f"{i}")
            srt_lines.append(f"{start} --> {end}")
            srt_lines.append(segment.text)
            srt_lines.append("")  # 空行分隔

        return "\n".join(srt_lines)

    @staticmethod
    def _format_timestamp(seconds: float) -> str:
        """格式化时间戳为SRT格式: HH:MM:SS,mmm"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

    def __repr__(self) -> str:
        return f"TranscriptionResult(language={self.language}, segments={len(self.segments)})"


class ASRService:
    """语音识别服务"""

    def __init__(self, model_name: str = "medium", device: Optional[str] = None):
        """
        初始化ASR服务

        Args:
            model_name: Whisper模型名称
                - tiny: 最快，精度较低 (~1GB)
                - base: 快速，精度一般 (~1GB)
                - small: 平衡，精度较好 (~2GB)
                - medium: 推荐，精度很好 (~5GB)
                - large: 最佳精度，速度慢 (~10GB)
            device: 设备 ("cuda" | "cpu" | None=自动检测)
        """
        self.model_name = model_name

        # 自动检测设备
        if device is None:
            device = "cuda" if torch.cuda.is_available() else "cpu"
        self.device = device

        logger.info(f"ASR服务初始化: model={model_name}, device={device}")

        # 延迟加载模型（首次使用时加载）
        self._model: Optional[whisper.Whisper] = None

    def _load_model(self):
        """加载Whisper模型"""
        if self._model is None:
            logger.info(f"加载Whisper模型: {self.model_name}")
            logger.info("⚠️  首次运行会自动下载模型，可能需要几分钟")

            self._model = whisper.load_model(self.model_name, device=self.device)

            logger.success(f"✓ Whisper模型已加载")

    def transcribe(
        self,
        audio_path: str,
        language: Optional[str] = None,
        word_timestamps: bool = True,
        initial_prompt: Optional[str] = None
    ) -> TranscriptionResult:
        """
        转录音频文件

        Args:
            audio_path: 音频文件路径
            language: 语言代码（None=自动检测，"zh"=中文，"en"=英文等）
            word_timestamps: 是否生成词级时间戳
            initial_prompt: 初始提示（可用于提高特定术语的识别准确度）

        Returns:
            转录结果

        Raises:
            FileNotFoundError: 音频文件不存在
            Exception: 转录失败
        """
        audio_path = Path(audio_path)

        if not audio_path.exists():
            raise FileNotFoundError(f"音频文件不存在: {audio_path}")

        # 加载模型
        self._load_model()

        logger.info(f"开始语音识别: {audio_path.name}")
        if language:
            logger.info(f"指定语言: {language}")

        try:
            # 执行转录
            result = self._model.transcribe(
                str(audio_path),
                language=language,
                word_timestamps=word_timestamps,
                initial_prompt=initial_prompt,
                verbose=False
            )

            # 解析结果
            segments = []
            for seg in result["segments"]:
                # 提取词级时间戳（如果有）
                words = []
                if "words" in seg:
                    words = seg["words"]

                segments.append(TranscriptionSegment(
                    text=seg["text"],
                    start=seg["start"],
                    end=seg["end"],
                    words=words
                ))

            detected_language = result.get("language", "unknown")
            full_text = result["text"]

            transcription_result = TranscriptionResult(
                segments=segments,
                language=detected_language,
                full_text=full_text
            )

            logger.success(f"✓ 语音识别完成: {len(segments)}个片段, 语言={detected_language}")
            logger.info(f"总文本长度: {len(full_text)}字符")

            return transcription_result

        except Exception as e:
            logger.error(f"语音识别失败: {e}")
            raise

    @staticmethod
    def check_installation() -> bool:
        """
        检查Whisper是否已安装

        Returns:
            是否已安装
        """
        try:
            import whisper
            logger.info("✓ Whisper已安装")
            return True
        except ImportError:
            logger.error("✗ Whisper未安装，请运行: pip install openai-whisper")
            return False

    @staticmethod
    def get_available_models() -> List[str]:
        """
        获取可用的Whisper模型列表

        Returns:
            模型名称列表
        """
        return ["tiny", "base", "small", "medium", "large"]
