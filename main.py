import os
import uuid
import json
import tempfile
import aiohttp

from astrbot.core.provider.entities import ProviderType
from astrbot.core.provider.provider import TTSProvider
from astrbot.core.provider.register import register_provider_adapter
from astrbot.api import logger


@register_provider_adapter(
    "aliyun_minimax_tts",
    "阿里云百炼 MiniMax TTS",
    provider_type=ProviderType.TEXT_TO_SPEECH,
)
class ProviderAliyunMiniMaxTTS(TTSProvider):
    def __init__(self, provider_config: dict, provider_settings: dict) -> None:
        super().__init__(provider_config, provider_settings)

        self.api_key = provider_config.get("api_key", "")
        self.voice_id = provider_config.get("aliyun_minimax_voice", "")
        self.model = provider_config.get("model", "MiniMax/speech-2.8-hd")
        self.set_model(self.model)

        # API 端点（阿里云百炼 MiniMax）
        self.api_url = "https://dashscope.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation"

        # 合成参数
        self.speed = float(provider_config.get("aliyun_minimax_speed", 1.0))
        self.volume = float(provider_config.get("aliyun_minimax_volume", 1.0))
        self.pitch = int(provider_config.get("aliyun_minimax_pitch", 0))
        self.sample_rate = int(provider_config.get("aliyun_minimax_sample_rate", 44100))

        # 阿里云 MiniMax 不支持 48kHz
        if self.sample_rate > 44100:
            self.sample_rate = 44100

        logger.info(f"Aliyun MiniMax TTS 初始化完成: voice={self.voice_id}, model={self.model}")

    async def get_audio(self, text: str) -> str:
        """合成语音，返回临时 WAV 文件路径"""
        if not self.api_key:
            raise Exception("API Key 未配置")
        if not self.voice_id:
            raise Exception("音色 ID (aliyun_minimax_voice) 未配置")

        # 构建阿里云百炼 MiniMax 请求体
        payload = {
            "model": self.model,
            "input": {
                "text": text,
                "voice_setting": {
                    "voice_id": self.voice_id,
                    "speed": self.speed,
                    "vol": self.volume,
                    "pitch": self.pitch,
                },
                "audio_setting": {
                    "sample_rate": self.sample_rate,
                    "format": "wav",
                    "channel": 1,
                },
            },
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json; charset=utf-8",
        }

        logger.debug(f"Aliyun MiniMax TTS 请求: {len(text)} 字符")

        async with aiohttp.ClientSession() as session:
            async with session.post(
                self.api_url,
                headers=headers,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=120),
            ) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    raise Exception(f"API 返回 {resp.status}: {error_text[:300]}")

                data = await resp.json()
                output = data.get("output", {})
                base_resp = output.get("base_resp", {})

                status_code = base_resp.get("status_code", -1)
                if status_code != 0:
                    raise Exception(
                        f"API 错误: {base_resp.get('status_msg', 'unknown')} (code={status_code})"
                    )

                # 音频在 output.data.audio 中，hex 编码的 WAV 数据
                audio_hex = output.get("data", {}).get("audio", "")
                if not audio_hex:
                    raise Exception("响应中没有音频数据")

                audio_bytes = bytes.fromhex(audio_hex)

        # 写入临时文件
        tmp_dir = tempfile.gettempdir()
        filename = f"aliyun_minimax_{uuid.uuid4().hex[:8]}.wav"
        filepath = os.path.join(tmp_dir, filename)

        with open(filepath, "wb") as f:
            f.write(audio_bytes)

        logger.info(f"Aliyun MiniMax TTS 完成: {len(audio_bytes)} bytes -> {filepath}")
        return filepath

    async def test(self) -> None:
        """健康检查：验证配置有效"""
        if not self.api_key:
            raise Exception("请检查 api_key 配置")
        if not self.voice_id:
            raise Exception("请检查 aliyun_minimax_voice 配置")
        await super().test()
