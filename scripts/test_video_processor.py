"""
视频处理测试脚本

测试视频元数据提取、音频提取、关键帧提取等功能
"""
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.core.video_processor import VideoProcessor
from src.utils.file_manager import TempFileManager
from src.utils.logger import logger
from src.config.settings import settings


def test_video_metadata():
    """测试视频元数据提取"""
    logger.info("=" * 60)
    logger.info("测试1: 视频元数据提取")
    logger.info("=" * 60)

    # 使用input目录下的第一个视频
    video_files = list(settings.INPUT_DIR.glob("*.mp4"))

    if not video_files:
        logger.error("❌ input目录下没有视频文件")
        return False

    video_path = video_files[0]
    logger.info(f"测试视频: {video_path.name}")

    try:
        with VideoProcessor(str(video_path)) as processor:
            metadata = processor.extract_metadata()

            logger.info(f"\n视频信息:")
            logger.info(f"  分辨率: {metadata.resolution}")
            logger.info(f"  帧率: {metadata.fps:.1f} fps")
            logger.info(f"  时长: {metadata.duration:.1f}秒")
            logger.info(f"  编码: {metadata.codec}")
            logger.info(f"  音频: {'有' if metadata.has_audio else '无'}")
            logger.info(f"  文件大小: {metadata.filesize / 1024 / 1024:.1f} MB")
            logger.info(f"  屏幕方向: {'竖屏' if metadata.is_vertical else '横屏'}")

            logger.success("✓ 元数据提取成功")
            return True

    except Exception as e:
        logger.error(f"✗ 元数据提取失败: {e}")
        return False


def test_audio_extraction():
    """测试音频提取"""
    logger.info("\n" + "=" * 60)
    logger.info("测试2: 音频提取")
    logger.info("=" * 60)

    video_files = list(settings.INPUT_DIR.glob("*.mp4"))
    if not video_files:
        logger.error("❌ input目录下没有视频文件")
        return False

    video_path = video_files[0]
    video_id = video_path.stem

    try:
        with VideoProcessor(str(video_path)) as processor:
            with TempFileManager(video_id) as file_mgr:
                # 提取音频
                audio_path = processor.extract_audio(
                    str(file_mgr.original_audio_path)
                )

                # 检查文件
                audio_file = Path(audio_path)
                if audio_file.exists():
                    size_mb = audio_file.stat().st_size / 1024 / 1024
                    logger.info(f"音频文件: {audio_file.name} ({size_mb:.1f} MB)")
                    logger.success("✓ 音频提取成功")
                    return True
                else:
                    logger.error("✗ 音频文件未生成")
                    return False

    except Exception as e:
        logger.error(f"✗ 音频提取失败: {e}")
        return False


def test_keyframe_extraction():
    """测试关键帧提取"""
    logger.info("\n" + "=" * 60)
    logger.info("测试3: 关键帧提取")
    logger.info("=" * 60)

    video_files = list(settings.INPUT_DIR.glob("*.mp4"))
    if not video_files:
        logger.error("❌ input目录下没有视频文件")
        return False

    video_path = video_files[0]
    video_id = video_path.stem

    try:
        with VideoProcessor(str(video_path)) as processor:
            # 先获取元数据
            metadata = processor.extract_metadata()

            with TempFileManager(video_id) as file_mgr:
                # 提取视频中间的一帧
                mid_time = metadata.duration / 2
                frame_path = file_mgr.get_keyframe_path("test_frame.jpg")

                logger.info(f"提取时间点: {mid_time:.1f}s")
                processor.extract_frame_at_time(mid_time, str(frame_path))

                # 检查文件
                if frame_path.exists():
                    size_kb = frame_path.stat().st_size / 1024
                    logger.info(f"关键帧: {frame_path.name} ({size_kb:.1f} KB)")
                    logger.success("✓ 关键帧提取成功")

                    # 测试最佳帧提取
                    logger.info("\n测试最佳帧提取...")
                    best_frame, best_time = processor.extract_best_frame_around_time(
                        mid_time,
                        window_size=2.0,
                        num_candidates=5
                    )

                    logger.info(f"最佳帧时间: {best_time:.2f}s")
                    logger.success("✓ 最佳帧提取成功")

                    return True
                else:
                    logger.error("✗ 关键帧文件未生成")
                    return False

    except Exception as e:
        logger.error(f"✗ 关键帧提取失败: {e}")
        return False


def test_file_manager():
    """测试文件管理器"""
    logger.info("\n" + "=" * 60)
    logger.info("测试4: 文件管理器")
    logger.info("=" * 60)

    video_id = "test_video"

    try:
        with TempFileManager(video_id) as file_mgr:
            logger.info(f"临时目录: {file_mgr.base_dir}")

            # 测试各种路径获取
            audio_path = file_mgr.get_audio_path("test.wav")
            keyframe_path = file_mgr.get_keyframe_path("test.jpg")

            logger.info(f"音频路径: {audio_path}")
            logger.info(f"关键帧路径: {keyframe_path}")

            # 测试文本保存
            file_mgr.save_text('transcriptions', 'test.txt', '测试文本')

            # 测试文本加载
            content = file_mgr.load_text('transcriptions', 'test.txt')
            if content == '测试文本':
                logger.success("✓ 文本读写成功")
            else:
                logger.error("✗ 文本读写失败")
                return False

            # 测试大小计算
            size_mb = file_mgr.get_size_mb()
            logger.info(f"临时文件大小: {size_mb:.3f} MB")

            logger.success("✓ 文件管理器测试成功")
            return True

    except Exception as e:
        logger.error(f"✗ 文件管理器测试失败: {e}")
        return False


def main():
    """主测试函数"""
    logger.info("开始视频处理模块测试\n")

    results = {
        "视频元数据提取": test_video_metadata(),
        "音频提取": test_audio_extraction(),
        "关键帧提取": test_keyframe_extraction(),
        "文件管理器": test_file_manager(),
    }

    # 汇总
    logger.info("\n" + "=" * 60)
    logger.info("测试汇总")
    logger.info("=" * 60)

    for name, result in results.items():
        status = "✓ 通过" if result else "✗ 失败"
        logger.info(f"{name}: {status}")

    passed = sum(results.values())
    total = len(results)

    if passed == total:
        logger.success(f"\n🎉 所有测试通过！({passed}/{total})")
        return 0
    else:
        logger.error(f"\n❌ 部分测试失败 ({passed}/{total})")
        return 1


if __name__ == "__main__":
    sys.exit(main())
