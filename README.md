# aioLTI - port of PyLTI to asyncio and Quart

This fork of PyLTI is a quick port so it works with the Quart async framework.
Feel free to use/experiment with it (at your own risk, of course).

For further information, the [original MITODL repository](https://github.com/mitodl/pylti) 
may be of some help.

## Notes

The only API change at the level of the Quart `@lti` decorator is that you don't need to pass an `error=` argument each time. Instead, you should use an `@app.errorhandler(LTIRequestError)` handler.

\<soapbox\> However, the decorator *still* needs an `app` argument each time. Also, it *still* instantiates a brand new `LTI` object for each decoration, and will *still* pass that object as an argument to the handler. I admit I don't understand this API design choice, vs. instantiating `LTI` once (globally, with an `app` argument) and overload it's `__call__` to decorate handlers. Furthermore, the LTI fields could just be added into a custom request context, rather than passing a separate argument into the handler. Maybe I'll fix this at some point, but currently need to actually start using this (and don't want to spend time un-tangling the request-specific bits out of the `LTI` object properties). \</soapbox\>