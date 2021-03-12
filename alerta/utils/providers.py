from flask import Flask


class AuthProviders:

    OIDC_PROVIDERS = ['openid', 'azure', 'cognito', 'gitlab', 'google', 'keycloak']

    def __init__(self, app: Flask = None) -> None:
        self.app = app
        if app is not None:
            self.init_app(app)

        self.providers = None

    def init_app(self, app: Flask) -> None:
        self.providers = app.config['AUTH_PROVIDER']

        if isinstance(self.providers, str):
            self.providers = [self.providers]

    def has_provider(self, provider: str) -> bool:
        return provider in self.providers

    def get_oidc_provider(self) -> str:
        for p in AuthProviders.OIDC_PROVIDERS:
            if p in self.providers:
                return p
