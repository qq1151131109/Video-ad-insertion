"""
主讲人检测器

识别视频中的主讲人，判断视频是否为单人口播场景。
"""

from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple
import numpy as np
from pathlib import Path
import cv2

from src.utils.logger import logger
from src.core.face_detector import FaceDetector, FaceInfo


@dataclass
class SpeakerProfile:
    """主讲人档案"""
    face_id: int
    appearance_count: int  # 出现次数
    avg_position: Tuple[float, float]  # 平均位置 (x, y) 归一化到0-1
    avg_size: float  # 平均大小（占画面比例）
    position_variance: float  # 位置稳定性（方差越小越稳定）
    confidence_avg: float  # 平均人脸置信度
    best_frame: Optional[np.ndarray] = None  # 最佳帧
    best_frame_time: float = 0.0  # 最佳帧时间


@dataclass
class VideoSceneType:
    """视频场景类型"""
    is_single_speaker: bool  # 是否单人口播
    speaker_profile: Optional[SpeakerProfile]  # 主讲人档案
    total_sampled_frames: int  # 总采样帧数
    frames_with_faces: int  # 有人脸的帧数
    unique_speakers: int  # 检测到的不同讲者数量


class SpeakerDetector:
    """主讲人检测器"""

    def __init__(self, face_detector: FaceDetector):
        self.face_detector = face_detector

        # 主讲人判定阈值
        self.min_appearance_ratio = 0.5  # 至少出现在50%的采样帧中
        self.center_region = (0.2, 0.8, 0.1, 0.9)  # 中央区域 (x1, x2, y1, y2)
        self.min_face_size_ratio = 0.03  # 人脸至少占画面3%
        self.max_position_variance = 0.15  # 位置方差阈值

        # 采样参数
        self.sample_interval = 5.0  # 每5秒采样一帧

    def analyze_video_scene(
        self,
        video_path: Path,
        duration: float
    ) -> VideoSceneType:
        """
        分析视频场景类型，识别是否为单人口播

        Args:
            video_path: 视频路径
            duration: 视频时长

        Returns:
            场景类型分析结果
        """
        logger.info("分析视频场景类型...")
        logger.info(f"  采样间隔: {self.sample_interval}秒")

        # 1. 采样视频帧
        sample_times = np.arange(0, duration, self.sample_interval)
        logger.info(f"  将采样 {len(sample_times)} 帧")

        face_tracks = []  # 每一帧的人脸检测结果

        cap = cv2.VideoCapture(str(video_path))
        fps = cap.get(cv2.CAP_PROP_FPS)

        for sample_time in sample_times:
            # 提取帧
            frame_number = int(sample_time * fps)
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
            ret, frame = cap.read()

            if not ret:
                continue

            # 检测人脸
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            faces = self.face_detector.detect_faces(frame_rgb)

            face_tracks.append({
                'time': sample_time,
                'frame': frame_rgb,
                'faces': faces,
                'frame_size': (frame.shape[1], frame.shape[0])  # (width, height)
            })

        cap.release()

        # 2. 统计分析
        frames_with_faces = sum(1 for t in face_tracks if len(t['faces']) > 0)
        logger.info(
            f"  有人脸的帧: {frames_with_faces}/{len(face_tracks)} "
            f"({frames_with_faces/max(len(face_tracks), 1)*100:.1f}%)"
        )

        # 3. 识别主讲人
        speaker_profile = self._identify_main_speaker(face_tracks)

        # 4. 判断场景类型
        is_single_speaker = False
        unique_speakers = 0

        if speaker_profile:
            is_single_speaker = True
            unique_speakers = 1
            logger.success(
                f"✓ 识别为单人口播场景\n"
                f"  主讲人出现率: {speaker_profile.appearance_count}/{len(face_tracks)} "
                f"({speaker_profile.appearance_count/max(len(face_tracks), 1)*100:.1f}%)\n"
                f"  平均位置: ({speaker_profile.avg_position[0]:.2f}, {speaker_profile.avg_position[1]:.2f})\n"
                f"  平均大小: {speaker_profile.avg_size*100:.1f}% 画面\n"
                f"  位置稳定性: {speaker_profile.position_variance:.3f}\n"
                f"  最佳帧时间: {speaker_profile.best_frame_time:.1f}s"
            )
        else:
            # 尝试统计有多少不同的人
            if frames_with_faces > 0:
                avg_faces_per_frame = sum(len(t['faces']) for t in face_tracks) / frames_with_faces
                unique_speakers = max(1, int(avg_faces_per_frame))

            if frames_with_faces < len(face_tracks) * 0.3:
                logger.warning("⚠️ 非口播场景：人脸出现频率过低")
            elif unique_speakers > 1:
                logger.warning(f"⚠️ 多人场景：平均每帧{unique_speakers}个人脸")
            else:
                logger.warning("⚠️ 未识别到稳定的主讲人")

        return VideoSceneType(
            is_single_speaker=is_single_speaker,
            speaker_profile=speaker_profile,
            total_sampled_frames=len(face_tracks),
            frames_with_faces=frames_with_faces,
            unique_speakers=unique_speakers
        )

    def _identify_main_speaker(
        self,
        face_tracks: List[Dict]
    ) -> Optional[SpeakerProfile]:
        """
        从人脸跟踪数据中识别主讲人

        策略：
        1. 找出现频率最高的人脸位置
        2. 验证是否满足主讲人条件（频率、位置、大小）
        """
        if not face_tracks:
            return None

        # 1. 聚合相似人脸（基于位置和大小）
        face_clusters = self._cluster_faces(face_tracks)

        if not face_clusters:
            return None

        # 2. 找出现最频繁的cluster
        main_cluster = max(face_clusters, key=lambda c: c.appearance_count)

        # 3. 验证是否满足主讲人条件
        appearance_ratio = main_cluster.appearance_count / len(face_tracks)

        # 检查出现频率
        if appearance_ratio < self.min_appearance_ratio:
            logger.debug(
                f"人脸出现率{appearance_ratio*100:.1f}%低于阈值{self.min_appearance_ratio*100:.0f}%"
            )
            return None

        # 检查位置（是否在中央区域）
        x, y = main_cluster.avg_position
        x1, x2, y1, y2 = self.center_region
        if not (x1 <= x <= x2 and y1 <= y <= y2):
            logger.debug(
                f"人脸位置({x:.2f}, {y:.2f})不在中央区域{self.center_region}"
            )
            # 不严格要求位置，降低为警告
            logger.debug("  (位置要求放宽，继续处理)")

        # 检查大小
        if main_cluster.avg_size < self.min_face_size_ratio:
            logger.debug(
                f"人脸大小{main_cluster.avg_size*100:.1f}%小于阈值{self.min_face_size_ratio*100:.0f}%"
            )
            return None

        # 检查位置稳定性
        if main_cluster.position_variance > self.max_position_variance:
            logger.debug(
                f"位置方差{main_cluster.position_variance:.3f}大于阈值{self.max_position_variance}"
            )
            # 不严格要求稳定性
            logger.debug("  (稳定性要求放宽，继续处理)")

        return main_cluster

    def _cluster_faces(
        self,
        face_tracks: List[Dict]
    ) -> List[SpeakerProfile]:
        """
        将人脸聚类（简化版：基于位置相似度）

        假设：同一个人的人脸在视频中位置和大小相对稳定
        """
        clusters = []

        for track_data in face_tracks:
            if not track_data['faces']:
                continue

            frame_w, frame_h = track_data['frame_size']

            # 只考虑最大的人脸（假设是主讲人）
            face = max(track_data['faces'], key=lambda f: f.area)

            # 归一化位置和大小
            face_x, face_y = face.center
            face_x = face_x / frame_w
            face_y = face_y / frame_h
            face_size = face.area / (frame_w * frame_h)

            # 尝试匹配到现有cluster
            matched = False
            for cluster in clusters:
                # 位置距离
                dist = np.sqrt(
                    (face_x - cluster.avg_position[0])**2 +
                    (face_y - cluster.avg_position[1])**2
                )

                # 大小差异
                size_diff = abs(face_size - cluster.avg_size) / max(cluster.avg_size, 0.01)

                # 如果位置接近且大小相似，认为是同一个人
                if dist < 0.2 and size_diff < 0.5:
                    # 更新cluster
                    n = cluster.appearance_count
                    cluster.avg_position = (
                        (cluster.avg_position[0] * n + face_x) / (n + 1),
                        (cluster.avg_position[1] * n + face_y) / (n + 1)
                    )
                    cluster.avg_size = (cluster.avg_size * n + face_size) / (n + 1)
                    cluster.confidence_avg = (cluster.confidence_avg * n + face.confidence) / (n + 1)
                    cluster.appearance_count += 1

                    # 更新最佳帧（选择置信度最高且人脸较大的）
                    if face.confidence > cluster.confidence_avg * 0.95:
                        cluster.best_frame = track_data['frame']
                        cluster.best_frame_time = track_data['time']

                    matched = True
                    break

            # 创建新cluster
            if not matched:
                clusters.append(SpeakerProfile(
                    face_id=len(clusters),
                    appearance_count=1,
                    avg_position=(face_x, face_y),
                    avg_size=face_size,
                    position_variance=0.0,  # 后续计算
                    confidence_avg=face.confidence,
                    best_frame=track_data['frame'],
                    best_frame_time=track_data['time']
                ))

        # 计算每个cluster的位置方差
        for cluster in clusters:
            positions = []
            for track_data in face_tracks:
                if not track_data['faces']:
                    continue

                face = max(track_data['faces'], key=lambda f: f.area)
                frame_w, frame_h = track_data['frame_size']
                face_x, face_y = face.center
                face_x = face_x / frame_w
                face_y = face_y / frame_h

                dist = np.sqrt(
                    (face_x - cluster.avg_position[0])**2 +
                    (face_y - cluster.avg_position[1])**2
                )
                if dist < 0.2:
                    positions.append((face_x, face_y))

            if len(positions) > 1:
                positions_arr = np.array(positions)
                cluster.position_variance = float(np.var(positions_arr))

        return clusters

    def is_main_speaker_in_frame(
        self,
        frame: np.ndarray,
        speaker_profile: SpeakerProfile
    ) -> Tuple[bool, Optional[FaceInfo]]:
        """
        判断给定帧中是否包含主讲人

        Args:
            frame: 图像帧（RGB格式）
            speaker_profile: 主讲人档案

        Returns:
            (是否是主讲人, 人脸信息)
        """
        faces = self.face_detector.detect_faces(frame)

        if not faces:
            return False, None

        frame_h, frame_w = frame.shape[:2]

        # 找最大的人脸
        best_face = max(faces, key=lambda f: f.area)

        # 计算人脸位置（归一化）
        face_x, face_y = best_face.center
        face_x = face_x / frame_w
        face_y = face_y / frame_w

        # 与主讲人位置比较
        dist = np.sqrt(
            (face_x - speaker_profile.avg_position[0])**2 +
            (face_y - speaker_profile.avg_position[1])**2
        )

        # 判断是否是主讲人（位置接近）
        is_main_speaker = dist < 0.25  # 稍微放宽距离阈值

        return is_main_speaker, best_face if is_main_speaker else None
