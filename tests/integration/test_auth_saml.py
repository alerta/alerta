import unittest

from lxml import etree

from alerta.app import create_app

NAMESPACE_MAP = {
    'samlp': 'urn:oasis:names:tc:SAML:2.0:protocol',
    'saml': 'urn:oasis:names:tc:SAML:2.0:assertion',
    'md': 'urn:oasis:names:tc:SAML:2.0:metadata',
    'ds': 'http://www.w3.org/2000/09/xmldsig#',
}


def xpath(el, path):
    return el.xpath(path, namespaces=NAMESPACE_MAP)[0]


class SAMLIntegrationTestCase(unittest.TestCase):

    def setUp(self):

        test_config = {
            'TESTING': True,
            'DEBUG': True,
            'AUTH_PROVIDER': 'saml2',
            'BASE_URL': 'http://localhost:8080',
            # 'SAML2_METADATA_URL': 'https://dev-490527.okta.com/app/exk65v4trcrBK3iH6357/sso/saml/metadata'
            'SAML2_METADATA_URL': 'http://localhost:9080/simplesaml/saml2/idp/metadata.php'
        }
        self.app = create_app(test_config)
        self.client = self.app.test_client()

    def test_login_redirect(self):

        response = self.client.get('/auth/saml')
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.headers['Location'].startswith('http://localhost:9080/simplesaml/saml2/idp/SSOService.php?SAMLRequest='))

    def test_saml2_metadata(self):

        response = self.client.get('/auth/saml/metadata.xml')
        self.assertEqual(response.status_code, 200)
        response_xml = etree.fromstring(response.data.decode('utf-8'))

        self.assertEqual(xpath(response_xml, '/md:EntityDescriptor').attrib['entityID'], 'http://localhost:8080')
        sp = xpath(response_xml, '/md:EntityDescriptor/md:SPSSODescriptor')
        self.assertEqual(xpath(sp, './md:AssertionConsumerService').attrib['Location'], 'http://localhost:8080/auth/saml')
