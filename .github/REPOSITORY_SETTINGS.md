# GitHub Repository Settings Configuration
#
# This file documents the recommended GitHub repository settings
# for the CareerAssist project to maintain a clean git history.
#
# NOTE: These settings must be applied manually in the GitHub web interface
# at: https://github.com/rom812/CareerAssist/settings
#
# Alternatively, use GitHub API or terraform/infrastructure-as-code tools

---
# Repository Settings > Pull Requests

# Merge button options (enable/disable merge strategies)
merge_options:
  # Allow squash merging - RECOMMENDED (keeps history clean)
  allow_squash_merge: true
  
  # Allow merge commits - Can be disabled to enforce squash merge
  allow_merge_commit: false
  
  # Allow rebase merging - Alternative to squash merge
  allow_rebase_merge: false
  
  # Automatically delete head branches after pull requests are merged
  delete_branch_on_merge: true

# Default merge method when merging PRs
default_merge_method: "squash"

# Squash merge commit message
# Options: "PR_TITLE", "COMMIT_MESSAGES", "BLANK"
squash_merge_commit_title: "PR_TITLE"
squash_merge_commit_message: "PR_BODY"

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
# Enable squash merge only
gh repo edit rom812/CareerAssist \
  --enable-squash-merge \
  --disable-merge-commit \
  --disable-rebase-merge \
  --delete-branch-on-merge

# Set default to squash merge
gh repo edit rom812/CareerAssist --default-branch main
```

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
