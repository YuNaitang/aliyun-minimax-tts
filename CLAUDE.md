# AstrBot 多插件开发工作区

## 项目概述

本目录是 AstrBot 多插件开发工作区，管理多个 AstrBot 插件源码和测试实例。

**作者**: YuNaitang（鱼鼐棠）

## 目录结构

```
d:\AI\Astrbot\
├── CLAUDE.md              ← 项目上下文（本文）
├── .gitignore             ← 主仓库 gitignore
├── data/                  ← AstrBot 运行时数据（主仓库跟踪基础配置，排除 data/logs/ data/config/）
│   ├── plugins/           ← AstrBot 实际加载的插件目录（自动同步 plugins/）
│   ├── config/            ← 插件配置（含 Token，被 .gitignore 排除）
│   ├── cmd_config.json    ← AstrBot 配置
│   └── data_v4.db         ← SQLite 数据库
├── plugins/               ← 插件开发工作区
│   ├── README.md
│   ├── helloworld/        ← 示例插件（可复制为新插件起点）
│   ├── templates/basic/   ← 插件基础模板
│   └── astrbot_plugin_memosnotes/  ← MemosNotes 插件（独立 git 仓库）
│       ├── main.py        ← 核心功能
│       ├── client.py      ← Memos REST API 客户端
│       ├── metadata.yaml
│       ├── _conf_schema.json
│       ├── README.md
│       └── LICENSE        ← MIT
```

## 仓库管理策略

本项目采用**双仓库模式**：

| 仓库 | 位置 | 远程 |
|------|------|------|
| **主开发仓库** | `d:\AI\Astrbot\` | 无远程（本地开发） |
| **插件独立仓库** | `plugins/astrbot_plugin_memosnotes/` | `origin → GitHub` |

- 主仓库 `.gitignore` 中已添加 `plugins/astrbot_plugin_memosnotes/`，防止嵌套 git 冲突
- 每个正式发布的插件应在自己目录内独立 `git init`，拥有独立的 GitHub 仓库
- `plugins/` 下的示例和模板归主仓库管理

## 开发命令

```bash
# 运行 AstrBot（在项目根目录）
astrbot run

