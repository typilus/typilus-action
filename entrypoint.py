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
from annotationutils import annotate_parameter
from graph_generator.extract_graphs import extract_graphs, Monitoring


class TypeSuggestion(NamedTuple):
    filepath: str
    name: str
    file_location: Tuple[int, int]
    suggestion: str
    confidence: float


assert os.environ["GITHUB_EVENT_NAME"] == "pull_request"
github_token = os.environ["GITHUB_TOKEN"]
debug = False

with open(os.environ["GITHUB_EVENT_PATH"]) as f:
    print("Event data:")
    event_data = json.load(f)
    print(json.dumps(event_data, indent=3))

repo_path = "."  # TODO: Is this always true?

if debug:
    print("ENV Variables")
    for env_name, env_value in os.environ.items():
        print(f"{env_name} --> {env_value}")

diff_rq = requests.get(
    event_data["pull_request"]["url"],
    headers={
        "authorization": f"Bearer {github_token}",
        "Accept": "application/vnd.github.v3.diff",
    },
)
print("Diff GET Status Code: ", diff_rq.status_code)
if debug:
    print(diff_rq.text)

changed_files = get_changed_files(diff_rq.text)
if len(changed_files) == 0:
    print("No changes found.")
    sys.exit(0)

if debug:
    print("Changed files: ", list(changed_files))

monitoring = Monitoring()

with TemporaryDirectory() as out_dir:
    typing_rules_path = os.path.join(os.path.dirname(__file__), "metadata", "typingRules.json")
    extract_graphs(
        repo_path, typing_rules_path, files_to_extract=set(changed_files), target_folder=out_dir,
    )

    # TODO: Get suggestions from Typilus!
    # TODO: Dummy code below
    type_suggestions: List[TypeSuggestion] = []
    for datafile_path in iglob(os.path.join(out_dir, "*.jsonl.gz")):
        print(f"Looking into {datafile_path}...")
        for graph in load_jsonl_gz(datafile_path):
            filepath = graph["filename"]
            print(f"Reading graph for {filepath}.")

            for _, node_data in graph["supernodes"].items():
                if node_data["type"] != "parameter":
                    continue  # Do not suggest annotations on non-params for now.
                lineno, colno = node_data["location"]
                if lineno in changed_files[filepath] and node_data["annotation"] is None:
                    type_suggestions.append(
                        TypeSuggestion(
                            filepath, node_data["name"], (lineno, colno), "DummyTypeTODO", 1,
                        )
                    )

    # Add PR comments
    if debug:
        print("# Suggestions:", len(type_suggestions))
        for suggestion in type_suggestions:
            print(suggestion)

    comment_url = event_data["pull_request"]["review_comments_url"]
    commit_id = event_data["pull_request"]["head"]["sha"]
    for suggestion in type_suggestions:
        data = {
            "path": suggestion.filepath[1:],  # No slash in the beginning
            "line": suggestion.file_location[0],
            "side": "RIGHT",
            "commit_id": commit_id,
            "body": "The following type annotation might be useful:\n ```suggestion\n"
            f"{annotate_parameter(suggestion.filepath[1:],suggestion.file_location,suggestion.name,suggestion.suggestion)}\n```\n",
        }
        headers = {
            "authorization": f"Bearer {github_token}",
            "Accept": "application/vnd.github.v3.raw+json",
        }
        r = requests.post(comment_url, data=json.dumps(data), headers=headers)
        if debug:
            print("URL: ", comment_url)
            print(f"Data: {data}. Status Code: {r.status_code}. Text: {r.text}")
