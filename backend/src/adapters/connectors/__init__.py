"""Connector plugin package — register concrete collectors in registry."""

from adapters.connectors.registry import get_connector, list_connector_ids

__all__ = ["get_connector", "list_connector_ids"]
