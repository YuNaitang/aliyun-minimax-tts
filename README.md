# 阿里云百炼 MiniMax TTS — AstrBot 插件

通过阿里云百炼调用 MiniMax 语音合成模型的 AstrBot TTS 适配器。

支持音色克隆（奶糖音色已就绪）。

---

## 安装

### 方式一：通过 AstrBot 插件管理（推荐）

1. 打开 AstrBot 管理面板 → **插件管理**
2. 点击 **安装插件** → 输入仓库 URL：
   ```
   https://github.com/YuNaitang/aliyun-minimax-tts
   ```
3. 点击安装，等待完成

### 方式二：手动安装

```bash
cd AstrBot/data/plugins/
git clone https://github.com/YuNaitang/aliyun-minimax-tts.git
```

---

## 首次使用（三步搞定）

### 第 1 步：重启 AstrBot

```bash
# 重启 AstrBot
astrbot run
```

插件会自动完成两件事：
- ✅ 注册 `aliyun_minimax_tts` 提供者
- ✅ 自动写入默认配置到 `data/cmd_config.json`

日志里会看到：
```
[INFO] Provider 适配器已注册: aliyun_minimax_tts
[INFO] ✓ 已自动添加 TTS 配置到 cmd_config.json
```

### 第 2 步：填写 API Key 和音色 ID

编辑 `data/cmd_config.json`，找到 `aliyun_minimax_tts` 配置段：

```json
{
  "type": "aliyun_minimax_tts",
  "id": "tts-aliyun-minimax",
  "enable": true,
  "api_key": "sk-你的阿里云百炼APIKEY",          // ← 必填
  "model": "MiniMax/speech-2.8-hd",
  "aliyun_minimax_voice": "naitang_efecebc41563", // ← 必填（奶糖克隆音色）
  "aliyun_minimax_speed": 1.0,
  "aliyun_minimax_volume": 1.0,
  "aliyun_minimax_pitch": 0,
  "aliyun_minimax_sample_rate": 44100,
  "timeout": 60
}
```

### 第 3 步：再次重启 AstrBot

```bash
astrbot run
```

日志确认：
```
[INFO] Loading model aliyun_minimax_tts(tts-aliyun-minimax) ...
[INFO] Aliyun MiniMax TTS: voice=naitang_efecebc41563
```

---

## 在聊天中使用 TTS

配置 TTS 提供者后，在对话中：

1. **发送语音消息** — AstrBot 会自动使用 `aliyun_minimax_tts` 合成语音
2. **配置 TTS 触发** — 在管理面板 → 模型提供商 → TTS 设置中开启

---

## 配置项说明

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `api_key` | 阿里云百炼 API Key（[获取](https://bailian.console.aliyun.com/?tab=model#/api-key)） | 必填 |
| `model` | MiniMax 模型名 | `MiniMax/speech-2.8-hd` |
| `aliyun_minimax_voice` | 克隆音色 ID | 必填 |
| `aliyun_minimax_speed` | 语速 0.5~2.0 | `1.0` |
| `aliyun_minimax_volume` | 音量 0~1.0 | `1.0` |
| `aliyun_minimax_pitch` | 音调 -12~12 | `0` |
| `aliyun_minimax_sample_rate` | 采样率（最大 44100） | `44100` |
| `timeout` | 请求超时（秒） | `60` |

---

## 更新插件

当 GitHub 有新版时：

```bash
cd AstrBot/data/plugins/aliyun-minimax-tts
git pull
```

重启 AstrBot 即可生效。

---

## 音色克隆（创建自己的音色）

```bash
# 1. 准备一段 10~20 秒的干净人声 WAV 文件
# 2. 上传到公网可访问的 URL
# 3. 调用阿里云克隆 API：

curl -X POST 'https://dashscope.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation' \
  -H "Authorization: Bearer sk-你的APIKEY" \
  -H "Content-Type: application/json; charset=utf-8" \
  -d '{
    "model": "MiniMax/speech-2.8-hd",
    "input": {
      "action": "voice_clone",
      "voice_id": "my_voice_8chars",
      "audio_url": "https://你的音频文件直链.wav"
    }
  }'

# 4. 返回的 voice_id 填入 aliyun_minimax_voice 即可使用
```

---

## 技术细节

| 项目 | 说明 |
|------|------|
| API 端点 | `POST https://dashscope.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation` |
| 请求格式 | JSON，音频参数在 `voice_setting` / `audio_setting` 中 |
| 响应格式 | JSON，音频以 **hex 编码** 在 `output.data.audio` 中 |
| 支持采样率 | 8000 / 16000 / 22050 / 24000 / 32000 / 44100 |
| ⚠️ 不支持 | 48000Hz |
| Content-Type | `application/json; charset=utf-8`（注意和 CosyVoice 不同） |
