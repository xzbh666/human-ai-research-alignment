# 安装到 ChatGPT 网页端与 marketplace

## 个人账号：使用已经创建的私有插件

打开 [Human–AI Research Alignment](https://chatgpt.com/plugins/plugins_6af429a6779c8191877efd33572273eb)，登录创建它的同一个 ChatGPT 账号，安装/启用，然后新建对话并选择插件。此链接是个人私有副本，不是面向所有人的公共安装链接。当前账号已保存 0.1.1；仓库提交不会自动更新这个通过上传创建的个人副本。

开始时可以发送：

> 请启动研究对齐流程。先问我是从零开始、中途接入还是恢复研究，再通过少量问题提取目标、共识和先验，把每条提案展示给我确认。请用中文交流。

插件只提供 Skill 和配套 Python CLI，没有 MCP 服务。网页环境能否运行代码、生成文件取决于当前会话的工具和账号/工作区权限。不能运行时只提供明确标注的临时聊天状态，不伪称写入账本。网页端不直接监控本机 Git。跨会话恢复需要下载并保管包含 `.ai-research/ledger.json` 的私有检查点，再在下次上传；披露 Markdown 不能替代检查点。上传研究内容到 ChatGPT 适用你的 ChatGPT 数据设置，并不意味着内容只在本机处理。

## 从源码构建可上传的插件包

```sh
python3 scripts/package_plugin.py --output dist/human-ai-research-alignment.zip
```

ZIP 只包含一个插件根目录，其中有 portable `plugin.json`、兼容 `.codex-plugin/plugin.json`、`skills/human-ai-research-alignment/SKILL.md` 与必要代码。它不包含 marketplace、测试、真实研究记录或额外外层项目目录。通过账号支持的私有插件上传/创建功能导入；并非所有账号都提供此入口。不要把整个仓库 ZIP 当作插件上传包。公开上架另需提交审核，本项目未上架公共目录。

## 工作区管理员：从 GitHub 导入 marketplace

按照 [OpenAI 官方导入说明](https://learn.chatgpt.com/docs/enterprise/plugin-management)：

1. 打开 **Admin → Plugins → Add → Import marketplace**。
2. **Source**：`https://github.com/xzbh666/human-ai-research-alignment`。
3. **Path**：留空；**Branch, tag, or commit**：`main`（或自行选定固定提交）。
4. 导入后检查结果、网页可用性与安装策略，再在新对话中测试。

此路径需要工作区管理员权限与相应 GitHub 读取授权。目录位于 `.agents/plugins/marketplace.json`，`source.path` 相对仓库根目录解析。默认策略为可选安装，不强制全员安装。管理员导入后的权限设置由工作区控制，不由仓库覆盖。

没有在 marketplace 条目写入 `pluginId`：现有插件是 USER 私有范围，不能把个人 ID 冒充为工作区同范围插件。工作区导入通常产生自己的副本；如以后要迁移已有工作区插件，请按官方流程核实其 ID 和名称。

## Codex / 桌面端：Git marketplace

在支持该命令的 Codex 客户端中：

```sh
codex plugin marketplace add xzbh666/human-ai-research-alignment --ref main
```

然后在支持的插件目录中选中 **Human–AI Research Tools**，安装 `human-ai-research-alignment`。本仓库不自动修改你电脑上的个人 marketplace 或全局设置。客户端缓存与会话刷新遵循其安装流程。

## 文件布局与更新

```text
.agents/plugins/marketplace.json
plugins/human-ai-research-alignment/
  plugin.json
  .codex-plugin/plugin.json
  skills/human-ai-research-alignment/
    SKILL.md
    README.md
    pyproject.toml
    harp/
scripts/package_plugin.py
```

仓库根目录继续提供独立 CLI。`plugins/` 内是可直接分发的网页适配版本。修改根目录 CLI 后需同步插件中的代码；打包脚本会拒绝代码不一致。Skill 的网页入口说明单独维护。个人账号上传版与 GitHub 导入版使用不同的更新路径，不能声称提交 GitHub 已更新个人插件。

验证范围：自动检查清单与路径、包内 CLI 与根目录一致、ZIP 内容受限；本地研究流程测试独立执行。管理员真实导入及网页新对话的完整执行需在有权限的目标账号验证，文件校验通过不等于这些步骤已完成。
