"""Stdlib WSGI app: POST /api/process validates JSON input and returns a JSON summary; GET / serves the UI."""
import json
from pathlib import Path

PAGE = (Path(__file__).parent / 'index.html').read_text('utf-8')


def validate(payload):
    """Return a list of {field, error} dicts (empty means valid)."""
    errs = []
    if not isinstance(payload, dict):
        return [{'field': '', 'error': 'body must be a JSON object'}]
    label = payload.get('label')
    if not isinstance(label, str) or not label.strip():
        errs.append({'field': 'label', 'error': 'required non-empty text'})
    elif len(label) > 50:
        errs.append({'field': 'label', 'error': 'at most 50 characters'})
    vals = payload.get('values')
    if not isinstance(vals, list) or not vals:
        errs.append({'field': 'values', 'error': 'required non-empty list of numbers'})
    elif len(vals) > 100:
        errs.append({'field': 'values', 'error': 'at most 100 numbers'})
    else:
        for i, v in enumerate(vals):
            if isinstance(v, bool) or not isinstance(v, (int, float)):
                errs.append({'field': 'values[%d]' % i, 'error': 'must be a number'})
    extra = sorted(set(payload) - {'label', 'values'})
    for k in extra:
        errs.append({'field': k, 'error': 'unknown field'})
    return errs


def process(raw):
    """raw bytes -> (status code, response dict)."""
    if not raw or not raw.strip():
        return 400, {'ok': False, 'errors': [{'field': '', 'error': 'empty body'}]}
    try:
        payload = json.loads(raw.decode('utf-8'))
    except (ValueError, UnicodeDecodeError):
        return 400, {'ok': False, 'errors': [{'field': '', 'error': 'malformed JSON'}]}
    errs = validate(payload)
    if errs:
        return 422, {'ok': False, 'errors': errs}
    v = payload['values']
    return 200, {'ok': True, 'result': {'label': payload['label'].strip(), 'count': len(v),
                 'sum': round(sum(v), 6), 'mean': round(sum(v) / len(v), 6), 'min': min(v), 'max': max(v)}}


REASONS = {200: 'OK', 400: 'Bad Request', 404: 'Not Found', 405: 'Method Not Allowed', 422: 'Unprocessable Entity'}


def app(environ, start_response):
    path, method = environ.get('PATH_INFO', '/'), environ.get('REQUEST_METHOD', 'GET')
    if path == '/' and method == 'GET':
        body, ctype, status = PAGE.encode('utf-8'), 'text/html; charset=utf-8', 200
    else:
        if path != '/api/process':
            status, data = 404, {'ok': False, 'errors': [{'field': '', 'error': 'not found'}]}
        elif method != 'POST':
            status, data = 405, {'ok': False, 'errors': [{'field': '', 'error': 'use POST'}]}
        else:
            n = int(environ.get('CONTENT_LENGTH') or 0)
            status, data = process(environ['wsgi.input'].read(n) if n else b'')
        body, ctype = json.dumps(data, indent=2, sort_keys=True).encode('utf-8'), 'application/json'
    start_response('%d %s' % (status, REASONS[status]), [('Content-Type', ctype), ('Content-Length', str(len(body)))])
    return [body]
