# GitHub Repository Settings Configuration

This document provides instructions for configuring GitHub repository settings to enable squash merge as the default merge strategy for the CareerAssist project.

**IMPORTANT:** These settings must be applied manually through the GitHub web interface, GitHub CLI, or GitHub API. This file is documentation only—it is not automatically applied.

## Recommended Merge Settings

The following table shows the recommended merge settings for this repository:

| Setting | Value | Purpose |
|---------|-------|---------|
| **Allow squash merging** | ✅ Enabled | Combines all PR commits into one (RECOMMENDED) |
| **Allow merge commits** | ❌ Disabled | Prevents regular merge commits (optional but recommended) |
| **Allow rebase merging** | ❌ Disabled | Alternative to squash merge (optional) |
| **Automatically delete head branches** | ✅ Enabled | Cleans up branches after merge |
| **Default merge method** | `squash` | Use squash merge by default |
| **Squash merge commit title** | `PR_TITLE` | Use PR title as commit message |
| **Squash merge commit message** | `PR_BODY` | Use PR body as commit description |

---
# Instructions for Applying These Settings

## Method 1: GitHub Web Interface (Easiest)
1. Navigate to: https://github.com/rom812/CareerAssist/settings
2. Scroll to "Pull Requests" section
3. Configure the following:
   - ✅ Check "Allow squash merging"
   - ❌ Uncheck "Allow merge commits" (optional but recommended)
   - ❌ Uncheck "Allow rebase merging" (optional)
   - ✅ Check "Automatically delete head branches"
4. Save changes

## Method 2: GitHub CLI (gh)
```bash
# Enable squash merge, disable other merge methods, and auto-delete branches
gh repo edit rom812/CareerAssist \
  --enable-squash-merge \
  --disable-merge-commit \
  --disable-rebase-merge \
  --delete-branch-on-merge
```

**Note:** The GitHub CLI does not currently support setting the default merge method to squash. That must be configured through the web interface under Settings → General → Pull Requests.

## Method 3: GitHub API
```bash
# Using curl (requires GitHub personal access token)
curl -X PATCH \
  -H "Authorization: token YOUR_GITHUB_TOKEN" \
  -H "Accept: application/vnd.github.v3+json" \
  https://api.github.com/repos/rom812/CareerAssist \
  -d '{
    "allow_squash_merge": true,
    "allow_merge_commit": false,
    "allow_rebase_merge": false,
    "delete_branch_on_merge": true
  }'
```

---
# Why Squash Merge?

When you use "Squash and Merge":
- All commits in the PR are combined into a single commit
- The main branch history stays clean and linear
- Each commit on main represents a complete feature or fix
- Makes it easier to review history and revert changes
- Prevents "work in progress" or "fix typo" commits from cluttering history

This is especially useful for PRs like "hide-pr-from-history" where you don't
want the intermediate commits to appear in the repository's commit history.
