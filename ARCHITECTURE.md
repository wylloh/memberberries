# System Architecture Overview

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Claude Code Session                      │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  User: "Implement user authentication"               │   │
│  └──────────────────────────────────────────────────────┘   │
│                            ↓                                 │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Memory System provides relevant context:            │   │
│  │  • Past solutions to auth problems                   │   │
│  │  • User preferences (coding style, tools)            │   │
│  │  • Project architecture decisions                    │   │
│  └──────────────────────────────────────────────────────┘   │
│                            ↓                                 │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Claude Code works with enhanced context             │   │
│  │  • Knows your conventions                            │   │
│  │  • Aware of past solutions                           │   │
│  │  • Understands project structure                     │   │
│  └──────────────────────────────────────────────────────┘   │
│                            ↓                                 │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Save new insights back to memory                    │   │
│  │  • What worked                                       │   │
│  │  • What didn't                                       │   │
│  │  • Key decisions made                                │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

## Component Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                     Memory Manager Core                      │
│                  (memory_manager.py)                         │
│                                                              │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐            │
│  │ Preferences│  │  Projects  │  │  Solutions │            │
│  │  Storage   │  │   Storage  │  │   Storage  │            │
│  └────────────┘  └────────────┘  └────────────┘            │
│         │               │               │                   │
│         └───────────────┴───────────────┘                   │
│                         │                                   │
│              ┌──────────▼──────────┐                        │
│              │   Semantic Search    │                        │
│              │   (Embeddings)       │                        │
│              └──────────┬──────────┘                        │
│                         │                                   │
│              ┌──────────▼──────────┐                        │
│              │   Memory Index       │                        │
│              │   (JSON)             │                        │
│              └─────────────────────┘                        │
└──────────────────────────────────────────────────────────────┘
                         ▲
                         │
        ┌────────────────┴────────────────┐
        │                                 │
┌───────▼────────┐              ┌────────▼────────┐
│  CLI Interface │              │  Integration    │
│ (claude_memory │              │  (integration.py)│
│     .py)       │              └─────────────────┘
└────────────────┘                        ▲
        │                                 │
        │                         ┌───────┴───────┐
        │                         │  Claude Code  │
        │                         │    Session    │
        └─────────────────────────┴───────────────┘
```

## Data Flow

### 1. Context Retrieval (Session Start)

```
User Input: "Implement feature X"
     ↓
integration.py: session_start()
     ↓
MemoryManager: get_relevant_context()
     ↓
     ├─→ Search preferences (semantic)
     ├─→ Load project context (hash lookup)
     └─→ Search solutions (semantic)
     ↓
Combine all context
     ↓
Return formatted context string
     ↓
User pastes into Claude Code
```

### 2. Insight Storage (During Session)

```
User: "Save this solution"
     ↓
CLI or integration.py: add_solution()
     ↓
MemoryManager:
     ├─→ Generate embedding for content
     ├─→ Create unique ID (hash)
     ├─→ Save to solutions/[id].json
     └─→ Update memory_index.json
     ↓
Confirmation to user
```

### 3. Search Process

```
User: "Find solutions about auth"
     ↓
CLI: search command
     ↓
MemoryManager: search_solutions()
     ↓
     ├─→ Generate query embedding
     ├─→ Calculate similarity with all solutions
     ├─→ Sort by similarity score
     └─→ Return top K results
     ↓
Display to user
```

## File System Layout

```
~/.claude-code-memory/
│
├── memory_index.json           ← Central index (fast lookup)
│   ├── preferences[]           ← Array of preference objects
│   ├── projects{}              ← Map of project hash → metadata
│   ├── solutions[]             ← Array of solution objects
│   └── sessions[]              ← Array of session objects
│
├── preferences/
│   ├── coding_style.md         ← Human-readable preferences
│   ├── tools.md
│   └── workflow.md
│
├── projects/
│   ├── [project-hash-1]/
│   │   └── context.json        ← Full project context
│   └── [project-hash-2]/
│       └── context.json
│
├── solutions/
│   ├── [solution-id-1].json    ← Individual solution files
│   ├── [solution-id-2].json
│   └── ...
│
└── sessions/
    ├── [session-id-1].json     ← Session summaries
    └── [session-id-2].json
