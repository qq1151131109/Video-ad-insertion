"""
ASR和LLM测试脚本

测试语音识别和内容分析功能
"""
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.core.asr import ASRService
from src.core.video_processor import VideoProcessor
from src.services.llm_service import LLMService
from src.config.ads import AdsManager
from src.utils.file_manager import TempFileManager
from src.utils.logger import logger
from src.config.settings import settings


def test_asr_installation():
    """测试ASR是否已安装"""
    logger.info("=" * 60)
    logger.info("测试1: 检查Whisper安装")
    logger.info("=" * 60)

    if ASRService.check_installation():
        logger.success("✓ Whisper已安装")
        models = ASRService.get_available_models()
        logger.info(f"可用模型: {', '.join(models)}")
        return True
    else:
        logger.error("✗ Whisper未安装")
        logger.info("\n安装方法:")
        logger.info("  pip install openai-whisper")
        return False


def test_llm_api_key():
    """测试LLM API密钥配置"""
    logger.info("\n" + "=" * 60)
    logger.info("测试2: 检查LLM API配置")
    logger.info("=" * 60)

    if LLMService.check_api_key():
        logger.success("✓ OpenAI API密钥已配置")
        logger.info(f"模型: {settings.OPENAI_MODEL}")
        logger.info(f"Base URL: {settings.OPENAI_BASE_URL}")
        return True
    else:
        logger.error("✗ OpenAI API密钥未配置")
        return False


