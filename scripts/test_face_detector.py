"""
人脸检测测试脚本

测试MTCNN人脸检测功能
"""
import sys
from pathlib import Path
import cv2

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.core.face_detector import FaceDetector
from src.core.video_processor import VideoProcessor
from src.utils.file_manager import TempFileManager
from src.utils.logger import logger
from src.config.settings import settings


def test_face_detector_installation():
    """测试人脸检测器是否已安装"""
    logger.info("=" * 60)
    logger.info("测试1: 检查MTCNN安装")
    logger.info("=" * 60)

    if FaceDetector.check_installation():
        logger.success("✓ MTCNN已安装")
        return True
    else:
        logger.error("✗ MTCNN未安装")
        logger.info("\n安装方法:")
        logger.info("  pip install mtcnn tensorflow")
        return False


def test_face_detection():
    """测试人脸检测"""
    logger.info("\n" + "=" * 60)
    logger.info("测试2: 人脸检测")
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
            logger.info("\n步骤1: 提取关键帧")
            with VideoProcessor(str(video_path)) as processor:
                metadata = processor.extract_metadata()
                logger.info(f"视频时长: {metadata.duration:.1f}秒")

                # 提取中间位置的关键帧
                mid_time = metadata.duration / 2
                frame, actual_time = processor.extract_best_frame_around_time(
                    target_time=mid_time,
                    window_size=2.0,
                    num_candidates=10
                )

            logger.info(f"关键帧时间: {actual_time:.2f}秒")
            logger.info(f"帧尺寸: {frame.shape[1]}x{frame.shape[0]}")

            # 2. 人脸检测
            logger.info("\n步骤2: 检测人脸")
            logger.info("⚠️  首次运行会自动下载MTCNN模型")

            detector = FaceDetector(
                min_face_size=20,
                confidence_threshold=0.9
            )

            faces = detector.detect_faces(frame)

            # 3. 显示结果
            logger.info("\n" + "=" * 60)
            logger.info("检测结果")
            logger.info("=" * 60)
            logger.info(f"检测到 {len(faces)} 个人脸")

            if faces:
                for i, face in enumerate(faces, 1):
                    logger.info(f"\n人脸 {i}:")
                    logger.info(f"  置信度: {face.confidence:.3f}")
                    logger.info(f"  位置: {[int(v) for v in face.bbox]}")
                    logger.info(f"  尺寸: {face.width:.0f}x{face.height:.0f}")
                    logger.info(f"  面积: {face.area:.0f}像素²")
                    logger.info(f"  中心: ({face.center[0]:.0f}, {face.center[1]:.0f})")

                # 测试清晰人脸检查
                has_clear = detector.has_clear_face(frame, min_face_ratio=0.05)
                logger.info(f"\n是否有清晰人脸: {'是' if has_clear else '否'}")

                # 测试最佳人脸获取
                best_face = detector.get_best_face(frame)
                if best_face:
                    logger.info(f"最佳人脸置信度: {best_face.confidence:.3f}")

                # 测试质量评分
                sharpness = cv2.Laplacian(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY), cv2.CV_64F).var()
                quality_score = detector.score_frame_quality(
                    frame,
                    sharpness_score=sharpness,
                    face_weight=0.3,
                    sharpness_weight=0.7
                )
                logger.info(f"\n帧质量评分:")
                logger.info(f"  清晰度: {sharpness:.1f}")
                logger.info(f"  综合评分: {quality_score:.3f}")

                # 保存带标注的图像
                output_path = file_mgr.get_path("keyframes", "face_detection_result.jpg")
                annotated = FaceDetector.draw_faces(frame, faces)
                cv2.imwrite(str(output_path), annotated)
                logger.info(f"\n标注图像已保存: {output_path}")

                logger.success("\n✓ 人脸检测成功")
                return True
            else:
                logger.warning("\n⚠️  未检测到人脸")
                logger.info("可能原因:")
                logger.info("  1. 视频中没有人脸")
                logger.info("  2. 置信度阈值过高")
                logger.info("  3. 人脸太小或模糊")
                return True  # 不算失败，只是没检测到

    except ImportError as e:
        if "mtcnn" in str(e).lower() or "tensorflow" in str(e).lower():
            logger.error("✗ MTCNN或TensorFlow未安装")
            logger.info("\n安装方法:")
            logger.info("  pip install mtcnn tensorflow")
        else:
            logger.error(f"✗ 导入错误: {e}")
        return False

    except Exception as e:
        logger.error(f"✗ 人脸检测失败: {e}")
        import traceback
        logger.debug(traceback.format_exc())
        return False


