"""Export only the download/TLS dependency closure, with uv.lock hashes.

This avoids installing GPU/model dependencies for the focused TLS check. It is
not a replacement for a full project install or model-inference test.
"""
from pathlib import Path
import tomllib

lock = tomllib.loads(Path('uv.lock').read_text())
selected = {}
pending = ['huggingface-hub', 'httpx']
while pending:
    name = pending.pop()
    if name in selected:
        continue
    matches = [p for p in lock['package'] if p['name'] == name]
    if len(matches) != 1:
        raise ValueError(f'Expected one locked package for {name}')
    package = matches[0]
    selected[name] = package
    pending.extend(d['name'] for d in package.get('dependencies', []))
for name, package in sorted(selected.items()):
    artifacts = package.get('wheels', []) + ([package['sdist']] if 'sdist' in package else [])
    hashes = sorted({a['hash'] for a in artifacts})
    if not hashes:
        raise ValueError(f'No locked artifact hashes for {name}')
    print(f"{name}=={package['version']} " + ' '.join('--hash=' + h for h in hashes))
