import asyncio
import time
import logging

from asteroid_sdk.api.generated.asteroid_api_client.api.run.get_run import sync as get_run_sync
from asteroid_sdk.api.generated.asteroid_api_client.client import Client


async def wait_for_unpaused(run_id: str, client: Client):
    """Wait until the run is no longer in paused state."""
    start_time = time.time()
    timeout = 1200 # 20 minute timeout
        
    while True:
        try:
            run_status = get_run_sync(client=client, run_id=run_id)
            if run_status and run_status.status != "paused":
                break
            
            # Check if we've exceeded timeout
            if time.time() - start_time > timeout:
                logging.error(f"Timeout waiting for run {run_id} to unpause")
                break
                
            logging.info(f"Run {run_id} is paused, waiting for unpaused state...")
            await asyncio.sleep(1)  # Wait 1 second before checking again
            
        except Exception as e:
            logging.error(f"Error checking run status: {e}")
            break  # Exit the loop on error instead of continuing indefinitely
