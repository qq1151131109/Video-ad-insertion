"""
主程序入口

提供命令行接口，执行完整的视频广告插入流程
"""
import sys
import argparse
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.core.pipeline import VideoPipeline
from src.utils.logger import logger
from src.config.settings import settings


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="智能视频广告插入系统",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 处理单个视频
  python main.py input/video.mp4

  # 处理单个视频，指定输出目录
  python main.py input/video.mp4 -o output/my_video

  # 批量处理input目录下的所有视频
  python main.py input/ --batch

  # 使用CPU（不使用GPU）
  python main.py input/video.mp4 --device cpu
        """
    )

    parser.add_argument(
        "input",
        type=str,
        help="输入视频文件路径或目录（批量模式）"
    )

    parser.add_argument(
        "-o", "--output",
        type=str,
        default=None,
        help="输出目录（默认: output/processed/视频ID）"
    )

    parser.add_argument(
        "--batch",
        action="store_true",
        help="批量模式：处理指定目录下的所有视频"
    )

    parser.add_argument(
        "--device",
        type=str,
        choices=["cuda", "cpu"],
        default="cuda",
        help="处理设备（默认: cuda）"
    )

    args = parser.parse_args()

    # 显示欢迎信息
    logger.info("=" * 80)
    logger.info("智能视频广告插入系统")
    logger.info("=" * 80)
    logger.info("使用AI技术自动在视频中插入自然、流畅的数字人软广告\n")

    # 初始化流水线
    logger.info("初始化处理流水线...")
    pipeline = VideoPipeline()

    # 执行处理
    input_path = Path(args.input)

    if not input_path.exists():
        logger.error(f"❌ 输入路径不存在: {input_path}")
        return 1

    try:
        if args.batch:
            # 批量模式
            if not input_path.is_dir():
                logger.error("❌ 批量模式需要指定目录")
                return 1

            logger.info(f"批量处理模式: {input_path}")

            results = pipeline.batch_process(
                video_dir=str(input_path),
                output_dir=args.output,
                device=args.device
            )

            # 显示结果
            success_count = sum(1 for r in results if r.success)

            if success_count == len(results):
                logger.success(f"\n✅ 全部成功！处理了{len(results)}个视频")
                return 0
            elif success_count > 0:
                logger.warning(f"\n⚠️  部分成功：{success_count}/{len(results)}个视频")
                return 1
            else:
                logger.error(f"\n❌ 全部失败：{len(results)}个视频")
                return 1

        else:
            # 单文件模式
            if not input_path.is_file():
                logger.error("❌ 请指定视频文件")
                return 1

            logger.info(f"单文件处理模式: {input_path.name}")

            result = pipeline.process_video(
                video_path=str(input_path),
                output_dir=args.output,
                device=args.device
            )

            if result.success:
                logger.success("\n✅ 处理成功！")
                logger.info(f"\n处理结果:")
                logger.info(f"  视频ID: {result.video_id}")
                logger.info(f"  视频主题: {result.video_theme}")
                logger.info(f"  插入时间: {result.insertion_time:.1f}秒")
                logger.info(f"  广告词: {result.ad_script}")
                logger.info(f"  输出路径: {result.output_video_path}")
                logger.info(f"  处理时间: {result.processing_time/60:.1f}分钟")
                return 0
            else:
                logger.error(f"\n❌ 处理失败: {result.error_message}")
                return 1

    except KeyboardInterrupt:
        logger.warning("\n\n⚠️  用户中断操作")
        return 130

    except Exception as e:
        logger.error(f"\n❌ 发生错误: {e}")
        import traceback
        logger.debug(traceback.format_exc())
        return 1


if __name__ == "__main__":
    sys.exit(main())
