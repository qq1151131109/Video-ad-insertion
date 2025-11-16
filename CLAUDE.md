# CLAUDE.md

本文件为 Claude Code (claude.ai/code) 在此仓库中工作时提供指导。

## 项目概述

这是一个基于AI的视频处理系统，能够智能地在短视频中插入数字人广告。系统分析视频内容，使用LLM识别插入点，克隆说话者的声音，并通过ComfyUI工作流生成自然逼真的数字人广告。

**技术栈**: Python 3.9+, OpenAI Whisper (ASR), OpenAI API (LLM), ComfyUI (图像/声音/视频生成), Demucs (音频分离), MTCNN (人脸检测), MoviePy (视频编辑)

## 常用命令

### 开发命令
```bash
# 激活虚拟环境
source .venv/bin/activate  # Linux/Mac
# 或
.venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt

# 处理单个视频
python main.py input/video.mp4

# 批量处理视频
python main.py input/ --batch

# 指定自定义输出目录
python main.py input/video.mp4 -o output/my_custom_output

# 使用CPU而非GPU
python main.py input/video.mp4 --device cpu
```

### 测试命令
```bash
# 运行所有单元测试
pytest tests/

# 测试ComfyUI连接
python scripts/test_comfyui.py

# 测试视频处理
python scripts/test_video_processor.py

# 测试音频分离（首次运行会下载约2GB的Demucs模型）
python scripts/test_audio_separator.py

# 测试ASR和LLM集成
python scripts/test_asr_llm.py

# 测试人脸检测（首次运行会下载MTCNN模型）
python scripts/test_face_detector.py

# 测试ComfyUI工作流（需要ComfyUI服务器运行）
python scripts/test_workflows.py

# 测试视频合成
python scripts/test_video_composer.py

# 端到端测试（完整流程）
python scripts/test_end_to_end.py
```

## 架构概览

### 5阶段处理流水线 (`src/core/pipeline.py`)

系统遵循严格的5阶段顺序流水线（阶段2.5为新增场景分析）：

1. **视频分析** (`video_processor.py`, `audio_separator.py`)
   - 提取元数据（时长、分辨率、帧率）
   - 从视频中提取音频
   - 使用Demucs分离人声

2. **内容理解** (`asr.py`, `llm_service.py`)
   - 使用Whisper转录语音（词级时间戳）
   - 使用LLM分析视频内容（主题、类别、语气）
   - 识别最佳广告插入点（多候选点，带优先级）

2.5. **场景分析** (`speaker_detector.py`) - 新增
   - 分析视频是否为单人口播场景
   - 识别主讲人并建立档案（位置、大小、出现频率）
   - 为后续插入点选择提供主讲人信息

3. **广告准备** (`face_detector.py`, `ads.py`)
   - **智能三级插入点选择策略**：
     1. 优先：在LLM推荐的点中找有主讲人的画面
     2. 降级：如果LLM推荐点都没人脸，使用主讲人最佳帧
     3. 兜底：完全找不到合适人脸则报错
   - 综合评分：语义优先级(40%) + 人脸质量(60%)
   - 从配置中选择匹配的广告
   - 使用LLM生成上下文相关的广告词

4. **数字人生成** (`ad_orchestrator.py`)
   - **三步ComfyUI工作流**（带重试机制）：
     1. 图片清洗（Qwen Image Edit - 去除文字/水印，2次重试，失败降级到原图）
     2. 声音克隆（IndexTTS2 - 克隆说话者声音，2次重试）
     3. 数字人视频（InfiniteTalk - 生成说话的数字人，2次重试）

5. **视频合成** (`video_composer.py`)
   - 在插入点分割原视频
   - 插入数字人广告视频
   - 合并片段生成最终输出

### 核心服务架构

**ComfyUI集成** (`src/services/`):
- `comfyui_client.py`: 核心API客户端（上传、提交、轮询、下载）
  - **HTTP重试机制**: 5次重试，指数退避，处理5xx和连接错误
  - **连接管理**: 默认 `Connection: close` 避免keep-alive问题
  - **超时控制**: 默认30秒超时
