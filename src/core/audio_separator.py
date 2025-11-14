"""
音频分离模块

使用Demucs进行人声分离，从混合音频中提取纯人声
"""
import subprocess
from pathlib import Path
from typing import Optional

from src.utils.logger import logger


class AudioSeparator:
    """音频分离器（基于Demucs）"""

    def __init__(self, model: str = "htdemucs"):
        """
        初始化音频分离器

        Args:
            model: Demucs模型名称
                - htdemucs: 混合Transformer模型（推荐，质量最好）
                - mdx_extra: MDX模型（速度快）
                - mdx: 标准MDX模型
        """
        self.model = model
        logger.info(f"音频分离器初始化: model={model}")

    def separate(
        self,
        audio_path: str,
        output_dir: str,
        extract_vocals_only: bool = True,
        device: str = "cuda"
    ) -> str:
        """
        分离音频

        Args:
            audio_path: 输入音频文件路径
            output_dir: 输出目录
            extract_vocals_only: 是否只提取人声（True则只保存人声，False保存所有分离结果）
            device: 设备 ("cuda" | "cpu")

        Returns:
            人声文件路径

        Raises:
            FileNotFoundError: 输入文件不存在
            Exception: 分离失败
        """
        audio_path = Path(audio_path)
        output_dir = Path(output_dir)

        if not audio_path.exists():
            raise FileNotFoundError(f"音频文件不存在: {audio_path}")

        output_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"开始人声分离: {audio_path.name}")
        logger.info(f"模型: {self.model}, 设备: {device}")

        # 构建demucs命令
        cmd = [
            "demucs",
            "--two-stems", "vocals",  # 只分离人声和其他
            "-n", self.model,
            "-o", str(output_dir),
            "--device", device,
            str(audio_path)
        ]

        try:
            # 运行demucs
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )

            logger.debug(f"Demucs输出: {result.stdout}")

            # Demucs的输出路径: output_dir / model / audio_stem / vocals.wav
            audio_stem = audio_path.stem
            vocals_path = output_dir / self.model / audio_stem / "vocals.wav"

            if not vocals_path.exists():
                raise Exception(f"人声文件未生成: {vocals_path}")

            logger.success(f"✓ 人声分离成功: {vocals_path}")

            # 如果只需要人声，可以移动到输出目录根目录并清理
            if extract_vocals_only:
                final_path = output_dir / "vocals.wav"
                vocals_path.rename(final_path)

                # 清理其他文件
                import shutil
                model_dir = output_dir / self.model
                if model_dir.exists():
                    shutil.rmtree(model_dir)

                logger.info(f"人声文件已移动到: {final_path}")
                return str(final_path)

            return str(vocals_path)

        except subprocess.CalledProcessError as e:
            error_msg = f"Demucs运行失败: {e.stderr}"
            logger.error(error_msg)
            raise Exception(error_msg)

        except Exception as e:
            logger.error(f"人声分离失败: {e}")
            raise

    def separate_simple(
        self,
        audio_path: str,
        output_path: str,
        device: str = "cuda"
    ) -> str:
        """
        简化的人声分离方法（直接指定输出路径）

        Args:
            audio_path: 输入音频文件
            output_path: 输出人声文件路径
            device: 设备

        Returns:
            输出文件路径
        """
        output_path = Path(output_path)
        output_dir = output_path.parent

        # 执行分离
        vocals_path = self.separate(
            audio_path=audio_path,
            output_dir=str(output_dir),
            extract_vocals_only=True,
            device=device
        )

        # 重命名到目标路径
        vocals_path = Path(vocals_path)
        if vocals_path != output_path:
            vocals_path.rename(output_path)

        return str(output_path)

    @staticmethod
    def check_installation() -> bool:
        """
        检查Demucs是否已安装

        Returns:
            bool: 是否已安装
        """
        try:
            result = subprocess.run(
                ["demucs", "--help"],
                capture_output=True,
                check=True
            )
            logger.info("✓ Demucs已安装")
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            logger.error("✗ Demucs未安装，请运行: pip install demucs")
            return False

    @staticmethod
    def get_available_models() -> list:
        """
        获取可用的Demucs模型列表

        Returns:
            模型名称列表
        """
        return [
            "htdemucs",      # Hybrid Transformer Demucs (最佳质量)
            "htdemucs_ft",   # Fine-tuned version
            "mdx_extra",     # MDX Extra (快速)
            "mdx",           # MDX (标准)
            "mdx_q",         # MDX Quantized
            "mdx_extra_q"    # MDX Extra Quantized
        ]
