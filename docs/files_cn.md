[← README](../README_cn.md) · [English](files.md)

# 文件放在哪里

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
