# Referencia Nextflow F5

Entrada 2xqh/A y doce unidades suministradas; mismo caso de desarrollo que F2–F4. Motor `trp-nextflow/1.2.0`, Nextflow 25.10.4, misma imagen GeomeTRe identificada por digest. Dos tareas simuladas y dos reales, CSV idéntico al archivado en F2. La aprobación es una respuesta sintética de un controlador de pruebas, no evidencia de intervención humana.

Se incorporan reporte estructural, catálogo y programa al contenido aprobado, los métodos y la copia completa. **127 archivos** declarados, manifiesto SHA-256 `245f11b45f74c601fab81e0096357b1dbecebe83cd1c4519b10ac29d762fed16`. La auditoría detectó 262/262 alteraciones, ausencias y otros fallos de integridad.

Verificación sin modelo, Docker ni red:

```bash
python3 evaluation/trp/reference/nextflow-f5/evidence/verify.py evaluation/trp/reference/nextflow-f5/evidence --sha256 245f11b45f74c601fab81e0096357b1dbecebe83cd1c4519b10ac29d762fed16
```

R3.2 sigue usando una estimación de disco; no se afirma cuota agregada ni reserva efectiva del controlador. Los controles estructurales no establecen validez biológica. La evidencia no sustituye las métricas reservadas de F6. [Auditoría](../../../../docs/tesis/evidencia/portable-audit-fase5.json).
