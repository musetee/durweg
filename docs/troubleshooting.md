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
