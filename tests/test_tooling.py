"""Consistency checks for dependency and tooling configuration."""

import re
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


class TestRequirementsLock:
    """Tests for how requirements.txt was compiled."""

    def test_lock_resolved_for_minimum_supported_python(self):
        """The lock must be universal and resolved for the oldest supported Python.

        Compiling for a newer interpreter can pin releases that dropped older Pythons
        (numpy 2.5 needs 3.12+), breaking installs on the minimum version, and compiling
        per-platform drops platform-specific pins (watchdog). Regenerate the lock with
        `make update-requirements` or `make upgrade-package PKG=<name>`.
        """
        pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text())
        minimum = re.search(r">=\s*(\d+\.\d+)", pyproject["project"]["requires-python"])
        assert minimum, "requires-python in pyproject.toml must declare a minimum version"

        lock = (ROOT / "requirements.txt").read_text()
        command = next((line for line in lock.splitlines() if "pip compile" in line), "").split()

        assert "--universal" in command, "requirements.txt must be compiled with --universal"
        assert "--python-version" in command, "requirements.txt must be compiled with --python-version"
        assert command[command.index("--python-version") + 1] == minimum.group(1)
