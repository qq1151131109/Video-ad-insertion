"""
声音克隆服务

使用IndexTTS2 workflow克隆原视频人物的声音，生成广告配音
"""
import json
from pathlib import Path
from typing import Optional, Dict, Any

from src.services.comfyui_client import ComfyUIClient
from src.config.settings import settings
from src.utils.logger import logger


class VoiceCloneService:
    """声音克隆服务（基于IndexTTS2）"""

    def __init__(self, client: Optional[ComfyUIClient] = None):
        """
        初始化声音克隆服务

        Args:
            client: ComfyUI客户端（None则自动创建）
        """
        self.client = client or ComfyUIClient()
        self.workflow_path = settings.get_workflow_path("voice_clone")

        # 加载workflow配置
        self._workflow_template: Optional[Dict] = None

        logger.info("声音克隆服务初始化")

    def _load_workflow_template(self) -> Dict:
        """
        加载workflow模板

        Returns:
            workflow配置字典
        """
        if self._workflow_template is None:
            logger.info(f"加载声音克隆workflow: {self.workflow_path.name}")

            with open(self.workflow_path, 'r', encoding='utf-8') as f:
                self._workflow_template = json.load(f)

            logger.debug(f"Workflow节点数: {len(self._workflow_template)}")

        return self._workflow_template

    def clone_voice(
        self,
        reference_audio_path: str,
        text: str,
        output_audio_path: str,
        emotion: str = "neutral",
        speed: float = 1.0,
        output_node_id: str = "173",  # SaveAudioMP3节点
        timeout: int = 300
    ) -> str:
        """
        克隆声音并生成语音

        Args:
            reference_audio_path: 参考音频路径（人声样本）
            text: 要生成的文本内容
            output_audio_path: 输出音频路径
            emotion: 情绪控制（neutral/happy/sad等，根据模型支持）
            speed: 语速控制（1.0为正常）
            output_node_id: workflow输出节点ID
            timeout: 超时时间（秒）

        Returns:
            输出音频路径

        Raises:
            FileNotFoundError: 参考音频不存在
            Exception: 处理失败
        """
        reference_path = Path(reference_audio_path)
        output_path = Path(output_audio_path)

        if not reference_path.exists():
            raise FileNotFoundError(f"参考音频不存在: {reference_path}")

        logger.info(f"开始声音克隆: {reference_path.name}")
        logger.info(f"生成文本: {text}")
        logger.info(f"情绪: {emotion}, 语速: {speed}")

        try:
            # 1. 上传参考音频到ComfyUI
            logger.info("上传参考音频到ComfyUI...")
            uploaded = self.client.upload_file(str(reference_path))
            uploaded_filename = uploaded.get("name")

            if not uploaded_filename:
                raise Exception("音频上传失败")

            logger.success(f"✓ 音频已上传: {uploaded_filename}")

            # 2. 准备workflow
            workflow = self._prepare_workflow(
                audio_filename=uploaded_filename,
                text=text,
                emotion=emotion,
                speed=speed
            )

            # 3. 执行workflow并下载结果
            logger.info("执行声音克隆workflow...")

            result_path = self.client.run_workflow_and_download(
                workflow=workflow,
                output_node_id=output_node_id,
                output_path=str(output_path),
                timeout=timeout,
                file_type='audio'  # 声音克隆输出音频文件
            )

            logger.success(f"✓ 声音克隆完成: {output_path.name}")

            return result_path

        except Exception as e:
            logger.error(f"声音克隆失败: {e}")
            raise

    def _prepare_workflow(
        self,
        audio_filename: str,
        text: str,
        emotion: str,
        speed: float
    ) -> Dict[str, Any]:
        """
        准备workflow（替换参数）

        根据新的workflow结构（index TTS2-1114-API.json）：
        - 节点101: LoadAudio - 参考音频
        - 节点102: MultiLinePromptIndex - 输入文本
        - 节点103: IndexTTS2Run - TTS运行（包含情绪参数）

        Args:
            audio_filename: 上传后的音频文件名
            text: 生成文本
            emotion: 情绪（暂不支持，保留参数）
            speed: 语速（暂不支持，保留参数）

        Returns:
            准备好的workflow配置
        """
        import copy

        # 加载模板（深拷贝）
        workflow = copy.deepcopy(self._load_workflow_template())

        # 查找并替换参数节点
        for node_id, node in workflow.items():
            if not isinstance(node, dict):
                continue

            class_type = node.get("class_type", "")

            # LoadAudio节点 - 设置参考音频
            if class_type == "LoadAudio":
                if "inputs" in node:
                    node["inputs"]["audio"] = audio_filename
                    logger.debug(f"设置音频输入: {audio_filename} (节点{node_id})")

            # MultiLinePromptIndex节点 - 设置文本输入
            elif class_type == "MultiLinePromptIndex":
                if "inputs" in node:
                    node["inputs"]["multi_line_prompt"] = text
                    logger.debug(f"设置文本输入 (节点{node_id}): {text[:50]}...")

            # IndexTTS2Run节点 - TTS参数（目前保持默认）
            elif class_type == "IndexTTS2Run":
                if "inputs" in node:
                    # 注：当前workflow的IndexTTS2Run节点通过emo_vector等参数控制情绪
                    # 暂时保持默认值，如需自定义可以在这里修改
                    logger.debug(f"IndexTTS2Run节点 (节点{node_id}) - 使用默认参数")

        return workflow

    def clone_voice_simple(
        self,
        reference_audio_path: str,
        text: str,
        output_audio_path: str,
        timeout: int = 300
    ) -> str:
        """
        简化的声音克隆接口（使用默认参数）

        Args:
            reference_audio_path: 参考音频路径
            text: 要生成的文本
            output_audio_path: 输出音频路径
            timeout: 超时时间

        Returns:
            输出音频路径
        """
        return self.clone_voice(
            reference_audio_path=reference_audio_path,
            text=text,
            output_audio_path=output_audio_path,
            emotion="neutral",
            speed=1.0,
            timeout=timeout
        )

    def batch_clone(
        self,
        reference_audio_path: str,
        texts: list[str],
        output_dir: str,
        emotion: str = "neutral",
        speed: float = 1.0,
        timeout_per_text: int = 300
    ) -> list[str]:
        """
        批量克隆声音

        Args:
            reference_audio_path: 参考音频路径
            texts: 文本列表
            output_dir: 输出目录
            emotion: 情绪
            speed: 语速
            timeout_per_text: 每个文本的超时时间

        Returns:
            输出音频路径列表
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"批量声音克隆: {len(texts)}个文本")

        output_paths = []

        for i, text in enumerate(texts, 1):
            output_path = output_dir / f"cloned_voice_{i:03d}.wav"

            logger.info(f"处理 {i}/{len(texts)}: {text[:30]}...")

            try:
                result = self.clone_voice(
                    reference_audio_path=reference_audio_path,
                    text=text,
                    output_audio_path=str(output_path),
                    emotion=emotion,
                    speed=speed,
                    timeout=timeout_per_text
                )
                output_paths.append(result)

            except Exception as e:
                logger.error(f"批量处理第{i}个失败: {e}")
                # 继续处理下一个
                continue

        logger.info(f"批量克隆完成: {len(output_paths)}/{len(texts)}成功")

        return output_paths

    @staticmethod
    def check_workflow_exists() -> bool:
        """
        检查workflow文件是否存在

        Returns:
            是否存在
        """
        workflow_path = settings.get_workflow_path("voice_clone")

        if workflow_path.exists():
            logger.info(f"✓ 声音克隆workflow存在: {workflow_path.name}")
            return True
        else:
            logger.error(f"✗ 声音克隆workflow不存在: {workflow_path}")
            return False
