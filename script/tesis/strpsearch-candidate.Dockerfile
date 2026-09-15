# Reconstruction probe, not an admitted or frozen scientific environment.
# Source: BioComputingUP/STRPsearch ed325a7f6b77578ee96753f31dbdcfda4931cca8.
# Upstream Dockerfile points PATH at a different environment than environment.yml.
FROM condaforge/miniforge3:latest
COPY . /app
WORKDIR /app
RUN conda env create -f environment.yml && conda clean -afy
ENV PATH=/opt/conda/envs/strpsearch_env_ch_before/bin:$PATH MPLBACKEND=Agg
RUN python -c "import zipfile; zipfile.ZipFile('data/databases.zip').extractall('data')"
ENTRYPOINT ["python", "/app/bin/strpsearch.py"]
