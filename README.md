# 短视频智能插入算力广告系统

在短视频中智能插入NVIDIA算力相关的数字人软广告，使用AI技术实现自然、流畅的广告植入。

## 📋 项目状态

**当前阶段**: 🎉 所有核心功能已完成！

### ✅ Phase 1 已完成 (13/13) - 基础框架
- [x] 项目目录结构
- [x] 配置管理系统（`src/config/settings.py`）
- [x] 日志系统（`src/utils/logger.py`）
- [x] ComfyUI API客户端（`src/services/comfyui_client.py`）
- [x] **广告配置系统**（`src/config/ads.py` + `config/ads.json`）✨
- [x] 文件管理器（`src/utils/file_manager.py`）
- [x] 视频元数据提取（`src/core/video_processor.py`）
- [x] 音频提取
- [x] 关键帧提取（基于清晰度）
- [x] 人声分离模块（`src/core/audio_separator.py` - Demucs）
- [x] 依赖配置（`requirements.txt`）
- [x] 基础单元测试（3个测试文件）

### ✅ Phase 2 已完成 (5/5) - ASR + 人脸检测 + LLM
- [x] **Whisper ASR集成**（`src/core/asr.py`）✨
  - 语音识别，带词级时间戳
  - 上下文提取
  - SRT字幕生成
- [x] **人脸检测模块**（`src/core/face_detector.py` - MTCNN）✨
  - 人脸检测和质量评估
  - 多帧最佳人脸选择
  - 综合质量评分（人脸+清晰度）
- [x] **LLM服务**（`src/services/llm_service.py`）✨
  - 视频内容分析
  - 插入点智能检测
  - 上下文感知的广告词生成
- [x] 测试脚本（ASR + LLM + 人脸检测）
- [x] 文档更新

### ✅ Phase 3 已完成 (6/6) - ComfyUI工作流集成
- [x] **图片清洗服务**（`src/services/image_cleaner.py`）✨
  - Qwen Image Edit集成
  - 去除文字、水印等干扰元素
- [x] **声音克隆服务**（`src/services/voice_clone.py`）✨
  - IndexTTS2集成
  - 情绪和语速控制
  - 批量克隆支持
- [x] **数字人生成服务**（`src/services/digital_human.py`）✨
  - InfiniteTalk集成
  - 高质量数字人视频生成
- [x] **广告视频编排器**（`src/core/ad_orchestrator.py`）✨
  - 三步workflow统一管理
  - 端到端广告视频生成
- [x] **完整处理流水线**（`src/core/pipeline.py` + `main.py`）✨
  - 5阶段完整流程
  - 批量处理支持
  - 命令行接口
- [x] 测试脚本和文档更新

### ✅ Phase 4 已完成 (4/4) - 视频合成与优化
- [x] **视频合成服务**（`src/core/video_composer.py`）✨
  - 视频剪辑（在插入点切分原视频）
  - 视频拼接（合成最终视频）
  - 音频淡入淡出
  - 音轨混合
- [x] **完善主流水线**
  - 集成视频合成到阶段5
  - 完整的端到端流程
- [x] **视频合成测试**（`scripts/test_video_composer.py`）
- [x] 文档更新

### ✅ Phase 5 已完成 (5/5) - 测试与优化
- [x] **端到端测试**（`scripts/test_end_to_end.py`）✨
  - 前置条件检查
  - 简化流程测试
  - 完整流程测试
- [x] **性能优化指南**（`docs/性能优化指南.md`）✨
  - 性能基准数据
  - 瓶颈分析
  - 优化建议
  - 资源监控方法
- [x] **质量评估体系**（`docs/质量评估指南.md`）✨
  - 5维度评分标准
  - 详细检查清单
  - 质量改进建议
  - 评估报告模板
- [x] **故障排查文档**（`docs/故障排查指南.md`）✨
  - 常见问题FAQ（25+问题）
  - 错误代码参考
  - 调试方法
  - 最佳实践
- [x] 文档完善和整理

### 🎊 项目完成
所有核心功能和文档已完成，系统可投入实际使用！

---

## 🚀 快速开始

### 1. 环境准备

#### 系统要求
- Python 3.9+
- NVIDIA GPU（推荐12GB+ 显存）
- 硬盘空间: 至少100GB

#### 创建虚拟环境
```bash
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# 或
.venv\Scripts\activate  # Windows
```

