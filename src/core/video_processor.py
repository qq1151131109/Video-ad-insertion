"""
视频处理模块

提供视频基础操作：
- 元数据提取
- 音频提取
- 关键帧提取
"""
from pathlib import Path
from typing import Optional, List
import numpy as np

from moviepy import VideoFileClip
import cv2

from src.models.video_models import VideoMetadata
from src.utils.logger import logger
from src.utils.file_manager import TempFileManager


class VideoProcessor:
    """视频处理器"""

    def __init__(self, video_path: str):
        """
        初始化视频处理器

        Args:
            video_path: 视频文件路径

        Raises:
            FileNotFoundError: 视频文件不存在
        """
        self.video_path = Path(video_path)

        if not self.video_path.exists():
            raise FileNotFoundError(f"视频文件不存在: {self.video_path}")

        self.video_clip: Optional[VideoFileClip] = None
        self.metadata: Optional[VideoMetadata] = None

        logger.info(f"视频处理器初始化: {self.video_path.name}")

    def extract_metadata(self) -> VideoMetadata:
        """
        提取视频元数据

        Returns:
            VideoMetadata对象

        Raises:
            Exception: 提取失败
        """
        logger.info("提取视频元数据...")

        try:
            # 使用moviepy提取基本信息
            clip = VideoFileClip(str(self.video_path))

            # 使用opencv获取更详细的信息
            cap = cv2.VideoCapture(str(self.video_path))

            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            duration = total_frames / fps if fps > 0 else 0

            # 获取编码信息
            fourcc = int(cap.get(cv2.CAP_PROP_FOURCC))
            codec = "".join([chr((fourcc >> 8 * i) & 0xFF) for i in range(4)])

            cap.release()

            # 检查音频
            has_audio = clip.audio is not None
            audio_codec = None
            if has_audio:
                # moviepy的音频编码信息
                audio_codec = "aac"  # 默认值，moviepy不直接提供

            # 文件大小
            filesize = self.video_path.stat().st_size

            metadata = VideoMetadata(
                width=width,
                height=height,
                fps=fps,
                duration=duration,
                codec=codec,
                audio_codec=audio_codec,
                has_audio=has_audio,
                filesize=filesize
            )

            self.metadata = metadata
            self.video_clip = clip  # 保存clip供后续使用

            logger.success(f"✓ 元数据提取成功: {metadata}")
            return metadata

        except Exception as e:
            logger.error(f"元数据提取失败: {e}")
            raise

    def extract_audio(self, output_path: str, fps: int = 44100) -> str:
        """
        提取音频轨道

        Args:
            output_path: 输出音频文件路径
            fps: 音频采样率（默认44100Hz）

        Returns:
            输出文件路径

        Raises:
            Exception: 提取失败或视频无音频
        """
        logger.info("提取音频轨道...")

        output_path = Path(output_path)

        if self.video_clip is None:
            self.video_clip = VideoFileClip(str(self.video_path))

        if self.video_clip.audio is None:
            raise Exception("视频没有音频轨道")

        try:
            # 确保输出目录存在
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # 提取音频
            self.video_clip.audio.write_audiofile(
                str(output_path),
                fps=fps,
                codec='pcm_s16le',  # WAV格式
                logger=None  # 禁用moviepy的日志
            )

            logger.success(f"✓ 音频提取成功: {output_path}")
            return str(output_path)

        except Exception as e:
            logger.error(f"音频提取失败: {e}")
            raise

    def extract_frame_at_time(self, timestamp: float, output_path: Optional[str] = None) -> np.ndarray:
        """
        提取指定时间点的视频帧

        Args:
            timestamp: 时间戳（秒）
            output_path: 输出图片路径（可选）

        Returns:
            图像数组（RGB格式）

        Raises:
            ValueError: 时间戳超出范围
        """
        if self.metadata and timestamp > self.metadata.duration:
            raise ValueError(f"时间戳超出视频时长: {timestamp}s > {self.metadata.duration}s")

        if self.video_clip is None:
            self.video_clip = VideoFileClip(str(self.video_path))

        logger.debug(f"提取帧: t={timestamp}s")

        # 提取帧
        frame = self.video_clip.get_frame(timestamp)

        # 保存（如果指定路径）
        if output_path:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # 转换为BGR（OpenCV格式）并保存
            frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            cv2.imwrite(str(output_path), frame_bgr)
            logger.debug(f"帧已保存: {output_path}")

        return frame

    def extract_frames_in_range(
        self,
        start_time: float,
        end_time: float,
        num_frames: int = 10,
        file_manager: Optional[TempFileManager] = None
    ) -> List[np.ndarray]:
        """
        提取时间范围内的多个帧

        Args:
            start_time: 开始时间（秒）
            end_time: 结束时间（秒）
            num_frames: 提取帧数
            file_manager: 文件管理器（可选，用于保存）

        Returns:
            帧列表（RGB格式）

        Raises:
            ValueError: 时间范围无效
        """
        if start_time >= end_time:
            raise ValueError(f"时间范围无效: {start_time} >= {end_time}")

        if self.metadata and end_time > self.metadata.duration:
            end_time = self.metadata.duration

        logger.info(f"提取{num_frames}个帧: {start_time:.1f}s ~ {end_time:.1f}s")

        # 计算时间点
        timestamps = np.linspace(start_time, end_time, num_frames)

        frames = []
        for i, timestamp in enumerate(timestamps):
            # 构造输出路径（如果提供了文件管理器）
            output_path = None
            if file_manager:
                output_path = file_manager.get_keyframe_path(f"frame_{i:03d}.jpg")

            frame = self.extract_frame_at_time(timestamp, str(output_path) if output_path else None)
            frames.append(frame)

        logger.success(f"✓ 成功提取{len(frames)}个帧")
        return frames

    def extract_best_frame_around_time(
        self,
        target_time: float,
        window_size: float = 2.0,
        num_candidates: int = 10
    ) -> tuple[np.ndarray, float]:
        """
        在目标时间附近提取最佳帧（清晰度最高）

        Args:
            target_time: 目标时间（秒）
            window_size: 搜索窗口大小（秒）
            num_candidates: 候选帧数量

        Returns:
            (最佳帧, 时间戳)
        """
        start_time = max(0, target_time - window_size / 2)
        end_time = target_time + window_size / 2

        if self.metadata:
            end_time = min(end_time, self.metadata.duration)

        logger.info(f"搜索最佳帧: t={target_time}s ± {window_size/2}s")

        # 提取候选帧
        frames = self.extract_frames_in_range(start_time, end_time, num_candidates)
        timestamps = np.linspace(start_time, end_time, num_candidates)

        # 计算每一帧的清晰度（拉普拉斯方差）
        best_score = -1
        best_frame = None
        best_timestamp = target_time

        for frame, timestamp in zip(frames, timestamps):
            # 转换为灰度图
            gray = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)

            # 计算拉普拉斯方差（清晰度指标）
            laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()

            logger.debug(f"  t={timestamp:.2f}s, 清晰度={laplacian_var:.1f}")

            if laplacian_var > best_score:
                best_score = laplacian_var
                best_frame = frame
                best_timestamp = timestamp

        logger.success(f"✓ 最佳帧: t={best_timestamp:.2f}s, 清晰度={best_score:.1f}")
        return best_frame, best_timestamp

    def close(self):
        """关闭视频文件"""
        if self.video_clip is not None:
            self.video_clip.close()
            self.video_clip = None
            logger.debug("视频文件已关闭")

    def __enter__(self):
        """上下文管理器入口"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器退出"""
        self.close()
