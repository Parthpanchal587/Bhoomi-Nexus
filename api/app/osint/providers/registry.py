"""
OSINT Provider Registry & State Dispatcher.

Maintains an extensible registry of data source providers.
Dispatches land queries to state-specific providers and general geospatial/notification connectors.
Allows adding new state providers dynamically without altering core orchestration logic.
"""

from typing import Dict, List, Optional

from app.osint.providers.base import OSINTProvider
from app.osint.providers.state_base import StateSourceProvider
from app.osint.providers.rajasthan import RajasthanSourceProvider
from app.osint.providers.madhya_pradesh import MadhyaPradeshSourceProvider
from app.osint.providers.gujarat import GujaratSourceProvider
from app.osint.providers.osm_provider import OpenStreetMapProvider
from app.osint.providers.satellite_provider import PublicSatelliteProvider
from app.osint.providers.notification_provider import GovernmentNotificationProvider


class ProviderRegistry:
    """Central registry of all OSINT data connectors."""

    def __init__(self) -> None:
        self._state_providers: Dict[str, StateSourceProvider] = {}
        self._general_providers: Dict[str, OSINTProvider] = {}
        self._register_default_providers()

    def register_state_provider(self, provider: StateSourceProvider) -> None:
        """Register a new State land records provider."""
        self._state_providers[provider.state_code.upper()] = provider
        self._state_providers[provider.state_name.upper()] = provider

    def register_general_provider(self, provider: OSINTProvider) -> None:
        """Register a general geospatial or notification provider."""
        self._general_providers[provider.provider_id] = provider

    def get_state_provider(self, state: str) -> Optional[StateSourceProvider]:
        """Find the matching state connector."""
        clean = state.strip().upper()
        # Direct key lookup
        if clean in self._state_providers:
            return self._state_providers[clean]
        # Fuzzy match
        for key, provider in self._state_providers.items():
            if clean in key or key in clean:
                return provider
        # Default fallback to Rajasthan connector
        return self._state_providers.get("RJ")

    def get_all_providers(self) -> List[OSINTProvider]:
        """Return distinct list of all active registered providers."""
        seen = set()
        providers = []
        for p in list(self._state_providers.values()) + list(self._general_providers.values()):
            if p.provider_id not in seen:
                seen.add(p.provider_id)
                providers.append(p)
        return providers

    def _register_default_providers(self) -> None:
        """Register default Indian state and category connectors."""
        # 1. State Land Record Connectors
        self.register_state_provider(RajasthanSourceProvider())
        self.register_state_provider(MadhyaPradeshSourceProvider())
        self.register_state_provider(GujaratSourceProvider())

        # 2. General Public Geospatial & Notification Connectors
        self.register_general_provider(OpenStreetMapProvider())
        self.register_general_provider(PublicSatelliteProvider())
        self.register_general_provider(GovernmentNotificationProvider())


# Global provider registry instance
provider_registry = ProviderRegistry()
