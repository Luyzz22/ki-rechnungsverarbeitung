"""
SSO/OAuth Configuration for SBS Deutschland
Supports: Google, Microsoft Entra ID, Okta, Generic SAML
"""
import os
from authlib.integrations.starlette_client import OAuth

oauth = OAuth()

# ============================================================
# GOOGLE OAUTH
# ============================================================
oauth.register(
    name='google',
    client_id=os.getenv('GOOGLE_CLIENT_ID'),
    client_secret=os.getenv('GOOGLE_CLIENT_SECRET'),
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={
        'scope': 'openid email profile'
    }
)

# ============================================================
# MICROSOFT ENTRA ID (Azure AD)
# ============================================================
oauth.register(
    name='microsoft',
    client_id=os.getenv('MICROSOFT_CLIENT_ID'),
    client_secret=os.getenv('MICROSOFT_CLIENT_SECRET'),
    server_metadata_url='https://login.microsoftonline.com/common/v2.0/.well-known/openid-configuration',
    client_kwargs={
        'scope': 'openid email profile'
    }
)

# ============================================================
# OKTA (Phase 2)
# ============================================================
# oauth.register(
#     name='okta',
#     client_id=os.getenv('OKTA_CLIENT_ID'),
#     client_secret=os.getenv('OKTA_CLIENT_SECRET'),
#     server_metadata_url=f"https://{os.getenv('OKTA_DOMAIN')}/.well-known/openid-configuration",
#     client_kwargs={
#         'scope': 'openid email profile'
#     }
# )

def get_oauth():
    return oauth
