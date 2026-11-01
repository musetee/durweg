[← README](../README_cn.md) · [English](install-codex-plugin.md)

# 把 Durweg 装成 Codex 插件

如果你已经在用 Codex CLI，可以把 Durweg 装成 Codex 插件：在终端里运行两条命令，不用手动下载。装好后的 skill 和用安装器装的一样，你的工作流也照样放在 `~/Durweg` 文件夹里。

第一版支持 **macOS、Linux 和 Windows 里的 WSL**，在 Linux 和 WSL 上用 Codex CLI 0.166.0 测过（没有测 Codex 桌面版和 IDE 插件）。在 Windows 本身上，请用 [README](../README_cn.md#方式-c用安装程序) 里的安装程序。

## 💻 需要什么

| 程序 | 在终端里检查 | 没有或版本较旧的话 |
| :--- | :--- | :--- |
| Codex CLI，已登录 | `codex --version` | [安装 Codex CLI](https://developers.openai.com/codex/cli) |
| Python 3.9 或更新 | `python3 --version` | • Mac：`xcode-select --install`；低于 3.9：在“系统设置 → 通用 → 软件更新”里更新<br>• Debian 或 Ubuntu（WSL 也是）：`sudo apt-get install -y python3` |
| git | `git --version` | • Mac：`xcode-select --install`<br>• Debian 或 Ubuntu（WSL 也是）：`sudo apt-get install -y git` |

## 🧭 安装

1. 打开一个终端（不是在 Codex 里）。
2. 运行 `codex plugin marketplace add musetee/durweg`。
3. 运行 `codex plugin add durweg@durweg`。
4. 在你平时工作的地方新开一个 Codex 会话。在 WSL 里要用 Linux 这边的文件夹（比如 `~/projects/…`）：运行记录会放在你打开 Codex 的那个文件夹里。

**装好的样子：** 在 Codex 里输入 `/skills`，能看到 `run-workflow` 和 `write-your-method`。然后对 Codex 说：`Run write-your-method with durweg.` 第一次时，它会先问你用中文还是英文交流。

## 🔒 Codex 的沙盒和 `~/Durweg`

Codex 在沙盒里运行命令：只有你的项目文件夹能写，网络是关的。Durweg 把你的设置和方法库放在 `~/Durweg`，所以：

- 往那里写的命令（设置语言、第一次运行、添加工作流）会请你批准，批准就行。
- `durweg library available` 和 `durweg library add` 要联网，也请批准。
- 如果有命令写不进 `~/Durweg`，Durweg 会用一句话说明，而不是打出一大段错误。

## 🔎 为什么 Codex 里没有 `durweg` 命令

Codex 不会把插件里的程序加到 PATH 上。skill 会自己在插件里找到 Durweg，用完整路径来运行，所以你会看到像 `"…/.codex/plugins/cache/durweg/durweg/1.4.0/bin/durweg" status …` 这样的命令。你什么都不用做。

## 📅 更新和卸载

| 你想 | 这样做 |
| :--- | :--- |
| 更新 Durweg 本身 | • 在终端里运行 `codex plugin marketplace upgrade durweg`<br>• 然后新开一个 Codex 会话（旧版本的文件夹会被删掉） |
| 更新你的工作流和目录 | • 请 Codex 运行 `durweg update`<br>• 其中 Durweg 那一行会提示上面那条命令，这是正常的 |
| 卸载 Durweg | • `codex plugin remove durweg@durweg`，再 `codex plugin marketplace remove durweg`<br>• 你的 `~/Durweg` 文件夹和运行记录都会保留 |

## 🛠️ 同时用安装程序或 Claude Code 插件装过

- **安装程序和 Codex 插件：** 安装程序装的 `durweg` 在 PATH 上，所以 Codex 用的是那一份。两份版本不同时，重新运行一次安装程序（或者 `durweg update`，1.1.0 以后才有），或者卸掉其中一份（`durweg uninstall` 卸掉的是安装程序那份）。
- **Claude Code 插件和 Codex 插件：** 两个 agent 各用各的，共用 `~/Durweg`。方法库里的示例 write-your-method 指向其中一份，只有那一份被卸掉时，才会改指向另一份。
