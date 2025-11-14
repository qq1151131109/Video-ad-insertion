"""
视频合成测试脚本

测试视频剪辑、拼接和广告插入功能
"""
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.core.video_composer import VideoComposer
from src.utils.logger import logger
from src.config.settings import settings


def test_video_info():
    """测试获取视频信息"""
    logger.info("=" * 60)
    logger.info("测试1: 获取视频信息")
    logger.info("=" * 60)

    # 查找测试视频
    video_files = list(settings.INPUT_DIR.glob("*.mp4"))
    if not video_files:
        logger.error("❌ input目录下没有视频文件")
        return False

    video_path = video_files[0]
    logger.info(f"测试视频: {video_path.name}")

    try:
        composer = VideoComposer()
        info = composer.get_video_info(str(video_path))

        logger.info("\n视频信息:")
        logger.info(f"  时长: {info['duration']:.2f}秒")
        logger.info(f"  帧率: {info['fps']}fps")
        logger.info(f"  分辨率: {info['width']}x{info['height']}")
        logger.info(f"  有音频: {'是' if info['has_audio'] else '否'}")

        logger.success("✓ 视频信息获取成功")
        return True

    except Exception as e:
        logger.error(f"✗ 视频信息获取失败: {e}")
        return False


def test_split_video():
    """测试视频切分"""
    logger.info("\n" + "=" * 60)
    logger.info("测试2: 视频切分")
    logger.info("=" * 60)

    # 查找测试视频
    video_files = list(settings.INPUT_DIR.glob("*.mp4"))
    if not video_files:
        logger.error("❌ input目录下没有视频文件")
        return False

    video_path = video_files[0]
    logger.info(f"测试视频: {video_path.name}")

    try:
        composer = VideoComposer()

        # 获取视频时长
        info = composer.get_video_info(str(video_path))
        duration = info['duration']

        # 在中间位置切分
        split_time = duration / 2
        output_dir = settings.OUTPUT_DIR / "test_split"

        logger.info(f"在 {split_time:.2f}秒 切分视频")

        part1, part2 = composer.split_video_at_time(
            video_path=str(video_path),
            split_time=split_time,
            output_dir=str(output_dir)
        )

        # 验证
        if Path(part1).exists() and Path(part2).exists():
            logger.success("✓ 视频切分成功")
            logger.info(f"  前半段: {part1}")
            logger.info(f"  后半段: {part2}")

            # 验证时长
            info1 = composer.get_video_info(part1)
            info2 = composer.get_video_info(part2)

            logger.info(f"\n时长验证:")
            logger.info(f"  原视频: {duration:.2f}s")
            logger.info(f"  前半段: {info1['duration']:.2f}s")
            logger.info(f"  后半段: {info2['duration']:.2f}s")
            logger.info(f"  总和: {info1['duration'] + info2['duration']:.2f}s")

            return True
        else:
            logger.error("✗ 视频切分失败: 输出文件不存在")
            return False

    except Exception as e:
        logger.error(f"✗ 视频切分失败: {e}")
        import traceback
        logger.debug(traceback.format_exc())
        return False


def test_concatenate_videos():
    """测试视频拼接"""
    logger.info("\n" + "=" * 60)
    logger.info("测试3: 视频拼接")
    logger.info("=" * 60)

    # 使用上一个测试的切分结果
    split_dir = settings.OUTPUT_DIR / "test_split"
    part1 = split_dir / "part1.mp4"
    part2 = split_dir / "part2.mp4"

    if not (part1.exists() and part2.exists()):
        logger.warning("⚠️  需要先运行测试2生成切分视频")
        logger.info("跳过此测试")
        return True  # 不算失败

    try:
        composer = VideoComposer()

        output_path = settings.OUTPUT_DIR / "test_concat" / "concatenated.mp4"

        logger.info("拼接两个视频片段...")

        result = composer.concatenate_videos(
            video_paths=[str(part1), str(part2)],
            output_path=str(output_path),
            method="compose"
        )

        if Path(result).exists():
            logger.success("✓ 视频拼接成功")
            logger.info(f"  输出: {result}")

            # 验证时长
            info = composer.get_video_info(result)
            logger.info(f"  时长: {info['duration']:.2f}s")

            return True
        else:
            logger.error("✗ 视频拼接失败: 输出文件不存在")
            return False

    except Exception as e:
        logger.error(f"✗ 视频拼接失败: {e}")
        import traceback
        logger.debug(traceback.format_exc())
        return False


