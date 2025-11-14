# ComfyUI API 调用说明

## 服务信息

- **服务地址**: `http://103.231.86.148:9000`
- **服务类型**: 标准ComfyUI实例
- **Workflow配置**: 已有3个JSON文件

---

## ComfyUI API 端点

### 1. 提交Workflow任务

**端点**: `POST /prompt`

**请求格式**:
```json
{
  "prompt": {
    // workflow的完整JSON内容
    "节点ID": {
      "inputs": {...},
      "class_type": "...",
      ...
    }
  },
  "client_id": "唯一客户端ID（可选）"
}
```

**响应格式**:
```json
{
  "prompt_id": "uuid-string",  // 任务ID，用于查询状态
  "number": 123,               // 队列编号
  "node_errors": {}            // 节点错误（如有）
}
```

---

### 2. 查询任务状态和结果

**端点**: `GET /history/{prompt_id}`

**响应格式**:
```json
{
  "prompt_id": {
    "prompt": [...],
    "outputs": {
      "节点ID": {
        "images": [
          {
            "filename": "生成的文件名.png",
            "subfolder": "子目录",
            "type": "output"
          }
        ],
        "audio": [...],  // 音频文件
        "videos": [...]  // 视频文件
      }
    },
    "status": {
      "status_str": "success",  // success | error | pending
      "completed": true,
      "messages": []
    }
  }
}
```

---

### 3. 下载生成的文件

**端点**: `GET /view`

**参数**:
- `filename`: 文件名（从history获取）
- `subfolder`: 子目录（可选）
- `type`: 文件类型（output | input | temp）

**示例**:
```
GET /view?filename=ComfyUI_00001_.png&type=output
```

**响应**: 文件的二进制内容

---

### 4. 上传文件

**端点**: `POST /upload/image`

**请求格式**: `multipart/form-data`
```
image: <文件内容>
overwrite: true/false (可选)
subfolder: 子目录 (可选)
```

**响应格式**:
```json
{
  "name": "上传后的文件名.png",
  "subfolder": "",
  "type": "input"
}
```

**说明**:
- 音频文件也使用此端点（尽管路径是/upload/image）
- 上传后的文件可以在workflow中通过filename引用

---

### 5. WebSocket实时进度（可选）

**端点**: `ws://103.231.86.148:9000/ws?clientId={client_id}`

**消息类型**:
```json
{
  "type": "status",
  "data": {
    "status": {
      "exec_info": {
        "queue_remaining": 0
      }
    }
  }
}

{
  "type": "executing",
  "data": {
    "node": "节点ID",
    "prompt_id": "任务ID"
  }
}

{
  "type": "executed",
  "data": {
    "node": "节点ID",
    "output": {...}
  }
}
```

---

## Python客户端实现示例

### 基础客户端类

