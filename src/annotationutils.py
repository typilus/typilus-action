from pathlib import Path
from typing import Tuple
import re
from itertools import groupby


def find_suggestion_for_return(suggestions):
    return next(
        (s for s in suggestions if s.symbol_kind == "class-or-function"), None
    )


def annotate_line(line, suggestions):
    para_suggestions = sorted(
        (s for s in suggestions if s.symbol_kind == "parameter"), key=lambda x: x.file_location[1]
    )
    annotated_line = annotate_parameters(line, para_suggestions)

    ret_suggestion = find_suggestion_for_return(suggestions)
    if ret_suggestion is not None:
        annotated_line = annotate_return(annotated_line, ret_suggestion)

    return annotated_line


def insert_at(original, inserted, idx):
    return original[:idx] + inserted + original[idx:]


def annotate_parameters(line, suggestions):
    """
    Annotate the parameters of a function on a particular line
    """
    annotated_line = f" {line}"
    length_increase = 0
    for s in suggestions:
        assert line[s.file_location[1] :].startswith(s.name)
        insertion_position = s.file_location[1] + len(s.name) + 1 + length_increase
        annotated_line = insert_at(annotated_line, f": {s.suggestion}", insertion_position)
        length_increase += len(s.suggestion) + 2
    return annotated_line


def annotate_return(line, suggestion):
    """
    Annotate the return of a function
    """
    assert line.rstrip().endswith(":")
    return f"{line.rstrip()[:-1]} -> {suggestion.suggestion}" + ":\n"


def find_annotation_line(filepath, location, func_name):
    with open(filepath) as f:
        lines = f.readlines()

    assert func_name in lines[location[0] - 1]

    # Assume that the function's return is *not* already annotated.
    func_def_end = re.compile(r"\)\s*:$")

    annotation_lineno = location[0]
    while annotation_lineno <= len(lines):
        if func_def_end.search(lines[annotation_lineno - 1].rstrip()) is not None:
            break
        annotation_lineno += 1
    else:
        raise Exception("Cannot find the closing brace for the parameter list.")

    return annotation_lineno


def group_suggestions(suggestions):
    def key(s):
        return s.filepath + str(s.annotation_lineno)

    sorted_suggestions = sorted(suggestions, key=key)
    return [list(it) for k, it in groupby(sorted_suggestions, key)]


ALIASES = {"typing.Text": "str"}


def annotation_rewrite(annotation: str) -> str:
    for k, v in ALIASES.items():
        annotation = annotation.replace(k, v)
    return annotation
