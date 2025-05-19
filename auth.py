import json
import os
from functools import wraps
from werkzeug.exceptions import Unauthorized, Forbidden
import requests
from flask import request, jsonify, _request_ctx_stack
from jose import jwt
import six
from config import Config

# Auth0 Configuration
AUTH0_DOMAIN = Config.AUTH0_DOMAIN
ALGORITHMS = Config.AUTH0_ALGORITHMS
API_AUDIENCE = Config.AUTH0_API_AUDIENCE


# Format error response and append status code
def get_token_auth_header():
    """Obtains the Access Token from the Authorization Header"""
    auth = request.headers.get("Authorization", None)
    if not auth:
        raise Unauthorized("Authorization header is expected")

    parts = auth.split()

    if parts[0].lower() != "bearer":
        raise Unauthorized("Authorization header must start with Bearer")
    elif len(parts) == 1:
        raise Unauthorized("Token not found")
    elif len(parts) > 2:
        raise Unauthorized("Authorization header must be Bearer token")

    token = parts[1]
    return token


def requires_auth(f):
    """Determines if the Access Token is valid"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = get_token_auth_header()
        jsonurl = requests.get(f"https://{AUTH0_DOMAIN}/.well-known/jwks.json")
        jwks = jsonurl.json()
        try:
            unverified_header = jwt.get_unverified_header(token)
        except Exception:
            raise Unauthorized("Invalid header. Use an RS256 signed JWT Access Token")
        
        rsa_key = {}
        for key in jwks["keys"]:
            if key["kid"] == unverified_header["kid"]:
                rsa_key = {
                    "kty": key["kty"],
                    "kid": key["kid"],
                    "use": key["use"],
                    "n": key["n"],
                    "e": key["e"]
                }
        if rsa_key:
            try:
                payload = jwt.decode(
                    token,
                    rsa_key,
                    algorithms=ALGORITHMS,
                    audience=API_AUDIENCE,
                    issuer=f"https://{AUTH0_DOMAIN}/"
                )
            except jwt.ExpiredSignatureError:
                raise Unauthorized("Token expired")
            except jwt.JWTClaimsError:
                raise Unauthorized("Incorrect claims. Please check the audience and issuer")
            except Exception:
                raise Unauthorized("Unable to parse authentication token")
            
            _request_ctx_stack.top.current_user = payload
            return f(*args, **kwargs)
        raise Unauthorized("Unable to find appropriate key")
    return decorated


def requires_role(role):
    """Determines if the user has the required role"""
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            token = get_token_auth_header()
            try:
                payload = jwt.decode(
                    token,
                    algorithms=ALGORITHMS,
                    options={"verify_signature": False}
                )
            except Exception:
                raise Unauthorized("Invalid token")
            
            # Check if token contains role permissions
            if 'permissions' not in payload:
                raise Forbidden("Insufficient permissions")
            
            # Check if user has required role
            roles = payload.get('permissions', [])
            if role not in roles:
                raise Forbidden("Insufficient permissions")
            
            return f(*args, **kwargs)
        return wrapper
    return decorator


def get_user_info():
    """Get the current user information from the JWT token"""
    token = get_token_auth_header()
    try:
        payload = jwt.decode(
            token,
            algorithms=ALGORITHMS,
            options={"verify_signature": False}
        )
        return payload
    except Exception:
        raise Unauthorized("Invalid token")
