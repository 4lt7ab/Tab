# Destructive git operations

**When this applies:** Anytime you'd run `git reset --hard`, `git push --force`, branch deletion, `git clean -f`, or any other operation that throws away local or remote state.

Get explicit confirmation in the current turn first. A user approving a destructive op once does not authorize it for later turns. If the user says "ok force-push that," the authorization is for that one push, not for any subsequent rewrite.

When in doubt, propose the safer alternative (a new commit, a feature branch, a soft reset) and ask before doing the destructive thing.
