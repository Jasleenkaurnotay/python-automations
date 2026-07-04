# IAM Access Key Rotation (Lambda)

A scheduled AWS Lambda function that finds IAM access keys older than a
configurable threshold, rotates them, and stores the new credentials in
AWS Secrets Manager — with the old key deleted only after the new one is
safely stored.

## Why this exists

Long-lived IAM access keys are one of the most common findings in any AWS
security review. Manual rotation doesn't scale past a handful of users and
is easy to forget. This script automates rotation on a schedule (e.g. via
EventBridge) so no access key in the account outlives the configured
threshold.

## How it works

```
get_users()
    → get_access_keys(users)          # age of every key, per user
        → new_access_key(key_tuple)   # create replacement keys for expired ones
            → store_aws_credentials() # persist new keys to Secrets Manager
                → delete_key()        # only runs if storing succeeded
```

**Core design principle: never delete before the replacement is safely
stored.** The happy path is create → store → delete, specifically so a
failure partway through never leaves a user with zero working credentials.

### Handling AWS's 2-key limit

IAM caps every user at 2 access keys. If a user is already at the cap, the
"create new key" step fails before an old key has ever been touched. This
script handles that case as a fallback, not the default path:

1. Try to create the new key first (the safe order, for the common case).
2. If IAM raises `LimitExceededException`, delete the old key **and only
   then** retry creating the new one.

The riskier delete-before-create order only ever runs for the rare user
who's already maxed out — not for every user, every run.

### Handling repeat runs (Secrets Manager collisions)

`create_secret` fails if a secret with that name already exists — which
it will, on every run after the first, for every user. The fix: try
`describe_secret` first; if the secret exists, update it with
`put_secret_value`; if it doesn't (`ResourceNotFoundException`), create it.

## Configuration

| Env var       | Default | Purpose                                   |
|---------------|---------|--------------------------------------------|
| `EXPIRY_DAYS` | `2`     | Age (in days) after which a key is rotated |

Secrets are stored under the name `rotated_key_pair_<username>` in
Secrets Manager (region hardcoded to `us-east-1` — update if deploying
elsewhere).

## Required IAM permissions (for the Lambda's execution role)

- `iam:ListUsers`
- `iam:ListAccessKeys`
- `iam:CreateAccessKey`
- `iam:DeleteAccessKey`
- `secretsmanager:DescribeSecret`
- `secretsmanager:CreateSecret`
- `secretsmanager:PutSecretValue`

## Known limitations / not yet handled

These are understood gaps, not oversights — flagged here deliberately
rather than fixed yet:

- **No pagination.** `list_users()` and `list_access_keys()` only read the
  first page of results. Fine for small accounts; will silently miss
  users/keys once an account grows past the default page size.
- **Harmless duplicate-delete log noise.** When the 2-key-limit fallback
  runs, the old key gets deleted inside `new_access_key()`. The later
  `delete_key()` call still tries to delete that same (already-gone) key
  from its original list, fails with `NoSuchEntityException`, and logs an
  error. It's caught and non-fatal — just a false alarm in the logs, not a
  functional break.
- **No dry-run mode or per-user exclusion list.** Every IAM user in the
  account is in scope. There's no way yet to exempt break-glass or
  service accounts, or to preview what would happen before it runs live.
- **No notification on rotation.** Users whose local CLI/SDK configs
  reference the old key aren't told their credentials changed.

## Testing notes

Tested against:
- A user with no existing secret (create path)
- A user with an existing secret from a prior run (update path)
- A user already at the 2-access-key limit (delete-then-create fallback)

---

*Part of [python-automations](https://github.com/Jasleenkaurnotay/python-automations) —
a growing collection of small, real DevOps automation scripts, built and
reviewed one bug at a time.*