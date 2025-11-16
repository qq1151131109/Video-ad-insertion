"""
广告视频生成编排器

统一管理图片清洗、声音克隆、数字人生成三个ComfyUI工作流，
提供端到端的广告视频生成能力
"""
from pathlib import Path
from typing import Optional
from dataclasses import dataclass

from src.services.comfyui_client import ComfyUIClient
from src.services.image_cleaner import ImageCleanerService
from src.services.voice_clone import VoiceCloneService
from src.services.digital_human import DigitalHumanService
from src.utils.logger import logger


@dataclass
class AdVideoResult:
    """广告视频生成结果"""
    cleaned_image_path: str  # 清洗后的人脸图片
    cloned_audio_path: str  # 克隆的广告配音
    digital_human_video_path: str  # 数字人视频
    success: bool  # 是否成功
    error_message: Optional[str] = None  # 错误信息


class AdVideoOrchestrator:
    """广告视频生成编排器"""

    def __init__(self, comfyui_client: Optional[ComfyUIClient] = None):
        """
        初始化编排器

        Args:
            comfyui_client: ComfyUI客户端（None则自动创建）
        """
        # 共享同一个ComfyUI客户端
        self.client = comfyui_client or ComfyUIClient()

        # 初始化三个服务
        self.image_cleaner = ImageCleanerService(client=self.client)
        self.voice_clone = VoiceCloneService(client=self.client)
        self.digital_human = DigitalHumanService(client=self.client)

        logger.info("广告视频生成编排器初始化")

    def generate_ad_video(
        self,
        keyframe_image_path: str,
        reference_audio_path: str,
        ad_script: str,
        output_dir: str,
        clean_image: bool = True,
        emotion: str = "neutral",
        speed: float = 1.0,
        fps: int = 25,
        video_width: Optional[int] = None,  # 原视频宽度
        video_height: Optional[int] = None  # 原视频高度
    ) -> AdVideoResult:
        """
        生成广告视频（完整流程）

        流程：
        1. 清洗关键帧图片（去除文字水印）
        2. 克隆声音（生成广告配音）
        3. 生成数字人视频

        Args:
            keyframe_image_path: 关键帧图片路径
            reference_audio_path: 参考音频路径（人声样本）
            ad_script: 广告词文本
            output_dir: 输出目录
            clean_image: 是否清洗图片（False则跳过第1步）
            emotion: 声音情绪
            speed: 语速
            fps: 数字人视频帧率

        Returns:
            生成结果
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        logger.info("=" * 60)
        logger.info("开始生成广告视频")
        logger.info("=" * 60)
        logger.info(f"关键帧: {Path(keyframe_image_path).name}")
        logger.info(f"参考音频: {Path(reference_audio_path).name}")
        logger.info(f"广告词: {ad_script}")
        logger.info(f"输出目录: {output_dir}")

        try:
            # Step 1: 清洗图片（带重试与降级）
            if clean_image:
                logger.info("\n" + "=" * 60)
                logger.info("Step 1/3: 清洗关键帧图片")
                logger.info("=" * 60)

                cleaned_image_path = str(output_dir / "cleaned_keyframe.jpg")

                import time
                last_err = None
                for attempt in range(1, 3):
                    try:
                        self.image_cleaner.clean_image_simple(
                            input_image_path=keyframe_image_path,
                            output_image_path=cleaned_image_path,
                            remove_text=True,
                            remove_watermark=True
                        )
                        logger.success("✓ Step 1 完成: 图片清洗")
                        break
                    except Exception as e:
                        last_err = e
                        wait_s = 2 * attempt
                        logger.warning(f"图片清洗失败，第{attempt}次重试前等待{wait_s}s: {e}")
                        time.sleep(wait_s)
                else:
                    logger.warning("图片清洗持续失败，降级为使用原图继续流程")
                    cleaned_image_path = keyframe_image_path
            else:
                logger.info("\n跳过图片清洗，直接使用原图")
                cleaned_image_path = keyframe_image_path

            # Step 2: 克隆声音
            logger.info("\n" + "=" * 60)
            logger.info("Step 2/3: 克隆声音生成广告配音")
            logger.info("=" * 60)

            cloned_audio_path = str(output_dir / "ad_voice.wav")

            import time
            last_err = None
            for attempt in range(1, 3):
                try:
                    self.voice_clone.clone_voice(
                        reference_audio_path=reference_audio_path,
                        text=ad_script,
                        output_audio_path=cloned_audio_path,
                        emotion=emotion,
                        speed=speed
                    )
                    break
                except Exception as e:
                    last_err = e
                    wait_s = 2 * attempt
                    logger.warning(f"声音克隆失败，第{attempt}次重试前等待{wait_s}s: {e}")
                    time.sleep(wait_s)
            if last_err:
                raise last_err

            logger.success("✓ Step 2 完成: 声音克隆")

            # Step 3: 生成数字人视频
            logger.info("\n" + "=" * 60)
            logger.info("Step 3/3: 生成数字人视频")
            logger.info("=" * 60)

            digital_human_video_path = str(output_dir / "ad_video.mp4")

            last_err = None
            for attempt in range(1, 3):
                try:
                    self.digital_human.generate_video(
                        face_image_path=cleaned_image_path,
                        audio_path=cloned_audio_path,
                        output_video_path=digital_human_video_path,
                        fps=fps,
                        quality="high",
                        target_width=video_width,
                        target_height=video_height
                    )
                    break
                except Exception as e:
                    last_err = e
                    wait_s = 3 * attempt
                    logger.warning(f"数字人生成失败，第{attempt}次重试前等待{wait_s}s: {e}")
                    time.sleep(wait_s)
            if last_err:
                raise last_err

            logger.success("✓ Step 3 完成: 数字人生成")

            # 完成
            logger.info("\n" + "=" * 60)
            logger.success("🎉 广告视频生成完成！")
            logger.info("=" * 60)
            logger.info(f"清洗图片: {cleaned_image_path}")
            logger.info(f"克隆音频: {cloned_audio_path}")
            logger.info(f"数字人视频: {digital_human_video_path}")

            return AdVideoResult(
                cleaned_image_path=cleaned_image_path,
                cloned_audio_path=cloned_audio_path,
                digital_human_video_path=digital_human_video_path,
                success=True
            )

        except Exception as e:
            logger.error(f"\n❌ 广告视频生成失败: {e}")
            import traceback
            logger.debug(traceback.format_exc())

            return AdVideoResult(
                cleaned_image_path="",
                cloned_audio_path="",
                digital_human_video_path="",
                success=False,
                error_message=str(e)
            )

    def generate_ad_video_simple(
        self,
        keyframe_image_path: str,
        reference_audio_path: str,
        ad_script: str,
        output_dir: str,
        video_width: Optional[int] = None,
        video_height: Optional[int] = None
    ) -> AdVideoResult:
        """
        简化的广告视频生成接口（使用默认参数）

        Args:
            keyframe_image_path: 关键帧图片路径
            reference_audio_path: 参考音频路径
            ad_script: 广告词
            output_dir: 输出目录
            video_width: 原视频宽度（用于匹配分辨率）
            video_height: 原视频高度（用于匹配分辨率）

        Returns:
            生成结果
        """
        return self.generate_ad_video(
            keyframe_image_path=keyframe_image_path,
            reference_audio_path=reference_audio_path,
            ad_script=ad_script,
            output_dir=output_dir,
            clean_image=True,
            emotion="neutral",
            speed=1.0,
            fps=25,
            video_width=video_width,
            video_height=video_height
        )

    @staticmethod
    def check_all_workflows() -> dict[str, bool]:
        """
        检查所有workflow是否存在

        Returns:
            workflow状态字典 {"image_edit": True, "voice_clone": False, ...}
        """
        logger.info("检查所有workflow配置文件...")

        results = {
            "image_edit": ImageCleanerService.check_workflow_exists(),
            "voice_clone": VoiceCloneService.check_workflow_exists(),
            "digital_human": DigitalHumanService.check_workflow_exists()
        }

        all_exist = all(results.values())

        if all_exist:
            logger.success("✓ 所有workflow配置文件存在")
        else:
            missing = [name for name, exists in results.items() if not exists]
            logger.error(f"✗ 缺失workflow: {', '.join(missing)}")

        return results
