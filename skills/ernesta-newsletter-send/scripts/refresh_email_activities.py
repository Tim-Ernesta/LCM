"""Checklist item 13: "delete and re-add emails when you've updated content" for a DRAFT journey, over the API.
Rebuilds every EMAILV2 activity from the CURRENT Content Builder assets: new activity id, emailId, subject, dynamic subject, preheader and name from the asset,
and drops any triggeredSendId/Key snapshot. Keys, branching and everything else stay as they are. Never touches a published journey.
usage: python refresh_email_activities.py <journey name> [--dry-run]"""
import sys,os,uuid,json,copy
sys.path.insert(0,os.path.dirname(__file__)); import sfmc
JN=sys.argv[1]; DRY='--dry-run' in sys.argv
def find(name):
    for pg in range(1,15):
        for i in sfmc.call(f'/interaction/v1/interactions?$pageSize=100&$page={pg}&$orderBy=modifiedDate%20DESC')['items']:
            if i['name']==name: return i
    raise SystemExit('journey not found')
meta=find(JN); j=sfmc.call('/interaction/v1/interactions/'+meta['id'])
if j['status']!='Draft': raise SystemExit(f"refusing: journey status is {j['status']}, not Draft")
def asset(name):
    i=sfmc.call('/asset/v1/content/assets/query',{"page":{"page":1,"pageSize":2},"query":{"property":"name","simpleOperator":"equal","value":name}})['items'][0]['id']; return sfmc.call(f'/asset/v1/content/assets/{i}')
A={v:asset(f'{JN}_{v}') for v in ('VA','VB')}
changes=[]
for a in j['activities']:
    if a['type']!='EMAILV2': continue
    ts=a['configurationArguments']['triggeredSend']; v='VB' if a['key'].endswith('VB') else 'VA'; as_=A[v]
    before=(a['id'],ts['emailId'],ts['emailSubject'],(ts.get('preHeader') or '')[:20],a['configurationArguments'].get('triggeredSendId'))
    a['id']=str(uuid.uuid4()); ts['emailId']=as_['legacyData']['legacyId']
    sub=as_['views']['subjectline']['content']; ts['emailSubject']=ts['dynamicEmailSubject']=sub; a['arguments']['emailSubjectDataBound']=sub
    ts['preHeader']=as_['views']['preheader']['content']; ts['name']=a['name']
    for k in ('triggeredSendId','triggeredSendKey'): a['configurationArguments'].pop(k,None)
    a['configurationArguments']['isModified']=False
    changes.append((a['key'],before[0][:8]+'->'+a['id'][:8],ts['emailId'],v))
for c in changes: print('re-added',c)
if DRY: raise SystemExit('dry run: nothing saved')
o=sfmc.call('/interaction/v1/interactions',j,'PUT'); print('saved:',o['status'],'v',o['version'])
