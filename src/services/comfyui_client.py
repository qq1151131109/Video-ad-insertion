"""
ComfyUI API客户端

提供与ComfyUI交互的接口，支持：
- 文件上传
- Workflow提交
- 任务状态查询
- 结果下载
"""
import json
import time
from pathlib import Path
from typing import Dict, Any, Optional, Tuple

import requests
from tqdm import tqdm

from src.config.settings import settings
from src.utils.logger import logger


class ComfyUIClient:
    """ComfyUI API客户端"""

    def __init__(self, base_url: Optional[str] = None):
        """
        初始化ComfyUI客户端

        Args:
            base_url: ComfyUI服务地址（可选，默认使用settings配置）
        """
        self.base_url = base_url or settings.comfyui_base_url
        self.session = requests.Session()
        logger.info(f"ComfyUI客户端初始化: {self.base_url}")

    def upload_file(self, file_path: str, subfolder: str = "") -> Dict[str, str]:
        """
        上传文件到ComfyUI

        Args:
            file_path: 本地文件路径
            subfolder: 子目录（可选）

        Returns:
            {"name": "filename.ext", "subfolder": "", "type": "input"}

        Raises:
            Exception: 上传失败
        """
        file_path = Path(file_path)
        # 根据扩展名选择上传端点与字段
        ext = file_path.suffix.lower()
        is_audio = ext in {".wav", ".mp3", ".flac", ".m4a", ".aac", ".ogg"}
        field_name = "audio" if is_audio else "image"
        endpoint = "audio" if is_audio else "image"
        url = f"{self.base_url}/upload/{endpoint}"

        if not file_path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")

        logger.info(f"上传文件: {file_path.name}")

        # 注意：不要在with块中打开文件，否则文件会在请求完成前关闭
        f = open(file_path, 'rb')
        try:
            files = {field_name: (file_path.name, f)}
            data = {'overwrite': 'true'}
            if subfolder:
                data['subfolder'] = subfolder

            response = self._request("POST", url, files=files, data=data)
            result = response.json()

            logger.success(f"✓ 文件上传成功: {result['name']} ({field_name})")
            return result
        finally:
            f.close()

    def submit_workflow(self, workflow: Dict[str, Any], client_id: Optional[str] = None) -> str:
        """
        提交workflow任务

        Args:
            workflow: workflow的JSON对象
            client_id: 客户端ID（可选）

        Returns:
            prompt_id: 任务ID

        Raises:
            Exception: 提交失败或workflow配置错误
        """
        url = f"{self.base_url}/prompt"

        if client_id is None:
            client_id = f"python_client_{int(time.time())}"

        payload = {
            "prompt": workflow,
            "client_id": client_id
        }

        logger.info(f"提交workflow任务 (client_id={client_id})")

        response = self._request("POST", url, json=payload)
        result = response.json()

        # 检查节点错误
        if result.get('node_errors'):
            error_msg = f"Workflow配置错误: {json.dumps(result['node_errors'], indent=2, ensure_ascii=False)}"
            logger.error(error_msg)
            raise Exception(error_msg)

        prompt_id = result['prompt_id']
        logger.success(f"✓ 任务已提交: {prompt_id}")
        return prompt_id

    def get_status(self, prompt_id: str) -> Dict[str, Any]:
        """
        查询任务状态

        Args:
            prompt_id: 任务ID

        Returns:
            任务状态和输出信息

        Raises:
            Exception: 查询失败
        """
        url = f"{self.base_url}/history/{prompt_id}"

        response = self._request("GET", url)
        history = response.json()
        return history.get(prompt_id, {})

    def wait_for_completion(
        self,
        prompt_id: str,
        timeout: int = 600,
        check_interval: int = 2,
        show_progress: bool = True
    ) -> Dict[str, Any]:
        """
        等待任务完成

        Args:
            prompt_id: 任务ID
            timeout: 超时时间（秒）
            check_interval: 检查间隔（秒）
            show_progress: 是否显示进度条

        Returns:
            完成后的输出信息

        Raises:
            TimeoutError: 超时
            Exception: 任务失败
        """
        start_time = time.time()
        logger.info(f"等待任务完成 (timeout={timeout}s)...")

        # 创建进度条
        pbar = None
        if show_progress:
            pbar = tqdm(total=timeout, desc="等待任务完成", unit="s")

        try:
            while True:
                elapsed = time.time() - start_time

                if elapsed > timeout:
                    raise TimeoutError(f"任务超时 (>{timeout}秒)")

                status = self.get_status(prompt_id)

                if not status:
                    # 任务还在队列中，未开始执行
                    time.sleep(check_interval)
                    if pbar:
                        pbar.update(check_interval)
                    continue

                status_info = status.get('status', {})

                if status_info.get('status_str') == 'success':
                    logger.success(f"✓ 任务完成 (耗时: {elapsed:.1f}秒)")
                    if pbar:
                        pbar.close()
                    return status.get('outputs', {})

                elif status_info.get('status_str') == 'error':
                    error_msg = f"任务失败: {status_info.get('messages', [])}"
                    logger.error(error_msg)
                    if pbar:
                        pbar.close()
                    raise Exception(error_msg)

                time.sleep(check_interval)
                if pbar:
                    pbar.update(check_interval)

        except KeyboardInterrupt:
            if pbar:
                pbar.close()
            logger.warning("用户中断任务")
            raise

    def download_file(
        self,
        filename: str,
        subfolder: str = "",
        output_path: Optional[str] = None
    ) -> bytes:
        """
        下载生成的文件

        Args:
            filename: 文件名
            subfolder: 子目录
            output_path: 保存路径（可选，不提供则返回字节）

        Returns:
            文件内容（字节）

        Raises:
            Exception: 下载失败
        """
        url = f"{self.base_url}/view"
        params = {
            'filename': filename,
            'type': 'output'
        }
        if subfolder:
            params['subfolder'] = subfolder

        logger.info(f"下载文件: {filename}")

        response = self._request("GET", url, params=params)
        content = response.content

        if output_path:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            with open(output_path, 'wb') as f:
                f.write(content)

            logger.success(f"✓ 文件已保存: {output_path}")

        return content

    def run_workflow_and_download(
        self,
        workflow: Dict[str, Any],
        output_node_id: str,
        output_path: str,
        timeout: int = 600,
        file_type: str = "images"
    ) -> str:
        """
        完整流程：提交workflow → 等待完成 → 下载结果

        Args:
            workflow: workflow JSON
            output_node_id: 输出节点ID（如 "60" for SaveImage）
            output_path: 保存路径
            timeout: 超时时间
            file_type: 文件类型 ("images" | "videos" | "audio")

        Returns:
            保存的文件路径

        Raises:
            Exception: 任何阶段失败
        """
        # 1. 提交任务
        prompt_id = self.submit_workflow(workflow)

        # 2. 等待完成
        outputs = self.wait_for_completion(prompt_id, timeout=timeout)

        # 3. 获取输出文件信息
        node_output = outputs.get(output_node_id, {})

        if file_type not in node_output:
            raise Exception(f"节点{output_node_id}没有{file_type}输出，可用输出: {list(node_output.keys())}")

        file_info = node_output[file_type][0]

        # 4. 下载文件
        self.download_file(
            filename=file_info['filename'],
            subfolder=file_info.get('subfolder', ''),
            output_path=output_path
        )

        return output_path

    def load_workflow(self, workflow_path: str) -> Dict[str, Any]:
        """
        从文件加载workflow配置

        Args:
            workflow_path: workflow JSON文件路径

        Returns:
            workflow字典

        Raises:
            FileNotFoundError: 文件不存在
            json.JSONDecodeError: JSON格式错误
        """
        workflow_path = Path(workflow_path)

        if not workflow_path.exists():
            raise FileNotFoundError(f"Workflow文件不存在: {workflow_path}")

        with open(workflow_path, 'r', encoding='utf-8') as f:
            workflow = json.load(f)

        logger.info(f"Workflow配置已加载: {workflow_path.name}")
        return workflow

    # ---- 内部工具：带重试与超时的HTTP请求 -----------------------------------
    def _request(self, method: str, url: str, retries: int = 5, backoff: float = 1.0, timeout: int = 30, **kwargs):
        """
        统一HTTP请求入口，增加超时、重试与错误日志。

        - 对5xx错误与连接类异常进行指数退避重试
        - 默认添加 'Connection: close' 以避免某些反向代理的keep-alive问题
        """
        headers = kwargs.pop("headers", {}) or {}
        headers.setdefault("Connection", "close")

        import random
        for attempt in range(1, retries + 1):
            try:
                resp = requests.request(method, url, headers=headers, timeout=timeout, **kwargs)
                if resp.status_code >= 500:
                    raise requests.HTTPError(f"{resp.status_code} Server Error", response=resp)
                return resp
            except (requests.HTTPError, requests.ConnectionError, requests.Timeout) as e:
                if attempt >= retries:
                    # 打印更多细节
                    try:
                        text = e.response.text[:500] if isinstance(e, requests.HTTPError) and e.response is not None else str(e)
                        logger.error(f"HTTP请求失败({method} {url})：{text}")
                    except Exception:
                        logger.error(f"HTTP请求失败({method} {url})：{e}")
                    raise
                # 指数退避 + 随机抖动，减少瞬时拥塞
                sleep_s = backoff * attempt + random.uniform(0, 0.5)
                logger.warning(f"请求失败({method} {url})，{sleep_s:.1f}s后重试({attempt}/{retries})……")
                time.sleep(sleep_s)
