[English](README.md) · [中文](README_cn.md)

# Durweg

**Durweg 把你做一件事的固定方法写成工作流，让 AI agent（Claude Code、Codex）每次都照着它一步一步做，不跳步、不替你拍板，产出稳定。**

只给 agent 一份说明（skill），它可能跳过一步、替你做了决定，事后也查不出来。Durweg 让每一步过了检查才能往下走，在你的方法要你拍板的地方停下来问你，并留下一份你可以核对的记录。

## 🧭 安装

不需要 GitHub 账号。需要 Claude Code 或 Codex 的账号（用量算在你自己的套餐里）；电脑上还没有 agent 的，安装程序会帮你装。已经装了 Antigravity 的，它也会一起用上 Durweg。

**运行安装程序**（按你的电脑选一行）：

| 你的电脑 | 怎么做 |
| :--- | :--- |
| **Windows**<br>（不管有没有 WSL） | • 下载 [`Durweg-Install.bat`](https://github.com/musetee/durweg/releases/latest/download/Durweg-Install.bat)，在 Windows 里双击<br>• 想装进 WSL 也用它：在安装程序里选 WSL，不用自己打开 WSL 输命令 |
| **Mac** | 下载 [`Durweg-Install-macOS.zip`](https://github.com/musetee/durweg/releases/latest/download/Durweg-Install-macOS.zip)，解压后双击 `Durweg-Install.command` |
| **Linux**<br>（不是 Windows 里的 WSL） | 在终端里运行：<br>`curl -fsSL https://raw.githubusercontent.com/musetee/durweg/v1.0.0/install.sh \| bash` |

安装程序先问语言，Windows 上再问装在哪里（Windows 还是 WSL），然后自动装好，在浏览器里打开这个页面，启动你的 agent，带你做[案例](#-案例写下你的方法)。途中遇到的每个提问怎么答：见本页最后的[安装时会遇到的提问](#-安装时会遇到的提问)。

## 📅 每天怎么用

1. **打开终端。** Windows：打开 Windows Terminal（Durweg 装在 WSL 里的话，从开始菜单打开 "Ubuntu"）。Mac 或 Linux：打开“终端”。
2. **进入你的项目文件夹：** `cd ~/projects/my-project`（Windows 本机上如 `cd C:\Users\<你>\projects\my-project`）。每次运行的记录都放在这个文件夹的 `runs/` 里。
3. **启动 agent：** 输入 `claude`（Claude Code）或 `codex`（Codex），按回车。
4. **告诉它要做什么：**
   - 运行一个工作流：“用 durweg 运行 weekly-report”。它一步一步执行，某一步的检查没过就停下，在你的方法要你拍板的地方问你。
   - 新建一个工作流：“用 durweg 运行 write-your-method”（就是[案例](#-案例写下你的方法)里的那个引导）。
   - 看看有哪些工作流：“列出我的 durweg 工作流”。

## 📁 文件放在哪里

| 什么 | 在哪里 | 里面有什么 |
| :--- | :--- | :--- |
| **你的设置和工作流** | `~/Durweg/` | • `config.json`：设置，其中有语言<br>• `workflows/`：你的工作流<br>• `library.json`：工作流的清单 |
| **你的案例** | `~/Durweg/cases/` | 每个案例一个网页文件（`<工作流>_<运行>.html`），双击打开；可以移走或发给别人 |
| **每次运行的记录** | 你启动它时所在项目文件夹的 `runs/` 下，一次运行一个文件夹 | • `steps/`：每一步交出的东西<br>• `run.md`：方便阅读的汇总（`durweg render <运行>`）<br>• `.wf/`：运行记录和锁定的工作流副本（不要改它） |

**在 Windows 里找到它们：**

| Durweg 装在 | 怎么找 |
| :--- | :--- |
| **Windows 本机** | `~/Durweg` 就是 `C:\Users\<你>\Durweg` |
| **WSL** | • 资源管理器左侧栏：**Linux → Ubuntu → home → <你的 Linux 用户名>**<br>• 或者在 WSL 终端里运行 `explorer.exe .`，用资源管理器打开当前文件夹 |

Mac 和 Linux 上，它们就在你的家目录里。

## 🚀 案例：写下你的方法

这个案例展示 Durweg 怎么把你的一个固定做法变成工作流：以每周进度汇报为例，做出一个你自己的工作流 `weekly-report`，用它跑一次，最后写成一个可以收藏或分享给别人的案例网页。安装程序第一次会自动带你做；以后想再做一个，按下面的步骤。

1. **打开终端**（“每天怎么用”第 1 步）。
2. **新建一个练习文件夹并进入：** `mkdir -p ~/projects/first-method && cd ~/projects/first-method`。这次运行的记录会放在这里。
3. **启动 agent**（“每天怎么用”第 3 步）。
4. **对它说：**“用 durweg 运行 write-your-method”。然后按它的提问说你是怎么做每周汇报的（收集、撰写、确认发送），确认它拆出来的步骤。
5. **写成案例（可选）：** 最后它问你要不要写成案例。要的话，说说你想告诉别人的经验；它把你的方法、步骤、你每次确认时的原话和试跑结果做成一个网页，放在 `~/Durweg/cases/`，双击就能在浏览器里打开，也可以直接发给别人。

agent 告诉你检查结果是 `PASS`，并且“列出我的 durweg 工作流”里有 `weekly-report`，就成功了。以后只要说“用 durweg 运行 weekly-report”。

**一个真实的案例：** 用这个引导写出工作流 `human-readme`（照 AIagents 项目的 README 写法），再用它重写了 Durweg 自己的 README。方法、步骤、每一步用户的原话和经验都在这个案例网页里：[写给人看的 README · Durweg 案例](https://claude.ai/artifact/LGnCog4wnBmgMAWJg1Xmi4)。想自己用这个工作流：[durweg-human-readme](https://github.com/musetee/durweg-human-readme)。

## 🙋 我想……

| 我想 | 怎么做 |
| :--- | :--- |
| 手写一个工作流 | [工作流格式](docs/workflow-format_cn.md) |
| 核对一次运行 | `durweg check <运行文件夹>` |
| 改语言 | `durweg config language zh`（或 `en`） |
| 装到别的地方（在 Windows 上改装进 WSL） | 再运行一次安装程序，它问要不要修改时输入 `c` |
| 把一次运行和 agent 自己的会话记录对照 | 可选插件 [durweg-audit](https://github.com/musetee/durweg-audit) |
| 卸载 | `durweg uninstall`：保留 `~/Durweg` 和你的运行记录（[卸载](docs/uninstall_cn.md)） |

## 🛠️ 常见问题

- **Windows 10：在安装窗口里登录不了 Claude。** 改在 Windows Terminal 里运行安装程序：打开一个命令提示符标签页，把 `Durweg-Install.bat` 拖进去，按回车（[详细步骤](docs/troubleshooting_cn.md#windows-10在安装窗口里登录不了-claude)）。
- **装好 Durweg 以后才装了另一个 agent（比如先有 Codex，后装 Claude Code）：** 新装的 agent 还不会用 Durweg。再运行一次安装程序，问要不要修改时按回车，它会给电脑上所有的 agent 都装上 Durweg。
- **agent 已经装了，安装程序却说没有找到：** 你的 agent 不在系统能直接找到的位置（比如要用一个脚本启动）。在“要装哪一个”时选 **3**：Durweg 会装好给 Claude Code 和 Codex 用的部分，你照平常的方式启动 agent，对它说“用 durweg 运行 write-your-method”。

## 💬 安装时会遇到的提问

| 提问 | 怎么选 |
| :--- | :--- |
| **语言** | 选你要 agent 用的语言；以后可以用 `durweg config language` 改 |
| **装在哪里**（Windows） | • 一般选 **Windows**<br>• 也想用需要 Linux 的工作流，选 **WSL**（Windows 里的 Linux） |
| **还没有 WSL** | • 同意管理员授权，重启电脑<br>• 从开始菜单打开一次 "Ubuntu"，设好 Linux 用户名和密码<br>• 再双击一次安装程序；之前的选择它都记着 |
| **“Windows 已保护你的电脑”** | 点 **更多信息 → 仍要运行** |
| **macOS 拦下了安装程序** | • 打开“系统设置 → 隐私与安全性”，点允许<br>• macOS 先装开发者工具的话，等它装完再双击一次 |
| **装 Claude Code 还是 Codex** | • 只在电脑上找不到 agent 时才问；直接回车装 Claude Code，装好以后在浏览器里登录一次<br>• 已经装了 agent、平时用自己的方式（比如一个脚本）启动它：选 **3**，不装新的 |
| **再次运行时问要不要修改** | • 回车：沿用上次的选择（更新或修复）<br>• 输入 `c`：重新选择，重新安装 |

---

MIT 许可证：[LICENSE](LICENSE)。
