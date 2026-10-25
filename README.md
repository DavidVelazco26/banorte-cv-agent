# Agente de CV — Reto IA Banorte (base editable)

> **Estado:** plantilla técnica con `data/profile.json` personalizado a partir del CV facilitado por el candidato (edición 2026). **NO** está desplegada ni validada contra un LLM real o la plataforma Banorte. Los datos reflejan afirmaciones del CV, no verificaciones independientes.

## Propósito

Agente que responde preguntas sobre la trayectoria del candidato con respaldo en fuentes estructuradas. Arquitectura: `POST /v1/responses` (FastAPI) → recuperación BM25 local → LLM Responses API → respuesta atribuible. El mismo endpoint ofrece JSON y SSE *diferido*.

## Justificación técnica

- **Sin base vectorial al inicio:** un CV consta de pocos documentos. Un retrieval léxico reproducible reduce costos y evita complejidad innecesaria. Si el corpus crece, evaluar primero recall@k y reemplazar por búsqueda híbrida (vector + BM25) y reranking.
- **Sin MCP ni multiagente artificial:** no hay herramientas externas obligatorias ni ejecución de tareas sensibles. Se puede extender con tools cuando exista necesidad real.
- **Grounding:** cada respuesta debe apoyarse en `data/profile.json`; las fuentes recuperadas van en el prompt y el LLM debe citar sus IDs.
- **Datos:** la base de conocimiento fue elaborada a partir del CV 2026 aportado por el candidato; se omitieron correo y teléfono personales. Antes de publicar, revisar autorización y exactitud de cada experiencia descrita.
- **Prevención:** las claves permanecen en variables de entorno; autenticación Bearer opcional para pruebas y recomendada como obligatoria en producción; validación de entrada y logs sin contenidos.
- **Limitación de memoria:** `previous_response_id` funciona solo en proceso (retención temporal 30 min, `store` predeterminado `true`); para escalabilidad utilizar Redis u otro almacén compartido. Como alternativa, enviar todo el historial en `input`.
- **Limitación de streaming:** eventos SSE sintácticamente ordenados, emitidos tras obtener la respuesta completa. Para *true streaming*, propagar los deltas de proveedor mediante `AsyncClient.stream`.
- **Compatibilidad:** implementa el caso de uso *texto/JSON/SSE* de Open Responses, **NO** la totalidad de la especificación (p. ej. multimodal, WebSocket, function calls expuestos, compactación, gestión persistente). Comprobar contra el evaluador del reto.

## Configuración

```bash
python -m venv .venv
# Windows PowerShell: .venv\\Scripts\\Activate.ps1
# Linux/macOS: source .venv/bin/activate
pip install -r requirements-dev.txt
# Copiar .env.example a .env y sustituir secretos (el servicio no carga .env automáticamente).
# Windows PowerShell: $env:OPENAI_API_KEY='tu-clave'; $env:AGENT_API_KEY='tu-secreto'
# Linux/macOS: export OPENAI_API_KEY='tu-clave'; export AGENT_API_KEY='tu-secreto'
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

**Importante:** `AGENT_API_KEY` vacío significa endpoint público sin autenticación. **No** publicar así. No utilizar una clave de OpenAI como clave de acceso del evaluador.

## Probar localmente

```bash
curl -X POST http://127.0.0.1:8000/v1/responses \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer tu-secreto" \
  -d '{"model":"cv-agent-v1","input":"¿Qué proyectos de IA has desarrollado?"}'
