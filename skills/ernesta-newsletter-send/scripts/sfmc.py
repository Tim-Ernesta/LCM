"""SFMC REST helper. Credentials come from the Claude environment: SFMC_AUTH_BASE_URL, SFMC_CLIENT_ID, SFMC_CLIENT_SECRET.
Never print the secret. Tokens last ~18 minutes: call token() again on a 401."""
import os,json,urllib.request,urllib.parse,time,concurrent.futures as cf
_state={}
def token():
    body=json.dumps({'grant_type':'client_credentials','client_id':os.environ['SFMC_CLIENT_ID'],'client_secret':os.environ['SFMC_CLIENT_SECRET']}).encode()
    r=urllib.request.Request(os.environ['SFMC_AUTH_BASE_URL'].rstrip('/')+'/v2/token',data=body,headers={'Content-Type':'application/json'})
    d=json.load(urllib.request.urlopen(r)); _state.update(d); _state['t']=time.time(); return d
def call(path,body=None,method=None):
    if 't' not in _state or time.time()-_state['t']>900: token()
    h={'Authorization':'Bearer '+_state['access_token'],'Content-Type':'application/json'}
    r=urllib.request.Request(_state['rest_instance_url'].rstrip('/')+path,data=json.dumps(body).encode() if body is not None else None,headers=h,method=method or ('POST' if body is not None else 'GET'))
    raw=urllib.request.urlopen(r).read(); return json.loads(raw) if raw[:1] in b'{[' else raw
def de_meta(name):
    for i in call('/data/v1/customobjects?$search='+urllib.parse.quote(name)+'&$pageSize=20')['items']:
        if i['name']==name: return i
def rows(name,size=2500,threads=8):
    """All rows of a data extension, field names lower-cased (what the REST rowset returns)."""
    m=de_meta(name); n=m.get('rowCount') or 0; key=urllib.parse.quote(m['key'])
    def one(p):
        for _ in range(3):
            try:
                r=call(f'/data/v1/customobjectdata/key/{key}/rowset?$pageSize={size}&$page={p}'); return [{**x['keys'],**x['values']} for x in r['items']]
            except Exception: time.sleep(2)
        raise RuntimeError('rowset failed '+name)
    with cf.ThreadPoolExecutor(threads) as ex: out=list(ex.map(one,range(1,(n+size-1)//size+1)))
    return [r for pg in out for r in pg]
def upsert_rows(key,items):
    return call(f'/data/v1/async/dataextensions/key:{key}/rows',{'items':items},'PUT')