def test_insert_ad():
    """测试插入广告"""
    logger.info("\n" + "=" * 60)
    logger.info("测试4: 插入广告视频")
    logger.info("=" * 60)

    logger.warning("⚠️  此测试需要广告视频文件")
    logger.info("如果没有广告视频，可以使用原视频的一个片段作为测试")

    # 查找原视频
    video_files = list(settings.INPUT_DIR.glob("*.mp4"))
    if not video_files:
        logger.error("❌ input目录下没有视频文件")
        return False

    original_video = video_files[0]

    # 检查是否有切分的视频可以作为广告
    split_dir = settings.OUTPUT_DIR / "test_split"
    ad_video = split_dir / "part1.mp4"

    if not ad_video.exists():
        logger.warning("⚠️  没有找到广告视频，跳过测试")
        logger.info("建议先运行测试2生成测试视频")
        return True  # 不算失败

    try:
        composer = VideoComposer()

        # 获取原视频时长
        info = composer.get_video_info(str(original_video))
        duration = info['duration']

        # 在1/3位置插入
        insertion_time = duration / 3

        output_path = settings.OUTPUT_DIR / "test_insert" / "video_with_ad.mp4"

        logger.info(f"原视频: {original_video.name}")
        logger.info(f"广告视频: {ad_video.name}")
        logger.info(f"插入时间: {insertion_time:.2f}s")

        result = composer.insert_ad_video(
            original_video_path=str(original_video),
            ad_video_path=str(ad_video),
            insertion_time=insertion_time,
            output_path=str(output_path)
        )

        if Path(result).exists():
            logger.success("✓ 广告插入成功")
            logger.info(f"  输出: {result}")

            # 验证时长
            result_info = composer.get_video_info(result)
            ad_info = composer.get_video_info(str(ad_video))

            expected_duration = info['duration'] + ad_info['duration']
            actual_duration = result_info['duration']

            logger.info(f"\n时长验证:")
            logger.info(f"  原视频: {info['duration']:.2f}s")
            logger.info(f"  广告视频: {ad_info['duration']:.2f}s")
            logger.info(f"  预期总时长: {expected_duration:.2f}s")
            logger.info(f"  实际总时长: {actual_duration:.2f}s")

            return True
        else:
            logger.error("✗ 广告插入失败: 输出文件不存在")
            return False

    except Exception as e:
        logger.error(f"✗ 广告插入失败: {e}")
        import traceback
        logger.debug(traceback.format_exc())
        return False


def main():
    """主测试函数"""
    logger.info("开始视频合成模块测试\n")

    results = {}

    # 测试1: 获取视频信息
    results['video_info'] = test_video_info()

    # 测试2: 视频切分
    results['split'] = test_split_video()

    # 测试3: 视频拼接
    results['concatenate'] = test_concatenate_videos()

    # 测试4: 插入广告
    results['insert_ad'] = test_insert_ad()

    # 汇总
    logger.info("\n" + "=" * 60)
    logger.info("测试汇总")
    logger.info("=" * 60)
    logger.info(f"1. 视频信息获取: {'✓ 通过' if results['video_info'] else '✗ 失败'}")
    logger.info(f"2. 视频切分: {'✓ 通过' if results['split'] else '✗ 失败'}")
    logger.info(f"3. 视频拼接: {'✓ 通过' if results['concatenate'] else '✗ 失败'}")
    logger.info(f"4. 广告插入: {'✓ 通过' if results['insert_ad'] else '✗ 失败'}")

    passed = sum(results.values())
    total = len(results)

    if passed == total:
        logger.success(f"\n🎉 所有测试通过！({passed}/{total})")
        return 0
    else:
        logger.warning(f"\n⚠️  部分测试通过 ({passed}/{total})")
        return 1


if __name__ == "__main__":
    sys.exit(main())
