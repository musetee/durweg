[← README](../README.md) · [中文](install-codex-plugin_cn.md)

# Installing Durweg as a Codex plugin

If you already use the Codex CLI, you can install Durweg as a Codex plugin: two commands in a
terminal, nothing to download by hand. You get the same skills as with the installer, and the same
`~/Durweg` folder with your workflows.

This first version works on **macOS, Linux and WSL on Windows**, and was tested with the Codex CLI
0.166.0 on Linux and WSL (not with the Codex desktop app or the IDE extensions). On Windows itself,
use the installer from the [README](../README.md#option-c-with-the-installer).

## 💻 What you need

| Program | Check it in a terminal | If it is missing or older |
| :--- | :--- | :--- |
| Codex CLI, signed in | `codex --version` | [Install the Codex CLI](https://developers.openai.com/codex/cli) |
| Python 3.9 or newer | `python3 --version` | • Mac: `xcode-select --install`; older than 3.9: update it in System Settings → General → Software Update<br>• Debian or Ubuntu (also WSL): `sudo apt-get install -y python3` |
| git | `git --version` | • Mac: `xcode-select --install`<br>• Debian or Ubuntu (also WSL): `sudo apt-get install -y git` |

## 🧭 Install

1. Open a terminal (not Codex itself).
2. Run `codex plugin marketplace add musetee/durweg`.
3. Run `codex plugin add durweg@durweg`.
4. Start a new Codex session where you usually work. In WSL, that is a Linux folder such as
   `~/projects/…`: your runs are kept in the folder you start in.

**It worked when** `/skills` in Codex lists `run-workflow` and `write-your-method`. Then tell
Codex: `Run write-your-method with durweg.` The first time, it asks whether you want to be talked to
in Chinese or English.

## 🔒 Codex's sandbox and `~/Durweg`

Codex runs commands in a sandbox where only your project folder can be written, and the network is
off. Durweg keeps your settings and your library in `~/Durweg`, so:

- Commands that write there (setting the language, the first run, adding a workflow) ask you for
  approval; approve them.
- `durweg library available` and `durweg library add` need the network; approve them too.
- If something cannot write to `~/Durweg`, Durweg says so in one sentence instead of an error
  trace.

## 🔎 Why there is no `durweg` command in Codex

Codex does not put a plugin's programs on the PATH. The skill finds Durweg inside the plugin by
itself and uses its full path, so you will see commands like
`"…/.codex/plugins/cache/durweg/durweg/1.4.0/bin/durweg" status …`. You do not need to do anything.

## 📅 Updating and removing

| You want to | Do this |
| :--- | :--- |
| Update Durweg itself | • `codex plugin marketplace upgrade durweg` in a terminal<br>• Then start a new Codex session (the old version's folder is removed) |
| Update your workflows and catalogs | • Ask Codex to run `durweg update`<br>• Its Durweg line points to the command above: that is expected |
| Remove Durweg | • `codex plugin remove durweg@durweg`, then `codex plugin marketplace remove durweg`<br>• Your `~/Durweg` folder and your runs stay |

## 🛠️ If you installed with the installer, or as a Claude Code plugin, too

- **Installer and Codex plugin:** the installer's `durweg` is on the PATH, so Codex uses that one.
  If the two versions differ, run the installer again (or `durweg update`, from version 1.1.0 on),
  or remove one of them (`durweg uninstall` removes the installer's).
- **Claude Code plugin and Codex plugin:** each agent uses its own; they share `~/Durweg`. The
  example write-your-method in your library points to one of them and moves to the other only when
  that one is removed.
