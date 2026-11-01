[← README](../README_cn.md) · [English](install-plugin.md)

# 把 Durweg 装成 Claude Code 插件

如果你已经在用 Claude Code，可以在 Claude Code 里用一条命令装好 Durweg：不用下载文件，也不用另开终端。装好后的 `durweg` 命令和 skill 跟安装器装的一样，你的工作流也照样放在 `~/Durweg` 文件夹里。

插件的第一版支持 **macOS、Linux 和 Windows 里的 WSL**。在 Windows 本身（不是 WSL）上，暂时请用 [README](../README_cn.md) 里的安装器。

## 💻 需要什么

| 程序 | 在 Claude Code 里输入这个来检查 | 没有或版本较旧的话 |
| :--- | :--- | :--- |
| Claude Code，已登录 | `/status` | [安装 Claude Code](https://code.claude.com/docs/en/setup) |
| Python 3.9 或更新 | `! python3 --version` | • Mac：`xcode-select --install`；低于 3.9：在“系统设置 → 通用 → 软件更新”里更新<br>• Debian 或 Ubuntu（WSL 也是）：`sudo apt-get install -y python3` |
| git | `! git --version` | • Mac：`xcode-select --install`<br>• Debian 或 Ubuntu（WSL 也是）：`sudo apt-get install -y git` |

输入 `! claude --version` 可以看 Claude Code 的版本：下面用一条命令安装，需要 2.1.275 或更新（`! claude update` 可以升级）。

## 🧭 安装

1. 在你平时工作的地方打开 Claude Code。在 WSL 里要用 Linux 这边的文件夹（比如 `~/projects/…`），不要用 `/mnt/c/` 下面的 Windows 文件夹：运行记录会放在你打开 Claude Code 的那个文件夹里。
2. 输入 `/plugin install durweg --marketplace musetee/durweg`，按回车。
3. 输入 `/reload-plugins`，按回车，让当前会话加载这个插件。

如果 Claude Code 版本较旧，第 2 步改成两条命令：先 `/plugin marketplace add musetee/durweg`，再 `/plugin install durweg@durweg`。

**装好的样子：** 输入 `! durweg --version`，显示版本号，后面跟着 `(Claude Code plugin)`。如果刚 `/reload-plugins` 完就提示 `command not found`，再试一次：会话有时要到下一次才认得新命令。

## 🚀 第一次试用

对 Claude 说：`Run write-your-method with durweg.` 第一次时，Claude 会先问你用中文还是英文交流。然后它帮你把自己做某件事的方法一步一步写成工作流，过程中请你检查和确认。`durweg check` 显示 `PASS` 就完成了。

这个示例已经在你的方法库里：Durweg 第一次运行时会把它放进去。别的工作流和用安装器时一样装：直接问 Claude 要，或者运行 `! durweg library available`，再 `! durweg library add <名字>`。

## 📅 更新和卸载

| 你想 | 这样做 |
| :--- | :--- |
| 更新 Durweg 本身 | • `/plugin update durweg`，再 `/reload-plugins`<br>• 这个 marketplace 的插件不会自动更新 |
| 更新你的工作流和目录 | • `! durweg update`（或者请 Claude 帮你更新）<br>• 其中 Durweg 那一行会写 `skipped … /plugin update durweg`，这是正常的 |
| 卸载 Durweg | • `/plugin uninstall durweg`<br>• 你的 `~/Durweg` 文件夹和运行记录都会保留 |

## 🛠️ 以前用安装器装过

两种可以同时装着，但这时运行的是安装器那一份（它在 PATH 里排在前面），`durweg --version` 后面也不会有 `(Claude Code plugin)`。只想留插件的话：

1. 运行 `! durweg uninstall`。它会去掉安装器装的那一份，以及它给你的 agent 装的 skill（如果也给 Codex 或 Antigravity 装过，它们的也会去掉；你还用它们的话，就留着安装器）。插件自带的 skill、你的 `~/Durweg` 文件夹和运行记录都会保留。
2. 输入 `/reload-plugins`（或者重开 Claude Code），之后用的就是插件的 `durweg`。

反过来只想留安装器的话，运行 `/plugin uninstall durweg`。
