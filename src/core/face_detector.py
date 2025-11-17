"""
人脸检测模块

使用MTCNN进行人脸检测，用于评估关键帧质量
"""
import numpy as np
from pathlib import Path
from typing import Optional, List, Tuple
import cv2

from src.utils.logger import logger


class FaceInfo:
    """人脸信息"""

    def __init__(self, bbox: List[float], confidence: float, landmarks: Optional[np.ndarray] = None):
        """
        初始化人脸信息

        Args:
            bbox: 边界框 [x1, y1, x2, y2]
            confidence: 置信度 (0-1)
            landmarks: 5个关键点 [[x, y], ...] (左眼、右眼、鼻子、左嘴角、右嘴角)
        """
        self.bbox = bbox
        self.confidence = confidence
        self.landmarks = landmarks

    @property
    def width(self) -> float:
        """人脸宽度"""
        return self.bbox[2] - self.bbox[0]

    @property
    def height(self) -> float:
        """人脸高度"""
        return self.bbox[3] - self.bbox[1]

    @property
    def area(self) -> float:
        """人脸面积"""
        return self.width * self.height

    @property
    def center(self) -> Tuple[float, float]:
        """人脸中心点"""
        x = (self.bbox[0] + self.bbox[2]) / 2
        y = (self.bbox[1] + self.bbox[3]) / 2
        return x, y

    def __repr__(self) -> str:
        return f"Face(bbox={self.bbox}, conf={self.confidence:.2f})"


