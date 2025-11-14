"""
ComfyUI工作流测试脚本

测试图片清洗、声音克隆、数字人生成三个workflow服务
"""
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.core.ad_orchestrator import AdVideoOrchestrator
from src.services.image_cleaner import ImageCleanerService
from src.services.voice_clone import VoiceCloneService
from src.services.digital_human import DigitalHumanService
from src.core.video_processor import VideoProcessor
from src.core.audio_separator import AudioSeparator
from src.utils.file_manager import TempFileManager
from src.utils.logger import logger
from src.config.settings import settings


def test_workflow_files():
    """测试workflow配置文件是否存在"""
    logger.info("=" * 60)
    logger.info("测试1: 检查workflow配置文件")
    logger.info("=" * 60)

    results = AdVideoOrchestrator.check_all_workflows()

    all_ok = all(results.values())

    if all_ok:
        logger.success("✓ 所有workflow配置文件存在")
        return True
    else:
        logger.error("✗ 部分workflow配置文件缺失")
        logger.info("\n请确保以下文件存在:")
        logger.info("  1. docs/workflow/qwen_image_edit.json")
        logger.info("  2. docs/workflow/index TTS2情绪控制_api_1013.json")
        logger.info("  3. docs/workflow/InfiniteTalk数字人视频生视频_api.json")
        return False


def test_image_cleaning():
    """测试图片清洗服务"""
    logger.info("\n" + "=" * 60)
    logger.info("测试2: 图片清洗服务")
    logger.info("=" * 60)

    # 查找测试视频
    video_files = list(settings.INPUT_DIR.glob("*.mp4"))
    if not video_files:
        logger.error("❌ input目录下没有视频文件")
        return False

    video_path = video_files[0]
    video_id = video_path.stem

    logger.info(f"测试视频: {video_path.name}")

    try:
        with TempFileManager(video_id) as file_mgr:
            # 1. 提取关键帧
            logger.info("\n准备测试数据: 提取关键帧")
            with VideoProcessor(str(video_path)) as processor:
                metadata = processor.extract_metadata()
                mid_time = metadata.duration / 2

                keyframe, _ = processor.extract_best_frame_around_time(
                    target_time=mid_time,
                    window_size=2.0
                )

            # 保存关键帧
            keyframe_path = file_mgr.get_keyframe_path("test_keyframe.jpg")
            import cv2
            cv2.imwrite(str(keyframe_path), keyframe)

            logger.info(f"关键帧: {keyframe_path}")

            # 2. 测试图片清洗
            logger.info("\n开始测试图片清洗...")

            output_path = file_mgr.get_keyframe_path("cleaned_keyframe.jpg")

            cleaner = ImageCleanerService()
            result = cleaner.clean_image_simple(
                input_image_path=str(keyframe_path),
                output_image_path=str(output_path),
                remove_text=True,
                remove_watermark=True,
                timeout=300
            )

            if Path(result).exists():
                logger.success(f"✓ 图片清洗成功: {Path(result).name}")
                logger.info(f"输出路径: {result}")
                return True
            else:
                logger.error("✗ 图片清洗失败: 输出文件不存在")
                return False

    except Exception as e:
        logger.error(f"✗ 图片清洗测试失败: {e}")
        import traceback
        logger.debug(traceback.format_exc())
        return False


def test_voice_cloning():
    """测试声音克隆服务"""
    logger.info("\n" + "=" * 60)
    logger.info("测试3: 声音克隆服务")
    logger.info("=" * 60)

    # 查找测试视频
    video_files = list(settings.INPUT_DIR.glob("*.mp4"))
    if not video_files:
        logger.error("❌ input目录下没有视频文件")
        return False

    video_path = video_files[0]
    video_id = video_path.stem

    logger.info(f"测试视频: {video_path.name}")

    try:
        with TempFileManager(video_id) as file_mgr:
            # 1. 提取并分离人声
            logger.info("\n准备测试数据: 提取人声样本")

            with VideoProcessor(str(video_path)) as processor:
                audio_path = processor.extract_audio(
                    str(file_mgr.original_audio_path)
                )

            # 人声分离
            logger.info("分离人声...")
            separator = AudioSeparator()
            vocals_path = separator.separate_simple(
                audio_path=audio_path,
                output_path=str(file_mgr.separated_vocals_path),
                device="cpu"  # 测试时使用CPU
            )

            logger.info(f"人声样本: {vocals_path}")

            # 2. 测试声音克隆
            logger.info("\n开始测试声音克隆...")

            test_text = "这得益于NVIDIA强大的算力支持，让AI训练事半功倍"
            output_path = file_mgr.get_path("ad_materials", "cloned_voice.wav")

            voice_clone = VoiceCloneService()
            result = voice_clone.clone_voice_simple(
                reference_audio_path=vocals_path,
                text=test_text,
                output_audio_path=str(output_path),
                timeout=300
            )

            if Path(result).exists():
                logger.success(f"✓ 声音克隆成功: {Path(result).name}")
                logger.info(f"输出路径: {result}")
                logger.info(f"测试文本: {test_text}")
                return True
            else:
                logger.error("✗ 声音克隆失败: 输出文件不存在")
                return False

    except Exception as e:
        logger.error(f"✗ 声音克隆测试失败: {e}")
        import traceback
        logger.debug(traceback.format_exc())
        return False


