# AstrBot 多插件开发项目

## 项目概述

本目录是 AstrBot 多插件开发工作区，管理多个 AstrBot 插件源码。

**作者**: YuNaitang（鱼鼐棠）

## 目录结构

- `plugins/` — 所有插件源码
- `plugins/helloworld/` — 示例插件（可复制作为新插件起点）
- `plugins/templates/basic/` — 插件基础模板
- `plugins/utils/` — 共享开发工具
- `plugins/astrbot_plugin_memosnotes/` — MemosNotes 插件
- `data/` — AstrBot 运行时数据

## 开发命令

```bash
# 运行 AstrBot
astrbot run

# 查看已安装插件
astrbot plug list
```

## 工作流程（重要）

每次修改文件时必须依次执行以下步骤：

1. **更新版本号** — 在 `metadata.yaml` 中递增 `version` 字段
2. **检查并更新文本描述** — 更新 `README.md` 和文档中的相关描述，确保与实际功能一致
3. **同步到 data/plugins** — 如果修改了 `plugins/<name>/` 下的文件，同步到 `data/plugins/<name>/`
4. **提交 Git** — 使用语义化 commit message，格式：`<type>(<scope>): <description>`，例如 `feat(memos): 添加创建备忘录命令`
5. **重启 AstrBot 测试** — 验证修改生效

> 这四个步骤缺一不可，每次修改文件都必须执行全流程。

## 版本号规范

遵循语义化版本 `MAJOR.MINOR.PATCH`：
- MAJOR: 不兼容的 API 修改
- MINOR: 向下兼容的功能新增
- PATCH: 向下兼容的问题修复

## 插件规范

每个插件必须包含：
- `main.py` — 入口文件，导出继承 `Star` 的类
- `metadata.yaml` — 元数据（name, author, desc, version, astrbot_version）
- `README.md` — 使用文档

插件类必须继承 `star.Star`，使用 `@filter.command("名称")` 注册指令，通过 `yield event.plain_result()` 回复。

## 相关文档

- 新版插件开发指南：https://docs.astrbot.app/en/dev/star/plugin-new
- 最小实例：https://docs.astrbot.app/dev/star/guides/simple.html
