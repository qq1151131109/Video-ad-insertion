"""
日志系统配置

使用loguru提供统一的日志管理
"""
import sys
from pathlib import Path
from loguru import logger

from src.config.settings import settings


def setup_logger():
    """
    配置日志系统

    日志格式：
    - 时间戳
    - 日志级别（彩色）
    - 模块名
    - 消息

    输出：
    - 控制台（彩色）
    - 文件（可选，通过settings.LOG_FILE配置）
    """
    # 移除默认的handler
    logger.remove()

    # 控制台日志（彩色，更易读）
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
               "<level>{level: <8}</level> | "
               "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
               "<level>{message}</level>",
        level=settings.LOG_LEVEL,
        colorize=True,
    )

    # 文件日志（如果配置）
    if settings.LOG_FILE:
        log_file_path = settings.OUTPUT_DIR / "logs" / settings.LOG_FILE
        logger.add(
            log_file_path,
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
            level=settings.LOG_LEVEL,
            rotation="100 MB",  # 日志文件超过100MB时轮转
            retention="7 days",  # 保留7天的日志
            compression="zip",  # 压缩旧日志
            encoding="utf-8",
        )

    # 每次运行都记录配置信息
    logger.info("=" * 60)
    logger.info("短视频智能插入算力广告系统启动")
    logger.info("=" * 60)
    logger.info(f"项目根目录: {settings.PROJECT_ROOT}")
    logger.info(f"日志级别: {settings.LOG_LEVEL}")
    logger.info(f"ComfyUI地址: {settings.comfyui_base_url}")
    logger.info(f"OpenAI模型: {settings.OPENAI_MODEL}")

    return logger


# 初始化logger
setup_logger()

# 导出logger供其他模块使用
__all__ = ["logger"]
