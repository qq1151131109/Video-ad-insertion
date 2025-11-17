"""
测试视频超分辨率功能

测试VideoUpscaler服务的各项功能
"""
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.services.video_upscaler import VideoUpscaler
from src.utils.logger import logger


def test_get_video_resolution():
    """测试获取视频分辨率"""
    logger.info("\n" + "=" * 80)
    logger.info("测试1: 获取视频分辨率")
    logger.info("=" * 80)

    # 使用input目录中的测试视频
    test_videos = list(Path("input").glob("*.mp4"))

    if not test_videos:
        logger.warning("⚠️ input目录中没有找到测试视频，跳过此测试")
        return False

    upscaler = VideoUpscaler()

    for video_path in test_videos[:3]:  # 只测试前3个
        try:
            width, height = upscaler.get_video_resolution(str(video_path))
            logger.success(f"✓ {video_path.name}: {width}x{height}")
        except Exception as e:
            logger.error(f"❌ {video_path.name}: {e}")
            return False

    return True


def test_upscale_video():
    """测试视频超分"""
    logger.info("\n" + "=" * 80)
    logger.info("测试2: 视频超分")
    logger.info("=" * 80)

    # 查找测试视频
    test_videos = list(Path("input").glob("*.mp4"))

    if not test_videos:
        logger.warning("⚠️ input目录中没有找到测试视频")
        logger.info("请在input目录中放置一个测试视频文件")
        return False

    test_video = test_videos[0]
    logger.info(f"使用测试视频: {test_video.name}")

    # 创建输出目录
    output_dir = Path("output/test_upscale")
    output_dir.mkdir(parents=True, exist_ok=True)

    upscaler = VideoUpscaler()

    try:
        # 获取原始分辨率
        original_width, original_height = upscaler.get_video_resolution(str(test_video))
        logger.info(f"原始分辨率: {original_width}x{original_height}")

        # 测试1: 放大到1.5倍
        logger.info("\n测试放大到1.5倍...")
        target_width = int(original_width * 1.5)
        target_height = int(original_height * 1.5)

        output_path = output_dir / f"{test_video.stem}_upscaled_1.5x.mp4"

        upscaled_video = upscaler.upscale_video(
            input_video_path=str(test_video),
            output_video_path=str(output_path),
            target_width=target_width,
            target_height=target_height,
            algorithm="lanczos",
            crf=18,
            preset="medium"
        )

        logger.success(f"✓ 视频已保存: {output_path}")

        # 验证输出
        result_width, result_height = upscaler.get_video_resolution(upscaled_video)
        logger.info(f"输出分辨率: {result_width}x{result_height}")

        if result_width == target_width and result_height == target_height:
            logger.success("✓ 分辨率匹配")
        else:
            logger.warning(f"⚠️ 分辨率不完全匹配")

        # 测试2: 缩小到0.5倍（模拟低分辨率数字人视频）
        logger.info("\n测试缩小到0.5倍（模拟数字人视频）...")
        target_width = int(original_width * 0.5)
        target_height = int(original_height * 0.5)

        downscaled_path = output_dir / f"{test_video.stem}_downscaled_0.5x.mp4"

        downscaled_video = upscaler.upscale_video(
            input_video_path=str(test_video),
            output_video_path=str(downscaled_path),
            target_width=target_width,
            target_height=target_height,
            algorithm="lanczos",
            crf=18,
            preset="fast"
        )

        logger.success(f"✓ 低分辨率视频已保存: {downscaled_path}")

        # 测试3: 将低分辨率视频超分回原始分辨率
        logger.info("\n测试超分回原始分辨率...")
        restored_path = output_dir / f"{test_video.stem}_restored.mp4"

        restored_video = upscaler.upscale_to_match(
            input_video_path=downscaled_video,
            reference_video_path=str(test_video),
            output_video_path=str(restored_path),
            algorithm="lanczos",
            crf=18,
            preset="medium"
        )

        logger.success(f"✓ 超分视频已保存: {restored_path}")

        # 验证
        result_width, result_height = upscaler.get_video_resolution(restored_video)
        if result_width == original_width and result_height == original_height:
            logger.success("✓ 超分后分辨率与原视频匹配")
        else:
            logger.warning(f"⚠️ 超分后分辨率不匹配: {result_width}x{result_height} vs {original_width}x{original_height}")

        logger.success("\n✓ 所有超分测试通过！")
        logger.info(f"\n测试输出目录: {output_dir}")

        return True

    except Exception as e:
        logger.error(f"❌ 测试失败: {e}")
        import traceback
        logger.debug(traceback.format_exc())
        return False