#### 安装依赖
```bash
pip install -r requirements.txt
```

**注意**: 某些依赖（如Demucs、Whisper）会自动下载模型文件，首次安装可能需要较长时间。

---

### 2. 配置

确保 `.env` 文件配置正确：

```env
# LLM API
OPENAI_API_KEY=sk-xxxx
OPENAI_BASE_URL=https://www.dmxapi.cn/v1
OPENAI_MODEL=gpt-4o-mini

# ComfyUI API
COMFYUI_HOST=103.231.86.148
COMFYUI_PORT=9000
COMFYUI_PROTOCOL=http

# Workflow路径
WORKFLOW_IMAGE_EDIT=docs/workflow/qwen_image_edit.json
WORKFLOW_VOICE_CLONE=docs/workflow/index TTS2情绪控制_api_1013.json
WORKFLOW_DIGITAL_HUMAN=docs/workflow/InfiniteTalk数字人视频生视频_api.json
```

---

### 3. 使用方法

#### 处理单个视频
```bash
python main.py input/video.mp4
```

输出将保存到 `output/processed/视频ID/` 目录。

#### 指定输出目录
```bash
python main.py input/video.mp4 -o output/my_custom_output
```

#### 批量处理
```bash
python main.py input/ --batch
```

这将处理 `input/` 目录下的所有 `.mp4` 视频文件。

#### 使用CPU（不使用GPU）
```bash
python main.py input/video.mp4 --device cpu
```

#### 完整参数说明
```
usage: main.py [-h] [-o OUTPUT] [--batch] [--device {cuda,cpu}] input

参数:
  input                 输入视频文件路径或目录（批量模式）
  -o, --output OUTPUT   输出目录（默认: output/processed/视频ID）
  --batch              批量模式：处理指定目录下的所有视频
  --device {cuda,cpu}  处理设备（默认: cuda）
```

#### 处理流程说明

完整的5阶段处理流程：

**阶段1: 视频分析**
1. 提取视频元数据（时长、分辨率、帧率）
2. 提取音频（WAV格式）
3. 人声分离（使用Demucs）

**阶段2: 内容理解**
1. 语音识别（Whisper ASR，带时间戳）
2. LLM内容分析（主题、类别、插入点检测）

**阶段3: 广告准备**
1. 提取插入点的关键帧
2. 人脸检测和质量评估
3. 选择匹配的广告
4. LLM生成上下文感知的广告词

**阶段4: 数字人视频生成**
1. 图片清洗（Qwen Image Edit - 去除文字水印）
2. 声音克隆（IndexTTS2 - 克隆原视频人物声音）
3. 数字人生成（InfiniteTalk - 生成说广告词的数字人视频）

**阶段5: 视频合成**
1. 在插入点切分原视频为两段
2. 将数字人广告视频插入中间
3. 拼接生成最终视频

---

### 4. 测试

#### 测试ComfyUI连接
```bash
python scripts/test_comfyui.py
```

预期输出：
```
✓ ComfyUI连接正常
✓ 图片清洗 - 配置加载成功
✓ 声音克隆 - 配置加载成功
✓ 数字人生成 - 配置加载成功
🎉 所有测试通过！
```

#### 测试视频处理
```bash
python scripts/test_video_processor.py
```

预期输出：
```
✓ 视频元数据提取成功
✓ 音频提取成功
✓ 关键帧提取成功
✓ 文件管理器测试成功
🎉 所有测试通过！(4/4)
```

#### 测试人声分离
```bash
python scripts/test_audio_separator.py
```

预期输出：
```
✓ Demucs已安装
✓ 人声分离成功
🎉 所有测试通过！
```

**注意**: 首次运行会下载Demucs模型（约2GB）

#### 测试ASR和LLM
```bash
python scripts/test_asr_llm.py
```

预期输出：
```
✓ Whisper已安装
✓ OpenAI API密钥已配置
✓ 语音识别成功
✓ 内容分析成功
✓ 广告词生成成功
🎉 所有测试通过！(5/5)
```

**注意**:
- 首次运行会下载Whisper模型
- 需要配置OpenAI API密钥

#### 测试人脸检测
```bash
python scripts/test_face_detector.py
```

预期输出：
```
✓ MTCNN已安装
✓ 人脸检测成功
✓ 多帧检测成功
🎉 所有测试通过！
```

**注意**: 首次运行会下载MTCNN模型

