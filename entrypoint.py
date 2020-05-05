#!/bin/python
import os
from glob import iglob
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from typing import Tuple, NamedTuple, List

from github import Github
import requests
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


assert os.environ["GITHUB_EVENT_NAME"] == "pull_request"

with open(os.environ["GITHUB_EVENT_PATH"]) as f:
    print("Event data:")
    event_data = json.load(f)
    print(json.dumps(event_data, indent=3))

repo_path = "."  # TODO: Is this always true?

print("ENV Variables")
for env_name, env_value in os.environ.items():
    print(f"{env_name} --> {env_value}")

changed_files = get_changed_files(
    Path(repo_path),
    "origin/" + os.environ["GITHUB_HEAD_REF"],
    "origin/" + os.environ["GITHUB_BASE_REF"],
)
if len(changed_files) == 0:
    print("No changes found.")
    sys.exit(0)

print("Changed files: ", list(changed_files))

monitoring = Monitoring()

with TemporaryDirectory() as out_dir:
    typing_rules_path = os.path.join(
        os.path.dirname(__file__), "metadata", "typingRules.json"
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
    print("# Suggestions:", len(type_suggestions))
    for suggestion in type_suggestions:
        print(suggestion)

    github_token = os.environ["GITHUB_TOKEN"]

    print("Diff URL:", event_data["pull_request"]["url"])
    r = requests.get(
        event_data["pull_request"]["url"],
        headers={
            "authorization": f"Bearer {github_token}",
            "Accept": "application/vnd.github.v3.diff",
        },
    )
    print("Status Code: ", r.status_code)
    print(r.text)
    g = Github(github_token)
    repo = g.get_repo(os.environ["GITHUB_REPOSITORY"])
