# -*- coding: utf-8 -*-
"""
    aioLTI decorator implementation for Quart framework
"""
from __future__ import absolute_import
from functools import wraps
import logging

from quart import session, current_app, Quart
from quart import request as quart_request

from .common import (
    LTI_SESSION_KEY,
    LTI_PROPERTY_LIST,
    verify_request_common,
    default_error,
    LTIException,
    LTINotInSessionException,
    LTIBase
)


log = logging.getLogger('aiolti.quart')  # pylint: disable=invalid-name


class LTI(LTIBase):
    """
    LTI Object represents abstraction of current LTI session. It provides
    callback methods and methods that allow developer to inspect
    LTI basic-launch-request.

    This object is instantiated by @lti wrapper.
    """

    def __init__(self, lti_args, lti_kwargs):
        self.session = session
        LTIBase.__init__(self, lti_args, lti_kwargs)
        # Set app to current_app if not specified
        if not self.lti_kwargs['app']:
            self.lti_kwargs['app'] = current_app

    def _consumers(self):
        """
        Gets consumer's map from app config

        :return: consumers map
        """
        app_config = self.lti_kwargs['app'].config
        config = app_config.get('AIOLTI_CONFIG', dict())
        consumers = config.get('consumers', dict())
        return consumers

    async def verify_request(self):
        """
        Verify LTI request
        :raises: LTIException is request validation failed
        """
        if quart_request.method == 'POST':
            params = quart_request.form.to_dict()
        else:
            params = quart_request.args.to_dict()
        log.debug(params)
        log.debug('verify_request?')
        try:
            await verify_request_common(self._consumers(), quart_request.url,
                                        quart_request.method, quart_request.headers,
                                        params)
            log.debug('verify_request success')

            # All good to go, store all of the LTI params into a
            # session dict for use in views
            for prop in LTI_PROPERTY_LIST:
                if params.get(prop, None):
                    log.debug("params %s=%s", prop, params.get(prop, None))
                    session[prop] = params[prop]

            # Set logged in session key
            session[LTI_SESSION_KEY] = True
            return True
        except LTIException:
            log.debug('verify_request failed')
            for prop in LTI_PROPERTY_LIST:
                if session.get(prop, None):
                    del session[prop]

            session[LTI_SESSION_KEY] = False
            raise

    @property
    def response_url(self):
        """
        Returns remapped lis_outcome_service_url
        uses AIOLTI_URL_FIX map to support edX dev-stack

        :return: remapped lis_outcome_service_url
        """
        url = ""
        url = self.session['lis_outcome_service_url']
        app_config = self.lti_kwargs['app'].config
        urls = app_config.get('AIOLTI_URL_FIX', dict())
        # url remapping is useful for using devstack
        # devstack reports httpS://localhost:8000/ and listens on HTTP
        for prefix, mapping in urls.items():
            if url.startswith(prefix):
                for _from, _to in mapping.items():
                    url = url.replace(_from, _to)
        return url

    async def _verify_any(self):
        """
        Verify that an initial request has been made, or failing that, that
        the request is in the session
        :raises: LTIException
        """
        log.debug('verify_any enter')

        # Check to see if there is a new LTI launch request incoming
        newrequest = False
        if quart_request.method == 'POST':
            params = quart_request.form.to_dict()
            initiation = "basic-lti-launch-request"
            if params.get("lti_message_type", None) == initiation:
                newrequest = True
                # Scrub the session of the old authentication
                for prop in LTI_PROPERTY_LIST:
                    if session.get(prop, None):
                        del session[prop]
                session[LTI_SESSION_KEY] = False

        # Attempt the appropriate validation
        # Both of these methods raise LTIException as necessary
        if newrequest:
            await self.verify_request()
        else:
            self._verify_session()

    @staticmethod
    def _verify_session():
        """
        Verify that session was already created

        :raises: LTIException
        """
        if not session.get(LTI_SESSION_KEY, False):
            log.debug('verify_session failed')
            raise LTINotInSessionException('Session expired or unavailable')

    @staticmethod
    def close_session():
        """
        Invalidates session
        """
        for prop in LTI_PROPERTY_LIST:
            if session.get(prop, None):
                del session[prop]
        session[LTI_SESSION_KEY] = False


# XXX WTH re: varargs?? - spapadim
def lti(app=None, request='any', error=default_error, role='any',
        *lti_args, **lti_kwargs):
    """
    LTI decorator

    :param: app - Quart App object (optional).
        :py:attr:`quart.current_app` is used if no object is passed in
    :param: error - Callback if LTI throws exception (optional).
        :py:attr:`aiolti.quart.default_error` is the default.
    :param: request - Request type from
        :py:attr:`aiolti.common.LTI_REQUEST_TYPE`. (default: any)
    :param: roles - LTI Role (default: any)
    :return: wrapper
    """

    def _lti(function):
        """
        Inner LTI decorator

        :param: function:
        :return:
        """

        @wraps(function)
        async def wrapper(*args, **kwargs):
            """
            Pass LTI reference to function or return error.
            """
            try:
                the_lti = LTI(lti_args, lti_kwargs)
                the_lti.verify()
                the_lti._check_role()  # pylint: disable=protected-access
                kwargs['lti'] = the_lti
                return await function(*args, **kwargs)
            except LTIException as lti_exception:
                error = lti_kwargs.get('error')
                exception = dict()
                exception['exception'] = lti_exception
                exception['kwargs'] = kwargs
                exception['args'] = args
                return await error(exception=exception)

        return wrapper

    lti_kwargs['request'] = request
    lti_kwargs['error'] = error
    lti_kwargs['role'] = role

    if (not app) or isinstance(app, Quart):
        lti_kwargs['app'] = app
        return _lti
    else:
        # We are wrapping without arguments
        # XXX How/why/where??!? - spapadim
        lti_kwargs['app'] = None
        return _lti(app)
