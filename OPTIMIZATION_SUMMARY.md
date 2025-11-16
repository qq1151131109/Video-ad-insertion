# 视频处理优化总结

## 优化时间
2025-11-16

## 优化内容

### 1. 禁用图片缩放以提升画质 ✅

**问题**: 插入的数字人视频清晰度很差
**原因**: digital_human.py 中存在 OOM 保护机制,强制将图片短边限制为 480px

**解决方案**:
- 修改 `src/core/pipeline.py:325-326`
- 将 `video_width` 和 `video_height` 参数设置为 `None`
- 跳过 `digital_human.py` 中的缩放逻辑（lines 210-237）
- 保持原始关键帧的完整分辨率

**效果**:
- 数字人视频将使用原图分辨率生成
- 画质显著提升
- 注意: 如遇 GPU OOM,可恢复缩放逻辑

### 2. 优化声音克隆音频输入 ✅

**问题**: 使用完整 65 秒音频作为参考,质量参差不齐
**原因**: 长音频包含多种情绪/音调,影响克隆稳定性

**解决方案**:
1. **新增功能** - `src/core/video_processor.py:106-163`
   - `extract_audio()` 方法新增 `start_time` 和 `end_time` 参数
   - 支持提取指定时间段的音频片段

2. **修改流程** - `src/core/pipeline.py:265-301`
   - 在插入点前后提取 5-10 秒音频片段
   - 对片段进行 Demucs 人声分离
   - 使用纯净的短片段作为声音克隆参考

**详细逻辑**:
```python
# 提取 10 秒音频（插入点前后各 5 秒）
audio_clip_duration = 10.0
clip_start = max(0, insertion_time - 5.0)
clip_end = min(duration, insertion_time + 5.0)

# 保证至少 5 秒
if clip_end - clip_start < 5.0:
    调整范围...
```

**效果**:
- 更稳定的音色克隆质量
- 更接近插入点的音频特征
- 减少无关内容干扰

## 代码变更

### 文件清单
1. `src/core/pipeline.py` - 主要流程修改
2. `src/core/video_processor.py` - 音频提取功能增强

### 阶段编号更新
阶段 3 (广告准备) 步骤数从 5 个增加到 6 个:
1. 智能选择插入点
2. **提取插入点附近音频片段（新增）**
3. 保存关键帧
4. 确认人脸质量
5. 选择广告
6. 生成广告词

## 测试建议

```bash
# 使用相同视频测试优化效果
python main.py input/2025-10-11-DPoue7CkhUX.mp4 --device cpu

# 对比输出
# 旧版本: cache/2025-10-11-DPoue7CkhUX/ (优化前)
# 新版本: output/processed/2025-10-11-DPoue7CkhUX/ (优化后)
```

##性能影响

- 增加耗时: ~20-30 秒（额外音频提取和分离）
- 画质提升: 显著（取决于原视频分辨率）
- 声音质量: 提升（更稳定的克隆效果）

## 回滚方案

如需回滚任一优化:

### 回滚图片缩放禁用:
```python
# src/core/pipeline.py:325-326
video_width=metadata.width,   # 恢复原值
video_height=metadata.height  # 恢复原值
```

### 回滚声音克隆优化:
```python
# src/core/pipeline.py:360
reference_audio_path=vocals_path,  # 使用完整人声轨道
```

## 注意事项

1. **GPU 内存**: 禁用缩放后,高分辨率视频可能导致 OOM
2. **兼容性**: extract_audio() 向后兼容,旧代码无需修改
3. **调试**: 音频片段保存在 `cache/{video_id}/audio/reference_*.wav`

