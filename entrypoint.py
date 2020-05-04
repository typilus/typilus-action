#!/bin/python
import os
from glob import iglob
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from typing import Tuple, NamedTuple, List

from dpu_utils.utils import load_jsonl_gz

from changeutils import get_changed_files
from graph_generator.type_lattice_generator import TypeLatticeGenerator
from graph_generator.extract_graphs import extract_graphs, Monitoring


class TypeSuggestion(NamedTuple):
    filepath: str
    name: str
    location: Tuple[int, int]
    suggestion: str
    confidence: float


# TODO: Get these variables from the environment
repo_path = "."

print('ENV Variables')
for env_name, env_value in os.environ.items():
    print(f'{env_name} --> {env_value}')

changed_files = get_changed_files(Path(repo_path), os.environ['GITHUB_BASE_REF'], os.environ['GITHUB_HEAD_REF'])
if len(changed_files) == 0:
    sys.exit(0)

monitoring = Monitoring()

with TemporaryDirectory() as out_dir:
    typing_rules_path = os.path.join(
        os.path.dirname(__file__), "src", "metadata", "typingRules.json"
    )
    extract_graphs(
        repo_path,
        typing_rules_path,
        files_to_extract=set(changed_files),
        target_folder=out_dir,
    )

    # TODO: Get suggestions from Typilus!
    # TODO: Dummy code below
    type_suggestions: List[TypeSuggestion] = []
    for datafile_path in iglob(os.path.join(out_dir, "*.jsonl.gz")):
        for graph in load_jsonl_gz(datafile_path):
            filepath = graph["filename"]
            assert filepath not in changed_files

            for _, node_data in graph["supernodes"].items():
                if node_data["type"] == "variable":
                    continue  # Do not suggest annotations on variables.
                lineno, colno = node_data["location"]
                if (
                    lineno in changed_files[filepath]
                    and node_data["annotation"] is None
                ):
                    type_suggestions.append(
                        TypeSuggestion(
                            filepath, node_data["name"], (lineno, colno), "DummyType", 1
                        )
                    )

    # Add PR comments
    for suggestion in type_suggestions:
        print(suggestion)
