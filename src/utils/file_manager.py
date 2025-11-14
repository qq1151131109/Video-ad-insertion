"""
临时文件管理器

管理视频处理过程中产生的临时文件：
- 音频文件
- 关键帧图片
- ASR转写结果
- 广告素材
"""
import shutil
import time
from pathlib import Path
from typing import Optional, List
from datetime import datetime

from src.config.settings import settings
from src.utils.logger import logger


class TempFileManager:
    """临时文件管理器"""

    def __init__(self, video_id: str):
        """
        初始化文件管理器

        Args:
            video_id: 视频唯一标识（通常使用视频文件名）
        """
        self.video_id = video_id
        self.base_dir = settings.CACHE_DIR / video_id
        self.created_files: List[Path] = []  # 记录创建的文件

        # 创建目录
        self._ensure_directories()

        logger.debug(f"文件管理器初始化: {self.base_dir}")

    def _ensure_directories(self):
        """确保所有必要的子目录存在"""
        subdirs = ['audio', 'keyframes', 'transcriptions', 'ad_materials', 'videos']

        for subdir in subdirs:
            dir_path = self.base_dir / subdir
            dir_path.mkdir(parents=True, exist_ok=True)

    def get_path(self, category: str, filename: str, create_dir: bool = True) -> Path:
        """
        获取临时文件路径

        Args:
            category: 文件类别 (audio | keyframes | transcriptions | ad_materials | videos)
            filename: 文件名
            create_dir: 是否创建目录（默认True）

        Returns:
            完整文件路径
        """
        if category not in ['audio', 'keyframes', 'transcriptions', 'ad_materials', 'videos']:
            raise ValueError(f"Invalid category: {category}")

        dir_path = self.base_dir / category
        if create_dir:
            dir_path.mkdir(parents=True, exist_ok=True)

        file_path = dir_path / filename
        self.created_files.append(file_path)

        return file_path

    # ==================== 便捷方法 ====================

    def get_audio_path(self, filename: str) -> Path:
        """获取音频文件路径"""
        return self.get_path('audio', filename)

    def get_keyframe_path(self, filename: str) -> Path:
        """获取关键帧路径"""
        return self.get_path('keyframes', filename)

    def get_transcription_path(self, filename: str = "transcription.json") -> Path:
        """获取转写结果路径"""
        return self.get_path('transcriptions', filename)

    def get_ad_material_path(self, filename: str) -> Path:
        """获取广告素材路径"""
        return self.get_path('ad_materials', filename)

    def get_video_path(self, filename: str) -> Path:
        """获取视频文件路径"""
        return self.get_path('videos', filename)

    # ==================== 特定文件路径 ====================

    @property
    def original_audio_path(self) -> Path:
        """原始音频路径"""
        return self.get_audio_path("original.wav")

    @property
    def separated_vocals_path(self) -> Path:
        """分离后的人声路径"""
        return self.get_audio_path("vocals.wav")

    @property
    def voice_sample_path(self) -> Path:
        """人声样本路径（用于声音克隆）"""
        return self.get_audio_path("voice_sample.wav")

    @property
    def cloned_audio_path(self) -> Path:
        """克隆后的音频路径"""
        return self.get_ad_material_path("cloned_voice.mp3")

    @property
    def cleaned_image_path(self) -> Path:
        """清洗后的图片路径"""
        return self.get_ad_material_path("cleaned_image.png")

    @property
    def digital_human_video_path(self) -> Path:
        """数字人视频路径"""
        return self.get_ad_material_path("digital_human.mp4")

    @property
    def final_video_path(self) -> Path:
        """最终视频路径（在output目录）"""
        output_dir = settings.OUTPUT_DIR / "processed"
        output_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return output_dir / f"{self.video_id}_{timestamp}.mp4"

    # ==================== 文件操作 ====================

    def file_exists(self, category: str, filename: str) -> bool:
        """检查文件是否存在"""
        path = self.get_path(category, filename, create_dir=False)
        return path.exists()

    def save_text(self, category: str, filename: str, content: str):
        """保存文本文件"""
        path = self.get_path(category, filename)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        logger.debug(f"文本已保存: {path}")

    def load_text(self, category: str, filename: str) -> Optional[str]:
        """加载文本文件"""
        path = self.get_path(category, filename, create_dir=False)
        if not path.exists():
            return None

        with open(path, 'r', encoding='utf-8') as f:
            return f.read()

    def copy_file(self, src: Path, dst_category: str, dst_filename: str):
        """
        复制文件到临时目录

        Args:
            src: 源文件路径
            dst_category: 目标类别
            dst_filename: 目标文件名
        """
        dst = self.get_path(dst_category, dst_filename)
        shutil.copy2(src, dst)
        logger.debug(f"文件已复制: {src.name} -> {dst}")

    # ==================== 清理操作 ====================

    def cleanup(self, keep_on_error: bool = None):
        """
        清理临时文件

        Args:
            keep_on_error: 是否在错误时保留文件（默认使用settings配置）
        """
        if keep_on_error is None:
            keep_on_error = settings.KEEP_TEMP_FILES_ON_ERROR

        if keep_on_error:
            logger.info(f"保留临时文件用于调试: {self.base_dir}")
            return

        if self.base_dir.exists():
            shutil.rmtree(self.base_dir)
            logger.info(f"临时文件已清理: {self.base_dir}")

    def cleanup_category(self, category: str):
        """清理特定类别的文件"""
        category_dir = self.base_dir / category
        if category_dir.exists():
            shutil.rmtree(category_dir)
            category_dir.mkdir(parents=True, exist_ok=True)
            logger.debug(f"已清理{category}目录")

    def get_size(self) -> int:
        """
        获取临时文件总大小（字节）

        Returns:
            总大小（字节）
        """
        total_size = 0
        if self.base_dir.exists():
            for file_path in self.base_dir.rglob('*'):
                if file_path.is_file():
                    total_size += file_path.stat().st_size
        return total_size

    def get_size_mb(self) -> float:
        """获取临时文件总大小（MB）"""
        return self.get_size() / (1024 * 1024)

    @staticmethod
    def cleanup_expired(ttl: int = None):
        """
        清理过期的临时文件

        Args:
            ttl: 过期时间（秒），默认使用settings配置
        """
        if ttl is None:
            ttl = settings.TEMP_FILES_TTL

        cache_dir = settings.CACHE_DIR
        if not cache_dir.exists():
            return

        current_time = time.time()
        cleaned_count = 0

        for video_dir in cache_dir.iterdir():
            if not video_dir.is_dir():
                continue

            # 检查目录的最后修改时间
            mtime = video_dir.stat().st_mtime
            age = current_time - mtime

            if age > ttl:
                try:
                    shutil.rmtree(video_dir)
                    cleaned_count += 1
                    logger.info(f"已清理过期目录: {video_dir.name} (age={age/3600:.1f}h)")
                except Exception as e:
                    logger.error(f"清理失败: {video_dir.name} - {e}")

        if cleaned_count > 0:
            logger.info(f"共清理 {cleaned_count} 个过期目录")

    def __enter__(self):
        """上下文管理器入口"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器退出"""
        # 如果发生异常且配置为保留文件，则不清理
        if exc_type is not None and settings.KEEP_TEMP_FILES_ON_ERROR:
            logger.warning(f"发生错误，保留临时文件: {self.base_dir}")
        else:
            # 正常完成或配置为不保留，则清理
            if exc_type is None:
                self.cleanup(keep_on_error=False)
