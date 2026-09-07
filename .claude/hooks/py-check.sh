#!/usr/bin/env bash
set -u

f=$(python -c "
import json, sys
data = json.load(sys.stdin)
print(data.get('tool_input', {}).get('file_path') or data.get('tool_response', {}).get('filePath') or '')
")

case "$f" in
  *.py) ;;
  *) exit 0 ;;
esac

VENV="C:/Users/hp/url-shortener/venv/Scripts"
ruff_log=$(mktemp)
pytest_log=$(mktemp)

"$VENV/ruff.exe" check . >"$ruff_log" 2>&1
ruff_rc=$?
"$VENV/pytest.exe" >"$pytest_log" 2>&1
pytest_rc=$?

RUFF_RC="$ruff_rc" PYTEST_RC="$pytest_rc" RUFF_LOG="$ruff_log" PYTEST_LOG="$pytest_log" FILE="$f" python -c "
import json, os

ruff_rc = int(os.environ['RUFF_RC'])
pytest_rc = int(os.environ['PYTEST_RC'])
f = os.environ['FILE']

with open(os.environ['RUFF_LOG'], encoding='utf-8', errors='replace') as fh:
    ruff_out = fh.read()
with open(os.environ['PYTEST_LOG'], encoding='utf-8', errors='replace') as fh:
    pytest_out = fh.read()

if ruff_rc != 0 or pytest_rc != 0:
    reason = (
        f'=== ruff check . (exit {ruff_rc}) ===\n{ruff_out}\n\n'
        f'=== pytest (exit {pytest_rc}) ===\n{pytest_out}'
    )
    print(json.dumps({
        'systemMessage': f'ruff/pytest found issues after editing {f}',
        'decision': 'block',
        'reason': reason,
    }))
else:
    print(json.dumps({
        'systemMessage': f'ruff check . and pytest passed after editing {f}',
    }))
"

rm -f "$ruff_log" "$pytest_log"
