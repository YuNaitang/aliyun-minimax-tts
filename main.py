import os
import uuid
import json
import tempfile
from pathlib import Path
import aiohttp

from astrbot.api.star import Star, register
from astrbot.api import logger
from astrbot.core.provider.entities import ProviderType, ProviderMetaData
from astrbot.core.provider.provider import TTSProvider
from astrbot.core.provider.register import provider_cls_map, provider_registry


_PROVIDER_TYPE = "aliyun_minimax_tts"
_PROVIDER_DESC = "阿里云百炼 MiniMax TTS"


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
    """阿里云百炼 MiniMax TTS - AstrBot 插件入口"""

    _DEFAULT_CONFIG = {
        "type": _PROVIDER_TYPE,
        "id": "tts-aliyun-minimax",
        "provider_type": "text_to_speech",
        "enable": True,
        "api_key": "",
        "model": "MiniMax/speech-2.8-hd",
        "aliyun_minimax_voice": "",
        "aliyun_minimax_speed": 1.0,
        "aliyun_minimax_volume": 1.0,
        "aliyun_minimax_pitch": 0,
        "aliyun_minimax_sample_rate": 44100,
        "timeout": 60,
    }

    def __init__(self, context: "RegisterContext"):
        super().__init__(context)
        # 手动注册 Provider 适配器（避免 AstrBot 重复扫描导致冲突）
        self._register_provider()
        # 自动将 TTS 配置写入 cmd_config.json（如果不存在）
        self._ensure_config(context)
        logger.info(f"aliyun_minimax_tts 插件已加载")

    def _register_provider(self) -> None:
        """将 Provider 适配器注册/更新到 AstrBot 的 Provider 系统"""
        metadata = ProviderMetaData(
            id="default",
            model=None,
            type=_PROVIDER_TYPE,
            provider_type=ProviderType.TEXT_TO_SPEECH,
            desc=_PROVIDER_DESC,
            cls_type=ProviderAliyunMiniMaxTTS,
        )
        if _PROVIDER_TYPE in provider_cls_map:
            # 已存在则替换为最新版（解决旧版注册被缓存的问题）
            old = provider_cls_map[_PROVIDER_TYPE]
            if old.cls_type is not ProviderAliyunMiniMaxTTS:
                provider_cls_map[_PROVIDER_TYPE] = metadata
                # 也更新 registry 中的记录
                for i, item in enumerate(provider_registry):
                    if item.type == _PROVIDER_TYPE:
                        provider_registry[i] = metadata
                        break
                logger.info(f"Provider 已更新: {_PROVIDER_TYPE}")
            else:
                logger.info(f"Provider 已注册且为最新，跳过")
            return

        provider_cls_map[_PROVIDER_TYPE] = metadata
        provider_registry.append(metadata)
        logger.info(f"Provider 适配器已注册: {_PROVIDER_TYPE}")

    def _find_astrbot_root(self) -> Path:
        """向上搜索目录树，寻找 AstrBot 根目录（包含 data/cmd_config.json 的目录）"""
        current = Path(__file__).resolve().parent
        for _ in range(10):  # 最多向上搜 10 层
            if (current / "data" / "cmd_config.json").exists():
                return current
            parent = current.parent
            if parent == current:
                break
            current = parent
        raise FileNotFoundError("无法定位 AstrBot 根目录（未找到 data/cmd_config.json）")

    def _ensure_config(self, context: "RegisterContext") -> None:
        """检查 cmd_config.json 中是否存在 TTS 配置，不存在则自动添加"""
        try:
            astrbot_root = self._find_astrbot_root()
            config_path = astrbot_root / "data" / "cmd_config.json"
            logger.info(f"AstrBot 根目录: {astrbot_root}")

            if not config_path.exists():
                logger.warning(f"未找到 cmd_config.json: {config_path}，跳过自动配置")
                return

            # 读取配置
            with open(config_path, encoding="utf-8-sig") as f:
                cfg = json.load(f)

            # 检查是否已有我们的 TTS 配置
            provider_list = cfg.get("provider", [])
            for p in provider_list:
                if p.get("type") == _PROVIDER_TYPE:
                    logger.info(f"TTS 配置已存在，跳过自动写入")
                    return

            # 添加默认配置
            cfg.setdefault("provider", []).append(self._DEFAULT_CONFIG)
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(cfg, f, ensure_ascii=False, indent=2)

            logger.info(f"✓ 已自动添加 TTS 配置到 cmd_config.json，请填写 api_key 和 voice 后重启生效")

        except Exception as e:
            logger.warning(f"自动写入 TTS 配置失败: {e}")
