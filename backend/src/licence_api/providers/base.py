"""Base provider interface."""

from abc import ABC, abstractmethod
from typing import Any


class BaseProvider(ABC):
    """Abstract base class for provider integrations."""

    def __init__(self, credentials: dict[str, Any]) -> None:
        """Initialize provider with credentials.

        Args:
            credentials: Provider-specific credentials
        """
        self.credentials = credentials

    @abstractmethod
    async def test_connection(self) -> bool:
        """Test the provider connection.

        Returns:
            True if connection is successful
        """
        pass

    @abstractmethod
    async def fetch_licenses(self) -> list[dict[str, Any]]:
        """Fetch licenses/users from the provider.

        Returns:
            List of license data dicts with keys:
            - external_user_id: str (required)
            - email: str (optional, for matching)
            - license_type: str (optional)
            - status: str (default: "active")
            - assigned_at: datetime (optional)
            - last_activity_at: datetime (optional)
            - monthly_cost: Decimal (optional)
            - currency: str (default: "EUR")
            - metadata: dict (optional)
        """
        pass


class HRISProvider(BaseProvider):
    """Base class for HRIS providers like HiBob."""

    @abstractmethod
    async def fetch_employees(self) -> list[dict[str, Any]]:
        """Fetch employees from the HRIS.

        Returns:
            List of employee data dicts with keys:
            - hibob_id: str (required)
            - email: str (required)
            - full_name: str (required)
            - department: str (optional)
            - status: str (required: "active" or "offboarded")
            - start_date: date (optional)
            - termination_date: date (optional)
        """
        pass

    async def fetch_licenses(self) -> list[dict[str, Any]]:
        """HRIS providers don't have licenses."""
        return []
