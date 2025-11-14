"""
音频分离测试脚本

测试Demucs人声分离功能
"""
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.core.audio_separator import AudioSeparator
from src.core.video_processor import VideoProcessor
from src.utils.file_manager import TempFileManager
from src.utils.logger import logger
from src.config.settings import settings


def test_demucs_installation():
    """测试Demucs是否已安装"""
    logger.info("=" * 60)
    logger.info("测试1: 检查Demucs安装")
    logger.info("=" * 60)

    if AudioSeparator.check_installation():
        logger.success("✓ Demucs已安装并可用")

        # 显示可用模型
        models = AudioSeparator.get_available_models()
        logger.info(f"可用模型: {', '.join(models)}")
        return True
    else:
        logger.error("✗ Demucs未安装")
        logger.info("\n安装方法:")
        logger.info("  pip install demucs")
        return False


def test_vocal_separation():
    """测试人声分离"""
    logger.info("\n" + "=" * 60)
    logger.info("测试2: 人声分离")
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
            # 1. 提取音频
            logger.info("\n步骤1: 提取音频")
            with VideoProcessor(str(video_path)) as processor:
                audio_path = processor.extract_audio(
                    str(file_mgr.original_audio_path)
                )

            logger.info(f"音频文件: {Path(audio_path).name}")

            # 2. 分离人声
            logger.info("\n步骤2: 分离人声")
            logger.info("⚠️  注意: 首次运行会自动下载模型（约2GB），可能需要几分钟")

            separator = AudioSeparator(model="htdemucs")

            # 检测设备
            import torch
            device = "cuda" if torch.cuda.is_available() else "cpu"
            logger.info(f"使用设备: {device}")

            vocals_path = separator.separate_simple(
                audio_path=audio_path,
                output_path=str(file_mgr.separated_vocals_path),
                device=device
            )

            # 3. 检查结果
            vocals_file = Path(vocals_path)
            if vocals_file.exists():
                size_mb = vocals_file.stat().st_size / 1024 / 1024
                logger.info(f"\n人声文件: {vocals_file.name} ({size_mb:.1f} MB)")
                logger.success("✓ 人声分离成功")
                return True
            else:
                logger.error("✗ 人声文件未生成")
                return False

    except ImportError as e:
        if "torch" in str(e):
            logger.error("✗ PyTorch未安装")
            logger.info("\n安装方法:")
            logger.info("  # CPU版本")
            logger.info("  pip install torch")
            logger.info("\n  # GPU版本（推荐）")
            logger.info("  pip install torch --index-url https://download.pytorch.org/whl/cu118")
        else:
            logger.error(f"✗ 导入错误: {e}")
        return False

    except Exception as e:
        logger.error(f"✗ 人声分离失败: {e}")
        import traceback
        logger.debug(traceback.format_exc())
        return False


def main():
    """主测试函数"""
    logger.info("开始音频分离模块测试\n")

    # 测试1: 检查安装
    installation_ok = test_demucs_installation()

    if not installation_ok:
        logger.error("\n❌ Demucs未安装，无法继续测试")
        logger.info("\n请先安装依赖:")
        logger.info("  pip install torch demucs")
        return 1

    # 测试2: 人声分离
    logger.info("\n是否继续测试人声分离？这可能需要几分钟...")
    logger.info("（首次运行会下载约2GB的模型文件）")

    # 自动继续（如果是脚本运行）
    separation_ok = test_vocal_separation()

    # 汇总
    logger.info("\n" + "=" * 60)
    logger.info("测试汇总")
    logger.info("=" * 60)
    logger.info(f"1. Demucs安装: {'✓ 通过' if installation_ok else '✗ 失败'}")
    logger.info(f"2. 人声分离: {'✓ 通过' if separation_ok else '✗ 失败'}")

    if installation_ok and separation_ok:
        logger.success("\n🎉 所有测试通过！")
        return 0
    else:
        logger.error("\n❌ 部分测试失败")
        return 1


if __name__ == "__main__":
    sys.exit(main())
