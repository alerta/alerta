from flask import Request, current_app
from mohawk import Receiver


def get_credentials(key_id: str):
    credentials_map = {
        creds['key']: dict(
            id=creds['key'],  # access_key
            key=creds['secret'],  # secret_key
            algorithm=creds.get('algorithm', 'sha256')
        ) for creds in current_app.config['HMAC_AUTH_CREDENTIALS']}

    if key_id in credentials_map:
        return credentials_map[key_id]
    else:
        raise LookupError('Unknown sender')


class HmacAuth:

    @staticmethod
    def authenticate(r: Request):
        return Receiver(
            get_credentials,
            r.headers.get('Authorization'),
            url=r.url,
            method=r.method,
            content=r.data,
            content_type=r.content_type,
            timestamp_skew_in_seconds=300
        )
