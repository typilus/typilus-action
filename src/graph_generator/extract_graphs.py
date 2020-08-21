from typing import Tuple, List, Optional, Set, Iterator
from dpu_utils.utils import save_jsonl_gz, run_and_debug, ChunkWriter
import traceback
import os
from glob import iglob

from docopt import docopt
import time

from .graphgenerator import AstGraphGenerator
from .type_lattice_generator import TypeLatticeGenerator
from .typeparsing import FaultyAnnotation


class Monitoring:
    def __init__(self):
        self.count = 0  # type: int
        self.errors = []
        self.file = ""  # type: str
        self.current_repo = ""
        self.empty_files = []

    def increment_count(self) -> None:
        self.count += 1

    def found_error(self, err, trace) -> None:
        self.errors.append([self.file, err, trace])

    def enter_file(self, filename: str) -> None:
        self.file = filename

    def enter_repo(self, repo_name: str) -> None:
        self.current_repo = repo_name


def build_graph(
    source_code, monitoring: Monitoring, type_lattice: TypeLatticeGenerator
) -> Tuple[Optional[List], Optional[List]]:
    """
    Parses the code of a file into a custom abstract syntax tree.
    """
    try:
        visitor = AstGraphGenerator(source_code, type_lattice)
        return visitor.build()
    except FaultyAnnotation as e:
        print("Faulty Annotation: ", e)
        print("at file: ", monitoring.file)
    except SyntaxError as e:
        monitoring.found_error(e, traceback.format_exc())
    except Exception as e:
        print(traceback.format_exc())
        monitoring.found_error(e, traceback.format_exc())


def explore_files(
    root_dir: str,
    files_to_extract: Set[str],
    monitoring: Monitoring,
    type_lattice: TypeLatticeGenerator,
) -> Iterator[Tuple]:
    """
    Walks through the root_dir and process each file.
    """
    for file_path in iglob(os.path.join(root_dir, "**", "*.py"), recursive=True):
        if not os.path.isfile(file_path):
            continue
        with open(file_path, encoding="utf-8", errors="ignore") as f:
            # import pdb; pdb.set_trace()
            if file_path[len(root_dir) :] not in files_to_extract:
                continue

            monitoring.increment_count()
            monitoring.enter_file(file_path)

            graph = build_graph(f.read(), monitoring, type_lattice)
            if graph is None or len(graph["supernodes"]) == 0:
                continue
            graph["filename"] = file_path[len(root_dir) :]
            yield graph
    type_lattice.build_graph()


def extract_graphs(root_dir, typing_rules_path, files_to_extract: Set[str], target_folder):
    start_time = time.time()
    print("Traversing folders ...")
    monitoring = Monitoring()
    type_lattice = TypeLatticeGenerator(typing_rules_path)

    # Extract graphs
    outputs = explore_files(root_dir, files_to_extract, monitoring, type_lattice)

    # Save results
    with ChunkWriter(
        out_folder=target_folder,
        file_prefix="all-graphs",
        max_chunk_size=5000,
        file_suffix=".jsonl.gz",
    ) as writer:
        for graph in outputs:
            writer.add(graph)

    print("Building and saving the type graph...")
    type_lattice.build_graph()
    save_jsonl_gz(
        [type_lattice.return_json()], os.path.join(target_folder, "_type_lattice.json.gz"),
    )

    print("Done.")
    print(
        "Generated %d graphs out of %d snippets"
        % (monitoring.count - len(monitoring.errors), monitoring.count)
    )

    with open(os.path.join(target_folder, "logs_graph_generator.txt"), "w") as f:
        for item in monitoring.errors:
            try:
                f.write("%s\n" % item)
            except:
                pass

    print("\nGraph Execution in: ", time.time() - start_time, " seconds")


if __name__ == "__main__":
    args = docopt(__doc__)
    run_and_debug(lambda: main(args), args["--debug"])
