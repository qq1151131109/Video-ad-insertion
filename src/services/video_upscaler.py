"""
视频超分辨率服务

使用ffmpeg实现高质量的视频缩放，支持多种插值算法
"""
import subprocess
from pathlib import Path
from typing import Optional, Tuple
import cv2

from src.utils.logger import logger


class VideoUpscaler:
    """视频超分辨率处理器"""

    def __init__(self):
        """初始化视频超分辨率处理器"""
        logger.debug("视频超分辨率处理器初始化")

    @staticmethod
    def get_video_resolution(video_path: str) -> Tuple[int, int]:
        """
        获取视频分辨率

        Args:
            video_path: 视频文件路径

        Returns:
            (width, height) 元组
        """
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise ValueError(f"无法打开视频文件: {video_path}")

        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        cap.release()

        return width, height

    def upscale_video(
        self,
        input_video_path: str,
        output_video_path: str,
        target_width: int,
        target_height: int,
        algorithm: str = "lanczos",
        crf: int = 18,
        preset: str = "medium"
    ) -> str:
        """
        使用ffmpeg对视频进行超分辨率处理

        Args:
            input_video_path: 输入视频路径
            output_video_path: 输出视频路径
            target_width: 目标宽度
            target_height: 目标高度
            algorithm: 缩放算法，可选：
                - lanczos: 高质量，适合大多数场景（默认）
                - bicubic: 较快，质量稍低
                - bilinear: 最快，质量最低
                - spline: 平滑效果好
            crf: 视频质量参数(0-51)，值越小质量越高，默认18（高质量）
            preset: 编码速度预设，可选：ultrafast, superfast, veryfast, faster,
                   fast, medium, slow, slower, veryslow

        Returns:
            输出视频路径
        """
        input_path = Path(input_video_path)
        output_path = Path(output_video_path)

        if not input_path.exists():
            raise FileNotFoundError(f"输入视频不存在: {input_path}")

        # 获取输入视频分辨率
        input_width, input_height = self.get_video_resolution(str(input_path))

        logger.info(f"视频超分:")
        logger.info(f"  输入: {input_width}x{input_height}")
        logger.info(f"  输出: {target_width}x{target_height}")
        logger.info(f"  算法: {algorithm}")
        logger.info(f"  质量: CRF={crf}, preset={preset}")

        # 如果分辨率已经匹配，直接复制
        if input_width == target_width and input_height == target_height:
            logger.info("分辨率已匹配，跳过超分")
            import shutil
            shutil.copy2(input_path, output_path)
            return str(output_path)

        # 构建ffmpeg命令
        # 使用高质量的缩放滤镜
        scale_filter = f"scale={target_width}:{target_height}:flags={algorithm}"

        cmd = [
            "ffmpeg",
            "-i", str(input_path),
            "-vf", scale_filter,
            "-c:v", "libx264",
            "-crf", str(crf),
            "-preset", preset,
            "-c:a", "copy",  # 音频直接复制
            "-y",  # 覆盖输出文件
            str(output_path)
        ]

        logger.debug(f"执行命令: {' '.join(cmd)}")

        try:
            # 执行ffmpeg命令
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=True
            )

            # 验证输出文件
            if not output_path.exists():
                raise RuntimeError("输出视频文件未生成")

            # 获取输出视频分辨率验证
            output_width, output_height = self.get_video_resolution(str(output_path))

            if output_width != target_width or output_height != target_height:
                logger.warning(
                    f"输出分辨率({output_width}x{output_height})"
                    f"与目标({target_width}x{target_height})不完全匹配"
                )

            logger.success(f"✓ 视频超分完成")
            logger.info(f"  输出: {output_path.name}")
            logger.info(f"  实际分辨率: {output_width}x{output_height}")

            return str(output_path)

        except subprocess.CalledProcessError as e:
            error_msg = e.stderr if e.stderr else str(e)
            logger.error(f"ffmpeg执行失败: {error_msg}")
            raise RuntimeError(f"视频超分失败: {error_msg}")

    def upscale_to_match(
        self,
        input_video_path: str,
        reference_video_path: str,
        output_video_path: str,
        algorithm: str = "lanczos",
        crf: int = 18,
        preset: str = "medium"
    ) -> str:
        """
        将输入视频超分到与参考视频相同的分辨率

        Args:
            input_video_path: 输入视频路径（低分辨率）
            reference_video_path: 参考视频路径（目标分辨率）
            output_video_path: 输出视频路径
            algorithm: 缩放算法
            crf: 视频质量参数
            preset: 编码速度预设

        Returns:
            输出视频路径
        """
        # 获取参考视频的分辨率
        target_width, target_height = self.get_video_resolution(reference_video_path)

        logger.info(f"将视频超分到参考视频分辨率: {target_width}x{target_height}")

        return self.upscale_video(
            input_video_path=input_video_path,
            output_video_path=output_video_path,
            target_width=target_width,
            target_height=target_height,
            algorithm=algorithm,
            crf=crf,
            preset=preset
        )

    def batch_upscale(
        self,
        input_dir: str,
        output_dir: str,
        target_width: int,
        target_height: int,
        algorithm: str = "lanczos",
        crf: int = 18,
        preset: str = "medium"
    ) -> list[str]:
        """
        批量处理目录中的所有视频

        Args:
            input_dir: 输入目录
            output_dir: 输出目录
            target_width: 目标宽度
            target_height: 目标高度
            algorithm: 缩放算法
            crf: 视频质量参数
            preset: 编码速度预设

        Returns:
            成功处理的输出文件路径列表
        """
        input_path = Path(input_dir)
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # 查找所有视频文件
        video_files = list(input_path.glob("*.mp4"))
        logger.info(f"找到 {len(video_files)} 个视频文件")

        results = []

        for i, video_file in enumerate(video_files, 1):
            logger.info(f"\n处理 [{i}/{len(video_files)}]: {video_file.name}")

            try:
                output_file = output_path / f"{video_file.stem}_upscaled.mp4"

                result_path = self.upscale_video(
                    input_video_path=str(video_file),
                    output_video_path=str(output_file),
                    target_width=target_width,
                    target_height=target_height,
                    algorithm=algorithm,
                    crf=crf,
                    preset=preset
                )

                results.append(result_path)
                logger.success(f"✓ 完成 [{i}/{len(video_files)}]")

            except Exception as e:
                logger.error(f"❌ 处理失败: {e}")
                continue

        logger.info(f"\n批量处理完成: 成功 {len(results)}/{len(video_files)}")
        return results
