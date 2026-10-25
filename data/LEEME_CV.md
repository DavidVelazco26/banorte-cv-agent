# Contenido de la carpeta data

- `profile.json`: **única base que consulta directamente el agente actual**. Contiene 25 fuentes iniciales del CV y 8 fuentes nuevas de dos proyectos (33 en total).
- `projects.json`: dos fichas técnicas estructuradas (VLM industrial anonimizado y tesis CNN/neuroevolución) con evidencia, supuestos, métricas propuestas y asuntos pendientes.
- `eval_cases.json`: banco exploratorio de preguntas para evaluar el agente; no son resultados medidos.
- `PROYECTOS_Y_FUENTES.md`: alcance, fuente de cada afirmación y precauciones de publicación.

## Fuentes y límites

El CV 2026 del candidato aporta formación, experiencia, tecnologías, tesis y referencia bibliográfica. Información complementaria procede de conversaciones y material de revisión técnica del caso VLM, que no acreditan automáticamente implementación o autoría individual. Las métricas sugeridas están rotuladas explícitamente como propuestas, nunca como logros comprobados.

No se incluyeron teléfono, correo, ubicaciones de instalaciones, datos internos o imágenes industriales. Confirmar permiso para compartir cualquier caso industrial antes de subir el repositorio público.

La aplicación recupera **solo `profile.json`**, no `projects.json` de modo independiente. `projects.json` funciona como registro documental estructurado; sus hechos aptos para conversación se sincronizaron a las nuevas fuentes.
