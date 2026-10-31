# Updating Durweg and your workflows

`durweg update` brings Durweg itself to the newest release and then the workflows you installed
from git (by name from a catalog, or from a git address) to their newest version. Runs you have
already started are not changed: each run keeps its own copy of the workflow.

1. Open a terminal (on Windows: PowerShell; if Durweg is in WSL, then `wsl`).
2. Run `durweg update`.
3. Read the lines it prints: one for Durweg, one per catalog, and one per workflow:

| Word | Meaning |
| :--- | :--- |
| `updated` | now the newest version (`old -> new`) |
| `unchanged` | was the newest already |
| `skipped` | left as it is, with the reason on the line; see below |
| `failed` | something went wrong; the previous version is kept |

The last line counts them. Durweg keeps the language and the place you chose when you installed it
and asks nothing; it does not install agents or start one.

## What Durweg never changes

- **Workflows in your own folders** (the ones you wrote, or added as `./folder`): they are already
  what you have; Durweg does not touch them (`skipped: your own folder`).
- **A clone you changed**: uncommitted changes, another branch, commits of your own, or a clone that
  has gone a different way from its remote (`diverged`) are skipped, never overwritten or reset.
- **A workflow that changed while it was being updated**: skipped; run `durweg update` again.

## Common reasons for `skipped`

| Reason on the line | What to do |
| :--- | :--- |
| `no access: for a private GitHub repository …` | Run `gh auth login` and `gh auth setup-git` once, then `durweg update` again |
| `cannot connect (offline?)` | Connect to the internet and try again |
| `the remote's default branch is now …` | `durweg library remove <name>`, then add it again |
| `cannot ask GitHub for the newest version` | Durweg itself was not checked (offline); your workflows were still updated |

Only the workflows: `durweg library update` (or `durweg library update <name>`). Running the
installer again also updates them.

**Coming from v1.0:** v1.0 has no `durweg update`. Run the installer of v1.1 or newer once (as in
the README); from then on `durweg update` is enough.
