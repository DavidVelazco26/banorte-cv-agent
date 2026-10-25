"""Regresiones de la base de conocimiento de los dos proyectos."""
import json
from pathlib import Path

from app.knowledge import load_profile, retrieve

ROOT = Path(__file__).resolve().parents[1]

def test_project_dataset_is_consistent():
    data = json.loads((ROOT / 'data' / 'projects.json').read_text(encoding='utf-8'))
    assert {p['id'] for p in data['projects']} == {'industrial_vlm_visual_analysis', 'cnn_neuroevolution_thesis'}
    profile = load_profile()
    ids = [source['id'] for source in profile['sources']]
    assert len(ids) == len(set(ids))
    for p in data['projects']:
        assert not p['evaluation']['confirmed_numeric_results']
        assert set(p['relevant_source_ids']).issubset(ids)

def test_vlm_project_can_be_found():
    profile = load_profile()
    found = [r['id'] for r in retrieve(profile, 'VLM industrial y JSON', k=4)]
    assert 'project_vlm_architecture' in found

def test_thesis_project_can_be_found():
    profile = load_profile()
    found = [r['id'] for r in retrieve(profile, 'tesis CNN neuroevolución conducción autónoma', k=4)]
    assert 'project_thesis_scope' in found

def test_industrial_project_public_data_are_anonymized():
    data = json.loads((ROOT / 'data' / 'projects.json').read_text(encoding='utf-8'))
    project = next(p for p in data['projects'] if p['id'] == 'industrial_vlm_visual_analysis')
    text = json.dumps(project, ensure_ascii=False).lower()
    for confidential_label in ('guerrero', 'ternium', 'camera 21', 'cam 21', 'ckpt931', '101,646', '182 coladas'):
        assert confidential_label not in text


def test_broad_question_retrieves_both_projects():
    p = load_profile()
    ids = [s['id'] for s in retrieve(p, 'Cuéntame sobre tus proyectos', k=3)]
    assert {'project_vlm_scope', 'project_thesis_scope'}.issubset(ids)

def test_personal_role_question_finds_limits():
    p = load_profile()
    ids = [s['id'] for s in retrieve(p, '¿Qué rol tuviste en el VLM?', k=3)]
    assert 'project_vlm_responsibility' in ids