- `image_cleaner.py`: Qwen Image Edit工作流封装
- `voice_clone.py`: IndexTTS2工作流封装
- `digital_human.py`: InfiniteTalk工作流封装
- `ad_orchestrator.py`: 按序编排所有3个工作流

**ComfyUI API模式**:
1. 上传文件（图片/音频）→ 返回 `{"name": "filename", "type": "input"}`
   - **注意**: 音频文件也使用 `/upload/image` 端点，字段名统一为 `image`
2. 加载工作流JSON，使用上传的文件名更新节点输入
3. 提交工作流 → 返回 `prompt_id`
4. 轮询 `/history/{prompt_id}` 直到 `status_str == "success"`
5. 从节点输出中提取输出文件名，通过 `/view` 下载

**重要提示**: 系统使用 `docs/workflow/` 中的**工作流JSON文件**，其中包含硬编码的节点ID。修改工作流时，确保节点ID与JSON结构匹配。

### 配置系统

**环境变量** (`.env`):
- `OPENAI_API_KEY`, `OPENAI_BASE_URL`, `OPENAI_MODEL` - LLM服务
- `COMFYUI_HOST`, `COMFYUI_PORT`, `COMFYUI_PROTOCOL` - ComfyUI服务器
- `WORKFLOW_IMAGE_EDIT`, `WORKFLOW_VOICE_CLONE`, `WORKFLOW_DIGITAL_HUMAN` - 工作流路径

**广告配置** (`config/ads.json`):
- 完全可配置的广告内容（不限于NVIDIA）
- 每个广告包含：id, name, product, selling_points, target_scenarios, templates
- LLM使用selling_points生成上下文相关的广告词
- 系统通过匹配视频主题到target_scenarios来选择广告

### 文件管理 (`src/utils/file_manager.py`)

**TempFileManager** 上下文管理器:
- 为每个视频创建唯一的临时目录（使用视频ID）
- 提供结构化路径：audio/, keyframes/, transcriptions/, ad_materials/
- **自动保存调试产物**: 退出时自动复制所有中间结果到 `output/debug/{video_id}_{timestamp}/`，包含README说明
- 成功时自动清理cache，错误时保留文件（用于调试）
- 使用模式：`with TempFileManager(video_id) as file_mgr:`

### 错误处理模式

**带降级的工作流重试** (`ad_orchestrator.py`):
- 图片清洗：2次重试，失败时回退到原图（非关键）
- 声音克隆：2次重试（质量关键，失败则整体失败）
- 数字人生成：2次重试（最昂贵的操作，失败则整体失败）
- 重试间隔：指数退避 (2s, 4s, 6s...)

**视频验证** (`pipeline.py`):
- 最小时长：15秒，最大时长：300秒（可在settings中配置）
- 处理开始前执行检查

**主讲人检测降级** (`pipeline.py`):
- 如果视频不是单人口播，发出警告但继续处理
- 三级插入点选择策略确保即使检测失败也能找到可用画面

## 重要实现细节

### 主讲人检测与智能插入点选择

**主讲人检测** (`speaker_detector.py`):
- 每5秒采样一帧，识别出现频率>50%的人脸为主讲人
- 建立主讲人档案：平均位置、大小、置信度、最佳帧
- 判定标准：中央区域、最小人脸尺寸、位置稳定性

**三级插入点选择策略** (`pipeline.py: _select_insertion_with_speaker`):
1. **策略1（最优）**: 在LLM推荐的候选点中寻找有主讲人的画面
   - 综合评分 = 语义优先级(40%) + 人脸置信度(60%)
   - 选择得分最高的点
2. **策略2（降级）**: 如果LLM推荐点都没合适人脸，使用主讲人的最佳帧
   - 时间上使用主讲人最佳帧的时间戳
   - 语义上仍使用LLM推荐的第一个点
3. **策略3（兜底）**: 完全找不到合适人脸则报错，建议使用单人口播视频

