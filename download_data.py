#!/usr/bin/python

import asyncio
import httpx
import json
import os
import time
import sys

"""
Asynchronously download requests from ASSIST.org's API
without getting rate limited (50 every 5 minutes)

Data is queried from ASSIST's 2024-2025 academic year
agreements. Missing articulation files are due to missing
agreements between the institutions for the academic
year.
"""

def curtime() -> str:
    lt = time.localtime(time.time())
    return f"{lt.tm_hour:02}:{lt.tm_min:02}:{lt.tm_sec:02}"


async def fetch_data(
        client: httpx.AsyncClient,
        cc: str,
        uni: str,
        query_type: str,
        overflow: list,
        overflow_query_type: str,
        err400tracker: list
    ) -> None:
    url_ext = f"{cc}/to/{uni}/{query_type}"
    # print("[Status] Querying", url_ext)
    response = None
    try:
        response = await client.get(url_ext, timeout=30)
        if response is None:
            raise RuntimeError("Error: client.get returned None...")

        while response.status_code == 429:
            print(f"[Status] {cc=} and {uni=} hit status=429, sleeping 5 minutes...")
            await asyncio.sleep(5*60 + 1)
            response = await client.get(url_ext, timeout=30)

        if response.status_code != 200:
            print(f"Error fetching {cc}>{uni}: {response.status_code} at https://assist.org/transfer/results?year=75&institution={cc}&agreement={uni}&agreementType=to&view=agreement&viewBy=major&viewSendingAgreements=false", file=sys.stderr)
            overflow.append((cc, uni, overflow_query_type))

            if response.status_code == 400:
                err400tracker.append(f"{cc},{uni}")

            return
        
    except httpx.ReadTimeout:
        overflow.append((cc, uni, query_type))
        print(f"[Status] Fetching {cc=}, {uni=}, {query_type=} timed out, pushing to overflow") 
    
    except httpx.RequestError as err:
        print(f"[Status] Uncaught error {err=} with {cc=} {uni=} {query_type=}")
        exit(1)

    json_response = response.json()
    data = json.loads(json_response.get("result", {}).get("articulations", []))
    if data:
        os.makedirs(f"./data/{uni}", exist_ok=True)
        with open(f"./data/{uni}/{cc}to{uni}-{query_type[3:].lower()}.json", "w") as fp:
            json.dump(obj=data, fp=fp, indent=2)
    else:
        print(f"No valid data for {cc} -> {uni}", file=sys.stderr)


async def main():
    BASE_URL = "https://assist.org/api/articulation/Agreements?Key=75/"

    # Read in institution:id mappings
    with open("./data/institutions_cc.json", "r") as cc_fp:
        ccs = json.load(cc_fp)
    with open("./data/institutions_state.json", "r") as uni_fp:
        unis = json.load(uni_fp)

    skip_agreements_fp = "skipread.csv"
    if not os.path.exists(skip_agreements_fp):
        with open(skip_agreements_fp, 'x') as fp:
            pass
    with open(skip_agreements_fp) as fp:
        skip_agreements = set(fp.read().strip().split("\n"))
    # 
    overflow = [
        (cc, uni, "AllPrefixes") for uni in sorted([int(k) for k in unis.keys()]) 
        for cc in sorted([int(k) for k in ccs.keys()])
        if not os.path.exists(f"data/{uni}/{cc}to{uni}-prefixes.json")
        and not os.path.exists(f"data/{uni}/{cc}to{uni}-departments.json")
        and not os.path.exists(f"data/{uni}/{cc}to{uni}-majors.json")
        and f"{cc},{uni}" not in skip_agreements
    ]

    skip_agreements_fp = "skipread.csv"
    if not os.path.exists(skip_agreements_fp):
        with open(skip_agreements_fp, 'x') as fp:
            pass
    with open(skip_agreements_fp) as fp:
        skip_agreements = fp.read().strip().split("\n")

    async with httpx.AsyncClient(http2=True, base_url=BASE_URL) as client:

        for overflow_query_type in ("AllDepartments", "AllMajors", "Error"):
            query_args = [overflow[i:i+50] for i in range(0, len(overflow), 50)]
            overflow = []

            if not query_args:
                continue
    
            for i, batch in enumerate(query_args):
                queries = [
                    fetch_data(client, cc, uni, query_type, overflow, overflow_query_type, skip_agreements)
                    for cc, uni, query_type in batch
                ]
                await asyncio.gather(*queries)

                with open(skip_agreements_fp, "w") as fp:
                    fp.write('\n'.join(skip_agreements))

                print(f"[{curtime()}] Completed run {i+1} batch {i+1} of {len(query_args)}, sleeping for 5 minutes...")
                await asyncio.sleep(5*60 + 1)

                


if __name__ == "__main__":
    asyncio.run(main())