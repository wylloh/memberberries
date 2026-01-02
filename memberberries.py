#!/usr/bin/env python3
"""
Memberberries CLI
🫐 Member when Claude Code had no memory? We memberberry!

Allows easy interaction with the berry storage from command line.
"""

import argparse
import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from berry_manager import BerryManager


def concentrate_preference_cmd(args, bm: BerryManager):
    """Concentrate a new preference berry."""
    tags = args.tags.split(',') if args.tags else []
    result = bm.add_preference(args.category, args.content, tags)
    print(f"🫐 Preference berry concentrated: {result['category']}")
    print(f"  Tags: {', '.join(result['tags'])}")


def concentrate_solution_cmd(args, bm: BerryManager):
    """Concentrate a new solution berry."""
    tags = args.tags.split(',') if args.tags else []
    result = bm.add_solution(
        problem=args.problem,
        solution=args.solution,
        tags=tags,
        code_snippet=args.code
    )
    print(f"🫐 Solution berry concentrated: {result['id']}")


def search_solutions_cmd(args, bm: BerryManager):
    """Juice solution berries (search)."""
    results = bm.search_solutions(args.query, top_k=args.limit)
    
    if not results:
        print("No berries found. Member to concentrate some first!")
        return
    
    print(f"\n🫐 Juiced {len(results)} relevant berry(ies):\n")
    for i, sol in enumerate(results, 1):
        print(f"{i}. {sol['problem']}")
        print(f"   Solution: {sol['solution']}")
        if sol.get('tags'):
            print(f"   Tags: {', '.join(sol['tags'])}")
        if sol.get('code_snippet'):
            print(f"   Code:\n{sol['code_snippet']}")
        print()


def concentrate_project_cmd(args, bm: BerryManager):
    """Concentrate project berry."""
    context = {
        "name": args.name,
        "description": args.description,
        "architecture": args.architecture,
        "conventions": args.conventions.split(',') if args.conventions else [],
        "tech_stack": args.tech_stack.split(',') if args.tech_stack else []
    }
    
    project_hash = bm.add_project_context(args.path, context)
    print(f"🫐 Project berry concentrated: {project_hash}")
    print(f"  Path: {args.path}")


def get_project_cmd(args, bm: BerryManager):
    """Juice project berry."""
    context = bm.get_project_context(args.path)
    
    if not context:
        print(f"No berry found for project: {args.path}")
        return
    
    print(f"\n🫐 Project: {context.get('name', 'Unknown')}")
    print(f"Path: {context.get('project_path')}")
    print(f"Last updated: {context.get('last_updated')}")
    print(f"\nDescription: {context.get('description')}")
    print(f"\nArchitecture: {context.get('architecture')}")
    print(f"Tech Stack: {', '.join(context.get('tech_stack', []))}")
    print(f"Conventions: {', '.join(context.get('conventions', []))}")


def juice_context_cmd(args, bm: BerryManager):
    """Juice relevant berries for a query."""
    project_path = args.project or os.getcwd()

    context = bm.get_relevant_context(
        query=args.query,
        project_path=project_path,
        include_preferences=not args.no_preferences,
        include_solutions=not args.no_solutions,
        include_project=not args.no_project,
        include_errors=not args.no_errors,
        include_antipatterns=not args.no_antipatterns,
        include_git_conventions=not args.no_git_conventions,
        include_testing=not args.no_testing,
        include_api_notes=not args.no_api_notes
    )

    print("\n" + "="*60)
    print("JUICED MEMBERBERRIES")
    print("="*60)
    print(context)
    print("="*60 + "\n")


def concentrate_session_cmd(args, bm: BerryManager):
    """Concentrate a session berry."""
    learnings = args.learnings.split('|') if args.learnings else []
    result = bm.save_session_summary(
        summary=args.summary,
        key_learnings=learnings,
        project_path=args.project
    )
    print(f"🫐 Session berry concentrated: {result['id']}")


# NEW MEMORY TYPE COMMANDS

def concentrate_error_cmd(args, bm: BerryManager):
    """Concentrate an error pattern berry."""
    tags = args.tags.split(',') if args.tags else []
    result = bm.add_error(
        error_message=args.error,
        resolution=args.resolution,
        context=args.context,
        tags=tags
    )
    print(f"🫐 Error berry concentrated: {result['id']}")