```

Enviar `"stream":true` para probar SSE. Para continuidad en un solo proceso, primera solicitud `"store":true`, después una segunda con `"previous_response_id":"resp_..."` e `"input":"otra pregunta"`. Enviar historial completo mediante `input` también es válido.

```bash
pytest -q
python scripts/evaluate.py https://tu-endpoint.example tu-secreto
```

La prueba `scripts/evaluate.py` es **orientativa**: edita los casos y añade evaluaciones semánticas, groundedness por humano y pruebas adversariales; no usar los casos actuales como evidencia de resultados reales.

## Docker

```bash
docker build -t cv-agent:local .
docker run --rm -p 8080:8080 -e OPENAI_API_KEY -e AGENT_API_KEY -e LLM_MODEL cv-agent:local
```

Usar un servicio de contenedores con URL HTTPS pública y variables de entorno seguras (por ejemplo Azure Container Apps, Cloud Run, Render). **El repositorio no despliega por sí mismo.** Evitar publicar logs detallados o trazas del CV. Para varias réplicas, sustituir la memoria local por un almacenamiento compartido o gestionar historial explícito.

## Personalización obligatoria

1. Revisar `data/profile.json`, integrado a partir del CV 2026, y confirmar que cada afirmación sea **real, verificable y publicable**; el CV no incluye detalles ni métricas de proyectos industriales particulares.
2. Escribir cada proyecto en formato *problema → arquitectura → papel personal → métricas reales → aprendizajes*.
3. No adjuntar código, imágenes, datos de planta, secretos o información interna sin autorización.
4. Revisar modelo/proveedor, costos, límites de peticiones y política de retención de datos.
5. Preparar evaluaciones con preguntas normales, complicadas y adversariales; registrar cifras medidas, no estimadas.
6. Confirmar con el agente Guía del reto URL base exacta, `model`, streaming y encabezados esperados.
7. Ejecutar conformidad de Open Responses en https://www.openresponses.org/compliance y verificar qué casos acepta realmente esta versión.
8. Publicar GitHub únicamente tras revisar archivos y `.gitignore`.

## Presentación técnica sugerida

Explicar requisitos, diagrama de arquitectura, decisión BM25 vs vector DB, fragmentos del repositorio, diseño de prompts con fuentes, controles de seguridad, pruebas, logs, uso de tokens/costos, despliegue y mejoras priorizadas. Sin atribuir capacidades no implementadas.

## Base de conocimiento integrada del CV (2026)

- Archivo principal: `data/profile.json`, con entradas `sources` para perfil, experiencia, formación, tecnologías, tesis y publicaciones.
- `data/eval_cases.json` incluye comprobaciones exploratorias, NO métricas fiables por sí solas.
- Se omitieron correo y teléfono para evitar su exposición involuntaria a usuarios del agente.
- Se mantienen únicamente datos del CV; no se agregaron nombres de proyectos industriales, años de experiencia por herramienta ni resultados cuantitativos no suministrados.
- Si el CV cambia, editar o ampliar fuentes dentro de `profile.json` (no es necesario colocar el PDF original en el repositorio público).

## Ampliación: dos proyectos documentados

Se integraron **dos casos**: (1) VLM industrial anonimizado (contexto técnico revisado, sin atribuir implementación personal no demostrada) y (2) tesis de Maestría sobre optimización de CNN con neuroevolución (documentada en el CV).

- `data/projects.json` contiene las dos fichas estructuradas con procedencia, límites, arquitectura de referencia y evaluaciones propuestas. **El agente no lee este archivo directamente**.
- `data/profile.json` incorpora **8 nuevas fuentes** recuperables mediante BM25 y un enrutamiento mínimo para consultas de proyectos; ahora contiene **33 fuentes** que sí utiliza el agente.
- `data/eval_cases.json` incluye preguntas adicionales de ambas experiencias y casos que deben reconocer evidencia faltante.
- `data/PROYECTOS_Y_FUENTES.md` explica cómo se diferencian hechos del CV, contexto técnico y propuestas de evaluación.
- `python scripts/check_knowledge.py` comprueba estructura, referencias y recuperación léxica para preguntas de los dos proyectos.

**Antes de presentar como logro personal:** verificar las atribuciones específicas, permisos de divulgación, resultados numéricos y metadatos bibliográficos. No subir documentación confidencial ni proyectos industriales originales.

---

## Actualización: Function calling (GPT-6 Luna)

Se incorporó un módulo `app/tools.py` con cuatro consultas de solo lectura sobre
`data/profile.json` y `data/projects.json`: perfil, proyectos, detalle de proyectos
y habilidades técnicas. `app/agent.py` permite que el LLM seleccione herramientas
y envía sus resultados mediante `function_call_output` con `store=False`.

**Guía detallada para Windows:** [PASO_A_PASO_TOOLS.md](PASO_A_PASO_TOOLS.md).

La implementación es un paso intermedio: aún requiere validación con una API real,
revisión de información industrial y pruebas en la plataforma Banorte.
