"""
Base OSINT Provider Interface.

Defines the contract for all data source connectors:
- search_parcel()
- get_land_record()
- get_geospatial_data()
- get_public_notifications()
- get_source_metadata()
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from app.osint.schemas import (
    GeospatialObservation,
    OSINTSearchQuery,
    ProvenanceMetadata,
    SourceRecordEntry,
)


class OSINTProvider(ABC):
    """Abstract Base Class for all OSINT data connectors."""

    @property
    @abstractmethod
    def provider_id(self) -> str:
        """Unique machine identifier for the provider."""
        pass

    @property
    @abstractmethod
    def display_name(self) -> str:
        """Human-readable provider name."""
        pass

    @property
    @abstractmethod
    def category(self) -> str:
        """Category: STATE_PORTAL, GEOSPATIAL, SATELLITE, GAZETTE, LEGAL."""
        pass

    @abstractmethod
    def get_source_metadata(self) -> ProvenanceMetadata:
        """Returns provenance and reliability metadata for this connector."""
        pass

    @abstractmethod
    async def search_parcel(self, query: OSINTSearchQuery) -> Optional[SourceRecordEntry]:
        """Search and extract parcel information according to query parameters."""
        pass

    @abstractmethod
    async def get_geospatial_data(self, query: OSINTSearchQuery) -> Optional[GeospatialObservation]:
        """Retrieve publicly accessible geospatial or satellite observations."""
        pass

    @abstractmethod
    async def get_public_notifications(self, query: OSINTSearchQuery) -> List[Dict[str, Any]]:
        """Retrieve relevant public gazettes or notifications."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if provider endpoint is legally and technically reachable."""
        pass
