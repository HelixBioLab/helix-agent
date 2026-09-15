# Herramientas de evidencia de la tesis

## Comprobación independiente de instantáneas

`verify_snapshot.py` requiere Python 3.9 o posterior y únicamente su biblioteca estándar. Se puede copiar junto a un corpus a otra máquina. No importa código de Bioinformática.org, no ejecuta el modelo, no escribe archivos y no usa la red.

```bash
python3 script/tesis/verify_snapshot.py /ruta/corpus/repeatsdb.manifest.json
```

Lee el contrato de `packages/bioinformatica/src/bio/snapshot.ts`: `data` es relativo al manifiesto; `rows`, `bytes` y `sha256` deben coincidir con el NDJSON. Calcula el hash de los bytes originales, cuenta y analiza cada registro JSON. Rechaza archivos ausentes, rutas fuera del paquete, claves JSON duplicadas, JSON inválido, filas vacías y metadatos incompatibles. Un corpus vacío explícito (`rows=0`, `bytes=0`, hash del archivo vacío) es válido. Omitir todos los manifiestos es un error.

La salida es JSON; código 0 significa que todas las instantáneas indicadas coinciden, 1 que alguna falla y 2 que la invocación es inválida. No descubre manifiestos automáticamente ni verifica manifiestos de **ejecución**: ese contrato se completa en F4. Tampoco acredita autenticidad, corrección biológica ni integridad frente a quien altera a la vez los datos y el manifiesto. Para autenticidad hace falta un hash de referencia conservado por un tercero.

Las pruebas diferenciales usan la serialización y el hash reales del productor TypeScript y ejecutan Python como proceso independiente:

```bash
cd packages/bioinformatica
bun test test/bio/independent-verify.test.ts
```

Incluyen un traslado del paquete, alteraciones de datos y contadores, JSON inválido con hash coincidente y escapes de ruta. No son una evaluación de los indicadores biológicos de la tesis.

## Edición y revisión del documento de la primera fase

`update_phase1_docx.py` aplica `docs/tesis/fase1-documento.json` a la revisión original de la tesis cuyo SHA-256 se declara en el script. Requiere Python estándar, escribe una copia nueva y rechaza un origen distinto o un destino existente. Conserva los saltos de sección, las partes de figuras y anotaciones; modifica el cuerpo, los estilos de encabezado y la actualización de campos. Para reproducir esa edición se necesita el respaldo original con el hash indicado.

```bash
python3 script/tesis/update_phase1_docx.py /ruta/respaldo-original.docx /tmp/revision/Tesis.docx
/usr/bin/python3 script/tesis/render_docx.py /tmp/revision/Tesis.docx /tmp/renderizado
```

`render_docx.py` requiere LibreOffice y su módulo Python UNO. Abre una instancia aislada sin interfaz, con macros desactivadas, recalcula el índice y exporta DOCX/PDF a un directorio nuevo. El renderizado reserializa el Word; por ello se comparan el texto de referencias y las ilustraciones activas, y se revisan visualmente las páginas afectadas antes de reemplazar el original. No usa una sesión de Word o LibreOffice que el usuario tenga abierta.

Estos scripts registran la transformación de F1. Para fases posteriores se edita la revisión actual: no se cambia el hash esperado para forzar la reaplicación de F1 sobre un Word ya modificado.
