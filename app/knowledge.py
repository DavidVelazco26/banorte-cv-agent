"""Recuperación textual determinista, transparente y auditable.

Para un CV pequeño es defendible no montar una base vectorial: evita costos,
reduce complejidad y permite documentar exactamente qué fuente se recuperó.
"""
import json
import math
import re
import unicodedata
from collections import Counter
from pathlib import Path

PROFILE_PATH = Path(__file__).resolve().parents[1] / "data" / "profile.json"


def normalize(value: str) -> list[str]:
    value = unicodedata.normalize("NFKD", value.casefold())
    value = "".join(c for c in value if not unicodedata.combining(c))
    return re.findall(r"[a-z0-9_]+", value)


def load_profile(path: Path | None = None) -> dict:
    with (path or PROFILE_PATH).open(encoding="utf-8") as file:
        profile = json.load(file)
    if not isinstance(profile.get("sources"), list) or not profile["sources"]:
        raise ValueError("Se requiere al menos una fuente de conocimiento")
    return profile


def retrieve(profile: dict, question: str, k: int = 3) -> list[dict]:
    """BM25 simplificado con boost de coincidencia en título/etiquetas."""
    sources = profile["sources"]
    query = set(normalize(question))
    if not query:
        return []
    documents = [normalize(x["title"] + " " + x["text"] + " " + " ".join(x.get("tags", []))) for x in sources]
    sizes = [len(doc) for doc in documents]
    mean_size = max(sum(sizes) / len(sizes), 1)
    df = Counter(term for doc in documents for term in set(doc))
    scored = []
    for index, (source, words) in enumerate(zip(sources, documents)):
        count = Counter(words)
        score = 0.0
        for word in query:
            freq = count[word]
            if not freq:
                continue
            idf = math.log(1 + (len(sources) - df[word] + 0.5) / (df[word] + 0.5))
            score += idf * (freq * 2.2) / (freq + 1.2 * (0.25 + 0.75 * sizes[index] / mean_size))
        boosted = set(normalize(source["title"] + " " + " ".join(source.get("tags", []))))
        score += 0.6 * len(query & boosted)
        if score:
            scored.append((score, source))
    ranked = [source for _, source in sorted(scored, key=lambda pair: pair[0], reverse=True)]

    # Intención explícita de enumerar proyectos: con un corpus tan pequeño es
    # preferible ofrecer los dos casos principales en vez de depender solo de
    # coincidencias léxicas dispersas por el CV.
    projects_requested = bool(query & {'proyecto', 'proyectos', 'casos', 'trabajos'})
    specific_project = bool(query & {
        'vlm', 'vision', 'imagenes', 'industrial', 'neuroevolucion',
        'tesis', 'cnn', 'conduccion', 'autonoma', 'lidar', 'escoria'
    })
    forced_ids = []
    if projects_requested and not specific_project:
        forced_ids = ['project_vlm_scope', 'project_thesis_scope']
    elif 'vlm' in query and bool(query & {
        'rol', 'responsabilidad', 'participacion', 'entrenaste',
        'implementaste', 'autor', 'hiciste', 'desarrollaste', 'quien'
    }):
        forced_ids = ['project_vlm_responsibility']

    by_id = {source['id']: source for source in sources}
    prioritized = [by_id[src_id] for src_id in forced_ids if src_id in by_id]
    selected_ids = {source['id'] for source in prioritized}
    prioritized += [source for source in ranked if source['id'] not in selected_ids]
    return prioritized[:k]


def context_for(question: str, profile: dict) -> tuple[str, list[str]]:
    sources = retrieve(profile, question)
    if not sources:
        return "NO SE RECUPERARON FUENTES RELEVANTES", []
    text = "\n\n".join(f"[FUENTE {src['id']}] {src['title']}\n{src['text']}" for src in sources)
    return text, [src["id"] for src in sources]
