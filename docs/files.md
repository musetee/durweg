[← README](../README.md) · [中文](files_cn.md)

# Where your files are

| What | Where | What is in it |
| :--- | :--- | :--- |
| **Your settings and workflows** | `~/Durweg/` | • `config.json`: the settings, with the language<br>• `workflows/`: your workflows<br>• `library.json`: the list of them |
| **Your cases** | `~/Durweg/cases/` | One web page per case (`<workflow>_<run>.html`); double-click to open; move or send it as you like |
| **The record of each run** | under `runs/` in the project folder you started it from, one folder per run | • `steps/`: what each step delivered<br>• `run.md`: a readable summary (`durweg render <run>`)<br>• `.wf/`: the record and the locked copy of the workflow (do not edit it) |

**Finding them in Windows:**

| Durweg is installed | How to find them |
| :--- | :--- |
| **on Windows itself** | `~/Durweg` is `C:\Users\<you>\Durweg` |
| **in WSL** | • In File Explorer's left pane: **Linux → Ubuntu → home → <your Linux user name>**<br>• Or run `explorer.exe .` in the WSL terminal to open the current folder |

On a Mac and on Linux they are in your home folder.
