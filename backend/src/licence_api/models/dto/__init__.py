"""Data Transfer Objects package."""

from licence_api.models.dto.auth import TokenResponse, UserInfo
from licence_api.models.dto.dashboard import DashboardResponse
from licence_api.models.dto.employee import EmployeeListResponse, EmployeeResponse
from licence_api.models.dto.license import LicenseListResponse, LicenseResponse
from licence_api.models.dto.provider import (
    ProviderCreate,
    ProviderListResponse,
    ProviderResponse,
    ProviderUpdate,
)
from licence_api.models.dto.report import (
    CostReportResponse,
    InactiveLicenseReport,
    OffboardingReport,
)

__all__ = [
    "TokenResponse",
    "UserInfo",
    "EmployeeResponse",
    "EmployeeListResponse",
    "LicenseResponse",
    "LicenseListResponse",
    "ProviderCreate",
    "ProviderUpdate",
    "ProviderResponse",
    "ProviderListResponse",
    "DashboardResponse",
    "CostReportResponse",
    "InactiveLicenseReport",
    "OffboardingReport",
]
