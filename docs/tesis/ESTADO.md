# Estado del cierre

Actualizado: 15 de septiembre de 2026.

## Fase 1 completada

- Plan de siete fases con hitos, dependencias, criterios de aceptación y calendario propuesto: [PLAN.md](PLAN.md).
- Los cinco objetivos y 21 resultados del Word vigente están mapeados contra código, pruebas y brechas: [trazabilidad.json](trazabilidad.json). Ningún indicador experimental completo se declara alcanzado por pasar pruebas de componentes.
- Se reemplazó `~/Projects/Tesis.docx` por la versión revisada y se guardó `~/Projects/Tesis-fase1.pdf`. El documento tiene 110 páginas renderizadas. Se completaron las 15 secciones del Anexo A como plan estimado; se redactó un resumen de 245 palabras y conclusiones de avance; se presentó el estado de los 21 resultados en el capítulo 4.
- Se corrigió el nivel de “Presentación de los resultados esperados”: ahora es el capítulo 4 y las conclusiones son el 5. Se recalcularon el índice y la paginación de preliminares, cuerpo y anexo; se uniformaron los encabezados. Se corrigieron las dos erratas señaladas y se completaron las celdas de R2.1 en la tabla de verificación.
- Se conservaron las cuatro ilustraciones en uso y las 100 entradas bibliográficas del documento. La pasada de LibreOffice descartó una imagen no utilizada y el comentario asociado a material de plantilla retirado; se conservaron las anotaciones vinculadas al texto que permanece. La revisión de contenido de esas referencias se hará en F7.
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

1. Copia auténtica del Tema FCI y denominación oficial del título. La sección se llenó con el alcance y una nota roja de pendiente administrativo; no se fabricó una aprobación institucional.
2. Confirmación de dedicación, fecha de sustentación y presupuesto. Se usó el escenario del contexto: julio de 2027, con entrega interna en junio. Las 640 horas y S/23 204,50 son supuestos de planificación detallados en el anexo.
3. Anotador externo para R1.3 y R4.3 y acceso a clúster para la ejecución declarada en esa infraestructura. No se presupone su disponibilidad.
4. Instrumentos TRP ejecutables y con condiciones verificadas; datos originales de los fallos publicados; modelo, configuración y límite de costo de la evaluación.

## Próxima fase: F2, catálogo y protocolo TRP

1. Releer el Word actualizado y la matriz; no reiniciar con los antiguos objetivos nf-core.
2. Inspeccionar interfaces y condiciones actuales de las herramientas TRP en fuentes primarias. Ejecutar una invocación mínima por candidata y guardar entrada, salida, versión y hashes. Priorizar el ensayo técnico de ReUPred señalado en el contexto.
3. Admitir en el catálogo únicamente operaciones con evidencia de ejecución y contratos completos. Mantener los recursos exclusivamente web como comparadores.
4. Cerrar el protocolo R2.1 de los 21 resultados antes de medir: particiones, corpus, denominadores, umbrales abiertos, tratamiento de fallos/no evaluables y registro de enmiendas.
5. Preparar instrucciones y material de anotación externa. No atribuir etiquetas a terceros ni iniciar gasto por el hecho de haber reservado una partida.

## Reanudación y archivos

El Word actualizado es el documento editable principal. [fase1-documento.json](fase1-documento.json) conserva el contenido aplicado en esta fase; no es un generador permanente que deba sobreescribir posteriores ediciones. El script de edición exige el hash del documento de entrada original para evitar aplicar los mismos cambios a una revisión distinta. [Las instrucciones de edición y renderizado](../../script/tesis/README.md) documentan ese límite.

El commit del verificador es `267afbd` (`feat(thesis): add independent snapshot verification`). La planificación, el contenido documental y los registros se guardan en el commit de documentación que contiene este archivo. El cambio previo en `packages/sdk/js/src/v2/client.ts` se conserva fuera de ambos commits; su hash antes y después es `99fa8d8e31a4b95c5b7ad2814319f94b8d96a27e22331e78b05d179e232311ba`.
