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
    def test_amazon_cognito(self, m):

        test_config = {
            'TESTING': True,
            'AUTH_REQUIRED': True,
            'AUTH_PROVIDER': 'cognito',
            'AWS_REGION': 'eu-west-1',
            'COGNITO_USER_POOL_ID': 'eu-west-1_BMkhxuZsn',
            'COGNITO_DOMAIN': 'alerta-webui',
            'CUSTOMER_VIEWS': True,
        }

        authorization_grant = """
        {
          "code": "9273a057-f70a-4056-b6b9-20f4f768db05",
          "clientId": "6gms81dft7up216pqnv7pcq194",
          "redirectUri": "http://localhost:8000",
          "state": "mlmie0tj03i"
        }
        """

        discovery_doc = """
        {
          "authorization_endpoint": "https://alerta-webui.auth.eu-west-1.amazoncognito.com/oauth2/authorize",
          "id_token_signing_alg_values_supported": [
            "RS256"
          ],
          "issuer": "https://cognito-idp.eu-west-1.amazonaws.com/eu-west-1_BMkhxuZsn",
          "jwks_uri": "https://cognito-idp.eu-west-1.amazonaws.com/eu-west-1_BMkhxuZsn/.well-known/jwks.json",
          "response_types_supported": [
            "code",
            "token",
            "token id_token"
          ],
          "scopes_supported": [
            "openid",
            "email",
            "phone",
            "profile"
          ],
          "subject_types_supported": [
            "public"
          ],
          "token_endpoint": "https://alerta-webui.auth.eu-west-1.amazoncognito.com/oauth2/token",
          "token_endpoint_auth_methods_supported": [
            "client_secret_basic",
            "client_secret_post"
          ],
          "userinfo_endpoint": "https://alerta-webui.auth.eu-west-1.amazoncognito.com/oauth2/userInfo"
        }
        """

        access_token = """
        {
          "id_token": "eyJraWQiOiJUWnhDZzJCMEZqRTAyaEFhWnRuXC9XSE9abURiaG5sXC91amlGdDd6aWhzOHc9IiwiYWxnIjoiUlMyNTYifQ.eyJhdF9oYXNoIjoiWW9ENFpfY0FKWUVUNTBUNnZpYVlkUSIsInN1YiI6IjM4ZmFmMWU4LTYzODQtNDU5OC04MWI1LTg0ZjQzZTkxYjNkYyIsImVtYWlsX3ZlcmlmaWVkIjp0cnVlLCJpc3MiOiJodHRwczpcL1wvY29nbml0by1pZHAuZXUtd2VzdC0xLmFtYXpvbmF3cy5jb21cL2V1LXdlc3QtMV9CTWtoeHVac24iLCJjb2duaXRvOnVzZXJuYW1lIjoic2F0dGVybHkiLCJwcmVmZXJyZWRfdXNlcm5hbWUiOiJzYXR0ZXJseSIsImdpdmVuX25hbWUiOiJOaWNrIiwicGljdHVyZSI6Imh0dHBzOlwvXC9hdmF0YWFhcnMuaW9cLyIsImF1ZCI6IjZnbXM4MWRmdDd1cDIxNnBxbnY3cGNxMTk0IiwidG9rZW5fdXNlIjoiaWQiLCJhdXRoX3RpbWUiOjE1NjEwNDI2OTksIm5hbWUiOiJOaWNrIFNhdHRlcmx5IiwiZXhwIjoxNTYxMDQ2Mjk5LCJpYXQiOjE1NjEwNDI2OTksImZhbWlseV9uYW1lIjoiU2F0dGVybHkiLCJlbWFpbCI6Im5mc2F0dGVybHkrMkBnbWFpbC5jb20ifQ.OgRHqVXzC5QCcUiioPPUJaA4O6X98XhWHPYhmjs5GzQCeSaUPVT3j45NyKqNDpkUKX3R-sijw57A4tc3MMHzr8EnLKAyr445GpqchCVGq0ntNixy0WamM073MvVSXN9ST2BZI4bu84AiGWV4D9YiqnhPt_kUEhaRxwvf9CDXPECLjlh-LHmQp5w06vI_itAJ_n6mEVHACXRNdQfSLhHbr4znWqOnQW40BP3gU3i-RulMJWjJGgDl94-dIfhqzvwRX0_k3Fnq7iYm1oz2DC8XvNiQqNCwt9Qfv7fU_pLTZkxTA2EBE3RiQnlgH4RNhZFrF_cH4kH8KRO2Hpoai57sVA",
          "access_token": "eyJraWQiOiJVeTEyVzZzOXNrZUJ3SGxBREtsdm5hVUp3TURFRjFxbmtGR01XOWU3NjFFPSIsImFsZyI6IlJTMjU2In0.eyJzdWIiOiIzOGZhZjFlOC02Mzg0LTQ1OTgtODFiNS04NGY0M2U5MWIzZGMiLCJ0b2tlbl91c2UiOiJhY2Nlc3MiLCJzY29wZSI6Im9wZW5pZCBwcm9maWxlIGVtYWlsIiwiYXV0aF90aW1lIjoxNTYxMDQyNjk5LCJpc3MiOiJodHRwczpcL1wvY29nbml0by1pZHAuZXUtd2VzdC0xLmFtYXpvbmF3cy5jb21cL2V1LXdlc3QtMV9CTWtoeHVac24iLCJleHAiOjE1NjEwNDYyOTksImlhdCI6MTU2MTA0MjY5OSwidmVyc2lvbiI6MiwianRpIjoiZWZkZjBmYzgtYWEwNi00M2I5LThkMmMtN2Y3MjY2OTgyZjFkIiwiY2xpZW50X2lkIjoiNmdtczgxZGZ0N3VwMjE2cHFudjdwY3ExOTQiLCJ1c2VybmFtZSI6InNhdHRlcmx5In0.QhNLAYaEG1c69yJq9-839FJ5q-Sq70IGlHFT2HeGzN_Qxx_qLBH_lZ5VNKPXxyeVAjP2Rj5EMWO0F1ygN8LrqgWaBTXw2Uw3BrfBwtfBVqQW4OFl0jg97FKrEAK9YT25zCm9HkCBdIeKVrhdY4-44w-5_JuBPevW9yzcZ5ApX5zpk4Z4aXGa32l8NYZAObxU3TDxPsCM4LKZVs7Slc1f2vzT93dll2jYg2_K6Kz9IFQkIfmRhxbNdwOsqXn3cHTtajEG-tHXG8Epsiy0ssiA1H9PQRE1It_LNMcc1RE-A34Yr1s0YGeqi10ntw-W2crtXzo-AS1YQ-gAkluAjeKe4A",
          "refresh_token": "eyJjdHkiOiJKV1QiLCJlbmMiOiJBMjU2R0NNIiwiYWxnIjoiUlNBLU9BRVAifQ.JxxBNOUNsqi4aGIaXVg6BqxYMKbeLEFCsKg2STYi7afj_vyTNbX1tQABb9ADiY9McOIcXyZzD2LM6ZcA1gkDqIkhoYnXsZOCWYWgy9USBnxu7kqK4aw7hVdYziF0gV9spxCCtweu9gGbcIcJFt5343dvHvDsIUSrOpMqgnIcOA_sUrA69KVkJPwehn6nvnilhwREoTbmmVDNyBphnUFI_cwLShS-jxtQSjqiYO_dFmwGBgDc7yBMdQmAzr5O52Zr9qxjyfjdy_acNLU8H31vIsDFfvahnj4n4Zf0lv-iEf8cqJcC4Fyp6Hz3_oJ4tu2FqQtqjG7QgVqQn5Vl5kfKyw.7a6qH9tAWvVexLyL.aiObMwNcnu1nlSD8-J4vCeAvrpCH-6R_QOkO0Ho0vmcDbDsorZbrSzrtVt18FBCfh6ul_R8AMCj4bLtdIU60kyZwxeArXx3qlZ0MmomnTLv3ulKkN2MQPKd0FyYSe3jeT6jL5TuBf2r8gZejkhW4JEufYpuAjz9xkf-QU1n7kRRykWKKsOl-QKW71xgKfVHceeeaFjMWk78HH5DM2M9nDIkBgJoFVCRrcn247Yjqy-vzB5zTSyKF9fCc5KlnGJ5n6TgsUuOMHoGX7KoUIVMKIAv76PjR7idjPFKti0XGu406iqplGOS7yngQI6-lm2hghx5Rbqu7wP8UnXKLouLlmRNmwCgcKnD7IHYHQU-cScktJedhdoYqHSyJAFqAPL6tmWzcu1X2IPxCtftTM6ute21Xp2Zs9V_abonooRZa7Dbjr5A_Kj8HFmCBy5QU54KOTn-VM6O_Af5sP-i2vOaTHSQ-ITOODnt6tK-B01UcK-jNmJVRL486NGF90G9EgkUOKAtHVu1oiLWTxC9JNgo9Kc01kloKrUkFK1ByHxdCYykUR2Nq8QsuKcpovYbRVXtakgY2WR6jJaRmu_LcDrKO2J1keglChvpoxmoTbBhSrAFOslvlHdalOqoyHxGYYXf-zfrIzhuiIJSUgQKlWYT4NPOLRIzBUhifbRZEPuC047CRGUt5XytgJLavYtgF9sMJecEKMFLBRQk9A1gwqvlp74ZgbFE2w4z34C8FGpcFjczE66JqWHb9SlRyqhpD-2_2YT7PHSoZiNpekNbeVD9QPYCr2YTIveCsQpEBqg-i1onylk0SAB7Sz8Fj8DUZAbhrtEMTX6JlUKujr1gWZmej4VhAlQ9YyEXLE82KGYiRj28OcJ2ROaHoI-wdZQdSeYR7JM_rVOFICaj9CZu3UrEBfVOO7O-sPs12uqiA73dHkKFwO3470L8ogC5uFN78AXwyA6kMdDFsxoKPulCqdqF5HrV2Hc14SJU8QrW16F9nkrqttQSDgJCVZkw3J7kyFpU7UCxtY2E1-ZD-lw6lGgc33rcMSDz4T35RVpMH0cd3JMqN-VgoPbWn7m9-oxSQ4cZoa4q02xheKBwBxPRR5ico5yJvYisi5T_xT3HDtzSD-bwIzqSneRHTmk87MRJzVkH1OW1yG2PAAmAGidgYrAj8WYm39vXJd8yFyRZLM8HHKI2P13B0Wo4s.adI0hTNlVZlzeI4HQByqaQ",
          "expires_in": 3600,
          "token_type": "Bearer"
        }
        """

        userinfo = r"""
        {
          "sub": "38faf1e8-6384-4598-81b5-84f43e91b3dc",
          "email_verified": "true",
          "name": "Nick Satterly",
          "preferred_username": "satterly",
          "given_name": "Nick",
          "family_name": "Satterly",
          "email": "nfsatterly+2@gmail.com",
          "picture": "https://avataaars.io/",
          "username": "satterly"
        }
        """

        m.get('https://cognito-idp.eu-west-1.amazonaws.com/eu-west-1_BMkhxuZsn/.well-known/openid-configuration', text=discovery_doc)
        m.post('https://alerta-webui.auth.eu-west-1.amazoncognito.com/oauth2/token', text=access_token)
        m.get('https://alerta-webui.auth.eu-west-1.amazoncognito.com/oauth2/userInfo', text=userinfo)

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
            'customer': 'Alphabet',
            'match': 'gmail.com'
        }
        response = self.client.post('/customer', data=json.dumps(payload),
                                    content_type='application/json', headers=self.headers)
        self.assertEqual(response.status_code, 201)

        response = self.client.post('/auth/openid', data=authorization_grant, content_type='application/json')
        self.assertEqual(response.status_code, 200, response.data)
        data = json.loads(response.data.decode('utf-8'))
        claims = jwt.decode(data['token'], verify=False)

        self.assertEqual(claims['name'], 'Nick Satterly', claims)
        self.assertEqual(claims['preferred_username'], 'satterly', claims)
        self.assertEqual(claims['provider'], 'cognito', claims)
        # self.assertEqual(claims['roles'], ['user'], claims)
        self.assertEqual(claims['scope'], 'read write', claims)
        self.assertEqual(claims['email'], 'nfsatterly+2@gmail.com', claims)
        self.assertEqual(claims.get('email_verified'), True, claims)
        self.assertEqual(claims['customers'], ['Alphabet'], claims)

    @requests_mock.mock()
    def test_azure_v1(self, m):

        test_config = {
            'TESTING': True,
            'AUTH_REQUIRED': True,
            'AUTH_PROVIDER': 'openid',
            'OIDC_ISSUER_URL': 'https://sts.windows.net/f24341ef-7a6f-4cff-abb7-99a11ab11127/',
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

        jwks_uri = """
        {
          "keys": [
            {
              "kty": "RSA",
              "use": "sig",
              "kid": "N-lC0n-9DALqwhuHYnHQ63GeCXc",
              "x5t": "N-lC0n-9DALqwhuHYnHQ63GeCXc",
              "n": "t3J1hnS4aRZaZGq5JUw1iKsHynCUV9lMBe2MDArXGeQlN-w8Xw9vU6InqmPVvJsUVyUkKE0jzn4dYLcwbTuttQ0hmN-lzNfGol04KKMIVdtTs1P0wo_-VyJ88EuWM3lvDxyTw1PLim14UJ1856zdp2_kZLOSy-B46K96ENJ8b2yCP_VHRTd3GgNTrx-xeU66WJdlon6SSkxI85KIAzOR4vxrl2XZZx_DkVcsAHa8KXQRkbMw82F2SHAbgJTv8qjSHR_WXjoGs3Wgds9UUqgNDXSK6qTjoG53zj8-faRkK0Px4wRD9rVXt-pPcGaul3TEkUVhpe8SyrLWETFexJesSQ",
              "e": "AQAB",
              "x5c": [
                "MIIDBTCCAe2gAwIBAgIQP8sUV4hf2ZxPfw5DB0O9CjANBgkqhkiG9w0BAQsFADAtMSswKQYDVQQDEyJhY2NvdW50cy5hY2Nlc3Njb250cm9sLndpbmRvd3MubmV0MB4XDTE5MDIwMTAwMDAwMFoXDTIxMDIwMTAwMDAwMFowLTErMCkGA1UEAxMiYWNjb3VudHMuYWNjZXNzY29udHJvbC53aW5kb3dzLm5ldDCCASIwDQYJKoZIhvcNAQEBBQADggEPADCCAQoCggEBALdydYZ0uGkWWmRquSVMNYirB8pwlFfZTAXtjAwK1xnkJTfsPF8Pb1OiJ6pj1bybFFclJChNI85+HWC3MG07rbUNIZjfpczXxqJdOCijCFXbU7NT9MKP/lcifPBLljN5bw8ck8NTy4pteFCdfOes3adv5GSzksvgeOivehDSfG9sgj/1R0U3dxoDU68fsXlOuliXZaJ+kkpMSPOSiAMzkeL8a5dl2Wcfw5FXLAB2vCl0EZGzMPNhdkhwG4CU7/Ko0h0f1l46BrN1oHbPVFKoDQ10iuqk46Bud84/Pn2kZCtD8eMEQ/a1V7fqT3Bmrpd0xJFFYaXvEsqy1hExXsSXrEkCAwEAAaMhMB8wHQYDVR0OBBYEFH5JQzlFI3FE9VxkkUbFT9XQDxifMA0GCSqGSIb3DQEBCwUAA4IBAQCb7re2PWF5ictaUCi4Ki2AWE6fGbmVRUdf0GkI06KdHWSiOgkPdB7Oka1Fv/j4GCs/ezHa1+oAx8uU96GECBBEMnCYPqkjmNKdLYkIUrcwEe9qz12MOCKJkCuYsDdLUqv+e4wHssbAnJn2+L13UmfAb6FM1VTaKIQtPs4yZsdhnk4M+Ee2EpcvgwOl2na+m58ovspieEyI6II/TolzwP9NWbvHw5VlF0IYttQprjmQU3tQ2E6j3HpZ31B0nrnFWglUB7lEC+0mkyJUGzovNECsr+BIEMhTlCp2/rbruCCbZBppYAlbWlTFwXA8TqfE4DNATYgm90ObQANcTnHJeRV1"
              ]
            },
            {
              "kty": "RSA",
              "use": "sig",
              "kid": "HBxl9mAe6gxavCkcoOU2THsDNa0",
              "x5t": "HBxl9mAe6gxavCkcoOU2THsDNa0",
              "n": "0afCaiPd_xl_ewZGfOkxKwYPfI4Efu0COfzajK_gnviWk7w3R-88Dmb0j24DSn1qVR3ptCnA1-QUfUMyhvl8pT5-t7oRkLNPzp0hVV-dAG3ZoMaSEMW0wapshA6LVGROpBncDmc66hx5-t3eOFA24fiKfQiv2TJth3Y9jhHnLe7GBOoomWYx_pJiEG3mhYFIt7shaEwNcEjo34vr1WWzRm8D8gogjrJWd1moyeGftWLzvfp9e79QwHYJv907vQbFrT7LYuy8g7-Rpxujgumw2mx7CewcCZXwPiZ-raM3Ap1FhINiGpd5mbbYrFDDFIWAjWPUY6KNvXtc24yUfZr4MQ",
              "e": "AQAB",
              "x5c": [
                "MIIDBTCCAe2gAwIBAgIQWcq84CdVhKVEcKbZdMOMGjANBgkqhkiG9w0BAQsFADAtMSswKQYDVQQDEyJhY2NvdW50cy5hY2Nlc3Njb250cm9sLndpbmRvd3MubmV0MB4XDTE5MDMxNDAwMDAwMFoXDTIxMDMxNDAwMDAwMFowLTErMCkGA1UEAxMiYWNjb3VudHMuYWNjZXNzY29udHJvbC53aW5kb3dzLm5ldDCCASIwDQYJKoZIhvcNAQEBBQADggEPADCCAQoCggEBANGnwmoj3f8Zf3sGRnzpMSsGD3yOBH7tAjn82oyv4J74lpO8N0fvPA5m9I9uA0p9alUd6bQpwNfkFH1DMob5fKU+fre6EZCzT86dIVVfnQBt2aDGkhDFtMGqbIQOi1RkTqQZ3A5nOuocefrd3jhQNuH4in0Ir9kybYd2PY4R5y3uxgTqKJlmMf6SYhBt5oWBSLe7IWhMDXBI6N+L69Vls0ZvA/IKII6yVndZqMnhn7Vi8736fXu/UMB2Cb/dO70Gxa0+y2LsvIO/kacbo4LpsNpsewnsHAmV8D4mfq2jNwKdRYSDYhqXeZm22KxQwxSFgI1j1GOijb17XNuMlH2a+DECAwEAAaMhMB8wHQYDVR0OBBYEFIkZ5wrSV8lohIsreOmig7h5wQDkMA0GCSqGSIb3DQEBCwUAA4IBAQAd8sKZLwZBocM4pMIRKarK60907jQCOi1m449WyToUcYPXmU7wrjy9fkYwJdC5sniItVBJ3RIQbF/hyjwnRoIaEcWYMAftBnH+c19WIuiWjR3EHnIdxmSopezl/9FaTNghbKjZtrKK+jL/RdkMY9uWxwUFLjTAtMm24QOt2+CGntBA9ohQUgiML/mlUpf4qEqa2/Lh+bjiHl3smg4TwuIl0i/TMN9Rg7UgQ6BnqfgiuMl6BtBiatNollwgGNI2zJEi47MjdeMf8+C3tXs//asqqlqJCyVLwN7AN47ynYmkl89MleOfKIojhrGRxryZG2nRjD9u/kZbPJ8e3JE9px67"
              ]
            },
            {
              "kty": "RSA",
              "use": "sig",
              "kid": "M6pX7RHoraLsprfJeRCjSxuURhc",
              "x5t": "M6pX7RHoraLsprfJeRCjSxuURhc",
              "n": "xHScZMPo8FifoDcrgncWQ7mGJtiKhrsho0-uFPXg-OdnRKYudTD7-Bq1MDjcqWRf3IfDVjFJixQS61M7wm9wALDj--lLuJJ9jDUAWTA3xWvQLbiBM-gqU0sj4mc2lWm6nPfqlyYeWtQcSC0sYkLlayNgX4noKDaXivhVOp7bwGXq77MRzeL4-9qrRYKjuzHfZL7kNBCsqO185P0NI2Jtmw-EsqYsrCaHsfNRGRrTvUHUq3hWa859kK_5uNd7TeY2ZEwKVD8ezCmSfR59ZzyxTtuPpkCSHS9OtUvS3mqTYit73qcvprjl3R8hpjXLb8oftfpWr3hFRdpxrwuoQEO4QQ",
              "e": "AQAB",
              "x5c": [
                "MIIC8TCCAdmgAwIBAgIQfEWlTVc1uINEc9RBi6qHMjANBgkqhkiG9w0BAQsFADAjMSEwHwYDVQQDExhsb2dpbi5taWNyb3NvZnRvbmxpbmUudXMwHhcNMTgxMDE0MDAwMDAwWhcNMjAxMDE0MDAwMDAwWjAjMSEwHwYDVQQDExhsb2dpbi5taWNyb3NvZnRvbmxpbmUudXMwggEiMA0GCSqGSIb3DQEBAQUAA4IBDwAwggEKAoIBAQDEdJxkw+jwWJ+gNyuCdxZDuYYm2IqGuyGjT64U9eD452dEpi51MPv4GrUwONypZF/ch8NWMUmLFBLrUzvCb3AAsOP76Uu4kn2MNQBZMDfFa9AtuIEz6CpTSyPiZzaVabqc9+qXJh5a1BxILSxiQuVrI2BfiegoNpeK+FU6ntvAZervsxHN4vj72qtFgqO7Md9kvuQ0EKyo7Xzk/Q0jYm2bD4SypiysJoex81EZGtO9QdSreFZrzn2Qr/m413tN5jZkTApUPx7MKZJ9Hn1nPLFO24+mQJIdL061S9LeapNiK3vepy+muOXdHyGmNctvyh+1+laveEVF2nGvC6hAQ7hBAgMBAAGjITAfMB0GA1UdDgQWBBQ5TKadw06O0cvXrQbXW0Nb3M3h/DANBgkqhkiG9w0BAQsFAAOCAQEAI48JaFtwOFcYS/3pfS5+7cINrafXAKTL+/+he4q+RMx4TCu/L1dl9zS5W1BeJNO2GUznfI+b5KndrxdlB6qJIDf6TRHh6EqfA18oJP5NOiKhU4pgkF2UMUw4kjxaZ5fQrSoD9omjfHAFNjradnHA7GOAoF4iotvXDWDBWx9K4XNZHWvD11Td66zTg5IaEQDIZ+f8WS6nn/98nAVMDtR9zW7Te5h9kGJGfe6WiHVaGRPpBvqC4iypGHjbRwANwofZvmp5wP08hY1CsnKY5tfP+E2k/iAQgKKa6QoxXToYvP7rsSkglak8N5g/+FJGnq4wP6cOzgZpjdPMwaVt5432GA=="
              ]
            }
          ]
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
        m.get('https://login.microsoftonline.com/common/discovery/keys', text=jwks_uri)
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

        response = self.client.post('/auth/openid', data=authorization_grant, content_type='application/json')
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
    def test_azure_v2(self, m):

        test_config = {
            'TESTING': True,
            'AUTH_REQUIRED': True,
            'AUTH_PROVIDER': 'azure',
            'AZURE_TENANT': 'common',
            'CUSTOMER_VIEWS': True,
        }

        authorization_grant = """
        {
          "code": "Mfd029b75-69e8-db17-b6c8-9062cafb6d06",
          "clientId": "00bb046a-36d9-4411-b93a-2f10fb35f0b5",
          "redirectUri": "http://localhost:8000",
          "state": "kr8y390mokk"
        }
        """

        discovery_doc = """
        {
          "authorization_endpoint": "https://login.microsoftonline.com/common/oauth2/v2.0/authorize",
          "token_endpoint": "https://login.microsoftonline.com/common/oauth2/v2.0/token",
          "token_endpoint_auth_methods_supported": [
            "client_secret_post",
            "private_key_jwt",
            "client_secret_basic"
          ],
          "jwks_uri": "https://login.microsoftonline.com/common/discovery/v2.0/keys",
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
          "end_session_endpoint": "https://login.microsoftonline.com/common/oauth2/v2.0/logout",
          "response_types_supported": [
            "code",
            "id_token",
            "code id_token",
            "id_token token"
          ],
          "scopes_supported": [
            "openid",
            "profile",
            "email",
            "offline_access"
          ],
          "issuer": "https://login.microsoftonline.com/{tenantid}/v2.0",
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
            "nonce",
            "preferred_username",
            "name",
            "tid",
            "ver",
            "at_hash",
            "c_hash",
            "email"
          ],
          "request_uri_parameter_supported": false,
          "userinfo_endpoint": "https://graph.microsoft.com/oidc/userinfo",
          "tenant_region_scope": null,
          "cloud_instance_name": "microsoftonline.com",
          "cloud_graph_host_name": "graph.windows.net",
          "msgraph_host": "graph.microsoft.com",
          "rbac_url": "https://pas.windows.net"
        }
        """

        jwks_uri = """
        {
          "keys": [
            {
              "kty": "RSA",
              "use": "sig",
              "kid": "HBxl9mAe6gxavCkcoOU2THsDNa0",
              "x5t": "HBxl9mAe6gxavCkcoOU2THsDNa0",
              "n": "0afCaiPd_xl_ewZGfOkxKwYPfI4Efu0COfzajK_gnviWk7w3R-88Dmb0j24DSn1qVR3ptCnA1-QUfUMyhvl8pT5-t7oRkLNPzp0hVV-dAG3ZoMaSEMW0wapshA6LVGROpBncDmc66hx5-t3eOFA24fiKfQiv2TJth3Y9jhHnLe7GBOoomWYx_pJiEG3mhYFIt7shaEwNcEjo34vr1WWzRm8D8gogjrJWd1moyeGftWLzvfp9e79QwHYJv907vQbFrT7LYuy8g7-Rpxujgumw2mx7CewcCZXwPiZ-raM3Ap1FhINiGpd5mbbYrFDDFIWAjWPUY6KNvXtc24yUfZr4MQ",
              "e": "AQAB",
              "x5c": [
                "MIIDBTCCAe2gAwIBAgIQWcq84CdVhKVEcKbZdMOMGjANBgkqhkiG9w0BAQsFADAtMSswKQYDVQQDEyJhY2NvdW50cy5hY2Nlc3Njb250cm9sLndpbmRvd3MubmV0MB4XDTE5MDMxNDAwMDAwMFoXDTIxMDMxNDAwMDAwMFowLTErMCkGA1UEAxMiYWNjb3VudHMuYWNjZXNzY29udHJvbC53aW5kb3dzLm5ldDCCASIwDQYJKoZIhvcNAQEBBQADggEPADCCAQoCggEBANGnwmoj3f8Zf3sGRnzpMSsGD3yOBH7tAjn82oyv4J74lpO8N0fvPA5m9I9uA0p9alUd6bQpwNfkFH1DMob5fKU+fre6EZCzT86dIVVfnQBt2aDGkhDFtMGqbIQOi1RkTqQZ3A5nOuocefrd3jhQNuH4in0Ir9kybYd2PY4R5y3uxgTqKJlmMf6SYhBt5oWBSLe7IWhMDXBI6N+L69Vls0ZvA/IKII6yVndZqMnhn7Vi8736fXu/UMB2Cb/dO70Gxa0+y2LsvIO/kacbo4LpsNpsewnsHAmV8D4mfq2jNwKdRYSDYhqXeZm22KxQwxSFgI1j1GOijb17XNuMlH2a+DECAwEAAaMhMB8wHQYDVR0OBBYEFIkZ5wrSV8lohIsreOmig7h5wQDkMA0GCSqGSIb3DQEBCwUAA4IBAQAd8sKZLwZBocM4pMIRKarK60907jQCOi1m449WyToUcYPXmU7wrjy9fkYwJdC5sniItVBJ3RIQbF/hyjwnRoIaEcWYMAftBnH+c19WIuiWjR3EHnIdxmSopezl/9FaTNghbKjZtrKK+jL/RdkMY9uWxwUFLjTAtMm24QOt2+CGntBA9ohQUgiML/mlUpf4qEqa2/Lh+bjiHl3smg4TwuIl0i/TMN9Rg7UgQ6BnqfgiuMl6BtBiatNollwgGNI2zJEi47MjdeMf8+C3tXs//asqqlqJCyVLwN7AN47ynYmkl89MleOfKIojhrGRxryZG2nRjD9u/kZbPJ8e3JE9px67"
              ],
              "issuer": "https://login.microsoftonline.com/{tenantid}/v2.0"
            },
            {
              "kty": "RSA",
              "use": "sig",
              "kid": "CtfQC8Le-8NsC7oC2zQkZpcrfOc",
              "x5t": "CtfQC8Le-8NsC7oC2zQkZpcrfOc",
              "n": "jmRWLbot3VWk7VHgzdUS0Oac_FY4ffz-fXyqlFFByYxYcI2X1Bm51kBfw7YDvDxTEew5yGECElKCUaNoe4eWc0OCrLNTisjLJ3oS0XhR0DDKm8iB15ciyCpJxHoqhN9_fBjpaOBucKKNzKWU0dBu8biX_vS3h0hr2Bc6M5G9YVPIWBrOGPfwzUrk3d3gikyNF8lTvxWFzUj9yuUhuwlD2UuAEtwwKT0LC7aZz-GjuRwUxnuNNSlPie3imrlGeII1tnILNJ7bC3dJvoTr9M9lptAThDkFFahpssSsCir4dBkViDTMsDw5CC9jtPWKTwH33P6fSrcwxl0gZJKpFNlGyw",
              "e": "AQAB",
              "x5c": [
                "MIIDBTCCAe2gAwIBAgIQIKS1IbCfX7xH/fHDCq11ljANBgkqhkiG9w0BAQsFADAtMSswKQYDVQQDEyJhY2NvdW50cy5hY2Nlc3Njb250cm9sLndpbmRvd3MubmV0MB4XDTE5MDQyNDAwMDAwMFoXDTIxMDQyNDAwMDAwMFowLTErMCkGA1UEAxMiYWNjb3VudHMuYWNjZXNzY29udHJvbC53aW5kb3dzLm5ldDCCASIwDQYJKoZIhvcNAQEBBQADggEPADCCAQoCggEBAI5kVi26Ld1VpO1R4M3VEtDmnPxWOH38/n18qpRRQcmMWHCNl9QZudZAX8O2A7w8UxHsOchhAhJSglGjaHuHlnNDgqyzU4rIyyd6EtF4UdAwypvIgdeXIsgqScR6KoTff3wY6WjgbnCijcyllNHQbvG4l/70t4dIa9gXOjORvWFTyFgazhj38M1K5N3d4IpMjRfJU78Vhc1I/crlIbsJQ9lLgBLcMCk9Cwu2mc/ho7kcFMZ7jTUpT4nt4pq5RniCNbZyCzSe2wt3Sb6E6/TPZabQE4Q5BRWoabLErAoq+HQZFYg0zLA8OQgvY7T1ik8B99z+n0q3MMZdIGSSqRTZRssCAwEAAaMhMB8wHQYDVR0OBBYEFFjkfvrQ97CY5HSyrhd98vkwj0SuMA0GCSqGSIb3DQEBCwUAA4IBAQAHVEnT+HZIxZc2jIdPqKcwCyCR4t44dsDTLYpvLB87iAJHckWgSblqgi/2hgW773PURIFSVWZbyT+/EgDPy0Bd+SHn0P9f4dOSrEWK6Ug3/GsOnUzooJ4SNcP91Shv5y5n5kCcZuglpnTBil85q+ZgB44CXQ5dPzDlZgO2IcCi2ZCYPGZUvKWSFnkQa0pjXu6wAArj1wWGbX7LuaPsSkOD1MK0A1/ve9V9kTeYr0fmmP+hD2TtOY+5fcv9oMbMQuL99Pwr+erjN3dDz7bQ0SDK+E8cerYgorHqjSIxbgH55yR9M1ca8sRriTl8Ah0rLAp/JIpFzn35oyrzCf6zzzWh"
              ],
              "issuer": "https://login.microsoftonline.com/{tenantid}/v2.0"
            },
            {
              "kty": "RSA",
              "use": "sig",
              "kid": "u4OfNFPHwEBosHjtrauObV84LnY",
              "x5t": "u4OfNFPHwEBosHjtrauObV84LnY",
              "n": "oRRQG-ib30x09eWtDpL0wWahA-hgjc0lWoQU4lwBFjXV2PfPImiAvwxOxNG34Mgnw3K9huBYLsrvOQAbMdBmE8lwz8DFKMWqHqoH3xSqDGhIYFobQDiVRkkecpberH5hqJauSD7PiwDBSQ_RCDIjb0SOmSTpZR97Ws4k1z9158VRf4BUbGjzVt4tUAz_y2cI5JsXQfcgAPB3voP8eunxGwZ_iM8evw3hUOw7-nuiPyts7HSkvV6GMwrXfOymY_w07mYxw_2LnKInfsWBtcRIDG-Nrsj237LgtBhK7TkzuVrguq__-bkDwwF3qTRXGAX9KrwY4huRxDRslMIg30Hqgw",
              "e": "AQAB",
              "x5c": [
                "MIIDBTCCAe2gAwIBAgIQdEMOjSqDVbdN3mzb2IumCzANBgkqhkiG9w0BAQsFADAtMSswKQYDVQQDEyJhY2NvdW50cy5hY2Nlc3Njb250cm9sLndpbmRvd3MubmV0MB4XDTE5MDYwNDAwMDAwMFoXDTIxMDYwNDAwMDAwMFowLTErMCkGA1UEAxMiYWNjb3VudHMuYWNjZXNzY29udHJvbC53aW5kb3dzLm5ldDCCASIwDQYJKoZIhvcNAQEBBQADggEPADCCAQoCggEBAKEUUBvom99MdPXlrQ6S9MFmoQPoYI3NJVqEFOJcARY11dj3zyJogL8MTsTRt+DIJ8NyvYbgWC7K7zkAGzHQZhPJcM/AxSjFqh6qB98UqgxoSGBaG0A4lUZJHnKW3qx+YaiWrkg+z4sAwUkP0QgyI29Ejpkk6WUfe1rOJNc/defFUX+AVGxo81beLVAM/8tnCOSbF0H3IADwd76D/Hrp8RsGf4jPHr8N4VDsO/p7oj8rbOx0pL1ehjMK13zspmP8NO5mMcP9i5yiJ37FgbXESAxvja7I9t+y4LQYSu05M7la4Lqv//m5A8MBd6k0VxgF/Sq8GOIbkcQ0bJTCIN9B6oMCAwEAAaMhMB8wHQYDVR0OBBYEFNRP0Lf6MDeL11RDH0uL7H+/JqtLMA0GCSqGSIb3DQEBCwUAA4IBAQCJKR1nxp9Ij/yisCmDG7bdN1yHj/2HdVvyLfCCyReRfkB3cnTZVaIOBy5occGkdmsYJ+q8uqczkoCMAz3gvvq1c0msKEiNpqWNeU2aRXqyL3QZJ/GBmUK1I0tINPVv8j7znm0DcvHHXFvhzS8E4s8ai8vQkcpyac/7Z4PN43HtjDnkZo9Zxm7JahHshrhA8sSPvsuC4dQAcHbOrLbHG+HIo3Tq2pNl7mfQ9fVJ2FxbqlzPYr/rK8H2GTA6N55SuP3KTNvyL3RnMa3hXmGTdG1dpMFzD/IE623h/BqY6j29PyQC/+MUD4UCZ6KW9oIzpi27pKQagH1i1jpBU/ceH6AW"
              ],
              "issuer": "https://login.microsoftonline.com/{tenantid}/v2.0"
            },
            {
              "kty": "RSA",
              "use": "sig",
              "kid": "M6pX7RHoraLsprfJeRCjSxuURhc",
              "x5t": "M6pX7RHoraLsprfJeRCjSxuURhc",
              "n": "xHScZMPo8FifoDcrgncWQ7mGJtiKhrsho0-uFPXg-OdnRKYudTD7-Bq1MDjcqWRf3IfDVjFJixQS61M7wm9wALDj--lLuJJ9jDUAWTA3xWvQLbiBM-gqU0sj4mc2lWm6nPfqlyYeWtQcSC0sYkLlayNgX4noKDaXivhVOp7bwGXq77MRzeL4-9qrRYKjuzHfZL7kNBCsqO185P0NI2Jtmw-EsqYsrCaHsfNRGRrTvUHUq3hWa859kK_5uNd7TeY2ZEwKVD8ezCmSfR59ZzyxTtuPpkCSHS9OtUvS3mqTYit73qcvprjl3R8hpjXLb8oftfpWr3hFRdpxrwuoQEO4QQ",
              "e": "AQAB",
              "x5c": [
                "MIIC8TCCAdmgAwIBAgIQfEWlTVc1uINEc9RBi6qHMjANBgkqhkiG9w0BAQsFADAjMSEwHwYDVQQDExhsb2dpbi5taWNyb3NvZnRvbmxpbmUudXMwHhcNMTgxMDE0MDAwMDAwWhcNMjAxMDE0MDAwMDAwWjAjMSEwHwYDVQQDExhsb2dpbi5taWNyb3NvZnRvbmxpbmUudXMwggEiMA0GCSqGSIb3DQEBAQUAA4IBDwAwggEKAoIBAQDEdJxkw+jwWJ+gNyuCdxZDuYYm2IqGuyGjT64U9eD452dEpi51MPv4GrUwONypZF/ch8NWMUmLFBLrUzvCb3AAsOP76Uu4kn2MNQBZMDfFa9AtuIEz6CpTSyPiZzaVabqc9+qXJh5a1BxILSxiQuVrI2BfiegoNpeK+FU6ntvAZervsxHN4vj72qtFgqO7Md9kvuQ0EKyo7Xzk/Q0jYm2bD4SypiysJoex81EZGtO9QdSreFZrzn2Qr/m413tN5jZkTApUPx7MKZJ9Hn1nPLFO24+mQJIdL061S9LeapNiK3vepy+muOXdHyGmNctvyh+1+laveEVF2nGvC6hAQ7hBAgMBAAGjITAfMB0GA1UdDgQWBBQ5TKadw06O0cvXrQbXW0Nb3M3h/DANBgkqhkiG9w0BAQsFAAOCAQEAI48JaFtwOFcYS/3pfS5+7cINrafXAKTL+/+he4q+RMx4TCu/L1dl9zS5W1BeJNO2GUznfI+b5KndrxdlB6qJIDf6TRHh6EqfA18oJP5NOiKhU4pgkF2UMUw4kjxaZ5fQrSoD9omjfHAFNjradnHA7GOAoF4iotvXDWDBWx9K4XNZHWvD11Td66zTg5IaEQDIZ+f8WS6nn/98nAVMDtR9zW7Te5h9kGJGfe6WiHVaGRPpBvqC4iypGHjbRwANwofZvmp5wP08hY1CsnKY5tfP+E2k/iAQgKKa6QoxXToYvP7rsSkglak8N5g/+FJGnq4wP6cOzgZpjdPMwaVt5432GA=="
              ],
              "issuer": "https://login.microsoftonline.com/{tenantid}/v2.0"
            },
            {
              "kty": "RSA",
              "use": "sig",
              "kid": "1LTMzakihiRla_8z2BEJVXeWMqo",
              "x5t": "1LTMzakihiRla_8z2BEJVXeWMqo",
              "n": "3sKcJSD4cHwTY5jYm5lNEzqk3wON1CaARO5EoWIQt5u-X-ZnW61CiRZpWpfhKwRYU153td5R8p-AJDWT-NcEJ0MHU3KiuIEPmbgJpS7qkyURuHRucDM2lO4L4XfIlvizQrlyJnJcd09uLErZEO9PcvKiDHoois2B4fGj7CsAe5UZgExJvACDlsQSku2JUyDmZUZP2_u_gCuqNJM5o0hW7FKRI3MFoYCsqSEmHnnumuJ2jF0RHDRWQpodhlAR6uKLoiWHqHO3aG7scxYMj5cMzkpe1Kq_Dm5yyHkMCSJ_JaRhwymFfV_SWkqd3n-WVZT0ADLEq0RNi9tqZ43noUnO_w",
              "e": "AQAB",
              "x5c": [
                "MIIDYDCCAkigAwIBAgIJAIB4jVVJ3BeuMA0GCSqGSIb3DQEBCwUAMCkxJzAlBgNVBAMTHkxpdmUgSUQgU1RTIFNpZ25pbmcgUHVibGljIEtleTAeFw0xNjA0MDUxNDQzMzVaFw0yMTA0MDQxNDQzMzVaMCkxJzAlBgNVBAMTHkxpdmUgSUQgU1RTIFNpZ25pbmcgUHVibGljIEtleTCCASIwDQYJKoZIhvcNAQEBBQADggEPADCCAQoCggEBAN7CnCUg+HB8E2OY2JuZTRM6pN8DjdQmgETuRKFiELebvl/mZ1utQokWaVqX4SsEWFNed7XeUfKfgCQ1k/jXBCdDB1NyoriBD5m4CaUu6pMlEbh0bnAzNpTuC+F3yJb4s0K5ciZyXHdPbixK2RDvT3Lyogx6KIrNgeHxo+wrAHuVGYBMSbwAg5bEEpLtiVMg5mVGT9v7v4ArqjSTOaNIVuxSkSNzBaGArKkhJh557pridoxdERw0VkKaHYZQEerii6Ilh6hzt2hu7HMWDI+XDM5KXtSqvw5ucsh5DAkifyWkYcMphX1f0lpKnd5/llWU9AAyxKtETYvbameN56FJzv8CAwEAAaOBijCBhzAdBgNVHQ4EFgQU9IdLLpbC2S8Wn1MCXsdtFac9SRYwWQYDVR0jBFIwUIAU9IdLLpbC2S8Wn1MCXsdtFac9SRahLaQrMCkxJzAlBgNVBAMTHkxpdmUgSUQgU1RTIFNpZ25pbmcgUHVibGljIEtleYIJAIB4jVVJ3BeuMAsGA1UdDwQEAwIBxjANBgkqhkiG9w0BAQsFAAOCAQEAXk0sQAib0PGqvwELTlflQEKS++vqpWYPW/2gCVCn5shbyP1J7z1nT8kE/ZDVdl3LvGgTMfdDHaRF5ie5NjkTHmVOKbbHaWpTwUFbYAFBJGnx+s/9XSdmNmW9GlUjdpd6lCZxsI6888r0ptBgKINRRrkwMlq3jD1U0kv4JlsIhafUIOqGi4+hIDXBlY0F/HJPfUU75N885/r4CCxKhmfh3PBM35XOch/NGC67fLjqLN+TIWLoxnvil9m3jRjqOA9u50JUeDGZABIYIMcAdLpI2lcfru4wXcYXuQul22nAR7yOyGKNOKULoOTE4t4AeGRqCogXSxZgaTgKSBhvhE+MGg=="
              ],
              "issuer": "https://login.microsoftonline.com/9188040d-6c67-4c5b-b112-36a304b66dad/v2.0"
            },
            {
              "kty": "RSA",
              "use": "sig",
              "kid": "xP_zn6I1YkXcUUmlBoPuXTGsaxk",
              "x5t": "xP_zn6I1YkXcUUmlBoPuXTGsaxk",
              "n": "2pWatafeb3mB0A73-Z-URwrubwDldWvivRu19GNC61MBOb3fZ4I4lyhUhNuS7aJRPJIFB6zl-HFx1nHpGg74BHe0z9skODHYZEACd2iKBIet55DdduIe1CXsZ9keyEmNaGv3XS4OW_7IDM0j5wR9OHugUifkH3PQIcFvTYanHmXojTmgjIOWoz7y0okpyN9-FbZRzdfx-ej-njaj5gR8r69muwO5wlTbIG20V40R6zYh-QODMUpayy7jDGFGw5vjFH9Ca0tLZcNQq__JKE_mp-0fODOAQobOrBUoASFkyCd95BVW7KJrndvW7ofRWaCTuZZOy5SnU4asbjMrgxFZFw",
              "e": "AQAB",
              "x5c": [
                "MIIDYDCCAkigAwIBAgIJAJzCyTLC+DjJMA0GCSqGSIb3DQEBCwUAMCkxJzAlBgNVBAMTHkxpdmUgSUQgU1RTIFNpZ25pbmcgUHVibGljIEtleTAeFw0xNjA3MTMyMDMyMTFaFw0yMTA3MTIyMDMyMTFaMCkxJzAlBgNVBAMTHkxpdmUgSUQgU1RTIFNpZ25pbmcgUHVibGljIEtleTCCASIwDQYJKoZIhvcNAQEBBQADggEPADCCAQoCggEBANqVmrWn3m95gdAO9/mflEcK7m8A5XVr4r0btfRjQutTATm932eCOJcoVITbku2iUTySBQes5fhxcdZx6RoO+AR3tM/bJDgx2GRAAndoigSHreeQ3XbiHtQl7GfZHshJjWhr910uDlv+yAzNI+cEfTh7oFIn5B9z0CHBb02Gpx5l6I05oIyDlqM+8tKJKcjffhW2Uc3X8fno/p42o+YEfK+vZrsDucJU2yBttFeNEes2IfkDgzFKWssu4wxhRsOb4xR/QmtLS2XDUKv/yShP5qftHzgzgEKGzqwVKAEhZMgnfeQVVuyia53b1u6H0Vmgk7mWTsuUp1OGrG4zK4MRWRcCAwEAAaOBijCBhzAdBgNVHQ4EFgQU11z579/IePwuc4WBdN4L0ljG4CUwWQYDVR0jBFIwUIAU11z579/IePwuc4WBdN4L0ljG4CWhLaQrMCkxJzAlBgNVBAMTHkxpdmUgSUQgU1RTIFNpZ25pbmcgUHVibGljIEtleYIJAJzCyTLC+DjJMAsGA1UdDwQEAwIBxjANBgkqhkiG9w0BAQsFAAOCAQEAiASLEpQseGNahE+9f9PQgmX3VgjJerNjXr1zXWXDJfFE31DxgsxddjcIgoBL9lwegOHHvwpzK1ecgH45xcJ0Z/40OgY8NITqXbQRfdgLrEGJCoyOQEbjb5PW5k2aOdn7LBxvDsH6Y8ax26v+EFMPh3G+xheh6bfoIRSK1b+44PfoDZoJ9NfJibOZ4Cq+wt/yOvpMYQDB/9CNo18wmA3RCLYjf2nAc7RO0PDYHSIq5QDWV+1awmXDKgIdRpYPpRtn9KFXQkpCeEc/lDTG+o6n7nC40wyjioyR6QmHGvNkMR4VfSoTKCTnFATyDpI1bqU2K7KNjUEsCYfwybFB8d6mjQ=="
              ],
              "issuer": "https://login.microsoftonline.com/9188040d-6c67-4c5b-b112-36a304b66dad/v2.0"
            }
          ]
        }
        """

        access_token = """
        {
          "token_type": "Bearer",
          "scope": "openid profile email",
          "expires_in": 3600,
          "ext_expires_in": 3600,
          "access_token": "EwBgA8l6BAAURSN/FHlDW5xN74t6GzbtsBBeBUYAAbQf93kT154CH65oNmvIxyehXU7dBZGBBt2jjbo6uCks4dZIVGkhZ+H3y7E3pYRR3aFNI1km+mzX3Emvs8HGC/0ESsJWOJof9tid6S6dlW0w912+6bmhF48W7T/CasERLLDQhaOtP6FrR5h3igGr64PlHd+JImiWltawHhNIbEmVmqyeDjjBI7J4/rOYEaJXneQu+POi8q+pQXGCx4ePB8OkeDzXuOAI7HcwWSNJlcFa5F8uL4vceQqpnCq9locH/xjNVPAKSqdD4DaLDTKcrPlE8hstQfq+NPuZIEksyzzl9QwUetrY7dEH39ihPogos1A5xHQ4wL1NuHMQW8y4fFcDZgAACPb3lig0AL5lMAIUV0FekjhyzKxZ1o2CD4WtriaYx0eF3j6i4jcd9HnhzZsJaOEQfyS22zKbzcNrkcVaB3z3nCkeBc2hN/1t/zGaH47iaWMkxo8YMp6EMUKX+vLBb7a4hohMRQA+B7LEvrrGSzS+TL5TrmI/m6ypfWI83Vwj7xvo3ESNK2BHJ/cTlJoecKgKsBaqkdgCjv3il38NJ30ekcQpNEwngpexEj63Ar5urZFlisZ3ZULbjaSx1J5nENxh1uFM3yNt1YLs4ttvUvgH+0n6/LC/9JjUcx910ix6GUELRSXOqp5DNGqKDcyYv8BaR5FcE5l99nXjOSSt8J0gWeJ4yA5to3CoGIglX5u9ZWHQdchjUsdMCIAmISqA0Y0O0VKWKg+T6N4qE1fg7nhLYjjwfp/I+t2kZ5fvnUlj+IC3iRB74CWVXtYGpMGHUMqQB2TtqBLImx9bSFlR/Q3MCeE2KEwVMbKv4zjx1XoBQguXijKFeY0PyEzlWgiGSSBNARJfD52v4FGQKJh5QCoo6SlC+Y6rIHf5R0sg1gAb4cquXuQ5TFix9MStK+WwW5j18pmYWGJn9ZY2+cDdT9OozcJ0oAF71GZv1ygGPl8WmwBFNZKzgtDXxYNbd7GxO1SG6Ag8RphoL4p/crS44RC/XTdCKR7SacNycV2ADSWdQ6S652bBsNdZ79f+tRGAAx2bO3rp0j6Vk94AiQNDWX7lQZmRMqQ52nLb0WwR9JpPUyMpgQexitHFpw7sW3YC",
          "id_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6IjFMVE16YWtpaGlSbGFfOHoyQkVKVlhlV01xbyJ9.eyJ2ZXIiOiIyLjAiLCJpc3MiOiJodHRwczovL2xvZ2luLm1pY3Jvc29mdG9ubGluZS5jb20vOTE4ODA0MGQtNmM2Ny00YzViLWIxMTItMzZhMzA0YjY2ZGFkL3YyLjAiLCJzdWIiOiJBQUFBQUFBQUFBQUFBQUFBQUFBQUFGUXRFVFZJeEpISjdIVTRpTkJVbGVNIiwiYXVkIjoiMDBiYjA0NmEtMzZkOS00NDExLWI5M2EtMmYxMGZiMzVmMGI1IiwiZXhwIjoxNTU5OTgwOTQ5LCJpYXQiOjE1NTk4OTQyNDksIm5iZiI6MTU1OTg5NDI0OSwibmFtZSI6Ik5pY2sgU2F0dGVybHkiLCJwcmVmZXJyZWRfdXNlcm5hbWUiOiJuaWNrLnNhdHRlcmx5QGhvdG1haWwuY29tIiwib2lkIjoiMDAwMDAwMDAtMDAwMC0wMDAwLTA2OTYtNmYzYjQ1NmVjY2QxIiwiZW1haWwiOiJuaWNrLnNhdHRlcmx5QGhvdG1haWwuY29tIiwidGlkIjoiOTE4ODA0MGQtNmM2Ny00YzViLWIxMTItMzZhMzA0YjY2ZGFkIiwiYWlvIjoiRGZ6UjgwRFpEVWMxaSp0cHVacXJoVUd4Snh5eHJzUW5PZVp5V040KnZNIWY1NDB0SklpdXdkcDR0azdyejZIdDNjIWtLWWk5WDFLRzhiT0UhVGhrN1BFVHRCZVNxOWt1U291YnJ2TWdUZHhSd1ZrRUhSSU8xcFFiMlNkcUJ2ZXZkU0Q2Y0M1YktUUTFBUTZqTGxuR1dZOCQifQ.G03Jyl5o-lKSAixQ8SBU71BT7FrsR3FXcbpcdQ7EHMeF9RG7MgVeqeUsr0iXHsFdxqyxpNttGj_7E2tGHqTdlqe66Nbj7IrwhjQymT32hte17fzwENKeu2k7yqNI5HsY0_iSzqKOgglDy5LXNqY9OA5L69UaMyp2txVUTLCh0WOWgtlAtLs0YSnow_HgJstgkKZZRTrNmTDaf86YOEAl9ATHOLPPWeacNjh2JkDgL4vVlNFkE_DJkpB6Iw-ARMi34dulp8BFdpD0Y6bpw9F8QqeFLcmLXvd15u7Xg0oEQSI22-FqRm5xA8JQ09pxrusvi6xc3yjqy8VUCd8RZDrsXg"
        }
        """

        userinfo = r"""
        {
          "sub": "AAAAAAAAAAAAAAAAAAAAAFQtETVIxJHJ7HU4iNBUleM"
        }
        """

        m.get('https://login.microsoftonline.com/common/v2.0/.well-known/openid-configuration', text=discovery_doc)
        m.get('https://login.microsoftonline.com/common/discovery/v2.0/keys', text=jwks_uri)
        m.post('https://login.microsoftonline.com/common/oauth2/v2.0/token', text=access_token)
        m.get('https://graph.microsoft.com/oidc/userinfo', text=userinfo)

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
            'customer': 'Hotmail',
            'match': 'hotmail.com'
        }
        response = self.client.post('/customer', data=json.dumps(payload),
                                    content_type='application/json', headers=self.headers)
        self.assertEqual(response.status_code, 201)

        response = self.client.post('/auth/openid', data=authorization_grant, content_type='application/json')
        self.assertEqual(response.status_code, 200, response.data)
        data = json.loads(response.data.decode('utf-8'))
        claims = jwt.decode(data['token'], verify=False)

        self.assertEqual(claims['name'], 'Nick Satterly', claims)
        self.assertEqual(claims['preferred_username'], 'nick.satterly@hotmail.com', claims)
        self.assertEqual(claims['provider'], 'azure', claims)
        # self.assertEqual(claims['roles'], ['user'], claims)
        self.assertEqual(claims['scope'], 'read write', claims)
        self.assertEqual(claims['email'], 'nick.satterly@hotmail.com', claims)
        self.assertEqual(claims.get('email_verified'), True, claims)
        self.assertEqual(claims['customers'], ['Hotmail'], claims)

    @requests_mock.mock()
    def test_github(self, m):

        test_config = {
            'TESTING': True,
            'AUTH_REQUIRED': True,
            'AUTH_PROVIDER': 'github',
            # 'GITHUB_URL': 'https://github.com',
            'OAUTH2_CLIENT_ID': '',
            'OAUTH2_CLIENT_SECRET': '',
            'ALLOWED_GITHUB_ORGS': ['alerta'],
            'CUSTOMER_VIEWS': True,
        }

        authorization_grant = """
        {
          "code": "342633785949fc9da249",
          "clientId": "4f846ebb21eec62ebdf0",
          "redirectUri": "http://local.alerta.io:8000"
        }
        """

        access_token = """
        {
          "access_token": "ef0b62b3d7f14ca003008dcaee2b313265fa6199",
          "token_type": "bearer",
          "scope": "read:org,user:email"
        }
        """

        profile = """
        {
          "login": "satterly",
          "id": 615058,
          "node_id": "MDQ6VXNlcgYxNTA1Nw==",
          "avatar_url": "https://avatars0.githubusercontent.com/u/615057?v=4",
          "gravatar_id": "",
          "url": "https://api.github.com/users/satterly",
          "html_url": "https://github.com/satterly",
          "followers_url": "https://api.github.com/users/satterly/followers",
          "following_url": "https://api.github.com/users/satterly/following{/other_user}",
          "gists_url": "https://api.github.com/users/satterly/gists{/gist_id}",
          "starred_url": "https://api.github.com/users/satterly/starred{/owner}{/repo}",
          "subscriptions_url": "https://api.github.com/users/satterly/subscriptions",
          "organizations_url": "https://api.github.com/users/satterly/orgs",
          "repos_url": "https://api.github.com/users/satterly/repos",
          "events_url": "https://api.github.com/users/satterly/events{/privacy}",
          "received_events_url": "https://api.github.com/users/satterly/received_events",
          "type": "User",
          "site_admin": false,
          "name": "Nick Satterly",
          "company": "@alerta",
          "blog": "",
          "location": "Stockholm",
          "email": null,
          "hireable": null,
          "bio": null,
          "public_repos": 29,
          "public_gists": 18,
          "followers": 76,
          "following": 4,
          "created_at": "2011-02-12T23:45:35Z",
          "updated_at": "2019-05-15T14:27:25Z"
        }
        """

        orgs = """
        [
          {
            "login": "ganglia",
            "id": 360097,
            "node_id": "MDEyOk9yZ2FuaXphdGlvbjM2MDA5Nw==",
            "url": "https://api.github.com/orgs/ganglia",
            "repos_url": "https://api.github.com/orgs/ganglia/repos",
            "events_url": "https://api.github.com/orgs/ganglia/events",
            "hooks_url": "https://api.github.com/orgs/ganglia/hooks",
            "issues_url": "https://api.github.com/orgs/ganglia/issues",
            "members_url": "https://api.github.com/orgs/ganglia/members{/member}",
            "public_members_url": "https://api.github.com/orgs/ganglia/public_members{/member}",
            "avatar_url": "https://avatars2.githubusercontent.com/u/360097?v=4",
            "description": null
          },
          {
            "login": "alerta",
            "id": 5067139,
            "node_id": "MDEyOk9yZ2FuaXphdGlvbjUwNjcxMzk=",
            "url": "https://api.github.com/orgs/alerta",
            "repos_url": "https://api.github.com/orgs/alerta/repos",
            "events_url": "https://api.github.com/orgs/alerta/events",
            "hooks_url": "https://api.github.com/orgs/alerta/hooks",
            "issues_url": "https://api.github.com/orgs/alerta/issues",
            "members_url": "https://api.github.com/orgs/alerta/members{/member}",
            "public_members_url": "https://api.github.com/orgs/alerta/public_members{/member}",
            "avatar_url": "https://avatars1.githubusercontent.com/u/5067139?v=4",
            "description": "@alertaio"
          }
        ]
        """

        m.post('https://github.com/login/oauth/access_token', text=access_token)
        m.get('https://api.github.com/user', text=profile)
        m.get('https://api.github.com/user/orgs', text=orgs)

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
            'match': 'alerta'
        }
        response = self.client.post('/customer', data=json.dumps(payload),
                                    content_type='application/json', headers=self.headers)
        self.assertEqual(response.status_code, 201)

        response = self.client.post('/auth/github', data=authorization_grant, content_type='application/json')
        self.assertEqual(response.status_code, 200, response.data)
        data = json.loads(response.data.decode('utf-8'))
        claims = jwt.decode(data['token'], verify=False)

        self.assertEqual(claims['name'], 'Nick Satterly', claims)
        self.assertEqual(claims['preferred_username'], '@satterly', claims)
        self.assertEqual(claims['provider'], 'github', claims)
        self.assertEqual(claims['orgs'], ['ganglia', 'alerta'], claims)
        self.assertEqual(claims['scope'], 'read write', claims)
        self.assertEqual(claims.get('email_verified'), False, claims)
        self.assertEqual(claims['customers'], ['Alerta IO'], claims)

    @requests_mock.mock()
    def test_gitlab(self, m):

        test_config = {
            'TESTING': True,
            'AUTH_REQUIRED': True,
            'AUTH_PROVIDER': 'gitlab',
            # 'OIDC_ISSUER_URL': 'https://gitlab.com',
            # 'OIDC_CUSTOM_CLAIM': 'groups',
            'ALLOWED_GITLAB_GROUPS': ['alerta-project'],
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

        jwks_uri = """
        {
          "keys": [
            {
              "kty": "RSA",
              "kid": "kewiQq9jiC84CvSsJYOB-N6A8WFLSV20Mb-y7IlWDSQ",
              "e": "AQAB",
              "n": "5RyvCSgBoOGNE03CMcJ9Bzo1JDvsU8XgddvRuJtdJAIq5zJ8fiUEGCnMfAZI4of36YXBuBalIycqkgxrRkSOENRUCWN45bf8xsQCcQ8zZxozu0St4w5S-aC7N7UTTarPZTp4BZH8ttUm-VnK4aEdMx9L3Izo0hxaJ135undTuA6gQpK-0nVsm6tRVq4akDe3OhC-7b2h6z7GWJX1SD4sAD3iaq4LZa8y1mvBBz6AIM9co8R-vU1_CduxKQc3KxCnqKALbEKXm0mTGsXha9aNv3pLNRNs_J-cCjBpb1EXAe_7qOURTiIHdv8_sdjcFTJ0OTeLWywuSf7mD0Wpx2LKcD6ImENbyq5IBuR1e2ghnh5Y9H33cuQ0FRni8ikq5W3xP3HSMfwlayhIAJN_WnmbhENRU-m2_hDPiD9JYF2CrQneLkE3kcazSdtarPbg9ZDiydHbKWCV-X7HxxIKEr9N7P1V5HKatF4ZUrG60e3eBnRyccPwmT66i9NYyrcy1_ZNN8D1DY8xh9kflUDy4dSYu4R7AEWxNJWQQov525v0MjD5FNAS03rpk4SuW3Mt7IP73m-_BpmIhW3LZsnmfd8xHRjf0M9veyJD0--ETGmh8t3_CXh3I3R9IbcSEntUl_2lCvc_6B-m8W-t2nZr4wvOq9-iaTQXAn1Au6EaOYWvDRE",
              "use": "sig",
              "alg": "RS256"
            }
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
        m.get('https://gitlab.com/oauth/discovery/keys', text=jwks_uri)
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
        self.assertEqual(claims['provider'], 'gitlab', claims)
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

        jwks_uri = """
        {
          "keys": [
            {
              "alg": "RS256",
              "n": "yyeEmeK35F8P54ozfpsF79n59ZsOrcZdxQWsxrzm0qjdA5r_b-be-cQnWAw_2AoGdeWHX-Cz7uPFDMdEwzLGlpv3SELi34h8PkzjyO7xlbhsNs-ICnqUyUTA7CovKtpJ47PjiQnXcaRNCFUQbli8VlEqbVLuqFjC98igICpNYR-iiVIm0VCFtkq0p8vf1yQ493Pnx2Bm8fUx6SkeJ7wKPWQq_K4e6ZH40JWLk6c1U9W5qPKeckevdNLrdZY5lsTZ5zrRvuRBoIeZfp9bKSZGMtEja4xSCDKLrkcpb4qf6Ywx9rsZ4b8eHSLpVvUzNsj3GS7qK5flHzoccovhPVBbbQ",
              "use": "sig",
              "kid": "0905d6f9cd9b0f1f852e8b207e8f673abca4bf75",
              "e": "AQAB",
              "kty": "RSA"
            },
            {
              "kid": "a4313e7fd1e9e2a4ded3b292d2a7f4e519574308",
              "e": "AQAB",
              "kty": "RSA",
              "alg": "RS256",
              "n": "lO3_QoRd_D8UHAjFcdg0_8GOiLyWo4Viiy8cDLNGf8T1eQlqqhPYZmvGOPhyILWZ9FInOXT9AzH5KPfeOnMEzy4TqfGLtdcAlufqALe_qusmq7SSNIVfSw5iPZjzXk3BXjzoFNZLfqsoqheGzek-sJV1Ti5JQQ2hRPSZQhba9xVn6G8Uxr5ugVhHQ25P6HL4acjhuvpSPEFn7tivEIhWZEL35CeqHelf-48WA4PLzRVvfFMS-hW6erjX7uxT9mj8uT7zGl41_zBd9lMn2CQeP3aLDeQFoFaLaX2NZctRASErz6H9MIXQngM1piKnc84hmify-ZAsPpBcxw7heFpYRw",
              "use": "sig"
            }
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
        m.get('https://www.googleapis.com/oauth2/v3/certs', text=jwks_uri)
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
        self.assertEqual(claims['provider'], 'google', claims)
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

        jwks_uri = """
        {
          "keys": [
            {
              "kid": "ve675JT-ilurPYgTl3-CHmZap-Vt-ucMbEv3nvKc6Ic",
              "kty": "RSA",
              "alg": "RS256",
              "use": "sig",
              "n": "mKJV_q1RCxz0m8tB4gOmN640erE1a9jGsPY0n50l6_a_GCS5rgy6vawl9tKc5eBNh8Wc-pdzPjLFd-PqKUmKMOBGpm9riTrTVQoqvU6115qvi5XSAYX2mbaUFaz7GjrI1KU7W7SkWMRR7tAGNkYIOW2hSblhzJYst7w3uSs1cuTxzV11xkMx0Yh9uGNhkfIUR7FitlpAF5taeJuFV61YJo2sXb38TNun4dSeD9FD1U9odK4jguh37huBv1m8UE5sW2Ud90UuOz4gXUppxHpBIdssaGdTOOON40dT18naTRlQK1wzrO9czQKK47Zi9d1sNz4ciOwJFX1sEx2Nfj403w",
              "e": "AQAB"
            }
          ]
        }
        """

        access_token = """
        {
          "access_token": "eyJhbGciOiJSUzI1NiIsInR5cCIgOiAiSldUIiwia2lkIiA6ICJ2ZTY3NUpULWlsdXJQWWdUbDMtQ0htWmFwLVZ0LXVjTWJFdjNudktjNkljIn0.eyJqdGkiOiJhMjQzMWM2OC1hMzkzLTQyYWMtYjRjMS1iNmE3NDcwYmJhOWIiLCJleHAiOjE1NTQxNTc4NTMsIm5iZiI6MCwiaWF0IjoxNTU0MTU3NzkzLCJpc3MiOiJodHRwOi8va2V5Y2xvYWsubG9jYWwuYWxlcnRhLmlvOjkwOTAvYXV0aC9yZWFsbXMvbWFzdGVyIiwiYXVkIjpbIm1hc3Rlci1yZWFsbSIsImFjY291bnQiXSwic3ViIjoiNGVlYWExMjItMDhkOC00N2JjLWI2ZDAtMDEwNDgxYzA1NWM1IiwidHlwIjoiQmVhcmVyIiwiYXpwIjoiYWxlcnRhLXVpIiwiYXV0aF90aW1lIjoxNTU0MTU3Nzg0LCJzZXNzaW9uX3N0YXRlIjoiNjZhMTQyMmEtY2IyOC00NzJjLWFhNzQtYjhiMTNiNTA4ZGRjIiwiYWNyIjoiMCIsImFsbG93ZWQtb3JpZ2lucyI6WyJodHRwOi8vbG9jYWwuYWxlcnRhLmlvOjgwMDAiXSwicmVhbG1fYWNjZXNzIjp7InJvbGVzIjpbImNyZWF0ZS1yZWFsbSIsImRldm9wcyIsImFkbWluIl19LCJyZXNvdXJjZV9hY2Nlc3MiOnsibWFzdGVyLXJlYWxtIjp7InJvbGVzIjpbInZpZXctcmVhbG0iLCJ2aWV3LWlkZW50aXR5LXByb3ZpZGVycyIsIm1hbmFnZS1pZGVudGl0eS1wcm92aWRlcnMiLCJpbXBlcnNvbmF0aW9uIiwiY3JlYXRlLWNsaWVudCIsIm1hbmFnZS11c2VycyIsInF1ZXJ5LXJlYWxtcyIsInZpZXctYXV0aG9yaXphdGlvbiIsInF1ZXJ5LWNsaWVudHMiLCJxdWVyeS11c2VycyIsIm1hbmFnZS1ldmVudHMiLCJtYW5hZ2UtcmVhbG0iLCJ2aWV3LWV2ZW50cyIsInZpZXctdXNlcnMiLCJ2aWV3LWNsaWVudHMiLCJtYW5hZ2UtYXV0aG9yaXphdGlvbiIsIm1hbmFnZS1jbGllbnRzIiwicXVlcnktZ3JvdXBzIl19LCJhY2NvdW50Ijp7InJvbGVzIjpbIm1hbmFnZS1hY2NvdW50IiwibWFuYWdlLWFjY291bnQtbGlua3MiLCJ2aWV3LXByb2ZpbGUiXX19LCJzY29wZSI6Im9wZW5pZCBlbWFpbCBwcm9maWxlIiwiZW1haWxfdmVyaWZpZWQiOnRydWUsInJvbGVzIjpbImNyZWF0ZS1yZWFsbSIsImRldm9wcyIsImFkbWluIl0sIm5hbWUiOiJOaWNob2xhcyBTYXR0ZXJseSIsInByZWZlcnJlZF91c2VybmFtZSI6Im5zYXR0ZXJsIiwiZ2l2ZW5fbmFtZSI6Ik5pY2hvbGFzIiwiZmFtaWx5X25hbWUiOiJTYXR0ZXJseSIsImVtYWlsIjoibmlja0BhbGVydGEuZGV2In0.WS-XrAlRNP7JvNggjwmRT_Eurjui_FzUK4asyJF9cr4X3xXPK9mGj8euwevyKr0VodahKX0vR59fBtmcGzPaGJfMucxWNwxwNVLpbiZzQuopYJ66xNxbNXpuvmsp9zSk-ct9cOD4Oo5dVnB0Lz55ytTLyyhzaRWO-XJeTpDrSey3Qg2mihmPRkKYOz2oacQeQV2IFWyZC8MOs4BdGw_386VlNDY-RjGffr4nF0HyoSidTh6cpZCQ8WvdsRdYTeArlxlzLxv6NAj9azGop7HP-zdIo_S56Tl_a-idHuzVZuGqHfgDKGWzIWUqAlhz1zABhnOt0IrtT_4f12XQcMRfqA",
          "expires_in": 60,
          "refresh_expires_in": 1800,
          "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCIgOiAiSldUIiwia2lkIiA6ICI4OTdhNmIyZS04YmFhLTQxN2UtOWQ1OS03YWIzZDAzZDJkYmQifQ.eyJqdGkiOiJkMTMyNTc1MS03MGYyLTQ2NzgtODA3NS1jMTU2ZDI0NzJmNDAiLCJleHAiOjE1NTQxNTk1OTMsIm5iZiI6MCwiaWF0IjoxNTU0MTU3NzkzLCJpc3MiOiJodHRwOi8va2V5Y2xvYWsubG9jYWwuYWxlcnRhLmlvOjkwOTAvYXV0aC9yZWFsbXMvbWFzdGVyIiwiYXVkIjoiaHR0cDovL2tleWNsb2FrLmxvY2FsLmFsZXJ0YS5pbzo5MDkwL2F1dGgvcmVhbG1zL21hc3RlciIsInN1YiI6IjRlZWFhMTIyLTA4ZDgtNDdiYy1iNmQwLTAxMDQ4MWMwNTVjNSIsInR5cCI6IlJlZnJlc2giLCJhenAiOiJhbGVydGEtdWkiLCJhdXRoX3RpbWUiOjAsInNlc3Npb25fc3RhdGUiOiI2NmExNDIyYS1jYjI4LTQ3MmMtYWE3NC1iOGIxM2I1MDhkZGMiLCJyZWFsbV9hY2Nlc3MiOnsicm9sZXMiOlsiY3JlYXRlLXJlYWxtIiwiZGV2b3BzIiwiYWRtaW4iXX0sInJlc291cmNlX2FjY2VzcyI6eyJtYXN0ZXItcmVhbG0iOnsicm9sZXMiOlsidmlldy1yZWFsbSIsInZpZXctaWRlbnRpdHktcHJvdmlkZXJzIiwibWFuYWdlLWlkZW50aXR5LXByb3ZpZGVycyIsImltcGVyc29uYXRpb24iLCJjcmVhdGUtY2xpZW50IiwibWFuYWdlLXVzZXJzIiwicXVlcnktcmVhbG1zIiwidmlldy1hdXRob3JpemF0aW9uIiwicXVlcnktY2xpZW50cyIsInF1ZXJ5LXVzZXJzIiwibWFuYWdlLWV2ZW50cyIsIm1hbmFnZS1yZWFsbSIsInZpZXctZXZlbnRzIiwidmlldy11c2VycyIsInZpZXctY2xpZW50cyIsIm1hbmFnZS1hdXRob3JpemF0aW9uIiwibWFuYWdlLWNsaWVudHMiLCJxdWVyeS1ncm91cHMiXX0sImFjY291bnQiOnsicm9sZXMiOlsibWFuYWdlLWFjY291bnQiLCJtYW5hZ2UtYWNjb3VudC1saW5rcyIsInZpZXctcHJvZmlsZSJdfX0sInNjb3BlIjoib3BlbmlkIGVtYWlsIHByb2ZpbGUifQ.MOqIkOHBARJ1D8cQIqOSJ6REHTZbcQiA-HlRHBQW3oQ",
          "token_type": "bearer",
          "id_token": "eyJhbGciOiJSUzI1NiIsInR5cCIgOiAiSldUIiwia2lkIiA6ICJ2ZTY3NUpULWlsdXJQWWdUbDMtQ0htWmFwLVZ0LXVjTWJFdjNudktjNkljIn0.eyJqdGkiOiI0MjIzMGI4My1hOGM4LTQ0ODEtYWE5My1mMjMwNzk5YWVjMmQiLCJleHAiOjE1NTQxNTc4NTMsIm5iZiI6MCwiaWF0IjoxNTU0MTU3NzkzLCJpc3MiOiJodHRwOi8va2V5Y2xvYWsubG9jYWwuYWxlcnRhLmlvOjkwOTAvYXV0aC9yZWFsbXMvbWFzdGVyIiwiYXVkIjoiYWxlcnRhLXVpIiwic3ViIjoiNGVlYWExMjItMDhkOC00N2JjLWI2ZDAtMDEwNDgxYzA1NWM1IiwidHlwIjoiSUQiLCJhenAiOiJhbGVydGEtdWkiLCJhdXRoX3RpbWUiOjE1NTQxNTc3ODQsInNlc3Npb25fc3RhdGUiOiI2NmExNDIyYS1jYjI4LTQ3MmMtYWE3NC1iOGIxM2I1MDhkZGMiLCJhY3IiOiIwIiwiZW1haWxfdmVyaWZpZWQiOnRydWUsInJvbGVzIjpbImNyZWF0ZS1yZWFsbSIsImRldm9wcyIsImFkbWluIl0sIm5hbWUiOiJOaWNob2xhcyBTYXR0ZXJseSIsInByZWZlcnJlZF91c2VybmFtZSI6Im5zYXR0ZXJsIiwiZ2l2ZW5fbmFtZSI6Ik5pY2hvbGFzIiwiZmFtaWx5X25hbWUiOiJTYXR0ZXJseSIsImVtYWlsIjoibmlja0BhbGVydGEuZGV2In0.H78MN_uRbniCEE6zOKFH9v2l5O_-JaNiP3W7CYiUR2sbA5H0e_vnFRy93A_RhKGiXBdEq-Lop6aE-BPgGgZpBR-G0wi9y0-pPRr3K3UHIL7z8ozUerXJ3g5DzQu3zFyHF9v62ew12YtBzRwebl2mW0_32_zEMlQPs3AzN2LxsjQT5QBV7nzygO_5xfgfA55guiBvJ8D8be13__wO-iQsFnnnFGK6JEbNDTM-M0JXqt4FtRfSEOdCjKRdLSUIfReTo1k2FrD2gtoVOcTOzUN6FCUefa8E52Xy3sgrWSHGUoE9brfoOvzoponiHUVCmbnPhHRTqBOSMZyfDw28v6z63Q",
          "not-before-policy": 0,
          "session_state": "66a1422a-cb28-472c-aa74-b8b13b508ddc",
          "scope": "openid email profile"
        }
        """

        userinfo = """
        {
          "sub": "4eeaa122-08d8-47bc-b6d0-010481c055c5",
          "email_verified": true,
          "roles": [
            "create-realm",
            "devops",
            "alerta-project",
            "admin"
          ],
          "name": "Nicholas Satterly",
          "preferred_username": "nsatterl",
          "given_name": "Nicholas",
          "family_name": "Satterly",
          "email": "nick@alerta.dev"
        }
        """

        m.get('http://keycloak.local.alerta.io:9090/auth/realms/master/.well-known/openid-configuration', text=discovery_doc)
        m.get('http://keycloak.local.alerta.io:9090/auth/realms/master/protocol/openid-connect/certs', text=jwks_uri)
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
        self.assertEqual(claims['provider'], 'keycloak', claims)
        self.assertEqual(claims['roles'], ['create-realm', 'devops', 'alerta-project', 'admin'], claims)
        self.assertEqual(claims['scope'], 'admin read write', claims)
        self.assertEqual(claims['email'], 'nick@alerta.dev', claims)
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

        jwks_uri = """
        {
          "keys": [
            {
              "alg": "RS256",
              "kty": "RSA",
              "use": "sig",
              "x5c": [
                "MIIDDTCCAfWgAwIBAgIJQGmNBJxybcLTMA0GCSqGSIb3DQEBCwUAMCQxIjAgBgNVBAMTGWRldi02NjE5MWpkci5ldS5hdXRoMC5jb20wHhcNMTkwMzMwMDYzODM1WhcNMzIxMjA2MDYzODM1WjAkMSIwIAYDVQQDExlkZXYtNjYxOTFqZHIuZXUuYXV0aDAuY29tMIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAp2ZcAYOMRWIVqO8Ih3qiLXoL0antgVSsyJvlHmvWJN0Oyn9xkmXX3qbJRIYN13Dj2EW0A1mGZYZBHVPDCoAe7dWLFA8UyU8ofQofQ76AXn4zEhI5ETnj5ZkqSMTfZuA8sbKtLtO7alVTPok24a4sfm4ECG8k5Rx59UOX1JIVOsvQLnWhnxYmoe+fB52XqnhY6tXF3Y+v+QC2jCWo1yZpG/ZpegMu4WcmT3zqxWqT4pbamCUH49IfJbVhRISF9JQdytz/ylfzaow4+QTgpMQHx27L99AFhgL9moxglyMmI8OO8yyoabWdkE9GPtKYiaNwxlfagze6sA0XMuWAMAH3NwIDAQABo0IwQDAPBgNVHRMBAf8EBTADAQH/MB0GA1UdDgQWBBQ4VB9WhbNhas/0DpOGSvQqui8j6zAOBgNVHQ8BAf8EBAMCAoQwDQYJKoZIhvcNAQELBQADggEBACix5lFpyx46oTNwwsJKVo3+gZAlLY6/sHldbUpV8MQIC2HXwCjNQAldUWQkMVWSieU3eE4fEUrfRxIwKOXZ/hV5oA9PSnnVAJyRzXuzYijtKPV15D3InnAr3TsgLGw3kWjPUDgXecqxsIo8hnuYaVIcNPJT12mBlZYtBckf4DAMl76/xwy0Y5vdLZX8/MICl8MoXn4a4DXfhyD/SG0mLYUOepdxAKjZNV5EfTQgUVkiZlYRkiKEU0jRy1moRbXDwJ4r7t1sVASO14D8r8JfkPUhqFovijVmk5+dLbLEQlr6mbEe6221riOD2a/Eq8CTukkYzzXxSDfohVniqHO3mLA="
              ],
              "n": "p2ZcAYOMRWIVqO8Ih3qiLXoL0antgVSsyJvlHmvWJN0Oyn9xkmXX3qbJRIYN13Dj2EW0A1mGZYZBHVPDCoAe7dWLFA8UyU8ofQofQ76AXn4zEhI5ETnj5ZkqSMTfZuA8sbKtLtO7alVTPok24a4sfm4ECG8k5Rx59UOX1JIVOsvQLnWhnxYmoe-fB52XqnhY6tXF3Y-v-QC2jCWo1yZpG_ZpegMu4WcmT3zqxWqT4pbamCUH49IfJbVhRISF9JQdytz_ylfzaow4-QTgpMQHx27L99AFhgL9moxglyMmI8OO8yyoabWdkE9GPtKYiaNwxlfagze6sA0XMuWAMAH3Nw",
              "e": "AQAB",
              "kid": "MjdFNjIxNjhFN0Y4N0E4RkFCODUyQzAyMUNBQzkxQjNFMDI2MkUyMA",
              "x5t": "MjdFNjIxNjhFN0Y4N0E4RkFCODUyQzAyMUNBQzkxQjNFMDI2MkUyMA"
            }
          ]
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
        m.get('https://dev-66191jdr.eu.auth0.com/.well-known/jwks.json', text=jwks_uri)
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

        jwks_uri = """
        {
          "keys": [
            {
              "kty": "RSA",
              "alg": "RS256",
              "kid": "KFvbIZMjjk6Gr47SrEKO8TgeeSswjlQ33X7JCgcnePk",
              "use": "sig",
              "e": "AQAB",
              "n": "meBXoV6oDzN2Rt0Ew7LxlRwmJHatDQ7LOeeW-TABViwTZK_MouvI9JCLuitMjNy-8ex9fl_JXuGsSej7oLgdlkPeinSzmsiMCxpiG2-v4JCdj5gYsKzAkP6j9QV4YHtBT-dds076aMlS1rVDUPiaIXP-PBAvdm4csUNO3aqNmCv1W-xyMTQ7GM_m3Ur-6QLT5gs78-Zhc_dnEljuqrG2zqVPfN7p03l8Ycic_mpE9oT2fevaOQY34ubSjbapYp-8Wz6yEVqAhCWC9LNRtkymGAObBLfaPvr3HKUmtXRYVIahodyDioKLqLAFWklqlqsVm1C-ID8dkdhz3k0Sc_UAsw"
            }
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
        m.get('https://dev-490527.okta.com/oauth2/default/v1/keys', text=jwks_uri)
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