# 查看已安装插件
astrbot plug list
```

## 工作流程

### 日常开发（每次修改文件）

1. **更新版本号** — 在 `metadata.yaml` 中递增 `version` 字段（语义化版本）
2. **检查并更新文档** — 同步 `README.md` 和注释
3. **同步 data/plugins** — 如果修改了 `plugins/<name>/`，同步到 `data/plugins/<name>/`
4. **提交 Git** — 语义化 commit：`<type>(<scope>): <description>`，如 `feat(memos): 添加创建备忘录命令`
5. **重启 AstrBot 测试** — 验证修改生效

### 发布新插件

1. **开发完成**后，在插件目录内：
   ```bash
   cd plugins/<your-plugin>
   git init
   git add -A && git commit -m "Initial release v1.0.0"
   ```
2. **在 GitHub 创建仓库**（公开）：
   ```bash
   gh repo create <repo-name> --public --source=. --remote=origin --push
   ```
3. **从主仓库解耦**：
   ```bash
   cd /d/AI/Astrbot
   git rm --cached -r plugins/<your-plugin>/
   echo "plugins/<your-plugin>/" >> .gitignore
   git add .gitignore && git commit -m "chore: 将 <your-plugin> 移至独立仓库"
   ```

### 上架到 AstrBot 插件市场

1. 确保 GitHub 仓库已推送且包含：
   - `main.py` / `metadata.yaml` — 必需
   - `README.md` — 安装和使用说明
   - `LICENSE` — 推荐 MIT
2. 访问 [plugins.astrbot.app](https://plugins.astrbot.app/)
3. 点击右下角 **+** 按钮
4. 填写插件信息（名称、作者、仓库地址、描述）
5. 点击 **提交到 GITHUB** → 自动跳转 Issue 页面 → 点击 **Create**
6. 等待 AI 审核通过，用户即可在 WebUI 插件市场一键安装

### 推送更新到仓库

每次修复/更新完插件后：

```bash
cd plugins/<your-plugin>
git add -A && git commit -m "<type>(<scope>): <description>"
git push
```

> 注意：主仓库和插件仓库是独立的，改了插件文件要分别提交两边的 git。

## 版本号规范

遵循语义化版本 `MAJOR.MINOR.PATCH`：
- **MAJOR**: 不兼容的 API 修改（如命令改名）
- **MINOR**: 向下兼容的功能新增（如新增子命令、LLM 工具）
- **PATCH**: 向下兼容的问题修复（如 bug 修复、API 适配调整）

## MemosNotes 插件关键记录

- **插件名**: `astrbot_plugin_memosnotes`
- **作者**: YuNaitang
- **仓库**: https://github.com/YuNaitang/astrbot_plugin_memosnotes
- **最新版本**: v1.5.1
- **技术栈**: AstrBot v4.25+ / httpx / Memos REST API v1

### 功能清单
- 命令式 CRUD: `/memos` / `/mn` create|list|get|update|delete|help
- 置顶/归档: pin / unpin / archive / restore
- 标签系统: Memos 从 #tag 自动提取
- 平台适配: QQ 系列 → 合并转发三段式，其他 → 纯文本
- LLM 工具: `write_diary` / `save_knowledge` / `search_memos`

### 核心 API 对接
- `POST /api/v1/memos` — 创建（tags 从 content 中 #tag 自动提取）
- `GET /api/v1/memos` — 列表（不支持 AIP-160 filter，不使用）
- `GET /api/v1/memos/{id}` — 详情（id 为短字符串，如 `Lnk3P22K8CKoAS4ZFMaj9G`）
- `PATCH /api/v1/memos/{id}` — 更新（updateMask 标识字段，pinned/state/content）
- `DELETE /api/v1/memos/{id}` — 删除
- Memo ID 是字符串不是数字，所有 ID 输入前自动 `.lstrip("#")`

### 版本历史
| 版本 | 内容 |
|------|------|
| 1.5.1 | 按平台选择 get 发送方式（QQ→合并转发，其他→纯文本） |
| 1.5.0 | get 改用 Nodes 合并转发三段式返回 |
| 1.4.0 | 标签系统、置顶/归档、LLM 知识格式优化 |
| 1.3.0 | 显示格式优化（list 空行分隔、get MD 格式、ID # 前缀） |
| 1.2.0 | LLM 知识库工具 save_knowledge + search_memos |
| 1.1.0 | create 支持可见性控制 -p / --public / --protected |
| 1.0.1 | 修复 API 兼容性问题（ID 类型、filter、yield from、config 参数） |
| 1.0.0 | 初始版本 |

## 插件规范

每个插件必须包含：
- `main.py` — 入口文件，导出继承 `Star` 的类
- `metadata.yaml` — 元数据（name, author, desc, version, astrbot_version）
- `README.md` — 使用文档
- `LICENSE` — 推荐 MIT（上架到插件市场必须）

插件类必须继承 `star.Star`，使用 `@filter.command("名称")` 注册指令，通过 `yield event.plain_result()` 回复。

## LLM 工具格式约定

### write_diary（写日记）
```
📖 2026年6月28日 周日 晴
内容正文……
```
- 可选 tag: `diary` / `生活` / `日常`

### save_knowledge（保存知识）
```
【知识】Nginx 反向代理配置
详情内容……
```
- tags: `运维 nginx docker`（自动加 #，Memos 自动提取）

## 相关文档

- 新版插件开发指南：https://docs.astrbot.app/en/dev/star/plugin-new
- 最小实例：https://docs.astrbot.app/dev/star/guides/simple.html
- 插件配置指南：https://docs.astrbot.app/en/dev/star/guides/plugin-config
- 插件市场发布：https://docs.astrbot.app/dev/star/plugin-publish.html
- 插件市场地址：https://plugins.astrbot.app
