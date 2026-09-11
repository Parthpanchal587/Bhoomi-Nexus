"""
OSINT Providers Package.
"""

from app.osint.providers.base import OSINTProvider
from app.osint.providers.state_base import StateSourceProvider
from app.osint.providers.rajasthan import RajasthanSourceProvider
from app.osint.providers.madhya_pradesh import MadhyaPradeshSourceProvider
from app.osint.providers.gujarat import GujaratSourceProvider
from app.osint.providers.osm_provider import OpenStreetMapProvider
from app.osint.providers.satellite_provider import PublicSatelliteProvider
from app.osint.providers.notification_provider import GovernmentNotificationProvider
from app.osint.providers.registry import ProviderRegistry, provider_registry

__all__ = [
    "OSINTProvider",
    "StateSourceProvider",
    "RajasthanSourceProvider",
    "MadhyaPradeshSourceProvider",
    "GujaratSourceProvider",
    "OpenStreetMapProvider",
    "PublicSatelliteProvider",
    "GovernmentNotificationProvider",
    "ProviderRegistry",
    "provider_registry",
]
