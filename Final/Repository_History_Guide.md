# A3 — Commit history: what exists and how to add real individual commits

## What was checked (8 Nov 2026)

* Repository: <https://github.com/zondbebox/SE-2623_Endterm> — public, default and only branch `main`.
* History at the start of the Final: **one commit**, `a7e5c749095e63e1cff1280b95279ca8bae6e447`, message "Initial commit", 6 Nov 2026 17:29 UTC, author and committer name `zombeparkour09`, GitHub login `zondbebox`. GitHub lists one contributor (`zondbebox`, 1 contribution).
* The team confirmed that `zondbebox` is **Mengdigerey Zhanzhol's** account.
* The local folder and `SE-2623_Endterm.zip` are identical to this commit (1,164 files compared, 0 differences).

**Update 8 Nov 2026:** Final commits `ca5d0e5` and later were pushed from Zhanzhol's account with Daniil and Daulet as `Co-authored-by` co-authors (they agreed). Their own commits from their own accounts are still recommended.

**Consequence for the Final rubric (A3: "a commit history in which each member's work is visible under their own account"):** not met yet. Daniil's and Daulet's work exists in the files but not under their accounts. This cannot be fixed by anyone else: commits must be made by each member, from their own GitHub account, on their own computer.

## Rules

* Do **not** rewrite or force-push history; do not fake dates or authors; do not commit "as" someone else.
* Each person commits only work they actually did (now or in the remaining Week 10 time).
* Never commit `runtime/session.key`, `runtime/audit.jsonl`, `backups/`, `.env` files or real personal data.

## Step by step (each member, own laptop)

1. Zhanzhol adds Daniil and Daulet as collaborators: GitHub → repository → **Settings → Collaborators → Add people** (needs the owner's action; Claude did not change any GitHub settings).
2. Each member installs Git, signs in to their own GitHub account and sets their identity once:
   ```bash
   git config --global user.name  "Galitskiy Daniil"
   git config --global user.email "<the email linked to your GitHub account>"
   ```
3. Clone and branch:
   ```bash
   git clone https://github.com/zondbebox/SE-2623_Endterm.git
   cd SE-2623_Endterm
   git switch -c final/<your-name>
   ```
4. Make a real, small change in your own area, test it, commit and push:
   ```bash
   git add <files>
   git commit -m "Final: <what you changed and why>"
   git push -u origin final/<your-name>
   ```
5. Open a pull request on GitHub; another member reviews and merges it. The merged commits stay under the author's account.

## Genuine Final-week work each member can commit (suggestions — choose what you actually do)

| Member | Real change in their own area |
|---|---|
| Zhanzhol | Add the new root `README.md` and the `Final/` folder (prepared in this package); add a `.gitignore` for `runtime/`, `backups/`, `data/uploads/`, `data/restore_checks/`; change the top-bar label "Endterm / Stage 2" to "Final" in `templates/base.html`. |
| Daniil | Add the real Final user-test rows to `Final/Testing/final_test_results.csv`, rebuild the report and slides, and commit the results; or add the location drop-down suggested by the analysis. |
| Daulet | Re-record the Assignment 4 video on the current interface and commit the updated captions (`Video/subtitles_EN_PLANNED.srt`) and a link file; or run the Linux scripts on the dual-boot laptop and commit the log to `Final/Evidence/`. |

After pushing, check <https://github.com/zondbebox/SE-2623_Endterm/commits/main> — each commit should show the author's own avatar and login. Write the commit links into the contribution statements (`Final/Contributions/`).

## How to find a commit live in the defense

```bash
git log --oneline --author="Daniil"           # commits by one person
git log --oneline -- Campus_Lost_Found/app.py # commits that touched a file
git show a7e5c74 --stat                        # what one commit changed
```

On GitHub: repository → **History** (or `…/commits/main`) → click the commit → "Browse files".