### ComfyUI工作流节点ID
每个工作流JSON都有特定的节点ID，必须正确引用：
- 通过检查工作流JSON文件查找节点ID
- 常见模式：LoadImage, LoadAudio, SaveImage, SaveAudioMP3, VHS_VideoCombine
- 节点ID是工作流特定的（例如，一个工作流中的LoadImage是"78"，另一个可能是"315"）

### 模型下载（首次运行）
以下模型在首次使用时自动下载：
- Whisper: ~1.5GB（默认medium模型）
- Demucs: ~2GB（htdemucs模型）
- MTCNN: ~5MB
- 总计：预计约4GB初始下载

### 处理时间预期
对于30秒视频（使用GPU加速）：
- 音频分离：1-1.5分钟
- ASR：1-2分钟
- LLM分析：10-30秒
- 场景分析：30秒-1分钟
- 图片清洗：1-2分钟
- 声音克隆：2-3分钟
- 数字人生成：3-5分钟
- 视频合成：30秒
- **总计：8-15分钟**

### 关键依赖
- **ComfyUI服务器必须运行**在配置的host:port上，用于阶段4
- **需要GPU**用于Whisper（ASR）和Demucs（音频分离）- 可使用 `--device cpu` 但会显著变慢
- **推荐NVIDIA GPU**，12GB+显存以获得最佳性能

## 代码模式

### 日志记录
使用 `src.utils.logger` 中的 `loguru` 日志器：
```python
from src.utils.logger import logger

logger.info("Processing...")
logger.success("✓ Done")
logger.error("❌ Failed")
logger.warning("⚠️  Warning")
```

### 配置访问
```python
from src.config.settings import settings

# 访问配置
base_url = settings.comfyui_base_url
workflow_path = settings.get_workflow_path("image_edit")
```

### 视频处理模式
```python
from src.core.video_processor import VideoProcessor

with VideoProcessor(video_path) as processor:
    metadata = processor.extract_metadata()
    audio_path = processor.extract_audio(output_path)
    frame, time = processor.extract_best_frame_around_time(target_time)
```

### ComfyUI工作流执行
```python
# 1. 上传文件
image_info = client.upload_file("image.jpg")  # 返回 {"name": "image_xxx.jpg"}
audio_info = client.upload_file("audio.mp3")

# 2. 加载并修改工作流
with open(workflow_path) as f:
    workflow = json.load(f)
workflow[node_id]['inputs']['image'] = image_info['name']

# 3. 提交并等待
prompt_id = client.submit_workflow(workflow)
outputs = client.wait_for_completion(prompt_id, timeout=300)

# 4. 下载结果
file_info = outputs[output_node_id]['images'][0]  # 或 'videos', 'audio'
client.download_file(file_info['filename'], output_path=save_path)
```

## ComfyUI服务器信息

**服务器**: `http://103.231.86.148:9000`
**Web界面**: 在上述URL可访问，用于手动测试
**系统状态**: `curl -s http://103.231.86.148:9000/system_stats`

**可用工作流**:
1. `qwen_image_edit-api-1114.json` - Qwen Image Edit（文字/水印去除）
2. `index TTS2-1114-API.json` - IndexTTS2（带情绪控制的声音克隆）
3. `InfiniteTalk数字人图生视频-1115.json` 或 `InfiniteTalk数字人图生视频-API-111502.json` - InfiniteTalk（数字人生成）

**注意**: 实际使用的workflow文件由 `.env` 中的配置决定。检查 `WORKFLOW_*` 环境变量以确认当前使用的文件。

所有工作流都是API优化版本，具有一致的节点结构。

## 测试策略

**单元测试** (`tests/`): 测试单个模块（settings, ads config, file manager）

**集成测试** (`scripts/test_*.py`): 独立测试每个组件：
- ComfyUI连接和基本工作流加载
- 视频处理（元数据、音频、关键帧）
- 使用Demucs的音频分离
- 使用Whisper的ASR + LLM分析
- 使用MTCNN的人脸检测
- 独立测试每个ComfyUI工作流
- 视频合成操作