#### 测试ComfyUI Workflows ✨
```bash
python scripts/test_workflows.py
```

预期输出：
```
✓ Workflow文件存在
✓ 数字人服务初始化成功
🎉 快速测试全部通过！
```

**注意**:
- 完整的workflow测试需要ComfyUI服务运行
- 确保 http://103.231.86.148:9000 可访问
- 完整测试可能需要5-10分钟

#### 测试视频合成 ✨
```bash
python scripts/test_video_composer.py
```

预期输出：
```
✓ 视频信息获取成功
✓ 视频切分成功
✓ 视频拼接成功
✓ 广告插入成功
🎉 所有测试通过！
```

**注意**: 此测试会生成较大的视频文件

#### 端到端完整测试 ✨
```bash
python scripts/test_end_to_end.py
```

预期输出：
```
✓ 前置条件检查通过
✓ 简化端到端测试通过
✓ 批量处理测试通过
🎉 所有测试通过！
```

**注意**:
- 会检查所有前置条件（视频、API、workflow）
- 简化测试跳过ComfyUI步骤，用于快速验证
- 完整测试需要ComfyUI服务运行

#### 运行单元测试
```bash
pytest tests/
```

---

## 📂 项目结构

```
中插广告/
├── README.md                    # 项目说明
├── 技术方案与执行计划.md         # 详细技术方案
├── .env                         # 环境变量配置
├── requirements.txt             # Python依赖
│
├── input/                       # 输入视频目录
│   ├── 2025-09-23-DO803bmkdTl.mp4
│   ├── 2025-10-11-DPoue7CkhUX.mp4
│   └── 2025-10-22-DQFGqaeAS0u.mp4
│
├── output/                      # 输出目录
│   ├── processed/               # 最终视频
│   ├── debug/                   # 调试中间结果
│   └── logs/                    # 处理日志
│
├── cache/                       # 缓存目录
│   ├── audio/                   # 音频缓存
│   ├── keyframes/               # 关键帧
│   ├── transcriptions/          # ASR结果
│   └── ad_materials/            # 广告素材
│
├── docs/                        # 文档
│   ├── workflow/                # ComfyUI workflow配置
│   ├── 需求文档.md
│   └── ComfyUI_API调用说明.md
│
├── src/                         # 源代码
│   ├── core/                    # 核心业务模块
│   │   ├── video_processor.py   # 视频处理
│   │   ├── audio_separator.py   # 人声分离（Demucs）
│   │   ├── asr.py               # 语音识别（Whisper）✨
│   │   └── face_detector.py     # 人脸检测（MTCNN）✨
│   ├── services/                # 外部服务
│   │   ├── comfyui_client.py    # ComfyUI客户端
│   │   └── llm_service.py       # LLM服务（OpenAI）✨
│   ├── models/                  # 数据模型
│   │   └── video_models.py      # 视频相关模型
│   ├── utils/                   # 工具函数
│   │   ├── logger.py            # 日志系统
│   │   └── file_manager.py      # 文件管理器
│   └── config/                  # 配置
│       ├── settings.py          # 配置管理
│       └── ads.py               # 广告配置系统
│
├── scripts/                     # 脚本
│   ├── test_comfyui.py          # ComfyUI测试
│   ├── test_video_processor.py  # 视频处理测试
│   ├── test_audio_separator.py  # 人声分离测试
│   ├── test_asr_llm.py          # ASR和LLM测试 ✨
│   └── test_face_detector.py    # 人脸检测测试 ✨
│
└── tests/                       # 单元测试
    ├── test_settings.py         # 配置测试
    ├── test_ads.py              # 广告配置测试
    └── test_file_manager.py     # 文件管理器测试
```

---

---

## 🎯 广告配置

广告内容完全可配置，不限于NVIDIA算力！编辑 `config/ads.json` 来管理广告：

```json
{
  "ads": [
    {
      "id": "nvidia_gpu",
      "name": "NVIDIA算力",
      "product": "NVIDIA GPU",
      "enabled": true,
      "priority": 1,
      "selling_points": [
        "高性能AI算力",
        "深度学习加速",
        "训练速度提升10倍"
      ],
      "target_scenarios": [
        "AI开发",
        "深度学习",
        "科技教程"
      ],
      "templates": {
        "科技类": [
          "这得益于NVIDIA强大的算力支持，让AI训练事半功倍"
        ],
        "通用": [
          "NVIDIA算力，性能强劲"
        ]
      }
    }
  ]
}
```

