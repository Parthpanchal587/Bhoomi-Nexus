"""
State-Level Land Records Source Provider Base Class.

Architecture allows any Indian State to implement its unique revenue structure,
khasra conventions, and public portal endpoints without hardcoding a single state.
"""

from abc import abstractmethod
from typing import Any, Dict, List, Optional

from app.osint.providers.base import OSINTProvider
from app.osint.schemas import OSINTSearchQuery, SourceRecordEntry


class StateSourceProvider(OSINTProvider):
    """Specialized base class for Indian State Revenue / Land Record Portals."""

    @property
    def category(self) -> str:
        return "STATE_REVENUE_PORTAL"

    @property
    @abstractmethod
    def state_code(self) -> str:
        """Two-letter ISO state code (e.g., 'RJ', 'MP', 'GJ')."""
        pass

    @property
    @abstractmethod
    def state_name(self) -> str:
        """Full state name in English."""
        pass

    @property
    @abstractmethod
    def portal_name(self) -> str:
        """Official name of the public land record portal (e.g. 'Apna Khata / Jamabandi')."""
        pass

    @property
    @abstractmethod
    def portal_url(self) -> str:
        """Base URL of the public inquiry portal."""
        pass

    def supports_query(self, query: OSINTSearchQuery) -> bool:
        """Verify if this provider handles the requested state."""
        return query.state.strip().lower() in (
            self.state_name.lower(),
            self.state_code.lower(),
        )

    @abstractmethod
    def generate_demo_record(self, query: OSINTSearchQuery) -> SourceRecordEntry:
        """
        Generate a clearly labelled demonstration record when the live portal
        is offline, maintenance-locked, or for testing.
        """
        pass
