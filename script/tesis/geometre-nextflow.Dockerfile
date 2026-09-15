# Recorded local parent: sha256:c10ef2d44297822270231bd26ac1ed0ab1b951525247bb6363de50057946fac2.
# GeomeTRe and all scientific dependencies remain those of the F2 reference.
FROM tesis/geometre:1.0-frozen
RUN apt-get update \
    && apt-get install --no-install-recommends -y procps=2:4.0.2-3 \
    && dpkg-query -W > /opt/os-packages.txt \
    && rm -rf /var/lib/apt/lists/*
