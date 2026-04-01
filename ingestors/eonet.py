import json

import requests


EONET_EVENTS_URL = "https://eonet.gsfc.nasa.gov/api/v3/events"


def main():
    response = requests.get(EONET_EVENTS_URL, timeout=30)
    response.raise_for_status()

    data = response.json()
    events = data.get("events", [])

    print(f"Fetched {len(events)} EONET events")

    if events:
        print(json.dumps(events[0], indent=2))


if __name__ == "__main__":
    main()

    id title description link categories sources geometries closed