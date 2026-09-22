# Qué falta para completar la tesis

Actualización adicional del 21 de septiembre: el autor da por cerrados
problemática, marco conceptual y estado del arte; su revisión bibliográfica ya
no se considera trabajo pendiente del agente. Se avanzó R2.3 con un adaptador
offline label/autor comprobado en 2xqh/A (12 unidades, 206 residuos y geometría
idéntica), pendiente de integración automática, SIFTS/UniProt y ruta predicha.
La regresión y la referencia real Nextflow volvieron a ejecutarse correctamente.

Actualización: 15 de septiembre de 2026. Sustentación prevista: julio de 2027;
borrador completo objetivo: 4 de junio de 2027. La segunda PC proporciona un
entorno Linux adicional; no acredita ejecución en un clúster con planificador.

## Trabajo de implementación que puede continuar

| Pendiente | Qué constituye su cierre | Opciones del autor |
| --- | --- | --- |
| Detección (R1.1) | Admitir detectores con licencia, receta reproducible, contratos de entrada/salida, datos reales y propagación de fallos; validar las coordenadas de RepeatsDB. Hoy se admiten 2 de 6 entradas auditadas. | Mantener el alcance y completar las integraciones (opción de continuidad), o aprobar una enmienda prospectiva que limite el sistema a unidades suministradas. |
| Identidad y coordenadas (R2.3) | Verificar SIFTS/UniProt y correspondencias de cadena/residuo; llevar modelos predichos inspeccionados a una ruta de ejecución admitida. | Completar la ruta experimental y predicha, o limitar explícitamente el alcance experimental. La segunda opción cambia las afirmaciones de la tesis. |
| Constructos y fallos estructurales (F5) | Completar señales aplicables, fuentes externas y referencias; conservar como no evaluable aquello que no tenga método/evidencia. | Mantener el catálogo y su distinción de no evaluabilidad, o acordar con la asesora un alcance menor antes de evaluar. No usar pLDDT/PAE como prueba de validez física. |

Estos puntos requieren programación, referencias y ensayos; no están bloqueados
por contratar nube o por una nueva autorización para editar el repositorio.

## Dependencias y decisiones externas

| Dependencia | Qué se necesita | Opciones y efecto |
| --- | --- | --- |
| Anotador independiente | Persona con competencia en el dominio, disponibilidad, guía y etiquetas iniciales ciegas; referencia de admisibilidad/equivalencia y al menos 100 turnos para acuerdo. | Colaborador/asesora que pueda asumir el papel independiente, o anotador remunerado. Registrar experiencia y adjudicación separada. Otro modelo no sustituye esta referencia humana. |
| Archivos de Pratt | Coordenadas originales, PAE cuando proceda y etiquetas justificadas. El suplemento recuperado contiene 78 filas de metadatos, no los modelos. | Buscar otro depósito público; solicitar originales a los autores con autorización expresa para contactar; o aprobar un benchmark recuperable equivalente y documentar la enmienda antes de medir. Regenerar predicciones no reproduce los archivos publicados. |
| Modelo y gasto de evaluación | Identificador exacto del modelo, parámetros, límites de tokens/llamadas y tope monetario. La preferencia del autor es minimizar el coste; el nombre comunicado no se ha validado como identificador de API. | Piloto con un tope elegido por el autor para medir coste real; después fijar presupuesto de campaña. O fijar directamente un presupuesto total y detenerse al alcanzarlo, informando los casos no ejecutados. No se iniciaron llamadas pagadas para R3.2. |
| Infraestructura de clúster | Cuenta, planificador/ejecutor, cuota y ventana de acceso si se mantiene esa afirmación. | Conseguir clúster institucional; presupuestar uno en nube; o enmendar prospectivamente la afirmación a ejecución local en dos equipos. Una VM o SSH por sí solos no validan un clúster. |
| Requisitos administrativos | Documento auténtico de aprobación FCI, título oficial y fecha institucional cuando corresponda. | Incorporar los documentos aprobados; mantener las notas rojas mientras estén pendientes. No inventar aprobaciones. |

La batería prevista incluye 50 intenciones factibles y dos paráfrasis por
intención, tres repeticiones (450 solicitudes de ese bloque), casos fuera de
alcance, 50 grafos válidos, 30 inválidos, 40 contrastes de recursos y conjuntos
estructurales con referencias independientes. Los fallos y no evaluables se
conservan en los denominadores conforme al protocolo F2.

## Documento y entrada a F6

El documento ya contiene las secciones de F5 y el anexo A.19. Para el cierre
faltan resultados reservados, sus intervalos y denominadores; discusión de los
límites observados, conclusiones ajustadas a esos resultados, referencias y
comprobación final del template/anexos. Las notas de autor deben retirarse o
resolverse con evidencia, no convertir metas en resultados.

Se puede preparar el corpus, la guía de anotación y los comprobadores de F6.
La medición dependiente no empieza hasta congelar la implementación aplicable,
referencias, particiones, modelo y presupuesto. No es necesario que una
dependencia detenga tareas independientes, pero tampoco se declara satisfecha
la compuerta completa de F5 mientras falten los contratos del dominio.

**Continuidad propuesta:** mantener el alcance actual, completar detectores y
mapeos, preparar anotación y recuperación de datos en paralelo al trabajo del
tesista, y decidir modelo/gasto mediante un piloto con límite explícito. La
nube queda como alternativa de infraestructura, no como requisito de R3.2.
