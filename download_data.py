import asyncio
import httpx
import json
import os

# populate data directory with local copy of all ASSIST 2025 articulations
# any missing articulations are not present in either prefix nor major form
# and are assumed to be missing. In most cases, this is due to schools not
# having an updated agreement.

async def fetch_data(client, cc_id, uni_id):
    """
    Fetch a single articulation agreement from ASSIST and dump the results
    in a new JSON file following the given naming convention:
    
    ./data/{cc_id}/{cc_id}to{uni_id}.json
    
    AllPrefixes endpoint is tried first, with AllMajors endpoint second if
    AllPrefixes fails. If neither works, the articulation is deemed as not
    updated and the function returns without writing to a file
    """
    try:
        response = await client.get(f"{uni_id}/AllPrefixes")
        response.raise_for_status()
        result = response.json()
    except httpx.HTTPStatusError as e:
        try:
            response = await client.get(f"{uni_id}/AllMajors")
            response.raise_for_status()
            result = response.json()
        except httpx.HTTPStatusError as e:
            print(f"Error fetching {cc_id} -> {uni_id}: {e}")
            return
    
    data = json.loads(result.get("result", {}).get("articulations", "[]"))

    if data:
        with open(f"./data/{cc_id}/{cc_id}to{uni_id}.json", "w") as fp:
            json.dump(obj=data, fp=fp, indent=2)
    else:
        print(f"No valid data for {cc_id} -> {uni_id}")


async def batch_download_queries(cc_id: str, uni_ids: list[str]):
    """
    Asynchronously run fetch_data in batch instances for universities
    """
    os.makedirs(f"./data/{cc_id}", exist_ok=True)

    base_url = f"https://assist.org/api/articulation/Agreements?Key=75/{cc_id}/to/"
    async with httpx.AsyncClient(http2=True, base_url=base_url) as client:
        tasks = [fetch_data(client, cc_id, uni_id) for uni_id in uni_ids]
        await asyncio.gather(*tasks)  # run all requests concurrently


def main():
    with open("./data/institutions_cc.json", "r") as cc_fp, open("./data/institutions_state.json", "r") as uni_fp:
        cc_ids, uni_ids = list(json.load(cc_fp).keys()), list(json.load(uni_fp).keys())
    
    for cc_id in cc_ids:
        chunks = [uni_ids[i:i+8] for i in range(0, len(uni_ids), 8)]
        for chunk in chunks:
            asyncio.run(batch_download_queries(cc_id=cc_id, uni_ids=chunk))
            print("finished chunk")
        print("finished all chunks (cc)")
        

if __name__ == "__main__":
    main()
    