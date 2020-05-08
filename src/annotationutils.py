from pathlib import Path
from typing import Tuple


def annotate_parameter(
    filepath: Path, location: Tuple[int, int], param_name: str, annotation: str
) -> str:
    """
    Annotate a single parameter. TODO: Allow annotating multiple parameters
    """
    with open(filepath) as f:
        lines = f.readlines()
    target_line = lines[location[0] - 1]
    assert target_line[location[1] :].startswith(param_name)
    return (
        target_line[: location[1] + len(param_name)]
        + f": {annotation}"
        + target_line[location[1] + len(param_name) :]
    )
