import re
from typing import Dict, Set, List, NamedTuple


HUNK_MATCH = re.compile("^@@ -\d+,\d+ \+(\d+),\d+ @@")


def get_line_ranges_of_interest(diff_lines: List[str]) -> Set[int]:
    lines_of_interest = set()
    current_line = 0
    for line in diff_lines:
        if hunk_start_match := HUNK_MATCH.match(line):
            current_line = int(hunk_start_match.group(1))
        elif line.startswith("+"):
            lines_of_interest.add(current_line)
            current_line += 1
        elif not line.startswith("-"):
            current_line += 1
        elif line.startswith("\\"):
            assert False, "When does this happen?"

    return lines_of_interest


def get_changed_files(diff: str, suffix=".py") -> Dict[str, Set[int]]:
    per_file_diff = diff.split("diff --git ")
    changed_files: Dict[str, Set[int]] = {}
    for file_diff in per_file_diff:
        if len(file_diff) == 0:
            continue
        file_diff_lines = file_diff.splitlines()

        if file_diff_lines[1].startswith("deleted"):
            continue
        elif file_diff_lines[1].startswith("new file"):
            assert file_diff_lines[2].startswith("index")
            assert file_diff_lines[3].startswith("---")
            assert file_diff_lines[4].startswith("+++ b/")
            target_filepath = file_diff_lines[4][len("+++ b") :]
            remaining_lines = file_diff_lines[5:]
        elif file_diff_lines[1].startswith("index"):
            assert file_diff_lines[2].startswith("--- a/")
            assert file_diff_lines[3].startswith("+++ b/")
            target_filepath = file_diff_lines[3][len("+++ b") :]
            remaining_lines = file_diff_lines[4:]
        elif file_diff_lines[1].startswith("similarity"):
            assert file_diff_lines[2].startswith("rename")
            assert file_diff_lines[3].startswith("rename")
            assert file_diff_lines[4].startswith("index")
            assert file_diff_lines[5].startswith("--- a/")
            assert file_diff_lines[6].startswith("+++ b/")
            target_filepath = file_diff_lines[6][len("+++ b") :]
            remaining_lines = file_diff_lines[7:]
        else:
            raise Exception(file_diff)

        if target_filepath.endswith(suffix):
            assert target_filepath not in changed_files
            changed_files[target_filepath] = get_line_ranges_of_interest(remaining_lines)

    return changed_files
