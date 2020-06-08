# CORD-19 Citation Graph Generator

Simple python script that extracts citation graphs of COVID-19 publications from the CORD-19 open research dataset.

Last updated for CORD-19 release 6/2/2020.

This graph is included as a sample graph in [Argo Lite](https://github.com/poloclub/argo-graph-lite).

Since the CORD-19 dataset has updated schema and introduced breaking changes, the code for one release of the dataset might not work for another. Please check the CORD-19 change log.

## Setup

Download the CORD-19 dataset. Unzip and organize into the following directory structure (relative to `generate.py` at the root repository folder).

```
generate.py
cord-2020-06-02/
    metadata.csv
    document_parses/
        pdf_json/*
        pmc_json/*

```

You can name the dataset folder (`cord-2020-06-02` above for illustration) to whatever you want, just remember to change the paths in the code.
