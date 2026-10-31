[← README](../README_cn.md) · [English](troubleshooting.md)

# 常见问题

## Windows 10：在安装窗口里登录不了 Claude

Windows 10 的旧式命令行窗口显示不好现代的命令行程序，Claude Code 的登录界面在里面会显示错乱或卡住。不用改 Durweg，换一个窗口运行安装程序即可：

1. 没有 Windows Terminal 的话，先从 Microsoft Store 安装它。
2. 打开 Windows Terminal。
3. 打开一个**命令提示符**标签页：点标签旁边的 ˅，选“命令提示符”。
4. 把 `Durweg-Install.bat` 拖进窗口，按回车。

如果你用的是 PowerShell 标签页，要先输入 `& `（& 加一个空格），再把文件拖进去，按回车；不加的话 PowerShell 只会把路径打印出来。
