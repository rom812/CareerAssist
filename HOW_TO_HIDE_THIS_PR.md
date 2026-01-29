# How to Hide This PR from Git History

This PR (Pull Request) contains configuration changes to enable squash merging, which will help keep the git history clean by combining all commits in a PR into a single commit.

## For This Specific PR

When you're ready to merge this PR to hide it from appearing as multiple commits in the main branch history, follow these steps:

### Option 1: Squash and Merge via GitHub UI

1. Go to the pull request on GitHub
2. Click the **"Squash and merge"** button (instead of regular "Merge pull request")
3. Edit the commit message to something concise like:
   ```
   Configure repository for clean git history with squash merge
   ```
4. Click **"Confirm squash and merge"**

This will combine all commits from this PR into a single commit on the main branch, effectively "hiding" the intermediate commits from the main history.

### Option 2: Squash and Merge via Command Line

```bash
# Checkout main branch
git checkout main

# Merge with squash (combines all commits into one)
git merge --squash copilot/hide-pr-from-history

# Commit with a clean message
git commit -m "Configure repository for clean git history with squash merge"

# Push to GitHub
git push origin main

# Delete the feature branch
git branch -d copilot/hide-pr-from-history
git push origin --delete copilot/hide-pr-from-history
```

## What Happens

After squash merging:
- ✅ Your main branch history will show only ONE commit from this PR
- ✅ The detailed commits ("Initial plan", etc.) will not appear in main branch history
- ✅ The feature branch will be deleted (if configured)
- ✅ You'll have a clean, linear history

## For Future PRs

After this configuration is in place:
1. All future PRs should use "Squash and merge" by default
2. The PR template will remind contributors about this
3. Repository settings will make squash merge the default option

## Verification

After merging, you can verify the clean history with:

```bash
git log --oneline main
```

You should see a single commit for this entire PR, not multiple individual commits.

---

**Remember:** The actual repository settings must be configured in GitHub's web interface or via GitHub API/CLI. See `.github/REPOSITORY_SETTINGS.md` for instructions.