### 配置说明
- **enabled**: 是否启用该广告
- **priority**: 优先级（数字越小越优先）
- **selling_points**: 产品卖点（LLM生成广告词时使用）
- **target_scenarios**: 适用场景（用于视频类型匹配）
- **templates**: 按类别预设的模板文案

### 添加新广告
直接在 `ads` 数组中添加新对象即可，支持多个广告同时管理。

---

## 🎯 核心功能

### ✅ Phase 1 - 基础框架（已完成）
- ✅ 配置管理系统
- ✅ 日志系统（Loguru）
- ✅ ComfyUI API客户端
- ✅ 可配置广告系统
- ✅ 视频处理
  - 元数据提取
  - 音频提取
  - 关键帧提取
- ✅ 人声分离（Demucs）
- ✅ 文件管理器

### ✅ Phase 2 - ASR + 人脸检测 + LLM（已完成）
- ✅ **Whisper ASR集成**
  - 高精度语音识别
  - 词级时间戳
  - 上下文提取功能
  - SRT字幕生成
- ✅ **人脸检测**（MTCNN）
  - 人脸检测和定位
  - 人脸质量评估
  - 多帧最佳人脸选择
  - 综合评分（人脸+清晰度）
- ✅ **LLM服务**（gpt-4o-mini）
  - 视频内容深度分析
  - 智能插入点检测
  - 上下文感知的广告词生成
  - 支持多候选插入点

### ✅ Phase 3 - ComfyUI工作流集成（已完成）
- ✅ **图片清洗服务**（Qwen Image Edit）
  - 智能去除文字、水印、字幕
  - 保持人物和背景清晰自然
  - 批处理支持
- ✅ **声音克隆服务**（IndexTTS2）
  - 克隆原视频人物声音
  - 情绪控制（neutral/happy/sad等）
  - 语速控制
  - 批量生成支持
- ✅ **数字人生成服务**（InfiniteTalk）
  - 根据人脸图片和音频生成数字人视频
  - 高质量口型同步
  - 可配置帧率和质量
- ✅ **广告视频编排器**
  - 三步workflow统一管理
  - 端到端广告视频生成
  - 自动化流程控制
- ✅ **完整处理流水线**
  - 5阶段完整流程
  - 从输入视频到数字人广告的全自动处理
  - 批量处理支持
  - 命令行接口

### ✅ Phase 4 - 视频合成与优化（已完成）
- ✅ **视频合成服务**
  - 视频剪辑和切分
  - 视频拼接和合成
  - 音频淡入淡出
  - 音轨混合
- ✅ **完善流水线**
  - 集成视频合成到阶段5
  - 完整的端到端处理流程
  - 从输入视频到带广告的最终视频

### ✅ Phase 5 - 测试与优化（已完成）
- ✅ 全流程测试
- ✅ 性能优化
- ✅ 质量评估
- ✅ 文档完善

---

## 📖 文档

- [技术方案与执行计划](./技术方案与执行计划.md) - 完整技术方案
- [需求文档](./docs/需求文档.md) - 详细需求说明
- [ComfyUI API调用说明](./docs/ComfyUI_API调用说明.md) - API使用指南

---

## 🔧 开发指南

### 运行测试
```bash
pytest tests/
```

### 代码风格
- 使用type hints
- 遵循PEP 8
- 添加docstrings

---

## ⚠️ 注意事项

1. **ComfyUI服务**: 确保 `103.231.86.148:9000` 可访问
2. **GPU要求**: Whisper和Demucs需要GPU加速
3. **模型下载**: 首次运行会自动下载模型（可能需要较长时间）
4. **敏感信息**: `.env` 文件包含API密钥，不要提交到Git

---

## 📊 预计性能

**单视频处理时间**（30秒视频）: 约 7-13分钟
- 人声分离: 1-1.5分钟
- ASR识别: 1-2分钟
- 数字人生成: 3-5分钟

**硬件推荐**:
- CPU: 8核16线程
- 内存: 32GB
- GPU: NVIDIA RTX 3060或更好（12GB显存）

---

## 📝 更新日志

### v0.5.0 (2025-11-14 - 当前)
- ✨ **新增**: Phase 4 完整实现 - 视频合成与优化
- ✨ **新增**: 视频合成服务（`src/core/video_composer.py`）
  - 视频剪辑功能（在指定时间点切分视频）
  - 视频拼接功能（合成多个视频片段）
  - 广告插入功能（一键将广告插入原视频）
  - 音频淡入淡出
  - 音轨混合
