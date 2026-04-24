import asyncio
import sys
import os

# Add src to path
sys.path.append(os.path.abspath("src"))

from entrypoints import search_inaturalist_observations
from unittest.mock import AsyncMock

async def main():
    print("Testing iNaturalist pagination logic...")
    
    # Mock process for logging
    process = AsyncMock()
    
    # Search parameters
    # Let's use a query that likely has multiple pages
    # Drosophila melanogaster is common.
    params = {
        "taxon_name": "Drosophila melanogaster",
        "per_page": 10, # Use small per_page to force pagination quickly
        "limit": 30     # Fetch 30 records (3 pages)
    }
    
    api_url = 'https://api.inaturalist.org/v1/observations'
    total_limit = 30
    
    print(f"Calling query_inaturalist_observations with limit={total_limit}, per_page=10")
    
    code, success, data = await search_inaturalist_observations.query_inaturalist_observations(
        api_url, params, process, total_limit
    )
    
    if success:
        results = data.get('results', [])
        print(f"Success! Retrieved {len(results)} records.")
        print(f"Total available according to API: {data.get('total_results')}")
        
        # Verify we got multiple pages
        # Each page is 10, we wanted 30.
        if len(results) == 30:
            print("Pagination verified: fetched exactly 30 records across 3 pages.")
        else:
            print(f"Pagination might have failed or reached end: got {len(results)} records.")
            
        # Check if logs show pagination
        for call in process.log.call_args_list:
            print(f"Log: {call.args[0]}")
    else:
        print(f"Failed with code: {code}")

if __name__ == "__main__":
    asyncio.run(main())
