Review pull request #$ARGUMENTS on this repository.

Steps:
1. Load CLAUDE.md to understand this project's specific context,
   conventions, and known limitations.
2. Fetch the PR's details and diff using gh (gh pr view $ARGUMENTS,
   gh pr diff $ARGUMENTS).
3. Delegate to the code-reviewer subagent to review the actual
   changes in the diff - not the whole codebase, specifically what
   this PR changes.
4. Delegate to the test-engineer subagent to check whether the PR's
   changes are adequately tested - are there new tests for new
   behavior, and do existing tests still make sense given the change?
5. Synthesize both subagents' findings into one clear summary:
   - Overall assessment (ready to merge, needs changes, or unclear)
   - Findings from code-reviewer
   - Findings from test-engineer
   - Any conflicts or disagreements between the two reviews

Do not make any code changes - this command is read-only, review only.