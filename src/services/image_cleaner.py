"""
图片清洗服务

使用Qwen Image Edit workflow清洗关键帧图片（去除文字、水印等干扰元素）
"""
import json
from pathlib import Path
from typing import Optional, Dict, Any

from src.services.comfyui_client import ComfyUIClient
from src.config.settings import settings
from src.utils.logger import logger


class ImageCleanerService:
    """图片清洗服务（基于Qwen Image Edit）"""

    def __init__(self, client: Optional[ComfyUIClient] = None):
        """
        初始化图片清洗服务

        Args:
            client: ComfyUI客户端（None则自动创建）
        """
        self.client = client or ComfyUIClient()
        self.workflow_path = settings.get_workflow_path("image_edit")

        # 加载workflow配置
        self._workflow_template: Optional[Dict] = None

        logger.info("图片清洗服务初始化")

    def _load_workflow_template(self) -> Dict:
        """
        加载workflow模板

        Returns:
            workflow配置字典
        """
        if self._workflow_template is None:
            logger.info(f"加载图片清洗workflow: {self.workflow_path.name}")

            with open(self.workflow_path, 'r', encoding='utf-8') as f:
                self._workflow_template = json.load(f)

            logger.debug(f"Workflow节点数: {len(self._workflow_template)}")

        return self._workflow_template

    def clean_image(
        self,
        input_image_path: str,
        output_image_path: str,
        prompt: str = "去除图片中的文字、水印和干扰元素，保持人物和背景清晰自然",
        negative_prompt: str = "文字、水印、logo、字幕",
        output_node_id: str = "9",  # 根据实际workflow调整
        timeout: int = 300
    ) -> str:
        """
        清洗图片

        Args:
            input_image_path: 输入图片路径
            output_image_path: 输出图片路径
            prompt: 正向提示词（描述期望的结果）
            negative_prompt: 负向提示词（描述要去除的内容）
            output_node_id: workflow输出节点ID
            timeout: 超时时间（秒）

        Returns:
            输出图片路径

        Raises:
            FileNotFoundError: 输入图片不存在
            Exception: 处理失败
        """
        input_path = Path(input_image_path)
        output_path = Path(output_image_path)

        if not input_path.exists():
            raise FileNotFoundError(f"输入图片不存在: {input_path}")

        logger.info(f"开始图片清洗: {input_path.name}")
        logger.info(f"提示词: {prompt}")

        try:
            # 1. 上传图片到ComfyUI
            logger.info("上传图片到ComfyUI...")
            # 为避免远端PIL解析JPEG异常，统一转为PNG再上传
            try:
                from PIL import Image
                tmp_upload_path = input_path.parent / f"{input_path.stem}_upload.png"
                with Image.open(input_path) as im:
                    if im.mode not in ("RGB", "RGBA"):
                        im = im.convert("RGB")
                    im.save(tmp_upload_path, format="PNG")
                upload_target = tmp_upload_path
                logger.debug(f"已转换为PNG用于上传: {upload_target.name}")
            except Exception as conv_e:
                logger.warning(f"PNG转码失败，回退原图上传: {conv_e}")
                upload_target = input_path

            uploaded = self.client.upload_file(str(upload_target))
            uploaded_filename = uploaded.get("name")

            if not uploaded_filename:
                raise Exception("图片上传失败")

            logger.success(f"✓ 图片已上传: {uploaded_filename}")

            # 2. 准备workflow
            workflow = self._prepare_workflow(
                image_filename=uploaded_filename,
                prompt=prompt,
                negative_prompt=negative_prompt
            )

            # 3. 执行workflow并下载结果
            logger.info("执行图片清洗workflow...")

            result_path = self.client.run_workflow_and_download(
                workflow=workflow,
                output_node_id=output_node_id,
                output_path=str(output_path),
                timeout=timeout
            )

            logger.success(f"✓ 图片清洗完成: {output_path.name}")

            return result_path

        except Exception as e:
            logger.error(f"图片清洗失败: {e}")
            raise

    def _prepare_workflow(
        self,
        image_filename: str,
        prompt: str,
        negative_prompt: str
    ) -> Dict[str, Any]:
        """
        准备workflow（替换参数）

        根据新的workflow结构（qwen_image_edit-api-1114.json）：
        - 节点78: LoadImage - 输入图片
        - 节点76: TextEncodeQwenImageEdit - 正向提示词
        - 节点77: TextEncodeQwenImageEdit - 负向提示词

        Args:
            image_filename: 上传后的图片文件名
            prompt: 正向提示词
            negative_prompt: 负向提示词

        Returns:
            准备好的workflow配置
        """
        import copy

        # 加载模板（深拷贝）
        workflow = copy.deepcopy(self._load_workflow_template())

        # 查找并替换图片输入节点
        for node_id, node in workflow.items():
            if not isinstance(node, dict):
                continue

            class_type = node.get("class_type", "")

            # LoadImage节点 - 设置输入图片
            if class_type == "LoadImage":
                if "inputs" in node:
                    node["inputs"]["image"] = image_filename
                    logger.debug(f"设置图片输入: {image_filename} (节点{node_id})")

            # TextEncodeQwenImageEdit节点 - 设置提示词
            elif class_type == "TextEncodeQwenImageEdit":
                if "inputs" in node:
                    current_prompt = node["inputs"].get("prompt", "")
                    # 根据当前prompt是否为空来判断是正向还是负向
                    if current_prompt:  # 非空的是正向提示词
                        node["inputs"]["prompt"] = prompt
                        logger.debug(f"设置正向提示词 (节点{node_id}): {prompt[:30]}...")
                    else:  # 空的是负向提示词
                        node["inputs"]["prompt"] = negative_prompt
                        logger.debug(f"设置负向提示词 (节点{node_id}): {negative_prompt[:30]}...")

        return workflow

    def clean_image_simple(
        self,
        input_image_path: str,
        output_image_path: str,
        remove_text: bool = True,
        remove_watermark: bool = True,
        timeout: int = 300
    ) -> str:
        """
        简化的图片清洗接口

        Args:
            input_image_path: 输入图片路径
            output_image_path: 输出图片路径
            remove_text: 是否去除文字
            remove_watermark: 是否去除水印
            timeout: 超时时间

        Returns:
            输出图片路径
        """
        # 构建提示词
        prompt_parts = ["保持人物和背景清晰自然"]
        negative_parts = []

        if remove_text:
            negative_parts.append("文字")
            negative_parts.append("字幕")

        if remove_watermark:
            negative_parts.append("水印")
            negative_parts.append("logo")

        if negative_parts:
            prompt_parts.insert(0, f"去除图片中的{' '.join(negative_parts)}")

        prompt = "，".join(prompt_parts)
        negative_prompt = "、".join(negative_parts)

        return self.clean_image(
            input_image_path=input_image_path,
            output_image_path=output_image_path,
            prompt=prompt,
            negative_prompt=negative_prompt,
            timeout=timeout
        )

    @staticmethod
    def check_workflow_exists() -> bool:
        """
        检查workflow文件是否存在

        Returns:
            是否存在
        """
        workflow_path = settings.get_workflow_path("image_edit")

        if workflow_path.exists():
            logger.info(f"✓ 图片清洗workflow存在: {workflow_path.name}")
            return True
        else:
            logger.error(f"✗ 图片清洗workflow不存在: {workflow_path}")
            return False
