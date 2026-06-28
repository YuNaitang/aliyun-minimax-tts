```
plugins/astrbot_plugin_aliyun_minimax/
├── main.py          ← VoiceManager + /voice 命令（clone/list/use/delete/info）
├── metadata.yaml    ← v1.3.0
├── README.md        ← 新增音色管理章节
├── LICENSE          ← MIT
├── .gitignore
└── data/             ← 运行时数据（不在 git 跟踪中）
    └── config/
        └── astrbot_plugin_aliyun_minimax_voices.json  ← 音色库（自动生成）
```

## 功能

### TTS 语音合成
- 通过阿里云百炼调用 MiniMax 模型合成语音
- 支持语速、音量、音调、采样率调节
- 异步 HTTP 请求，超时 120 秒，自动清理临时文件

### 音色克隆与管理
- `/voice clone <名称> <音频URL>` - 调用阿里云 voice_clone API 克隆音色，自动存入本地库
- `/voice list` - 列出所有已克隆音色（含活跃标识）
- `/voice use <名称>` - 切换到指定音色（写入 cmd_config.json，需重启生效）
- `/voice delete <名称>` - 从本地库删除音色记录
- `/voice info` - 显示当前 TTS 配置和活跃音色

> 音色库存储在 `data/config/astrbot_plugin_aliyun_minimax_voices.json`。
> MiniMax API 不支持查询和删除云端音色，管理功能基于本地持久化。

## 首次使用（三步搞定）

### 第 1 步：重启 AstrBot
插件会自动完成：
- ✅ 注册 `aliyun_minimax_tts` 提供者
- ✅ 自动写入默认配置到 `data/cmd_config.json`

### 第 2 步：填写 API Key
编辑 `data/cmd_config.json`，找到 `aliyun_minimax_tts` 配置段：
```json
{
  "type": "aliyun_minimax_tts",
  "id": "tts-aliyun-minimax",
  "enable": true,
  "api_key": "sk-你的阿里云百炼APIKEY",
  ...
  "aliyun_minimax_voice": "",
  ...
}
```

### 第 3 步：再次重启并克隆音色
```bash
# 重启 AstrBot
astrbot run

# 克隆音色（在聊天中发送）
/voice clone 奶糖 https://你的音频文件直链.wav

# 查看音色
/voice list

# 切换音色（克隆后自动设为活跃）
/voice use 奶糖

# 重启 AstrBot 生效
astrbot run
```

## 配置项说明

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `api_key` | 阿里云百炼 API Key（[获取](https://bailian.console.aliyun.com/?tab=model#/api-key)） | 必填 |
| `model` | MiniMax 模型名 | `MiniMax/speech-2.8-hd` |
| `aliyun_minimax_voice` | 音色 ID（可通过 /voice use 切换） | 必填 |
| `aliyun_minimax_speed` | 语速 0.5~2.0 | `1.0` |
| `aliyun_minimax_volume` | 音量 0~1.0 | `1.0` |
| `aliyun_minimax_pitch` | 音调 -12~12 | `0` |
| `aliyun_minimax_sample_rate` | 采样率（最大 44100） | `44100` |
| `timeout` | 请求超时（秒） | `60` |

## 音色克隆（创建自己的音色）

通过聊天命令直接克隆：

```bash
/voice clone 我的音色 https://example.com/my-voice.wav
```

**音频要求：**
- 格式: mp3 / m4a / wav
- 时长: 10 秒 ~ 5 分钟
- 大小: ≤ 20MB
- 需要上传到公网可访问的 URL

## 技术细节

| 项目 | 说明 |
|------|------|
| API 端点 | `POST https://dashscope.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation` |
| 请求格式 | JSON，音频参数在 `voice_setting` / `audio_setting` 中 |
| 音色克隆 | `input.action = "voice_clone"`，返回 `demo_audio` 试听链接 |
| 响应格式 | JSON，音频以 **hex 编码** 在 `output.data.audio` 中 |
| 支持采样率 | 8000 / 16000 / 22050 / 24000 / 32000 / 44100 |
| ⚠️ 不支持 | 48000Hz |
| Content-Type | `application/json; charset=utf-8`（注意和 CosyVoice 不同） |

## 更新插件

```bash
cd plugins/astrbot_plugin_aliyun_minimax
git pull
# 重启 AstrBot
astrbot run
```
