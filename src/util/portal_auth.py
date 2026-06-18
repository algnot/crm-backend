from odoo.http import request

from .request import json_response

PORTAL_ROLE_ADMIN = "admin"
PORTAL_ROLE_OPERATION = "operation"
PORTAL_ROLES = {PORTAL_ROLE_ADMIN, PORTAL_ROLE_OPERATION}


def get_bearer_token():
    authorization = request.httprequest.headers.get("Authorization", "")
    if authorization.lower().startswith("bearer "):
        return authorization[7:].strip()
    return False


def get_portal_user_from_request():
    token = get_bearer_token()
    if not token:
        return request.env["res.users"]

    return request.env["partner.portal.token"].sudo().get_user_from_token(token)


def get_portal_role(user):
    if not user:
        return False
    return user.portal_role or PORTAL_ROLE_ADMIN


def is_portal_admin(user):
    return get_portal_role(user) == PORTAL_ROLE_ADMIN


def portal_unauthorized_response():
    return json_response(
        {"error": "unauthorized", "message": "Invalid or expired token."},
        status=401,
    )


def portal_forbidden_response():
    return json_response(
        {"error": "forbidden", "message": "You do not have permission to perform this action."},
        status=403,
    )


def get_portal_admin_from_request():
    user = get_portal_user_from_request()
    if not user:
        return None, portal_unauthorized_response()
    if not is_portal_admin(user):
        return None, portal_forbidden_response()
    return user, None
