"""
MemosNotes - AstrBot Memos 备忘录/日记集成插件

功能:
  - 命令式 CRUD: /memos (或 /mn) create|list|get|update|delete|help
  - LLM Tool: write_diary — 让 LLM 通过自然语言写日记

配置 (通过 WebUI 或 _conf_schema.json):
  - memos_url:  Memos 实例地址 (例如 https://memos.example.com)
  - memos_token: Memos API 访问令牌
"""
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star
from astrbot.api import logger
from .client import MemosClient


class MemosNotesPlugin(Star):
    """连接到自建 Memos 实例，管理备忘录和日记"""

    def __init__(self, context: Context, config: dict = None):
        super().__init__(context)
        # ---------- 读取插件配置 ----------
        if config is not None and isinstance(config, dict):
            memos_url = (config.get("memos_url") or "").strip()
            memos_token = (config.get("memos_token") or "").strip()
        else:
            # 回退到 context.get_config()
            cfg = context.get_config() or {}
            memos_url = (cfg.get("memos_url") or "").strip()
            memos_token = (cfg.get("memos_token") or "").strip()

        if not memos_url or not memos_token:
            logger.warning(
                "MemosNotesPlugin: memos_url 或 memos_token 未配置，"
                "请在 WebUI 中设置。"
            )
            self.client = None
        else:
            self.client = MemosClient(memos_url, memos_token)
            logger.info("MemosNotesPlugin 已加载。")

    # ------------------------------------------------------------------
    # 生命周期
    # ------------------------------------------------------------------

    async def terminate(self):
        """插件卸载时关闭 HTTP 客户端"""
        if self.client:
            await self.client.close()
            logger.info("MemosNotesPlugin 已卸载。")

    # ------------------------------------------------------------------
    # 命令入口: /memos 和 /mn
    # ------------------------------------------------------------------

    @filter.command("memos")
    async def memos(self, event: AstrMessageEvent):
        """Memos 备忘录管理"""
        async for result in self._route(event):
            yield result

    @filter.command("mn")
    async def mn(self, event: AstrMessageEvent):
        """Memos 快捷别名"""
        async for result in self._route(event):
            yield result

    # ------------------------------------------------------------------
    # 子命令路由
    # ------------------------------------------------------------------

    async def _route(self, event: AstrMessageEvent):
        """解析子命令并分发"""
        if self.client is None:
            yield event.plain_result(
                "❌ MemosNotes 未配置，请在 WebUI 中设置 memos_url 和 memos_token。"
            )
            return

        text = event.message_str.strip()

        # AstrBot 的 @filter.command 会剥掉 / 前缀，
        # 所以 event.message_str 可能是 "memos help" 或仅 "help"
        parts = text.split(maxsplit=1)
        if parts[0] in ("memos", "mn"):
            # 命令名还在 message_str 中，去掉它
            rest = parts[1].strip() if len(parts) > 1 else ""
        else:
            # 只有子命令+参数
            rest = text

        if not rest:
            yield event.plain_result(
                "📝 MemosNotes\n"
                "用法: /memos <子命令> [参数]\n"
                "子命令: create, list, get, update, delete, help\n"
                "快捷别名: /mn"
            )
            return

        subcmd_parts = rest.split(maxsplit=1)
        subcmd = subcmd_parts[0].lower()
        args = subcmd_parts[1].strip() if len(subcmd_parts) > 1 else ""

        if subcmd == "help":
            async for result in self._help(event):
                yield result
        elif subcmd == "create":
            async for result in self._cmd_create(event, args):
                yield result
        elif subcmd == "list":
            async for result in self._cmd_list(event, args):
                yield result
        elif subcmd == "get":
            async for result in self._cmd_get(event, args):
                yield result
        elif subcmd == "update":
            async for result in self._cmd_update(event, args):
                yield result
        elif subcmd == "delete":
            async for result in self._cmd_delete(event, args):
                yield result
        else:
            yield event.plain_result(
                f"❌ 未知子命令: {subcmd}。使用 /memos help 查看帮助。"
            )

    # ------------------------------------------------------------------
    # 子命令实现
    # ------------------------------------------------------------------

    async def _help(self, event: AstrMessageEvent):
        yield event.plain_result(
            "📝 MemosNotes 帮助\n"
            "──────────────\n"
            "/memos create <内容>   创建备忘录\n"
            "/memos list [数量]    列出最近备忘录\n"
            "/memos get <ID>       查看单条详情\n"
            "/memos update <ID> <内容>  更新备忘录\n"
            "/memos delete <ID>    删除备忘录\n"
            "/memos help           显示本帮助\n"
            "快捷别名: /mn\n"
            "──────────────\n"
            "💡 LLM 自然语言写日记:\n"
            "   直接对 bot 说「写日记」「记录今天」等即可"
        )

    async def _cmd_create(self, event: AstrMessageEvent, args: str):
        if not args:
            yield event.plain_result("❌ 用法: /memos create <备忘录内容>")
            return

        memo = await self.client.create_memo(content=args, visibility="PRIVATE")
        if memo is None:
            yield event.plain_result("❌ 创建失败，请检查配置和网络。")
            return

        # Memos API 返回的 name 格式为 "memos/{id}"
        memo_name = memo.get("name", "")
        memo_id = memo_name.split("/")[-1] if "/" in memo_name else memo.get("id", "?")
        yield event.plain_result(f"✅ 备忘录 #{memo_id} 已创建。")

    async def _cmd_list(self, event: AstrMessageEvent, args: str):
        # 解析可选的数量参数
        page_size = 10
        if args:
            try:
                page_size = max(1, min(int(args.split()[0]), 50))
            except (ValueError, IndexError):
                pass

        result = await self.client.list_memos(page_size=page_size)
        if result is None:
            yield event.plain_result("❌ 查询失败，请检查配置和网络。")
            return

        memos = result.get("memos", [])
        if not memos:
            yield event.plain_result("📭 暂无备忘录。")
            return

        lines = [f"📋 最近 {len(memos)} 条备忘录:"]
        for m in memos:
            memo_name = m.get("name", "")
            memo_id = memo_name.split("/")[-1] if "/" in memo_name else m.get("id", "?")
            content = (m.get("content", "") or "").replace("\n", " ")[:80]
            lines.append(f"  #{memo_id}  {content}")
        yield event.plain_result("\n".join(lines))

    async def _cmd_get(self, event: AstrMessageEvent, args: str):
        if not args:
            yield event.plain_result("❌ 用法: /memos get <备忘录ID>")
            return

        memo_id = args.split()[0].strip()
        if not memo_id:
            yield event.plain_result("❌ ID 不能为空。")
            return

        memo = await self.client.get_memo(memo_id)
        if memo is None:
            yield event.plain_result(f"❌ 未找到备忘录 #{memo_id}。")
            return

        content = (memo.get("content") or "").strip()
        visibility = memo.get("visibility", "PRIVATE")
        created = memo.get("createTime", "")
        pinned = "📌 已置顶" if memo.get("pinned") else ""

        yield event.plain_result(
            f"📝 备忘录 #{memo_id}  {pinned}\n"
            f"可见性: {visibility}\n"
            f"时间: {created}\n"
            f"──────────────\n"
            f"{content}"
        )

    async def _cmd_update(self, event: AstrMessageEvent, args: str):
        if not args:
            yield event.plain_result("❌ 用法: /memos update <ID> <新内容>")
            return

        parts = args.split(maxsplit=1)
        if len(parts) < 2:
            yield event.plain_result("❌ 用法: /memos update <ID> <新内容>")
            return

        memo_id = parts[0].strip()
        if not memo_id:
            yield event.plain_result("❌ ID 不能为空。")
            return

        new_content = parts[1].strip()
        if not new_content:
            yield event.plain_result("❌ 内容不能为空。")
            return

        memo = await self.client.update_memo(memo_id, content=new_content)
        if memo is None:
            yield event.plain_result(f"❌ 更新备忘录 #{memo_id} 失败。")
            return

        yield event.plain_result(f"✅ 备忘录 #{memo_id} 已更新。")

    async def _cmd_delete(self, event: AstrMessageEvent, args: str):
        if not args:
            yield event.plain_result("❌ 用法: /memos delete <备忘录ID>")
            return

        memo_id = args.split()[0].strip()
        if not memo_id:
            yield event.plain_result("❌ ID 不能为空。")
            return

        success = await self.client.delete_memo(memo_id)
        if not success:
            yield event.plain_result(f"❌ 删除备忘录 #{memo_id} 失败。")
            return

        yield event.plain_result(f"✅ 备忘录 #{memo_id} 已删除。")

    # ------------------------------------------------------------------
    # LLM 工具 — 自然语言写日记
    # ------------------------------------------------------------------

    @filter.llm_tool(name="write_diary")
    async def write_diary(self, event: AstrMessageEvent, content: str):
        """Write a diary entry to Memos. 当用户想记录事情、写日记、保存备忘时，使用此工具将内容写入 Memos。

        Args:
            content(string): 日记或备忘录的完整内容，保留原始语言。
        """
        if self.client is None:
            yield event.plain_result("❌ MemosNotes 未配置，无法保存。请联系管理员配置 memos_url 和 memos_token。")
            return

        memo = await self.client.create_memo(content=content, visibility="PRIVATE")
        if memo is None:
            yield event.plain_result("❌ 保存失败，请稍后重试。")
            return

        memo_name = memo.get("name", "")
        memo_id = memo_name.split("/")[-1] if "/" in memo_name else memo.get("id", "?")
        logger.info(f"write_diary: 已保存备忘录 #{memo_id}")
        yield event.plain_result(f"✅ 已保存为备忘录 #{memo_id}。")
