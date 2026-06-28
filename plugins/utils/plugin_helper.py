"""AstrBot 插件开发工具函数

提供在插件开发期间使用的辅助函数，不发布到插件中。
"""
from pathlib import Path
from datetime import datetime


def find_plugins_dir(root: Path = None) -> Path:
    """查找 AstrBot 的插件目录

    搜索顺序：
    1. 当前项目下的 plugins/
    2. AstrBot 默认的 data/plugins/
    """
    root = root or Path.cwd()

    # 搜索当前项目
    candidates = [
        root / "plugins",
        root / "data" / "plugins",
    ]

    for path in candidates:
        if path.exists():
            return path

    return root / "plugins"


def create_plugin_stub(name: str, author: str = "YourName", desc: str = ""):
    """快速创建插件脚手架

    Args:
        name: 插件名称（用作目录名和类名）
        author: 作者名
        desc: 插件描述
    """
    from pathlib import Path

    plugin_dir = Path.cwd() / "plugins" / name
    plugin_dir.mkdir(parents=True, exist_ok=True)

    class_name = ''.join(word.capitalize() for word in name.replace('-', '_').split('_'))
    if not class_name.endswith("Plugin"):
        class_name += "Plugin"

    # main.py
    main_content = f'''"""
{name} - AstrBot 插件

描述: {desc or name}
"""
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star
from astrbot.api import logger


class {class_name}(Star):
    """{desc or name}"""

    def __init__(self, context: Context):
        super().__init__(context)
        logger.info("{class_name} 已加载")

    @filter.command("{name}")
    async def handle_command(self, event: AstrMessageEvent):
        """请替换为你的指令逻辑"""
        yield event.plain_result(f"这是 {name} 插件的响应")

    async def terminate(self):
        logger.info("{class_name} 已卸载")
'''

    metadata_content = f'''name: astrbot_plugin_{name}
author: {author}
desc: {desc or "AstrBot 插件"}
version: "0.1.0"
astrbot_version: ">=4.16"
'''

    (plugin_dir / "main.py").write_text(main_content, encoding="utf-8")
    (plugin_dir / "metadata.yaml").write_text(metadata_content, encoding="utf-8")

    print(f"✅ 插件 '{name}' 已创建: {plugin_dir}")
    return plugin_dir
