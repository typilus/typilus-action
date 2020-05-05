import re
from typing import Dict, Set, List, NamedTuple


class Edit(NamedTuple):
    file_line_no: int
    diff_line_no: int


HUNK_MATCH = re.compile("^@@ -\d+,\d+ \+(\d+),\d+ @@")


def get_line_ranges_of_interest(diff_lines: List[str], diff_line_no: int) -> Set[Edit]:
    lines_of_interest = set()
    current_line = 0
    for line in diff_lines:
        diff_line_no += 1
        hunk_start_match = HUNK_MATCH.match(line)
        if hunk_start_match:
            current_line = int(hunk_start_match.group(1))
        elif line.startswith("+"):
            lines_of_interest.add(Edit(current_line, diff_line_no))
            current_line += 1
        elif not line.startswith("-"):
            current_line += 1
        elif line.startswith("\\"):
            assert False, "When does this happen?"

    return lines_of_interest


def get_changed_files(diff: str, suffix=".py") -> Dict[str, Set[Edit]]:
    diff_line_no = 0
    per_file_diff = diff.split("diff --git ")
    changed_files: Dict[str, Set[int]] = {}
    for file_diff in per_file_diff:
        if len(file_diff) == 0:
            continue
        file_diff_lines = file_diff.splitlines()

        assert file_diff_lines[1].startswith("index")
        assert file_diff_lines[2].startswith("--- a/")
        assert file_diff_lines[3].startswith("+++ b/")
        target_filepath = file_diff_lines[3][len("+++ b") :]

        if target_filepath.endswith(suffix):
            assert target_filepath not in changed_files
            changed_files[target_filepath] = get_line_ranges_of_interest(
                file_diff_lines[4:], diff_line_no + 4
            )

        diff_line_no += len(file_diff_lines)

    return changed_files
