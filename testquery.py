import json
import requests

resp = requests.get("https://assist.org/api/articulation/Agreements?Key=74/2/to/1/AllPrefixes")
contents = json.loads(resp.json()["result"]["articulations"])

with open("testagreement.json", "w") as file:
    json.dump(contents, file, indent=4)
    
    
for inst in 