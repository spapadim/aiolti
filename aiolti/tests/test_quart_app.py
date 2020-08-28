"""
Test pylti/test_flask_app.py module
"""
from quart import Quart, session

from aiolti.quart import lti as lti_quart
from aiolti.common import LTI_SESSION_KEY
from aiolti.tests.test_common import ExceptionHandler

app = Quart(__name__)  # pylint: disable=invalid-name
app_exception = ExceptionHandler()  # pylint: disable=invalid-name


def error(exception):
    """
    Set exception to exception handler and returns error string.
    """
    app_exception.set(exception)
    return "error"


@app.route("/unknown_protection")
@lti_quart(error=error, app=app, request='notreal')
async def unknown_protection(lti):
    # pylint: disable=unused-argument,
    """
    Access route with unknown protection.

    :param lti: `lti` object
    :return: string "hi"
    """
    return "hi"  # pragma: no cover


@app.route("/no_app")
@lti_quart(error=error)
async def no_app(lti):
    # pylint: disable=unused-argument,
    """
    Use decorator without specifying LTI, raise exception.

    :param lti: `lti` object
    """
    # Check that we have the app in our lti object and raise if we
    # don't
    if not lti.lti_kwargs['app']:  # pragma: no cover
        raise Exception(
            'The app is null and is not properly getting current_app'
        )
    return 'hi'


@app.route("/any")
@lti_quart(error=error, request='any', app=app)
async def any_route(lti):
    # pylint: disable=unused-argument,
    """
    Access route with 'any' request.

    :param lti: `lti` object
    :return: string "hi"
    """
    return "hi"


@app.route("/session")
@lti_quart(error=error, request='session', app=app)
async def session_route(lti):
    # pylint: disable=unused-argument,
    """
    Access route with 'session' request.

    :param lti: `lti` object
    :return: string "hi"
    """
    return "hi"


@app.route("/initial", methods=['GET', 'POST'])
@lti_quart(error=error, request='initial', app=app)
async def initial_route(lti):
    # pylint: disable=unused-argument,
    """
    Access route with 'initial' request.

    :param lti: `lti` object
    :return: string "hi"
    """
    return "hi"


@app.route("/name", methods=['GET', 'POST'])
@lti_quart(error=error, request='initial', app=app)
async def name(lti):
    """
    Access route with 'initial' request.

    :param lti: `lti` object
    :return: string "hi"
    """
    return lti.name


@app.route("/initial_staff", methods=['GET', 'POST'])
@lti_quart(error=error, request='initial', role='staff', app=app)
async def initial_staff_route(lti):
    # pylint: disable=unused-argument,
    """
    Access route with 'initial' request and 'staff' role.

    :param lti: `lti` object
    :return: string "hi"
    """
    return "hi"


@app.route("/initial_student", methods=['GET', 'POST'])
@lti_quart(error=error, request='initial', role='student', app=app)
async def initial_student_route(lti):
    # pylint: disable=unused-argument,
    """
    Access route with 'initial' request and 'student' role.

    :param lti: `lti` object
    :return: string "hi"
    """
    return "hi"


@app.route("/initial_unknown", methods=['GET', 'POST'])
@lti_quart(error=error, request='initial', role='unknown', app=app)
async def initial_unknown_route(lti):
    # pylint: disable=unused-argument,
    """
    Access route with 'initial' request and 'unknown' role.

    :param lti: `lti` object
    :return: string "hi"
    """
    return "hi"  # pragma: no cover


@app.route("/setup_session")
async def setup_session():
    """
    Access 'setup_session' route with 'Student' role and oauth_consumer_key.

    :return: string "session set"
    """
    session[LTI_SESSION_KEY] = True
    session['oauth_consumer_key'] = '__consumer_key__'
    session['roles'] = 'Student'
    return "session set"


@app.route("/close_session")
@lti_quart(error=error, request='session', app=app)
async def logout_route(lti):
    """
    Access 'close_session' route.

    :param lti: `lti` object
    :return: string "session closed"
    """
    lti.close_session()
    return "session closed"


@app.route("/post_grade/<float:grade>")
@lti_quart(error=error, request='session', app=app)
async def post_grade(grade, lti):
    """
    Access route with 'session' request.

    :param lti: `lti` object
    :return: string "grade={}"
    """
    ret = await lti.post_grade(grade)
    return "grade={}".format(ret)


@app.route("/post_grade2/<float:grade>")
@lti_quart(error=error, request='session', app=app)
async def post_grade2(grade, lti):
    """
    Access route with 'session' request.

    :param lti: `lti` object
    :return: string "grade={}"
    """
    ret = await lti.post_grade2(grade)
    return "grade={}".format(ret)


@app.route("/default_lti")
@lti_quart
async def default_lti(lti=lti_quart):
    # pylint: disable=unused-argument,
    """
    Make sure default LTI decorator works.
    """
    return 'hi'  # pragma: no cover
