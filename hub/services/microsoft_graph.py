import logging
from urllib.parse import urlencode

import msal
import requests
from django.conf import settings

logger = logging.getLogger(__name__)

GRAPH_USERS_ENDPOINT = "https://graph.microsoft.com/v1.0/users"
DEFAULT_SELECT_FIELDS = ("displayName", "mail", "id", "userPrincipalName")
REQUEST_TIMEOUT_SECONDS = 20


class GraphConfigurationError(RuntimeError):
    """Raised when required Microsoft Graph settings are missing."""


class GraphAuthenticationError(RuntimeError):
    """Raised when access token acquisition fails."""


class GraphRequestError(RuntimeError):
    """Raised when the Microsoft Graph API request fails."""


def _normalized_scope_list() -> list[str]:
    scopes = [scope.strip() for scope in getattr(settings, "PHILDATA_GRAPH_SCOPE", []) if scope and scope.strip()]
    if not scopes:
        scopes = ["https://graph.microsoft.com/.default"]
    return scopes


def _tenant_configuration() -> tuple[str, str, str, str]:
    tenant_id = (getattr(settings, "PHILDATA_TENANT_ID", "") or "").strip()
    client_id = (getattr(settings, "PHILDATA_CLIENT_ID", "") or "").strip()
    client_secret = (getattr(settings, "PHILDATA_CLIENT_SECRET", "") or "").strip()
    domain = (getattr(settings, "PHILDATA_DOMAIN", "phildata.com") or "phildata.com").strip().lower()

    missing = [
        name
        for name, value in (
            ("PHILDATA_TENANT_ID", tenant_id),
            ("PHILDATA_CLIENT_ID", client_id),
            ("PHILDATA_CLIENT_SECRET", client_secret),
        )
        if not value
    ]
    if missing:
        raise GraphConfigurationError(
            "Missing Microsoft Graph configuration: " + ", ".join(missing)
        )

    return tenant_id, client_id, client_secret, domain


def _build_authority(tenant_id: str) -> str:
    # This always targets the configured tenant directly, not the host tenant.
    return f"https://login.microsoftonline.com/{tenant_id}"


def acquire_graph_access_token() -> str:
    tenant_id, client_id, client_secret, _ = _tenant_configuration()
    authority = _build_authority(tenant_id)

    app = msal.ConfidentialClientApplication(
        client_id,
        authority=authority,
        client_credential=client_secret,
    )
    result = app.acquire_token_for_client(scopes=_normalized_scope_list())

    access_token = result.get("access_token")
    if access_token:
        return access_token

    error = result.get("error") or "unknown_error"
    description = result.get("error_description") or "No error description returned by MSAL."
    raise GraphAuthenticationError(f"{error}: {description}")


def fetch_phildata_users(limit: int | None = None, include_non_domain: bool = False) -> list[dict]:
    _, _, _, domain = _tenant_configuration()
    access_token = acquire_graph_access_token()

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json",
    }

    params: dict[str, str | int] = {
        "$select": ",".join(DEFAULT_SELECT_FIELDS),
    }

    if limit and limit > 0:
        params["$top"] = min(limit, 999)

    next_url = f"{GRAPH_USERS_ENDPOINT}?{urlencode(params)}"
    collected: list[dict] = []

    with requests.Session() as session:
        while next_url:
            response = session.get(next_url, headers=headers, timeout=REQUEST_TIMEOUT_SECONDS)
            if response.status_code != 200:
                raise GraphRequestError(f"{response.status_code}: {response.text}")

            payload = response.json()
            users = payload.get("value", [])

            for user in users:
                if include_non_domain:
                    collected.append(user)
                else:
                    upn = (user.get("userPrincipalName") or "").lower()
                    mail = (user.get("mail") or "").lower()
                    if upn.endswith(f"@{domain}") or mail.endswith(f"@{domain}"):
                        collected.append(user)

                if limit and limit > 0 and len(collected) >= limit:
                    logger.info("Fetched %s users from Microsoft Graph (limit reached)", len(collected))
                    return collected

            next_url = payload.get("@odata.nextLink")

    logger.info("Fetched %s users from Microsoft Graph", len(collected))
    return collected
