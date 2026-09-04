Run the full pytest suite. If all tests pass, simply report that -
no further action needed.

For EVERY failing test, do NOT make any code changes yet - first
diagnose and report:
- Which test failed
- What the actual root cause is
- Whether the fix belongs in the application code or the test itself
- A proposed fix, described clearly

If the fix is to the test itself, explain precisely why the test's
ORIGINAL expectation was wrong, not just what change would make it
pass. Never weaken or disable a test to make it pass - no loosening
assertions, removing checks, or skipping/marking it as expected to
fail - unless you can clearly justify the original test was
genuinely incorrect.

Present all failures and proposed fixes together as a summary. Wait
for explicit approval before making any actual code changes. Do not
assume a fix is correct just because it would make a test pass -
consider whether it matches the codebase's existing patterns and
conventions.