def search_errors_cmd(args, bm: BerryManager):
    """Juice error berries (search)."""
    results = bm.search_errors(args.query, top_k=args.limit)

    if not results:
        print("No error berries found.")
        return

    print(f"\n🫐 Juiced {len(results)} error berry(ies):\n")
    for i, err in enumerate(results, 1):
        print(f"{i}. {err['error_message'][:80]}...")
        print(f"   Resolution: {err['resolution']}")
        if err.get('context'):
            print(f"   Context: {err['context']}")
        if err.get('tags'):
            print(f"   Tags: {', '.join(err['tags'])}")
        print()


def concentrate_antipattern_cmd(args, bm: BerryManager):
    """Concentrate an antipattern berry."""
    tags = args.tags.split(',') if args.tags else []
    result = bm.add_antipattern(
        pattern=args.pattern,
        reason=args.reason,
        alternative=args.alternative,
        tags=tags
    )
    print(f"🫐 Antipattern berry concentrated: {result['id']}")


def search_antipatterns_cmd(args, bm: BerryManager):
    """Juice antipattern berries (search)."""
    results = bm.search_antipatterns(args.query, top_k=args.limit)

    if not results:
        print("No antipattern berries found.")
        return

    print(f"\n🫐 Juiced {len(results)} antipattern berry(ies):\n")
    for i, ap in enumerate(results, 1):
        print(f"{i}. DON'T: {ap['pattern']}")
        print(f"   WHY: {ap['reason']}")
        print(f"   INSTEAD: {ap['alternative']}")
        if ap.get('tags'):
            print(f"   Tags: {', '.join(ap['tags'])}")
        print()


def concentrate_git_convention_cmd(args, bm: BerryManager):
    """Concentrate a git convention berry."""
    tags = args.tags.split(',') if args.tags else []
    result = bm.add_git_convention(
        convention_type=args.type,
        pattern=args.pattern,
        example=args.example,
        tags=tags
    )
    print(f"🫐 Git convention berry concentrated: {result['id']}")


def search_git_conventions_cmd(args, bm: BerryManager):
    """Juice git convention berries (search)."""
    results = bm.search_git_conventions(args.query, top_k=args.limit)

    if not results:
        print("No git convention berries found.")
        return

    print(f"\n🫐 Juiced {len(results)} git convention berry(ies):\n")
    for i, conv in enumerate(results, 1):
        print(f"{i}. [{conv['convention_type']}]")
        print(f"   Pattern: {conv['pattern']}")
        print(f"   Example: {conv['example']}")
        if conv.get('tags'):
            print(f"   Tags: {', '.join(conv['tags'])}")
        print()


def concentrate_dependency_cmd(args, bm: BerryManager):
    """Concentrate a dependency berry."""
    tags = args.tags.split(',') if args.tags else []
    result = bm.add_dependency(
        name=args.name,
        version_constraint=args.version,
        notes=args.notes,
        tags=tags
    )
    print(f"🫐 Dependency berry concentrated: {result['name']}")


def get_dependency_cmd(args, bm: BerryManager):
    """Juice a dependency berry by name."""
    result = bm.get_dependency(args.name)

    if not result:
        print(f"No dependency berry found for: {args.name}")
        return

    print(f"\n🫐 Dependency: {result['name']}")
    if result.get('version_constraint'):
        print(f"Version: {result['version_constraint']}")
    if result.get('notes'):
        print(f"Notes: {result['notes']}")
    if result.get('tags'):
        print(f"Tags: {', '.join(result['tags'])}")
    print()


def concentrate_testing_cmd(args, bm: BerryManager):
    """Concentrate a testing pattern berry."""
    tags = args.tags.split(',') if args.tags else []
    result = bm.add_testing_pattern(
        strategy=args.strategy,
        framework=args.framework,
        pattern=args.pattern,
        example=args.example,
        tags=tags
    )
    print(f"🫐 Testing pattern berry concentrated: {result['id']}")


def search_testing_cmd(args, bm: BerryManager):
    """Juice testing pattern berries (search)."""
    results = bm.search_testing_patterns(args.query, top_k=args.limit)

    if not results:
        print("No testing pattern berries found.")
        return

    print(f"\n🫐 Juiced {len(results)} testing pattern berry(ies):\n")
    for i, tp in enumerate(results, 1):
        print(f"{i}. [{tp['strategy']} - {tp['framework']}]")
        print(f"   Pattern: {tp['pattern']}")
        if tp.get('example'):
            print(f"   Example:\n{tp['example']}")
        if tp.get('tags'):
            print(f"   Tags: {', '.join(tp['tags'])}")
        print()


