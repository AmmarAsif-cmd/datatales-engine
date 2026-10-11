# Generated sources

One YAML file per dataset added from the backlog by the weekly new-dataset step
(`python -m datatales add-datasets`, run by `.github/workflows/pipeline.yml`). Same format as
a `sources.yaml` entry. The `detect` block is added when you approve the source's recipe.

Hand-edit a file only to fix it; delete it (and reject the backlog item) to drop a source.
