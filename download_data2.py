#!/usr/bin/python

import asyncio
import httpx
import json
import os
import time

"""
Asynchronously download requests from ASSIST.org's API
without getting rate limited (50 every 5 minutes)

Data is queried from ASSIST's 2024-2025 academic year
agreements. Missing articulation files are due to missing
agreements between the institutions for the academic
year.
"""

async def fetch_data(client: httpx.AsyncClient, cc: str, uni: str, query_type, overflow: list, overflow_query_type: str) -> None:
    url_ext = f"{cc}/to/{uni}/{query_type}"
    # print("[Status] Querying", url_ext)
    response = await client.get(url_ext, timeout=30)

    while response.status_code == 429:
        print(f"[Status] {cc=} and {uni=} hit status=429, sleeping 5 minutes...")
        time.sleep(5*60 + 1)
        response = await client.get(url_ext, timeout=30)

    if response.status_code != 200:
        f"Error fetching {cc} -> {uni}: {response.status_code} at https://assist.org/transfer/results?year=75&institution={cc}&agreement={uni}&agreementType=to&view=agreement&viewBy=major&viewSendingAgreements=false"
        overflow.append((cc, uni, overflow_query_type))
        return

    data = json.loads(response.json().get("result", {}).get("articulations", "[]"))
    if data:
        if not os.path.isdir(f"./data/{uni}"):
            os.mkdir(f"./data/{uni}")
        with open(f"./data/{uni}/{cc}to{uni}.json", "w") as fp:
            json.dump(obj=data, fp=fp, indent=2)
    else:
        print(f"No valid data for {cc} -> {uni}")


async def main():
    with open("./data/institutions_cc.json", "r") as cc_fp:
        ccs = json.load(cc_fp)
    with open("./data/institutions_state.json", "r") as uni_fp:
        unis = json.load(uni_fp)

    query_args = [
        (cc, uni, "AllPrefixes") for uni in unis.keys() 
        for cc in ccs.keys() 
        if not os.path.exists(f"./data/{uni}/{cc}to{uni}.json")
    ]
    
    query_args = [query_args[i:i+50] for i in range(0, len(query_args), 50)]
    if not query_args:
        return

    overflow = query_args[:-1]
    query_args.pop()

    base_url = "https://assist.org/api/articulation/Agreements?Key=75/"
    async with httpx.AsyncClient(http2=True, base_url=base_url) as client:
        
        for i, batch in enumerate(query_args):
            if i < 8:
                continue
            queries = [fetch_data(client, cc, uni, query_type, overflow, "AllDepartments") for cc, uni, query_type in batch]
            await asyncio.gather(*queries)
            lt = time.localtime(time.time())
            print(f"[{lt.tm_hour}:{lt.tm_min}:{lt.tm_sec}] Completed batch {i+1} of {len(query_args)}, sleeping for 5 minutes...")
            time.sleep(5*60 + 1)
            
        query_args = [overflow[i:i+50] for i in range(0, len(overflow), 50)]
        
        if query_args:
            overflow = query_args[:-1]
            query_args.pop()
        
        for i, batch in enumerate(query_args):
            queries = [fetch_data(client, cc, uni, query_type, overflow, "AllMajors") for cc, uni, query_type in batch]
            await asyncio.gather(*queries)
            lt = time.localtime(time.time())
            print(f"[{lt.tm_hour}:{lt.tm_min}:{lt.tm_sec}] Completed batch {i+1} of {len(query_args)}, sleeping for 5 minutes...")
            time.sleep(5*60 + 1)

        query_args = [overflow[i:i+50] for i in range(0, len(overflow), 50)]
        
        if query_args:
            overflow = query_args[:-1]
            query_args.pop()
        error_list = []

        for i, batch in enumerate(overflow):
            queries = [fetch_data(client, cc, uni, query_type, error_list, "Error") for cc, uni, query_type in batch]
            await asyncio.gather(*queries)
            print(f"[{lt.tm_hour}:{lt.tm_min}:{lt.tm_sec}] Completed final batch of queries")


if __name__ == "__main__":
    asyncio.run(main())