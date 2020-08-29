# -*- coding: utf-8 -*-
"""
    aioLTI decorator implementation for Quart framework
"""
from __future__ import absolute_import
from functools import wraps
import logging

from quart import session, current_app, Quart
from quart.exceptions import BadRequest
from quart import request as quart_request

from .common import (
    LTI_SESSION_KEY,
    LTI_PROPERTY_LIST,
    verify_request_common,
    LTIException,
    LTINotInSessionException,
    LTIBase
)


log = logging.getLogger('aiolti.quart')  # pylint: disable=invalid-name


class LTIRequestError(BadRequest):
    def __init__(self, lti_exception: LTIException = None):
        super().__init__()
        self.lti_exception = lti_exception
        if lti_exception is not None and len(lti_exception.args) > 0:
            self.description = f"LTI Error: {lti_exception.args[0]}"
        else:
            self.description = "Unknown LTI Error"


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

    async def _verify_request(self):
        """
        Verify LTI request
        :raises: LTIException is request validation failed
        """
        if quart_request.method == 'POST':
            form = await quart_request.form
            params = form.to_dict()
        else:
            params = quart_request.args.to_dict()
        log.debug(params)
        log.debug('_verify_request?')
        try:
            verify_request_common(self._consumers(), quart_request.url,
                                  quart_request.method, quart_request.headers,
                                  params)
            log.debug('_verify_request success')

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
            log.debug('_verify_request failed')
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
            form = await quart_request.form
            params = form.to_dict()
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
            self._verify_request()
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


# XXX WTH re: varargs after optional args?? - spapadim
def lti(app=None, request='any', role='any',
        *lti_args, **lti_kwargs):
    """
    LTI decorator

    :param: app - Quart App object (optional).
        :py:attr:`quart.current_app` is used if no object is passed in
    :param: request - Request type from
        :py:attr:`aiolti.common.LTI_REQUEST_TYPE`. (default: any)
    :param: roles - LTI Role (default: any)
    :return: wrapper
    """

    # XXX - Why is this nested? So a partial bind can be done (but: see comments
    #   below -- also, could use functools.partial, if still really necesasry..)
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
                await the_lti.verify()
                the_lti._check_role()  # pylint: disable=protected-access
                kwargs['lti'] = the_lti
                return await function(*args, **kwargs)
            except LTIException as lti_exception:
                raise LTIRequestError(lti_exception=lti_exception)

        return wrapper

    lti_kwargs['request'] = request
    lti_kwargs['role'] = role

    if (not app) or isinstance(app, Quart):
        lti_kwargs['app'] = app
        return _lti
    else:
        # We are wrapping without arguments
        # XXX What is this?? If I'm getting this straight, seems like the decorator 
        #   can also be used as.. not decorator? If so, should just instantiate
        #   "lti = LTI(app)" once, globally... actually, should do that anyway -- spapadim
        lti_kwargs['app'] = None
        return _lti(app)
