import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_import_linter_contracts_hold() -> None:
    executable = shutil.which("lint-imports")
    assert executable is not None, "import-linter is not installed in the environment"
    result = subprocess.run([executable], cwd=ROOT, capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stdout + result.stderr
