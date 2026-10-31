# 更新 Durweg 和你的工作流

`durweg update` 先把 Durweg 本身升到最新的发布版本，再把你从 git 装的工作流（从目录里按名字装的，或者按 git 地址装的）更新到最新版本。已经开始的运行不受影响：每次运行都存着自己的一份工作流。

1. 打开终端（Windows 上打开 PowerShell；Durweg 装在 WSL 里的话，再输入 `wsl`）。
2. 运行 `durweg update`。
3. 看它打出的结果：Durweg 一行，每个目录一行，每个工作流一行：

| 词 | 意思 |
| :--- | :--- |
| `updated` | 已经是最新版本（`旧 -> 新`） |
| `unchanged` | 本来就是最新的 |
| `skipped` | 没有动，原因写在这一行；见下面 |
| `failed` | 出错了；原来的版本保留 |

最后一行是各有几个。Durweg 沿用你安装时选的语言和安装位置，什么都不问；它不装 agent，也不启动 agent。

## Durweg 从不改动的

- **你自己文件夹里的工作流**（你自己写的，或者用 `./文件夹` 加进来的）：它们本来就是你现在的样子，Durweg 不碰（`skipped: your own folder`）。
- **你改过的副本**：有没提交的改动、换了分支、有你自己的提交、或者和远端走了不同的路（`diverged`），一律跳过，不覆盖、不重置。
- **更新过程中被改动的工作流**：跳过；再运行一次 `durweg update`。

## `skipped` 的常见原因

| 这一行写的原因 | 怎么办 |
| :--- | :--- |
| `no access: for a private GitHub repository …` | 运行一次 `gh auth login` 和 `gh auth setup-git`，再 `durweg update` |
| `cannot connect (offline?)` | 连上网再试 |
| `the remote's default branch is now …` | `durweg library remove <名字>`，再加一次 |
| `cannot ask GitHub for the newest version` | 这次没检查 Durweg 本身（连不上网）；你的工作流照样更新了 |

只更新工作流：`durweg library update`（或 `durweg library update <名字>`）。再运行一次安装程序也会更新它们。

**从 v1.0 升级：** v1.0 里没有 `durweg update`。先按 README 运行一次 v1.1 或更新版本的安装程序；之后用 `durweg update` 就够了。
