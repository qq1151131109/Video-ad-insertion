"""
视频合成服务

实现视频剪辑、拼接和音频混合，将数字人广告插入原视频
"""
from pathlib import Path
from typing import Optional, List, Tuple
from moviepy import (
    VideoFileClip,
    AudioFileClip,
    concatenate_videoclips,
    CompositeAudioClip
)
import numpy as np

from src.utils.logger import logger


class VideoComposer:
    """视频合成器"""

    def __init__(self):
        """初始化视频合成器"""
        logger.info("视频合成器初始化")

    def split_video_at_time(
        self,
        video_path: str,
        split_time: float,
        output_dir: str
    ) -> Tuple[str, str]:
        """
        在指定时间点切分视频

        Args:
            video_path: 输入视频路径
            split_time: 切分时间点（秒）
            output_dir: 输出目录

        Returns:
            (前半段路径, 后半段路径)
        """
        video_path = Path(video_path)
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"切分视频: {video_path.name} 在 {split_time:.2f}秒")

        try:
            # 加载视频
            video = VideoFileClip(str(video_path))

            # 检查切分时间
            if split_time <= 0 or split_time >= video.duration:
                raise ValueError(f"切分时间{split_time}s不在有效范围(0, {video.duration}s)")

            # 切分为两段（moviepy v2: 使用 subclipped）
            part1 = video.subclipped(0, split_time)
            part2 = video.subclipped(split_time, video.duration)

            # 保存
            part1_path = output_dir / "part1.mp4"
            part2_path = output_dir / "part2.mp4"

            logger.info(f"保存前半段: 0s - {split_time:.2f}s")
            part1.write_videofile(
                str(part1_path),
                codec='libx264',
                audio_codec='aac',
                temp_audiofile=str(output_dir / 'temp_audio1.m4a'),
                remove_temp=True,
                logger=None  # 禁用moviepy的日志
            )

            logger.info(f"保存后半段: {split_time:.2f}s - {video.duration:.2f}s")
            part2.write_videofile(
                str(part2_path),
                codec='libx264',
                audio_codec='aac',
                temp_audiofile=str(output_dir / 'temp_audio2.m4a'),
                remove_temp=True,
                logger=None
            )

            # 关闭视频
            part1.close()
            part2.close()
            video.close()

            logger.success(f"✓ 视频切分完成")
            logger.info(f"  前半段: {part1_path.name}")
            logger.info(f"  后半段: {part2_path.name}")

            return str(part1_path), str(part2_path)

        except Exception as e:
            logger.error(f"视频切分失败: {e}")
            raise

    def concatenate_videos(
        self,
        video_paths: List[str],
        output_path: str,
        method: str = "compose"
    ) -> str:
        """
        拼接多个视频

        Args:
            video_paths: 视频路径列表（按顺序）
            output_path: 输出路径
            method: 拼接方法
                - "compose": 使用原视频参数
                - "chain": 简单链接（可能有参数不匹配问题）

        Returns:
            输出视频路径
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        logger.info(f"拼接 {len(video_paths)} 个视频片段")

        try:
            # 加载所有视频
            clips = [VideoFileClip(str(path)) for path in video_paths]

            # 显示每个片段信息
            for i, clip in enumerate(clips, 1):
                logger.info(f"  片段{i}: {clip.duration:.2f}s, {clip.size[0]}x{clip.size[1]}, {clip.fps}fps")

            # 拼接
            logger.info(f"拼接方法: {method}")
            final_clip = concatenate_videoclips(clips, method=method)

            # 保存
            logger.info(f"保存拼接视频: {output_path.name}")
            final_clip.write_videofile(
                str(output_path),
                codec='libx264',
                audio_codec='aac',
                temp_audiofile=str(output_path.parent / 'temp_audio_final.m4a'),
                remove_temp=True,
                logger=None
            )

            # 关闭所有片段
            for clip in clips:
                clip.close()
            final_clip.close()

            logger.success(f"✓ 视频拼接完成: {output_path.name}")
            logger.info(f"  总时长: {VideoFileClip(str(output_path)).duration:.2f}s")

            return str(output_path)

        except Exception as e:
            logger.error(f"视频拼接失败: {e}")
            raise

    def insert_ad_video(
        self,
        original_video_path: str,
        ad_video_path: str,
        insertion_time: float,
        output_path: str
    ) -> str:
        """
        在原视频中插入广告视频

        Args:
            original_video_path: 原视频路径
            ad_video_path: 广告视频路径
            insertion_time: 插入时间点（秒）
            output_path: 输出路径

        Returns:
            输出视频路径
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        logger.info("=" * 60)
        logger.info("插入广告视频")
        logger.info("=" * 60)
        logger.info(f"原视频: {Path(original_video_path).name}")
        logger.info(f"广告视频: {Path(ad_video_path).name}")
        logger.info(f"插入时间: {insertion_time:.2f}s")

        try:
            # 1. 切分原视频
            logger.info("\n[1/2] 切分原视频...")
            temp_dir = output_path.parent / "temp_splits"
            part1_path, part2_path = self.split_video_at_time(
                video_path=original_video_path,
                split_time=insertion_time,
                output_dir=str(temp_dir)
            )

            # 2. 拼接三段视频
            logger.info("\n[2/2] 拼接视频...")
            video_paths = [part1_path, ad_video_path, part2_path]

            final_path = self.concatenate_videos(
                video_paths=video_paths,
                output_path=str(output_path),
                method="compose"
            )

            # 清理临时文件
            logger.info("\n清理临时文件...")
            import shutil
            if temp_dir.exists():
                shutil.rmtree(temp_dir)

            logger.success("\n✓ 广告插入完成！")
            logger.info(f"输出: {output_path}")

            return final_path

        except Exception as e:
            logger.error(f"广告插入失败: {e}")
            raise

    def add_audio_fade(
        self,
        audio_path: str,
        output_path: str,
        fade_in_duration: float = 0.5,
        fade_out_duration: float = 0.5
    ) -> str:
        """
        为音频添加淡入淡出效果

        Args:
            audio_path: 输入音频路径
            output_path: 输出音频路径
            fade_in_duration: 淡入时长（秒）
            fade_out_duration: 淡出时长（秒）

        Returns:
            输出音频路径
        """
        logger.info(f"添加音频淡入淡出: fade_in={fade_in_duration}s, fade_out={fade_out_duration}s")

        try:
            # 加载音频
            audio = AudioFileClip(str(audio_path))

            # 添加淡入淡出
            audio = audio.audio_fadein(fade_in_duration).audio_fadeout(fade_out_duration)

            # 保存
            audio.write_audiofile(str(output_path), logger=None)

            audio.close()

            logger.success(f"✓ 音频淡入淡出完成")

            return str(output_path)

        except Exception as e:
            logger.error(f"音频淡入淡出失败: {e}")
            raise

    def mix_audio_tracks(
        self,
        audio_paths: List[str],
        output_path: str,
        volumes: Optional[List[float]] = None
    ) -> str:
        """
        混合多个音轨

        Args:
            audio_paths: 音频路径列表
            output_path: 输出路径
            volumes: 各音轨的音量（0-1），None则使用默认值1.0

        Returns:
            输出音频路径
        """
        logger.info(f"混合 {len(audio_paths)} 个音轨")

        if volumes is None:
            volumes = [1.0] * len(audio_paths)

        if len(volumes) != len(audio_paths):
            raise ValueError(f"音量列表长度({len(volumes)})与音轨数量({len(audio_paths)})不匹配")

        try:
            # 加载所有音轨
            audio_clips = []
            for i, (path, vol) in enumerate(zip(audio_paths, volumes), 1):
                clip = AudioFileClip(str(path))
                if vol != 1.0:
                    clip = clip.volumex(vol)
                audio_clips.append(clip)
                logger.info(f"  音轨{i}: {Path(path).name}, 音量={vol}")

            # 混合
            composite = CompositeAudioClip(audio_clips)

            # 保存
            composite.write_audiofile(str(output_path), logger=None)

            # 关闭
            for clip in audio_clips:
                clip.close()
            composite.close()

            logger.success(f"✓ 音轨混合完成")

            return str(output_path)

        except Exception as e:
            logger.error(f"音轨混合失败: {e}")
            raise

    @staticmethod
    def get_video_info(video_path: str) -> dict:
        """
        获取视频信息

        Args:
            video_path: 视频路径

        Returns:
            视频信息字典
        """
        try:
            video = VideoFileClip(str(video_path))

            info = {
                "duration": video.duration,
                "fps": video.fps,
                "size": video.size,
                "width": video.w,
                "height": video.h,
                "has_audio": video.audio is not None
            }

            video.close()

            return info

        except Exception as e:
            logger.error(f"获取视频信息失败: {e}")
            raise