def test_different_algorithms():
    """测试不同的缩放算法"""
    logger.info("\n" + "=" * 80)
    logger.info("测试3: 比较不同缩放算法")
    logger.info("=" * 80)

    # 查找测试视频
    test_videos = list(Path("input").glob("*.mp4"))

    if not test_videos:
        logger.warning("⚠️ 跳过算法比较测试")
        return True

    test_video = test_videos[0]
    logger.info(f"使用测试视频: {test_video.name}")

    output_dir = Path("output/test_upscale/algorithms")
    output_dir.mkdir(parents=True, exist_ok=True)

    upscaler = VideoUpscaler()

    # 获取原始分辨率
    original_width, original_height = upscaler.get_video_resolution(str(test_video))

    # 目标分辨率：放大1.5倍
    target_width = int(original_width * 1.5)
    target_height = int(original_height * 1.5)

    algorithms = ["lanczos", "bicubic", "bilinear", "spline"]

    for algo in algorithms:
        try:
            logger.info(f"\n测试算法: {algo}")
            output_path = output_dir / f"{test_video.stem}_{algo}.mp4"

            upscaler.upscale_video(
                input_video_path=str(test_video),
                output_video_path=str(output_path),
                target_width=target_width,
                target_height=target_height,
                algorithm=algo,
                crf=18,
                preset="fast"
            )

            logger.success(f"✓ {algo} 完成")

        except Exception as e:
            logger.error(f"❌ {algo} 失败: {e}")

    logger.info(f"\n算法比较输出目录: {output_dir}")
    logger.info("可以对比不同算法的视觉质量")

    return True


def main():
    """主测试函数"""
    logger.info("=" * 80)
    logger.info("视频超分辨率服务测试")
    logger.info("=" * 80)

    # 检查ffmpeg
    import subprocess
    try:
        result = subprocess.run(
            ["ffmpeg", "-version"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True
        )
        logger.success("✓ ffmpeg已安装")
    except (subprocess.CalledProcessError, FileNotFoundError):
        logger.error("❌ ffmpeg未安装或不在PATH中")
        logger.info("请先安装ffmpeg: https://ffmpeg.org/download.html")
        return

    # 运行测试
    tests = [
        ("获取视频分辨率", test_get_video_resolution),
        ("视频超分", test_upscale_video),
        ("不同算法比较", test_different_algorithms),
    ]

    results = []

    for test_name, test_func in tests:
        try:
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            logger.error(f"❌ 测试异常: {e}")
            results.append((test_name, False))
            import traceback
            logger.debug(traceback.format_exc())

    # 汇总结果
    logger.info("\n" + "=" * 80)
    logger.info("测试结果汇总")
    logger.info("=" * 80)

    for test_name, success in results:
        status = "✓ 通过" if success else "❌ 失败"
        logger.info(f"{test_name}: {status}")

    success_count = sum(1 for _, success in results if success)
    logger.info(f"\n总计: {success_count}/{len(results)} 个测试通过")

    if success_count == len(results):
        logger.success("\n🎉 所有测试通过！")
    else:
        logger.warning("\n⚠️ 部分测试失败")


if __name__ == "__main__":
    main()
