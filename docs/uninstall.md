[← README](../README.md) · [中文](uninstall_cn.md)

# Remove Durweg

`durweg uninstall` removes what the installer put on your computer and keeps your own work.

1. Open a terminal where Durweg is installed:
   - **Windows:** Windows Terminal or Command Prompt.
   - **WSL:** open your Linux (for example "Ubuntu" from the Start menu). Durweg installed in WSL is
     removed there; one installed on Windows itself is removed in a Windows terminal.
   - **macOS / Linux:** Terminal.
2. Run:
   ```
   durweg uninstall
   ```
   To see first what it would remove: `durweg uninstall --dry-run`.
3. Done looks like this: it lists each item it removed, and ends with the line that `~/Durweg` and
   your runs were kept. On Windows the `durweg` command itself disappears a moment after the command
   ends.

## What it removes, what it keeps

| Removed | Kept |
|---|---|
| • the `durweg` command<br>• the Durweg program folder (`~/.local/share/durweg`, on Windows `%LOCALAPPDATA%\Durweg`)<br>• the skills it gave your agents (`run-workflow`, `write-your-method`)<br>• the PATH line or entry it added | • `~/Durweg` (on Windows `C:\Users\<you>\Durweg`): your settings, your workflows, the library<br>• every `runs` folder in your projects<br>• skills and commands of the same name that were not Durweg's |

Not removed either, because they are separate programs you may use without Durweg: Claude Code,
Codex, and (on Windows) the Python the installer may have installed. Remove them like other programs
if you no longer need them.

## Remove everything

After `durweg uninstall`, delete the folder `~/Durweg` (on Windows `C:\Users\<you>\Durweg`) and the
`runs` folders in your projects. They hold your workflows and records: once deleted they are gone.

## If `durweg` is not found

Open a new terminal and try again. If it is still not found, Durweg is already removed, or it was
installed in the other place (Windows or WSL). Running the installer again and then
`durweg uninstall` also works.
