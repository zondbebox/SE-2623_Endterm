from concurrent.futures import ThreadPoolExecutor
import http.cookiejar,urllib.request,urllib.parse,re,sqlite3,time,json,math,threading
from pathlib import Path
ROOT=Path(__file__).resolve().parent
(ROOT.parent/'Evidence').mkdir(parents=True,exist_ok=True)
DB=ROOT/'data/campus.sqlite3'
with sqlite3.connect(DB) as c: accounts=[r[0] for r in c.execute('SELECT email FROM users ORDER BY id LIMIT 10')]
clients=[]
for email in accounts:
    opener=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
    with opener.open('http://127.0.0.1:5055/login') as r: html=r.read().decode()
    token=re.search(r'name="csrf" value="([^"]+)"',html).group(1)
    data=urllib.parse.urlencode({'email':email,'password':'CampusDemo!2026','csrf':token}).encode()
    with opener.open('http://127.0.0.1:5055/login',data=data) as r:
        assert r.status==200 and r.url.endswith('/')
    clients.append(opener)
barrier=threading.Barrier(10)
def run(opener):
    barrier.wait();timings=[]
    for i in range(10):
        start=time.perf_counter()
        with opener.open('http://127.0.0.1:5055/?q=notebook',timeout=10) as r:
            body=r.read();assert r.status==200 and b'Open notice' in body
        timings.append((time.perf_counter()-start)*1000)
    return timings
with ThreadPoolExecutor(max_workers=10) as pool: times=sorted(t for group in pool.map(run,clients) for t in group)
result={'users':10,'requests':100,'p95_ms':round(times[math.ceil(.95*len(times))-1],3),'max_ms':round(max(times),3),'median_ms':round((times[49]+times[50])/2,3),'threshold_ms':2000,'pass_under_test_conditions':times[94]<=2000,'method':'10 authenticated sessions, 10 sequential searches per session; 10 workers synchronised at start; real loopback HTTP, server-rendered HTML fully received. Asset loads and browser painting excluded; no network throttling.','limits':'This verifies local HTTP search response latency only, not end-to-end browser display under 10 throttled mobile users.','sorted_ms':[round(t,3) for t in times]}
(ROOT.parent/'Evidence/search_performance.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in result.items() if k!='sorted_ms'},indent=2))


