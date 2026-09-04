Review main.py, crud.py, models.py, and schemas.py for functions that
genuinely benefit from a docstring - ones where the name and
signature alone don't fully convey what the function does, why it
exists, or any non-obvious behavior (e.g. retry logic, validation
rules, side effects). Skip functions that are already fully clear
from their name and signature alone - don't add a docstring just to
have one.

Also review README.md for accuracy against the current code - flag
anything outdated or missing (new routes, changed behavior).

Show me the proposed docstring and README changes before applying
them. Keep docstrings concise - one or two sentences, explaining the
non-obvious part, not restating the code line by line.