"""
完整视频处理流水线

整合所有模块，实现从输入视频到输出带广告视频的完整处理流程
"""
from pathlib import Path
from typing import Optional
from dataclasses import dataclass
import time

from src.core.video_processor import VideoProcessor
from src.core.audio_separator import AudioSeparator
from src.core.asr import ASRService
from src.core.face_detector import FaceDetector
from src.services.llm_service import LLMService
from src.config.ads import AdsManager
from src.core.ad_orchestrator import AdVideoOrchestrator
from src.core.video_composer import VideoComposer
from src.utils.file_manager import TempFileManager
from src.utils.logger import logger
from src.config.settings import settings


@dataclass
class ProcessingResult:
    """处理结果"""
    video_id: str
    original_video_path: str
    output_video_path: Optional[str]
    success: bool
    error_message: Optional[str] = None
    processing_time: float = 0.0  # 处理时间（秒）

    # 中间结果
    transcription_text: Optional[str] = None
    video_theme: Optional[str] = None
    insertion_time: Optional[float] = None
    ad_script: Optional[str] = None
    digital_human_video: Optional[str] = None


class VideoPipeline:
    """视频处理流水线"""

    def __init__(self):
        """初始化流水线"""
        logger.info("初始化视频处理流水线...")

        # 初始化所有服务
        self.audio_separator = AudioSeparator(model="htdemucs")
        self.asr_service = ASRService(model_name="medium")  # 使用medium模型平衡质量和速度
        self.face_detector = FaceDetector()
        self.llm_service = LLMService()
        self.ads_manager = AdsManager()
        self.ad_orchestrator = AdVideoOrchestrator()
        self.video_composer = VideoComposer()

        logger.success("✓ 流水线初始化完成")

    def process_video(
        self,
        video_path: str,
        output_dir: Optional[str] = None,
        device: str = "cuda"
    ) -> ProcessingResult:
        """
        处理视频（完整流程）

        Args:
            video_path: 输入视频路径
            output_dir: 输出目录（None则使用默认）
            device: 设备（cuda/cpu）

        Returns:
            处理结果
        """
        start_time = time.time()

        video_path = Path(video_path)
        video_id = video_path.stem

        if not video_path.exists():
            return ProcessingResult(
                video_id=video_id,
                original_video_path=str(video_path),
                output_video_path=None,
                success=False,
                error_message=f"视频文件不存在: {video_path}"
            )

        # 设置输出目录
        if output_dir is None:
            output_dir = settings.OUTPUT_DIR / "processed" / video_id
        else:
            output_dir = Path(output_dir)

        output_dir.mkdir(parents=True, exist_ok=True)

        logger.info("=" * 80)
        logger.info(f"开始处理视频: {video_path.name}")
        logger.info("=" * 80)

        try:
            with TempFileManager(video_id) as file_mgr:
                # ============================================================
                # 阶段1: 视频分析
                # ============================================================
                logger.info("\n" + "=" * 80)
                logger.info("阶段1: 视频分析")
                logger.info("=" * 80)

                # 1.1 提取元数据
                logger.info("\n[1/3] 提取视频元数据...")
                with VideoProcessor(str(video_path)) as processor:
                    metadata = processor.extract_metadata()

                logger.info(f"  时长: {metadata.duration:.1f}秒")
                logger.info(f"  分辨率: {metadata.resolution}")
                logger.info(f"  帧率: {metadata.fps}")

                # 检查视频时长
                if metadata.duration < settings.MIN_VIDEO_DURATION:
                    raise Exception(f"视频太短({metadata.duration:.1f}s)，最小要求{settings.MIN_VIDEO_DURATION}s")

                if metadata.duration > settings.MAX_VIDEO_DURATION:
                    raise Exception(f"视频太长({metadata.duration:.1f}s)，最大限制{settings.MAX_VIDEO_DURATION}s")

                # 1.2 提取音频
                logger.info("\n[2/3] 提取音频...")
                with VideoProcessor(str(video_path)) as processor:
                    audio_path = processor.extract_audio(
                        str(file_mgr.original_audio_path)
                    )

                logger.success(f"  ✓ 音频已提取: {Path(audio_path).name}")

                # 1.3 人声分离
                logger.info("\n[3/3] 分离人声...")
                vocals_path = self.audio_separator.separate_simple(
                    audio_path=audio_path,
                    output_path=str(file_mgr.separated_vocals_path),
                    device=device
                )

                logger.success(f"  ✓ 人声已分离: {Path(vocals_path).name}")

                # ============================================================
                # 阶段2: 内容理解
                # ============================================================
                logger.info("\n" + "=" * 80)
                logger.info("阶段2: 内容理解")
                logger.info("=" * 80)

                # 2.1 语音识别
                logger.info("\n[1/2] 语音识别...")
                transcription = self.asr_service.transcribe(
                    audio_path=audio_path,
                    language="zh",
                    word_timestamps=True
                )

                logger.success(f"  ✓ 识别完成: {len(transcription.segments)}个片段")
                logger.info(f"  文本预览: {transcription.full_text[:100]}...")

                # 保存转录结果
                transcription_path = file_mgr.get_transcription_path()
                file_mgr.save_text("transcriptions", "transcription.txt", transcription.full_text)

                # 保存SRT字幕
                srt_content = transcription.to_srt()
                file_mgr.save_text("transcriptions", "subtitles.srt", srt_content)

                # 2.2 LLM内容分析
                logger.info("\n[2/2] LLM内容分析...")

                # 转换为LLM所需格式
                segments = [
                    {"text": seg.text, "start": seg.start, "end": seg.end}
                    for seg in transcription.segments
                ]

                analysis = self.llm_service.analyze_video_content(
                    transcription_segments=segments,
                    video_duration=metadata.duration,
                    avoid_start=settings.INSERTION_POINT_AVOID_START,
                    avoid_end=settings.INSERTION_POINT_AVOID_END,
                    num_candidates=3
                )

                logger.success("  ✓ 内容分析完成")
                logger.info(f"  主题: {analysis.theme}")
                logger.info(f"  类别: {analysis.category}")
                logger.info(f"  找到{len(analysis.insertion_points)}个插入点候选")

                # ============================================================
                # 阶段3: 广告准备
                # ============================================================
                logger.info("\n" + "=" * 80)
                logger.info("阶段3: 广告准备")
                logger.info("=" * 80)

                # 3.1 选择插入点（使用第一个候选）
                if not analysis.insertion_points:
                    raise Exception("LLM未找到合适的插入点")

                insertion_point = analysis.insertion_points[0]
                logger.info(f"\n[1/5] 选择插入点: {insertion_point.time:.1f}秒 (优先级{insertion_point.priority})")
                logger.info(f"  理由: {insertion_point.reason}")

                # 3.2 提取关键帧
                logger.info("\n[2/5] 提取关键帧...")
                with VideoProcessor(str(video_path)) as processor:
                    keyframe, actual_time = processor.extract_best_frame_around_time(
                        target_time=insertion_point.time,
                        window_size=2.0,
                        num_candidates=10
                    )

                # 保存关键帧
                import cv2
                keyframe_path = file_mgr.get_keyframe_path("insertion_keyframe.jpg")
                cv2.imwrite(str(keyframe_path), keyframe)

                logger.success(f"  ✓ 关键帧已提取: {actual_time:.2f}秒")

                # 3.3 人脸检测和质量评估
                logger.info("\n[3/5] 人脸检测...")
                faces = self.face_detector.detect_faces(keyframe)

                if not faces:
                    logger.warning("  ⚠️  未检测到人脸，继续使用原关键帧")
                else:
                    best_face = self.face_detector.get_best_face(keyframe)
                    logger.success(f"  ✓ 检测到{len(faces)}个人脸")
                    logger.info(f"  最佳人脸置信度: {best_face.confidence:.3f}")

                # 3.4 选择广告
                logger.info("\n[4/5] 选择广告...")
                ad = self.ads_manager.select_ad_for_video(analysis.theme)

                if not ad:
                    raise Exception("没有可用的广告")

                logger.success(f"  ✓ 选中广告: {ad.name}")
                logger.info(f"  产品: {ad.product}")
                logger.info(f"  卖点: {ad.get_selling_points_text()}")

                # 3.5 生成广告词
                logger.info("\n[5/5] 生成广告词...")
                ad_script = self.llm_service.generate_ad_script(
                    video_theme=analysis.theme,
                    video_category=analysis.category,
                    video_tone=analysis.tone,
                    context_before=insertion_point.context_before,
                    context_after=insertion_point.context_after,
                    ad_config=ad,
                    transition_hint=insertion_point.transition_hint
                )

                logger.success("  ✓ 广告词生成完成")
                logger.info(f"  内容: {ad_script}")

                # ============================================================
                # 阶段4: 数字人视频生成
                # ============================================================
                logger.info("\n" + "=" * 80)
                logger.info("阶段4: 数字人视频生成")
                logger.info("=" * 80)

                ad_output_dir = file_mgr.base_dir / "ad_video"

                logger.info("\n执行三步workflow: 图片清洗 → 声音克隆 → 数字人生成")

                ad_result = self.ad_orchestrator.generate_ad_video_simple(
                    keyframe_image_path=str(keyframe_path),
                    reference_audio_path=vocals_path,
                    ad_script=ad_script,
                    output_dir=str(ad_output_dir)
                )

                if not ad_result.success:
                    raise Exception(f"数字人视频生成失败: {ad_result.error_message}")

                logger.success("✓ 数字人视频生成完成")

                # ============================================================
                # 阶段5: 视频合成
                # ============================================================
                logger.info("\n" + "=" * 80)
                logger.info("阶段5: 视频合成")
                logger.info("=" * 80)

                logger.info("\n将数字人广告插入原视频...")

                final_output_path = output_dir / f"{video_id}_with_ad.mp4"

                # 插入广告视频
                self.video_composer.insert_ad_video(
                    original_video_path=str(video_path),
                    ad_video_path=ad_result.digital_human_video_path,
                    insertion_time=insertion_point.time,
                    output_path=str(final_output_path)
                )

                logger.success("✓ 视频合成完成")

                # ============================================================
                # 完成
                # ============================================================
                elapsed_time = time.time() - start_time

                logger.info("\n" + "=" * 80)
                logger.success("🎉 视频处理完成！")
                logger.info("=" * 80)
                logger.info(f"处理时间: {elapsed_time:.1f}秒 ({elapsed_time/60:.1f}分钟)")
                logger.info(f"输出目录: {output_dir}")

                return ProcessingResult(
                    video_id=video_id,
                    original_video_path=str(video_path),
                    output_video_path=str(final_output_path),
                    success=True,
                    processing_time=elapsed_time,
                    transcription_text=transcription.full_text,
                    video_theme=analysis.theme,
                    insertion_time=insertion_point.time,
                    ad_script=ad_script,
                    digital_human_video=ad_result.digital_human_video_path
                )

        except Exception as e:
            elapsed_time = time.time() - start_time

            logger.error(f"\n❌ 视频处理失败: {e}")
            import traceback
            logger.debug(traceback.format_exc())

            return ProcessingResult(
                video_id=video_id,
                original_video_path=str(video_path),
                output_video_path=None,
                success=False,
                error_message=str(e),
                processing_time=elapsed_time
            )

    def batch_process(
        self,
        video_dir: str,
        output_dir: Optional[str] = None,
        device: str = "cuda"
    ) -> list[ProcessingResult]:
        """
        批量处理视频

        Args:
            video_dir: 视频目录
            output_dir: 输出目录
            device: 设备

        Returns:
            处理结果列表
        """
        video_dir = Path(video_dir)
        video_files = list(video_dir.glob("*.mp4"))

        logger.info(f"批量处理: 找到{len(video_files)}个视频文件")

        results = []

        for i, video_file in enumerate(video_files, 1):
            logger.info(f"\n{'=' * 80}")
            logger.info(f"处理进度: {i}/{len(video_files)}")
            logger.info(f"{'=' * 80}")

            result = self.process_video(
                video_path=str(video_file),
                output_dir=output_dir,
                device=device
            )

            results.append(result)

        # 汇总
        success_count = sum(1 for r in results if r.success)
        total_time = sum(r.processing_time for r in results)

        logger.info("\n" + "=" * 80)
        logger.info("批量处理汇总")
        logger.info("=" * 80)
        logger.info(f"总计: {len(results)}个视频")
        logger.info(f"成功: {success_count}个")
        logger.info(f"失败: {len(results) - success_count}个")
        logger.info(f"总耗时: {total_time/60:.1f}分钟")
        logger.info(f"平均: {total_time/len(results)/60:.1f}分钟/视频")

        return results
