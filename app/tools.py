"""Herramientas de consulta en modo solo lectura para el agente de CV.

No ejecutan código del modelo, no acceden a la red y no modifican información.
Los datos se recuperan de un CV revisable y dos fichas de proyectos.
"""
import json
from pathlib import Path
from typing import Any

from .knowledge import load_profile, normalize

PROJECTS_PATH = Path(__file__).resolve().parents[1] / "data" / "projects.json"

SKILL_CATEGORIES: dict[str, list[str]] = {
    "ia_generativa": ["genai_rag", "vlm", "lora_finetuning", "agents_mcp"],
    "vision": ["computer_vision", "lidar_3d", "ml_deep_learning"],
    "backend": ["software_integration", "tech_stack"],
    "datos": ["data_stack", "datasets_evaluation"],
    "infraestructura": ["deployment", "cloud_mlops"],
    "todas": ["tech_stack", "data_stack", "cloud_mlops", "industry_integration"],
}

TOOL_SCHEMAS = [
    {
        "type": "function",
        "name": "get_professional_profile",
        "description": "Consulta el perfil general, experiencia laboral y formación académica del candidato.",
        "parameters": {"type": "object", "properties": {}, "required": [], "additionalProperties": False},
        "strict": True,
    },
    {
        "type": "function",
        "name": "search_projects",
        "description": "Busca proyectos profesionales o académicos usando palabras clave. Usa la herramienta antes de hablar de proyectos.",
        "parameters": {
            "type": "object",
            "properties": {"query": {"type": "string", "description": "Tema del proyecto: VLM, visión, CNN, neuroevolución, etc."}},
            "required": ["query"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "get_project_details",
        "description": "Obtiene los detalles públicos y límites de evidencia de uno de los dos proyectos identificados.",
        "parameters": {
            "type": "object",
            "properties": {
                "project_id": {"type": "string", "enum": ["industrial_vlm_visual_analysis", "cnn_neuroevolution_thesis"]}
            },
            "required": ["project_id"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "get_technical_skills",
        "description": "Consulta habilidades técnicas según categoría, indicando que una habilidad declarada no garantiza años de experiencia.",
        "parameters": {
            "type": "object",
            "properties": {"category": {"type": "string", "enum": list(SKILL_CATEGORIES)}},
            "required": ["category"],
            "additionalProperties": False,
        },
        "strict": True,
    },
]


def _load_projects() -> list[dict[str, Any]]:
    with PROJECTS_PATH.open(encoding="utf-8") as file:
        return json.load(file)["projects"]


def _extract(profile: dict, ids: list[str]) -> list[dict]:
    index = {s["id"]: s for s in profile["sources"]}
    return [
        {"source_id": s["id"], "title": s["title"], "text": s["text"][:3500]}
        for source_id in ids if (s := index.get(source_id))
    ]


def get_professional_profile() -> dict:
    profile = load_profile()
    return {
        "candidate_name": profile["candidate_name"],
        "headline": profile["headline"],
        "sources": _extract(profile, ["profile", "current_role", "masters", "bachelors", "languages"]),
    }


def search_projects(query: str) -> dict:
    if not isinstance(query, str) or not 1 <= len(query.strip()) <= 200:
        raise ValueError("La búsqueda debe contener entre 1 y 200 caracteres")
    projects = _load_projects()
    terms = set(normalize(query))
    meaningful_terms = terms - {"proyectos", "proyecto", "de", "del", "que", "sobre", "los", "las", "la", "el", "dos", "cuales", "cual", "son", "tiene", "tienes", "sus", "mas", "relevantes", "importantes", "dime", "explica", "menciona"}
    scored = []
    for project in projects:
        text = " ".join([
            project["title"], project["public_description"], project["problem"],
            " ".join(project["category"]), " ".join(project.get("relevant_source_ids", [])),
        ])
        tokens = set(normalize(text))
        score = len(meaningful_terms & tokens)
        if not meaningful_terms or score > 0:
            scored.append((score, project))
    # Si se pide un listado general de proyectos, mostrar los dos casos documentados.
    if not scored and ({"proyecto", "proyectos", "casos"} & terms):
        scored = [(0, p) for p in projects]
    scored.sort(key=lambda result: result[0], reverse=True)
    return {
        "query": query,
        "projects": [
            {"project_id": p["id"], "title": p["title"], "summary": p["public_description"],
             "source_ids": p.get("relevant_source_ids", [])}
            for _, p in scored[:2]
        ],
        "note": "Las fichas son borradores y no deben confundirse con responsabilidades o métricas verificadas.",
    }


def get_project_details(project_id: str) -> dict:
    project = next((p for p in _load_projects() if p["id"] == project_id), None)
    if project is None:
        raise ValueError("Identificador de proyecto no permitido")
    return {
        "project_id": project_id,
        "title": project["title"],
        "public_description": project["public_description"],
        "problem": project["problem"],
        "goal": project["goal"],
        "technologies": project.get("tools_and_technologies", {}),
        "candidate_involvement": project.get("candidate_involvement", {}),
        "evaluation": project.get("evaluation", {}),
        "source_ids": project.get("relevant_source_ids", []),
        "note": "No presentar métricas propuestas como resultados medidos ni atribuir autorías no confirmadas.",
    }


def get_technical_skills(category: str) -> dict:
    if category not in SKILL_CATEGORIES:
        raise ValueError("Categoría de habilidades desconocida")
    profile = load_profile()
    return {
        "category": category,
        "sources": _extract(profile, SKILL_CATEGORIES[category]),
        "note": "Son habilidades declaradas en el CV; su grado de dominio no se infiere automáticamente.",
    }


# No hay eval(), exec(), llamadas externas ni acceso arbitrario a archivos.
_TOOL_HANDLERS = {
    "get_professional_profile": get_professional_profile,
    "search_projects": search_projects,
    "get_project_details": get_project_details,
    "get_technical_skills": get_technical_skills,
}


def execute_tool(name: str, arguments: str) -> dict:
    """Lista blanca + validación explícita antes de ejecutar una función."""
    if name not in _TOOL_HANDLERS:
        return {"error": "Herramienta no permitida"}
    if len(arguments) > 2000:
        return {"error": "Argumentos demasiado extensos"}
    try:
        data = json.loads(arguments)
        if not isinstance(data, dict):
            raise ValueError("Se esperaba un objeto JSON")
        expected = {
            "get_professional_profile": set(),
            "search_projects": {"query"},
            "get_project_details": {"project_id"},
            "get_technical_skills": {"category"},
        }[name]
        if set(data) != expected:
            raise ValueError("Claves de argumentos inválidas")
        return _TOOL_HANDLERS[name](**data)
    except (ValueError, TypeError, KeyError, json.JSONDecodeError):
        return {"error": "Argumentos inválidos para la herramienta"}
