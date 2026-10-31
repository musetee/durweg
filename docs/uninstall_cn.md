[← README](../README_cn.md) · [English](uninstall.md)

# 卸载 Durweg

`durweg uninstall` 会删掉安装程序装到电脑上的东西，保留你自己的工作成果。

1. 在装了 Durweg 的地方打开终端：
   - **Windows：** Windows Terminal 或命令提示符。
   - **WSL：** 打开你的 Linux（比如开始菜单里的 "Ubuntu"）。装在 WSL 里的 Durweg 要在 WSL 里卸载；装在 Windows 本机上的，要在 Windows 的终端里卸载。
   - **macOS / Linux：** 终端。
2. 运行：
   ```
   durweg uninstall
   ```
   想先看看会删掉哪些东西，可以运行：`durweg uninstall --dry-run`。
3. 完成的样子：它逐项列出删掉的东西，最后一行说明 `~/Durweg` 和你的运行记录都保留了。在 Windows 上，`durweg` 命令本身会在这条命令结束后稍等片刻才消失。

## 删掉什么，保留什么

| 删掉 | 保留 |
|---|---|
| • `durweg` 命令<br>• Durweg 的程序文件夹（`~/.local/share/durweg`，Windows 上是 `%LOCALAPPDATA%\Durweg`）<br>• 它给 agent 装的 skill（`run-workflow`、`write-your-method`）<br>• 它加进 PATH 的那一行或那一项 | • `~/Durweg`（Windows 上是 `C:\Users\<你>\Durweg`）：你的设置、你的工作流、方法库<br>• 各个项目里的 `runs` 文件夹<br>• 不属于 Durweg 的同名 skill 和命令 |

下面这些也不会删，因为它们是独立的程序，不用 Durweg 也可能在用：Claude Code、Codex，以及（在 Windows 上）安装程序可能帮你装的 Python。不再需要的话，像卸载其他程序一样卸载它们。

## 彻底删除

运行 `durweg uninstall` 以后，再删掉 `~/Durweg` 文件夹（Windows 上是 `C:\Users\<你>\Durweg`），以及各个项目里的 `runs` 文件夹。里面是你的工作流和运行记录，删了就找不回来了。

## 找不到 `durweg` 命令

打开一个新终端再试。如果还是找不到，说明 Durweg 已经卸载了，或者它装在另一边（Windows 或 WSL）。也可以再运行一次安装程序，然后再运行 `durweg uninstall`。