def test_asr_transcription():
    """测试语音识别"""
    logger.info("\n" + "=" * 60)
    logger.info("测试3: 语音识别")
    logger.info("=" * 60)

    # 查找测试视频
    video_files = list(settings.INPUT_DIR.glob("*.mp4"))
    if not video_files:
        logger.error("❌ input目录下没有视频文件")
        return False, None

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

            # 2. 语音识别
            logger.info("\n步骤2: 语音识别")
            logger.info("⚠️  注意: 首次运行会自动下载Whisper模型，可能需要几分钟")
            logger.info("推荐使用GPU加速（需安装PyTorch CUDA版本）")

            asr = ASRService(model_name="base")  # 使用base模型（快速，适合测试）

            result = asr.transcribe(
                audio_path=audio_path,
                language="zh",  # 指定中文
                word_timestamps=True
            )

            # 3. 显示结果
            logger.info("\n" + "=" * 60)
            logger.info("识别结果")
            logger.info("=" * 60)
            logger.info(f"检测语言: {result.language}")
            logger.info(f"片段数量: {len(result.segments)}")
            logger.info(f"\n完整文本:\n{result.full_text}")

            logger.info("\n前5个片段:")
            for i, seg in enumerate(result.segments[:5], 1):
                logger.info(f"{i}. {seg}")

            # 测试上下文提取
            if result.segments:
                mid_time = result.segments[len(result.segments) // 2].start
                before, after = result.get_context(mid_time, before_sentences=2, after_sentences=1)

                logger.info(f"\n中间位置({mid_time:.1f}s)的上下文:")
                logger.info(f"前文: {before}")
                logger.info(f"后文: {after}")

            logger.success("\n✓ 语音识别成功")
            return True, result

    except ImportError as e:
        if "whisper" in str(e):
            logger.error("✗ Whisper未安装")
            logger.info("\n安装方法:")
            logger.info("  pip install openai-whisper")
        else:
            logger.error(f"✗ 导入错误: {e}")
        return False, None

    except Exception as e:
        logger.error(f"✗ 语音识别失败: {e}")
        import traceback
        logger.debug(traceback.format_exc())
        return False, None


def test_llm_content_analysis(transcription_result):
    """测试LLM内容分析"""
    logger.info("\n" + "=" * 60)
    logger.info("测试4: LLM内容分析")
    logger.info("=" * 60)

    if transcription_result is None:
        logger.error("❌ 没有转录结果，跳过测试")
        return False, None

    try:
        # 转换为LLM所需格式
        segments = [
            {
                "text": seg.text,
                "start": seg.start,
                "end": seg.end
            }
            for seg in transcription_result.segments
        ]

        # 计算视频时长
        video_duration = segments[-1]["end"] if segments else 60.0

        logger.info(f"视频时长: {video_duration:.1f}秒")
        logger.info(f"片段数量: {len(segments)}")

        # 执行内容分析
        llm = LLMService()
        analysis = llm.analyze_video_content(
            transcription_segments=segments,
            video_duration=video_duration,
            avoid_start=5.0,
            avoid_end=5.0,
            num_candidates=3
        )

        # 显示分析结果
        logger.info("\n" + "=" * 60)
        logger.info("分析结果")
        logger.info("=" * 60)
        logger.info(f"主题: {analysis.theme}")
        logger.info(f"类别: {analysis.category}")
        logger.info(f"语气: {analysis.tone}")
        logger.info(f"受众: {analysis.target_audience}")

        logger.info(f"\n关键要点:")
        for i, point in enumerate(analysis.key_points, 1):
            logger.info(f"  {i}. {point}")

        logger.info(f"\n推荐插入点:")
        for i, point in enumerate(analysis.insertion_points, 1):
            logger.info(f"\n  候选{i} (优先级{point.priority}):")
            logger.info(f"    时间: {point.time:.1f}秒")
            logger.info(f"    理由: {point.reason}")
            logger.info(f"    前文: {point.context_before}")
            logger.info(f"    后文: {point.context_after}")
            logger.info(f"    过渡: {point.transition_hint}")

        logger.success("\n✓ 内容分析成功")
        return True, analysis

    except Exception as e:
        logger.error(f"✗ 内容分析失败: {e}")
        import traceback
        logger.debug(traceback.format_exc())
        return False, None


def test_ad_script_generation(analysis):
    """测试广告词生成"""
    logger.info("\n" + "=" * 60)
    logger.info("测试5: 广告词生成")
    logger.info("=" * 60)

    if analysis is None:
        logger.error("❌ 没有分析结果，跳过测试")
        return False

    try:
        # 加载广告配置
        ads_manager = AdsManager()

        # 选择合适的广告
        ad = ads_manager.select_ad_for_video(analysis.theme)

        if ad is None:
            logger.error("❌ 没有可用的广告")
            return False

        logger.info(f"选中广告: {ad.name} ({ad.product})")
        logger.info(f"卖点: {ad.get_selling_points_text()}")

        # 使用第一个插入点生成广告词
        if not analysis.insertion_points:
            logger.error("❌ 没有插入点")
            return False

        insertion_point = analysis.insertion_points[0]

        # 生成广告词
        llm = LLMService()
        ad_script = llm.generate_ad_script(
            video_theme=analysis.theme,
            video_category=analysis.category,
            video_tone=analysis.tone,
            context_before=insertion_point.context_before,
            context_after=insertion_point.context_after,
            ad_config=ad,
            transition_hint=insertion_point.transition_hint
        )

        # 显示结果
        logger.info("\n" + "=" * 60)
        logger.info("生成的广告词")
        logger.info("=" * 60)
        logger.info(f"\n插入位置: {insertion_point.time:.1f}秒")
        logger.info(f"前文: {insertion_point.context_before}")
        logger.info(f"【广告词】{ad_script}")
        logger.info(f"后文: {insertion_point.context_after}")

        logger.success("\n✓ 广告词生成成功")
        return True

    except Exception as e:
        logger.error(f"✗ 广告词生成失败: {e}")
        import traceback
        logger.debug(traceback.format_exc())
        return False


def main():
    """主测试函数"""
    logger.info("开始ASR和LLM模块测试\n")

    results = {}

    # 测试1: 检查ASR安装
    results['asr_install'] = test_asr_installation()

    # 测试2: 检查LLM配置
    results['llm_config'] = test_llm_api_key()

    if not results['asr_install']:
        logger.error("\n❌ Whisper未安装，无法继续测试")
        logger.info("\n请先安装依赖:")
        logger.info("  pip install openai-whisper")
        return 1

    if not results['llm_config']:
        logger.error("\n❌ LLM API未配置，部分测试将被跳过")

    # 测试3: 语音识别
    results['asr'], transcription = test_asr_transcription()

    # 测试4: 内容分析（需要LLM API）
    if results['llm_config'] and results['asr']:
        results['analysis'], analysis = test_llm_content_analysis(transcription)
    else:
        results['analysis'] = False
        analysis = None

    # 测试5: 广告词生成（需要LLM API和分析结果）
    if results['llm_config'] and results['analysis']:
        results['ad_script'] = test_ad_script_generation(analysis)
    else:
        results['ad_script'] = False

    # 汇总
    logger.info("\n" + "=" * 60)
    logger.info("测试汇总")
    logger.info("=" * 60)
    logger.info(f"1. Whisper安装: {'✓ 通过' if results['asr_install'] else '✗ 失败'}")
    logger.info(f"2. LLM API配置: {'✓ 通过' if results['llm_config'] else '✗ 失败'}")
    logger.info(f"3. 语音识别: {'✓ 通过' if results['asr'] else '✗ 失败'}")
    logger.info(f"4. 内容分析: {'✓ 通过' if results['analysis'] else '✗ 失败'}")
    logger.info(f"5. 广告词生成: {'✓ 通过' if results['ad_script'] else '✗ 失败'}")

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
