[← README](../README.md) · [中文](install-plugin_cn.md)

# Installing Durweg as a Claude Code plugin

If you already use Claude Code, you can install Durweg from inside it with one command: nothing to
download, no second terminal. You get the same `durweg` command and the same skills as with the
installer, and the same `~/Durweg` folder with your workflows.

The plugin works on **Windows, macOS, Linux and WSL on Windows**. Using Codex instead: see
[Installing Durweg as a Codex plugin](install-codex-plugin.md).

## 💻 What you need

| Program | Check it in Claude Code by typing | If it is missing or older |
| :--- | :--- | :--- |
| Claude Code, signed in | `/status` | [Install Claude Code](https://code.claude.com/docs/en/setup) |
| Python 3.9 or newer | `! python3 --version`<br>(Windows: `! py -3 --version`) | • Windows: `winget install -e --id Python.Python.3.12`<br>• Mac: `xcode-select --install`; older than 3.9: update it in System Settings → General → Software Update<br>• Debian or Ubuntu (also WSL): `sudo apt-get install -y python3` |
| git | `! git --version` | • Windows: comes with Git for Windows, which Claude Code needs there anyway<br>• Mac: `xcode-select --install`<br>• Debian or Ubuntu (also WSL): `sudo apt-get install -y git` |

`! claude --version` shows the version of Claude Code: the one-command install below needs 2.1.275
or newer (`! claude update` brings it there).

## 🧭 Install

1. Open Claude Code where you usually work. In WSL, that is a Linux folder such as
   `~/projects/…`, not a Windows folder under `/mnt/c/`: your runs are kept in the folder you start in.
2. Type `/plugin install durweg --marketplace musetee/durweg` and press Enter.
3. Type `/reload-plugins` and press Enter, so that this session sees the plugin.

With an older Claude Code, step 2 is two commands instead: `/plugin marketplace add musetee/durweg`,
then `/plugin install durweg@durweg`.

**It worked when** `! durweg --version` shows a version followed by `(Claude Code plugin)`. If it
says `needs Python 3.9 or newer`, install Python (table above) and try again. If it
says `command not found` right after `/reload-plugins`, try once more: the session sometimes picks
up the new command only on the next try.

## 🚀 First try

Tell Claude: `Run write-your-method with durweg.` The first time, Claude asks whether you want to be
talked to in Chinese or English. Then it helps you write down one way you do your work as a
workflow, step by step, and asks you to check and confirm along the way. It ends when
`durweg check` shows `PASS`.

The example is already in your library; Durweg puts it there the first time it runs. Other
workflows are installed the same way as with the installer: ask Claude for one, or run
`! durweg library available`, then `! durweg library add <name>`.

## 📅 Updating and removing

| You want to | Do this |
| :--- | :--- |
| Update Durweg itself | • `/plugin update durweg`, then `/reload-plugins`<br>• Plugins from this marketplace are not updated automatically |
| Update your workflows and catalogs | • `! durweg update` (or ask Claude to update them)<br>• Its Durweg line says `skipped … /plugin update durweg`: that is expected |
| Remove Durweg | • `/plugin uninstall durweg`<br>• Your `~/Durweg` folder and your runs stay |

## 🛠️ If you installed with the installer before

Both can be installed at the same time, but then the installer's copy is the one that runs (it
comes first on the PATH), and `durweg --version` does not say `(Claude Code plugin)`. To keep only
the plugin:

1. Run `! durweg uninstall`. It removes the installer's copy and the skills it gave your agents
   (for Codex or Antigravity too, if it gave them skills: keep the installer if you also use them); the
   plugin's own skills, your `~/Durweg` folder and your runs stay.
2. Type `/reload-plugins` (or start Claude Code again), so that the plugin's `durweg` is used.

To keep only the installer instead, run `/plugin uninstall durweg`.