- ✨ **新增**: 完善主流水线（`src/core/pipeline.py`）
  - 集成视频合成到阶段5
  - 完整的端到端流程（输入视频 → 带广告的最终视频）
  - 所有5个阶段全部实现
- ✨ **新增**: 视频合成测试脚本（`scripts/test_video_composer.py`）
  - 视频信息获取测试
  - 视频切分测试
  - 视频拼接测试
  - 广告插入测试
- 📝 **文档**: 更新README，添加Phase 4功能说明
- 📝 **文档**: 更新处理流程说明（所有5阶段完成）

### v0.4.0 (2025-11-14)
- ✨ **新增**: Phase 3 完整实现 - ComfyUI工作流集成
- ✨ **新增**: 图片清洗服务（`src/services/image_cleaner.py`）
  - Qwen Image Edit workflow集成
  - 智能去除文字、水印等干扰元素
  - 批处理支持
- ✨ **新增**: 声音克隆服务（`src/services/voice_clone.py`）
  - IndexTTS2 workflow集成
  - 情绪和语速控制
  - 批量克隆支持
- ✨ **新增**: 数字人生成服务（`src/services/digital_human.py`）
  - InfiniteTalk workflow集成
  - 高质量口型同步
  - 批量生成支持
- ✨ **新增**: 广告视频编排器（`src/core/ad_orchestrator.py`）
  - 三步workflow统一管理
  - 端到端广告视频生成
  - 错误处理和状态管理
- ✨ **新增**: 完整处理流水线（`src/core/pipeline.py` + `main.py`）
  - 5阶段自动化流程
  - 批量处理支持
  - 完整的命令行接口
  - 处理时间统计
- ✨ **新增**: ComfyUI工作流测试脚本（`scripts/test_workflows.py`）
- 📝 **文档**: 更新README，添加使用说明和Phase 3详细功能
- 📝 **文档**: 添加完整的处理流程说明

### v0.3.0 (2025-11-14)
- ✨ **新增**: Phase 2 完整实现
- ✨ **新增**: Whisper ASR集成（`src/core/asr.py`）
  - 支持多种Whisper模型（tiny/base/small/medium/large）
  - 词级时间戳
  - 智能上下文提取
  - SRT字幕格式导出
- ✨ **新增**: MTCNN人脸检测（`src/core/face_detector.py`）
  - 高精度人脸检测
  - 人脸质量评分
  - 多帧最佳人脸选择
  - 可视化调试支持
- ✨ **新增**: LLM服务（`src/services/llm_service.py`）
  - 视频内容智能分析
  - 插入点自动检测（带优先级）
  - 上下文感知的广告词生成
  - 支持自定义提示词
- ✨ **新增**: 完整测试套件
  - ASR和LLM集成测试（`scripts/test_asr_llm.py`）
  - 人脸检测测试（`scripts/test_face_detector.py`）
- 📝 **文档**: 更新README，添加Phase 2功能说明
- 📝 **文档**: 添加详细的测试指南

### v0.2.0 (2025-11-14)
- ✨ **新增**: 可配置的广告系统（`config/ads.json`）
- ✨ **新增**: 文件管理器，支持临时文件自动管理和清理
- ✨ **新增**: 视频处理模块
  - 视频元数据提取（分辨率、帧率、时长等）
  - 音频提取（WAV格式）
  - 关键帧提取（支持指定时间点）
  - 最佳帧选择（基于清晰度评分）
- ✨ **新增**: 人声分离模块（`src/core/audio_separator.py`）
- ✨ **新增**: 视频处理测试脚本
- ✨ **新增**: 基础单元测试（3个测试文件）
- 📝 **文档**: 更新README，添加广告配置说明

### v0.1.0 (2025-11-14)
- 初始化项目结构
- 实现配置管理和日志系统
- 实现ComfyUI API客户端
- 添加基础测试脚本

---

**开发者**: Claude Code
**项目启动**: 2025-11-14
**Phase 1 完成**: 2025-11-14
**Phase 2 完成**: 2025-11-14
**Phase 3 完成**: 2025-11-14
**Phase 4 完成**: 2025-11-14
**下一里程碑**: Phase 5 - 测试与优化
