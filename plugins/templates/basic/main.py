"""
插件名称 - AstrBot 插件

功能描述：请在此处描述你的插件功能。

更多文档：https://docs.astrbot.app/en/dev/star/plugin-new
"""
from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star
from astrbot.api import logger


class YourPlugin(Star):
    """请将 YourPlugin 替换为你的插件类名"""

    def __init__(self, context: Context):
        super().__init__(context)
        logger.info("YourPlugin 已加载")

    # ===== 注册指令 =====
    # @filter.command("指令名")      # 注册 /指令名
    # @filter.command_group("组名")  # 注册指令组
    #
    # ===== 回复方式 =====
    # yield event.plain_result("文本")           # 纯文本回复
    # yield event.image_result("url或路径")      # 图片回复
    # yield event.chain_result([...])            # 复合消息
    #
    # ===== 获取信息 =====
    # user_name = event.get_sender_name()        # 发送者名称
    # user_id   = event.get_sender_id()          # 发送者 ID
    # msg_str   = event.message_str              # 消息原文
    # msg_obj   = event.message_obj              # 消息对象

    @filter.command("hello")
    async def hello(self, event: AstrMessageEvent):
        """指令示例：发送 /hello 触发"""
        user_name = event.get_sender_name()
        yield event.plain_result(f"你好, {user_name}! ⭐")

    @filter.command("echo")
    async def echo(self, event: AstrMessageEvent):
        """指令示例：发送 /echo <内容> 触发

        获取指令参数：event.message_str
        """
        # 去掉 /echo 前缀获取参数
        args = event.message_str.strip()
        if args.startswith("/echo "):
            args = args[6:].strip()
        if args:
            yield event.plain_result(f"你说: {args}")
        else:
            yield event.plain_result("请输入要复读的内容，例如: /echo 你好")

    async def terminate(self):
        """插件被卸载时调用（可选）"""
        logger.info("YourPlugin 已卸载")
