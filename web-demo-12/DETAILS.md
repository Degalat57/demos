## What this is
A minimal local Python web app: a form page sends input to a POST /api/process endpoint, which validates it and returns a JSON summary or structured JSON errors. It was built from the public job post on synthetic data, not on client data. It uses only the Python standard library (a Flask + Pydantic version is a direct port).

## Done
- POST /api/process: validates a label and a list of numbers, returns count, sum, mean, min, max
- Clear JSON errors: 400 for empty or malformed bodies, 422 with per-field errors, 404/405 for wrong routes
- One HTML page that submits the form and renders the returned JSON or the errors
- 6 automated checks (valid known answer, empty, malformed, field errors, limits, routes)
- Local server: `python3 poc.py --serve`, then open localhost port 8000

## Remaining
- The real input fields and JSON output shape the app needs
- Port to Flask with Pydantic models if preferred
- Styling and branding of the page
- Headless browser check (browser not available in this build sandbox)

## How to run
`python3 poc.py`

Built from the public job post on synthetic data; not client work. The code is yours if you hire me.
