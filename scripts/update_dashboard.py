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


def contributions():
    query = '{ user(login: "' + USER + '") { contributionsCollection { contributionCalendar { totalContributions weeks { contributionDays { date weekday contributionCount contributionLevel } } } } } }'
    headers = {"Authorization": "Bearer " + os.environ["GH_TOKEN"], "Content-Type": "application/json", "User-Agent": "profile-dashboard"}
    request = Request("https://api.github.com/graphql", data=json.dumps({"query": query}).encode(), headers=headers)
    with urlopen(request, timeout=30) as response:
        result = json.load(response)
    if result.get("errors"):
        raise RuntimeError("GitHub could not return contribution data")
    return result["data"]["user"]["contributionsCollection"]["contributionCalendar"]


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
    p = [panel(x,y,width,280),text(x+24,y+34,"LENGUAJES",16,"#8b949e",600)]
    p += [donut(x+116,y+146,70,values,f"{values[0][1]/total:.0%}" if total else "—",values[0][0] if values else "Sin código")]
    for i,(name,value) in enumerate(values):
        ly=y+76+i*29
        p += [f'<circle cx="{x+227}" cy="{ly-5}" r="4" fill="{COLORS[i]}"/>',text(x+240,ly,f"{name} {value/total:.1%}",17)]
    p += [text(x+24,y+260,"Por bytes · sin forks ni perfil",14,"#8b949e")]
    return "".join(p)


def repos_card(data,x,y,width):
    values=[("Originales",data["original_repos"]),("Forks",data["forked_repos"])]
    p=[panel(x,y,width,280),text(x+24,y+34,"REPOSITORIOS",16,"#8b949e",600),donut(x+116,y+146,70,values,data["public_repos"],"públicos")]
    for i,(name,value) in enumerate(values):
        ly=y+125+i*43
        p += [f'<circle cx="{x+227}" cy="{ly-5}" r="5" fill="{COLORS[i]}"/>',text(x+240,ly,f"{name}  {value}",20)]
    p += [text(x+24,y+260,"Incluye el repositorio de perfil",14,"#8b949e")]
    return "".join(p)


def activity_days(data):
    return [day for week in data.get("contributions",{}).get("weeks",[]) for day in week["contributionDays"]]


def calendar_card(data,x,y,width):
    cal=data.get("contributions",{"totalContributions":0,"weeks":[]})
    p=[panel(x,y,width,280),text(x+24,y+34,"CONTRIBUCIONES",16,"#8b949e",600),text(x+24,y+74,f"{cal['totalContributions']} en los últimos 12 meses",23,weight=600)]
    weeks=cal["weeks"]
    step=(width-48)/max(len(weeks),1)
    size=min(step-2,16)
    shades={"NONE":"#21262d","FIRST_QUARTILE":"#16345b","SECOND_QUARTILE":"#225b9d","THIRD_QUARTILE":"#388bfd","FOURTH_QUARTILE":"#79c0ff"}
    last_month=None
    months=["Ene","Feb","Mar","Abr","May","Jun","Jul","Ago","Sep","Oct","Nov","Dic"]
    for i,week in enumerate(weeks):
        for day in week["contributionDays"]:
            dx=x+24+i*step
            dy=y+119+day["weekday"]*18
            if day["date"][8:]=="01" and i<len(weeks)-2:
                month=int(day["date"][5:7])
                if month != last_month:
                    p += [text(dx,y+108,months[month-1],12,"#8b949e")]
                    last_month=month
            title=escape(f"{day['date']}: {day['contributionCount']} contribuciones")
            p += [f'<rect x="{dx:.2f}" y="{dy}" width="{size:.2f}" height="{size:.2f}" rx="2" fill="{shades[day["contributionLevel"]]}"><title>{title}</title></rect>']
    p += [text(x+24,y+259,"Actividad registrada por GitHub",13,"#8b949e"),text(x+width-152,y+259,"Menos",12,"#8b949e")]
    for i,color in enumerate(shades.values()):
        p += [f'<rect x="{x+width-111+i*14}" y="{y+249}" width="11" height="11" rx="2" fill="{color}"/>']
    p += [text(x+width-34,y+259,"Más",12,"#8b949e")]
    return "".join(p)


def activity_card(data,x,y,width):
    days=activity_days(data)
    active=sum(day["contributionCount"]>0 for day in days)
    p=[panel(x,y,width,280),text(x+24,y+34,"ACTIVIDAD Y COMUNIDAD",16,"#8b949e",600),donut(x+96,y+139,55,[("Activos",active),("Sin actividad",len(days)-active)],active,""),text(x+96,y+228,"días activos",16,"#8b949e",anchor="middle"),f'<path d="M{x+179} {y+66}V{y+228}" stroke="#30363d"/>']
    for i,(key,label) in enumerate([("stars","Estrellas"),("forks","Forks"),("followers","Seguidores"),("following","Siguiendo")]):
        p += [text(x+199,y+91+i*40,label,17,"#8b949e"),text(x+width-24,y+91+i*40,data[key],21,weight=600,anchor="end")]
    p += [text(x+24,y+259,"Días activos en los últimos 12 meses",13,"#8b949e")]
    return "".join(p)


def render(data,mobile=False):
    width,height=(436,1220) if mobile else (1164,632)
    p=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">','<title id="title">Benja Guerra · GitHub dashboard</title>',f'<desc id="desc">Lenguajes, repositorios, contribuciones y comunidad. Actualizado {escape(data["updated_at"])}.</desc>','<g font-family="Segoe UI,Arial,sans-serif">',f'<rect width="{width}" height="{height}" rx="24" fill="#0d1117"/>']
    if mobile:
        p += [languages_card(data,20,20,396),repos_card(data,20,320,396),calendar_card(data,20,620,396),activity_card(data,20,920,396)]
    else:
        p += [languages_card(data,24,24,550),repos_card(data,590,24,550),calendar_card(data,24,328,654),activity_card(data,694,328,446)]
    return "".join(p)+"</g></svg>"



def main():
    data=collect()
    data['contributions']=contributions()
    # Generate only after every API call succeeds, keeping the last good dashboard on failure.
    assets=ROOT/"assets"
    assets.mkdir(exist_ok=True)
    for mobile in (False,True):
        (assets/("dashboard-mobile.svg" if mobile else "dashboard.svg")).write_text(render(data,mobile),encoding="utf-8")
    (assets/"stats.json").write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(f"Updated {data['public_repos']} public repos, {len(data['languages'])} languages")


if __name__ == "__main__":
    main()
