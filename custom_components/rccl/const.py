"""Constants for the Royal Caribbean integration."""

from __future__ import annotations

from datetime import timedelta

DOMAIN = "rccl"

CONF_USERNAME = "username"
CONF_PASSWORD = "password"
CONF_ACCESS_TOKEN = "access_token"
CONF_ACCOUNT_ID = "account_id"
CONF_APP_KEY = "app_key"
CONF_VDS_ID = "vds_id"
CONF_AUTH_REFERER = "auth_referer"
CONF_AUTHORIZE_REFERER = "authorize_referer"
CONF_REFRESH_TOKEN = "refresh_token"
CONF_ID_TOKEN = "id_token"
CONF_TOKEN_EXPIRES_AT = "token_expires_at"
CONF_SCAN_INTERVAL = "scan_interval"
CONF_ENTRY_TYPE = "entry_type"
CONF_CLUB_ROYALE_LOYALTY_ID = "club_royale_loyalty_id"

ENTRY_TYPE_ACCOUNT = "account"
ENTRY_TYPE_CLUB_ROYALE = "club_royale"

DEFAULT_API_BASE_URL = "https://aws-prd.api.rccl.com"
DEFAULT_CLUB_ROYALE_API_BASE_URL = "https://api.rccl.com"
DEFAULT_WEB_BASE_URL = "https://www.royalcaribbean.com"
DEFAULT_APP_KEY = "hyNNqIPHHzaLzVpcICPdAdbFV8yvTsAm"
DEFAULT_BRAND = "royal"
DEFAULT_LANGUAGE = "en"
DEFAULT_OAUTH_CLIENT = "login-component"
DEFAULT_REQUEST_TIMEOUT = 20
DEFAULT_SCAN_INTERVAL = 60
MIN_SCAN_INTERVAL = 15
DEFAULT_UPDATE_INTERVAL = timedelta(minutes=DEFAULT_SCAN_INTERVAL)

HEADER_ACCESS_TOKEN = "access-token"
HEADER_ACCOUNT_ID = "account-id"
HEADER_APP_KEY = "appkey"
HEADER_VDS_ID = "vds-id"

REQ_APP_ID = "RCL-WEB"
REQ_APP_VERSION = "1.0.0"

PLATFORMS = ["sensor", "calendar"]
CLUB_ROYALE_PLATFORMS = ["sensor"]
