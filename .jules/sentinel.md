## 2024-05-23 - Git Argument Injection via Branch Names
**Vulnerability:** User-controlled branch names (e.g., starting with `-`) can be interpreted as flags by `git` commands if not properly separated or validated. For example, a branch named `-f` could cause `git push origin -f` (force push).
**Learning:** Even though `git` makes it difficult to create such branches, they are possible (e.g., `git branch -- -f`). Tools wrapping `git` must assume branch names are untrusted input.
**Prevention:**
1. Validate branch names to reject those starting with `-`.
2. Always use `--` separator for `git` commands that accept revisions/refs (e.g., `git push origin -- <branch>`).
3. For `git log`, use `--end-of-options` to separate options from revisions if the revision might look like a flag.