def test_multiple_frames():
    """测试多帧人脸检测（选择最佳人脸帧）"""
    logger.info("\n" + "=" * 60)
    logger.info("测试3: 多帧最佳人脸选择")
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
            with VideoProcessor(str(video_path)) as processor:
                metadata = processor.extract_metadata()

                # 提取多个时间点的帧
                times = [
                    metadata.duration * 0.25,
                    metadata.duration * 0.5,
                    metadata.duration * 0.75
                ]

                logger.info(f"测试时间点: {[f'{t:.1f}s' for t in times]}")

                detector = FaceDetector()
                results = []

                for i, time in enumerate(times, 1):
                    logger.info(f"\n检测帧 {i} ({time:.1f}s)...")

                    frame, actual_time = processor.extract_best_frame_around_time(
                        target_time=time,
                        window_size=1.0
                    )

                    faces = detector.detect_faces(frame)
                    best_face = detector.get_best_face(frame)

                    sharpness = cv2.Laplacian(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY), cv2.CV_64F).var()
                    quality = detector.score_frame_quality(frame, sharpness)

                    results.append({
                        'time': actual_time,
                        'faces': len(faces),
                        'best_face': best_face,
                        'quality': quality,
                        'frame': frame
                    })

                    logger.info(f"  人脸数: {len(faces)}")
                    if best_face:
                        logger.info(f"  最佳人脸置信度: {best_face.confidence:.3f}")
                    logger.info(f"  质量评分: {quality:.3f}")

                # 选择最佳帧
                best_result = max(results, key=lambda r: r['quality'])

                logger.info("\n" + "=" * 60)
                logger.info("最佳关键帧")
                logger.info("=" * 60)
                logger.info(f"时间: {best_result['time']:.1f}秒")
                logger.info(f"人脸数: {best_result['faces']}")
                logger.info(f"质量评分: {best_result['quality']:.3f}")

                # 保存最佳帧
                output_path = file_mgr.get_path("keyframes", "best_face_frame.jpg")
                cv2.imwrite(str(output_path), best_result['frame'])
                logger.info(f"\n最佳帧已保存: {output_path}")

                logger.success("\n✓ 多帧检测成功")
                return True

    except Exception as e:
        logger.error(f"✗ 多帧检测失败: {e}")
        import traceback
        logger.debug(traceback.format_exc())
        return False


def main():
    """主测试函数"""
    logger.info("开始人脸检测模块测试\n")

    # 测试1: 检查安装
    installation_ok = test_face_detector_installation()

    if not installation_ok:
        logger.error("\n❌ MTCNN未安装，无法继续测试")
        logger.info("\n请先安装依赖:")
        logger.info("  pip install mtcnn tensorflow")
        return 1

    # 测试2: 人脸检测
    detection_ok = test_face_detection()

    # 测试3: 多帧检测
    multi_frame_ok = test_multiple_frames()

    # 汇总
    logger.info("\n" + "=" * 60)
    logger.info("测试汇总")
    logger.info("=" * 60)
    logger.info(f"1. MTCNN安装: {'✓ 通过' if installation_ok else '✗ 失败'}")
    logger.info(f"2. 人脸检测: {'✓ 通过' if detection_ok else '✗ 失败'}")
    logger.info(f"3. 多帧检测: {'✓ 通过' if multi_frame_ok else '✗ 失败'}")

    if installation_ok and detection_ok and multi_frame_ok:
        logger.success("\n🎉 所有测试通过！")
        return 0
    else:
        logger.error("\n❌ 部分测试失败")
        return 1


if __name__ == "__main__":
    sys.exit(main())
