# Repository Guidelines

## 项目结构与模块组织
- `src/core/`: 视频处理、音频分离、ASR、人脸检测、编排与合成
- `src/services/`: ComfyUI、LLM、数字人、图片清洗、声音克隆
- `src/config/`: 代码级配置；广告策略在 `config/ads.json`
- `src/utils/`, `src/models/`: 工具与数据模型
- `scripts/`: 集成验证脚本（可独立运行）
- `tests/`: 单元测试集合
- 其他: `input/` 输入、`output/` 输出、`docs/` 文档、`.env` 环境变量

## 构建、测试与开发命令
- 环境准备: `python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`
- 本地运行: `python main.py input/video.mp4 [-o OUT --device {cuda,cpu}]`
- 单元测试: `pytest tests/ -q`
- 覆盖率: `pytest --cov=src --cov-report=term-missing`
- 集成自测: `python scripts/test_end_to_end.py`、`python scripts/test_video_composer.py` 等

## 代码风格与命名约定
- 遵循 PEP 8；4 空格缩进；强制类型注解与简洁 docstring
- 命名: 模块/函数/变量使用 snake_case；类用 PascalCase；常量 UPPER_CASE
- 日志: 禁止 `print`，统一使用 `from src.utils.logger import logger`
- 目录与文件: 新模块置于相应子包（如 `src/core/`、`src/services/`），文件名使用 snake_case

## 测试指南
- 框架: `pytest` 与 `pytest-cov`
- 目标: 核心模块覆盖率≥80%
- 约定: 测试文件 `tests/test_*.py`，测试函数 `test_*`
- 数据: 使用临时目录与小样本；避免将大文件写入 `output/processed/`

## 提交与 PR 规范
- 提交信息: `type(scope): summary`
  - 常用 type: feat/fix/docs/chore/refactor/test/perf/ci
  - 示例: `feat(core): 支持视频合成与广告插入`
- PR 要求: 清晰描述变更、动机与影响；附测试方式与关键输出；关联 issue；必要时附截图/短视频
- 其他: 小步可回滚；勿提交 `.env`、模型/缓存与生成产物

## 安全与配置提示
- `.env` 含敏感信息（如 `OPENAI_API_KEY`、ComfyUI 连接），已在 `.gitignore`，严禁提交
- 广告策略在 `config/ads.json`；通用配置在 `src/config/settings.py`
- 默认使用 GPU，加 `--device cpu` 可在无 GPU 环境运行

