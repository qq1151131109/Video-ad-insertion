"""
数字人生成服务

使用InfiniteTalk workflow生成数字人说话视频
"""
import json
from pathlib import Path
from typing import Optional, Dict, Any

from PIL import Image

from src.services.comfyui_client import ComfyUIClient
from src.config.settings import settings
from src.utils.logger import logger


class DigitalHumanService:
    """数字人生成服务（基于InfiniteTalk）"""

    def __init__(self, client: Optional[ComfyUIClient] = None):
        """
        初始化数字人生成服务

        Args:
            client: ComfyUI客户端（None则自动创建）
        """
        self.client = client or ComfyUIClient()
        self.workflow_path = settings.get_workflow_path("digital_human")

        # 加载workflow配置
        self._workflow_template: Optional[Dict] = None

        logger.info("数字人生成服务初始化")

    def _load_workflow_template(self) -> Dict:
        """
        加载workflow模板

        Returns:
            workflow配置字典
        """
        if self._workflow_template is None:
            logger.info(f"加载数字人生成workflow: {self.workflow_path.name}")

            with open(self.workflow_path, 'r', encoding='utf-8') as f:
                self._workflow_template = json.load(f)

            logger.debug(f"Workflow节点数: {len(self._workflow_template)}")

        return self._workflow_template

    def generate_video(
        self,
        face_image_path: str,
        audio_path: str,
        output_video_path: str,
        fps: int = 25,
        quality: str = "high",
        target_width: Optional[int] = None,  # 目标宽度（匹配原视频）
        target_height: Optional[int] = None,  # 目标高度（匹配原视频）
        output_node_id: str = "385",  # VHS_VideoCombine节点（111603版本）
        timeout: int = 3600  # 增加到60分钟，InfiniteTalk生成81帧需要较长时间
    ) -> str:
        """
        生成数字人视频

        Args:
            face_image_path: 人脸图片路径（清洗后的关键帧）
            audio_path: 音频路径（克隆的声音）
            output_video_path: 输出视频路径
            fps: 帧率
            quality: 质量（high/medium/low）
            output_node_id: workflow输出节点ID
            timeout: 超时时间（秒）

        Returns:
            输出视频路径

        Raises:
            FileNotFoundError: 输入文件不存在
            Exception: 处理失败
        """
        face_path = Path(face_image_path)
        audio_file = Path(audio_path)
        output_path = Path(output_video_path)

        if not face_path.exists():
            raise FileNotFoundError(f"人脸图片不存在: {face_path}")

        if not audio_file.exists():
            raise FileNotFoundError(f"音频文件不存在: {audio_file}")

        # 如果未显式提供目标分辨率，则从人脸图片自动推断
        if target_width is None or target_height is None:
            try:
                with Image.open(face_path) as img:
                    img_width, img_height = img.size
                if target_width is None:
                    target_width = img_width
                if target_height is None:
                    target_height = img_height
                logger.info(f"自动推断目标分辨率: {target_width}x{target_height}")
            except Exception as e:
                logger.warning(f"无法从图片推断分辨率，将使用workflow默认设置: {e}")

        logger.info("开始生成数字人视频")
        logger.info(f"人脸图片: {face_path.name}")
        logger.info(f"音频文件: {audio_file.name}")
        logger.info(f"参数: fps={fps}, quality={quality}")

        try:
            # 1. 上传人脸图片
            logger.info("上传人脸图片到ComfyUI...")
            uploaded_image = self.client.upload_file(str(face_path))
            image_filename = uploaded_image.get("name")

            if not image_filename:
                raise Exception("人脸图片上传失败")

            logger.success(f"✓ 图片已上传: {image_filename}")

            # 2. 上传音频
            logger.info("上传音频到ComfyUI...")
            uploaded_audio = self.client.upload_file(str(audio_file))
            audio_filename = uploaded_audio.get("name")

            if not audio_filename:
                raise Exception("音频上传失败")

            logger.success(f"✓ 音频已上传: {audio_filename}")

            # 3. 准备workflow
            workflow = self._prepare_workflow(
                image_filename=image_filename,
                audio_filename=audio_filename,
                fps=fps,
                quality=quality,
                target_width=target_width,
                target_height=target_height
            )

            # 4. 执行workflow并下载结果
            logger.info("执行数字人生成workflow...")
            logger.info("⚠️  这可能需要3-5分钟，请耐心等待...")

            result_path = self.client.run_workflow_and_download(
                workflow=workflow,
                output_node_id=output_node_id,
                output_path=str(output_path),
                timeout=timeout,
                file_type='gifs'  # VHS_VideoCombine节点使用'gifs'作为输出键（即使是MP4格式）
            )

            logger.success(f"✓ 数字人视频生成完成: {output_path.name}")

            return result_path

        except Exception as e:
            logger.error(f"数字人生成失败: {e}")
            raise

    def _prepare_workflow(
        self,
        image_filename: str,
        audio_filename: str,
        fps: int,
        quality: str,
        target_width: Optional[int] = None,
        target_height: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        准备workflow（替换参数）

        根据最新workflow结构（InfiniteTalk数字人图生视频-API-111604.json）：
        - LoadImage: 输入图片
        - LoadAudio: 输入音频
        - MultiTalkWav2VecEmbeds: fps参数
        - VHS_VideoCombine: frame_rate参数

        Args:
            image_filename: 上传后的图片文件名
            audio_filename: 上传后的音频文件名
            fps: 帧率
            quality: 质量（当前workflow暂不支持quality参数）

        Returns:
            准备好的workflow配置
        """
        import copy

        # 加载模板（深拷贝）
        workflow = copy.deepcopy(self._load_workflow_template())

        # 查找并替换参数节点
        for node_id, node in workflow.items():
            if not isinstance(node, dict):  # 跳过非字典项
                continue

            class_type = node.get("class_type", "")

            # LoadImage节点 - 设置输入图片
            if class_type == "LoadImage":
                if "inputs" in node:
                    node["inputs"]["image"] = image_filename
                    logger.debug(f"设置图片输入: {image_filename} (节点{node_id})")

            # LoadAudio节点 - 设置输入音频
            elif class_type == "LoadAudio":
                if "inputs" in node:
                    node["inputs"]["audio"] = audio_filename
                    logger.debug(f"设置音频输入: {audio_filename} (节点{node_id})")

            # MultiTalkWav2VecEmbeds节点 - 设置fps
            elif class_type == "MultiTalkWav2VecEmbeds":
                if "inputs" in node and "fps" in node["inputs"]:
                    node["inputs"]["fps"] = fps
                    logger.debug(f"设置音频嵌入fps: {fps} (节点{node_id})")

            # VHS_VideoCombine节点 - 设置frame_rate
            elif class_type == "VHS_VideoCombine":
                if "inputs" in node and "frame_rate" in node["inputs"]:
                    node["inputs"]["frame_rate"] = fps
                    logger.debug(f"设置视频合成帧率: {fps} (节点{node_id})")

            # LayerUtility: ImageScaleByAspectRatio V2节点 - 设置分辨率（带OOM保护）
            elif class_type == "LayerUtility: ImageScaleByAspectRatio V2":
                if target_width and target_height and "inputs" in node:
                    # OOM保护：控制短边最大为480（避免显存溢出）
                    # InfiniteTalk生成81帧视频，高分辨率会导致GPU OOM
                    MIN_EDGE_LIMIT = 480

                    # 计算短边和长边
                    original_min_edge = min(target_width, target_height)
                    original_max_edge = max(target_width, target_height)

                    # 如果短边超过限制，按短边缩放
                    if original_min_edge > MIN_EDGE_LIMIT:
                        # 计算缩放比例（基于短边）
                        scale_ratio = MIN_EDGE_LIMIT / original_min_edge
                        # 计算缩放后的长边
                        scaled_max_edge = int(original_max_edge * scale_ratio)
                        # LayerUtility节点使用长边作为scale_to_length
                        scale_to_length = scaled_max_edge

                        logger.warning(f"⚠️  原分辨率短边{original_min_edge}过大，缩小到短边{MIN_EDGE_LIMIT}以避免GPU OOM")
                        logger.info(f"原尺寸: {target_width}x{target_height} → 缩放后约: {int(target_width * scale_ratio)}x{int(target_height * scale_ratio)}")
                    else:
                        # 不需要缩放，使用原始长边
                        scale_to_length = original_max_edge

                    node["inputs"]["scale_to_length"] = scale_to_length
                    logger.info(f"设置图片缩放尺寸: {scale_to_length} (原{target_width}x{target_height})")

            # WanVideoImageToVideoMultiTalk节点 - 启用色彩匹配（修复渐进式变暗）
            elif class_type == "WanVideoImageToVideoMultiTalk":
                if "inputs" in node:
                    # 启用最强色彩匹配以保持81帧的色彩一致性
                    # hm-mvgd-hm: 组合Histogram Matching和MVGD，最强的色彩一致性保证
                    node["inputs"]["colormatch"] = "hm-mvgd-hm"
                    logger.info(f"✓ 启用色彩匹配: hm-mvgd-hm (节点{node_id}) - 防止渐进式变暗")

            # WanVideoDecode节点 - 优化归一化设置（修复VAE解码色彩衰减）
            elif class_type == "WanVideoDecode":
                if "inputs" in node:
                    # 使用minmax归一化以更严格控制亮度范围
                    node["inputs"]["normalization"] = "minmax"
                    logger.info(f"✓ 优化VAE归一化: minmax (节点{node_id}) - 保持亮度稳定性")

        return workflow

    def generate_video_simple(
        self,
        face_image_path: str,
        audio_path: str,
        output_video_path: str,
        timeout: int = 1200
    ) -> str:
        """
        简化的数字人生成接口（使用默认参数）

        Args:
            face_image_path: 人脸图片路径
            audio_path: 音频路径
            output_video_path: 输出视频路径
            timeout: 超时时间

        Returns:
            输出视频路径
        """
        return self.generate_video(
            face_image_path=face_image_path,
            audio_path=audio_path,
            output_video_path=output_video_path,
            fps=25,
            quality="high",
            timeout=timeout
        )

    def batch_generate(
        self,
        face_image_path: str,
        audio_paths: list[str],
        output_dir: str,
        fps: int = 25,
        timeout_per_video: int = 600
    ) -> list[str]:
        """
        批量生成数字人视频

        Args:
            face_image_path: 人脸图片路径（同一人脸）
            audio_paths: 音频路径列表
            output_dir: 输出目录
            fps: 帧率
            timeout_per_video: 每个视频的超时时间

        Returns:
            输出视频路径列表
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"批量生成数字人视频: {len(audio_paths)}个")

        output_paths = []

        for i, audio_path in enumerate(audio_paths, 1):
            output_path = output_dir / f"digital_human_{i:03d}.mp4"

            logger.info(f"处理 {i}/{len(audio_paths)}: {Path(audio_path).name}")

            try:
                result = self.generate_video(
                    face_image_path=face_image_path,
                    audio_path=audio_path,
                    output_video_path=str(output_path),
                    fps=fps,
                    timeout=timeout_per_video
                )
                output_paths.append(result)

            except Exception as e:
                logger.error(f"批量处理第{i}个失败: {e}")
                # 继续处理下一个
                continue

        logger.info(f"批量生成完成: {len(output_paths)}/{len(audio_paths)}成功")

        return output_paths

    @staticmethod
    def check_workflow_exists() -> bool:
        """
        检查workflow文件是否存在

        Returns:
            是否存在
        """
        workflow_path = settings.get_workflow_path("digital_human")

        if workflow_path.exists():
            logger.info(f"✓ 数字人生成workflow存在: {workflow_path.name}")
            return True
        else:
            logger.error(f"✗ 数字人生成workflow不存在: {workflow_path}")
            return False
