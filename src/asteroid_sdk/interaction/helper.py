"""
Helper functions for interacting with running agents
"""
import asyncio
import time
import logging

from asteroid_sdk.api.generated.asteroid_api_client.api.run.get_run import sync as get_run_sync
from asteroid_sdk.api.generated.asteroid_api_client.client import Client
from asteroid_sdk.api.generated.asteroid_api_client.api.run.update_run_status import sync_detailed as update_run_status_sync
from asteroid_sdk.api.generated.asteroid_api_client.models.status import Status
from asteroid_sdk.registration.helper import APIClientFactory
from asteroid_sdk.api.generated.asteroid_api_client.api.run.update_run_metadata import sync_detailed as update_run_metadata_sync
from asteroid_sdk.api.generated.asteroid_api_client.models.update_run_metadata_body import UpdateRunMetadataBody


async def wait_for_unpaused(run_id: str):
    """Wait until the run is no longer in paused state."""
    client = APIClientFactory.get_client()

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

def pause_run(run_id: str):
    """Pause a running run."""
    client = APIClientFactory.get_client()

    try:
        response = update_run_status_sync(client=client, run_id=run_id, body=Status(status="paused"))
        if response is not None:
            raise Exception(f"Failed to pause run {run_id}: {response.status_code} {response.content}")
    except Exception as e:
        logging.error(f"Error pausing run {run_id}: {e}")
        raise e

def fail_run(run_id: str, error_message: str):
    """Fail a running run."""
    client = APIClientFactory.get_client()

    try:
        response = update_run_status_sync(client=client, run_id=run_id, body=Status(status="failed", error_message=error_message))
        if response is not None:
            raise Exception(f"Failed to fail run {run_id}: {response.status_code} {response.content}")
        update_run_metadata(run_id, {"fail_reason": error_message})
    except Exception as e:
        logging.error(f"Error failing run {run_id}: {e}")
        raise e

def update_run_metadata(run_id: str, metadata: dict):
    """Update the metadata of a run with the provided dictionary."""
    client = APIClientFactory.get_client()

    try:
        metadata_body = UpdateRunMetadataBody.from_dict(metadata)
        response = update_run_metadata_sync(
            client=client,
            run_id=run_id,
            body=metadata_body
        )
        if response.status_code != 204:
            raise Exception(f"Failed to update run metadata for {run_id}: {response.status_code} {response.content}")
    except Exception as e:
        logging.error(f"Error updating run metadata for {run_id}: {e}")
        raise e