```python
import json
import time
import requests
from typing import Dict, Any, Optional
from pathlib import Path

class ComfyUIClient:
    def __init__(self, host: str = "103.231.86.148", port: int = 9000, protocol: str = "http"):
        self.base_url = f"{protocol}://{host}:{port}"
        self.session = requests.Session()

    def upload_file(self, file_path: str, subfolder: str = "") -> Dict[str, str]:
        """
        上传文件到ComfyUI

        Args:
            file_path: 本地文件路径
            subfolder: 子目录（可选）

        Returns:
            {"name": "filename.ext", "subfolder": "", "type": "input"}
        """
        url = f"{self.base_url}/upload/image"

        with open(file_path, 'rb') as f:
            files = {'image': (Path(file_path).name, f)}
            data = {'overwrite': 'true'}
            if subfolder:
                data['subfolder'] = subfolder

            response = self.session.post(url, files=files, data=data)
            response.raise_for_status()
            return response.json()

    def submit_workflow(self, workflow: Dict[str, Any]) -> str:
        """
        提交workflow任务

        Args:
            workflow: workflow的JSON对象

        Returns:
            prompt_id: 任务ID
        """
        url = f"{self.base_url}/prompt"

        payload = {
            "prompt": workflow,
            "client_id": f"python_client_{int(time.time())}"
        }

        response = self.session.post(url, json=payload)
        response.raise_for_status()

        result = response.json()
        if result.get('node_errors'):
            raise Exception(f"Workflow错误: {result['node_errors']}")

        return result['prompt_id']

    def get_status(self, prompt_id: str) -> Dict[str, Any]:
        """
        查询任务状态

        Args:
            prompt_id: 任务ID

        Returns:
            任务状态和输出信息
        """
        url = f"{self.base_url}/history/{prompt_id}"

        response = self.session.get(url)
        response.raise_for_status()

        history = response.json()
        return history.get(prompt_id, {})

    def wait_for_completion(self, prompt_id: str, timeout: int = 600, check_interval: int = 2) -> Dict[str, Any]:
        """
        等待任务完成

        Args:
            prompt_id: 任务ID
            timeout: 超时时间（秒）
            check_interval: 检查间隔（秒）

        Returns:
            完成后的输出信息

        Raises:
            TimeoutError: 超时
            Exception: 任务失败
        """
        start_time = time.time()

        while True:
            if time.time() - start_time > timeout:
                raise TimeoutError(f"任务超时 (>{timeout}秒)")

            status = self.get_status(prompt_id)

            if not status:
                # 任务还在队列中，未开始执行
                time.sleep(check_interval)
                continue

            status_info = status.get('status', {})

            if status_info.get('status_str') == 'success':
                return status.get('outputs', {})
            elif status_info.get('status_str') == 'error':
                raise Exception(f"任务失败: {status_info.get('messages', [])}")

            time.sleep(check_interval)

    def download_file(self, filename: str, subfolder: str = "", output_path: str = None) -> bytes:
        """
        下载生成的文件

        Args:
            filename: 文件名
            subfolder: 子目录
            output_path: 保存路径（可选，不提供则返回字节）

        Returns:
            文件内容（字节）
        """
        url = f"{self.base_url}/view"
        params = {
            'filename': filename,
            'type': 'output'
        }
        if subfolder:
            params['subfolder'] = subfolder

        response = self.session.get(url, params=params)
        response.raise_for_status()

        content = response.content

        if output_path:
            with open(output_path, 'wb') as f:
                f.write(content)

        return content

    def run_workflow_and_download(self,
                                   workflow: Dict[str, Any],
                                   output_node_id: str,
                                   output_path: str,
                                   timeout: int = 600) -> str:
        """
        完整流程：提交workflow → 等待完成 → 下载结果

        Args:
            workflow: workflow JSON
            output_node_id: 输出节点ID（如 "60" for SaveImage）
            output_path: 保存路径
            timeout: 超时时间

        Returns:
            保存的文件路径
        """
        # 1. 提交任务
        prompt_id = self.submit_workflow(workflow)
        print(f"✓ 任务已提交: {prompt_id}")

        # 2. 等待完成
        outputs = self.wait_for_completion(prompt_id, timeout=timeout)
        print(f"✓ 任务完成")

        # 3. 获取输出文件信息
        node_output = outputs.get(output_node_id, {})

        # 根据输出类型获取文件信息
        if 'images' in node_output:
            file_info = node_output['images'][0]
        elif 'videos' in node_output:
            file_info = node_output['videos'][0]
        elif 'audio' in node_output:
            file_info = node_output['audio'][0]
        else:
            raise Exception(f"节点{output_node_id}没有输出文件")

        # 4. 下载文件
        self.download_file(
            filename=file_info['filename'],
            subfolder=file_info.get('subfolder', ''),
            output_path=output_path
        )
        print(f"✓ 文件已保存: {output_path}")

        return output_path
```

---

## 使用示例

### 示例1: 图片清洗（Qwen Image Edit）

```python
import json
from pathlib import Path

# 初始化客户端
client = ComfyUIClient()

# 1. 上传图片
uploaded = client.upload_file("keyframe.jpg")
print(f"上传成功: {uploaded['name']}")

# 2. 加载workflow模板
with open('docs/workflow/qwen_image_edit.json', 'r', encoding='utf-8') as f:
    workflow = json.load(f)

# 3. 修改workflow参数
# 找到LoadImage节点（假设是节点78）
workflow['78']['inputs']['image'] = uploaded['name']

# 找到TextEncode节点（假设是节点76），设置提示词
workflow['76']['widgets_values'][0] = "去除字幕、水印、文字"

# 4. 提交并下载
output_path = client.run_workflow_and_download(
    workflow=workflow,
    output_node_id='60',  # SaveImage节点ID
    output_path='output/cleaned_image.png',
    timeout=300
)

print(f"✓ 图片清洗完成: {output_path}")
```

