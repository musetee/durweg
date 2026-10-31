[← README](../README_cn.md) · [English](workflow-format.md)

# 写一个工作流

工作流是一个文件夹，里面有 `workflow.json`，还有一个 skill 文件夹，写明每一步怎么做。它不一定要是 git 仓库。如果它在 git 仓库里，`durweg start` 会记下 commit，并且拒绝还没提交的文件（编写阶段可以用 `--dev`，这样的运行会被标记出来，不能用于验收）。无论是否用 git，每次运行都会保留一份锁定的工作流副本。完整的例子：[`examples/mini`](../examples/mini)。结构定义：[`schema/workflow.schema.json`](../schema/workflow.schema.json)。

## workflow.json

| 字段 | 含义 |
|---|---|
| `id`、`title` | 工作流的名字 |
| `platforms` | 可选：`linux`、`macos`、`windows`（WSL 算 linux）；不写就是三个都支持。在不支持的系统上，`durweg start` 会在建立任何东西之前拒绝（退出码 3） |
| `skill` | skill 文件夹；每次运行都会整个复制一份，所以之后再改它，不会影响正在进行的运行 |
| `snapshot` | 另外要复制的文件，例如关卡脚本（`tools/check.py`）和它们要导入的模块 |
| `steps[].id` | 小写的 id，在命令里用（`durweg begin <运行> <id>`） |
| `steps[].instructions` | 这一步在 skill 里那一节的 `路径#锚点`；`durweg begin` 会把它打印出来 |
| `steps[].needs` | 必须先完成的步骤；默认是上一步 |
| `steps[].artifacts` | 这一步写的、或者它的关卡要读的**所有**文件（glob）；`done` 以后再改其中任何一个，`durweg check` 都会失败 |
| `steps[].gates` | 关卡：`durweg done` 时检查，`durweg check` 时再查一次 |

## 关卡

| 类型 | 参数 | 什么时候通过 |
|---|---|---|
| `json` | `file`、`schema`（type、required、properties、items、minItems、maxItems、minLength、enum、uniqueItems） | • 文件是合法的 JSON，并且符合 schema<br>• 没有空字符串或占位符（`TODO`、`TBD`、`…`、`-`、`?`） |
| `sections` | `file`、`headings: [{title, min_items, max_items, min_chars}]` | • 每个标题（`#` 写法，文字完全一致）在代码块之外恰好出现一次<br>• 它下面的列表项数量对，而且不为空 |
| `table` | `file`、`under`、`columns`、`min_rows`、`max_rows`、`unique` | 标题下的第一张表格列名完全一致，行数够，没有空单元格，`unique` 列里没有重复 |
| `files` | `glob`、`min_count` | 匹配到的文件够数，而且都不为空 |
| `command` | `argv`（列表，不经过 shell；`{run}`、`{wf}`、`{step}` 会被替换）、`timeout`（默认 60 秒） | • 从运行快照（`{wf}/…`）里执行的脚本，在运行文件夹中退出码为 0<br>• 脚本能拿到 `WF_RUN`、`WF_SNAPSHOT`、`WF_STATE`、`WF_STEP` 和 `DURWEG_PLATFORM`；输出存在 `.wf/gates/` |
| `user` | — | • 用户确认了这一轮的提案（`durweg propose` → `durweg confirm`）<br>• 提案之后没有改动；决定文件里存的是 `--set` 的值 |

关卡脚本只检查已经保存下来的证据，不能联网。用户回答里的决定，存在 `steps/<n>-<id>.decision.json`，格式是 `{"confirm_event": n, "values": {...}}`。

## 核对

`durweg check <运行>` 重放这次运行的事件记录，并且按 `durweg start` 时锁定的工作流副本，重新检查每一个关卡、每一个文件的指纹，结果是 `PASS` 或 `FAIL`。它只读运行文件夹，所以工作流后来被修改或移动了，也照样能核对。如果有人围着合格的文件手工重写了记录，它查不出来；把运行和 agent 自己的会话记录对照，是可选插件 [durweg-audit](https://github.com/musetee/durweg-audit) 的事。

## 什么时候写关卡脚本

大多数步骤不需要脚本：结果由用户来看（`user` 关卡），`json`、`sections`、`table`、`files` 负责检查结果在不在、全不全。只有同时满足下面三条，才写 `command` 脚本：
1. 看结果看不出错，比如某件事到底有没有真的去查；
2. 错了代价大；
3. 这个工作流会反复运行。

## 方法库

`durweg library add <内容> [--name 名字]` 把一个工作流登记到某个名字下。`<内容>` 按这个顺序判断：

1. git 地址（`https://…`、`git@…`、`ssh://…`、`….git`）：clone 到 `~/Durweg/workflows/`；
2. `<目录>:<名字>`（例如 `public:human-readme`）：从这个目录里装这个工作流（clone）；
3. 看起来像路径的（`./x`、`/x`、`~/x`、`C:\x`，或者任何带斜杠的）：这个文件夹，留在原处；
4. 单个词：当前文件夹里同名的文件夹，或者某个目录里同名的工作流。两者都有时什么也不加，并提示写
   `./<词>` 或 `<目录>:<词>`；好几个目录都有这个名字时，要求写 `<目录>:<词>`。

之后就可以 `durweg start <名字> <这次运行的名字>`；`start` 只查方法库，从不查目录。`durweg library list`
列出名字、支持的系统，以及文件夹还在不在；`durweg library available` 列出各个目录里能装的工作流；
`durweg runs` 列出这台电脑上启动过的运行（索引丢了，可以用 `--rebuild <文件夹>` 重新扫描）。

## 目录

目录是一个 git 仓库，里面只有一个文件 `catalog.json`，列出别人可以按名字安装的工作流：

```json
{"format": 1, "workflows": {
  "human-readme": {"title": "给人看的 README", "summary": "一句话说明它做什么",
                   "url": "https://github.com/<owner>/durweg-human-readme.git"}}}
```

名字只用小写字母、数字和 `-`；没有 `url` 的条目会被跳过。公开目录（`public`）一直都在：
`durweg catalog remove public` 关掉它，`durweg catalog add public` 重新打开。别的目录，比如你自己的私人目录：
`durweg catalog add <名字> <git 地址>`（名字至少 2 个字符）、`durweg catalog list`、
`durweg catalog remove <名字>`（从它装的工作流仍留在方法库里）。Durweg 在 `~/Durweg/catalogs/` 里存每个目录的一份副本；
下载不到时就显示这份副本，并写明是什么时候的。

git 只用电脑上已有的凭据，从不弹出要密码的提问：GitHub 私有仓库需要先运行一次 `gh auth login` 和 `gh auth setup-git`。
