"""
Aliyun MiniMax TTS — AstrBot 阿里云百炼 MiniMax 语音合成适配器

通过阿里云百炼调用 MiniMax 语音合成模型，为 AstrBot 提供 TTS 能力。
支持音色克隆和本地音色管理。

命令:
  /voice clone <名称> <音频URL>  从音频文件克隆音色
  /voice list                   列出已克隆的音色
  /voice use <名称>             切换活跃音色
  /voice delete <名称>          从本地库删除音色
  /voice info                   显示当前 TTS 配置

配置项（自动写入 cmd_config.json）:
  - api_key:                 阿里云百炼 API Key
  - model:                   MiniMax/speech-2.8-hd
  - aliyun_minimax_voice:    音色 ID（必填）
  - aliyun_minimax_speed:    语速 0.5~2.0 (default: 1.0)
  - aliyun_minimax_volume:   音量 0~1.0 (default: 1.0)
  - aliyun_minimax_pitch:    音调 -12~12 (default: 0)
  - aliyun_minimax_sample_rate: 采样率 max 44100 (default: 44100)

音色库文件: data/config/astrbot_plugin_aliyun_minimax_voices.json
"""
import os
import uuid
import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path
import aiohttp

from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Star, register
from astrbot.api import logger
from astrbot.core.provider.entities import ProviderType, ProviderMetaData
from astrbot.core.provider.provider import TTSProvider
from astrbot.core.provider.register import provider_cls_map, provider_registry


_PROVIDER_TYPE = "aliyun_minimax_tts"
_PROVIDER_DESC = "阿里云百炼 MiniMax TTS"
_VOICES_FILE = "astrbot_plugin_aliyun_minimax_voices.json"


# ====================================================================
# 音色库管理器（本地 JSON 存储）
# ====================================================================

class VoiceManager:
    """管理本地音色库，提供增删改查功能

    音色库存储在 data/config/ 下，与 AstrBot 插件配置同级。
    MiniMax API 本身不支持查询和删除音色列表，因此所有管理
    操作基于本地持久化。
    """

    def __init__(self, astrbot_root: Path):
        self._path = astrbot_root / "data" / "config" / _VOICES_FILE
        self._data = self._load()

    def _load(self) -> dict:
        """从 JSON 文件读取音色库"""
        if self._path.exists():
            try:
                with open(self._path, encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError) as e:
                logger.warning(f"读取音色库失败，重置为空: {e}")
        return {"voices": [], "active": None}

    def save(self):
        """写入 JSON 文件"""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._path, "w", encoding="utf-8") as f:
            json.dump(self._data, f, ensure_ascii=False, indent=2)

    def add(self, name: str, voice_id: str, model: str, demo_audio: str = "") -> None:
        """添加音色记录（如已存在同名则更新）"""
        now = datetime.now(timezone.utc).isoformat()
        entry = {
            "name": name,
            "voice_id": voice_id,
            "model": model,
            "created_at": now,
            "demo_audio": demo_audio,
        }
        # 同名覆盖
        for i, v in enumerate(self._data["voices"]):
            if v["name"] == name:
                entry["created_at"] = v.get("created_at", now)
                self._data["voices"][i] = entry
                self.save()
                return
        self._data["voices"].append(entry)
        self.save()

    def delete(self, name: str) -> bool:
        """删除音色记录，如果正活跃则清除活跃标记"""
        before = len(self._data["voices"])
        self._data["voices"] = [v for v in self._data["voices"] if v["name"] != name]
        if self._data.get("active") == name:
            self._data["active"] = None
        self.save()
        return len(self._data["voices"]) < before

    def get(self, name: str) -> dict | None:
        """按名称查询音色"""
        for v in self._data["voices"]:
            if v["name"] == name:
                return v
        return None

    def list_all(self) -> list[dict]:
        """返回所有音色"""
        return list(self._data["voices"])

    def get_active_name(self) -> str | None:
        """获取活跃音色名称"""
        return self._data.get("active")

    def set_active(self, name: str) -> bool:
        """设置活跃音色，并更新 cmd_config.json 中 aliyun_minimax_voice"""
        voice = self.get(name)
        if not voice:
            return False
        self._data["active"] = name
        self.save()
        return True

    def path(self) -> Path:
        return self._path


