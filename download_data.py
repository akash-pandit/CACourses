import asyncio
import httpx
import json
import os
from time import sleep
import random

# populate data directory with local copy of all ASSIST 2025 articulations
# any missing articulations are not present in either prefix nor major form
# and are assumed to be missing. In most cases, this is due to schools not
# having an updated agreement.

async def fetch_data(client: httpx.AsyncClient, cc_id: str, uni_id: str):
    """
    Fetch a single articulation agreement from ASSIST and dump the results
    in a new JSON file following the given naming convention:
    
    ./data/{cc_id}/{cc_id}to{uni_id}.json
    
    AllPrefixes endpoint is tried first, with AllMajors endpoint second if
    AllPrefixes fails. If neither works, the articulation is deemed as not
    updated and the function returns without writing to a file
    """
    if os.path.exists(f"./data/{uni_id}/{cc_id}to{uni_id}.json"):
        return
    
    try:
        response = await client.get(f"{cc_id}/to/{uni_id}/AllPrefixes", timeout=30)
        response.raise_for_status()
        result = response.json()
    except httpx.HTTPStatusError:
        try:
            response = await client.get(f"{cc_id}/to/{uni_id}/AllMajors", timeout=30)
            response.raise_for_status()
            result = response.json()
        except httpx.HTTPStatusError:
            print(f"Error fetching {cc_id} -> {uni_id}: {response.status_code} at https://assist.org/transfer/results?year=75&institution={cc_id}&agreement={uni_id}&agreementType=to&view=agreement&viewBy=major&viewSendingAgreements=false")
            return
    
    data = json.loads(result.get("result", {}).get("articulations", "[]"))

    if data:
        if not os.path.isdir(f"./data/{uni_id}"):
            os.mkdir(f"./data/{uni_id}")
        with open(f"./data/{uni_id}/{cc_id}to{uni_id}.json", "w") as fp:
            json.dump(obj=data, fp=fp, indent=2)
    else:
        print(f"No valid data for {cc_id} -> {uni_id}")


async def batch_download_queries(cc_ids: list[str], uni_id: str):
    """
    Asynchronously run fetch_data in batch instances for universities
    """
    os.makedirs(f"./data/{uni_id}", exist_ok=True)

    base_url = "https://assist.org/api/articulation/Agreements?Key=75/"
    async with httpx.AsyncClient(http2=True, base_url=base_url) as client:
        tasks = [fetch_data(client, cc_id, uni_id) for cc_id in cc_ids]
        await asyncio.gather(*tasks)  # run all requests concurrently


def main():
    with open("./data/institutions_cc.json", "r") as cc_fp, open("./data/institutions_state.json", "r") as uni_fp:
        cc_ids, uni_ids = list(json.load(cc_fp).keys()), json.load(uni_fp)
    
    for uni_id, uni_name in uni_ids.items():
        chunks = [cc_ids[i:i+10] for i in range(0, len(cc_ids), 8)]
        for chunk in chunks:
            asyncio.run(batch_download_queries(cc_ids=chunk, uni_id=uni_id))
        
        sleepnum = random.random() * 3 + 2
        print(f"Finished all cc_id -> {uni_id} ({uni_name}), sleeping for {sleepnum:.2f} seconds...")
        sleep(sleepnum)
        

if __name__ == "__main__":
    main()
    