"""
ComfyUI API测试脚本

测试ComfyUI客户端是否能正常工作
"""
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.services.comfyui_client import ComfyUIClient
from src.utils.logger import logger
from src.config.settings import settings


def test_connection():
    """测试ComfyUI连接"""
    logger.info("=" * 60)
    logger.info("测试1: ComfyUI连接")
    logger.info("=" * 60)

    try:
        client = ComfyUIClient()

        # 尝试访问基本端点
        response = client.session.get(f"{client.base_url}/system_stats")

        if response.status_code == 200:
            logger.success("✓ ComfyUI连接正常")
            stats = response.json()
            logger.info(f"系统信息: {stats}")
            return True
        else:
            logger.error(f"✗ ComfyUI连接失败: {response.status_code}")
            return False

    except Exception as e:
        logger.error(f"✗ ComfyUI连接失败: {e}")
        return False


def test_workflow_loading():
    """测试workflow加载"""
    logger.info("\n" + "=" * 60)
    logger.info("测试2: Workflow配置加载")
    logger.info("=" * 60)

    client = ComfyUIClient()

    workflows = {
        "图片清洗": settings.get_workflow_path("image_edit"),
        "声音克隆": settings.get_workflow_path("voice_clone"),
        "数字人生成": settings.get_workflow_path("digital_human"),
    }

    success_count = 0
    for name, path in workflows.items():
        try:
            workflow = client.load_workflow(str(path))
            logger.success(f"✓ {name} - 配置加载成功 ({len(workflow)} 个节点)")
            success_count += 1
        except Exception as e:
            logger.error(f"✗ {name} - 加载失败: {e}")

    logger.info(f"\n成功加载: {success_count}/{len(workflows)}")
    return success_count == len(workflows)


def main():
    """主测试函数"""
    logger.info("开始ComfyUI API测试\n")

    # 测试1: 连接
    connection_ok = test_connection()

    # 测试2: Workflow加载
    workflow_ok = test_workflow_loading()

    # 汇总
    logger.info("\n" + "=" * 60)
    logger.info("测试汇总")
    logger.info("=" * 60)
    logger.info(f"1. ComfyUI连接: {'✓ 通过' if connection_ok else '✗ 失败'}")
    logger.info(f"2. Workflow加载: {'✓ 通过' if workflow_ok else '✗ 失败'}")

    if connection_ok and workflow_ok:
        logger.success("\n🎉 所有测试通过！ComfyUI已就绪。")
        return 0
    else:
        logger.error("\n❌ 部分测试失败，请检查配置。")
        return 1


if __name__ == "__main__":
    sys.exit(main())