def test_digital_human():
    """测试数字人生成服务"""
    logger.info("\n" + "=" * 60)
    logger.info("测试4: 数字人生成服务")
    logger.info("=" * 60)

    logger.warning("⚠️  注意: 此测试需要前两个测试成功生成的文件")
    logger.info("如果想单独测试，请确保有可用的人脸图片和音频文件")

    # 这里简化测试，只检查服务是否可以初始化
    try:
        digital_human = DigitalHumanService()
        logger.success("✓ 数字人生成服务初始化成功")

        logger.info("\n完整的数字人生成测试需要:")
        logger.info("  1. 清洗后的人脸图片")
        logger.info("  2. 克隆的声音文件")
        logger.info("  3. ComfyUI服务正常运行")
        logger.info("\n建议使用测试5的完整流程测试")

        return True

    except Exception as e:
        logger.error(f"✗ 数字人生成服务初始化失败: {e}")
        return False


def test_full_pipeline():
    """测试完整的广告生成流程"""
    logger.info("\n" + "=" * 60)
    logger.info("测试5: 完整广告生成流程")
    logger.info("=" * 60)

    logger.warning("⚠️  这是端到端的完整测试，预计需要5-10分钟")
    logger.info("将依次执行: 提取关键帧 → 分离人声 → 清洗图片 → 克隆声音 → 生成数字人视频")

    # 查找测试视频
    video_files = list(settings.INPUT_DIR.glob("*.mp4"))
    if not video_files:
        logger.error("❌ input目录下没有视频文件")
        return False

    video_path = video_files[0]
    video_id = video_path.stem

    logger.info(f"\n测试视频: {video_path.name}")

    try:
        with TempFileManager(video_id) as file_mgr:
            # 准备数据
            logger.info("\n" + "-" * 60)
            logger.info("准备阶段")
            logger.info("-" * 60)

            # 1. 提取关键帧
            logger.info("\n1. 提取关键帧...")
            with VideoProcessor(str(video_path)) as processor:
                metadata = processor.extract_metadata()
                mid_time = metadata.duration / 2

                keyframe, _ = processor.extract_best_frame_around_time(
                    target_time=mid_time,
                    window_size=2.0
                )

                # 保存关键帧
                keyframe_path = file_mgr.get_keyframe_path("ad_keyframe.jpg")
                import cv2
                cv2.imwrite(str(keyframe_path), keyframe)

                # 提取音频
                logger.info("2. 提取音频...")
                audio_path = processor.extract_audio(
                    str(file_mgr.original_audio_path)
                )

            # 2. 分离人声
            logger.info("3. 分离人声...")
            separator = AudioSeparator()
            vocals_path = separator.separate_simple(
                audio_path=audio_path,
                output_path=str(file_mgr.separated_vocals_path),
                device="cpu"
            )

            logger.success("✓ 准备完成")

            # 完整流程测试
            logger.info("\n" + "-" * 60)
            logger.info("广告生成流程")
            logger.info("-" * 60)

            ad_script = "NVIDIA GPU算力强劲，让AI训练速度提升10倍"
            output_dir = file_mgr.get_path("ad_materials", "final_output")

            orchestrator = AdVideoOrchestrator()

            result = orchestrator.generate_ad_video_simple(
                keyframe_image_path=str(keyframe_path),
                reference_audio_path=vocals_path,
                ad_script=ad_script,
                output_dir=str(output_dir)
            )

            if result.success:
                logger.success("\n✓ 完整流程测试成功！")
                logger.info("\n生成结果:")
                logger.info(f"  清洗图片: {result.cleaned_image_path}")
                logger.info(f"  克隆音频: {result.cloned_audio_path}")
                logger.info(f"  数字人视频: {result.digital_human_video_path}")
                return True
            else:
                logger.error(f"\n✗ 完整流程测试失败: {result.error_message}")
                return False

    except Exception as e:
        logger.error(f"✗ 完整流程测试失败: {e}")
        import traceback
        logger.debug(traceback.format_exc())
        return False


def main():
    """主测试函数"""
    logger.info("开始ComfyUI工作流服务测试\n")

    results = {}

    # 测试1: 检查workflow文件
    results['workflow_files'] = test_workflow_files()

    if not results['workflow_files']:
        logger.error("\n❌ workflow配置文件缺失，无法继续测试")
        logger.info("请检查docs/workflow/目录下的JSON文件")
        return 1

    # 提示用户选择测试模式
    logger.info("\n" + "=" * 60)
    logger.info("测试模式选择")
    logger.info("=" * 60)
    logger.info("由于ComfyUI workflow测试需要实际调用API，可能耗时较长")
    logger.info("\n推荐测试方式:")
    logger.info("  • 快速测试: 只测试服务初始化（已完成）")
    logger.info("  • 完整测试: 需要手动执行，并确保ComfyUI服务运行正常")

    logger.info("\n如需完整测试，请手动取消注释以下测试:")
    logger.info("  - test_image_cleaning()")
    logger.info("  - test_voice_cloning()")
    logger.info("  - test_digital_human()")
    logger.info("  - test_full_pipeline()")

    # 快速测试：只测试数字人服务初始化
    results['digital_human_init'] = test_digital_human()

    # 汇总
    logger.info("\n" + "=" * 60)
    logger.info("测试汇总")
    logger.info("=" * 60)
    logger.info(f"1. Workflow文件: {'✓ 通过' if results['workflow_files'] else '✗ 失败'}")
    logger.info(f"2. 数字人服务初始化: {'✓ 通过' if results['digital_human_init'] else '✗ 失败'}")

    logger.info("\n💡 提示:")
    logger.info("  完整的workflow测试需要ComfyUI服务运行")
    logger.info("  请确保 http://103.231.86.148:9000 可访问")

    passed = sum(results.values())
    total = len(results)

    if passed == total:
        logger.success(f"\n🎉 快速测试全部通过！({passed}/{total})")
        return 0
    else:
        logger.warning(f"\n⚠️  部分测试失败 ({passed}/{total})")
        return 1


if __name__ == "__main__":
    sys.exit(main())
