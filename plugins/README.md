# AstrBot 多插件开发工作区

本目录是 **AstrBot 插件开发工作区**，管理多个 AstrBot 插件的源码。

## 目录结构

```
plugins/
├── helloworld/         # 示例插件（可复制用作新插件模板）
│   ├── main.py
│   ├── metadata.yaml
│   └── README.md
├── <your-plugin>/      # 你的其他插件
│   ├── main.py
│   ├── metadata.yaml
│   ├── requirements.txt (可选)
│   ├── _conf_schema.json (可选)
│   └── logo.png (可选)
├── templates/          # 插件模板
│   └── basic/
└── utils/              # 共享工具（调试时使用）
    └── plugin_helper.py
```

## 快速开始：创建新插件

### 方式一：使用 CLI 命令（推荐）

```bash
astrbot plug new <插件名称>
```

输入后按提示填写元数据，会在 AstrBot 默认插件目录下生成脚手架。

### 方式二：手动创建（开发阶段）

复制示例插件并重命名：

```bash
cp -r plugins/helloworld plugins/你的插件名
```

修改 `metadata.yaml` 和 `main.py` 中的类名即可。

## 插件基础结构

每个插件必须包含：

| 文件 | 必需 | 说明 |
|------|------|------|
| `main.py` | ✅ | 入口文件，导出继承 `Star` 的插件类 |
| `metadata.yaml` | ✅ 推荐 | 插件元数据（名称、版本、作者、描述等） |

## 开发注意事项

1. **依赖管理**：使用 `requirements.txt` 声明依赖，优先使用异步库（`aiohttp`、`httpx` 等替代 `requests`）
2. **持久化数据**：存放在 AstrBot 的 `data/` 目录下，不要写在插件自身目录里
3. **代码风格**：提交前建议使用 `ruff` 格式化
4. **配置界面**：使用 `_conf_schema.json` 定义 WebUI 配置，支持 `string`、`int`、`bool`、`list`、`file` 等类型

## 推荐工作流

1. 开发阶段：在 `plugins/` 下手动开发
2. 调试：在插件目录下直接修改，配合 `astrbot run` 或 WebUI 热重载
3. 发布：准备好后通过 Symlink 或在 AstrBot 配置中指向插件目录

---

更多信息请查阅 AstrBot 官方文档：
- https://docs.astrbot.app/dev/star/plugin-new
- https://docs.astrbot.app/dev/star/guides/simple.html
