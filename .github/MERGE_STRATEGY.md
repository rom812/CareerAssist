# GitHub Configuration for CareerAssist

## Merge Strategy Settings

### Recommended: Squash Merge
To keep the git history clean and focused, it's recommended to use **"Squash and Merge"** for most pull requests.

This combines all commits in a PR into a single commit on the main branch, which:
- Keeps the main branch history clean and readable
- Groups related changes together logically
- Prevents "work in progress" commits from appearing in history
- Makes it easier to revert changes if needed

### How to Enable Squash Merge (Repository Settings)
Repository administrators should configure the following in GitHub Settings:

1. Go to: **Settings** → **General** → **Pull Requests**
2. Enable: **Allow squash merging**
3. (Optional) Disable regular merge commits if you want to enforce squash merge

### For This Repository
Configure these settings in GitHub repository settings:
- ✅ **Allow squash merging** (enabled)
- ✅ **Allow auto-merge** (optional, for automation)
- ❌ **Allow merge commits** (optional, can be disabled to enforce squash)
- ❌ **Allow rebase merging** (optional, alternative to squash)

## Branch Protection Rules
Consider adding branch protection rules for the main branch:
- Require pull request reviews before merging
- Require status checks to pass before merging
- Require branches to be up to date before merging

## Additional Notes
- When creating a PR, the PR template will remind contributors to use squash merge
- Squash merge is particularly useful for feature branches with multiple commits
- For PRs that should not appear in history, always use squash merge with a clear, concise commit message
