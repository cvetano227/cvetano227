import os, json, urllib.request, datetime, html, pathlib

USER = 'cvetano227'
TOKEN = os.environ.get('GH_TOKEN') or os.environ.get('GITHUB_TOKEN')
if not TOKEN:
    raise SystemExit('Missing GH_TOKEN / GITHUB_TOKEN. Run from GitHub Actions.')

def request(url, data=None):
    headers = {'Authorization': f'Bearer {TOKEN}', 'Accept':'application/vnd.github+json', 'User-Agent':'golevelbeyond-readme-dashboard', 'X-GitHub-Api-Version':'2022-11-28'}
    if data is not None:
        headers['Content-Type'] = 'application/json'
        data = json.dumps(data).encode()
    req = urllib.request.Request(url, data=data, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)

query = '''query($login:String!) { user(login:$login) { login followers { totalCount } contributionsCollection { contributionCalendar { totalContributions weeks { contributionDays { date contributionCount contributionLevel } } } } } }'''
graph = request('https://api.github.com/graphql', {'query':query,'variables':{'login':USER}})
if graph.get('errors') or not graph.get('data',{}).get('user'):
    raise RuntimeError('GraphQL failed: '+str(graph.get('errors',graph)))
user = graph['data']['user']
calendar = user['contributionsCollection']['contributionCalendar']
followers = user['followers']['totalCount']
repos = []
page = 1
while True:
    batch = request(f'https://api.github.com/users/{USER}/repos?type=owner&per_page=100&page={page}')
    if not isinstance(batch,list): raise RuntimeError('Repositories API returned unexpected response')
    repos.extend(r for r in batch if not r['fork'] and not r['private'])
    if len(batch)<100: break
    page+=1
    if page>30: raise RuntimeError('Unexpectedly many repository pages')
stars = sum(r['stargazers_count'] for r in repos)
repo_count = len(repos)
total = calendar['totalContributions']
weeks = calendar['weeks']

# Palette based on GoLevelBeyond homepage: deep navy and violet/lavender.
BG='#0D1220'; PANEL='#141B2D'; BORDER='#303653'; WHITE='#F4F2FF'; MUTED='#A7B0C8'; ACCENT='#9472F4'; LAVENDER='#C8A8FF'
LEVEL={'NONE':'#23283B','FIRST_QUARTILE':'#45346F','SECOND_QUARTILE':'#6746A6','THIRD_QUARTILE':'#8C66E8','FOURTH_QUARTILE':'#C39CFF'}
W,H=1040,304
parts=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="GitHub contribution dashboard for {USER}">',f'<rect width="{W}" height="{H}" rx="18" fill="{BG}"/>',f'<rect x="1" y="1" width="{W-2}" height="{H-2}" rx="17" fill="none" stroke="{BORDER}"/>']
def text(x,y,t,size=15,color=WHITE,weight=400,anchor='start'):
    parts.append(f'<text x="{x}" y="{y}" font-family="Arial, Helvetica, sans-serif" font-size="{size}" font-weight="{weight}" fill="{color}" text-anchor="{anchor}">{html.escape(str(t))}</text>')
text(28,39,'GitHub',24,WHITE,700)
text(113,39,'Activity',24,LAVENDER,700)
text(1012,37,'@'+USER,14,MUTED,500,'end')
text(28,61,'Building, shipping and improving.',12,MUTED)
metrics=[('CONTRIBUTIONS',total),('PUBLIC REPOS',repo_count),('TOTAL STARS',stars),('FOLLOWERS',followers)]
for i,(label,value) in enumerate(metrics):
    x=28+i*253
    parts.append(f'<rect x="{x}" y="78" width="238" height="77" rx="12" fill="{PANEL}" stroke="{BORDER}"/>')
    text(x+16,106,label,11,MUTED,700)
    text(x+16,140,f'{value:,}',28,WHITE,700)
text(28,185,'Contribution calendar',15,WHITE,700)
text(1012,185,'Last 12 months',11,MUTED,400,'end')
# GitHub supplies weeks in Sunday-to-Saturday order, including partial edge weeks.
cell=11; gap=4; start_x=88; start_y=204
for i,week in enumerate(weeks):
    for day in week['contributionDays']:
        weekday=(datetime.date.fromisoformat(day['date']).weekday()+1)%7
        x=start_x+i*(cell+gap); y=start_y+weekday*(cell+gap)
        fill=LEVEL.get(day['contributionLevel'],LEVEL['NONE'])
        parts.append(f'<rect x="{x}" y="{y}" width="{cell}" height="{cell}" rx="3" fill="{fill}"><title>{html.escape(day["date"])}: {day["contributionCount"]} contributions</title></rect>')
for d,lab in [(1,'Mon'),(3,'Wed'),(5,'Fri')]: text(28,start_y+d*15+10,lab,11,MUTED)
text(879,294,'Less',10,MUTED)
for i,c in enumerate(LEVEL.values()): parts.append(f'<rect x="{908+i*17}" y="284" width="12" height="12" rx="3" fill="{c}"/>')
text(1012,294,'More',10,MUTED,400,'end')
parts.append('</svg>')
out=pathlib.Path('assets/github-dashboard.svg');out.parent.mkdir(parents=True,exist_ok=True);out.write_text('\n'.join(parts),encoding='utf-8')
print(f'Generated {out}: {total} contributions, {repo_count} public non-fork repositories, {stars} stars, {followers} followers')