def concentrate_environment_cmd(args, bm: BerryManager):
    """Concentrate an environment berry."""
    tags = args.tags.split(',') if args.tags else []
    result = bm.add_environment(
        env_type=args.type,
        config=args.config,
        notes=args.notes,
        tags=tags
    )
    print(f"🫐 Environment berry concentrated: {result['env_type']}")


def get_environment_cmd(args, bm: BerryManager):
    """Juice an environment berry by type."""
    result = bm.get_environment(args.type)

    if not result:
        print(f"No environment berry found for: {args.type}")
        return

    print(f"\n🫐 Environment: {result['env_type']}")
    print(f"Config: {result['config']}")
    if result.get('notes'):
        print(f"Notes: {result['notes']}")
    if result.get('tags'):
        print(f"Tags: {', '.join(result['tags'])}")
    print()


def concentrate_api_note_cmd(args, bm: BerryManager):
    """Concentrate an API note berry."""
    tags = args.tags.split(',') if args.tags else []
    result = bm.add_api_note(
        service_name=args.service,
        notes=args.notes,
        endpoint=args.endpoint,
        tags=tags
    )
    print(f"🫐 API note berry concentrated: {result['id']}")


def search_api_notes_cmd(args, bm: BerryManager):
    """Juice API note berries (search)."""
    results = bm.search_api_notes(args.query, top_k=args.limit)

    if not results:
        print("No API note berries found.")
        return

    print(f"\n🫐 Juiced {len(results)} API note berry(ies):\n")
    for i, note in enumerate(results, 1):
        print(f"{i}. [{note['service_name']}]")
        if note.get('endpoint'):
            print(f"   Endpoint: {note['endpoint']}")
        print(f"   Notes: {note['notes']}")
        if note.get('tags'):
            print(f"   Tags: {', '.join(note['tags'])}")
        print()


def stats_cmd(args, bm: BerryManager):
    """Show berry statistics."""
    stats = bm.get_stats()

    print("\n🫐 === Memberberries Statistics ===")
    print(f"Storage: {bm.base_path}")
    print()
    print("Original Types:")
    print(f"  Preference berries: {stats['preferences']}")
    print(f"  Project berries: {stats['projects']}")
    print(f"  Solution berries: {stats['solutions']}")
    print(f"  Session berries: {stats['sessions']}")
    print()
    print("Extended Types:")
    print(f"  Error berries: {stats['errors']}")
    print(f"  Antipattern berries: {stats['antipatterns']}")
    print(f"  Git convention berries: {stats['git_conventions']}")
    print(f"  Dependency berries: {stats['dependencies']}")
    print(f"  Testing berries: {stats['testing']}")
    print(f"  Environment berries: {stats['environment']}")
    print(f"  API note berries: {stats['api_notes']}")
    print()


def export_cmd(args, bm: BerryManager):
    """Export all memberberries."""
    bm.export_memory(args.output)


def init_gitignore_cmd(args, bm: BerryManager):
    """Add .memberberries/ to project's .gitignore."""
    project_path = args.path or os.getcwd()
    gitignore_path = Path(project_path) / ".gitignore"

    # Read template
    template_path = Path(__file__).parent / "templates" / "gitignore_template"
    if template_path.exists():
        with open(template_path, 'r') as f:
            template_content = f.read()
    else:
        template_content = """# Memberberries local storage
# This directory may contain sensitive information
.memberberries/
"""

    # Check if .gitignore exists and if pattern already present
    if gitignore_path.exists():
        with open(gitignore_path, 'r') as f:
            existing = f.read()
        if '.memberberries/' in existing:
            print("🫐 .memberberries/ already in .gitignore")
            return

        # Append to existing
        with open(gitignore_path, 'a') as f:
            f.write("\n" + template_content)
        print(f"🫐 Added .memberberries/ to {gitignore_path}")
    else:
        # Create new .gitignore
        with open(gitignore_path, 'w') as f:
            f.write(template_content)
        print(f"🫐 Created {gitignore_path} with .memberberries/ entry")


