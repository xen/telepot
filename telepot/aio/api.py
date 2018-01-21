import aiohttp
import re
import json
from .. import exception
from ..api import _guess_filename

_proxy = None  # (url, (username, password))

def set_proxy(url, basic_auth=None):
    global _proxy
    if not url:
        _proxy = None
    else:
        _proxy = (url, basic_auth) if basic_auth else (url,)

def _compose_data(req):
    token, method, params, files = req

    data = aiohttp.FormData()

    if params:
        for key,value in params.items():
            data.add_field(key, str(value))

    if files:
        for key,f in files.items():
            if isinstance(f, tuple):
                if len(f) == 2:
                    filename, fileobj = f
                else:
                    raise ValueError('Tuple must have exactly 2 elements: filename, fileobj')
            else:
                filename, fileobj = _guess_filename(f) or key, f

            data.add_field(key, fileobj, filename=filename)

    return data

async def _parse(response):
    try:
        data = await response.json()
        if data is None:
            raise ValueError()
    except (ValueError, json.JSONDecodeError, aiohttp.ClientResponseError):
        text = await response.text()
        raise exception.BadHTTPResponse(response.status, text, response)

    if data['ok']:
        return data['result']
    else:
        description, error_code = data['description'], data['error_code']

        # Look for specific error ...
        for e in exception.TelegramError.__subclasses__():
            n = len(e.DESCRIPTION_PATTERNS)
            if any(map(re.search, e.DESCRIPTION_PATTERNS, n*[description], n*[re.IGNORECASE])):
                raise e(description, error_code, data)

        # ... or raise generic error
        raise exception.TelegramError(description, error_code, data)

