# Typilus: Suggest Python Type Annotations

A GitHub action that suggests type annotations for Python using machine learning.

This action makes suggestions within each pull request as
[suggested edits](https://help.github.com/en/github/collaborating-with-issues-and-pull-requests/incorporating-feedback-in-your-pull-request#applying-a-suggested-change).
You can then directly apply these suggestions to your code or ignore them.

> TODO: Add a screenshot of an edit suggestion.

***What are Python type annotations?***
Introduced in Python 3.5, [type hints](https://www.python.org/dev/peps/pep-0484/)
(more traditionally called type annotations) allow users
to annotate their code with the expected types. These annotations are
optionally checked by external tools, such as [mypy](http://www.mypy-lang.org/) and [pyright](https://github.com/Microsoft/pyright),
to prevent type errors; they also facilitate code comprehension and navigation.
The [`typing`](https://docs.python.org/3/library/typing.html) module
provides the core types.

***Why use machine learning?***
Given the dynamic nature of Python, type inference is challenging,
especially over partial contexts. To tackle this challenge, we use a graph neural
network model that predicts types by probabilistically reasoning over
a program’s structure, names, and patterns. This allows us to make
suggestions with only a partial context, at the cost of suggesting some false
positives.


### Install Action in your Repository

To use the GitHub action, create a workflow file. For example,
```yaml
name: Typilus Type Annotation Suggestions

# Controls when the action will run. Triggers the workflow on push or pull request
# events but only for the master branch
on:
  pull_request:
    branches: [ master ]

jobs:
  suggest:
    # The type of runner that the job will run on
    runs-on: ubuntu-latest

    # Checks-out your repository under $GITHUB_WORKSPACE, so that typilus can access it.
    - uses: actions/checkout@v2
    - run: echo ${{ secrets.GITHUB_TOKEN }} | docker login docker.pkg.github.com -u ${{ github.actor }} --password-stdin  # Allow pulling Typilus container. Requires login.
    - uses: typilus/typilus-action@master
      env:
        GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        MODEL_PATH: path/to/model.pkl.gz   # Optional: provide the path of a custom model instead of the pre-trained model.
        SUGGESTION_CONFIDENCE_THRESHOLD: 0.8   # Configure this to limit the confidence of suggestions on un-annotated locations. A float in [0, 1]. Default 0.8
        DISAGREEMENT_CONFIDENCE_THRESHOLD: 0.95  # Configure this to limit the confidence of suggestions on annotated locations.  A float in [0, 1]. Default 0.95
```
The action uses the `GITHUB_TOKEN` to retrieve the diff of the pull request
and to post comments on the analyzed pull request.



#### Technical Details & Internals
This GitHub action is a reimplementation of the Graph2Class model of
[Allamanis _et al._ PLDI 2020](https://arxiv.org/abs/2004.10657) using the
[`ptgnn`](https://github.com/microsoft/ptgnn/) library. Internally, it
uses a Graph Neural Network to predict likely type annotations for Python
code.

This action uses a pre-trained neural network that has been trained on
a corpus of open-source repositories that use Python's type annotations.
At this point we do _not_ support online adaptation of the model to each project.


##### Training your own model
You may wish to train your own model and use it in this action. To
do so, please follow the steps in [`ptgnn`](https://github.com/microsoft/ptgnn/).
Then provide a path to the model in your GitHub action configuration, through the
`MODEL_PATH` environment variable.


## Contributing
We welcome external contributions and ideas. Please look at the issues in the repository
for ideas and improvements.
