"""Kubernetes MCP Server Discovery Service.

This module discovers MCP servers deployed in Kubernetes by:
1. Finding MCPServer custom resources with label app.kubernetes.io/component: mcp-server
2. Finding Service resources with label app.kubernetes.io/component: mcp-server
"""

import logging
import os
from typing import Any, Dict, List, Optional

from kubernetes import client, config

logger = logging.getLogger(__name__)


class K8sMCPDiscovery:
    """Discover MCP servers in Kubernetes."""

    def __init__(self):
        """Initialize Kubernetes client."""
        try:
            # Try to load in-cluster config first (when running in K8s)
            config.load_incluster_config()
            logger.info("Loaded in-cluster Kubernetes configuration")
        except config.ConfigException:
            try:
                # Fall back to kubeconfig (for local development)
                config.load_kube_config()
                logger.info("Loaded kubeconfig Kubernetes configuration")
            except config.ConfigException as e:
                logger.warning(f"Could not load Kubernetes config: {e}")
                self.enabled = False
                return

        self.enabled = True
        self.custom_api = client.CustomObjectsApi()
        self.core_api = client.CoreV1Api()

        # Try to get namespace from service account mount first (in-cluster)
        namespace_file = "/var/run/secrets/kubernetes.io/serviceaccount/namespace"
        if os.path.exists(namespace_file):
            with open(namespace_file, "r") as f:
                self.namespace = f.read().strip()
        else:
            # Fallback to environment variable or default
            self.namespace = os.getenv("KUBERNETES_NAMESPACE", "default")

        logger.info(f"Using Kubernetes namespace: {self.namespace}")

    def discover_mcp_servers(self) -> List[Dict[str, Any]]:
        """
        Discover MCP servers from Kubernetes resources.

        Returns:
            List of discovered MCP servers with their metadata
        """
        if not self.enabled:
            logger.warning("Kubernetes discovery is disabled")
            return []

        discovered_servers = []

        # Discover MCPServer custom resources
        try:
            mcpserver_resources = self._discover_mcpserver_resources()
            discovered_servers.extend(mcpserver_resources)
            logger.info(f"Discovered {len(mcpserver_resources)} MCPServer resources")
        except Exception as e:
            logger.error(f"Error discovering MCPServer resources: {e}")

        # Discover Service resources
        try:
            service_resources = self._discover_service_resources()
            discovered_servers.extend(service_resources)
            logger.info(f"Discovered {len(service_resources)} Service resources")
        except Exception as e:
            logger.error(f"Error discovering Service resources: {e}")

        return discovered_servers

    def _discover_mcpserver_resources(self) -> List[Dict[str, Any]]:
        """
        Discover MCPServer custom resources.

        Returns:
            List of discovered MCPServer resources
        """
        discovered = []
        label_selector = "app.kubernetes.io/component=mcp-server"

        try:
            # List MCPServer resources in the namespace
            resources = self.custom_api.list_namespaced_custom_object(
                group="toolhive.stacklok.dev",
                version="v1alpha1",
                namespace=self.namespace,
                plural="mcpservers",
                label_selector=label_selector,
            )

            for item in resources.get("items", []):
                metadata = item.get("metadata", {})
                spec = item.get("spec", {})
                status = item.get("status", {})

                name = metadata.get("name", "")
                description = spec.get("description", "")
                # Auto-generate description if empty
                if not description:
                    description = (
                        f"MCP server discovered from mcpserver resource '{name}'"
                    )

                # Get transport type from label
                labels = metadata.get("labels", {})
                transport = labels.get("mcp.transport", "")

                # Get URL from status
                endpoint_url = self._get_mcpserver_url(status, transport)

                if endpoint_url:
                    discovered.append(
                        {
                            "source": "mcpserver",
                            "name": name,
                            "description": description,
                            "endpoint_url": endpoint_url,
                        }
                    )

        except client.exceptions.ApiException as e:
            if e.status == 404:
                logger.info("MCPServer CRD not found in cluster")
            else:
                logger.error(f"Error listing MCPServer resources: {e}")
        except Exception as e:
            logger.error(f"Unexpected error discovering MCPServer resources: {e}")

        return discovered

    def _get_mcpserver_url(
        self, status: Dict[str, Any], transport: str
    ) -> Optional[str]:
        """
        Extract URL from MCPServer status.

        Args:
            status: MCPServer status object
            transport: Transport type from mcp.transport label

        Returns:
            Constructed endpoint URL or None
        """
        base_url = status.get("url")

        if not base_url:
            return None

        if transport == "sse":
            # Append /sse for SSE transport
            return f"{base_url}/sse"
        else:
            # Append /mcp for streamable-http or other transports
            return f"{base_url}/mcp"

    def _discover_service_resources(self) -> List[Dict[str, Any]]:
        """
        Discover Service resources with MCP server label.

        Returns:
            List of discovered Service resources
        """
        discovered = []
        label_selector = "app.kubernetes.io/component=mcp-server"

        try:
            # List Services in the namespace
            services = self.core_api.list_namespaced_service(
                namespace=self.namespace, label_selector=label_selector
            )

            for service in services.items:
                name = service.metadata.name

                # Get service description from annotation
                annotations = service.metadata.annotations or {}
                description = annotations.get("description", "")
                # Auto-generate description if empty
                if not description:
                    description = (
                        f"MCP server discovered from service resource '{name}'"
                    )

                # Get transport type from label
                labels = service.metadata.labels or {}
                transport = labels.get("mcp.transport", "")

                # Get first port
                if service.spec.ports:
                    port = service.spec.ports[0].port

                    # Determine URL suffix based on transport type
                    suffix = "/sse" if transport == "sse" else "/mcp"

                    # Construct service URL
                    endpoint_url = f"http://{name}.{self.namespace}.svc.cluster.local:{port}{suffix}"

                    discovered.append(
                        {
                            "source": "service",
                            "name": name,
                            "description": description,
                            "endpoint_url": endpoint_url,
                        }
                    )

        except Exception as e:
            logger.error(f"Error discovering Service resources: {e}")

        return discovered


# Singleton instance
_discovery_instance: Optional[K8sMCPDiscovery] = None


def get_k8s_discovery() -> K8sMCPDiscovery:
    """Get singleton K8sMCPDiscovery instance."""
    global _discovery_instance
    if _discovery_instance is None:
        _discovery_instance = K8sMCPDiscovery()
    return _discovery_instance
