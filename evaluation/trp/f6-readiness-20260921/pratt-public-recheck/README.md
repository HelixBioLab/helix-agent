# Recuperabilidad pública de Pratt et al.

Reconsulta: 21-09-2026, hora de Lima (22-09-2026 UTC). DOI: 10.1016/j.csbj.2025.01.016.
`retrieval.json` registra URL, hora, estado HTTP, bytes y SHA-256 de cada respuesta.

Se consultaron el XML de Europe PMC, la entrada BioStudies S-EPMC11795689 y el
registro institucional de Liverpool 3190290. El XML vuelve a identificar dos
suplementos, `mmc1.docx` y `mmc2.xlsx`, sin un enlace de depósito de modelos
originales/PAE. El registro de Liverpool remite al DOI, sin archivos estructurales.

**Se detectó una discrepancia de procedencia en BioStudies.** Aunque su metadato
identifica correctamente el artículo, los archivos descargados bajo esos nombres
contienen un suplemento de cáncer pulmonar y una tabla eQTL, respectivamente.
Sus tamaños y hashes difieren de los suplementos Pratt previamente recuperados.
Se rechazaron ambos como evidencia del estudio. Se conservan hashes, tamaños y
extractos breves identificadores en `retrieval.json`; no se conservan los binarios
ajenos. No se atribuye una causa al error del servicio.

Las búsquedas públicas adicionales por título/DOI y términos GitHub, Zenodo,
Figshare y repositorio Liverpool no localizaron un depósito inequívoco de los
modelos publicados. Esto **no demuestra inexistencia de archivos en manos de los
autores o en un depósito no encontrado**.

Los 78 registros de la hoja Pratt ya auditada continúan siendo metadatos, sin
coordenadas/PAE originales recuperados ni etiquetas independientes de fallo.
No se calculan sensibilidad ni especificidad. Una predicción nueva no sustituye
la salida original publicada. No se enviaron mensajes a autores.

Fuentes primarias consultadas:

- https://www.ebi.ac.uk/europepmc/webservices/rest/PMC11795689/fullTextXML
- https://www.ebi.ac.uk/biostudies/api/v1/studies/S-EPMC11795689
- https://livrepository.liverpool.ac.uk/3190290/
- https://spj.science.org/doi/10.1016/j.csbj.2025.01.016

La auditoría anterior permanece en
`evaluation/trp/reference/structural-f5/pratt/recoverability.json`.
