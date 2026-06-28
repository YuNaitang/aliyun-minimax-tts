"""
helloworld - AstrBot 示例插件

演示最基本的 AstrBot 插件结构：
  - 继承 Star 基类
  - 使用 @filter.command 注册指令
  - 使用 yield event.plain_result() 回复消息

更多文档：https://docs.astrbot.app/dev/star/plugin-new
"""
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star
from astrbot.api import logger


class HelloWorldPlugin(Star):
    """AstrBot 示例插件"""

    def __init__(self, context: Context):
        super().__init__(context)
        logger.info("HelloWorldPlugin 已加载")

    @filter.command("helloworld")
    async def helloworld(self, event: AstrMessageEvent):
        """发送 `/helloworld` 触发"""
        user_name = event.get_sender_name()
        logger.info(f"用户 {user_name} 触发了 helloworld 指令")
        yield event.plain_result(f"Hello, {user_name}! 👋")

    @filter.command("ping")
    async def ping(self, event: AstrMessageEvent):
        """发送 `/ping` 检查插件存活"""
        yield event.plain_result("pong! 🏓")

    async def terminate(self):
        """插件被卸载/停用时调用（可选）"""
        logger.info("HelloWorldPlugin 已卸载")