def check_compatibility_cmd(args, bm: BerryManager):
    """Check compatibility with Claude Code features."""
    project_path = Path(args.path) if args.path else Path.cwd()

    print("\n🫐 === Claude Code Compatibility Check ===\n")

    # Check for CLAUDE.md
    claude_md = project_path / "CLAUDE.md"
    claude_dir = project_path / ".claude"

    findings = []

    if claude_md.exists():
        findings.append(("CLAUDE.md", "Found", "Project instructions file"))
        print(f"✓ Found: {claude_md}")
        print("  → Use CLAUDE.md for static rules/instructions")
        print("  → Use Memberberries for dynamic decisions and history")
        print()

    if claude_dir.exists():
        findings.append((".claude/", "Found", "Claude Code config directory"))
        print(f"✓ Found: {claude_dir}")
        print("  → Claude Code is configured for this project")
        print()

    # Check for local memberberries
    local_mb = project_path / ".memberberries"
    if local_mb.exists():
        findings.append((".memberberries/", "Found", "Local Memberberries storage"))
        print(f"✓ Found: {local_mb}")
        print("  → Using per-project Memberberries storage")
        print()

    # Check gitignore
    gitignore = project_path / ".gitignore"
    if gitignore.exists():
        with open(gitignore, 'r') as f:
            content = f.read()
        if '.memberberries/' in content:
            findings.append((".gitignore", "OK", "Memberberries excluded"))
            print("✓ .gitignore: .memberberries/ is excluded")
        else:
            findings.append((".gitignore", "Warning", "Memberberries not excluded"))
            print("⚠ .gitignore: .memberberries/ is NOT excluded")
            print("  → Run: python memberberries.py init-gitignore")
        print()

    # Summary
    print("=== Recommendations ===\n")

    if claude_md.exists():
        print("1. CLAUDE.md detected:")
        print("   - Keep static project rules in CLAUDE.md")
        print("   - Store 'why' decisions in Memberberries project context")
        print("   - Avoid duplicating content between them")
        print()

    print("2. Best Practices:")
    print("   - Use Memberberries for cross-session memory")
    print("   - Use Claude Code session for within-session context")
    print("   - Concentrate insights at end of sessions")
    print()

    print("3. Monitor for Overlap:")
    print("   - Check Claude Code release notes for /memory commands")
    print("   - Re-run this check after Claude Code updates")
    print()

    print(f"See COMPATIBILITY.md for detailed guidance.")
    print()


