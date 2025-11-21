"""
Temporary script to update imports from orchestration to agents
"""
import re
from pathlib import Path

# Files that need updates
files_to_update = [
    "cockpit/api.py",
    "examples/advanced_workflows.py",
    "run_demo.py",
    "tests/test_system_integration.py",
    "tests/test_integration.py",
    "examples/test_live_agent.py",
    "src/uaef/agents/agents.py",
    "examples/view_workflow_status.py",
    "migrations/env.py",
    "src/uaef/agents/workflow.py",
    "GETTING_STARTED.md",
    "examples/workflow_monitor.py",
    "examples/simple_workflow_demo.py",
    "FINAL_IMPLEMENTATION_SUMMARY.md",
    "IMPLEMENTATION_STATUS.md",
    "functions/scheduled_workflow.py",
    "functions/workflow_trigger.py",
    "tests/test_workflow.py",
    "src/uaef/agents/__init__.py",
    "tests/test_agents.py",
]

def update_file(file_path: Path):
    """Update imports in a file"""
    try:
        content = file_path.read_text(encoding='utf-8')
        original = content

        # Replace all variations
        content = re.sub(r'from uaef\.orchestration', 'from uaef.agents', content)
        content = re.sub(r'import uaef\.orchestration', 'import uaef.agents', content)
        content = re.sub(r'uaef\.orchestration', 'uaef.agents', content)

        if content != original:
            file_path.write_text(content, encoding='utf-8')
            print(f"[OK] Updated: {file_path}")
            return True
        else:
            print(f"  Skipped: {file_path} (no changes needed)")
            return False
    except Exception as e:
        print(f"[ERROR] Error updating {file_path}: {e}")
        return False

def main():
    root = Path(__file__).parent
    updated = 0

    print("Updating imports from orchestration to agents...")
    print("=" * 60)

    for file_path in files_to_update:
        full_path = root / file_path
        if full_path.exists():
            if update_file(full_path):
                updated += 1
        else:
            print(f"  Not found: {file_path}")

    print("=" * 60)
    print(f"Updated {updated} files")

if __name__ == "__main__":
    main()
