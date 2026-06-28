# MemosNotes — AstrBot Memos 备忘录/日记集成插件

连接到自建 [Memos](https://usememos.com/) 实例，通过 AstrBot 命令和 LLM 自然语言管理备忘录。

## 功能

- **命令 CRUD**: 通过 `/memos` 指令创建、查询、修改、删除备忘录
- **快捷别名**: `/mn` 是 `/memos` 的快捷方式
- **LLM 自然语言写日记**: 对 bot 说"写日记"、"记录今天"等，LLM 自动调用工具保存

## 配置

在 AstrBot WebUI 管理面板中设置：

| 配置项 | 说明 |
|--------|------|
| `memos_url` | Memos 实例地址，例如 `https://memos.example.com` |
| `memos_token` | Memos API 访问令牌（设置 → 我的账户 → 访问令牌） |

## 指令

| 命令 | 说明 |
|------|------|
| `/memos create <内容>` | 创建备忘录 |
| `/memos list [n]` | 列出最近 n 条（默认 10） |
| `/memos get <ID>` | 查看单条详情 |
| `/memos update <ID> <内容>` | 更新备忘录内容 |
| `/memos delete <ID>` | 删除备忘录 |
| `/memos help` | 显示帮助 |
| `/mn ...` | `/memos` 的快捷别名 |

## 开发者

**作者**: YuNaitang（鱼鼐棠）
**仓库**: https://github.com/YuNaitang/astrbot_plugin_memosnotes
