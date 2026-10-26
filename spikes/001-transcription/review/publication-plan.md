# First public snapshot — privacy and provenance plan

Status: **COMPLETED — INITIAL PUBLIC ROOT PUSHED AND VERIFIED**. 2026-10-26. The execution record below applies to the first public snapshot, not product/runtime readiness.

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

## Execution record — initial public snapshot

- Approved repository: `https://github.com/fabzter/escalier`, read back as **PUBLIC**.
- Retained private development tip: `0ff4ac5909f1f04bca625a7b79afd14a4c537cfa` on local `spike/transcription`, unchanged and not published.
- Initial public root: `28841def783c410c59ed00bbc8309b7a826c53dc`, with **zero parents**.
- Exact initial public tree: `befa8b76e4b03809e49cf4d2ad2cda07790d369f`, equal to the final audited development tree; **209 files**.
- Reachable-object audit: **1 commit, 46 trees, 209 blobs**. No private development commit and neither known pre-fix scanner/test blob was reachable. All paths were ordinary tracked files, without model/build/cache/session-state paths or symlinks.
- A generated `git archive main` export matched all 209 committed blobs byte for byte. All 205 non-audio files were UTF-8 and within the scanner's size limit; the four WAV files were canonical mono PCM 16-bit/16 kHz with only `fmt ` and `data` chunks, not hidden metadata containers. The exported scanner checked that exact export: 209 candidate files, no findings.
- Effective author/committer and every local-ref commit identity were the approved personal identity. Public-root metadata matched it. No tags/tagger identities existed. Content checks and metadata checks were separate.
- The remote was still empty immediately before the push. Only `refs/heads/main:refs/heads/main` was pushed, without force or automatic tags.
- Remote readback matched the root SHA and tree above; visibility was PUBLIC, default branch `main`, and the only published branch was `main`, with no tags.
- The existing local clone was then switched to public `main`, configured to track `origin/main`, and updated with `git pull --ff-only --no-tags`: already up to date, clean. The private development branch stayed at its original tip.
- No refs were rewritten/deleted, no reflogs expired, no garbage collection/pruning ran, and no app launch, GUI/capture/tap/permission action or security-state change occurred.

This operational record is retained as a documentation-only descendant of the public root. The root/tree IDs above identify the initial exact reviewed snapshot, not every later documentation tip. Any descendant must retain the public-only ancestry and pass its own content/identity/reachability check before a normal push.
