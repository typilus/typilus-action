from collections import defaultdict
from pathlib import Path
import re
from typing import Dict, Set, Tuple, Optional

from git import Repo


HUNK_MATCH = re.compile("^@@ -\d+,\d+ \+(\d+),\d+ @@")


def get_line_ranges_of_interest(diff: str) -> Set[int]:
    lines_of_interest = set()
    current_line = 0
    for line in diff.splitlines():
        hunk_start_match = HUNK_MATCH.match(line)
        if hunk_start_match:
            current_line = int(hunk_start_match.group(1))
        elif line.startswith("+"):
            lines_of_interest.add(current_line)
            current_line += 1
        elif not line.startswith("-"):
            current_line += 1
        elif line.startswith("\\"):
            assert False, "When does this happen?"

    return lines_of_interest


def get_changed_files(
    repo_path: Path, base_ref: str, head_ref: str, suffix: str = ".py"
) -> Dict[str, Set[int]]:
    repo = Repo(repo_path)
    assert not repo.bare

    diffs = repo.commit(head_ref).diff(
        repo.commit(base_ref).hexsha,
        create_patch=True,
        ignore_blank_lines=True,
        ignore_space_at_eol=True,
    )
    changed_files: Dict[str, Set[int]] = {}
    for diff in diffs:
        if diff.b_path is not None and diff.b_path.endswith(suffix):
            assert diff.b_path not in changed_files
            changed_files[diff.b_path] = get_line_ranges_of_interest(diff.diff.decode())

    return changed_files
