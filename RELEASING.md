# Releasing Memberberries

This guide documents the release process for maintainers.

## Version Numbering

We follow [Semantic Versioning](https://semver.org/):
- **MAJOR** (x.0.0): Breaking changes
- **MINOR** (1.x.0): New features, backwards compatible
- **PATCH** (1.1.x): Bug fixes, backwards compatible

## Pre-Release Checklist

- [ ] All tests pass (when implemented)
- [ ] CHANGELOG.md updated with changes
- [ ] README.md reflects current features
- [ ] Documentation is up to date
- [ ] No sensitive data in code or comments

## Creating a Release

### 1. Update Version Numbers

Update version in:
- `CHANGELOG.md` - Add release date
- `README.md` - If version is mentioned

### 2. Commit and Tag

```bash
# Commit any final changes
git add -A
git commit -m "chore: prepare release v1.x.x"

# Create annotated tag
git tag -a v1.x.x -m "Release v1.x.x"

# Push with tags
git push origin main --tags
```

### 3. Create GitHub Release

1. Go to [Releases](https://github.com/wylloh/memberberries/releases)
2. Click "Draft a new release"
3. Select the tag you just created
4. Title: `v1.x.x - Release Title`
5. Description: Copy from CHANGELOG.md
6. Click "Publish release"

### Release Notes Template

```markdown
## What's New

### Features
- Feature 1
- Feature 2

### Bug Fixes
- Fix 1

### Documentation
- Doc update 1

## Upgrade Notes

Any breaking changes or migration steps.

## Full Changelog

https://github.com/wylloh/memberberries/compare/v1.x.x...v1.y.y
```

## Post-Release

- [ ] Verify release appears on GitHub
- [ ] Test installation from fresh clone
- [ ] Announce on relevant channels (optional)
- [ ] Monitor issues for release-related problems

## Hotfix Process

For urgent fixes:

```bash
# Create hotfix branch from tag
git checkout -b hotfix/v1.x.1 v1.x.0

# Make fix, commit
git add -A
git commit -m "fix: description"

# Merge to main
git checkout main
git merge hotfix/v1.x.1

# Tag and release
git tag -a v1.x.1 -m "Hotfix v1.x.1"
git push origin main --tags
```

## GitHub Repository Setup

### Issue Templates

Located in `.github/ISSUE_TEMPLATE/`:
- `bug_report.md` - Bug reports
- `feature_request.md` - Feature requests

### Labels

Recommended labels:
- `bug` - Something isn't working
- `enhancement` - New feature request
- `documentation` - Documentation improvements
- `good first issue` - Good for newcomers
- `help wanted` - Extra attention needed
- `question` - Further information requested

### Topics

Repository topics:
- `claude-code`
- `ai-memory`
- `developer-tools`
- `python`
- `productivity`

## Promotion Channels

When announcing releases:
- GitHub Discussions
- Reddit: r/ClaudeAI, r/Python
- Twitter/X: #ClaudeCode
- Claude community Discord
