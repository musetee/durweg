[English](README.md) · [中文](README_cn.md)

# Durweg

Durweg 让 AI agent（Claude Code、Codex）按你自己的方法干活，每次都一样，产出稳定。skill 只告诉 agent 怎么做，却不检查它做了没有：它可能跳过一步、替你做了决定，或者不留下任何记录。Durweg 带着 agent 一步一步执行你的方法，每一步过了检查才能往下走，按你的方法在该问你的地方问你，并留下一份你可以核对的记录。

## 安装

不需要 GitHub 账号。安装程序先问你用哪种语言，然后自动装好，并启动你的 agent，带你做第一个示例。如果电脑上还没有 agent，它会问你装 Claude Code 还是 Codex；装好以后，你在浏览器里登录一次。

- **Windows：** 下载 [`Durweg-Install.bat`](https://github.com/musetee/durweg/releases/latest/download/Durweg-Install.bat)，双击。
  1. 选择语言。
  2. 选择 Durweg 装在哪里：**Windows**，还是 **WSL**（Windows 里的 Linux；如果你也想用需要 Linux 的工作流，就选它）。
  3. 如果还没有 WSL，它会先装 WSL：同意管理员授权，重启电脑，从开始菜单打开一次 "Ubuntu"，设置 Linux 用户名和密码，然后再双击一次这个文件。你之前的选择它都记着。
  4. 出现“Windows 已保护你的电脑”：点 **更多信息 → 仍要运行**。
- **macOS：** 下载 [`Durweg-Install-macOS.zip`](https://github.com/musetee/durweg/releases/latest/download/Durweg-Install-macOS.zip)，解压，双击 `Durweg-Install.command`。第一次 macOS 可能会拦下它：打开“系统设置 → 隐私与安全性”，点允许。如果 macOS 先安装开发者工具，等它装完以后再双击一次。
- **Linux：** 打开终端，粘贴：
  `curl -fsSL https://raw.githubusercontent.com/musetee/durweg/v1.0.0/install.sh | bash`

装好的样子：你的 agent 自动启动，带你做**写下你的方法**。你描述一件每次都用同样方式做的工作，确认拆出来的步骤，就得到一个属于你自己的工作流，然后马上用它跑一次。

## 每天怎么用

1. 在你要做事的项目文件夹里打开终端：Windows 上用 Windows Terminal（Durweg 装在 WSL 里的话，从开始菜单打开 "Ubuntu"）；macOS 和 Linux 上用“终端”。每次运行的记录都放在这个文件夹的 `runs/` 里。
2. 启动你的 agent：输入 `claude`（Claude Code）或 `codex`（Codex），按回车。
3. 告诉它你要做什么：
   - **新建一个工作流：**“用 durweg 运行 write-your-method”。这就是安装时带你做的那个引导：你描述一件每次都用同样方式做的工作，确认步骤，方法库里就多了一个新工作流。
   - **运行一个工作流：**“用 durweg 运行 weekly-report”。它一步一步执行，某一步的检查没过就停下，在你的方法要你拍板的地方问你。
   - **看看有哪些工作流：**“列出我的 durweg 工作流”（它会运行 `durweg library list`）。

## 你的文件在哪里

- `~/Durweg/`（Windows 上是 `C:\Users\<你>\Durweg`）：你的设置（`config.json`，其中有语言）、你的工作流（`workflows/`），以及它们的清单（`library.json`）。
- 每次运行是一个文件夹，放在你启动它时所在项目文件夹的 `runs/` 下：`steps/` 是每一步交出的东西，`run.md` 是一份方便阅读的汇总（`durweg render <运行>`），`.wf/` 是运行记录和锁定的工作流副本（不要改它）。

## 例子：写下你的方法

这是安装程序启动的第一件事，用来展示 Durweg 是做什么的。你告诉 agent 你是怎么做某件事的（比如每周的进度汇报：收集、撰写、确认发送）；它把你的步骤写下来给你看，再按你确认过的步骤，原样生成一个工作流 `weekly-report`，放进你的方法库，并陪你跑一次。以后只要说：“用 durweg 运行 weekly-report”。

## 你还可以

- 手写一个工作流：[docs/workflow-format_cn.md](docs/workflow-format_cn.md)。
- 核对一次运行：`durweg check <运行文件夹>`。
- 改语言：`durweg config language zh`（或 `en`）。想装到别的地方（在 Windows 上也可以再装进 WSL），就再运行一次安装程序，它问要不要修改时输入 `c`。
- 卸载 Durweg（保留 `~/Durweg` 和你的运行记录）：`durweg uninstall`，详见 [docs/uninstall_cn.md](docs/uninstall_cn.md)。
- 把一次运行和 agent 自己的会话记录对照：可选插件 [durweg-audit](https://github.com/musetee/durweg-audit)。

## 常见问题

- **Windows 10：在安装窗口里登录不了 Claude。** Windows 10 的旧式命令行窗口显示不好现代的命令行程序。没有 Windows Terminal 就先从 Microsoft Store 安装，打开它，在里面运行安装程序：打开一个**命令提示符**标签页（标签旁边的 ˅），把 `Durweg-Install.bat` 拖进去，按回车。如果是 PowerShell 标签页，要先输入 `& `（& 加一个空格），再把文件拖进去，按回车。

许可证：[MIT](LICENSE)。