**端到端测试** (`scripts/test_end_to_end.py`):
- 检查所有先决条件（文件、API密钥、ComfyUI服务器）
- 简化流程测试（跳过ComfyUI工作流）
- 完整流程测试（需要ComfyUI服务器）

## 常见问题与调试

**ComfyUI连接失败**:
- 验证服务器可访问：`curl http://103.231.86.148:9000/system_stats`
- 检查防火墙/网络设置
- 确保工作流JSON文件存在且有效
- 查看 `comfyui_client.py` 的重试日志

**工作流执行超时**:
- 默认超时：图片（300秒）、声音（300秒）、数字人（600秒）
- 检查ComfyUI服务器日志查看实际错误
- 验证上传的文件在工作流中被正确引用

**502错误 / 文件上传失败**:
- 确保文件句柄正确关闭（已在 `comfyui_client.py` 中使用 `f = open()...finally: f.close()` 模式）
- 检查ComfyUI服务器的反向代理配置
- 利用内置的HTTP重试机制（5次，指数退避）

**模型加载问题**:
- 首次模型下载可能因网络问题失败
- 模型缓存在：`~/.cache/whisper`, `~/.cache/torch` (Demucs)等
- 如果损坏，删除缓存并重试

**内存问题**:
- Whisper medium模型需要约5GB显存
- Demucs需要约4GB显存
- 如果GPU内存不足，使用 `--device cpu`（会慢很多）

**调试中间结果**:
- 所有处理的中间结果自动保存到 `output/debug/{video_id}_{timestamp}/`
- 包含：原始音频、人声分离、关键帧、转录文本、广告视频等
- 每个debug目录都有README.txt说明文件结构

## 目录结构

```
src/
├── core/              # 核心业务逻辑
│   ├── pipeline.py           # 主要的5阶段流水线
│   ├── video_processor.py    # 视频/音频提取
│   ├── audio_separator.py    # Demucs人声分离
│   ├── asr.py               # Whisper转录
│   ├── face_detector.py     # MTCNN人脸检测
│   ├── speaker_detector.py  # 主讲人识别（新增）
│   ├── ad_orchestrator.py   # ComfyUI工作流编排
│   └── video_composer.py    # 最终视频组装
├── services/          # 外部服务集成
│   ├── comfyui_client.py    # ComfyUI API客户端
│   ├── llm_service.py       # OpenAI LLM封装
│   ├── image_cleaner.py     # Qwen Image Edit服务
│   ├── voice_clone.py       # IndexTTS2服务
│   └── digital_human.py     # InfiniteTalk服务
├── models/            # 数据模型（Pydantic）
│   └── video_models.py      # 视频元数据模型
├── utils/             # 工具函数
│   ├── logger.py            # Loguru设置
│   └── file_manager.py      # 临时文件管理
└── config/            # 配置
    ├── settings.py          # 环境配置
    └── ads.py              # 广告配置加载器
```

## 添加新功能时

**新ComfyUI工作流**:
1. 从ComfyUI web界面导出工作流为API JSON
2. 保存到 `docs/workflow/`，使用描述性名称
3. 添加工作流路径到 `.env` 和 `settings.py`
4. 在 `src/services/` 中创建服务封装，遵循现有模式
5. 在 `scripts/` 中添加集成测试

**新流水线阶段**:
- 流水线阶段是顺序的，不能重新排序
- 修改 `src/core/pipeline.py` 中的 `process_video()` 方法
- 更新阶段日志（当前格式：`阶段N: Description`）
- 添加相应的测试

**新广告配置字段**:
- 更新 `config/ads.json` 架构
- 修改 `src/config/ads.py` 中的 AdConfig 模型
- 如需要，更新 `llm_service.py` 中的LLM提示词

**改进插入点选择**:
- 修改 `pipeline.py` 中的 `_select_insertion_with_speaker` 方法
- 调整综合评分权重（当前：语义40% + 人脸60%）
- 更新 `speaker_detector.py` 中的主讲人判定阈值
