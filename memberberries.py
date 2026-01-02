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
        include_project=not args.no_project
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


def stats_cmd(args, bm: BerryManager):
    """Show berry statistics."""
    stats = bm.get_stats()
    
    print("\n🫐 === Memberberries Statistics ===")
    print(f"Preference berries: {stats['preferences']}")
    print(f"Project berries: {stats['projects']}")
    print(f"Solution berries: {stats['solutions']}")
    print(f"Session berries: {stats['sessions']}")
    print()


def export_cmd(args, bm: BerryManager):
    """Export all memberberries."""
    bm.export_memory(args.output)


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
    
    # Concentrate session
    session_parser = subparsers.add_parser('concentrate-session', help='Concentrate session berry')
    session_parser.add_argument('summary', help='Session summary')
    session_parser.add_argument('-l', '--learnings', help='Pipe-separated key learnings')
    session_parser.add_argument('-p', '--project', help='Project path')
    
    # Stats
    subparsers.add_parser('stats', help='Show berry statistics')
    
    # Export
    export_parser = subparsers.add_parser('export', help='Export all memberberries')
    export_parser.add_argument('output', help='Output file path')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Initialize berry manager
    bm = BerryManager(args.base_path)
    
    # Execute command
    commands = {
        'concentrate': concentrate_preference_cmd,
        'concentrate-solution': concentrate_solution_cmd,
        'juice': search_solutions_cmd,
        'concentrate-project': concentrate_project_cmd,
        'juice-project': get_project_cmd,
        'juice-context': juice_context_cmd,
        'concentrate-session': concentrate_session_cmd,
        'stats': stats_cmd,
        'export': export_cmd
    }
    
    if args.command in commands:
        commands[args.command](args, bm)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
