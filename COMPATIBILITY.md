# Claude Code Compatibility Guide

This document tracks compatibility between Memberberries and Claude Code's evolving features, ensuring they work together effectively without redundancy.

## Feature Comparison

| Feature | Claude Code | Memberberries | Recommendation |
|---------|-------------|---------------|----------------|
| **Project Instructions** | `CLAUDE.md` files | Project context | Use CLAUDE.md for instructions, Memberberries for decisions/history |
| **Conversation Context** | Session-based | Persistent across sessions | Memberberries for long-term memory |
| **Memory Commands** | `/memory` (if available) | `concentrate-*` / `juice-*` | Check for overlap, prefer native if equivalent |
| **Preferences** | Settings/config | Preference berries | Use Memberberries for coding-style preferences |

## How They Complement Each Other

### CLAUDE.md vs Memberberries

**CLAUDE.md** (Claude Code native):
- Static project instructions
- Read automatically at session start
- Best for: Project rules, coding standards, architecture overview

**Memberberries Project Context**:
- Dynamic, can be updated during sessions
- Semantic search across all projects
- Best for: Architecture decisions, tech stack rationale, conventions

**Recommendation**: Use both together:
1. Put static rules in `CLAUDE.md`
2. Store decision history and "why" in Memberberries
3. Cross-reference when juicing context

### Session Context vs Memberberries

**Claude Code Sessions**:
- Context within a single conversation
- Lost when session ends
- Automatic, no user action needed

**Memberberries Sessions**:
- Persists across conversations
- Requires explicit concentrate/juice
- Searchable history

**Recommendation**: Use Memberberries to bridge sessions:
```bash
# End of session
python memberberries.py concentrate-session \
  "Implemented OAuth2 flow" \
  -l "Use PKCE for mobile|Refresh tokens in Redis"

# Start of next session
python juice.py "continue OAuth implementation"
```

## Avoiding Redundancy

### When to Use Memberberries

Use Memberberries when:
- Information should persist across multiple sessions
- You want semantic search across memories
- Content is dynamic and evolves over time
- You need cross-project knowledge sharing

### When to Use Claude Code Native Features

Use native features when:
- Claude Code offers equivalent functionality
- The feature is automatic (no manual steps)
- It's tightly integrated with the session

### Overlap Detection

Run `python memberberries.py check-compatibility` to:
- Detect `CLAUDE.md` files in your project
- Identify potential overlaps
- Get suggestions for optimal usage

## Version Compatibility Matrix

| Memberberries Version | Claude Code Features | Notes |
|-----------------------|----------------------|-------|
| v1.0 | Basic sessions | Fully complementary |
| v1.1 | CLAUDE.md files | Use together, avoid duplication |
| v1.1+ | Future /memory commands | Monitor for overlap |

## Monitoring Claude Code Updates

To stay compatible:
1. Check Claude Code release notes for memory-related features
2. Run `check-compatibility` after Claude Code updates
3. Report compatibility issues at [GitHub Issues](https://github.com/wylloh/memberberries/issues)

## Migration Guidance

If Claude Code adds native memory features:

1. **Evaluate overlap**: Does it replace Memberberries functionality?
2. **Export data**: Use `python memberberries.py export backup.json`
3. **Gradual migration**: Run both in parallel during transition
4. **Keep unique features**: Memberberries may still offer unique value (semantic search, extended types)

## Reporting Compatibility Issues

If you encounter compatibility issues:

1. Check this document for known interactions
2. Run `python memberberries.py check-compatibility`
3. Create an issue with:
   - Claude Code version
   - Memberberries version
   - Description of the conflict
   - Steps to reproduce
