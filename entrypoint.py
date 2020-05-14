#!/bin/python
import os
from glob import iglob
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from typing import Tuple, List

import requests
from dpu_utils.utils import load_jsonl_gz
from ptgnn.implementations.typilus.graph2class import Graph2Class

from changeutils import get_changed_files
from annotationutils import annotate_line, find_annotation_line, group_suggestions
from graph_generator.extract_graphs import extract_graphs, Monitoring


class TypeSuggestion:
    def __init__(
        self,
        filepath: str,
        name: str,
        file_location: Tuple[int, int],
        suggestion: str,
        symbol_kind: str,
        confidence: float,
        annotation_lineno: int = 0,
    ):
        self.filepath = filepath
        self.name = name
        self.file_location = file_location
        self.suggestion = suggestion
        self.symbol_kind = symbol_kind
        self.confidence = confidence
        self.annotation_lineno = annotation_lineno


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

    def data_iter():
        for datafile_path in iglob(os.path.join(out_dir, "*.jsonl.gz")):
            print(f"Looking into {datafile_path}...")
            for graph in load_jsonl_gz(datafile_path):
                filepath = graph["filename"]
                yield graph

    model_path = os.getenv("MODEL_PATH", "/usr/src/model.pkl.gz")
    model, nn = Graph2Class.restore_model(model_path, "cpu")

    type_suggestions: List[TypeSuggestion] = []
    for graph, predictions in model.predict(data_iter(), nn, "cpu"):
        # predictions has the type: Dict[int, Tuple[str, float]]
        filepath = graph["filename"]
        print(f"Suggestions for graph {filepath}: {predictions}")
        print(f"Supernodes: {graph['supernodes']}")
        for supernode_idx, (predicted_type, predicted_prob) in predictions.items():
            supernode_data = graph["supernodes"][str(supernode_idx)]
            if supernode_data["type"] == "variable":
                continue  # Do not suggest annotations on variables for now.
            lineno, colno = supernode_data["location"]
            suggestion = TypeSuggestion(
                filepath,
                supernode_data["name"],
                (lineno, colno),
                predicted_type,
                supernode_data["type"],
                predicted_prob,
            )
            # TODO: Add confidence filtering!
            # TODO: Add very confident disagreements
            if lineno in changed_files[filepath] and supernode_data["annotation"] == "??":
                type_suggestions.append(suggestion)

    # Add PR comments
    if debug:
        print("# Suggestions:", len(type_suggestions))
        for suggestion in type_suggestions:
            print(suggestion)

    confidence_threshold = float(os.getenv("CONFIDENCE_THRESHOLD", 0.0))
    print(f"Confidence Threshold: {confidence_threshold:.2%}")

    comment_url = event_data["pull_request"]["review_comments_url"]
    commit_id = event_data["pull_request"]["head"]["sha"]

    for suggestion in type_suggestions:
        if suggestion.symbol_kind == "class-or-function":
            suggestion.annotation_lineno = find_annotation_line(
                suggestion.filepath, suggestion.file_location, suggestion.name
            )
        else:  # when the underlying symbol is a parameter
            suggestion.annotation_lineno = suggestion.file_location[0]

    # Group type suggestions by (filepath + lineno)
    grouped_suggestions = group_suggestions(type_suggestions)

    for same_line_suggestions in grouped_suggestions:
        suggestion = same_line_suggestions[0]
        path = suggestion.filepath[1:]  # No slash in the beginning
        annotation_lineno = suggestion.annotation_lineno
        with open(path) as file:
            target_line = file.readlines()[annotation_lineno - 1]
        data = {
            "path": path,
            "line": annotation_lineno,
            "side": "RIGHT",
            "commit_id": commit_id,
            "body": "The following type annotation might be useful:\n ```suggestion\n"
            f"{annotate_line(target_line, same_line_suggestions)}```\n"
            f"(prediction probability {suggestion.confidence:.1%})",
        }
        headers = {
            "authorization": f"Bearer {github_token}",
            "Accept": "application/vnd.github.v3.raw+json",
        }
        r = requests.post(comment_url, data=json.dumps(data), headers=headers)
        if debug:
            print("URL: ", comment_url)
            print(f"Data: {data}. Status Code: {r.status_code}. Text: {r.text}")
