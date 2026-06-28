"""
MemosNotes - AstrBot Memos 备忘录/日记/知识库集成插件

功能:
  - 命令式 CRUD: /memos (或 /mn) create|list|get|update|delete|help
                    pin|unpin|archive|restore
  - LLM Tool: write_diary         — 自然语言写日记（格式：📖 日期 + 内容）
  - LLM Tool: save_knowledge      — 自动保存知识到 Memos（格式：【知识】+ #标签）
  - LLM Tool: search_memos        — 从 Memos 搜索历史知识

配置 (通过 WebUI 或 _conf_schema.json):
  - memos_url:  Memos 实例地址 (例如 https://memos.example.com)
  - memos_token: Memos API 访问令牌

平台适配:
  - get 指令使用 Nodes 合并转发格式返回，分三段（Front Matter / 内容 / 附件）
  - 其他指令使用 plain_result 返回
"""
import asyncio
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star
from astrbot.api import logger
from astrbot.core.message.components import Plain, Node, Nodes
from .client import MemosClient


class MemosNotesPlugin(Star):
    """连接到自建 Memos 实例，管理备忘录、日记和知识库"""

    def __init__(self, context: Context, config: dict = None):
        super().__init__(context)
        # ---------- 读取插件配置 ----------
        if config is not None and isinstance(config, dict):
            memos_url = (config.get("memos_url") or "").strip()
            memos_token = (config.get("memos_token") or "").strip()
        else:
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

        # AstrBot 的 @filter.command 会剥掉 / 前缀
        parts = text.split(maxsplit=1)
        if parts[0] in ("memos", "mn"):
            rest = parts[1].strip() if len(parts) > 1 else ""
        else:
            rest = text

        if not rest:
            yield event.plain_result(
                "📝 MemosNotes\n"
                "用法: /memos <子命令> [参数]\n"
                "子命令: create, list, get, update, delete,\n"
                "        pin, unpin, archive, restore, help\n"
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
        elif subcmd == "pin":
            async for result in self._cmd_pin(event, args):
                yield result
        elif subcmd == "unpin":
            async for result in self._cmd_unpin(event, args):
                yield result
        elif subcmd == "archive":
            async for result in self._cmd_archive(event, args):
                yield result
        elif subcmd == "restore":
            async for result in self._cmd_restore(event, args):
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
            "/memos create [-p|--public|--protected] <内容>  创建备忘录（默认私有）\n"
            "/memos list [数量]    列出最近备忘录\n"
            "/memos get <ID>       查看单条详情\n"
            "/memos update <ID> <内容>  更新备忘录\n"
            "/memos delete <ID>    删除备忘录\n"
            "/memos pin <ID>       置顶备忘录\n"
            "/memos unpin <ID>     取消置顶\n"
            "/memos archive <ID>   归档备忘录\n"
            "/memos restore <ID>   恢复归档\n"
            "/memos help           显示本帮助\n"
            "快捷别名: /mn\n"
            "──────────────\n"
            "💡 LLM 也可以:\n"
            "   · 写日记（格式：📖 2026-06-28 + 内容）\n"
            "   · 记知识（格式：【知识】标题 + #标签 + 详情）\n"
            "   · 查知识：说「查一下」「我有记录过吗」"
        )

    async def _cmd_create(self, event: AstrMessageEvent, args: str):
        if not args:
            yield event.plain_result("❌ 用法: /memos create [-p | --public | --protected] <内容>")
            return

        visibility = "PRIVATE"
        content = args
        if content.startswith("--public"):
            visibility = "PUBLIC"
            content = content[len("--public"):].strip()
        elif content.startswith("-p "):
            visibility = "PUBLIC"
            content = content[len("-p "):].strip()
        elif content.startswith("--protected"):
            visibility = "PROTECTED"
            content = content[len("--protected"):].strip()

        if not content:
            yield event.plain_result("❌ 内容不能为空。")
            return

        memo = await self.client.create_memo(content=content, visibility=visibility)
        if memo is None:
            yield event.plain_result("❌ 创建失败，请检查配置和网络。")
            return

        memo_name = memo.get("name", "")
        memo_id = memo_name.split("/")[-1] if "/" in memo_name else memo.get("id", "?")
        tags = memo.get("tags", [])
        tag_str = f" #{' #'.join(tags)}" if tags else ""
        yield event.plain_result(f"✅ 备忘录 #{memo_id} 已创建（{visibility}）。{tag_str}")

    async def _cmd_list(self, event: AstrMessageEvent, args: str):
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
            content = (m.get("content", "") or "").strip()
            snippet = content.replace("\n", " ")[:60]
            if len(content.replace("\n", " ")) > 60:
                snippet += "……"
            tags = m.get("tags", [])
            tag_str = f"  #{' #'.join(tags)}" if tags else ""
            pinned = "📌 " if m.get("pinned") else ""
            lines.append(f"{pinned}#{memo_id}{tag_str}")
            lines.append(f"  {snippet}")
            lines.append("")  # 空行分隔
        yield event.plain_result("\n".join(lines))

    async def _cmd_get(self, event: AstrMessageEvent, args: str):
        if not args:
            yield event.plain_result("❌ 用法: /memos get <备忘录ID>")
            return

        memo_id = args.split()[0].strip().lstrip("#")
        if not memo_id:
            yield event.plain_result("❌ ID 不能为空。")
            return

        memo = await self.client.get_memo(memo_id)
        if memo is None:
            yield event.plain_result(f"❌ 未找到备忘录 #{memo_id}。")
            return

        # ---- 构建元数据 ----
        memo_name = memo.get("name", "")
        memo_id = memo_name.split("/")[-1] or memo.get("id", "?")
        content = (memo.get("content") or "").strip()
        visibility = memo.get("visibility", "PRIVATE")
        created = memo.get("createTime", "")
        updated = memo.get("updateTime", "")
        state = memo.get("state", "NORMAL")
        creator = memo.get("creator", "").replace("users/", "")
        tags = memo.get("tags", [])
        title = memo.get("snippet", "") or content[:60] if content else ""
        pinned = "📌 " if memo.get("pinned") else ""
        tag_str = " #".join(tags) if tags else "（无标签）"

        front_matter = (
            f"{pinned}#{memo_id}  标题: {title}\n"
            f"作者: {creator}  状态: {'正常' if state == 'NORMAL' else '已归档'}\n"
            f"可见性: {visibility}  标签: #{tag_str}\n"
            f"创建: {created}\n"
            f"更新: {updated}"
        )

        attachments = memo.get("attachments", [])
        if attachments:
            attach_lines = [f"  - {a.get('name', '未命名')} ({a.get('type', '未知')})" for a in attachments]
            attachment_text = "📎 附件\n" + "\n".join(attach_lines)
        else:
            attachment_text = "📎 无附件"

        # ---- 按平台选择发送方式 ----
        platform = event.get_platform_name()
        # 支持合并转发的平台: aiocqhttp, qq_official, qq_official_webhook
        can_forward = platform in ("aiocqhttp", "qq_official", "qq_official_webhook")

        if can_forward:
            nodes = Nodes(nodes=[
                Node(content=[Plain(text=front_matter)], name="📋 MemosNotes", uin="0"),
                Node(content=[Plain(text=content or "（空）")], name="📝 内容", uin="0"),
                Node(content=[Plain(text=attachment_text)], name="📎 附件", uin="0"),
            ])
            yield event.chain_result([nodes])
        else:
            # 其他平台降级为纯文本 + 分隔线
            yield event.plain_result(
                front_matter
                + "\n\n──────\n\n"
                + (content or "（空）")
                + "\n\n──────\n\n"
                + attachment_text
            )

    async def _cmd_update(self, event: AstrMessageEvent, args: str):
        if not args:
            yield event.plain_result("❌ 用法: /memos update <ID> <新内容>")
            return

        parts = args.split(maxsplit=1)
        if len(parts) < 2:
            yield event.plain_result("❌ 用法: /memos update <ID> <新内容>")
            return

        memo_id = parts[0].strip().lstrip("#")
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

        memo_id = args.split()[0].strip().lstrip("#")
        if not memo_id:
            yield event.plain_result("❌ ID 不能为空。")
            return

        success = await self.client.delete_memo(memo_id)
        if not success:
            yield event.plain_result(f"❌ 删除备忘录 #{memo_id} 失败。")
            return

        yield event.plain_result(f"✅ 备忘录 #{memo_id} 已删除。")

    # ------------------------------------------------------------------
    # 置顶 / 归档
    # ------------------------------------------------------------------

    async def _cmd_pin(self, event: AstrMessageEvent, args: str):
        if not args:
            yield event.plain_result("❌ 用法: /memos pin <备忘录ID>")
            return
        memo_id = args.split()[0].strip().lstrip("#")
        if not memo_id:
            yield event.plain_result("❌ ID 不能为空。")
            return
        memo = await self.client.update_memo(memo_id, pinned=True)
        if memo is None:
            yield event.plain_result(f"❌ 置顶失败。")
            return
        yield event.plain_result(f"📌 备忘录 #{memo_id} 已置顶。")

    async def _cmd_unpin(self, event: AstrMessageEvent, args: str):
        if not args:
            yield event.plain_result("❌ 用法: /memos unpin <备忘录ID>")
            return
        memo_id = args.split()[0].strip().lstrip("#")
        if not memo_id:
            yield event.plain_result("❌ ID 不能为空。")
            return
        memo = await self.client.update_memo(memo_id, pinned=False)
        if memo is None:
            yield event.plain_result(f"❌ 取消置顶失败。")
            return
        yield event.plain_result(f"📌 备忘录 #{memo_id} 已取消置顶。")

    async def _cmd_archive(self, event: AstrMessageEvent, args: str):
        if not args:
            yield event.plain_result("❌ 用法: /memos archive <备忘录ID>")
            return
        memo_id = args.split()[0].strip().lstrip("#")
        if not memo_id:
            yield event.plain_result("❌ ID 不能为空。")
            return
        memo = await self.client.update_memo(memo_id, state="ARCHIVED")
        if memo is None:
            yield event.plain_result(f"❌ 归档失败。")
            return
        yield event.plain_result(f"📦 备忘录 #{memo_id} 已归档。")

    async def _cmd_restore(self, event: AstrMessageEvent, args: str):
        if not args:
            yield event.plain_result("❌ 用法: /memos restore <备忘录ID>")
            return
        memo_id = args.split()[0].strip().lstrip("#")
        if not memo_id:
            yield event.plain_result("❌ ID 不能为空。")
            return
        memo = await self.client.update_memo(memo_id, state="NORMAL")
        if memo is None:
            yield event.plain_result(f"❌ 恢复失败。")
            return
        yield event.plain_result(f"📦 备忘录 #{memo_id} 已恢复。")

    # ------------------------------------------------------------------
    # LLM 工具 — 自然语言写日记
    # ------------------------------------------------------------------

    @filter.llm_tool(name="write_diary")
    async def write_diary(self, event: AstrMessageEvent, content: str, tag: str = ""):
        """Write a diary entry to Memos. 当用户想记录事情、写日记时，使用此工具。格式：以 📖 开头，包含日期，内容尽量完整保留原始语言。

        Args:
            content(string): 日记的完整内容。
            tag(string): 可选标签，如 diary、daily、生活。自动添加 # 前缀。
        """
        if self.client is None:
            yield event.plain_result("❌ MemosNotes 未配置。")
            return

        # 如果有标签，追加到内容末尾让 Memos 自动提取
        full_content = content
        if tag:
            tag_clean = tag.strip().strip("#")
            if tag_clean:
                full_content += f"\n\n#{tag_clean}"

        memo = await self.client.create_memo(content=full_content, visibility="PRIVATE")
        if memo is None:
            yield event.plain_result("❌ 保存失败。")
            return

        memo_name = memo.get("name", "")
        memo_id = memo_name.split("/")[-1] if "/" in memo_name else memo.get("id", "?")
        tags = memo.get("tags", [])
        tag_str = f" #{' #'.join(tags)}" if tags else ""
        logger.info(f"write_diary: 已保存 #{memo_id}{tag_str}")
        yield event.plain_result(f"✅ 日记已保存 #{memo_id}。{tag_str}")

    # ------------------------------------------------------------------
    # LLM 工具 — 知识库读写
    # ------------------------------------------------------------------

    @filter.llm_tool(name="save_knowledge")
    async def save_knowledge(self, event: AstrMessageEvent, content: str, tags: str = ""):
        """Save a knowledge note to Memos knowledge base. 当用户在对话中提到有用的知识点、技巧、经验总结时，使用此工具保存。内容应包含标题+详情。配合其他工具使用，完成用户任务后自动记录。

        Args:
            content(string): 知识内容。格式：【知识】标题 + 换行 + 详情描述。
            tags(string): 逗号/空格分隔的标签，如 \"运维 nginx docker\"。每个标签自动添加 # 前缀。
        """
        if self.client is None:
            yield event.plain_result("❌ MemosNotes 未配置。")
            return

        # 追加标签让 Memos 自动提取
        full_content = content
        if tags:
            tag_items = [f"#{t.strip().strip('#')}" for t in tags.replace("，", ",").replace(" ", " ").split(",") if t.strip()]
            if tag_items:
                full_content += "\n\n" + " ".join(tag_items)

        memo = await self.client.create_memo(content=full_content, visibility="PRIVATE")
        if memo is None:
            yield event.plain_result("❌ 知识保存失败。")
            return

        memo_name = memo.get("name", "")
        memo_id = memo_name.split("/")[-1] if "/" in memo_name else memo.get("id", "?")
        tags_out = memo.get("tags", [])
        tag_str = f" #{' #'.join(tags_out)}" if tags_out else ""
        logger.info(f"save_knowledge: 已保存 #{memo_id}{tag_str}")
        yield event.plain_result(f"✅ 知识已保存 #{memo_id}。{tag_str}")

    @filter.llm_tool(name="search_memos")
    async def search_memos(self, event: AstrMessageEvent, query: str, limit: str = "10"):
        """Search recent memos from Memos knowledge base. 当需要查询历史知识、查找之前记录的信息、回顾笔记时，使用此工具检索。结果由 AI 自行做语义匹配。

        Args:
            query(string): 搜索关键词或查询意图描述。
            limit(string): 返回结果数量上限，最大 50，默认 10。
        """
        if self.client is None:
            yield event.plain_result("❌ MemosNotes 未配置。")
            return

        try:
            page_size = max(1, min(int(limit), 50))
        except (ValueError, TypeError):
            page_size = 10

        result = await self.client.list_memos(page_size=page_size)
        if result is None:
            yield event.plain_result("❌ 查询失败。")
            return

        memos = result.get("memos", [])
        if not memos:
            yield event.plain_result("📭 知识库中暂无内容。")
            return

        lines = ["📚 以下是 Memos 知识库中找到的相关内容："]
        for m in memos:
            memo_name = m.get("name", "")
            memo_id = memo_name.split("/")[-1] if "/" in memo_name else m.get("id", "?")
            snippet = m.get("content", "") or ""
            if len(snippet) > 300:
                snippet = snippet[:300] + "……"
            created = m.get("createTime", "")
            tags = m.get("tags", [])
            tag_str = f" #{' #'.join(tags)}" if tags else ""
            pinned = "📌 " if m.get("pinned") else ""

            lines.append("")
            lines.append(f"━━━ {pinned}#{memo_id}{tag_str} ━━━")
            if created:
                lines.append(f"📅 {created}")
            lines.append(snippet)

        yield event.plain_result("\n".join(lines))
