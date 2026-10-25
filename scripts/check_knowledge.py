"""Comprueba el JSON y algunas consultas BM25 sin consumir API ni LLM."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.knowledge import load_profile, retrieve  # noqa: E402


def main():
    p = load_profile()
    project_db = json.loads((ROOT / 'data' / 'projects.json').read_text(encoding='utf-8'))
    assert len(project_db['projects']) == 2
    ids = [x['id'] for x in p['sources']]
    assert len(ids) == len(set(ids))
    for project in project_db['projects']:
        for ref in project['relevant_source_ids']:
            assert ref in ids, (project['id'], ref)
    questions = {
       'VLM industrial y JSON': 'project_vlm_architecture',
       'tesis CNN neuroevolución conducción autónoma': 'project_thesis_scope'
    }
    for query, expected_id in questions.items():
        found = [x['id'] for x in retrieve(p, query, k=4)]
        assert expected_id in found, (query, found)
        print(f'{query} -> {found}')
    print(f'OK: {len(project_db["projects"])} proyectos, {len(ids)} fuentes y referencias consistentes')


if __name__ == '__main__':
    main()