```

## Semantic Search Mechanism

### Current Implementation (Simple)

```
Text → Simple Hash-Based Embedding (128-dim vector)
     ↓
Normalize to unit length
     ↓
Store in index
     ↓
Query time: Cosine similarity with all stored embeddings
     ↓
Return top K matches
```

### Upgrade Path (Better Quality)

```
Text → Sentence Transformer Model
     ↓
     [option 1: Local]
     "all-MiniLM-L6-v2" (384-dim)
     
     [option 2: API]
     OpenAI text-embedding-ada-002 (1536-dim)
     ↓
Store embeddings
     ↓
Use same cosine similarity for search
```

## Key Design Decisions

### 1. File-Based Storage
**Why:** Simple, portable, no database required, easy to backup/version control
**Trade-off:** Not suitable for >10,000 entries (but fine for personal use)

### 2. JSON Index + Individual Files
**Why:** Fast lookups via index, human-readable individual files
**Trade-off:** Two-step process (index + file), requires consistency

### 3. Simple Embeddings (Default)
**Why:** Zero external dependencies, works everywhere
**Trade-off:** Lower quality search results (but upgradeable)

### 4. Manual Context Injection
**Why:** User controls what context Claude Code sees
**Trade-off:** Not automatic (but more transparent)

## Performance Characteristics

### Search Performance
- **Small (<100 items):** Instant (<10ms)
- **Medium (100-1000 items):** Fast (<100ms)
- **Large (>1000 items):** Consider upgrading to vector DB

### Storage
- **Per preference:** ~1-2 KB
- **Per solution:** ~2-5 KB
- **Per project:** ~5-10 KB
- **1000 items:** ~2-5 MB total

### Embedding Generation
- **Simple (current):** <1ms per text
- **Sentence Transformers:** ~50ms per text
- **OpenAI API:** ~200ms per text (network)

## Extension Points

### 1. Better Embeddings
Replace `_simple_embedding()` method with:
- Sentence Transformers (local)
- OpenAI Embeddings (API)
- Custom fine-tuned model

### 2. Vector Database
Replace file storage with:
- ChromaDB
- Pinecone
- Weaviate

### 3. Auto-Extraction
Add session transcript analysis to automatically extract:
- Preferences from conversation
- Solutions from code blocks
- Project decisions from architecture discussions

### 4. Web Interface
Build a simple web UI to:
- Browse all memories
- Search and filter
- Edit and organize
- Visualize connections

### 5. Git Integration
Add git hooks to:
- Auto-save project context on commit
- Extract patterns from commit messages
- Track architectural evolution

## Security Considerations

1. **Local Storage Only:** All data stays on your machine
2. **No API Keys:** System doesn't require any external services
3. **Plain Text:** Easy to audit, no encryption overhead
4. **User Control:** Explicit save/load operations

For sensitive projects, store memory on encrypted filesystem.

## Troubleshooting Guide

### Search Returns No Results
- **Cause:** Empty index or no relevant content
- **Fix:** Run demo.py to populate with examples

### Search Returns Irrelevant Results  
- **Cause:** Simple embeddings are less accurate
- **Fix:** Upgrade to Sentence Transformers

### Memory Files Corrupted
- **Cause:** Write interrupted or manual edit error
- **Fix:** Restore from backup (use export command regularly)

### Context Too Large for Claude Code
- **Cause:** Too many results returned
- **Fix:** Reduce top_k parameters in integration.py

## Future Improvements

1. **Automatic timestamped backups**
2. **Merge/deduplicate similar entries**
3. **Tag suggestions based on content**
4. **Visual memory graph/connections**
5. **Import from other sources (notes, docs)**
6. **Share memories with team (encrypted)**
7. **Claude Code plugin/extension**
