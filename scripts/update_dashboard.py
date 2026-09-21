"""Build profile SVGs from public GitHub data. Python standard library only."""
import json
import math
import os
from collections import Counter
from datetime import datetime, timezone
from html import escape
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
USER = "benjaguerra192"
COLORS = ["#58a6ff", "#bc8cff", "#79c0ff", "#d29922", "#f778ba", "#8b949e"]


def api(path):
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "benjaguerra192-profile"}
    if os.environ.get("GH_TOKEN"):
        headers["Authorization"] = "Bearer " + os.environ["GH_TOKEN"]
    with urlopen(Request("https://api.github.com/" + path, headers=headers), timeout=30) as response:
        return json.load(response)


def collect():
    user = api(f"users/{USER}")
    repos = []
    page = 1
    while True:
        batch = api(f"users/{USER}/repos?type=owner&per_page=100&page={page}")
        repos.extend(repo for repo in batch if not repo["private"])
        if len(batch) < 100:
            break
        page += 1
    own = [repo for repo in repos if not repo["fork"]]
    languages = Counter()
    for repo in own:
        # Generated profile graphics must not skew code-language percentages.
        if repo["name"] != USER:
            languages.update(api(f"repos/{USER}/{repo['name']}/languages"))
    return {
        "updated_at": datetime.now(timezone.utc).strftime("%d/%m/%Y · %H:%M UTC"),
        "public_repos": len(repos), "original_repos": len(own),
        "forked_repos": len(repos) - len(own),
        "stars": sum(repo["stargazers_count"] for repo in own),
        "forks": sum(repo["forks_count"] for repo in own),
        "followers": user["followers"], "following": user["following"],
        "languages": dict(languages.most_common()),
    }


def text(x, y, value, size=20, color="#e6edf3", weight=400, anchor="start"):
    return f'<text x="{x}" y="{y}" font-size="{size}" fill="{color}" font-weight="{weight}" text-anchor="{anchor}">{escape(str(value))}</text>'


def panel(x, y, width, height):
    return f'<rect x="{x}" y="{y}" width="{width}" height="{height}" rx="22" fill="#161b22" stroke="#30363d"/>'


def donut(cx, cy, radius, values, center, subtitle):
    parts = [f'<circle cx="{cx}" cy="{cy}" r="{radius}" fill="none" stroke="#30363d" stroke-width="25"/>']
    total = sum(value for _, value in values)
    circumference = 2 * math.pi * radius
    offset = 0
    for index, (_, value) in enumerate(values):
        if total and value:
            length = value / total * circumference
            parts.append(f'<circle cx="{cx}" cy="{cy}" r="{radius}" fill="none" stroke="{COLORS[index % len(COLORS)]}" stroke-width="25" stroke-dasharray="{length:.4f} {circumference - length:.4f}" stroke-dashoffset="{-offset:.4f}" transform="rotate(-90 {cx} {cy})"/>')
            offset += length
    parts += [text(cx, cy + 6, center, 37, weight=700, anchor="middle"), text(cx, cy + 35, subtitle, 15, "#8b949e", anchor="middle")]
    return "".join(parts)


def language_values(data):
    items = list(data["languages"].items())
    if len(items) > 5:
        items = items[:5] + [("Otros", sum(value for _, value in items[5:]))]
    return items


def languages_card(data, x, y, width):
    values = language_values(data)
    total = sum(value for _, value in values)
    top_percent = f"{values[0][1]/total:.0%}" if total else "—"
    p = [panel(x,y,width,402), text(x+25,y+36,"LENGUAJES",16,"#8b949e",600)]
    p += [donut(x+width/2,y+154,76,values,top_percent,values[0][0] if values else "Sin código")]
    for i,(name,value) in enumerate(values):
        lx = x+25+(i%2)*(width/2-8)
        ly = y+277+(i//2)*32
        p += [f'<circle cx="{lx+4}" cy="{ly-5}" r="4" fill="{COLORS[i]}"/>',text(lx+16,ly,f"{name} {value/total:.1%}",15)]
    p += [text(x+25,y+378,"Por bytes · sin forks ni perfil",13,"#8b949e")]
    return "".join(p)


def repos_card(data,x,y,width):
    values=[("Originales",data["original_repos"]),("Forks",data["forked_repos"])]
    p=[panel(x,y,width,402),text(x+25,y+36,"REPOSITORIOS",16,"#8b949e",600),donut(x+width/2,y+154,76,values,data["public_repos"],"públicos")]
    for i,(name,value) in enumerate(values):
        ly=y+281+i*35
        p += [f'<circle cx="{x+29}" cy="{ly-5}" r="5" fill="{COLORS[i]}"/>',text(x+45,ly,name,18),text(x+width-28,ly,value,20,weight=700,anchor="end")]
    p += [text(x+25,y+378,"Incluye este repositorio de perfil",13,"#8b949e")]
    return "".join(p)


def counters(data,x,y,width):
    p=[panel(x,y,width,198),text(x+25,y+37,"EN NÚMEROS",16,"#8b949e",600)]
    columns=[("stars","Estrellas"),("forks","Forks recibidos"),("followers","Seguidores"),("following","Siguiendo")]
    for i,(key,label) in enumerate(columns):
        cx=x+width*(i+.5)/4
        p += [text(cx,y+98,data[key],39,"#58a6ff",700,"middle"),text(cx,y+130,label,15,"#e6edf3",anchor="middle")]
    p += [text(x+25,y+174,"Estrellas y forks de repositorios originales públicos",13,"#8b949e")]
    return "".join(p)


def render(data,mobile=False):
    width,height=(480,1170) if mobile else (950,664)
    p=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">', '<title id="title">Benja Guerra · GitHub dashboard</title>',f'<desc id="desc">{data["public_repos"]} repositorios públicos, {data["stars"]} estrellas, {data["forks"]} forks recibidos y {data["followers"]} seguidores. Actualizado {escape(data["updated_at"])}.</desc>', '<g font-family="Segoe UI,Arial,sans-serif">',f'<rect width="{width}" height="{height}" rx="26" fill="#0d1117"/>']
    if mobile:
        p += [languages_card(data,20,20,440),repos_card(data,20,438,440),panel(20,856,440,294),text(45,894,"EN NÚMEROS",18,"#8b949e",600)]
        for i,(key,label) in enumerate([("stars","Estrellas"),("forks","Forks recibidos"),("followers","Seguidores"),("following","Siguiendo")]):
            cx=130+(i%2)*220
            cy=946+(i//2)*94
            p += [text(cx,cy,data[key],37,"#58a6ff",700,"middle"),text(cx,cy+30,label,19,anchor="middle")]
        p += [text(45,1125,"Estrellas y forks: originales públicos",16,"#8b949e")]
    else:
        p += [languages_card(data,24,24,443),repos_card(data,483,24,443),counters(data,24,442,902)]
    p += ['</g></svg>']
    return "".join(p)


def main():
    data=collect()
    # Generate only after every API call succeeds, keeping the last good dashboard on failure.
    assets=ROOT/"assets"
    assets.mkdir(exist_ok=True)
    for mobile in (False,True):
        (assets/("dashboard-mobile.svg" if mobile else "dashboard.svg")).write_text(render(data,mobile),encoding="utf-8")
    (assets/"stats.json").write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(f"Updated {data['public_repos']} public repos, {len(data['languages'])} languages")


if __name__ == "__main__":
    main()
