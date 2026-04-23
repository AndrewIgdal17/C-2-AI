"""
API endpoints for provider registration and management.
This handles updating the LlamaStack configuration and restarting the deployment.
"""

import asyncio
import logging
from typing import Any, Dict, List

import yaml
from fastapi import APIRouter, HTTPException, Request, status
from kubernetes import client
from kubernetes import config as k8s_config
from kubernetes.client.rest import ApiException

from ...api.llamastack import get_client_from_request
from ...schemas.providers import ProviderCreate, ProviderRead

logger = logging.getLogger(__name__)

router = APIRouter()

# Kubernetes configuration
CONFIGMAP_NAME = "run-config"
DEPLOYMENT_NAME = "llamastack"
MAX_WAIT_TIME = 120  # Maximum wait time in seconds
POLL_INTERVAL = 2  # Poll every 2 seconds


async def wait_for_llamastack(request: Request, max_wait: int = MAX_WAIT_TIME) -> bool:
    """
    Wait for LlamaStack to be ready after restart by checking if we can list providers.
    Returns True if LlamaStack is ready, False if timeout.
    """
    start_time = asyncio.get_event_loop().time()

    while (asyncio.get_event_loop().time() - start_time) < max_wait:
        try:
            client = get_client_from_request(request)
            # Try to list providers as a health check
            await client.providers.list()
            logger.info("LlamaStack is ready")
            return True
        except Exception as e:
            logger.debug(f"LlamaStack not ready yet: {str(e)}")
            await asyncio.sleep(POLL_INTERVAL)

    logger.warning(f"LlamaStack did not become ready within {max_wait} seconds")
    return False


def get_namespace():
    """Get the current namespace from the pod's service account."""
    try:
        with open("/var/run/secrets/kubernetes.io/serviceaccount/namespace", "r") as f:
            return f.read().strip()
    except FileNotFoundError:
        logger.warning("Could not read namespace from service account, using 'default'")
        return "default"


def get_k8s_clients():
    """Initialize Kubernetes clients."""
    try:
        # Try to load in-cluster config first
        k8s_config.load_incluster_config()
    except k8s_config.ConfigException:
        # Fall back to kubeconfig for local development
        k8s_config.load_kube_config()

    core_v1 = client.CoreV1Api()
    apps_v1 = client.AppsV1Api()
    return core_v1, apps_v1


@router.get("/", response_model=List[Dict[str, Any]])
async def list_providers(request: Request):
    """
    List all available providers.
    """
    llama_client = get_client_from_request(request)
    try:
        providers = await llama_client.providers.list()

        providers_list = []
        for provider in providers:
            provider_info = {
                "provider_id": str(provider.provider_id),
                "provider_type": provider.provider_type,
                "api": provider.api,
                "config": provider.config if hasattr(provider, "config") else {},
            }
            providers_list.append(provider_info)

        logger.info(f"Retrieved {len(providers_list)} providers")
        return providers_list

    except Exception as e:
        logger.error(f"Error listing providers: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list providers: {str(e)}",
        )


@router.post("/", response_model=ProviderRead, status_code=status.HTTP_201_CREATED)
async def register_provider(provider_data: ProviderCreate, request: Request):
    """
    Register a new vLLM or Ollama provider.
    This updates the LlamaStack configmap and restarts the deployment.
    """
    namespace = get_namespace()

    try:
        logger.info(
            f"Registering provider: {provider_data.provider_id} "
            f"of type {provider_data.provider_type} in namespace {namespace}"
        )

        # Get Kubernetes clients
        core_v1, apps_v1 = get_k8s_clients()

        # Read the current configmap
        try:
            configmap = core_v1.read_namespaced_config_map(CONFIGMAP_NAME, namespace)
        except ApiException as e:
            logger.error(f"Failed to read configmap: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to read LlamaStack configuration: {str(e)}",
            )

        # Parse the YAML configuration
        config_yaml = configmap.data.get("config.yaml")
        if not config_yaml:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Configuration YAML not found in configmap",
            )

        config_data = yaml.safe_load(config_yaml)
        inference_count = len(config_data.get("providers", {}).get("inference", []))
        logger.info(f"Current config loaded, has {inference_count} inference providers")

        # Check if provider already exists
        inference_providers = config_data.setdefault("providers", {}).setdefault(
            "inference", []
        )
        existing_provider = next(
            (
                p
                for p in inference_providers
                if p.get("provider_id") == provider_data.provider_id
            ),
            None,
        )

        if existing_provider:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Provider '{provider_data.provider_id}' already exists",
            )

        # Add the new provider
        new_provider = {
            "provider_id": provider_data.provider_id,
            "provider_type": provider_data.provider_type,
            "config": provider_data.config,
        }
        inference_providers.append(new_provider)

        logger.info(f"Added new provider: {new_provider}")

        # Update the configmap
        config_yaml_updated = yaml.dump(
            config_data, default_flow_style=False, sort_keys=False
        )
        configmap.data["config.yaml"] = config_yaml_updated

        try:
            core_v1.patch_namespaced_config_map(CONFIGMAP_NAME, namespace, configmap)
            logger.info(
                f"Successfully updated configmap {CONFIGMAP_NAME} in namespace {namespace}"
            )
        except ApiException as e:
            logger.error(f"Failed to update configmap: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to update LlamaStack configuration: {str(e)}",
            )

        # Restart the LlamaStack deployment
        try:
            deployment = apps_v1.read_namespaced_deployment(DEPLOYMENT_NAME, namespace)

            # Update deployment annotation to trigger restart
            if not deployment.spec.template.metadata.annotations:
                deployment.spec.template.metadata.annotations = {}

            from datetime import datetime

            deployment.spec.template.metadata.annotations[
                "kubectl.kubernetes.io/restartedAt"
            ] = datetime.utcnow().isoformat()

            apps_v1.patch_namespaced_deployment(DEPLOYMENT_NAME, namespace, deployment)
            logger.info(
                f"Successfully triggered restart of deployment {DEPLOYMENT_NAME} in namespace {namespace}"
            )
        except ApiException as e:
            logger.error(f"Failed to restart deployment: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Provider registered but failed to restart LlamaStack: {str(e)}",
            )

        # Wait for LlamaStack to be ready
        logger.info("Waiting for LlamaStack to restart...")
        is_ready = await wait_for_llamastack(request)

        if not is_ready:
            logger.warning("LlamaStack restart timeout, but provider was registered")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=(
                    "Provider registered and LlamaStack restarted, but service did "
                    "not become ready within expected time. Please check LlamaStack logs."
                ),
            )

        logger.info("LlamaStack is ready, provider registration complete")

        # Return the created provider
        return ProviderRead(
            provider_id=provider_data.provider_id,
            provider_type=provider_data.provider_type,
            api="inference",
            config=provider_data.config,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error registering provider: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to register provider: {str(e)}",
        )
