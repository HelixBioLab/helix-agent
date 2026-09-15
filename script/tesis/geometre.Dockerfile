FROM python:3.11.11-slim-bookworm@sha256:081075da77b2b55c23c088251026fb69a7b2bf92471e491ff5fd75c192fd38e5
ENV OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 PYTHONUNBUFFERED=1
COPY . /opt/geometre
RUN python -m pip install --no-cache-dir \
    numpy==2.2.2 pandas==2.2.3 scipy==1.15.0 scikit-learn==1.6.0 \
    biopython==1.84 tmtools==0.2.0 scikit-image==0.25.0 requests==2.32.3 \
    certifi==2026.7.22 charset-normalizer==3.5.1 cloudpickle==3.1.2 \
    idna==3.19 ImageIO==2.37.4 joblib==1.6.0 lazy-loader==0.5 networkx==3.6.1 \
    packaging==26.3 pillow==12.3.0 python-dateutil==2.9.0.post0 pytz==2026.3.post1 \
    six==1.17.0 threadpoolctl==3.6.0 tifffile==2026.3.3 tzdata==2026.4 urllib3==2.7.0 \
    /opt/geometre \
    && python -m pip freeze > /opt/geometre-freeze.txt
WORKDIR /work
ENTRYPOINT ["geometre"]