def main():
    parser = argparse.ArgumentParser(
        description='🫐 Memberberries CLI - Member when Claude Code had no memory?',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Concentrate a coding preference
  %(prog)s concentrate coding_style "Use 4 spaces for indentation" -t python,style
  
  # Concentrate a solution berry
  %(prog)s concentrate-solution "How to parse JSON safely" "Use json.loads with try/except" -t python,json
  
  # Juice berries (search)
  %(prog)s juice "python error handling"
  
  # Concentrate project berry
  %(prog)s concentrate-project /path/to/project -n "My App" -d "Web application" -a "MVC pattern"
  
  # Juice berries for current task
  %(prog)s juice-context "implement user authentication" -p /path/to/project
  
  # View berry statistics
  %(prog)s stats
        """
    )
    
    parser.add_argument('--base-path', help='Base path for berry storage')
    parser.add_argument('--global', dest='global_storage', action='store_true',
                        help='Use global storage (~/.memberberries)')
    parser.add_argument('--local', dest='local_storage', action='store_true',
                        help='Use per-project storage (.memberberries/)')

    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    # Concentrate preference
    pref_parser = subparsers.add_parser('concentrate', help='Concentrate a preference berry')
    pref_parser.add_argument('category', help='Preference category')
    pref_parser.add_argument('content', help='Preference content')
    pref_parser.add_argument('-t', '--tags', help='Comma-separated tags')
    
    # Concentrate solution
    sol_parser = subparsers.add_parser('concentrate-solution', help='Concentrate a solution berry')
    sol_parser.add_argument('problem', help='Problem description')
    sol_parser.add_argument('solution', help='Solution description')
    sol_parser.add_argument('-t', '--tags', help='Comma-separated tags')
    sol_parser.add_argument('-c', '--code', help='Code snippet')
    
    # Juice (search) solutions
    search_parser = subparsers.add_parser('juice', help='Juice solution berries (search)')
    search_parser.add_argument('query', help='Search query')
    search_parser.add_argument('-l', '--limit', type=int, default=3, help='Max results')
    
    # Concentrate project
    proj_parser = subparsers.add_parser('concentrate-project', help='Concentrate project berry')
    proj_parser.add_argument('path', help='Project path')
    proj_parser.add_argument('-n', '--name', required=True, help='Project name')
    proj_parser.add_argument('-d', '--description', default='', help='Description')
    proj_parser.add_argument('-a', '--architecture', default='', help='Architecture notes')
    proj_parser.add_argument('-c', '--conventions', help='Comma-separated conventions')
    proj_parser.add_argument('-s', '--tech-stack', help='Comma-separated tech stack')
    
    # Juice project
    get_proj_parser = subparsers.add_parser('juice-project', help='Juice project berry')
    get_proj_parser.add_argument('path', help='Project path')
    
    # Juice context
    ctx_parser = subparsers.add_parser('juice-context', help='Juice relevant berries')
    ctx_parser.add_argument('query', help='Current task or query')
    ctx_parser.add_argument('-p', '--project', help='Project path')
    ctx_parser.add_argument('--no-preferences', action='store_true', help='Exclude preferences')
    ctx_parser.add_argument('--no-solutions', action='store_true', help='Exclude solutions')
    ctx_parser.add_argument('--no-project', action='store_true', help='Exclude project context')
    ctx_parser.add_argument('--no-errors', action='store_true', help='Exclude error patterns')
    ctx_parser.add_argument('--no-antipatterns', action='store_true', help='Exclude antipatterns')
    ctx_parser.add_argument('--no-git-conventions', action='store_true', help='Exclude git conventions')
    ctx_parser.add_argument('--no-testing', action='store_true', help='Exclude testing patterns')
    ctx_parser.add_argument('--no-api-notes', action='store_true', help='Exclude API notes')

    # Concentrate session
    session_parser = subparsers.add_parser('concentrate-session', help='Concentrate session berry')
    session_parser.add_argument('summary', help='Session summary')
    session_parser.add_argument('-l', '--learnings', help='Pipe-separated key learnings')
    session_parser.add_argument('-p', '--project', help='Project path')

    # === NEW MEMORY TYPE PARSERS ===

    # Concentrate error
    error_parser = subparsers.add_parser('concentrate-error', help='Concentrate an error pattern berry')
    error_parser.add_argument('error', help='Error message or stack trace')
    error_parser.add_argument('resolution', help='How the error was resolved')
    error_parser.add_argument('-c', '--context', help='Context about what was happening')
    error_parser.add_argument('-t', '--tags', help='Comma-separated tags')

    # Juice errors
    juice_error_parser = subparsers.add_parser('juice-errors', help='Search error pattern berries')
    juice_error_parser.add_argument('query', help='Search query')
    juice_error_parser.add_argument('-l', '--limit', type=int, default=3, help='Max results')

    # Concentrate antipattern
    antipattern_parser = subparsers.add_parser('concentrate-antipattern', help='Concentrate an antipattern berry')
    antipattern_parser.add_argument('pattern', help='What NOT to do')
    antipattern_parser.add_argument('reason', help='Why it is bad')
    antipattern_parser.add_argument('alternative', help='What to do instead')
    antipattern_parser.add_argument('-t', '--tags', help='Comma-separated tags')

    # Juice antipatterns
    juice_antipattern_parser = subparsers.add_parser('juice-antipatterns', help='Search antipattern berries')
    juice_antipattern_parser.add_argument('query', help='Search query')
    juice_antipattern_parser.add_argument('-l', '--limit', type=int, default=3, help='Max results')

    # Concentrate git convention
    git_conv_parser = subparsers.add_parser('concentrate-git-convention', help='Concentrate a git convention berry')
    git_conv_parser.add_argument('type', help='Convention type (commit_message, branch_naming, pr_template)')
    git_conv_parser.add_argument('pattern', help='The pattern or rule')
    git_conv_parser.add_argument('example', help='Example demonstrating the convention')
    git_conv_parser.add_argument('-t', '--tags', help='Comma-separated tags')

    # Juice git conventions
    juice_git_conv_parser = subparsers.add_parser('juice-git-conventions', help='Search git convention berries')
    juice_git_conv_parser.add_argument('query', help='Search query')
    juice_git_conv_parser.add_argument('-l', '--limit', type=int, default=3, help='Max results')

    # Concentrate dependency
    dep_parser = subparsers.add_parser('concentrate-dependency', help='Concentrate a dependency berry')
    dep_parser.add_argument('name', help='Package/library name')
    dep_parser.add_argument('-v', '--version', help='Version constraint (e.g., ">=2.0,<3.0")')
    dep_parser.add_argument('-n', '--notes', help='Notes about the dependency')
    dep_parser.add_argument('-t', '--tags', help='Comma-separated tags')

    # Juice dependency (get by name)
    juice_dep_parser = subparsers.add_parser('juice-dependency', help='Get dependency info by name')
    juice_dep_parser.add_argument('name', help='Package/library name')

    # Concentrate testing pattern
    testing_parser = subparsers.add_parser('concentrate-testing', help='Concentrate a testing pattern berry')
    testing_parser.add_argument('strategy', help='Testing strategy (unit, integration, e2e)')
    testing_parser.add_argument('framework', help='Testing framework (pytest, jest, etc.)')
    testing_parser.add_argument('pattern', help='The testing pattern or approach')
    testing_parser.add_argument('-e', '--example', help='Code example')
    testing_parser.add_argument('-t', '--tags', help='Comma-separated tags')

    # Juice testing patterns
    juice_testing_parser = subparsers.add_parser('juice-testing', help='Search testing pattern berries')
    juice_testing_parser.add_argument('query', help='Search query')
    juice_testing_parser.add_argument('-l', '--limit', type=int, default=3, help='Max results')

    # Concentrate environment
    env_parser = subparsers.add_parser('concentrate-environment', help='Concentrate an environment berry')
    env_parser.add_argument('type', help='Environment type (local, docker, ci, staging, production)')
    env_parser.add_argument('config', help='Configuration details')
    env_parser.add_argument('-n', '--notes', help='Additional notes')
    env_parser.add_argument('-t', '--tags', help='Comma-separated tags')

    # Juice environment (get by type)
    juice_env_parser = subparsers.add_parser('juice-environment', help='Get environment config by type')
    juice_env_parser.add_argument('type', help='Environment type')

    # Concentrate API note
    api_parser = subparsers.add_parser('concentrate-api-note', help='Concentrate an API note berry')
    api_parser.add_argument('service', help='Service/API name')
    api_parser.add_argument('notes', help='Notes (rate limits, auth, quirks, etc.)')
    api_parser.add_argument('-e', '--endpoint', help='Specific endpoint')
    api_parser.add_argument('-t', '--tags', help='Comma-separated tags')

    # Juice API notes
    juice_api_parser = subparsers.add_parser('juice-api-notes', help='Search API note berries')
    juice_api_parser.add_argument('query', help='Search query')
    juice_api_parser.add_argument('-l', '--limit', type=int, default=3, help='Max results')

    # Stats
    subparsers.add_parser('stats', help='Show berry statistics')

    # Export
    export_parser = subparsers.add_parser('export', help='Export all memberberries')
    export_parser.add_argument('output', help='Output file path')

    # Init gitignore
    gitignore_parser = subparsers.add_parser('init-gitignore',
                                              help='Add .memberberries/ to .gitignore')
    gitignore_parser.add_argument('path', nargs='?', help='Project path (default: current dir)')

    # Check compatibility
    compat_parser = subparsers.add_parser('check-compatibility',
                                           help='Check Claude Code compatibility')
    compat_parser.add_argument('path', nargs='?', help='Project path (default: current dir)')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    # Determine storage mode
    storage_mode = 'auto'
    if args.global_storage:
        storage_mode = 'global'
    elif args.local_storage:
        storage_mode = 'local'

    # Initialize berry manager
    bm = BerryManager(args.base_path, storage_mode=storage_mode)

    # Execute command
    commands = {
        'concentrate': concentrate_preference_cmd,
        'concentrate-solution': concentrate_solution_cmd,
        'juice': search_solutions_cmd,
        'concentrate-project': concentrate_project_cmd,
        'juice-project': get_project_cmd,
        'juice-context': juice_context_cmd,
        'concentrate-session': concentrate_session_cmd,
        # New memory type commands
        'concentrate-error': concentrate_error_cmd,
        'juice-errors': search_errors_cmd,
        'concentrate-antipattern': concentrate_antipattern_cmd,
        'juice-antipatterns': search_antipatterns_cmd,
        'concentrate-git-convention': concentrate_git_convention_cmd,
        'juice-git-conventions': search_git_conventions_cmd,
        'concentrate-dependency': concentrate_dependency_cmd,
        'juice-dependency': get_dependency_cmd,
        'concentrate-testing': concentrate_testing_cmd,
        'juice-testing': search_testing_cmd,
        'concentrate-environment': concentrate_environment_cmd,
        'juice-environment': get_environment_cmd,
        'concentrate-api-note': concentrate_api_note_cmd,
        'juice-api-notes': search_api_notes_cmd,
        'stats': stats_cmd,
        'export': export_cmd,
        'init-gitignore': init_gitignore_cmd,
        'check-compatibility': check_compatibility_cmd
    }
    
    if args.command in commands:
        commands[args.command](args, bm)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