# ====================================================================
# TTS Provider 适配器
# ====================================================================

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

    async def clone_voice(self, name: str, audio_url: str) -> dict:
        """调用阿里云百炼 MiniMax voice_clone API

        Args:
            name: 自定义音色标识（用作 voice_id）
            audio_url: 音频文件公网直链

        Returns:
            {"demo_audio": "...", "voice_id": "..."} 或抛出异常
        """
        if not self.api_key:
            raise Exception("API Key 未配置")

        # voice_id 规则：首字母英文，长度 8~256，允许字母数字-_-
        safe_name = name.strip().replace(" ", "_").replace(".", "_")
        # 取前 8 字符 + 简短 hash 防冲突
        voice_id = f"{safe_name[:8]}_{uuid.uuid4().hex[:6]}"

        payload = {
            "model": "MiniMax/speech-2.8-hd",
            "input": {
                "action": "voice_clone",
                "voice_id": voice_id,
                "audio_url": audio_url,
                "text": "你好，我是新克隆的音色，欢迎使用阿里云百炼语音合成服务。",
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
                    raise Exception(f"克隆失败: {base_resp.get('status_msg', 'unknown')}")
                demo_audio = output.get("demo_audio", "")

        return {"demo_audio": demo_audio, "voice_id": voice_id}

    async def test(self) -> None:
        if not self.api_key or not self.voice_id:
            raise Exception("请检查 api_key 和 aliyun_minimax_voice 配置")
        await super().test()


# ====================================================================
# 插件入口
# ====================================================================

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
        # 初始化音色管理器
        try:
            root = self._find_astrbot_root()
            self._voices = VoiceManager(root)
        except Exception as e:
            logger.warning(f"初始化音色管理器失败: {e}")
            self._voices = None
        logger.info("aliyun_minimax_tts 插件已加载")

    # ----------------------------------------------------------------
    # Provider 注册
    # ----------------------------------------------------------------

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
            old = provider_cls_map[_PROVIDER_TYPE]
            if old.cls_type is not ProviderAliyunMiniMaxTTS:
                provider_cls_map[_PROVIDER_TYPE] = metadata
                for i, item in enumerate(provider_registry):
                    if item.type == _PROVIDER_TYPE:
                        provider_registry[i] = metadata
                        break
                logger.info(f"Provider 已更新: {_PROVIDER_TYPE}")
            else:
                logger.info("Provider 已注册且为最新，跳过")
            return

        provider_cls_map[_PROVIDER_TYPE] = metadata
        provider_registry.append(metadata)
        logger.info(f"Provider 适配器已注册: {_PROVIDER_TYPE}")

    # ----------------------------------------------------------------
    # 配置管理
    # ----------------------------------------------------------------

    def _find_astrbot_root(self) -> Path:
        """向上搜索目录树，寻找 AstrBot 根目录（包含 data/cmd_config.json 的目录）"""
        current = Path(__file__).resolve().parent
        for _ in range(10):
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

            with open(config_path, encoding="utf-8-sig") as f:
                cfg = json.load(f)

            provider_list = cfg.get("provider", [])
            for p in provider_list:
                if p.get("type") == _PROVIDER_TYPE:
                    logger.info("TTS 配置已存在，跳过自动写入")
                    return

            cfg.setdefault("provider", []).append(self._DEFAULT_CONFIG)
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(cfg, f, ensure_ascii=False, indent=2)

            logger.info("已自动添加 TTS 配置到 cmd_config.json，请填写 api_key 和 voice 后重启生效")

        except Exception as e:
            logger.warning(f"自动写入 TTS 配置失败: {e}")

    # ----------------------------------------------------------------
    # 命令: /voice
    # ----------------------------------------------------------------

    @filter.command("voice")
    async def voice(self, event: AstrMessageEvent):
        """音色克隆与管理"""
        async for result in self._route_voice(event):
            yield result

    async def _route_voice(self, event: AstrMessageEvent):
        """解析 /voice 子命令"""
        text = event.message_str.strip()
        parts = text.split(maxsplit=1)
        if parts[0] == "voice":
            rest = parts[1].strip() if len(parts) > 1 else ""
        else:
            rest = text

        if not rest:
            yield event.plain_result(
                "🎙 音色管理\n"
                "用法:\n"
                "  /voice clone <名称> <音频URL>  从音频克隆新音色\n"
                "  /voice list                    列出已克隆的音色\n"
                "  /voice use <名称>              切换到指定音色\n"
                "  /voice delete <名称>            删除音色\n"
                "  /voice info                    查看当前 TTS 配置"
            )
            return

        subcmd_parts = rest.split(maxsplit=1)
        subcmd = subcmd_parts[0].lower()
        args = subcmd_parts[1].strip() if len(subcmd_parts) > 1 else ""

        if subcmd == "info":
            async for result in self._cmd_voice_info(event):
                yield result
        elif subcmd == "list":
            async for result in self._cmd_voice_list(event):
                yield result
        elif subcmd == "clone":
            async for result in self._cmd_voice_clone(event, args):
                yield result
        elif subcmd == "use":
            async for result in self._cmd_voice_use(event, args):
                yield result
        elif subcmd == "delete":
            async for result in self._cmd_voice_delete(event, args):
                yield result
        else:
            yield event.plain_result(f"❌ 未知子命令: {subcmd}。使用 /voice help 查看帮助。")

    async def _cmd_voice_info(self, event: AstrMessageEvent):
        """显示当前 TTS 配置"""
        try:
            root = self._find_astrbot_root()
            config_path = root / "data" / "cmd_config.json"
            if not config_path.exists():
                yield event.plain_result("❌ 无法读取 AstrBot 配置")
                return

            with open(config_path, encoding="utf-8-sig") as f:
                cfg = json.load(f)

            tts_config = None
            for p in cfg.get("provider", []):
                if p.get("type") == _PROVIDER_TYPE:
                    tts_config = p
                    break

            if not tts_config:
                yield event.plain_result("❌ 未找到 TTS 配置")
                return

            lines = [
                "🎙 TTS 当前配置",
                "───",
                f"状态: {'✅ 已启用' if tts_config.get('enable') else '⏸ 已禁用'}",
                f"模型: {tts_config.get('model', '未设置')}",
                f"音色 ID: {tts_config.get('aliyun_minimax_voice', '未设置') or '未设置'}",
                f"语速: {tts_config.get('aliyun_minimax_speed', 1.0)}",
                f"音量: {tts_config.get('aliyun_minimax_volume', 1.0)}",
                f"音调: {tts_config.get('aliyun_minimax_pitch', 0)}",
                f"采样率: {tts_config.get('aliyun_minimax_sample_rate', 44100)}",
            ]

            # 显示当前活跃音色
            if self._voices:
                active = self._voices.get_active_name()
                if active:
                    voice = self._voices.get(active)
                    lines.append(f"活跃音色: 🎤 {active}")
                    if voice and voice.get("demo_audio"):
                        lines.append(f"试听: {voice['demo_audio']}")
                else:
                    lines.append("活跃音色: 未设置（使用原始 voice_id）")

            lines.append(f"\n💡 提示: 用 /voice list 查看所有音色")
            yield event.plain_result("\n".join(lines))

        except Exception as e:
            yield event.plain_result(f"❌ 读取配置失败: {e}")

    async def _cmd_voice_list(self, event: AstrMessageEvent):
        """列出所有已克隆音色"""
        if not self._voices:
            yield event.plain_result("❌ 音色管理器未初始化")
            return

        voices = self._voices.list_all()
        if not voices:
            yield event.plain_result("📭 音色库为空。使用 /voice clone <名称> <音频URL> 创建第一个音色。")
            return

        active = self._voices.get_active_name()
        lines = [f"🎙 已克隆 {len(voices)} 个音色:"]
        for v in voices:
            marker = "🟢 " if v["name"] == active else "  "
            demo = " 🔊" if v.get("demo_audio") else ""
            lines.append(f"{marker}{v['name']}{demo}")
            lines.append(f"    ID: {v['voice_id']}  模型: {v.get('model', '-')}")
            if v.get("created_at"):
                lines.append(f"    创建: {v['created_at'][:19].replace('T', ' ')}")
        lines.append(f"\n💡 使用 /voice use <名称> 切换音色，/voice delete <名称> 删除")
        yield event.plain_result("\n".join(lines))

    async def _cmd_voice_clone(self, event: AstrMessageEvent, args: str):
        """克隆新音色"""
        # 解析参数: /voice clone <名称> <音频URL>
        parts = args.split(maxsplit=1)
        if len(parts) < 2:
            yield event.plain_result("❌ 用法: /voice clone <名称> <音频URL>\n示例: /voice clone 奶糖 https://example.com/audio.wav")
            return

        name = parts[0].strip()
        audio_url = parts[1].strip()

        if not name or not audio_url:
            yield event.plain_result("❌ 名称和音频 URL 不能为空")
            return

        if not audio_url.startswith(("http://", "https://")):
            yield event.plain_result("❌ 音频 URL 必须以 http:// 或 https:// 开头")
            return

        # 检查是否已存在同名音色
        if self._voices and self._voices.get(name):
            yield event.plain_result(f"❌ 音色「{name}」已存在。如需重新克隆，请先 /voice delete {name}")
            return

        # 获取 API Key（从已注册的 Provider 配置中读取）
        api_key = ""
        try:
            root = self._find_astrbot_root()
            config_path = root / "data" / "cmd_config.json"
            with open(config_path, encoding="utf-8-sig") as f:
                cfg = json.load(f)
            for p in cfg.get("provider", []):
                if p.get("type") == _PROVIDER_TYPE:
                    api_key = p.get("api_key", "")
                    break
        except Exception:
            pass

        if not api_key:
            yield event.plain_result("❌ 未配置阿里云百炼 API Key。请在 cmd_config.json 中填写 api_key。")
            return

        # 调用克隆 API
        yield event.plain_result(f"⏳ 正在克隆音色「{name}」… 请稍候（通常 10~30 秒）")

        provider = ProviderAliyunMiniMaxTTS(
            provider_config={"api_key": api_key, **self._DEFAULT_CONFIG},
            provider_settings={},
        )

        try:
            result = await provider.clone_voice(name, audio_url)
        except Exception as e:
            yield event.plain_result(f"❌ 克隆失败: {e}")
            return

        voice_id = result["voice_id"]
        demo_audio = result.get("demo_audio", "")

        # 保存到音色库
        if self._voices:
            self._voices.add(
                name=name,
                voice_id=voice_id,
                model="MiniMax/speech-2.8-hd",
                demo_audio=demo_audio,
            )

        # 默认设置为活跃音色
        if self._voices:
            self._voices.set_active(name)
            self._update_config_voice_id(voice_id)

        lines = [
            f"✅ 音色「{name}」克隆成功！",
            f"音色 ID: {voice_id}",
        ]
        if demo_audio:
            lines.append(f"试听: {demo_audio}")
        lines.append(f"\n💡 已自动设为活跃音色。重启 AstrBot 后生效。")
        yield event.plain_result("\n".join(lines))

    async def _cmd_voice_use(self, event: AstrMessageEvent, args: str):
        """切换活跃音色"""
        if not self._voices:
            yield event.plain_result("❌ 音色管理器未初始化")
            return

        name = args.strip()
        if not name:
            yield event.plain_result("❌ 用法: /voice use <音色名称>")
            return

        voice = self._voices.get(name)
        if not voice:
            yield event.plain_result(f"❌ 音色「{name}」不存在。使用 /voice list 查看所有音色。")
            return

        self._voices.set_active(name)
        self._update_config_voice_id(voice["voice_id"])

        yield event.plain_result(
            f"✅ 已切换到音色「{name}」\n"
            f"音色 ID: {voice['voice_id']}\n"
            f"💡 重启 AstrBot 后生效"
        )

    async def _cmd_voice_delete(self, event: AstrMessageEvent, args: str):
        """删除音色"""
        if not self._voices:
            yield event.plain_result("❌ 音色管理器未初始化")
            return

        name = args.strip()
        if not name:
            yield event.plain_result("❌ 用法: /voice delete <音色名称>")
            return

        if not self._voices.get(name):
            yield event.plain_result(f"❌ 音色「{name}」不存在。")
            return

        self._voices.delete(name)
        yield event.plain_result(f"🗑 音色「{name}」已从本地库删除。\n⚠ MiniMax 服务端可能保留该音色，如需彻底删除请联系阿里云。")

    # ----------------------------------------------------------------
    # 内部辅助
    # ----------------------------------------------------------------

    def _update_config_voice_id(self, voice_id: str) -> None:
        """更新 cmd_config.json 中的 aliyun_minimax_voice 字段"""
        try:
            root = self._find_astrbot_root()
            config_path = root / "data" / "cmd_config.json"
            with open(config_path, encoding="utf-8-sig") as f:
                cfg = json.load(f)

            for p in cfg.get("provider", []):
                if p.get("type") == _PROVIDER_TYPE:
                    p["aliyun_minimax_voice"] = voice_id
                    break

            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(cfg, f, ensure_ascii=False, indent=2)

            logger.info(f"已更新 cmd_config.json: aliyun_minimax_voice = {voice_id}")
        except Exception as e:
            logger.warning(f"更新 cmd_config.json 失败: {e}")
