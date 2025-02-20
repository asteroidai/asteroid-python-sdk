"""
Helper functions for interacting with running agents
"""
import asyncio
import os
import time
import logging

import aiohttp
from asteroid_sdk.api.generated.asteroid_api_client.api.run.get_run import sync as get_run_sync
from asteroid_sdk.api.generated.asteroid_api_client.client import Client
from asteroid_sdk.api.generated.asteroid_api_client.api.run.update_run_status import sync_detailed as update_run_status_sync
from asteroid_sdk.api.generated.asteroid_api_client.models.status import Status
from asteroid_sdk.registration.helper import APIClientFactory, submit_run_result, submit_run_status
from asteroid_sdk.api.generated.asteroid_api_client.api.run.update_run_metadata import sync_detailed as update_run_metadata_sync
from asteroid_sdk.api.generated.asteroid_api_client.api.run.get_create_file_url import sync_detailed as get_create_file_url_sync
from asteroid_sdk.api.generated.asteroid_api_client.models.update_run_metadata_body import UpdateRunMetadataBody
from asteroid_sdk.api.generated.asteroid_api_client.models.get_create_file_url_body import GetCreateFileURLBody
import requests

async def wait_for_unpaused(run_id: str):
    """Wait until the run is no longer in paused state."""
    client = APIClientFactory.get_client()

    start_time = time.time()
    timeout = 1200 # 20 minute timeout
        
    while True:
        try:
            run = get_run_sync(client=client, run_id=run_id)
        
            # Check if the run has been killed
            if run.status == Status.FAILED:
                raise Exception(f"Run {run_id} has failed") 

            if run.status != Status.PAUSED:
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
        response = submit_run_status(run_id, Status.PAUSED)
        if response is not None:
            raise Exception(f"Failed to pause run {run_id}: {response.status_code} {response.content}")
    except Exception as e:
        logging.error(f"Error pausing run {run_id}: {e}")
        raise e

def fail_run(run_id: str, error_message: str):
    """Fail a running run."""
    client = APIClientFactory.get_client()

    try:
        submit_run_status(run_id, Status.FAILED)
        update_run_metadata(run_id, {"fail_reason": error_message})
        submit_run_result(run_id, "failed")
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
        if response.status_code < 200 or response.status_code >= 300:
            raise Exception(f"Failed to update run metadata for {run_id}: {response.status_code}. Response was: {response.content}")
    except Exception as e:
        logging.error(f"Error updating run metadata for {run_id}: {e}")
        raise e

async def upload_file(run_id: str, file_path: str, file_name: str = None):
    """Upload a file to the run's local storage."""
    client = APIClientFactory.get_client()

    if file_name is None:
        file_name = os.path.basename(file_path)

    # Prefix the file name with the run ID
    file_name = f"{run_id}_{time.time()}_{file_name}"

    body = GetCreateFileURLBody(
        file_name=file_name,
    )

    try:
        response = get_create_file_url_sync(client=client, run_id=run_id, body=body)
        if response.status_code < 200 or response.status_code >= 300:
            raise Exception(f"Failed to get signed URL for run {run_id}: {response.status_code}. Response was: {response.content}")
        signed_url = response.parsed
        if signed_url is None:
            raise Exception(f"Failed to get signed URL for run {run_id}: {response.status_code}. Response was: {response.content}")

    except Exception as e:
        logging.error(f"Error getting signed URL for run {run_id}: {e}")
        raise e

    print(f"Uploading file {file_path} to run {run_id}")

    # Step 2: Perform the actual PUT request (with the PDF or binary data).
    async with aiohttp.ClientSession() as session:
        with open(file_path, "rb") as f:
            file_data = f.read()
        headers = {
            "Content-Type": "application/pdf",  # or text/plain as needed
        }
        async with session.put(signed_url, data=file_data, headers=headers) as resp:
            if resp.status not in (200, 201):
                error_text = await resp.text()
                raise RuntimeError(
                    f"Failed to upload. Status={resp.status}, Response={error_text}"
                )

    logging.info(f"File '{file_path}' successfully uploaded to '{signed_url}' (run_id={run_id}).")

def get_run_status(run_id: str) -> Status:
    """Get the status of a run."""
    client = APIClientFactory.get_client()

    run = get_run_sync(client=client, run_id=run_id)
    return run.status