class FaceDetector:
    """人脸检测器（基于MTCNN）"""

    def __init__(self, min_face_size: int = 20, confidence_threshold: float = 0.9):
        """
        初始化人脸检测器

        Args:
            min_face_size: 最小人脸尺寸（像素）
            confidence_threshold: 置信度阈值 (0-1)
        """
        self.min_face_size = min_face_size
        self.confidence_threshold = confidence_threshold

        # 延迟加载MTCNN（首次使用时加载）
        self._detector = None

        logger.info(f"人脸检测器初始化: min_size={min_face_size}, threshold={confidence_threshold}")

    def _load_detector(self):
        """加载MTCNN检测器"""
        if self._detector is None:
            try:
                from mtcnn import MTCNN
                logger.info("加载MTCNN人脸检测器...")
                # MTCNN不接受min_face_size参数，我们在后处理时过滤
                self._detector = MTCNN()
                logger.success("✓ MTCNN已加载")
            except ImportError:
                logger.error("✗ MTCNN未安装，请运行: pip install mtcnn")
                raise

    def detect_faces(self, image: np.ndarray) -> List[FaceInfo]:
        """
        检测图像中的人脸

        Args:
            image: 图像数组 (BGR格式，OpenCV格式)

        Returns:
            人脸信息列表，按置信度降序排序
        """
        # 加载检测器
        self._load_detector()

        # 转换为RGB（MTCNN需要RGB格式）
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

        # 检测人脸
        detections = self._detector.detect_faces(image_rgb)

        # 过滤低置信度和小人脸
        faces = []
        for det in detections:
            confidence = det['confidence']
            if confidence >= self.confidence_threshold:
                bbox = det['box']  # [x, y, width, height]

                # 检查人脸大小
                face_width = bbox[2]
                face_height = bbox[3]
                if face_width < self.min_face_size or face_height < self.min_face_size:
                    continue  # 跳过太小的人脸

                # 转换为 [x1, y1, x2, y2]
                bbox = [bbox[0], bbox[1], bbox[0] + bbox[2], bbox[1] + bbox[3]]

                # 提取关键点
                landmarks = None
                if 'keypoints' in det:
                    kp = det['keypoints']
                    landmarks = np.array([
                        [kp['left_eye'][0], kp['left_eye'][1]],
                        [kp['right_eye'][0], kp['right_eye'][1]],
                        [kp['nose'][0], kp['nose'][1]],
                        [kp['mouth_left'][0], kp['mouth_left'][1]],
                        [kp['mouth_right'][0], kp['mouth_right'][1]]
                    ])

                faces.append(FaceInfo(
                    bbox=bbox,
                    confidence=confidence,
                    landmarks=landmarks
                ))

        # 按置信度降序排序
        faces.sort(key=lambda f: f.confidence, reverse=True)

        return faces

    def has_clear_face(self, image: np.ndarray, min_face_ratio: float = 0.05) -> bool:
        """
        检查图像是否有清晰的人脸

        Args:
            image: 图像数组
            min_face_ratio: 人脸最小面积占比（相对于图像总面积）

        Returns:
            是否有清晰人脸
        """
        faces = self.detect_faces(image)

        if not faces:
            return False

        # 获取最大人脸
        largest_face = max(faces, key=lambda f: f.area)

        # 计算面积占比
        image_area = image.shape[0] * image.shape[1]
        face_ratio = largest_face.area / image_area

        return face_ratio >= min_face_ratio

    def get_best_face(self, image: np.ndarray) -> Optional[FaceInfo]:
        """
        获取图像中最佳人脸（综合考虑大小和置信度）

        Args:
            image: 图像数组

        Returns:
            最佳人脸信息，如果没有则返回None
        """
        faces = self.detect_faces(image)

        if not faces:
            return None

        # 综合评分：置信度 * sqrt(面积)
        # 使用sqrt避免过度偏向大人脸
        def score(face: FaceInfo) -> float:
            return face.confidence * np.sqrt(face.area)

        best_face = max(faces, key=score)
        return best_face

    def score_frame_quality(
        self,
        image: np.ndarray,
        sharpness_score: float,
        face_weight: float = 0.3,
        sharpness_weight: float = 0.7
    ) -> float:
        """
        综合评分关键帧质量（结合人脸和清晰度）

        Args:
            image: 图像数组
            sharpness_score: 清晰度分数 (通常是Laplacian方差)
            face_weight: 人脸权重
            sharpness_weight: 清晰度权重

        Returns:
            综合质量分数（越高越好）
        """
        faces = self.detect_faces(image)

        # 归一化清晰度分数（假设典型范围是0-1000）
        normalized_sharpness = min(sharpness_score / 1000.0, 1.0)

        # 计算人脸分数
        if not faces:
            # 没有人脸，只用清晰度
            return normalized_sharpness
        else:
            # 有人脸，综合评分
            best_face = max(faces, key=lambda f: f.confidence * np.sqrt(f.area))

            # 归一化人脸分数
            image_area = image.shape[0] * image.shape[1]
            face_ratio = best_face.area / image_area
            normalized_face = min(face_ratio * 10, 1.0) * best_face.confidence

            # 加权求和
            total_score = (
                face_weight * normalized_face +
                sharpness_weight * normalized_sharpness
            )

            return total_score

    @staticmethod
    def check_installation() -> bool:
        """
        检查MTCNN是否已安装

        Returns:
            是否已安装
        """
        try:
            from mtcnn import MTCNN
            logger.info("✓ MTCNN已安装")
            return True
        except ImportError:
            logger.error("✗ MTCNN未安装，请运行: pip install mtcnn")
            return False

    @staticmethod
    def draw_faces(image: np.ndarray, faces: List[FaceInfo], color=(0, 255, 0), thickness=2) -> np.ndarray:
        """
        在图像上绘制人脸框（用于调试）

        Args:
            image: 图像数组
            faces: 人脸列表
            color: 边框颜色 (B, G, R)
            thickness: 边框粗细

        Returns:
            绘制后的图像
        """
        result = image.copy()

        for face in faces:
            x1, y1, x2, y2 = [int(v) for v in face.bbox]

            # 绘制边框
            cv2.rectangle(result, (x1, y1), (x2, y2), color, thickness)

            # 绘制置信度
            label = f"{face.confidence:.2f}"
            cv2.putText(
                result,
                label,
                (x1, y1 - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                color,
                thickness
            )

            # 绘制关键点
            if face.landmarks is not None:
                for point in face.landmarks:
                    cv2.circle(result, tuple(point.astype(int)), 2, (0, 0, 255), -1)

        return result
