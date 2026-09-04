Review this codebase for issues. Check specifically for:
- Duplicated logic that could be extracted into a shared helper
- Missing or inconsistent error handling
- Formatting or naming inconsistencies with the rest of the codebase
- Unused functions, imports, or variables
- Data integrity issues - anything that could allow invalid or
  conflicting states that shouldn't be possible (e.g. missing
  uniqueness constraints, missing validation)
- Anything that works correctly today but could be a hidden risk
  under specific edge cases or concurrent use

Don't hold back just because the code currently works - flag anything
worth reconsidering, even if it's a smaller stylistic point.