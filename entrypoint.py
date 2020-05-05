#!/bin/python
import os
from glob import iglob
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from typing import Tuple, NamedTuple, List

import requests
from dpu_utils.utils import load_jsonl_gz

from changeutils import get_changed_files
from graph_generator.extract_graphs import extract_graphs, Monitoring



class TypeSuggestion(NamedTuple):
    filepath: str
    name: str
    file_location: Tuple[int, int]
    diff_location: int
    suggestion: str
    confidence: float


assert os.environ["GITHUB_EVENT_NAME"] == "pull_request"
github_token = os.environ["GITHUB_TOKEN"]

with open(os.environ["GITHUB_EVENT_PATH"]) as f:
    print("Event data:")
    event_data = json.load(f)
    print(json.dumps(event_data, indent=3))

repo_path = "."  # TODO: Is this always true?

print("ENV Variables")
for env_name, env_value in os.environ.items():
    print(f"{env_name} --> {env_value}")

print("Diff URL:", event_data["pull_request"]["url"])
r = requests.get(
    event_data["pull_request"]["url"],
    headers={
        "authorization": f"Bearer {github_token}",
        "Accept": "application/vnd.github.v3.diff",
    },
)
print("Diff GET Status Code: ", r.status_code)
print(r.text)

changed_files = get_changed_files(r.text)
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
        print(f'Looking into {datafile_path}...')
        for graph in load_jsonl_gz(datafile_path):
            filepath = graph["filename"]
            print(f'Reading graph for {filepath}.')

            for _, node_data in graph["supernodes"].items():
                if node_data["type"] == "variable":
                    continue  # Do not suggest annotations on variables.
                lineno, colno = node_data["location"]
                if (
                    any(lineno == e.file_line_no for e in changed_files[filepath])
                    and node_data["annotation"] is None
                ):
                    diff_location = [
                        e for e in changed_files[filepath] if lineno == e.file_line_no
                    ][0].diff_line_no
                    type_suggestions.append(
                        TypeSuggestion(
                            filepath,
                            node_data["name"],
                            (lineno, colno),
                            diff_location,
                            "DummyType",
                            1,
                        )
                    )

    # Add PR comments
    print("# Suggestions:", len(type_suggestions))
    for suggestion in type_suggestions:
        print(suggestion)

    comment_url = event_data["pull_request"]["review_comments_url"]
    print('URL: ', comment_url)
    commit_id = event_data["pull_request"]["head"]["sha"]
    for suggestion in type_suggestions:
        data = {
            "path": suggestion.filepath[1:],  # No slash in the beginning
            "line": suggestion.file_location[0],
            "side": "RIGHT",
            "commit_id": commit_id,
            "body": f"What about annotating `{suggestion.name}` with the type `{suggestion.suggestion}`?"
        }
        headers={
            "authorization": f"Bearer {github_token}",
            "Accept": "application/vnd.github.v3.raw+json",
         }
        r = requests.post(comment_url, data=json.dumps(data), headers=headers)
        print(f"Data: {data}. Status Code: {r.status_code}. Text: {r.text}")

