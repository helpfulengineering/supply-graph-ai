import sys
import pytest
from pathlib import Path

def main():
    # Resolve the absolute path to src/plugins
    # Script is in tests/plugins/runner.py -> parent is tests/plugins -> parent is tests -> parent is root
    root_dir = Path(__file__).resolve().parent.parent.parent
    plugins_dir = root_dir / "src" / "plugins"

    if not plugins_dir.exists():
        print(f"❌ Error: Plugins directory not found at {plugins_dir}")
        sys.exit(1)

    # Dynamically discover all 'tests' directories inside each plugin
    plugin_test_paths = []
    for plugin_path in plugins_dir.iterdir():
        if plugin_path.is_dir() and not plugin_path.name.startswith("__"):
            test_dir = plugin_path / "tests"
            if test_dir.exists() and test_dir.is_dir():
                plugin_test_paths.append(str(test_dir))

    if not plugin_test_paths:
        print("⚠️ No plugin tests discovered.")
        sys.exit(0)

    print(f"🔍 Discovered tests for {len(plugin_test_paths)} plugin(s).")
    for p in plugin_test_paths:
        print(f"  - {p}")

    print("\n🚀 Running pytest...\n" + "-"*40)

    # Pass the discovered paths to pytest, along with any CLI args the user provided
    pytest_args = plugin_test_paths + sys.argv[1:]
    exit_code = pytest.main(pytest_args)

    sys.exit(exit_code)

if __name__ == "__main__":
    main()
