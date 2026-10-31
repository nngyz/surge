#!/usr/bin/env python3
"""Update MagicRule-owned sections while preserving custom rules."""
from __future__ import annotations
import hashlib, json, os, re, sys
from pathlib import Path
from urllib.request import Request, urlopen

INDEX_URL = "https://magicrule.pages.dev/data/index/Surge.json"
ROOT = Path(__file__).resolve().parents[1]
RULES = ROOT / "rules"
MAPPING = {"B+Y.list": {"Boc": "BOC"}, "G+S+Y+O.list": {"Spotify": "Spotify", "Gemini": "Gemini", "Google": "Google", "Github": "GitHub", "YouTube": "YouTube", "OpenAi": "OpenAI"}, "T+T.list": {"TikTok": "TikTok"}, "E+M.list": {"Emby": "Emby"}}

def get(url):
    req = Request(url, headers={"User-Agent": "magicrule-sync/1.0"})
    with urlopen(req, timeout=60) as r: return r.read()

def normal_name(s): return re.sub(r"[^a-z0-9]", "", s.lower())

def load_catalog():
    data=json.loads(get(INDEX_URL)); out={}
    for x in data["rules"]:
        if x.get("name"): out[normal_name(x["name"])] = x
    for x in data["rules"]:
        if x.get("chinese_name") and normal_name(x["chinese_name"]) not in out: out[normal_name(x["chinese_name"])] = x
    return out

def latest(item):
    m=json.loads(get(item["manifest"])); a=m.get("artifacts",[])
    x=next((z for z in a if z.get("recommended") and z.get("ext")=="list"),None) or next((z for z in a if z.get("role")=="full" and z.get("ext")=="list"),None)
    if not x: raise RuntimeError("No full list for "+item.get("name","unknown"))
    return x["url"],m

def update(path, sections, fetched):
    old=path.read_text(encoding="utf-8") if path.exists() else ""; lines=old.replace("\r\n","\n").replace("\r","\n").splitlines()
    markers=[(i,l[1:].strip()) for i,l in enumerate(lines) if l.startswith("#")]
    for marker,name in sections.items():
        hit=[i for i,label in markers if label==marker]
        if not hit: print("WARN missing #"+marker,file=sys.stderr); continue
        start=hit[0]; ends=[i for i,_ in markers if i>start]; end=ends[0] if ends else len(lines)
        lines=lines[:start+1]+fetched[name][0]+lines[end:]
        markers=[(i,l[1:].strip()) for i,l in enumerate(lines) if l.startswith("#")]
    new="\n".join(lines).rstrip()+"\n"
    if new!=old: path.write_text(new,encoding="utf-8"); return True
    return False

def main():
    catalog=load_catalog(); fetched={}
    for ss in MAPPING.values():
        for name in ss.values():
            if name in fetched: continue
            item=catalog.get(normal_name(name))
            if not item: raise RuntimeError("MagicRule rule not found: "+name)
            url,m=latest(item); raw=get(url); fetched[name]=(raw.decode("utf-8").replace("\r\n","\n").replace("\r","\n").rstrip("\n").split("\n"),url,m)
            print(name+": "+str(m.get("rule_updated_at"))+" -> "+url)
    changed=[]
    for fn,ss in MAPPING.items():
        if update(RULES/fn,ss,fetched): changed.append(str((RULES/fn).relative_to(ROOT)))
    Path(os.environ.get("GITHUB_OUTPUT","/tmp/magicrule-output")).write_text("changed="+("true" if changed else "false")+"\nfiles="+",".join(changed)+"\n")
    print("Changed files: "+(", ".join(changed) if changed else "none"))

if __name__ == "__main__": main()
