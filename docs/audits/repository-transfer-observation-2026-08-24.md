# Repository post-transfer observation, 2026-08-24

> Dated public-state observation. It records only the queried GitHub surfaces at the stated time and is not a general migration-completion or deletion certificate.

- identity: `criterion-loom post-transfer repository observation・8aff10d0-cc23-4842-b237-9ed1d732b6f0`
- subject_ref: `canonical repository object・51d473df-7d86-466d-a9f4-47a01ff70d44`
- observed_at: `2026-08-24T12:10:32+09:00`
- machine_record: [`../../migration/repository-transfer-observation-2026-08-24.json`](../../migration/repository-transfer-observation-2026-08-24.json)
- final_human_decision: `pending`

## Observed facts

| Query subject | Observation |
| --- | --- |
| `mait2355n/criterion-loom` | public repository, GitHub repository ID `1270877024`, default branch `main` |
| historical locator `morie-lene/criterion-loom` | resolved through the GitHub API to `mait2355n/criterion-loom`, repository ID `1270877024` |
| remote `main` | commit `83bdd6deb86aeaa3c99515c013a1d30984a719e1`, tree `b1e473a917ba3b81e0f6437db41330a128fe636e` |
| latest `main` CI for that commit | run [`32652456895`](https://github.com/mait2355n/criterion-loom/actions/runs/32652456895), completed with `success` |
| repository ID `1284490044` | authenticated API query returned HTTP 404 |

The 404 result means only that the authenticated query could not access that repository object. It does not distinguish deletion from private or otherwise inaccessible state and is not evidence that deletion occurred.

## Method

The observations were obtained with authenticated `gh api` and `gh run list` queries. The owner/name strings are mutable labels; repository ID `1270877024` is the identity authority for the preserved GitHub object. Historical URLs remain historical locators and are not rewritten as if earlier events occurred under the later label.

## Not verified

- complete preservation of branches, tags, pull requests, releases, Actions records and artifacts, permissions, or security settings against the pre-transfer baseline;
- deletion or continued existence of repository ID `1284490044`;
- continued integrity and availability of external backups;
- a publicly bound destructive-operation authorization;
- final human acceptance.

The earlier [repository-unification record](../repository-unification-2026-08-24.md) remains the `pre_transfer` plan and evidence record. This observation supplements it; it does not rewrite that earlier phase.
