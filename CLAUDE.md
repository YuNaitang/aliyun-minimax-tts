# AstrBot 主开发仓库

## 项目概述

本目录是 AstrBot 测试实例 + 本地开发环境。

**作者**: YuNaitang（鱼鼐棠）

## 目录约定

| 目录 | 说明 |
|------|------|
| `data/` | AstrBot 运行时数据（配置、数据库、插件等） |
| `plugins/` | **插件开发目录** — 被 `.gitignore` 忽略，不归本仓库管理 |

> ⚠️ **重要**：`plugins/` 目录已被 `.gitignore` 忽略，整个目录不归本仓库管理。
> 每个插件都是一个独立的 Git 仓库，拥有各自的 GitHub 远程。

## 插件开发流程

### 创建新插件

```bash
# 1. 在插件目录创建
mkdir -p plugins/<your-plugin>
cd plugins/<your-plugin>

# 2. 初始化独立仓库
git init
echo "# 你的插件" > README.md
# ... 编写 main.py, metadata.yaml 等 ...

# 3. 在 GitHub 创建公开仓库并推送
gh repo create <repo-name> --public --source=. --remote=origin --push
```

### 日常开发

```bash
# 编写代码
code plugins/astrbot_plugin_memosnotes/main.py

# 测试（在项目根目录）
astrbot run

# 提交（在插件目录）
cd plugins/astrbot_plugin_memosnotes
git add -A && git commit -m "fix: 修复xxx"
git push
```

### 修改配置后必须重启 AstrBot

```bash
astrbot run
```

## 当前插件列表

| 插件 | 仓库 | 版本 |
|------|------|------|
| MemosNotes | [astrbot_plugin_memosnotes](https://github.com/YuNaitang/astrbot_plugin_memosnotes) | v1.5.1 |
| Aliyun MiniMax TTS | [aliyun-minimax-tts](https://github.com/YuNaitang/aliyun-minimax-tts) | v1.3.0 |

## 相关文档

- AstrBot 插件开发指南：https://docs.astrbot.app/en/dev/star/plugin-new
- 插件市场发布：https://docs.astrbot.app/dev/star/plugin-publish.html
- 插件市场：https://plugins.astrbot.app
