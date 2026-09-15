# Estado del cierre

Actualizado: 15 de septiembre de 2026.

## Fase 2 completada en su alcance inicial

- Catálogo TRP 1.0.0 implementado con seis recursos auditados: **dos operaciones admitidas**, tres candidatas y un comparador web. Conserva contratos de identificadores, numeración y escalas, con términos EDAM y anclas de bio.tools comprobados. [Catálogo y alcance](../../evaluation/trp/README.md).
- Referencias ejecutadas: recuperación PDB y GeomeTRe 1.0 sobre 2xqh/A con 12 unidades suministradas. Se guardan revisión, digest de imagen local, entorno, comando, archivos y hashes. El catálogo rechaza candidatos y comprueba los bytes antes de resolver una operación. La ejecución de referencia no mide detección de repeticiones.
- **R1.1 permanece parcial.** Falta integrar el catálogo y admitir detección/mapeos; las exclusiones y el traslado de esas tareas a F3 se declaran en el plan. No se presenta 2/2 como cobertura de todos los recursos TRP.
- R2.1 implementado como diseño: [protocolo 1.0.0](../../evaluation/trp/PROTOCOL.md), 21 indicadores, criterios, corpus, denominadores, tres repeticiones de lenguaje, incertidumbre y enmiendas. [Guía externa](../../evaluation/trp/ANNOTATION.md) y plantillas preparadas; no existe anotador confirmado ni evaluación empírica ejecutada.
- Se instaló el Word revisado en `~/Projects/Tesis.docx` y el PDF en `~/Projects/Tesis-fase2.pdf`: **121 páginas**, incluidas dos páginas automáticas de separación. Se actualizan capítulos 4 y 5, viabilidad y calendario; A.16 contiene el protocolo completo. Índice sin duplicados, 25 notas rojas en cursiva y cuatro ilustraciones conservadas. [Hashes y comprobaciones](evidencia/documento-fase2.json).
- Se corrigió un defecto de F1: el texto de R2.1 se había colocado fuera de los párrafos de las celdas y Writer lo descartaba. F2 corrige el escritor y verifica las celdas ya renderizadas. El texto bibliográfico completo se conservó; contar y depurar entradas partidas queda para F7.

| Comprobación F2                   | Resultado                                             | Evidencia                                                 |
| --------------------------------- | ----------------------------------------------------- | --------------------------------------------------------- |
| Suite conjunta nf-core, bio y TRP | 350 aprobadas, 0 fallidas, 32 archivos                | [Log](evidencia/dominio-fase2.log)                        |
| Pruebas específicas del catálogo  | 16 aprobadas, 0 fallidas                              | [Log](evidencia/catalogo-pruebas-fase2.log)               |
| Tipos y lint                      | Tipos sin errores; lint sin errores ni advertencias   | [Registro](evidencia/fase2.json)                          |
| Referencias guardadas             | 2/2 entradas admitidas verificables sin red ni Docker | [Verificación](evidencia/catalogo-verificacion-fase2.log) |

La sustentación se mantiene en julio de 2027 y el borrador completo tiene fecha objetivo 4 de junio. Anotador y clúster siguen pendientes por confirmación expresa del usuario. No se realizaron inferencias de evaluación ni se enviaron encargos a terceros. El cambio previo del SDK queda fuera del commit.

## Fase 1 completada

- Plan de siete fases con hitos, dependencias, criterios de aceptación y calendario propuesto: [PLAN.md](PLAN.md).
- Los cinco objetivos y 21 resultados del Word vigente están mapeados contra código, pruebas y brechas: [trazabilidad.json](trazabilidad.json). Ningún indicador experimental completo se declara alcanzado por pasar pruebas de componentes.
- Se reemplazó `~/Projects/Tesis.docx` por la versión revisada y se guardó `~/Projects/Tesis-fase1.pdf`. El documento tiene 110 páginas renderizadas. Se completaron las 15 secciones del Anexo A como plan estimado; se redactó un resumen de 245 palabras y conclusiones de avance; se presentó el estado de los 21 resultados en el capítulo 4.
- Se corrigió el nivel de “Presentación de los resultados esperados”: ahora es el capítulo 4 y las conclusiones son el 5. Se recalcularon el índice y la paginación de preliminares, cuerpo y anexo; se uniformaron los encabezados. Se corrigieron las dos erratas señaladas y se completaron las celdas de R2.1 en la tabla de verificación.
- Se conservaron las cuatro ilustraciones en uso y el texto de la bibliografía. El conteo de 100 entradas comunicado en F1 no se reutiliza: F2 cotejó 99 párrafos bibliográficos y dos notas, con entradas partidas pendientes de depurar en F7. La pasada de LibreOffice descartó una imagen no utilizada y el comentario asociado a material de plantilla retirado; se conservaron las anotaciones vinculadas al texto que permanece. La revisión de contenido de esas referencias se hará en F7.
- Se incorporaron notas con el formato existente: `NOTA PARA EL AUTOR.`, cursiva y rojo. Las estimaciones no se presentan como gastos realizados, y las conclusiones de avance no se presentan como resultados finales.
- Se implementó una comprobación de corpus con Python estándar, independiente del productor TypeScript y sin modelo ni red: [verificador](../../script/tesis/verify_snapshot.py). También verificó correctamente la instantánea histórica de 156 entradas de nf-core conservada en la bitácora; ese corpus no sustituye el de evaluación TRP.

