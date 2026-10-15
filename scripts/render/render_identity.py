"""Bind a frame sequence before rendering so resume cannot mix scene/settings versions."""
import json
from pathlib import Path

def bind_sequence(folder, identity, resume):
    folder=Path(folder)
    marker=folder/'sequence_identity.json'
    if resume:
        if marker.exists():
            previous=json.loads(marker.read_text(encoding='utf-8'))
            if previous!=identity:
                raise ValueError('Resume refused: scene, renderer or effective settings changed; use a new output directory')
        elif any(folder.glob('f[0-9]*.png')):
            raise ValueError('Resume refused: existing frames have no verified sequence identity; use a new output directory')
    tmp=marker.with_suffix('.tmp')
    tmp.write_text(json.dumps(identity,ensure_ascii=False,sort_keys=True,indent=2),encoding='utf-8')
    tmp.replace(marker)
