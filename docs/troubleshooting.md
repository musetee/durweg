[← README](../README.md) · [中文](troubleshooting_cn.md)

# Common problems

## Windows 10: the Claude login does not work in the installer window

Windows 10's old console window cannot show modern command-line programs well; Claude Code's login
screen comes out garbled or stuck in it. Durweg needs no change; run the installer in another
window:

1. If you do not have Windows Terminal, install it from the Microsoft Store.
2. Open Windows Terminal.
3. Open a **Command Prompt** tab: click the ˅ next to the tabs and choose "Command Prompt".
4. Drag `Durweg-Install.bat` into the window and press Enter.

In a PowerShell tab, type `& ` (& and a space) first, then drag the file in and press Enter;
without it PowerShell only prints the path.

## Mac: the installer says Durweg needs Python 3.9 or newer

Durweg uses the `python3` that Terminal finds first. If you installed Anaconda or an older Python
from python.org, that one comes before the Mac's own Python. You do not have to reinstall Python:

1. Open Terminal and run `/usr/bin/python3 --version`.
   - **3.9 or newer:** the Mac's own Python is fine; go on with step 2.
   - **3.7 or 3.8:** your developer tools are old. Update "Command Line Tools" in System Settings →
     General → Software Update, then go on with step 2.
2. Run `which python3` to see which Python comes first:

   | The path contains | What to do |
   | :--- | :--- |
   | `anaconda3` or `miniconda3` | Run `conda config --set auto_activate_base false`. Conda stays installed; `conda activate` turns it on when you need it |
   | `/Library/Frameworks/Python.framework` | Open `~/.zprofile` in a text editor and put `#` in front of the lines that add the old Python to `PATH` |

3. Close Terminal and open it again. `python3 --version` now shows 3.9 or newer.
4. Double-click `Durweg-Install.command` again.
