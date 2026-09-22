# Preparación de la evaluación F6 — 21 de septiembre de 2026

Se implementó un control de preparación por campaña. No ejecuta llamadas pagadas,
no crea etiquetas externas y no cambia los umbrales del protocolo 1.0.0.

```bash
python3 -m unittest discover -s script/tesis -p test_f6_readiness.py -v
python3 script/tesis/check_f6_readiness.py --output /tmp/f6-readiness.json
```

La segunda orden devuelve **2** cuando quedan dependencias pendientes (comportamiento
esperado con `freeze.template.json`) y **0** cuando los metadatos y bytes requeridos
están completos. `readiness.json` conserva la ejecución real de esta auditoría sobre
el commit indicado y el árbol en edición; no es una campaña ni una congelación final.

El control acepta `--scope graphs`, `resources`, `language`, `trace` o `structural`
(se pueden repetir). El modelo y presupuesto son exigibles para `language`; el
anotador para `language`, `trace` y `structural`. `--cluster` exige acceso confirmado
solo cuando se pretende afirmar ejecución en clúster. Los ensayos de desarrollo
locales o en la segunda computadora pueden continuar aunque este control falle.

Para una campaña preparada, pasar `--freeze ruta/freeze.json --artifacts ruta/artifacts.json`.
`artifacts.json` relaciona cada campo de hash con un archivo real, mediante rutas
absolutas o relativas al repositorio. Ejemplo de una entrada:

```json
{"protocol_sha256": "evaluation/trp/protocol.json"}
```

El comprobador verifica igualdad del commit, árbol limpio, versión de protocolo,
semillas, valores explícitos de configuración y SHA-256 de los artefactos. Admite
`unsupported` para temperatura/top-p cuando el proveedor no los expone; no inventa
un valor predeterminado. La ausencia explícita de soporte de semilla (`false`) es
válida. Los identificadores de modelo y revisión deben provenir del proveedor.

Se requieren algunos campos de evidencia adicionales a la plantilla histórica:

- `<scope>_corpus_review_sha256`: revisión registrada del corpus de esa campaña,
  con mínimos del protocolo, separación de familias respecto del desarrollo,
  asignaciones, referencias, fuentes y elegibilidad.
- `annotation_agreement_sha256`: acuerdo y registro del participante independiente,
  para campañas que lo necesitan.
- `original_structural_inputs_sha256` e `independent_reference_review_sha256`:
  manifiesto de entradas originales y revisión del patrón de referencia estructural.

Estos campos documentan condiciones ya descritas en el protocolo, sin cambiar las
metas. El control verifica existencia e integridad; **no puede certificar por sí
solo la calidad de una etiqueta ni la independencia científica de un corpus**.
Una revisión con un hash válido también requiere inspección sustantiva antes de F6.

Decisiones que siguen requiriendo información del investigador:

1. Identidad/disponibilidad del anotador externo y acuerdo para usar sus juicios.
2. Modelo exacto, revisión y presupuesto máximo autorizado para la campaña pagada.
3. Alcance de infraestructura que se afirmará (local/laboratorio o clúster real).
4. Fuente de modelos y etiquetas independientes para T-STRUCT si los originales
   de Pratt no son recuperables. Usar otro conjunto exige documentar su selección
   antes de medir; volver a predecir las secuencias no recupera los modelos originales.

La selección y preparación técnica de casos, hashes, contratos e instrumentos
continúa siendo trabajo de implementación. No depende de obtener esas decisiones
para poder avanzar en desarrollo.
