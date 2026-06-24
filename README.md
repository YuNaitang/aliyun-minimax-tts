# 阿里云百炼 MiniMax TTS — AstrBot 插件

通过阿里云百炼调用 MiniMax 语音合成模型的 AstrBot TTS 适配器。

## 安装

### 通过 AstrBot 插件市场

搜索 `aliyun-minimax-tts` 一键安装。

### 手动安装

```bash
cd AstrBot/Addons/plugins/
git clone https://github.com/YuNaitang/aliyun-minimax-tts.git
```

## 配置

在 AstrBot 的 `data/config.yaml` 中添加 TTS 提供者：

```yaml
provider:
  - type: aliyun_minimax_tts
    id: "tts-aliyun-minimax"
    provider_type: "text_to_speech"
    enable: true
    api_key: "sk-你的阿里云百炼APIKEY"
    model: "MiniMax/speech-2.8-hd"
    aliyun_minimax_voice: "naitang_efecebc41563"
    aliyun_minimax_speed: 1.0
    aliyun_minimax_volume: 1.0
    aliyun_minimax_pitch: 0
    aliyun_minimax_sample_rate: 44100
    timeout: 60
```

### 配置项说明

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `api_key` | 阿里云百炼 API Key | 必填 |
| `model` | MiniMax 模型名 | `MiniMax/speech-2.8-hd` |
| `aliyun_minimax_voice` | 克隆音色 ID | 必填 |
| `aliyun_minimax_speed` | 语速 0.5~2.0 | `1.0` |
| `aliyun_minimax_volume` | 音量 0~1.0 | `1.0` |
| `aliyun_minimax_pitch` | 音调 -12~12 | `0` |
| `aliyun_minimax_sample_rate` | 采样率（最大 44100） | `44100` |

## 音色克隆

```bash
# 安装依赖
pip install requests python-dotenv

# 配置 .env
echo 'DASHSCOPE_API_KEY=sk-xxx' > .env
echo 'COSYVOICE_VOICE_URL=https://你的音频文件.wav' >> .env

# 运行克隆脚本
python clone_voice.py
```

## 技术细节

- API 端点：`https://dashscope.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation`
- 响应格式：JSON，音频以 hex 编码在 `output.data.audio` 中
- 不支持 48kHz 采样率，最大 44100
