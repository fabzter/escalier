# First public snapshot — privacy and provenance plan

Status: **PLANNED, NOT PUSHED**. 2026-10-26. This is a coordinator execution ruling, not a new owner product decision or a claim that the publication audit has passed.

## Authority and finding

The owner approved creating and pushing public `fabzter/escalier` after privacy review, under the personal Git identity, while retaining the feasibility spikes and their findings. The approved remote currently has no published content.

Task 4's current-tree fix and scoped re-review passed. Its report also correctly identifies private identity fragments in an earlier, unpublished development blob. A later clean commit does not remove that blob from the ancestry. **The existing development branch must not be pushed as public history.** No private fragment is reproduced in this plan.

## Non-destructive publication ruling

Publish the final audited tree as a **new root commit on a new local `main` branch**, then push only that branch. Keep the existing local development branch and all its commits unchanged. Do not rewrite refs, delete history, expire reflogs, prune objects, force-push or publish the private development branch.

Why: the remote is empty, so a new public root preserves every approved final artifact without exposing superseded private drafts or changing existing public history. This implements the already-approved target/visibility with a safer history boundary.

Cost if wrong: development commit IDs quoted in retained review reports will not resolve in the public repository. They remain useful local audit references, not public checkout instructions. Findings must therefore retain exact executed-file/library/model hashes and an explicit explanation of this boundary. A public source-tree identity and reachable-history audit are required; a green scan of the working tree alone is insufficient.

## Required gates before creating or pushing `main`

1. Finish task-scoped reviews/fix loops, real-model measurements and the single broad integration review. Do not replace interactive NOT RUN labels with build/test results.
2. Freeze and commit the final approved tree. Retain commands, source/model/library fingerprints and measurement limitations. Check that numerical target-file hashes match the committed blobs actually executed; environment variables alone are not evidence of target selection.
3. Run the complete current-tree privacy scan, inspect the staged/published path list, and exclude models, caches, apps, raw private paths, generated build logs and session-scratch data. Stage only approved curated results.
4. Audit authors and committers across local refs, tagger identities, and the effective local identity. No work identity is permitted. Personal author attribution is intentional.
5. Verify the configured origin is the approved public repository and that it still has no published branch requiring reconciliation. Refuse to overwrite an existing local `main` or a changed remote.
6. Create a new root commit from the exact final audited Git tree, with no parent; create `main` without switching or disturbing the active development worktree. Record the source and public tree IDs and prove they are identical.
7. Inspect **all objects reachable from the public ref**. Prove the new root has no parent and only the intended commit/tree/blobs are reachable. Audit its metadata and content, not the development branch's ancestry.
8. Push only `refs/heads/main:refs/heads/main`, without force or automatic tag publication. Do not push all branches, tags or mirror refs.
9. Read back the remote SHA, public visibility, default branch and exact tree identity. Refresh the remote ref in the existing local clone rather than merging the unrelated private development branch. Confirm the only published branch is the intended one.

## Reproducibility boundary

- Retained review commit IDs refer to the local development lineage unless explicitly labelled as public.
- Numerical source hashes and the pinned native-engine/model identities establish the executed measurement inputs independently of that lineage.
- The public root contains the final reviewed files and retained reports, not a claim that every historical draft was public or safe.
- Ad-hoc bundle signing and headless tests do not establish GUI launch, capture exclusion, global-key suppression, browser non-delivery, TCC grant reuse or HackerRank server-side invisibility.