## Comprobaciones realizadas

| Comprobación                        | Resultado                                                                                                                                                       | Evidencia                                           |
| ----------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------- |
| Suite de dominio antes de cambios   | 322 aprobadas, 0 fallidas; 30 archivos                                                                                                                          | [Log](evidencia/dominio-antes.log)                  |
| Pruebas nuevas del verificador      | 12 aprobadas, 0 fallidas                                                                                                                                        | [Log](evidencia/verificador.log)                    |
| Suite de dominio después de cambios | 334 aprobadas, 0 fallidas; 31 archivos                                                                                                                          | [Log](evidencia/dominio-despues.log)                |
| Tipos del paquete                   | `bun typecheck`, salida 0                                                                                                                                       | [Log](evidencia/tipos.log)                          |
| Lint del archivo de prueba nuevo    | 0 errores y 0 advertencias                                                                                                                                      | [Registro](evidencia/fase1.json)                    |
| Word/PDF                            | Sin instrucciones pendientes de la plantilla; 21 resultados y 15 apartados del anexo presentes; índice actualizado; imágenes activas y bibliografía preservadas | [Registro y hashes](evidencia/documento-fase1.json) |

Las pruebas de ingeniería no acreditan los indicadores biológicos o de elicitación. El verificador nuevo cubre **instantáneas de corpus**; la cobertura de todas las ejecuciones se completa en F4. La revisión visual se concentró en portada, resumen, índice, capítulos nuevos y tablas del anexo; la auditoría completa de contenido y presentación de los capítulos 1–3 está planificada en F7.

## Dependencias que siguen abiertas

**Conexión resuelta por confirmación del usuario:** el agente ya está conectado con OpenAI. No es necesario solicitar esa conexión otra vez. F1 no ejecutó llamadas al modelo; la identidad exacta del modelo y su configuración se verificarán al preparar el protocolo.

**Plazo confirmado por el usuario:** sustentación en julio de 2027, con un borrador completo previo. El plan mantiene el 4 de junio como fecha objetivo del borrador y reserva el resto de junio para revisión y correcciones. No se necesita volver a preguntar por el mes de sustentación.

1. Copia auténtica del Tema FCI y denominación oficial del título. La sección se llenó con el alcance y una nota roja de pendiente administrativo; no se fabricó una aprobación institucional.
2. Confirmación de dedicación y presupuesto; programación institucional del día exacto de sustentación dentro de julio de 2027. Las 640 horas y S/23 204,50 siguen siendo supuestos de planificación detallados en el anexo; la confirmación del plazo no confirma esos recursos.
3. Anotador externo para R1.3 y R4.3 y acceso a clúster: el usuario confirmó que ninguno está asegurado y pidió registrarlos como dependencias pendientes. Preparar los instrumentos sin atribuirles participación ni disponibilidad.
4. Instrumentos TRP ejecutables y con condiciones verificadas; datos originales de los fallos publicados; modelo, configuración y límite de costo de la evaluación.

## Siguiente fase: F3, especificación y composición

1. Partir del Word y catálogo de F2. R1.1 sigue parcial: reconstruir los entornos de ReUPred/STRPsearch y conseguir referencias de detección antes de prometer tareas de descubrimiento. Verificar condiciones y marco de la API actual de RepeatsDB. El ensayo GeomeTRe no sustituye esos recursos.
2. Construir el esquema de especificación con procedencia de parámetros y aprobación ligada a su hash. Integrar la resolución del catálogo que verifica sus archivos.
3. Emitir Nextflow, comprobar todo el grafo, los identificadores concretos, formatos, cadenas, numeración y controles exigibles; emitir informe de comprobaciones realizadas y omitidas.
4. Construir el corpus adversarial y los ejemplos de desarrollo. Mantener las familias/intenciones de depuración fuera de la reserva de F6.
5. Completar la guía y asignación externa cuando exista participante, sin atribuir a terceros etiquetas del investigador. El modelo, presupuesto, clúster y congelación de la campaña siguen pendientes donde correspondan.

## Reanudación y archivos

El Word actualizado es el documento editable principal. [fase1-documento.json](fase1-documento.json) conserva el contenido aplicado en esta fase; no es un generador permanente que deba sobreescribir posteriores ediciones. El script de edición exige el hash del documento de entrada original para evitar aplicar los mismos cambios a una revisión distinta. [Las instrucciones de edición y renderizado](../../script/tesis/README.md) documentan ese límite.

El commit del verificador es `267afbd` (`feat(thesis): add independent snapshot verification`). La planificación, el contenido documental y los registros se guardan en el commit de documentación que contiene este archivo. El cambio previo en `packages/sdk/js/src/v2/client.ts` se conserva fuera de ambos commits; su hash antes y después es `99fa8d8e31a4b95c5b7ad2814319f94b8d96a27e22331e78b05d179e232311ba`.
