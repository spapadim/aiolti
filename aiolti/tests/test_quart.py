# -*- coding: utf-8 -*-
"""
Test aiolti/test_quart.py module
"""
from __future__ import absolute_import
import unittest

#import httpretty
from mocket.plugins import httpretty
import mock
import oauthlib.oauth1

from six.moves.urllib.parse import urlencode

from quart.testing import QuartClient

from aiolti.common import LTIException
from aiolti.quart import LTI
from aiolti.tests.test_quart_app import app_exception, app


class TestQuart(unittest.IsolatedAsyncioTestCase):
    """
    Consumers.
    """
    app_client: QuartClient

    # pylint: disable=too-many-public-methods
    consumers = {
        "__consumer_key__": {"secret": "__lti_secret__"}
    }

    # Valid XML response from LTI 1.0 consumer
    expected_response = """<?xml version="1.0" encoding="UTF-8"?>
<imsx_POXEnvelopeResponse xmlns = "http://www.imsglobal.org/services/ltiv1p1\
/xsd/imsoms_v1p0">
    <imsx_POXHeader>
        <imsx_POXResponseHeaderInfo>
            <imsx_version>V1.0</imsx_version>
            <imsx_messageIdentifier>edX_fix</imsx_messageIdentifier>
            <imsx_statusInfo>
                <imsx_codeMajor>success</imsx_codeMajor>
                <imsx_severity>status</imsx_severity>
                <imsx_description>Score for StarX/StarX_DEMO/201X_StarX:\
edge.edx.org-i4x-StarX-StarX_DEMO-lti-40559041895b4065b2818c23b9cd9da8\
:18b71d3c46cb4dbe66a7c950d88e78ec is now 0.0</imsx_description>
                <imsx_messageRefIdentifier>
                </imsx_messageRefIdentifier>
            </imsx_statusInfo>
        </imsx_POXResponseHeaderInfo>
    </imsx_POXHeader>
    <imsx_POXBody><replaceResultResponse/></imsx_POXBody>
</imsx_POXEnvelopeResponse>
        """

    def setUp(self):
        """
        Setting up app config.
        """
        app.config['TESTING'] = True
        app.config['SERVER_NAME'] = 'localhost'
        app.config['WTF_CSRF_ENABLED'] = False
        app.config['SECRET_KEY'] = 'you-will-never-guess'
        app.config['AIOLTI_CONFIG'] = {'consumers': self.consumers}
        app.config['AIOLTI_URL_FIX'] = {
            "https://localhost:8000/": {
                "https://localhost:8000/": "http://localhost:8000/"
            }
        }
        self.app_client = app.test_client()
        app_exception.reset()

    @staticmethod
    def get_exception():
        """
        Returns exception raised by PyLTI.
        :return: exception
        """
        return app_exception.get()

    @staticmethod
    def has_exception():
        """
        Check if PyLTI raised exception.
        :return: is exception raised
        """
        return app_exception.get() is not None

    @staticmethod
    def get_exception_as_string():
        """
        Return text of the exception raised by LTI.
        :return: text
        """
        return "{}".format(TestQuart.get_exception())

    async def test_access_to_oauth_resource_unknown_protection(self):
        """
        Invalid LTI request scope.
        """
        await self.app_client.get('/unknown_protection')
        self.assertTrue(self.has_exception())
        self.assertIsInstance(self.get_exception(), LTIException)
        self.assertEqual(self.get_exception_as_string(),
                         'Unknown request type')

    async def test_access_to_oauth_resource_without_authorization_any(self):
        """
        Accessing LTI without establishing session.
        """
        await self.app_client.get('/any')
        self.assertTrue(self.has_exception())
        self.assertIsInstance(self.get_exception(), LTIException)
        self.assertEqual(self.get_exception_as_string(),
                         'Session expired or unavailable')

    async def test_access_to_oauth_resource_without_authorization_session(self):
        """
        Accessing LTI session scope before session established.
        """
        await self.app_client.get('/session')
        self.assertTrue(self.has_exception())
        self.assertIsInstance(self.get_exception(), LTIException)
        self.assertEqual(self.get_exception_as_string(),
                         'Session expired or unavailable')

    async def test_access_to_oauth_resource_without_authorization_initial_get(self):
        """
        Accessing LTI without basic-lti-launch-request parameters as GET.
        """
        await self.app_client.get('/initial')
        self.assertTrue(self.has_exception())
        self.assertIsInstance(self.get_exception(), LTIException)
        self.assertEqual(self.get_exception_as_string(),
                         'This page requires a valid oauth session or request')

    async def test_access_to_oauth_resource_without_authorization_initial_post(self):
        """
        Accessing LTI without basic-lti-launch-request parameters as POST.
        """
        await self.app_client.post('/initial')
        self.assertTrue(self.has_exception())
        self.assertIsInstance(self.get_exception(), LTIException)
        self.assertEqual(self.get_exception_as_string(),
                         'This page requires a valid oauth session or request')

    async def test_access_to_oauth_resource_in_session(self):
        """
        Accessing LTI after session established.
        """
        await self.app_client.get('/setup_session')

        await self.app_client.get('/session')

        self.assertFalse(self.has_exception())

    async def test_access_to_oauth_resource_in_session_with_close(self):
        """
        Accessing LTI after session closed.
        """
        await self.app_client.get('/setup_session')

        await self.app_client.get('/session')

        self.assertFalse(self.has_exception())

        await self.app_client.get('/close_session')

        await self.app_client.get('/session')

        self.assertTrue(self.has_exception())

    async def test_access_to_oauth_resource(self):
        """
        Accessing oauth_resource.
        """
        consumers = self.consumers
        url = 'http://localhost/initial?'
        new_url = self.generate_launch_request(consumers, url)

        await self.app_client.get(new_url)
        self.assertFalse(self.has_exception())

    async def test_access_to_oauth_resource_name_passed(self):
        """
        Check that name is returned if passed via initial request.
        """
        # pylint: disable=maybe-no-member
        consumers = self.consumers
        url = 'http://localhost/name?'
        add_params = {u'lis_person_sourcedid': u'person'}
        new_url = self.generate_launch_request(
            consumers, url, add_params=add_params
        )

        ret = await self.app_client.get(new_url)
        self.assertFalse(self.has_exception())
        data = await ret.get_data()
        self.assertEqual(data.decode('utf-8'), u'person')

    async def test_access_to_oauth_resource_email_passed(self):
        """
        Check that email is returned if passed via initial request.
        """
        # pylint: disable=maybe-no-member
        consumers = self.consumers
        url = 'http://localhost/name?'
        add_params = {u'lis_person_contact_email_primary': u'email@email.com'}
        new_url = self.generate_launch_request(
            consumers, url, add_params=add_params
        )

        ret = await self.app_client.get(new_url)
        self.assertFalse(self.has_exception())
        data = await ret.get_data()
        self.assertEqual(data.decode('utf-8'), u'email@email.com')

    async def test_access_to_oauth_resource_name_and_email_passed(self):
        """
        Check that name is returned if both email and name passed.
        """
        # pylint: disable=maybe-no-member
        consumers = self.consumers
        url = 'http://localhost/name?'
        add_params = {u'lis_person_sourcedid': u'person',
                      u'lis_person_contact_email_primary': u'email@email.com'}
        new_url = self.generate_launch_request(
            consumers, url, add_params=add_params
        )

        ret = await self.app_client.get(new_url)
        self.assertFalse(self.has_exception())
        data = await ret.get_data()
        self.assertEqual(data.decode('utf-8'), u'person')

    async def test_access_to_oauth_resource_staff_only_as_student(self):
        """
        Deny access if user not in role.
        """
        consumers = self.consumers
        url = 'http://localhost/initial_staff?'
        student_url = self.generate_launch_request(
            consumers, url, roles='Student'
        )
        await self.app_client.get(student_url)
        self.assertTrue(self.has_exception())

        learner_url = self.generate_launch_request(
            consumers, url, roles='Learner'
        )
        await self.app_client.get(learner_url)
        self.assertTrue(self.has_exception())

    async def test_access_to_oauth_resource_staff_only_as_administrator(self):
        """
        Allow access if user in role.
        """
        consumers = self.consumers
        url = 'http://localhost/initial_staff?'
        new_url = self.generate_launch_request(
            consumers, url, roles='Administrator'
        )

        await self.app_client.get(new_url)
        self.assertFalse(self.has_exception())

    async def test_access_to_oauth_resource_staff_only_as_unknown_role(self):
        """
        Deny access if role not defined.
        """
        consumers = self.consumers
        url = 'http://localhost/initial_staff?'
        admin_url = self.generate_launch_request(
            consumers, url, roles='Foo'
        )

        await self.app_client.get(admin_url)
        self.assertTrue(self.has_exception())

    async def test_access_to_oauth_resource_student_as_student(self):
        """
        Verify that the various roles we consider as students are students.
        """
        consumers = self.consumers
        url = 'http://localhost/initial_student?'

        # Learner Role
        learner_url = self.generate_launch_request(
            consumers, url, roles='Learner'
        )
        await self.app_client.get(learner_url)
        self.assertFalse(self.has_exception())

        student_url = self.generate_launch_request(
            consumers, url, roles='Student'
        )
        await self.app_client.get(student_url)
        self.assertFalse(self.has_exception())

    async def test_access_to_oauth_resource_student_as_staff(self):
        """Verify staff doesn't have access to student only."""
        consumers = self.consumers
        url = 'http://localhost/initial_student?'
        staff_url = self.generate_launch_request(
            consumers, url, roles='Instructor'
        )
        await self.app_client.get(staff_url)
        self.assertTrue(self.has_exception())

    async def test_access_to_oauth_resource_student_as_unknown(self):
        """Verify staff doesn't have access to student only."""
        consumers = self.consumers
        url = 'http://localhost/initial_student?'
        unknown_url = self.generate_launch_request(
            consumers, url, roles='FooBar'
        )
        await self.app_client.get(unknown_url)
        self.assertTrue(self.has_exception())

    @staticmethod
    def generate_launch_request(consumers, url,
                                lit_outcome_service_url=None,
                                roles=u'Instructor',
                                add_params=None,
                                include_lti_message_type=False):
        """
        Generate valid basic-lti-launch-request request with options.
        :param consumers: consumer map
        :param url: URL to sign
        :param lit_outcome_service_url: LTI callback
        :param roles: LTI role
        :return: signed request
        """
        # pylint: disable=unused-argument, too-many-arguments
        params = {'resource_link_id': u'edge.edx.org-i4x-MITx-ODL_ENG-lti-'
                                      u'94173d3e79d145fd8ec2e83f15836ac8',
                  'user_id': u'008437924c9852377e8994829aaac7a1',
                  'lis_result_sourcedid': u'MITx/ODL_ENG/2014_T1:'
                                          u'edge.edx.org-i4x-MITx-ODL_ENG-lti-'
                                          u'94173d3e79d145fd8ec2e83f15836ac8:'
                                          u'008437924c9852377e8994829aaac7a1',
                  'context_id': u'MITx/ODL_ENG/2014_T1',
                  'lti_version': u'LTI-1p0',
                  'launch_presentation_return_url': u'',
                  'lis_outcome_service_url': (lit_outcome_service_url or
                                              u'https://example.edu/'
                                              u'courses/MITx/ODL_ENG/'
                                              u'2014_T1/xblock/i4x:;_;'
                                              u'_MITx;_ODL_ENG;_lti;'
                                              u'_94173d3e79d145fd8ec2e'
                                              u'83f15836ac8'
                                              u'/handler_noauth/'
                                              u'grade_handler')}

        if include_lti_message_type:
            params['lti_message_type'] = u'basic-lti-launch-request'

        if roles is not None:
            params['roles'] = roles

        if add_params is not None:
            params.update(add_params)

        urlparams = urlencode(params)

        client = oauthlib.oauth1.Client('__consumer_key__',
                                        client_secret='__lti_secret__',
                                        signature_method=oauthlib.oauth1.
                                        SIGNATURE_HMAC,
                                        signature_type=oauthlib.oauth1.
                                        SIGNATURE_TYPE_QUERY)
        signature = client.sign("{}{}".format(url, urlparams))
        signed_url = signature[0]
        new_url = signed_url[len('http://localhost'):]
        return new_url

    async def test_access_to_oauth_resource_any(self):
        """
        Test access to LTI protected resources.
        """
        url = 'http://localhost/any?'
        new_url = self.generate_launch_request(self.consumers, url)
        await self.app_client.post(new_url)
        self.assertFalse(self.has_exception())

    async def test_access_to_oauth_resource_any_norole(self):
        """
        Test access to LTI protected resources.
        """
        url = 'http://localhost/any?'
        new_url = self.generate_launch_request(self.consumers, url, roles=None)
        await self.app_client.post(new_url)
        self.assertFalse(self.has_exception())

    async def test_access_to_oauth_resource_any_nonstandard_role(self):
        """
        Test access to LTI protected resources.
        """
        url = 'http://localhost/any?'
        new_url = self.generate_launch_request(self.consumers, url,
                                               roles=u'ThisIsNotAStandardRole')
        await self.app_client.post(new_url)
        self.assertFalse(self.has_exception())

    async def test_access_to_oauth_resource_invalid(self):
        """
        Deny access to LTI protected resources
        on man in the middle attack.
        """
        url = 'http://localhost/initial?'
        new_url = self.generate_launch_request(self.consumers, url)

        await self.app_client.get("{}&FAIL=TRUE".format(new_url))
        self.assertTrue(self.has_exception())
        self.assertIsInstance(self.get_exception(), LTIException)
        self.assertEqual(self.get_exception_as_string(),
                         'OAuth error: Please check your key and secret')

    async def test_access_to_oauth_resource_invalid_after_session_setup(self):
        """
        Remove browser session on man in the middle attach.
        """
        await self.app_client.get('/setup_session')
        await self.app_client.get('/session')
        self.assertFalse(self.has_exception())

        url = 'http://localhost/initial?'
        new_url = self.generate_launch_request(self.consumers, url)

        await self.app_client.get("{}&FAIL=TRUE".format(new_url))
        self.assertTrue(self.has_exception())
        self.assertIsInstance(self.get_exception(), LTIException)
        self.assertEqual(self.get_exception_as_string(),
                         'OAuth error: Please check your key and secret')

    @httpretty.activate
    async def test_access_to_oauth_resource_post_grade(self):
        """
        Check post_grade functionality.
        """
        # pylint: disable=maybe-no-member
        uri = (u'https://example.edu/courses/MITx/ODL_ENG/2014_T1/xblock/'
               u'i4x:;_;_MITx;_ODL_ENG;_lti;'
               u'_94173d3e79d145fd8ec2e83f15836ac8/handler_noauth'
               u'/grade_handler')

        httpretty.register_uri(httpretty.POST, uri, body=self.request_callback)

        consumers = self.consumers
        url = 'http://localhost/initial?'
        new_url = self.generate_launch_request(consumers, url)

        ret = await self.app_client.get(new_url)
        self.assertFalse(self.has_exception())

        ret = await self.app_client.get("/post_grade/1.0")
        self.assertFalse(self.has_exception())
        self.assertEqual(ret.data.decode('utf-8'), "grade=True")

        ret = await self.app_client.get("/post_grade/2.0")
        self.assertFalse(self.has_exception())
        self.assertEqual(ret.data.decode('utf-8'), "grade=False")

    @httpretty.activate
    async def test_access_to_oauth_resource_post_grade_fail(self):
        """
        Check post_grade functionality fails on invalid response.
        """
        # pylint: disable=maybe-no-member
        uri = (u'https://example.edu/courses/MITx/ODL_ENG/2014_T1/xblock/'
               u'i4x:;_;_MITx;_ODL_ENG;_lti;'
               u'_94173d3e79d145fd8ec2e83f15836ac8/handler_noauth'
               u'/grade_handler')

        def request_callback(request, cburi, headers):
            # pylint: disable=unused-argument
            """
            Mock error response callback.
            """
            return 200, headers, "wrong_response"

        httpretty.register_uri(httpretty.POST, uri, body=request_callback)

        consumers = self.consumers
        url = 'http://localhost/initial?'
        new_url = self.generate_launch_request(consumers, url)
        ret = await self.app_client.get(new_url)
        self.assertFalse(self.has_exception())
        self.assertFalse(self.has_exception())

        ret = await self.app_client.get("/post_grade/1.0")
        self.assertTrue(self.has_exception())
        self.assertEqual(ret.data.decode('utf-8'), "error")

    @httpretty.activate
    async def test_access_to_oauth_resource_post_grade_fix_url(self):
        """
        Make sure URL remap works for edX vagrant stack.
        """
        # pylint: disable=maybe-no-member
        uri = 'https://localhost:8000/dev_stack'

        httpretty.register_uri(httpretty.POST, uri, body=self.request_callback)

        url = 'http://localhost/initial?'
        new_url = self.generate_launch_request(
            self.consumers, url, lit_outcome_service_url=uri
        )
        ret = await self.app_client.get(new_url)
        self.assertFalse(self.has_exception())

        ret = await self.app_client.get("/post_grade/1.0")
        self.assertFalse(self.has_exception())
        self.assertEqual(ret.data.decode('utf-8'), "grade=True")

        ret = await self.app_client.get("/post_grade/2.0")
        self.assertFalse(self.has_exception())
        self.assertEqual(ret.data.decode('utf-8'), "grade=False")

    @httpretty.activate
    async def test_access_to_oauth_resource_post_grade2(self):
        """
        Check post_grade edX LTI2 functionality.
        """
        uri = (u'https://example.edu/courses/MITx/ODL_ENG/2014_T1/xblock/'
               u'i4x:;_;_MITx;_ODL_ENG;_lti;'
               u'_94173d3e79d145fd8ec2e83f15836ac8/handler_noauth'
               u'/lti_2_0_result_rest_handler/user/'
               u'008437924c9852377e8994829aaac7a1')

        httpretty.register_uri(httpretty.PUT, uri, body=self.request_callback)

        consumers = self.consumers
        url = 'http://localhost/initial?'
        new_url = self.generate_launch_request(consumers, url)

        ret = await self.app_client.get(new_url)
        self.assertFalse(self.has_exception())

        ret = await self.app_client.get("/post_grade2/1.0")
        self.assertFalse(self.has_exception())
        self.assertEqual(ret.data.decode('utf-8'), "grade=True")

        ret = await self.app_client.get("/post_grade2/2.0")
        self.assertFalse(self.has_exception())
        self.assertEqual(ret.data.decode('utf-8'), "grade=False")

    def request_callback(self, request, cburi, headers):
        # pylint: disable=unused-argument
        """
        Mock expected response.
        """
        return 200, headers, self.expected_response

    @httpretty.activate
    async def test_access_to_oauth_resource_post_grade2_fail(self):
        """
        Check post_grade edX LTI2 functionality
        """
        uri = (u'https://example.edu/courses/MITx/ODL_ENG/2014_T1/xblock/'
               u'i4x:;_;_MITx;_ODL_ENG;_lti;'
               u'_94173d3e79d145fd8ec2e83f15836ac8/handler_noauth'
               u'/lti_2_0_result_rest_handler/user/'
               u'008437924c9852377e8994829aaac7a1')

        def request_callback(request, cburi, headers):
            # pylint: disable=unused-argument
            """
            Mock expected response.
            """
            return 400, headers, self.expected_response

        httpretty.register_uri(httpretty.PUT, uri, body=request_callback)

        consumers = self.consumers
        url = 'http://localhost/initial?'
        new_url = self.generate_launch_request(consumers, url)

        ret = await self.app_client.get(new_url)
        self.assertFalse(self.has_exception())

        ret = await self.app_client.get("/post_grade2/1.0")
        self.assertTrue(self.has_exception())
        self.assertEqual(ret.data.decode('utf-8'), "error")

    @mock.patch.object(LTI, '_check_role')
    @mock.patch.object(LTI, 'verify')
    async def test_decorator_no_app(self, mock_verify, _):
        """Verify the decorator doesn't require the app object."""
        # pylint: disable=maybe-no-member
        mock_verify.return_value = True
        response = await self.app_client.get('/no_app')
        self.assertEqual(200, response.status_code)
        data = await response.get_data()
        self.assertEqual('hi', data.decode('utf-8'))

    async def test_default_decorator(self):
        """
        Verify default decorator works.
        """
        url = 'http://localhost.local/default_lti?'
        new_url = self.generate_launch_request(self.consumers, url)
        await self.app_client.get(new_url)
        self.assertFalse(self.has_exception())

    async def test_default_decorator_bad(self):
        """
        Verify error handling works.
        """
        # Validate we get our error page when there is a bad LTI
        # request
        # pylint: disable=maybe-no-member
        response = await self.app_client.get('/default_lti')
        self.assertEqual(500, response.status_code)
        data = await response.get_data()
        self.assertEqual("error", data.decode('utf-8'))
