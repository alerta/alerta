import json
import unittest

import jwt
import requests_mock

from alerta.app import create_app, db
from alerta.models.enums import Scope
from alerta.models.key import ApiKey


class AuthProvidersTestCase(unittest.TestCase):

    def setUp(self):
        pass

    def tearDown(self):
        db.destroy()

    @requests_mock.mock()
    def test_azure(self, m):

        test_config = {
            'TESTING': True,
            'AUTH_REQUIRED': True,
            'AUTH_PROVIDER': 'azure',
            # 'OIDC_ISSUER_URL': 'https://sts.windows.net/f24341ef-7a6f-4cff-abb7-99a11ab11127/',
            'AZURE_TENANT': 'f24341ef-7a6f-4cff-abb7-99a11ab11127',
            'CUSTOMER_VIEWS': True,
        }

        authorization_grant = """
        {
          "code": "AQABAAIAAACEfexXxjamQb3OeGQ4GugvJfMVkt3b4O9rcjh8Euhco7OpeacDZ2B-y249nPI6bFmVXZHz5x-NVY7G9UumTVrd9GZGLt7g4PN6WL50NxPROTFTZWOX3lZW4FHh6VQh9TfQ6w2-V_G4YUkJe14MZVlunWg7_AEi0HcINg1k6T1yeM9R538zzDoypaH9kP3s1QwK5O4nsBbt8azqW4QdEoQQDs1r9W9UnV3GTAEdQdS-tpaeax0-ZVlX0GlQdygw0eDfAsRxFZV2qRY9DcUyLDL_mFrlh35T7NuihSkJTvm5vIu5kzqm6Lub5oKJBBIIvQzUbW8_waTIjIPh28D1drKDCY0_QSneZsrndHTYrLJaBtJqz-M0yd6bE6xz1Vh96G997DzWyxW_ZsRaT2YIrg0CD407cqSTDrsz4GiuBbtLsSHSBwMYNSYL7RKW-uxiVD8aRMn46OSVB2nkDuKGqsv7fEcBWEQ-YQM4cYhJp6V6UWG3XBOP-O0fqlFXLyztVB8rHXyVUAllkPYEl3DVW1ToJKSr-zPLo__RXZEXGCmGvMDHFg51O04Vh21KyiGfDtuRwrv_XuMao8342G9aFanCE6oMrNx2qqWZ9fCaVmd0K5ODgUVhSx_Rd1yYVmz39X9iuFuasx5X5ftZlcdPiy0b6rsqLAlfZcRvgkS21DtwCOLvk7g4ND_k2kDDMx_EyEeaf_cosas4l_Iwxcbng6ZBkP6e2y90ccSAUAtCoCR_rOLyEP_h_FgWJ_eGJWQZGQaLWyl0ELGHPAiFq0E2lyFFJ7z3FMVA50FzGtK7ndBrYs01ZA5845_oxdzkJzQyDYY_5Vw0qJ-nmTeSrgXdbPk9RiwfsdOrKscMi-Vmz2kiKfGxa0adKFx6KKbFjs4_X-66KciSMy_b-kEG8P7m-069qxR6XL_i3SfcGiN18io9PCcqgi_0MIwLMQyO-wl0soF-PZVf4zF1ofjccxnQbpJEW2qU9x5r5bCghgA0aD3wtx0WvNx221AJ28jJ00SRd2B36zkfHe5VXuuip_lnpY8SRO6Tb5vL5BYMo9erCMQhv_lOxcsfmlJ0TqeBDyv2pbIPxBqUILtSoJeW-uQxyZMuIAA",
          "clientId": "38ba6223-a887-43e2-9f7d-8d539df55f67",
          "redirectUri": "http://local.alerta.io:8000"
        }
        """

        discovery_doc = """
        {
          "authorization_endpoint": "https://login.microsoftonline.com/f24341ef-7a6f-4cff-abb7-99a11ab11127/oauth2/authorize",
          "token_endpoint": "https://login.microsoftonline.com/f24341ef-7a6f-4cff-abb7-99a11ab11127/oauth2/token",
          "token_endpoint_auth_methods_supported": [
            "client_secret_post",
            "private_key_jwt",
            "client_secret_basic"
          ],
          "jwks_uri": "https://login.microsoftonline.com/common/discovery/keys",
          "response_modes_supported": [
            "query",
            "fragment",
            "form_post"
          ],
          "subject_types_supported": [
            "pairwise"
          ],
          "id_token_signing_alg_values_supported": [
            "RS256"
          ],
          "http_logout_supported": true,
          "frontchannel_logout_supported": true,
          "end_session_endpoint": "https://login.microsoftonline.com/f24341ef-7a6f-4cff-abb7-99a11ab11127/oauth2/logout",
          "response_types_supported": [
            "code",
            "id_token",
            "code id_token",
            "token id_token",
            "token"
          ],
          "scopes_supported": [
            "openid"
          ],
          "issuer": "https://sts.windows.net/f24341ef-7a6f-4cff-abb7-99a11ab11127/",
          "claims_supported": [
            "sub",
            "iss",
            "cloud_instance_name",
            "cloud_instance_host_name",
            "cloud_graph_host_name",
            "msgraph_host",
            "aud",
            "exp",
            "iat",
            "auth_time",
            "acr",
            "amr",
            "nonce",
            "email",
            "given_name",
            "family_name",
            "nickname"
          ],
          "microsoft_multi_refresh_token": true,
          "check_session_iframe": "https://login.microsoftonline.com/f24341ef-7a6f-4cff-abb7-99a11ab11127/oauth2/checksession",
          "userinfo_endpoint": "https://login.microsoftonline.com/f24341ef-7a6f-4cff-abb7-99a11ab11127/openid/userinfo",
          "tenant_region_scope": "EU",
          "cloud_instance_name": "microsoftonline.com",
          "cloud_graph_host_name": "graph.windows.net",
          "msgraph_host": "graph.microsoft.com",
          "rbac_url": "https://pas.windows.net"
        }
        """

        access_token = """
        {
          "token_type": "Bearer",
          "scope": "User.Read",
          "expires_in": "3600",
          "ext_expires_in": "3600",
          "expires_on": "1553983022",
          "not_before": "1553979122",
          "resource": "00000002-0000-0000-c000-000000000000",
          "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsIng1dCI6Ik4tbEMwbi05REFMcXdodUhZbkhRNjNHZUNYYyIsImtpZCI6Ik4tbEMwbi05REFMcXdodUhZbkhRNjNHZUNYYyJ9.eyJhdWQiOiIwMDAwMDAwMi0wMDAwLTAwMDAtYzAwMC0wMDAwMDAwMDAwMDAiLCJpc3MiOiJodHRwczovL3N0cy53aW5kb3dzLm5ldC9mMjQzNDFlZi03YTZmLTRjZmYtYWJiNy05OWExMWFiMTExMjcvIiwiaWF0IjoxNTUzOTc5MTIyLCJuYmYiOjE1NTM5NzkxMjIsImV4cCI6MTU1Mzk4MzAyMiwiYWNyIjoiMSIsImFpbyI6IkFVUUF1LzhLQUFBQStQZzdRcW5EUFY3Q1JFdEsweUlESFdoTHVLL1BzZFQ3ZmtKSHE3YmxFT0dZMGpyTERvanJ4STVpUjk1eU0xZCsrVkQwZ3VuTSt5K2RpYVhvL0ErdzZBPT0iLCJhbHRzZWNpZCI6IjE6bGl2ZS5jb206MDAwMzQwMDFGMTI1MUFBRCIsImFtciI6WyJwd2QiXSwiYXBwaWQiOiIzOGJhNjIyMy1hODg3LTQzZTItOWY3ZC04ZDUzOWRmNTVmNjciLCJhcHBpZGFjciI6IjEiLCJlbWFpbCI6Im5mc2F0dGVybHlAZ21haWwuY29tIiwiZmFtaWx5X25hbWUiOiJTYXR0ZXJseSIsImdpdmVuX25hbWUiOiJOaWNrIiwiaWRwIjoibGl2ZS5jb20iLCJpcGFkZHIiOiIxNDUuMTQuMTEyLjEwMyIsIm5hbWUiOiJOaWNrIFNhdHRlcmx5Iiwib2lkIjoiZGNhMGFjYWItMTcyNy00MTJiLWEwM2EtMGUzYTRiNjYyNmIxIiwicHVpZCI6IjEwMDMyMDAwM0M2ODk5ODYiLCJzY3AiOiJVc2VyLlJlYWQiLCJzdWIiOiJndWN1a2FaNzRrSmtxVGZpdGpQQ1ZsVWkyQ1J4NUtVdVFaTDlNaWpRUlZRIiwidGVuYW50X3JlZ2lvbl9zY29wZSI6IkVVIiwidGlkIjoiZjI0MzQxZWYtN2E2Zi00Y2ZmLWFiYjctOTlhMTFhYjExMTI3IiwidW5pcXVlX25hbWUiOiJsaXZlLmNvbSNuZnNhdHRlcmx5QGdtYWlsLmNvbSIsInV0aSI6ImJOeC1UbVlZY2tXbUxmekxFLUVWQUEiLCJ2ZXIiOiIxLjAifQ.GM_KwtpOX18LHgA-0y7sdKM5DKiHaoSfA81lClJulkJ2nPJROpGND226m2MJycQqrNrYz-kEMe-6_rpApian1-xGygsprwa4lDwUtIlxa_PQs4-DQB9GFC9h31o4bPhnP5QqH5bjNZzpUTX_9v91qe9hwpbBct0fHgl9uVZD-aW8TYCLNx5_OhAb9uOmCN6prvmhK4Ttv47UU4mfWmXMInUlRIZUJ-84izdqWPeV9rk6Y6WqttwFNVunzXUGQ_1FujJB2RbHXbSrk-JKl12HOm0NA-m4Xxn0Z0K3oA2LOYtwCiTvrNtlcUDr6Lwy3vGnNtzzUAwsrTCWWvwzrfEpWw",
          "refresh_token": "AQABAAAAAACEfexXxjamQb3OeGQ4GugvEpV_oEBJ-4rwh3wnP_fgyuzUG0l2_I6ofeaxYrRJbmZIuybWJMVtrFt1mcxepuqkYP_X8ngoivbN4RI0kRtxI59bLbedLhq3lUUlcJIThiPLL0WRPDy7St6gICL-vbsEMe4y_1ltjoiGBlj8OaOk4o5BVWbKkXtzy2gI6IPNKHukHZ00T1sPZWA0YrObLlu9h-Tt1CcdoLxWSWRGshATAu-XepC7MNgmjSvQAUXxuW7Y6t_w3gSHGyNlPpEVm_H3oKU2RLSMvQsLi-PKLJ0WS3DXYy01V6AG3huyWY562Cd80xcgT1Ly2gl4kBjsxGwABxwNSEcgyCWVs4nzWKCdzcZ1mscyAtmY4Kr74xxGlIwPQ6Sx34gLEunnoHDGXn_RE0ipzc7qg-e5Ws8bv8_JLVHQYXm4Mi_5KRpuh_5tFBtbn5aUc6TJQqRyQOUrG_A4IER_YbTN0u90Io0C4acrp9GVidpFagmG2vL-dqczZ-rv0rLmhX0uRE__PHz7biY0UaRNURgS4hkDB33vyEsw5o-E3N9b09ajwhHiz55PkV22LfESB5ebPpRW2d5AZmKwPBkE57Z0i9oC8Z_ZfIrO2xo_deDXFiKKndFbzIlnYc4Th37lcVBd5B3yDAtfLJNkw7dtCHA4caS7kYayako2cPvkYpM13Jh3dNEiYtY9rUeaF8fkj0pvOH0g4gITQdRcMAFtyHosXrRWMrbweIVYpZ5HOF18abZcmnGs41jUjci4GR_q0SJvdt15-QdmMdDu4GlFFfNvZTtpxKb51ref1a44sdTr77fgFWVFVlYgaw3yyDV3PoYrrWksf3xFEYfOvfhZ6OkroYewPGcVwcDW-4WkEceD-RcMRzkjd1Mecu5RAPQeIWjxort6Gq1OvVHbUl4eSLA256mxLJur0W84vOHZpv3rgg9SbUP81tcPRwYGT00xJDt-mXh1mEx9RukPLpJ_BgU51TvOnch_YsFCnRW-C2jBY40OJvHqpFxZ2vUhpiROxj9phJEPO0APWTdpmXmQdycWchfoxB9LhCLF6S16fX-3rmvMc-woIhV0oNQmZt5n2HHPx-LQsHVOkNs93nr6yzIcNXLfw-QkJScArlLwgtEJ9vXVnefCLhA6TNHXYxquf6FJbarih4LB-51Cf9NmejaA8-nWLL6Sdv5234fXm-9mVq1gKeAdIM4JctidYyfm7juuDZtY3ocDiHGNK-gqPmOklWxp2hOL6ry3haoqC--j9DFNbN6cAavMX00t_NBTKA8U4qRY6yHidF_xoxM9_HwZp0SHJgJzYYKRJKxc0pfvRFHFM_Ciwb4xsFjn7OIMoxkfvAUD2Mp2JaZuQBXeOSt4l-oe1xKQoJbGdcEZa1J9Gr0BRoQhtvFiUoJa3ahNlPTsbCY38oFFS7tnIAA",
          "id_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJub25lIn0.eyJhdWQiOiIzOGJhNjIyMy1hODg3LTQzZTItOWY3ZC04ZDUzOWRmNTVmNjciLCJpc3MiOiJodHRwczovL3N0cy53aW5kb3dzLm5ldC9mMjQzNDFlZi03YTZmLTRjZmYtYWJiNy05OWExMWFiMTExMjcvIiwiaWF0IjoxNTUzOTc5MTIyLCJuYmYiOjE1NTM5NzkxMjIsImV4cCI6MTU1Mzk4MzAyMiwiYW1yIjpbInB3ZCJdLCJlbWFpbCI6Im5mc2F0dGVybHlAZ21haWwuY29tIiwiZmFtaWx5X25hbWUiOiJTYXR0ZXJseSIsImdpdmVuX25hbWUiOiJOaWNrIiwiaWRwIjoibGl2ZS5jb20iLCJpcGFkZHIiOiIxNDUuMTQuMTEyLjEwMyIsIm5hbWUiOiJOaWNrIFNhdHRlcmx5Iiwib2lkIjoiZGNhMGFjYWItMTcyNy00MTJiLWEwM2EtMGUzYTRiNjYyNmIxIiwic3ViIjoiOUhZaGR3X2Y3NjdyWE5JazUyamFfNldNeTE3UENTTGttcXZQSGlwcnNjYyIsInRpZCI6ImYyNDM0MWVmLTdhNmYtNGNmZi1hYmI3LTk5YTExYWIxMTEyNyIsInVuaXF1ZV9uYW1lIjoibGl2ZS5jb20jbmZzYXR0ZXJseUBnbWFpbC5jb20iLCJ2ZXIiOiIxLjAifQ."
        }
        """

        userinfo = r"""
        {
          "aio": "AVQAq/8KAAAAFfowTD/1PFNpiTdO2zhegMtdKv8enA2o5jRatUb6GvYsZg3DXiAwcLnGvLngrqtL1Kb4eInAWXgHIorirIGG2kycNq3C8fLk4jzrgoFl9yA=",
          "amr": "[\"pwd\"]",
          "email": "nfsatterly@gmail.com",
          "family_name": "Satterly",
          "given_name": "Nick",
          "idp": "live.com",
          "ipaddr": "145.14.112.103",
          "name": "Nick Satterly",
          "oid": "dca0acab-1727-412b-a03a-0e3a4b6626b1",
          "sub": "9HYhdw_f767rXNIk52ja_6WMy17PCSLkmqvPHiprscc",
          "tid": "f24341ef-7a6f-4cff-abb7-99a11ab11127",
          "unique_name": "live.com#nfsatterly@gmail.com",
          "uti": "EBafu2Mx2UekJd5Y_24fAA",
          "ver": "1.0"
        }
        """

        m.get('https://sts.windows.net/f24341ef-7a6f-4cff-abb7-99a11ab11127/.well-known/openid-configuration', text=discovery_doc)
        m.post('https://login.microsoftonline.com/f24341ef-7a6f-4cff-abb7-99a11ab11127/oauth2/token', text=access_token)
        m.get('https://login.microsoftonline.com/f24341ef-7a6f-4cff-abb7-99a11ab11127/openid/userinfo', text=userinfo)

        self.app = create_app(test_config)
        self.client = self.app.test_client()

        with self.app.test_request_context('/'):
            self.app.preprocess_request()
            self.api_key = ApiKey(
                user='admin@alerta.io',
                scopes=[Scope.admin, Scope.read, Scope.write],
                text='demo-key'
            )
            self.api_key.create()

        self.headers = {
            'Authorization': 'Key %s' % self.api_key.key,
            'Content-type': 'application/json'
        }

        # add customer mapping
        payload = {
            'customer': 'Alerta IO',
            'match': 'nfsatterly@gmail.com'
        }
        response = self.client.post('/customer', data=json.dumps(payload),
                                    content_type='application/json', headers=self.headers)
        self.assertEqual(response.status_code, 201)

        response = self.client.post('/auth/azure', data=authorization_grant, content_type='application/json')
        self.assertEqual(response.status_code, 200, response.data)
        data = json.loads(response.data.decode('utf-8'))
        claims = jwt.decode(data['token'], verify=False)

        self.assertEqual(claims['name'], 'Nick Satterly', claims)
        self.assertEqual(claims['preferred_username'], 'nfsatterly@gmail.com', claims)
        self.assertEqual(claims['provider'], 'openid', claims)
        # self.assertEqual(claims['roles'], ['user'], claims)
        self.assertEqual(claims['scope'], 'read write', claims)
        self.assertEqual(claims['email'], 'nfsatterly@gmail.com', claims)
        self.assertEqual(claims.get('email_verified'), True, claims)
        self.assertEqual(claims['customers'], ['Alerta IO'], claims)

    @requests_mock.mock()
    def test_gitlab(self, m):

        test_config = {
            'TESTING': True,
            'AUTH_REQUIRED': True,
            'AUTH_PROVIDER': 'gitlab',
            # 'OIDC_ISSUER_URL': 'https://gitlab.com',
            # 'OIDC_CUSTOM_CLAIM': 'groups',
            'ALLOWED_OIDC_ROLES': ['alerta-project'],
            'CUSTOMER_VIEWS': True,
        }

        authorization_grant = """
        {
          "code": "68d753e94fab78d24e13cfa34882c2740b74ba251859bec147f56281d6ea1dd1",
          "clientId": "765904e9909fc9cc5c448a887849029d999cc2e400e097221bf910be39a16678",
          "redirectUri": "http://local.alerta.io:8000"
        }
        """

        discovery_doc = """
        {
          "issuer": "https://gitlab.com",
          "authorization_endpoint": "https://gitlab.com/oauth/authorize",
          "token_endpoint": "https://gitlab.com/oauth/token",
          "userinfo_endpoint": "https://gitlab.com/oauth/userinfo",
          "jwks_uri": "https://gitlab.com/oauth/discovery/keys",
          "scopes_supported": [
            "api",
            "read_user",
            "sudo",
            "read_repository",
            "read_registry",
            "openid",
            "profile",
            "email"
          ],
          "response_types_supported": [
            "code",
            "token"
          ],
          "response_modes_supported": [
            "query",
            "fragment"
          ],
          "token_endpoint_auth_methods_supported": [
            "client_secret_basic",
            "client_secret_post"
          ],
          "subject_types_supported": [
            "public"
          ],
          "id_token_signing_alg_values_supported": [
            "RS256"
          ],
          "claim_types_supported": [
            "normal"
          ],
          "claims_supported": [
            "iss",
            "sub",
            "aud",
            "exp",
            "iat",
            "sub_legacy",
            "name",
            "nickname",
            "email",
            "email_verified",
            "website",
            "profile",
            "picture",
            "groups"
          ]
        }
        """
        access_token = """
        {
          "access_token": "2152f0d2256fe245a98532e699cc7fae51c24fc85437d0f095246ae0890db0fe",
          "token_type": "bearer",
          "refresh_token": "10687059782a69dd76db7466b5f6fbe3395b9db09e78319db61d5473e31e7b2f",
          "scope": "openid profile email",
          "created_at": 1553982929,
          "id_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6Imtld2lRcTlqaUM4NEN2U3NKWU9CLU42QThXRkxTVjIwTWIteTdJbFdEU1EifQ.eyJpc3MiOiJodHRwczovL2dpdGxhYi5jb20iLCJzdWIiOiIxNTY1MDEyIiwiYXVkIjoiNzY1OTA0ZTk5MDlmYzljYzVjNDQ4YTg4Nzg0OTAyOWQ5OTljYzJlNDAwZTA5NzIyMWJmOTEwYmUzOWExNjY3OCIsImV4cCI6MTU1Mzk4MzE2MywiaWF0IjoxNTUzOTgzMDQzLCJhdXRoX3RpbWUiOjE1NTMwMjQ3ODksInN1Yl9sZWdhY3kiOiJlZDk4YjUwZGI5NzdlNmNlMTczMjRhYTkyMmMzZDBlYmIwMzdiYTRjNjBkN2RlZjE2YjQ5YzlkYmJmYjIyYzc1In0.O0SpmNXksWxM1WFH9G8_0cK4d1nVg2bYV2ICUZLn6kKX5ZJ48TOTtNMPpSGF_8MkF-ZlPNse9bsx8Dp_1BmIZCVqhV0bMkRGHtPUYZJEflLln8-mOOpg0ave55HG3yYXTaegPc60CDA-UnXTVhOkzVnvjPF2RcD7EgVKXYOyI2uJ9aebz43_h02eNjIAnJig8VZAeJZbt-0LE2rMlMB3aLS9a3C015_HR9cjqoeZ4ckUpg4F3xRpROpA5hZvpRsZRRq5W56mlSrZ_6GysPCxsruxOgNkw9Of5j-i1IWGxH0mM8oG4EtRIL7y4sBO16YYKVQihkJ1zAtFLa5wQH7pK6I4uShJAoqq21EhDJqZU3-ucuWupbQHubybGdrl_y6Gk6oxFb8BHHf2yE6faQ1QznwT5kiqZH1vdCGr9HP2PheNKZnXuGn-EKy0HRI_tuN5tcIvHV4cXa6xbeiYGCgbZWqJpLWTCLDuPzT_BsinLwgZW5bvO7zXs6N5VRaWWbC03A9FWIZK9tl1xFGfa411eFVM-G5UBEjJNvT0kZHdiNHGkNG-MyO1soT0p741e-yvKQEIQwdo6kyNZ-ZJ6yA0NSmHZy4b3DM67zn5L8uZ0fSToQV0oYnbDjn40Tm83qL3oZqvLr4Y1kKQjO9AK5kOzLtFRNqxvZ2d-FtkdyHgTKM"
        }
        """

        tokeninfo = """
        {
          "resource_owner_id": 1565012,
          "scopes": [
            "openid",
            "profile",
            "email"
          ],
          "expires_in_seconds": null,
          "application": {
            "uid": "765904e9909fc9cc5c448a887849029d999cc2e400e097221bf910be39a16678"
          },
          "created_at": 1553982929
        }
        """

        userinfo = """
        {
          "sub": "1565012",
          "sub_legacy": "ed98b50db977e6ce17324aa922c3d0ebb037ba4c60d7def16b49c9dbbfb22c75",
          "name": "Nick Satterly",
          "nickname": "satterly",
          "email": "nfsatterly@gmail.com",
          "email_verified": true,
          "website": "http://alerta.io",
          "profile": "https://gitlab.com/satterly",
          "picture": "https://secure.gravatar.com/avatar/520444488b63424244e4c90a5b943b91?s=80&d=identicon",
          "groups": [
            "team-alerta",
            "alertaio",
            "alerta-project",
            "team-alerta/core",
            "team-alerta/cli",
            "team-alerta/sdk"
          ]
        }
        """

        m.get('https://gitlab.com/.well-known/openid-configuration', text=discovery_doc)
        m.post('https://gitlab.com/oauth/token', text=access_token)
        m.get('https://gitlab.com/oauth/token/info', text=tokeninfo)
        m.get('https://gitlab.com/oauth/userinfo', text=userinfo)

        self.app = create_app(test_config)
        self.client = self.app.test_client()

        with self.app.test_request_context('/'):
            self.app.preprocess_request()
            self.api_key = ApiKey(
                user='admin@alerta.io',
                scopes=[Scope.admin, Scope.read, Scope.write],
                text='demo-key'
            )
            self.api_key.create()

        self.headers = {
            'Authorization': 'Key %s' % self.api_key.key,
            'Content-type': 'application/json'
        }

        # add customer mapping
        payload = {
            'customer': 'Alerta IO',
            'match': 'alertaio'
        }
        response = self.client.post('/customer', data=json.dumps(payload),
                                    content_type='application/json', headers=self.headers)
        self.assertEqual(response.status_code, 201)

        response = self.client.post('/auth/gitlab', data=authorization_grant, content_type='application/json')
        self.assertEqual(response.status_code, 200, response.data)
        data = json.loads(response.data.decode('utf-8'))
        claims = jwt.decode(data['token'], verify=False)

        self.assertEqual(claims['name'], 'Nick Satterly', claims)
        self.assertEqual(claims['preferred_username'], 'satterly', claims)
        self.assertEqual(claims['provider'], 'openid', claims)
        self.assertEqual(claims['groups'],
                         ['team-alerta', 'alertaio', 'alerta-project',
                             'team-alerta/core', 'team-alerta/cli', 'team-alerta/sdk'],
                         claims)
        self.assertEqual(claims['scope'], 'read write', claims)
        self.assertEqual(claims['email'], 'nfsatterly@gmail.com', claims)
        self.assertEqual(claims.get('email_verified'), True, claims)
        self.assertEqual(claims['customers'], ['Alerta IO'], claims)

    @requests_mock.mock()
    def test_google(self, m):

        test_config = {
            'TESTING': True,
            'AUTH_REQUIRED': True,
            'AUTH_PROVIDER': 'google',
            # 'OIDC_ISSUER_URL': 'https://accounts.google.com',
            'CUSTOMER_VIEWS': True,
        }

        authorization_grant = """
        {
          "code": "4/HAGPqNLjICAusQsYooo85izagxMM-_KJe2ZrEO7_lRPY7sG7-G79KMt-aZu-L6DF8Yy-Umb5iNXMdzFC041PdEE",
          "clientId": "736147134702-glkb1pesv716j1utg4llg7c3rr7nnhli.apps.googleusercontent.com",
          "redirectUri": "http://local.alerta.io:8000"
        }
        """

        discovery_doc = """
        {
          "issuer": "https://accounts.google.com",
          "authorization_endpoint": "https://accounts.google.com/o/oauth2/v2/auth",
          "token_endpoint": "https://oauth2.googleapis.com/token",
          "userinfo_endpoint": "https://openidconnect.googleapis.com/v1/userinfo",
          "revocation_endpoint": "https://oauth2.googleapis.com/revoke",
          "jwks_uri": "https://www.googleapis.com/oauth2/v3/certs",
          "response_types_supported": [
            "code",
            "token",
            "id_token",
            "code token",
            "code id_token",
            "token id_token",
            "code token id_token",
            "none"
          ],
          "subject_types_supported": [
            "public"
          ],
          "id_token_signing_alg_values_supported": [
            "RS256"
          ],
          "scopes_supported": [
            "openid",
            "email",
            "profile"
          ],
          "token_endpoint_auth_methods_supported": [
            "client_secret_post",
            "client_secret_basic"
          ],
          "claims_supported": [
            "aud",
            "email",
            "email_verified",
            "exp",
            "family_name",
            "given_name",
            "iat",
            "iss",
            "locale",
            "name",
            "picture",
            "sub"
          ],
          "code_challenge_methods_supported": [
            "plain",
            "S256"
          ]
        }
        """

        access_token = """
        {
          "access_token": "ya29.GmPbBq199Kx4bH7wwQrAnuQ4F6DhVn9Y3qCVnalVqVnOcFhJSqV5dZiABs4jbS8LFyVFBBYy_VXLmCRt4h4eP7sN11NyIK1kj-7M0t1RB6GvKS1ElLZBjvVzDDCoHG3SFVJVZAc",
          "expires_in": 3599,
          "scope": "https://www.googleapis.com/auth/userinfo.profile https://www.googleapis.com/auth/userinfo.email openid",
          "token_type": "Bearer",
          "id_token": "eyJhbGciOiJSUzI1NiIsImtpZCI6ImE0MzEzZTdmZDFlOWUyYTRkZWQzYjI5MmQyYTdmNGU1MTk1NzQzMDgiLCJ0eXAiOiJKV1QifQ.eyJpc3MiOiJodHRwczovL2FjY291bnRzLmdvb2dsZS5jb20iLCJhenAiOiI3MzYxNDcxMzQ3MDItZ2xrYjFwZXN2NzE2ajF1dGc0bGxnN2MzcnI3bm5obGkuYXBwcy5nb29nbGV1c2VyY29udGVudC5jb20iLCJhdWQiOiI3MzYxNDcxMzQ3MDItZ2xrYjFwZXN2NzE2ajF1dGc0bGxnN2MzcnI3bm5obGkuYXBwcy5nb29nbGV1c2VyY29udGVudC5jb20iLCJzdWIiOiIxMDQwMDQ3NjQ4MjQwNjYzNTkzOTAiLCJlbWFpbCI6Im5mc2F0dGVybHlAZ21haWwuY29tIiwiZW1haWxfdmVyaWZpZWQiOnRydWUsImF0X2hhc2giOiJVY29QSlE5d3ZNYTljY2VLdmZHdXVBIiwibmFtZSI6Ik5pY2sgU2F0dGVybHkiLCJwaWN0dXJlIjoiaHR0cHM6Ly9saDYuZ29vZ2xldXNlcmNvbnRlbnQuY29tLy1KU2dzbjFpbFhhRS9BQUFBQUFBQUFBSS9BQUFBQUFBQUFMcy9pRFRybjFTdFo1Yy9zOTYtYy9waG90by5qcGciLCJnaXZlbl9uYW1lIjoiTmljayIsImZhbWlseV9uYW1lIjoiU2F0dGVybHkiLCJsb2NhbGUiOiJlbi1HQiIsImlhdCI6MTU1Mzg2MDE0MiwiZXhwIjoxNTUzODYzNzQyfQ.MM14xSL1E1VfHtoSUCqe1L8R6M8xY7tkr0D8PoMhOAGheXehUruGl9R73mI8ciALkqRWZJMWO-v7wgEEik9r5jJh3NbRGT0I4obQMKsKglyAvdYKl5_heB18tkg-p08EKt90CGW7bIHVyZbHPBqW0U1EvN34v2qpDv2OuErHSfJhPAY514i0EltRKhKf4t2PdbfDq6_iSz5cVCbAIzFHj7NRHL42GsYsxWohfF4OckXOQCScJk7upyFPKP2UZ14vkARIn5sagmyLynKvnXLtwwBx5n9zvsKyx63wrGsQDd8TfuN6kWM-eDI796QfW62iZ1-I0XAe_CJdjcpjA7M4Uw"
        }
        """

        userinfo = """
        {
          "sub": "104004764824066359390",
          "name": "Nick Satterly",
          "given_name": "Nick",
          "family_name": "Satterly",
          "picture": "https://lh6.googleusercontent.com/-JSgsn1ilXaE/AAAAAAAAAAI/AAAAAAAAALs/iDTrn1StZ5c/photo.jpg",
          "email": "nfsatterly@gmail.com",
          "email_verified": true,
          "locale": "en-GB"
        }
        """

        m.get('https://accounts.google.com/.well-known/openid-configuration', text=discovery_doc)
        m.post('https://oauth2.googleapis.com/token', text=access_token)
        m.get('https://openidconnect.googleapis.com/v1/userinfo', text=userinfo)

        self.app = create_app(test_config)
        self.client = self.app.test_client()

        with self.app.test_request_context('/'):
            self.app.preprocess_request()
            self.api_key = ApiKey(
                user='admin@alerta.io',
                scopes=[Scope.admin, Scope.read, Scope.write],
                text='demo-key'
            )
            self.api_key.create()

        self.headers = {
            'Authorization': 'Key %s' % self.api_key.key,
            'Content-type': 'application/json'
        }

        # add customer mapping
        payload = {
            'customer': 'Google Inc.',
            'match': 'gmail.com'
        }
        response = self.client.post('/customer', data=json.dumps(payload),
                                    content_type='application/json', headers=self.headers)
        self.assertEqual(response.status_code, 201)

        response = self.client.post('/auth/google', data=authorization_grant, content_type='application/json')
        self.assertEqual(response.status_code, 200, response.data)
        data = json.loads(response.data.decode('utf-8'))
        claims = jwt.decode(data['token'], verify=False)

        self.assertEqual(claims['name'], 'Nick Satterly', claims)
        self.assertEqual(claims['preferred_username'], 'nfsatterly@gmail.com', claims)
        self.assertEqual(claims['provider'], 'openid', claims)
        # self.assertEqual(claims['roles'], ['user'], claims)
        self.assertEqual(claims['scope'], 'read write', claims)
        self.assertEqual(claims['email'], 'nfsatterly@gmail.com', claims)
        self.assertEqual(claims.get('email_verified'), True, claims)
        self.assertEqual(claims['customers'], ['Google Inc.'], claims)

    @requests_mock.mock()
    def test_keycloak(self, m):

        test_config = {
            'TESTING': True,
            'AUTH_REQUIRED': True,
            'AUTH_PROVIDER': 'keycloak',
            'KEYCLOAK_URL': 'http://keycloak.local.alerta.io:9090',
            'KEYCLOAK_REALM': 'master',
            'OIDC_CUSTOM_CLAIM': 'roles',
            # 'OIDC_ISSUER_URL': 'http://keycloak.local.alerta.io:9090/auth/realms/master',
            # 'OIDC_ROLE_CLAIM': 'roles',
            'ALLOWED_OIDC_ROLES': ['alerta-project'],
            'CUSTOMER_VIEWS': True
        }

        authorization_grant = """
        {
          "code": "5b48d2b7-78fb-4399-bdd3-d3fa227270fe.9c3393ab-5150-4c5f-b131-b17dfbc098f6.077fc6f0-9eef-4d02-ade8-4220348ad3c4",
          "clientId": "alerta-ui",
          "redirectUri": "http://local.alerta.io:8000",
          "state": "67xpd400cg7"
        }
        """

        discovery_doc = """
        {
          "issuer": "http://keycloak.local.alerta.io:9090/auth/realms/master",
          "authorization_endpoint": "http://keycloak.local.alerta.io:9090/auth/realms/master/protocol/openid-connect/auth",
          "token_endpoint": "http://keycloak.local.alerta.io:9090/auth/realms/master/protocol/openid-connect/token",
          "token_introspection_endpoint": "http://keycloak.local.alerta.io:9090/auth/realms/master/protocol/openid-connect/token/introspect",
          "userinfo_endpoint": "http://keycloak.local.alerta.io:9090/auth/realms/master/protocol/openid-connect/userinfo",
          "end_session_endpoint": "http://keycloak.local.alerta.io:9090/auth/realms/master/protocol/openid-connect/logout",
          "jwks_uri": "http://keycloak.local.alerta.io:9090/auth/realms/master/protocol/openid-connect/certs",
          "check_session_iframe": "http://keycloak.local.alerta.io:9090/auth/realms/master/protocol/openid-connect/login-status-iframe.html",
          "grant_types_supported": [
            "authorization_code",
            "implicit",
            "refresh_token",
            "password",
            "client_credentials"
          ],
          "response_types_supported": [
            "code",
            "none",
            "id_token",
            "token",
            "id_token token",
            "code id_token",
            "code token",
            "code id_token token"
          ],
          "subject_types_supported": [
            "public",
            "pairwise"
          ],
          "id_token_signing_alg_values_supported": [
            "ES384",
            "RS384",
            "HS256",
            "HS512",
            "ES256",
            "RS256",
            "HS384",
            "ES512",
            "RS512"
          ],
          "userinfo_signing_alg_values_supported": [
            "ES384",
            "RS384",
            "HS256",
            "HS512",
            "ES256",
            "RS256",
            "HS384",
            "ES512",
            "RS512",
            "none"
          ],
          "request_object_signing_alg_values_supported": [
            "ES384",
            "RS384",
            "ES256",
            "RS256",
            "ES512",
            "RS512",
            "none"
          ],
          "response_modes_supported": [
            "query",
            "fragment",
            "form_post"
          ],
          "registration_endpoint": "http://keycloak.local.alerta.io:9090/auth/realms/master/clients-registrations/openid-connect",
          "token_endpoint_auth_methods_supported": [
            "private_key_jwt",
            "client_secret_basic",
            "client_secret_post",
            "client_secret_jwt"
          ],
          "token_endpoint_auth_signing_alg_values_supported": [
            "RS256"
          ],
          "claims_supported": [
            "sub",
            "iss",
            "auth_time",
            "name",
            "given_name",
            "family_name",
            "preferred_username",
            "email"
          ],
          "claim_types_supported": [
            "normal"
          ],
          "claims_parameter_supported": false,
          "scopes_supported": [
            "openid",
            "address",
            "email",
            "offline_access",
            "phone",
            "profile",
            "roles",
            "web-origins"
          ],
          "request_parameter_supported": true,
          "request_uri_parameter_supported": true,
          "code_challenge_methods_supported": [
            "plain",
            "S256"
          ],
          "tls_client_certificate_bound_access_tokens": true,
          "introspection_endpoint": "http://keycloak.local.alerta.io:9090/auth/realms/master/protocol/openid-connect/token/introspect"
        }
        """
        access_token = """
        {
          "access_token": "eyJhbGciOiJSUzI1NiIsInR5cCIgOiAiSldUIiwia2lkIiA6ICI2ODZicVdhRzB4Z2owWkxLVEJSWjVxaDItWmJKSHdCYTRlRmx3bncyLUtVIn0.eyJqdGkiOiI2MGRhY2NkNi05OGYzLTQ2NGQtODljMC1lMWI5OGQ3ZTY4MjQiLCJleHAiOjE1NTQwNjIwMTgsIm5iZiI6MCwiaWF0IjoxNTU0MDYxOTU4LCJpc3MiOiJodHRwOi8va2V5Y2xvYWsubG9jYWwuYWxlcnRhLmlvOjkwOTAvYXV0aC9yZWFsbXMvbWFzdGVyIiwiYXVkIjpbIm1hc3Rlci1yZWFsbSIsImFjY291bnQiXSwic3ViIjoiODlkNzI2M2EtYmQ3Ny00Y2ZjLWJlZjUtMjJlM2Y4ZmVjYzViIiwidHlwIjoiQmVhcmVyIiwiYXpwIjoiYWxlcnRhLXVpIiwiYXV0aF90aW1lIjoxNTU0MDYxOTU3LCJzZXNzaW9uX3N0YXRlIjoiN2VjZWMyODgtZWFmYy00ZTYyLWFhOTUtZmFmMTU3YTMxOGZmIiwiYWNyIjoiMSIsImFsbG93ZWQtb3JpZ2lucyI6WyJodHRwOi8vbG9jYWwuYWxlcnRhLmlvOjgwMDAiXSwicmVhbG1fYWNjZXNzIjp7InJvbGVzIjpbImNyZWF0ZS1yZWFsbSIsIm9mZmxpbmVfYWNjZXNzIiwiYWRtaW4iLCJ1bWFfYXV0aG9yaXphdGlvbiJdfSwicmVzb3VyY2VfYWNjZXNzIjp7Im1hc3Rlci1yZWFsbSI6eyJyb2xlcyI6WyJ2aWV3LWlkZW50aXR5LXByb3ZpZGVycyIsInZpZXctcmVhbG0iLCJtYW5hZ2UtaWRlbnRpdHktcHJvdmlkZXJzIiwiaW1wZXJzb25hdGlvbiIsImNyZWF0ZS1jbGllbnQiLCJtYW5hZ2UtdXNlcnMiLCJxdWVyeS1yZWFsbXMiLCJ2aWV3LWF1dGhvcml6YXRpb24iLCJxdWVyeS1jbGllbnRzIiwicXVlcnktdXNlcnMiLCJtYW5hZ2UtZXZlbnRzIiwibWFuYWdlLXJlYWxtIiwidmlldy1ldmVudHMiLCJ2aWV3LXVzZXJzIiwidmlldy1jbGllbnRzIiwibWFuYWdlLWF1dGhvcml6YXRpb24iLCJtYW5hZ2UtY2xpZW50cyIsInF1ZXJ5LWdyb3VwcyJdfSwiYWNjb3VudCI6eyJyb2xlcyI6WyJtYW5hZ2UtYWNjb3VudCIsIm1hbmFnZS1hY2NvdW50LWxpbmtzIiwidmlldy1wcm9maWxlIl19fSwic2NvcGUiOiJvcGVuaWQgcHJvZmlsZSBlbWFpbCIsImVtYWlsX3ZlcmlmaWVkIjp0cnVlLCJyb2xlcyI6WyJjcmVhdGUtcmVhbG0iLCJvZmZsaW5lX2FjY2VzcyIsImFkbWluIiwidW1hX2F1dGhvcml6YXRpb24iXSwibmFtZSI6Ik5pY2hvbGFzIFNhdHRlcmx5IiwicHJlZmVycmVkX3VzZXJuYW1lIjoibnNhdHRlcmwiLCJnaXZlbl9uYW1lIjoiTmljaG9sYXMiLCJmYW1pbHlfbmFtZSI6IlNhdHRlcmx5IiwiZW1haWwiOiJuZnNAYWxlcnRhLmRldiJ9.ROvp_FpReWVaWUn0pHDIfU6S8ZvxX_nLvIDxxosQCBOFHgGgjk-_VW0vgHBSKqxBbtEmOeSSrcovUToTL_N8emiWgrRteq4ZFhCCFNEXigvZGXCtjp5F-wugkoNM8N7seIlOgGQwH9jGwvV4U2PmOsvF6kl8JHifh5yyyUu3ab4Lxaw5fdT2_-vZocK6FaFGJCGbZ09mzLaubLCBpbgU6nssYlWLDVJfA5iNgfwIGvWCC_OFAP-NAx-BnUP4m3mv7GN2xNDqU4Bjhw5-fANxvWqZZVqS45BFJmdFm1WIhqybu3JIMf29s7ErntU6EoRs88_-pACVMW1-fpZCq_Nt4w",
          "expires_in": 60,
          "refresh_expires_in": 1800,
          "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCIgOiAiSldUIiwia2lkIiA6ICJjZDIwZTQ1Zi0yYzNiLTQ2NzAtOGQwZi0wNzVmOTllNjA5NTUifQ.eyJqdGkiOiJlZWY1MTczMC0zZWM1LTQ4MTktOWY5OC1lYmQyZTc4Y2QwYmIiLCJleHAiOjE1NTQwNjM3NTgsIm5iZiI6MCwiaWF0IjoxNTU0MDYxOTU4LCJpc3MiOiJodHRwOi8va2V5Y2xvYWsubG9jYWwuYWxlcnRhLmlvOjkwOTAvYXV0aC9yZWFsbXMvbWFzdGVyIiwiYXVkIjoiaHR0cDovL2tleWNsb2FrLmxvY2FsLmFsZXJ0YS5pbzo5MDkwL2F1dGgvcmVhbG1zL21hc3RlciIsInN1YiI6Ijg5ZDcyNjNhLWJkNzctNGNmYy1iZWY1LTIyZTNmOGZlY2M1YiIsInR5cCI6IlJlZnJlc2giLCJhenAiOiJhbGVydGEtdWkiLCJhdXRoX3RpbWUiOjAsInNlc3Npb25fc3RhdGUiOiI3ZWNlYzI4OC1lYWZjLTRlNjItYWE5NS1mYWYxNTdhMzE4ZmYiLCJyZWFsbV9hY2Nlc3MiOnsicm9sZXMiOlsiY3JlYXRlLXJlYWxtIiwib2ZmbGluZV9hY2Nlc3MiLCJhZG1pbiIsInVtYV9hdXRob3JpemF0aW9uIl19LCJyZXNvdXJjZV9hY2Nlc3MiOnsibWFzdGVyLXJlYWxtIjp7InJvbGVzIjpbInZpZXctaWRlbnRpdHktcHJvdmlkZXJzIiwidmlldy1yZWFsbSIsIm1hbmFnZS1pZGVudGl0eS1wcm92aWRlcnMiLCJpbXBlcnNvbmF0aW9uIiwiY3JlYXRlLWNsaWVudCIsIm1hbmFnZS11c2VycyIsInF1ZXJ5LXJlYWxtcyIsInZpZXctYXV0aG9yaXphdGlvbiIsInF1ZXJ5LWNsaWVudHMiLCJxdWVyeS11c2VycyIsIm1hbmFnZS1ldmVudHMiLCJtYW5hZ2UtcmVhbG0iLCJ2aWV3LWV2ZW50cyIsInZpZXctdXNlcnMiLCJ2aWV3LWNsaWVudHMiLCJtYW5hZ2UtYXV0aG9yaXphdGlvbiIsIm1hbmFnZS1jbGllbnRzIiwicXVlcnktZ3JvdXBzIl19LCJhY2NvdW50Ijp7InJvbGVzIjpbIm1hbmFnZS1hY2NvdW50IiwibWFuYWdlLWFjY291bnQtbGlua3MiLCJ2aWV3LXByb2ZpbGUiXX19LCJzY29wZSI6Im9wZW5pZCBwcm9maWxlIGVtYWlsIn0.IJEIKMAhTinHKRMjULLWzbfK-DGkjo0oznYuUOmGhqU",
          "token_type": "bearer",
          "id_token": "eyJhbGciOiJSUzI1NiIsInR5cCIgOiAiSldUIiwia2lkIiA6ICI2ODZicVdhRzB4Z2owWkxLVEJSWjVxaDItWmJKSHdCYTRlRmx3bncyLUtVIn0.eyJqdGkiOiJiNjZlNzEwNi0xMjhiLTRiNDItYjU4Ni1iOGIyYmVkNzU5ZjEiLCJleHAiOjE1NTQwNjIwMTgsIm5iZiI6MCwiaWF0IjoxNTU0MDYxOTU4LCJpc3MiOiJodHRwOi8va2V5Y2xvYWsubG9jYWwuYWxlcnRhLmlvOjkwOTAvYXV0aC9yZWFsbXMvbWFzdGVyIiwiYXVkIjoiYWxlcnRhLXVpIiwic3ViIjoiODlkNzI2M2EtYmQ3Ny00Y2ZjLWJlZjUtMjJlM2Y4ZmVjYzViIiwidHlwIjoiSUQiLCJhenAiOiJhbGVydGEtdWkiLCJhdXRoX3RpbWUiOjE1NTQwNjE5NTcsInNlc3Npb25fc3RhdGUiOiI3ZWNlYzI4OC1lYWZjLTRlNjItYWE5NS1mYWYxNTdhMzE4ZmYiLCJhY3IiOiIxIiwiZW1haWxfdmVyaWZpZWQiOnRydWUsInJvbGVzIjpbImNyZWF0ZS1yZWFsbSIsIm9mZmxpbmVfYWNjZXNzIiwiYWRtaW4iLCJ1bWFfYXV0aG9yaXphdGlvbiJdLCJuYW1lIjoiTmljaG9sYXMgU2F0dGVybHkiLCJwcmVmZXJyZWRfdXNlcm5hbWUiOiJuc2F0dGVybCIsImdpdmVuX25hbWUiOiJOaWNob2xhcyIsImZhbWlseV9uYW1lIjoiU2F0dGVybHkiLCJlbWFpbCI6Im5mc0BhbGVydGEuZGV2In0.W-4pdC3IqpHuwqXZsybZBrIeiSZ701K7bQa_DFS8oOhyVqERnmQdiTdoZuQCQCxhU6XzwGayhNEo3PtCUH6deioWmXo9wWXWBv0d8qbifc3udtGCHv-mXEom9yelYr_bVZaJ941B8AXh3rzhk5JEsBaepUEe2INLVFTxactcmnRYV7YZcU1ouMIoiLM4nyRlR9V5ewxrVn0l_8XHk209cOYbkHxP20HGRekwqbo25wDwHxkjGb1qqu2UdsaAGkyKeiEN-av5YGtUSyAbUkE7PL7EL_wDYXCK7NHT8xMMYjSQ7rGHQ60B4tRvsQ7FUson9G1KnsYvm4o8mLnU4B82rQ",
          "not-before-policy": 0,
          "session_state": "7ecec288-eafc-4e62-aa95-faf157a318ff",
          "scope": "openid profile email"
        }
        """

        userinfo = """
        {
          "sub": "89d7263a-bd77-4cfc-bef5-22e3f8fecc5b",
          "email_verified": true,
          "roles": [
            "create-realm",
            "offline_access",
            "admin",
            "uma_authorization"
          ],
          "name": "Nicholas Satterly",
          "preferred_username": "nsatterl",
          "given_name": "Nicholas",
          "family_name": "Satterly",
          "email": "nfs@alerta.dev"
        }
        """

        m.get('http://keycloak.local.alerta.io:9090/auth/realms/master/.well-known/openid-configuration', text=discovery_doc)
        m.post('http://keycloak.local.alerta.io:9090/auth/realms/master/protocol/openid-connect/token', text=access_token)
        m.get('http://keycloak.local.alerta.io:9090/auth/realms/master/protocol/openid-connect/userinfo', text=userinfo)

        self.app = create_app(test_config)
        self.client = self.app.test_client()

        with self.app.test_request_context('/'):
            self.app.preprocess_request()
            self.api_key = ApiKey(
                user='admin@alerta.io',
                scopes=[Scope.admin, Scope.read, Scope.write],
                text='demo-key'
            )
            self.api_key.create()

        self.headers = {
            'Authorization': 'Key %s' % self.api_key.key,
            'Content-type': 'application/json'
        }

        # add customer mapping
        payload = {
            'customer': 'Domain Customer',
            'match': 'alerta.dev'
        }
        response = self.client.post('/customer', data=json.dumps(payload),
                                    content_type='application/json', headers=self.headers)
        self.assertEqual(response.status_code, 201)

        response = self.client.post('/auth/keycloak', data=authorization_grant, content_type='application/json')
        self.assertEqual(response.status_code, 200, response.data)
        data = json.loads(response.data.decode('utf-8'))
        claims = jwt.decode(data['token'], verify=False)

        self.assertEqual(claims['name'], 'Nicholas Satterly', claims)
        self.assertEqual(claims['preferred_username'], 'nsatterl', claims)
        self.assertEqual(claims['provider'], 'openid', claims)
        self.assertEqual(claims['roles'], ['create-realm', 'offline_access', 'admin', 'uma_authorization'], claims)
        self.assertEqual(claims['scope'], 'read write', claims)
        self.assertEqual(claims['email'], 'nfs@alerta.dev', claims)
        self.assertEqual(claims.get('email_verified'), True, claims)
        self.assertEqual(claims['customers'], ['Domain Customer'], claims)

    @requests_mock.mock()
    def test_openid_auth0(self, m):

        test_config = {
            'TESTING': True,
            'AUTH_REQUIRED': True,
            'AUTH_PROVIDER': 'openid',
            'OIDC_ISSUER_URL': 'https://dev-66191jdr.eu.auth0.com/',
            'CUSTOMER_VIEWS': True
        }

        authorization_grant = """
        {
          "code": "q79ntL3d9mzPFAU-",
          "clientId": "LMMEZSlPYKvM14cFxnWNWkC4DgvRk0dZ",
          "redirectUri": "http://local.alerta.io:8000",
          "state": "051pvr3x5e4y"
        }
        """

        discovery_doc = """
        {
          "issuer": "https://dev-66191jdr.eu.auth0.com/",
          "authorization_endpoint": "https://dev-66191jdr.eu.auth0.com/authorize",
          "token_endpoint": "https://dev-66191jdr.eu.auth0.com/oauth/token",
          "userinfo_endpoint": "https://dev-66191jdr.eu.auth0.com/userinfo",
          "mfa_challenge_endpoint": "https://dev-66191jdr.eu.auth0.com/mfa/challenge",
          "jwks_uri": "https://dev-66191jdr.eu.auth0.com/.well-known/jwks.json",
          "registration_endpoint": "https://dev-66191jdr.eu.auth0.com/oidc/register",
          "revocation_endpoint": "https://dev-66191jdr.eu.auth0.com/oauth/revoke",
          "scopes_supported": [
            "openid",
            "profile",
            "offline_access",
            "name",
            "given_name",
            "family_name",
            "nickname",
            "email",
            "email_verified",
            "picture",
            "created_at",
            "identities",
            "phone",
            "address"
          ],
          "response_types_supported": [
            "code",
            "token",
            "id_token",
            "code token",
            "code id_token",
            "token id_token",
            "code token id_token"
          ],
          "response_modes_supported": [
            "query",
            "fragment",
            "form_post"
          ],
          "subject_types_supported": [
            "public"
          ],
          "id_token_signing_alg_values_supported": [
            "HS256",
            "RS256"
          ],
          "token_endpoint_auth_methods_supported": [
            "client_secret_basic",
            "client_secret_post"
          ],
          "claims_supported": [
            "aud",
            "auth_time",
            "created_at",
            "email",
            "email_verified",
            "exp",
            "family_name",
            "given_name",
            "iat",
            "identities",
            "iss",
            "name",
            "nickname",
            "phone_number",
            "picture",
            "sub"
          ],
          "request_uri_parameter_supported": false
        }
        """

        access_token = """
        {
          "access_token": "h2JFhciS6loTegmGVvGrap5rXZlO-MLg",
          "id_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6Ik1qZEZOakl4TmpoRk4wWTROMEU0UmtGQ09EVXlRekF5TVVOQlF6a3hRak5GTURJMk1rVXlNQSJ9.eyJuaWNrbmFtZSI6ImFkbWluIiwibmFtZSI6ImFkbWluQGFsZXJ0YS5kZXYiLCJwaWN0dXJlIjoiaHR0cHM6Ly9zLmdyYXZhdGFyLmNvbS9hdmF0YXIvMzA2YTMxOTRmYzZhNzJkZTk1OTE3MWQyMjQyZjMxYTc_cz00ODAmcj1wZyZkPWh0dHBzJTNBJTJGJTJGY2RuLmF1dGgwLmNvbSUyRmF2YXRhcnMlMkZhZC5wbmciLCJ1cGRhdGVkX2F0IjoiMjAxOS0wMy0zMFQwNjo1ODozNS4yNTZaIiwiZW1haWwiOiJhZG1pbkBhbGVydGEuZGV2IiwiZW1haWxfdmVyaWZpZWQiOmZhbHNlLCJpc3MiOiJodHRwczovL2Rldi02NjE5MWpkci5ldS5hdXRoMC5jb20vIiwic3ViIjoiYXV0aDB8NWM5ZjEwNmQxODUxOGMxMWI3MGNhZTk5IiwiYXVkIjoiTE1NRVpTbFBZS3ZNMTRjRnhuV05Xa0M0RGd2UmswZFoiLCJpYXQiOjE1NTM5Mjk1NzYsImV4cCI6MTU1Mzk2NTU3Nn0.lTiboCdvtzIpFWnX2sOqtAgrY5UDe15HjVaiDUPkZPXGpx837o85IVq6YL0OFu2OOqZI3jD_7G-0GsWJpTW7EsIzNfFmWF2s0mTHf0fz1ab6bwBBANEPnAgbbGf-ZyNJNrVdhqy3cJJjpdyc5_9U2Y8ZCzC9wX0f1Fc-0d7sIFJQfLH-GHzoCtKeI7nqSQus8NCS8cToPcw_V7kkgsSSiG4ZRxwymcxANeXqWKoyT2GrOEIGWZZBznwXDu5l42QNvSFkueQjCF9Q5IB7O0G3lRVwssEBQXE6VRymGQjDnN5Ie-66dPQwX7YEbNbOQXCkQqvy8v52yUmlltMwcjToHQ",
          "scope": "openid profile email",
          "expires_in": 86400,
          "token_type": "Bearer"
        }
        """

        userinfo = """
        {
          "sub": "auth0|5c9f106d18518c11b70cae99",
          "nickname": "admin",
          "name": "admin@alerta.dev",
          "picture": "https://s.gravatar.com/avatar/306a3194fc6a72de959171d2242f31a7?s=480&r=pg&d=https%3A%2F%2Fcdn.auth0.com%2Favatars%2Fad.png",
          "updated_at": "2019-03-30T06:58:35.256Z",
          "email": "admin@alerta.dev",
          "email_verified": false
        }
        """

        m.get('https://dev-66191jdr.eu.auth0.com/.well-known/openid-configuration', text=discovery_doc)
        m.post('https://dev-66191jdr.eu.auth0.com/oauth/token', text=access_token)
        m.get('https://dev-66191jdr.eu.auth0.com/userinfo', text=userinfo)

        self.app = create_app(test_config)
        self.client = self.app.test_client()

        with self.app.test_request_context('/'):
            self.app.preprocess_request()
            self.api_key = ApiKey(
                user='admin@alerta.io',
                scopes=[Scope.admin, Scope.read, Scope.write],
                text='demo-key'
            )
            self.api_key.create()

        self.headers = {
            'Authorization': 'Key %s' % self.api_key.key,
            'Content-type': 'application/json'
        }

        # add customer mapping
        payload = {
            'customer': 'Foo Corp',
            'match': 'admin'
        }
        response = self.client.post('/customer', data=json.dumps(payload),
                                    content_type='application/json', headers=self.headers)
        self.assertEqual(response.status_code, 201)

        response = self.client.post('/auth/openid', data=authorization_grant, content_type='application/json')
        self.assertEqual(response.status_code, 200, response.data)
        data = json.loads(response.data.decode('utf-8'))
        claims = jwt.decode(data['token'], verify=False)

        self.assertEqual(claims['name'], 'admin@alerta.dev', claims)
        self.assertEqual(claims['preferred_username'], 'admin', claims)
        self.assertEqual(claims['provider'], 'openid', claims)
        # self.assertEqual(claims['roles'], ['user'], claims)
        self.assertEqual(claims['scope'], 'read write', claims)
        self.assertEqual(claims['email'], 'admin@alerta.dev', claims)
        self.assertEqual(claims.get('email_verified'), False, claims)
        self.assertEqual(claims['customers'], ['Foo Corp'], claims)

    @requests_mock.mock()
    def test_openid_okta(self, m):

        test_config = {
            'TESTING': True,
            'AUTH_REQUIRED': True,
            'AUTH_PROVIDER': 'openid',
            'OIDC_ISSUER_URL': 'https://dev-490527.okta.com/oauth2/default',
            'OIDC_ROLE_CLAIM': 'groups',
            # 'OIDC_CUSTOM_CLAIM': 'groups',
            'CUSTOMER_VIEWS': True,
        }

        authorization_grant = """
        {
          "code": "tdjeq4_jMQ0P9K-4Csod",
          "clientId": "0oac5s46zwh5crGiH356",
          "redirectUri": "http://local.alerta.io:8000",
          "state": "p3hmwtujboq"
        }
        """

        discovery_doc = """
        {
          "issuer": "https://dev-490527.okta.com/oauth2/default",
          "authorization_endpoint": "https://dev-490527.okta.com/oauth2/default/v1/authorize",
          "token_endpoint": "https://dev-490527.okta.com/oauth2/default/v1/token",
          "userinfo_endpoint": "https://dev-490527.okta.com/oauth2/default/v1/userinfo",
          "registration_endpoint": "https://dev-490527.okta.com/oauth2/v1/clients",
          "jwks_uri": "https://dev-490527.okta.com/oauth2/default/v1/keys",
          "response_types_supported": [
            "code",
            "id_token",
            "code id_token",
            "code token",
            "id_token token",
            "code id_token token"
          ],
          "response_modes_supported": [
            "query",
            "fragment",
            "form_post",
            "okta_post_message"
          ],
          "grant_types_supported": [
            "authorization_code",
            "implicit",
            "refresh_token",
            "password"
          ],
          "subject_types_supported": [
            "public"
          ],
          "id_token_signing_alg_values_supported": [
            "RS256"
          ],
          "scopes_supported": [
            "openid",
            "profile",
            "email",
            "address",
            "phone",
            "offline_access"
          ],
          "token_endpoint_auth_methods_supported": [
            "client_secret_basic",
            "client_secret_post",
            "client_secret_jwt",
            "private_key_jwt",
            "none"
          ],
          "claims_supported": [
            "iss",
            "ver",
            "sub",
            "aud",
            "iat",
            "exp",
            "jti",
            "auth_time",
            "amr",
            "idp",
            "nonce",
            "name",
            "nickname",
            "preferred_username",
            "given_name",
            "middle_name",
            "family_name",
            "email",
            "email_verified",
            "profile",
            "zoneinfo",
            "locale",
            "address",
            "phone_number",
            "picture",
            "website",
            "gender",
            "birthdate",
            "updated_at",
            "at_hash",
            "c_hash"
          ],
          "code_challenge_methods_supported": [
            "S256"
          ],
          "introspection_endpoint": "https://dev-490527.okta.com/oauth2/default/v1/introspect",
          "introspection_endpoint_auth_methods_supported": [
            "client_secret_basic",
            "client_secret_post",
            "client_secret_jwt",
            "private_key_jwt",
            "none"
          ],
          "revocation_endpoint": "https://dev-490527.okta.com/oauth2/default/v1/revoke",
          "revocation_endpoint_auth_methods_supported": [
            "client_secret_basic",
            "client_secret_post",
            "client_secret_jwt",
            "private_key_jwt",
            "none"
          ],
          "end_session_endpoint": "https://dev-490527.okta.com/oauth2/default/v1/logout",
          "request_parameter_supported": true,
          "request_object_signing_alg_values_supported": [
            "HS256",
            "HS384",
            "HS512",
            "RS256",
            "RS384",
            "RS512",
            "ES256",
            "ES384",
            "ES512"
          ]
        }
        """

        access_token = """
        {
          "access_token": "eyJraWQiOiJLRnZiSVpNamprNkdyNDdTckVLTzhUZ2VlU3N3amxRMzNYN0pDZ2NuZVBrIiwiYWxnIjoiUlMyNTYifQ.eyJ2ZXIiOjEsImp0aSI6IkFULlFVZTdDNW1MTmFnT0xVU3VISXdyZFBXN2lPOHVRREdpTVJpS213ZEFZcTQiLCJpc3MiOiJodHRwczovL2Rldi00OTA1Mjcub2t0YS5jb20vb2F1dGgyL2RlZmF1bHQiLCJhdWQiOiJhcGk6Ly9kZWZhdWx0IiwiaWF0IjoxNTUzOTgyMjgzLCJleHAiOjE1NTM5ODU4ODMsImNpZCI6IjBvYWM1czQ2endoNWNyR2lIMzU2IiwidWlkIjoiMDB1YzVzb3BjZWI4OWg1U2szNTYiLCJzY3AiOlsib3BlbmlkIiwicHJvZmlsZSIsImVtYWlsIl0sInN1YiI6Im5mc0BhbGVydGEuZGV2In0.AnQ4r4lXCHRg3kyzFd8uL-5Hgb-9KcAxcjkc32CkJiOogtyp0a3IVHJN6usgl2qTbMxur4R1pMgwn9MlZ4njiflkmADctcrsD5iLtCCzS8AC59XQJsq9xHjAfdRfuaqsWL00Fz2XRyjr3fZmLPzgP7RXXf96Efho9lhefZuSUPaSO46JSdPlTG-_wxTVhaxwLI_b405Dqfv_kS3Ksv5gevbAAHQ8_WRtzNzQoPN_8WR-XO6XHYgC7xKW3yiu01Yn59YRouzIDtQKXNRPMr2CigwbMw2lkikL9eYqLozQ6O7_h2o1pd-X_oJ1QbNyOBjnynIlwS3S9Aws3B-N_KhtSQ",
          "token_type": "Bearer",
          "expires_in": 3600,
          "scope": "openid profile email",
          "id_token": "eyJraWQiOiJLRnZiSVpNamprNkdyNDdTckVLTzhUZ2VlU3N3amxRMzNYN0pDZ2NuZVBrIiwiYWxnIjoiUlMyNTYifQ.eyJzdWIiOiIwMHVjNXNvcGNlYjg5aDVTazM1NiIsIm5hbWUiOiJOaWNrIFNhdHRlcmx5IiwiZW1haWwiOiJuZnNAYWxlcnRhLmRldiIsInZlciI6MSwiaXNzIjoiaHR0cHM6Ly9kZXYtNDkwNTI3Lm9rdGEuY29tL29hdXRoMi9kZWZhdWx0IiwiYXVkIjoiMG9hYzVzNDZ6d2g1Y3JHaUgzNTYiLCJpYXQiOjE1NTM5ODIyODMsImV4cCI6MTU1Mzk4NTg4MywianRpIjoiSUQuTHhEWGFOV2VibVRUekxmVHMxUXBBa05pem50VldaNDYycTZFMGlWZE9SOCIsImFtciI6WyJwd2QiXSwiaWRwIjoiMDBvYzVzb21nRXJJWHdjRDgzNTYiLCJwcmVmZXJyZWRfdXNlcm5hbWUiOiJuZnNAYWxlcnRhLmRldiIsImF1dGhfdGltZSI6MTU1Mzk3MDM5NSwiYXRfaGFzaCI6IjFTbUJKN0s4UkN3dXcxeWJVV1ptdHcifQ.AyWlF4UCBRmdXDJHP6tvu5Z1QjBDzNjXZPKtRtOVdJRhIEMB5rfDMgYh5eBbv5aoK_ZYeHtSNRpXHgof6OldEWZnl8dac-iRiHeFMR65p7YqCpbxzbzYPcDuIbGY_MffGNbH34dDSFruKGg2He8atUwSIczxzMP_5kLgZk2oCMU7S_Uijzf5eosho7AOQ-ybAaWDlxLrxdH8Q0kCfdWcOu0JHFHFlh0-VvCWQVe4uZ6rGdl8_OdaeVdt6xHukEYQTR1QWmmAejEccQ04mgHmgHAjGxNAsXMzOT9mE-FQaDdQkbnap97jYWtIKp78580A5InJedJ3fn_c3brIo2MZYQ"
        }
        """

        userinfo = """
        {
          "sub": "00uc5sopceb89h5Sk356",
          "name": "Nick Satterly",
          "locale": "en-US",
          "email": "nfs@alerta.dev",
          "preferred_username": "nfs@alerta.dev",
          "given_name": "Nick",
          "family_name": "Satterly",
          "zoneinfo": "America/Los_Angeles",
          "updated_at": 1551995091,
          "email_verified": true,
          "groups": [
            "Everyone"
          ]
        }
        """

        m.get('https://dev-490527.okta.com/oauth2/default/.well-known/openid-configuration', text=discovery_doc)
        m.post('https://dev-490527.okta.com/oauth2/default/v1/token', text=access_token)
        m.get('https://dev-490527.okta.com/oauth2/default/v1/userinfo', text=userinfo)

        self.app = create_app(test_config)
        self.client = self.app.test_client()

        with self.app.test_request_context('/'):
            self.app.preprocess_request()
            self.api_key = ApiKey(
                user='admin@alerta.io',
                scopes=[Scope.admin, Scope.read, Scope.write],
                text='demo-key'
            )
            self.api_key.create()

        self.headers = {
            'Authorization': 'Key %s' % self.api_key.key,
            'Content-type': 'application/json'
        }

        # add customer mapping
        payload = {
            'customer': 'Alerta Dev',
            'match': 'nfs@alerta.dev'
        }
        response = self.client.post('/customer', data=json.dumps(payload),
                                    content_type='application/json', headers=self.headers)
        self.assertEqual(response.status_code, 201)

        response = self.client.post('/auth/openid', data=authorization_grant, content_type='application/json')
        self.assertEqual(response.status_code, 200, response.data)
        data = json.loads(response.data.decode('utf-8'))
        claims = jwt.decode(data['token'], verify=False)

        self.assertEqual(claims['scope'], 'read write', claims)
        self.assertEqual(claims['name'], 'Nick Satterly', claims)
        self.assertEqual(claims['preferred_username'], 'nfs@alerta.dev', claims)
        self.assertEqual(claims['provider'], 'openid', claims)
        self.assertEqual(claims['groups'], ['Everyone'], claims)
        self.assertEqual(claims['scope'], 'read write', claims)
        self.assertEqual(claims['email'], 'nfs@alerta.dev', claims)
        self.assertEqual(claims.get('email_verified'), True, claims)
        self.assertEqual(claims['customers'], ['Alerta Dev'], claims)
