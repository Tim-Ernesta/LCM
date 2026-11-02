"""Minimal SFMC helpers for Sample_Rundown_Content. Reads credentials from env only
(SFMC_CLIENT_ID, SFMC_CLIENT_SECRET, SFMC_AUTH_BASE_URL). Never print or store the token."""
import os, requests
BASE = "https://mclnt213fqhrdcy3jp7h2--3c9jy.rest.marketingcloudapis.com"
DE = "Sample_Rundown_Content"

def token():
    for _ in range(2):  # retry once
        r = requests.post(os.environ["SFMC_AUTH_BASE_URL"].rstrip("/") + "/v2/token", json={
            "grant_type": "client_credentials",
            "client_id": os.environ["SFMC_CLIENT_ID"],
            "client_secret": os.environ["SFMC_CLIENT_SECRET"]}, timeout=60)
        if r.status_code == 200:
            return r.json()["access_token"]
    raise SystemExit(f"token failed: {r.status_code} {r.text[:200]}")

def hdr(t): return {"Authorization": "Bearer " + t}

def pull_all(t):
    """Return {'Style|Color': values-dict} for every row (lower-cased field names)."""
    rows, p = [], 1
    while True:
        j = requests.get(f"{BASE}/data/v1/customobjectdata/key/{DE}/rowset?$pageSize=100&$page={p}",
                         headers=hdr(t), timeout=120).json()
        rows += j["items"]; p += 1
        if len(rows) >= j["count"] or not j["items"]:
            break
    return {x["keys"]["style"] + "|" + x["keys"]["color"]: x["values"] for x in rows}

def upsert(t, items):
    """items: [{'keys': {'Style':..,'Color':..}, 'values': {'ReviewQuote':..,...}}]; retries once."""
    for _ in range(2):
        r = requests.post(f"{BASE}/hub/v1/dataevents/key:{DE}/rowset", headers=hdr(t), json=items, timeout=120)
        if r.status_code < 300:
            return r
    raise SystemExit(f"upsert failed: {r.status_code} {r.text[:200]}")
