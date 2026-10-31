#!/usr/bin/env python3
"""Add missing MagicRule lines only; never delete existing rules."""
import json, os
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
INDEX = 'https://magicrule.pages.dev/data/index/Surge.json'
MAPPING = {
    'B+Y.list': {'Boc': 'BOC'},
    'G+S+Y+O.list': {'Spotify': 'Spotify', 'Gemini': 'Gemini', 'Google': 'Google', 'Github': 'GitHub', 'YouTube': 'YouTube', 'OpenAi': 'OpenAI'},
    'T+T.list': {'TikTok': 'TikTok'},
    'E+M.list': {'Emby': 'Emby'},
}

def fetch(url):
    req = Request(url, headers={'User-Agent': 'magicrule-sync/1.0'})
    with urlopen(req, timeout=60) as response:
        return response.read()

def main():
    catalog = json.loads(fetch(INDEX))['rules']
    by_name = {}
    for item in catalog:
        name = item.get('name')
        if name in by_name: raise ValueError('Duplicate rule name: ' + name)
        by_name[name] = item
    rules = {}
    for name in sorted({v for m in MAPPING.values() for v in m.values()}):
        item = by_name[name]
        manifest = json.loads(fetch(item['manifest']))
        artifact = next ( (a for a in manifest['artifacts'] if a.get('role') == 'full' and a.get('ext') == 'list' and not a.get('empty')), None)
        if not artifact: raise ValueError('Missing full artifact: ' + name)
        lines = fetch(artifact['url']).decode('utf-8-sig').splitlines()
        lines = [line.strip() for line in lines if line.strip() and not line.lstrip().startswith(('#', '//', ';'))]
        if not lines or any(',' not in line for line in lines): raise ValueError('Invalid or empty artifact: ' + name)
        rules[name] = lines
        print(name, 'rules:', len(lines), 'source:', artifact['url'])
    updates = {}
    for filename, mapping in MAPPING.items():
        path = ROOT / 'rules' / filename
        raw = path.read_text(encoding='utf-8')
        lines = raw.splitlines()
        existing = {line.strip() for line in lines if line.strip() and not line.lstrip().startswith(('#', '//', ';'))}
        additions = {}
        for marker, name in mapping.items():
            indexes = [i for i, line in enumerate(lines) if line.strip() == '#' + marker]
            if len(indexes) != 1: raise ValueError(f'{filename}: marker #{marker} missing or duplicated')
            fresh = []
            for rule in rules[name]:
                if rule not in existing:
                    fresh.append(rule)
                    existing.add(rule)
            if fresh: additions[indexes[0]] = fresh
            print(filename, marker, 'new rules:', len(fresh))
        for i in sorted(additions, reverse=True):
            lines[i+1:i+1] = additions[i]
        if additions: updates[path] = '\n'.join(lines) + '\n'
    for path, content in updates.items(): path.write_text(content, encoding='utf-8')
    output = os.environ.get('GITHUB_OUTPUT')
    if output:
        with open(output, 'a', encoding='utf-8') as f: f.write('changed=' + ('true' if updates else 'false') + '\n')
    print('Changed files:', ', '.join(str(p.relative_to(ROOT)) for p in updates) or 'none')

if __name__ == '__main__': main()
