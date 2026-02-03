"""Provider integrations package."""

from licence_api.providers.adobe import AdobeProvider
from licence_api.providers.anthropic import AnthropicProvider
from licence_api.providers.atlassian import AtlassianProvider
from licence_api.providers.auth0 import Auth0Provider
from licence_api.providers.base import BaseProvider
from licence_api.providers.cursor import CursorProvider
from licence_api.providers.figma import FigmaProvider
from licence_api.providers.github import GitHubProvider
from licence_api.providers.gitlab import GitLabProvider
from licence_api.providers.google_workspace import GoogleWorkspaceProvider
from licence_api.providers.hibob import HiBobProvider
from licence_api.providers.huggingface import HuggingFaceProvider
from licence_api.providers.jetbrains import JetBrainsProvider
from licence_api.providers.mailjet import MailjetProvider
from licence_api.providers.mattermost import MattermostProvider
from licence_api.providers.microsoft import MicrosoftProvider
from licence_api.providers.miro import MiroProvider
from licence_api.providers.onepassword import OnePasswordProvider
from licence_api.providers.openai import OpenAIProvider
from licence_api.providers.personio import PersonioProvider
from licence_api.providers.slack import SlackProvider
from licence_api.providers.zoom import ZoomProvider

__all__ = [
    "AdobeProvider",
    "AnthropicProvider",
    "AtlassianProvider",
    "Auth0Provider",
    "BaseProvider",
    "CursorProvider",
    "FigmaProvider",
    "GitHubProvider",
    "GitLabProvider",
    "GoogleWorkspaceProvider",
    "HiBobProvider",
    "HuggingFaceProvider",
    "JetBrainsProvider",
    "MailjetProvider",
    "MattermostProvider",
    "MicrosoftProvider",
    "MiroProvider",
    "OnePasswordProvider",
    "OpenAIProvider",
    "PersonioProvider",
    "SlackProvider",
    "ZoomProvider",
]
