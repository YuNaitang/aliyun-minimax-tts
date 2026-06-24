import os
import uuid
import json
import tempfile
import aiohttp

from astrbot.api.star import Star, register, AstrMessageEvent
from astrbot.api import logger
from astrbot.core.provider.entities import ProviderType
from astrbot.core.provider.provider import TTSProvider
from astrbot.core.provider.register import register_provider_adapter


@register_provider_adapter(
    "aliyun_minimax_tts",
    "阿里云百炼 MiniMax TTS",
    provider_type=ProviderType.TEXT_TO_SPEECH,
)
class ProviderAliyunMiniMaxTTS(TTSProvider):
    """阿里云百炼 MiniMax 语音合成适配器"""

    def __init__(self, provider_config: dict, provider_settings: dict) -> None:
        super().__init__(provider_config, provider_settings)

        self.api_key = provider_config.get("api_key", "")
        self.voice_id = provider_config.get("aliyun_minimax_voice", "")
        self.model = provider_config.get("model", "MiniMax/speech-2.8-hd")
        self.set_model(self.model)

        self.api_url = "https://dashscope.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation"

        self.speed = float(provider_config.get("aliyun_minimax_speed", 1.0))
        self.volume = float(provider_config.get("aliyun_minimax_volume", 1.0))
        self.pitch = int(provider_config.get("aliyun_minimax_pitch", 0))
        self.sample_rate = int(provider_config.get("aliyun_minimax_sample_rate", 44100))
        if self.sample_rate > 44100:
            self.sample_rate = 44100

        logger.info(f"Aliyun MiniMax TTS: voice={self.voice_id}, model={self.model}")

    async def get_audio(self, text: str) -> str:
        if not self.api_key:
            raise Exception("API Key 未配置")
        if not self.voice_id:
            raise Exception("aliyun_minimax_voice 未配置")

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

        async with aiohttp.ClientSession() as session:
            async with session.post(
                self.api_url, headers=headers, json=payload,
                timeout=aiohttp.ClientTimeout(total=120),
            ) as resp:
                if resp.status != 200:
                    raise Exception(f"API 返回 {resp.status}: {(await resp.text())[:300]}")
                data = await resp.json()
                output = data.get("output", {})
                base_resp = output.get("base_resp", {})
                if base_resp.get("status_code", -1) != 0:
                    raise Exception(f"API 错误: {base_resp.get('status_msg', 'unknown')}")
                audio_hex = output.get("data", {}).get("audio", "")
                if not audio_hex:
                    raise Exception("响应中没有音频数据")
                audio_bytes = bytes.fromhex(audio_hex)

        tmp_dir = tempfile.gettempdir()
        filepath = os.path.join(tmp_dir, f"aliyun_minimax_{uuid.uuid4().hex[:8]}.wav")
        with open(filepath, "wb") as f:
            f.write(audio_bytes)
        return filepath

    async def test(self) -> None:
        if not self.api_key or not self.voice_id:
            raise Exception("请检查 api_key 和 aliyun_minimax_voice 配置")
        await super().test()


class Main(Star):
    """阿里云百炼 MiniMax TTS - AstrBot 插件入口

    通过本插件，AstrBot 可以使用阿里云百炼平台上的 MiniMax 语音合成模型。
    Provider 适配器由 @register_provider_adapter 自动注册，
    此类仅用于通过 AstrBot 的插件加载器检测。
    """

    def __init__(self, context: "RegisterContext"):
        super().__init__(context)
        logger.info("aliyun_minimax_tts 插件已加载")
        logger.info("TTS 适配器已注册，可在配置中选择 type=aliyun_minimax_tts")
