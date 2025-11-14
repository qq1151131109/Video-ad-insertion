"""
文件管理器测试
"""
import pytest
from pathlib import Path
import tempfile
import shutil

from src.utils.file_manager import TempFileManager
from src.config.settings import settings


def test_file_manager_initialization():
    """测试文件管理器初始化"""
    video_id = "test_video_123"
    manager = TempFileManager(video_id)

    assert manager.video_id == video_id
    assert manager.base_dir.exists()
    assert (manager.base_dir / "audio").exists()
    assert (manager.base_dir / "keyframes").exists()

    # 清理
    manager.cleanup(keep_on_error=False)


def test_get_path():
    """测试路径获取"""
    manager = TempFileManager("test")

    # 测试各种类别
    audio_path = manager.get_path("audio", "test.wav")
    assert audio_path.parent.name == "audio"
    assert audio_path.name == "test.wav"

    keyframe_path = manager.get_path("keyframes", "frame.jpg")
    assert keyframe_path.parent.name == "keyframes"

    # 测试无效类别
    with pytest.raises(ValueError):
        manager.get_path("invalid_category", "file.txt")

    manager.cleanup(keep_on_error=False)


def test_convenience_methods():
    """测试便捷方法"""
    manager = TempFileManager("test")

    # 测试各种快捷方法
    assert manager.get_audio_path("test.wav").parent.name == "audio"
    assert manager.get_keyframe_path("test.jpg").parent.name == "keyframes"
    assert manager.get_transcription_path().parent.name == "transcriptions"
    assert manager.get_ad_material_path("test.mp4").parent.name == "ad_materials"
    assert manager.get_video_path("test.mp4").parent.name == "videos"

    # 测试预定义路径
    assert manager.original_audio_path.name == "original.wav"
    assert manager.separated_vocals_path.name == "vocals.wav"
    assert manager.voice_sample_path.name == "voice_sample.wav"

    manager.cleanup(keep_on_error=False)


def test_save_and_load_text():
    """测试文本读写"""
    manager = TempFileManager("test")

    # 保存文本
    test_content = "这是测试内容\n包含多行"
    manager.save_text("transcriptions", "test.txt", test_content)

    # 加载文本
    loaded = manager.load_text("transcriptions", "test.txt")
    assert loaded == test_content

    # 加载不存在的文件
    not_exist = manager.load_text("transcriptions", "not_exist.txt")
    assert not_exist is None

    manager.cleanup(keep_on_error=False)


def test_file_exists():
    """测试文件存在检查"""
    manager = TempFileManager("test")

    # 创建文件
    manager.save_text("audio", "test.txt", "test")

    assert manager.file_exists("audio", "test.txt") is True
    assert manager.file_exists("audio", "not_exist.txt") is False

    manager.cleanup(keep_on_error=False)


def test_copy_file():
    """测试文件复制"""
    manager = TempFileManager("test")

    # 创建源文件
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
        f.write("test content")
        src_path = Path(f.name)

    try:
        # 复制文件
        manager.copy_file(src_path, "audio", "copied.txt")

        # 验证
        assert manager.file_exists("audio", "copied.txt")
        content = manager.load_text("audio", "copied.txt")
        assert content == "test content"

    finally:
        src_path.unlink()
        manager.cleanup(keep_on_error=False)


def test_get_size():
    """测试大小计算"""
    manager = TempFileManager("test")

    # 创建一些文件
    manager.save_text("audio", "file1.txt", "x" * 1000)
    manager.save_text("keyframes", "file2.txt", "y" * 2000)

    # 测试大小计算
    size_bytes = manager.get_size()
    assert size_bytes >= 3000  # 至少3000字节

    size_mb = manager.get_size_mb()
    assert size_mb > 0

    manager.cleanup(keep_on_error=False)


def test_cleanup():
    """测试清理功能"""
    manager = TempFileManager("test_cleanup")

    # 创建文件
    manager.save_text("audio", "test.txt", "test")

    base_dir = manager.base_dir
    assert base_dir.exists()

    # 清理
    manager.cleanup(keep_on_error=False)
    assert not base_dir.exists()


def test_context_manager():
    """测试上下文管理器"""
    video_id = "test_context"

    # 正常退出
    with TempFileManager(video_id) as manager:
        manager.save_text("audio", "test.txt", "test")
        base_dir = manager.base_dir

    # 退出后应该被清理
    assert not base_dir.exists()


def test_context_manager_with_error():
    """测试上下文管理器错误处理"""
    video_id = "test_error"

    try:
        with TempFileManager(video_id) as manager:
            manager.save_text("audio", "test.txt", "test")
            base_dir = manager.base_dir
            # 模拟错误
            raise Exception("Test error")
    except Exception:
        pass

    # 如果配置为保留错误文件，则不应该被清理
    if settings.KEEP_TEMP_FILES_ON_ERROR:
        assert base_dir.exists()
        # 手动清理
        shutil.rmtree(base_dir)
    else:
        assert not base_dir.exists()
