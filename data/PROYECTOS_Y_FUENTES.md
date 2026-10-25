# Dos proyectos para el agente de CV Banorte

Esta carpeta ahora contiene dos proyectos en **`projects.json`**, además del CV general y fuentes indexables en **`profile.json`**.

## ¿Qué lee el agente?

El backend actual (`app/knowledge.py`) recupera texto únicamente de `profile.json → sources`. Por eso se añadieron **ocho fuentes** indexables nuevas (cuatro por proyecto). **`projects.json` es un registro estructurado para documentar los dos casos**, pero el backend no lo lee directamente; sus hechos aptos para conversación están resumidos en las ocho fuentes. No es una base SQL ni vectorial, sino una base de conocimiento JSON compatible con la plantilla existente.

## Casos documentados

### 1. Análisis de imágenes industriales mediante VLM (anonimizado)

- **Problema:** interpretación de imágenes variables y transformación de observaciones en resultados estructurados.
- **Experiencia respaldada en CV (general):** integración de VLM, prompts, JSON y servicios REST; el CV también declara LoRA, pero **no lo atribuye inequívocamente a este proyecto concreto**.
- **Contexto técnico revisado:** flujo visual y sus limitaciones; la arquitectura descrita es una **referencia técnica**, no una implementación individual certificada.
- **Participación personal:** se dispone de evidencia de revisión y documentación técnica; están **pendientes** las responsabilidades precisas de implementación/entrenamiento.
- **Resultados:** no se incluyen métricas numéricas confirmadas.
- **Divulgación:** no se incluyen nombres de instalaciones, activos, identificadores, imágenes ni volúmenes internos.

### 2. Tesis de Maestría: Reducción de parámetros en una CNN mediante neuroevolución

- **Problema:** reducir la complejidad de una CNN para estimar el ángulo de dirección en conducción autónoma.
- **Enfoque documentado en CV:** desarrollar CNN y optimizar su arquitectura mediante neuroevolución para reducir parámetros conservando capacidad predictiva.
- **Resultados:** reducción cualitativa declarada; **no hay porcentajes, conteos de parámetros ni errores de regresión** documentados.
- **Publicación citada:** se reproduce el DOI señalado en el CV, aún pendiente de cotejar con el original.

## Campos de trazabilidad

En cada proyecto de `projects.json` se distinguen:

- `approach.cv_verified_general_experience` o `approach.confirmed_by_cv`: afirmaciones presentes en CV.
- `approach.case_context_from_prior_technical_review`: material comentado previamente, distinto a prueba de participación individual.
- `approach.illustrative_architecture_not_deployment_claim`: arquitectura de referencia, no despliegue acreditado.
- `candidate_involvement`: respaldo y aspectos no confirmados.
- `evaluation.confirmed_numeric_results`: resultados numéricos comprobados (vacío si no existen).
- `evaluation.proposed_not_measured`: métricas sugeridas, no resultados reales.
- `pending_verification`: confirmaciones necesarias antes de presentarlo como hecho.

## Cómo verificar en Windows

```powershell
.\.venv\Scripts\python.exe scripts\check_knowledge.py
.\.venv\Scripts\python.exe -m pytest -q
```

## Preguntas sugeridas para la demo

1. ¿Cuáles son tus dos proyectos principales?
2. ¿Cuál es el problema que aborda un VLM en un proceso industrial?
3. ¿Qué papel cumple JSON en la integración de análisis visual?
4. ¿Qué realizaste personalmente en el proyecto VLM? (Debe reconocer que falta delimitar atribuciones).
5. ¿Qué resultados cuantitativos obtuvo el VLM? (No deben inventarse).
6. ¿Cómo optimizaste una CNN mediante neuroevolución en tu tesis?
7. ¿Qué aplicación tiene la predicción del ángulo de dirección?
8. ¿Qué porcentaje exacto de parámetros redujiste? (No consta).
9. ¿Qué publicaciones relacionadas con la tesis mencionas?

**Revisión requerida:** confirmar permiso para publicar el primer caso y precisar responsabilidades, bibliografía y métricas reales.
