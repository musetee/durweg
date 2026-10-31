[← README](../README_cn.md) · [English](publish.md)

# 发布你自己的工作流

`durweg publish` 把你自己的一个工作流放进一个 GitHub 仓库（公开或私有），这样你别的电脑能装，或者别人能装。它需要 GitHub 账号和 GitHub 命令 `gh`（用 `gh auth login` 和 `gh auth setup-git` 登录一次）；只是使用 Durweg 不需要。

1. 启动 agent（和每天一样），对它说：“用 durweg 发布 <名字>。”
2. 它给你看要发布什么，并问还没定的事：
   - **公开还是私有**；
   - **许可证**，文件夹里没有的话（MIT、Apache-2.0、CC-BY-4.0，或者不加）；
   - **目录**：公开的工作流，问要不要申请加进公开目录；私有的，问要不要放进你的私人目录（第一次：要不要建一个）；
   - **案例网页**，只有你点名 `~/Durweg/cases/` 里的某一个时才加。
3. 看一下文件清单，说可以。它这时才建仓库、推送。

做完是这样：它打出 `created <你>/durweg-<名字>` 和 `pushed …`；工作流已经在 GitHub 上，`durweg library list` 里它仍然在你自己的文件夹。

## 仓库里放什么

| 会放进去 | 从不放进去 |
| :--- | :--- |
| • `workflow.json`、skill 文件夹，以及 `snapshot` 里列的文件<br>• 你的 `README.md`（没有就由 Durweg 按步骤写一份）<br>• 你的 `LICENSE`（或者你选的那个）<br>• 你点名的案例网页 | • 文件夹里的其他东西<br>• 运行记录、`.wf/`、你的设置<br>• 你没点名的案例网页 |

Durweg 把这些复制到 `~/Durweg/publish/<名字>/`，从那里推送；你的文件夹不变，你照常在那里改工作流。

## 以后

- **新版本：** 在你的文件夹里改好工作流，再说一次“用 durweg 发布 <名字>”。它推到同一个仓库；别的电脑用 `durweg update` 拿到。
- **另一台电脑：** `durweg library add <仓库地址>`；在目录里的话按名字装：你的私人目录要先 `durweg catalog add private <它的地址>`（一次，需要 `gh` 已登录）。

## Durweg 从不做的

- 推送到不是这台电脑上的 Durweg 建的仓库，或者改一个仓库是公开还是私有；
- 把私有工作流放进公开目录，或者放进 GitHub 上看不出是私有、你也不能写的目录（每次写之前都会再查一次）；
- 发布你从别人的仓库装来的工作流。