---

### 示例2: 声音克隆（IndexTTS2）

```python
# 1. 上传参考音频
ref_audio = client.upload_file("voice_sample.mp3")

# 2. 加载workflow
with open('docs/workflow/index TTS2情绪控制_api_1013.json', 'r') as f:
    workflow = json.load(f)

# 3. 修改参数
workflow['101']['inputs']['audio'] = ref_audio['name']  # LoadAudio节点
workflow['102']['inputs']['multi_line_prompt'] = "这得益于NVIDIA强大的算力支持"  # 文本

# 4. 执行
output_path = client.run_workflow_and_download(
    workflow=workflow,
    output_node_id='173',  # SaveAudioMP3节点
    output_path='output/cloned_voice.mp3',
    timeout=300
)
```

---

### 示例3: 数字人视频生成（InfiniteTalk）

```python
# 1. 上传图片和音频
image = client.upload_file("cleaned_person.jpg")
audio = client.upload_file("cloned_voice.mp3")

# 2. 加载workflow
with open('docs/workflow/InfiniteTalk数字人视频生视频_api.json', 'r') as f:
    workflow = json.load(f)

# 3. 修改参数
workflow['315']['inputs']['image'] = image['name']  # LoadImage节点
workflow['125']['inputs']['audio'] = audio['name']  # LoadAudio节点

# 可能需要调整的其他参数：
# - 分辨率 (节点304, 305)
# - 帧率 (节点306)
# - 提示词 (节点311)

# 4. 执行（数字人生成较慢，timeout设置长一些）
output_path = client.run_workflow_and_download(
    workflow=workflow,
    output_node_id='324',  # VideoCombine节点
    output_path='output/digital_human.mp4',
    timeout=600
)
```

---

## 注意事项

### 1. Workflow节点ID查找

每个workflow的节点ID不同，需要从JSON文件中查找：

```json
{
  "78": {  // ← 这是节点ID
    "inputs": {
      "image": "example.jpg"
    },
    "class_type": "LoadImage"  // ← 节点类型
  }
}
```

**常见节点类型**:
- `LoadImage`: 加载图片
- `LoadAudio`: 加载音频
- `SaveImage`: 保存图片
- `SaveAudioMP3`: 保存音频
- `VHS_VideoCombine`: 保存视频

### 2. 文件路径处理

- 上传的文件会保存在ComfyUI的`input`目录
- 生成的文件在`output`目录
- Workflow中只需要文件名，不需要完整路径

### 3. 错误处理

常见错误：
- `node_errors`: Workflow配置错误（节点参数不匹配）
- 超时: 任务执行时间过长
- 文件未找到: 上传的文件名在workflow中未正确引用

### 4. 性能优化

- 复用session（已在ComfyUIClient中实现）
- 合理设置timeout（图片<5分钟，音频<5分钟，视频<10分钟）
- 可以并发提交多个独立任务

---

## 调试技巧

### 1. 查看ComfyUI日志

SSH到服务器查看ComfyUI的运行日志：
```bash
ssh user@103.231.86.148
# 查看ComfyUI进程日志
```

### 2. 在浏览器中测试

访问 `http://103.231.86.148:9000` 可以看到ComfyUI的Web界面，可以：
- 手动运行workflow验证配置
- 查看队列状态
- 检查生成的文件

### 3. 使用curl测试API

```bash
# 查看队列
curl http://103.231.86.148:9000/queue

# 查看历史
curl http://103.231.86.148:9000/history

# 提交任务
curl -X POST http://103.231.86.148:9000/prompt \
  -H "Content-Type: application/json" \
  -d @workflow.json
```

---

**文档版本**: v1.0
**更新时间**: 2025-11-14
