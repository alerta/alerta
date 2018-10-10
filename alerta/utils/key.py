
import base64
import hashlib
import hmac
import os
from typing import List

from flask import Flask


class ApiKeyHelper:

    def __init__(self, app: Flask=None) -> None:
        self.app = app
        if app is not None:
            self.init_app(app)

    def init_app(self, app: Flask) -> None:
        self.secret_key = app.config['SECRET_KEY']
        self.admin_users = app.config['ADMIN_USERS']
        self.user_default_scopes = app.config['USER_DEFAULT_SCOPES']
        self.api_key_expire_days = app.config['API_KEY_EXPIRE_DAYS']

    def generate(self) -> str:
        random = str(os.urandom(32)).encode('utf-8')
        digest = hmac.new(self.secret_key.encode('utf-8'), msg=random, digestmod=hashlib.sha256).digest()
        return base64.urlsafe_b64encode(digest).decode('utf-8')[:40]

    def scopes_to_type(self, scopes: List[str]) -> str:
        for scope in scopes:
            if scope.startswith('write') or scope.startswith('admin'):
                return 'read-write'
        return 'read-only'

    def type_to_scopes(self, user: str, key_type: str) -> List[str]:
        if user in self.admin_users:
            return ['admin', 'read', 'write']
        if key_type == 'read-write':
            return ['read', 'write']
        if key_type == 'read-only':
            return ['read']
        return []
