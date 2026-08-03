# RDS Storage Shrink Automation

Automates safely resizing an over-provisioned AWS RDS PostgreSQL instance down to what it actually needs.

## The problem

RDS storage only scales in one direction: up. There's no built-in "shrink" operation. If an instance was over-provisioned — a bad initial estimate, a cleanup that freed up space, whatever — you're stuck paying for capacity you'll never use again unless you migrate to a new, right-sized instance.

This project automates that migration end-to-end: measure actual usage, spin up a smaller instance, sync the data over, swap identities, and retire the old one.

## How it works

```
sourcedbinfo
  → get_db_free_storage / evaluate_db_storage
  → create_new_db
  → check_rds_availability
  → allow_sgs
  → sync_dbs
  → revoke_sgs
  ── [manual verification checkpoint] ──
  → swap_db
  → stop_rds
```

1. **Measure** — pulls the source instance's config and recent CloudWatch `FreeStorageSpace` data to calculate actual usage, not a guess.
2. **Provision** — creates a new instance sized at ~1.2x actual usage (or a 20 GB floor), matching the original's engine, class, and network config.
3. **Wait & verify connectivity** — waits for the new instance to report `available`, then confirms Postgres itself is actually accepting connections (a status flag isn't proof of that).
4. **Temporary access** — opens a security group rule so the runner (EC2/ECS) can reach both databases, for the sync only.
5. **Sync** — uses [pgsync](https://github.com/ankane/pgsync) to copy all data from the old instance to the new one.
6. **Revoke access** — closes the temporary security group rule, whether or not the sync succeeded.
7. **Verification checkpoint (manual)** — prints row counts from both databases side by side and requires explicit confirmation (`yes`) before continuing. This is the last safe point to bail out — the next step renames the new instance to take over the original's identifier.
8. **Swap** — renames the old instance to `<name>-old` and the new instance to `<name>`, so it inherits the original's endpoint.
9. **Stop (not delete)** — stops the old instance as a rollback safety net, rather than deleting it outright.

## Requirements

- Python 3.9+
- [pgsync](https://github.com/ankane/pgsync) installed separately (Ruby gem — `gem install pgsync`), reachable on the runner's `PATH`
- AWS credentials with permissions for `rds:*` and `ec2:AuthorizeSecurityGroupIngress` / `RevokeSecurityGroupIngress` on the relevant resources
- Network path from the runner to both RDS instances on port 5432

Install Python dependencies:

```bash
pip install -r requirements.txt
```

## Configuration

Set the source database's master password as an environment variable before running:

```bash
export RDS_PASSWORD=your-master-password
```

The new instance is created with the same master username/password as the source.

## Usage

**Check the recommended size for a database, without making any changes:**

```bash
python main.py evaluate <db-name>
```

**Run the full migration:**

```bash
python main.py migrate <db-name> <table-name> <runner-security-group-id>
```

- `db-name` — identifier of the oversized source RDS instance
- `table-name` — table used for the row-count check at the verification checkpoint
- `runner-security-group-id` — security group ID of the machine running this script, so it can be temporarily granted DB access

You'll be prompted at the verification checkpoint to confirm row counts match before the script proceeds to the irreversible rename/swap step.

## Why not use AWS Blue/Green Deployments?

AWS's managed Blue/Green Deployments feature can also shrink storage, and is a reasonable choice if this is a recurring, multi-database need — it comes with a built-in testing window and safety net. This project takes the scoped-script route instead because:

- Blue/Green runs two full database copies side by side for as long as the deployment window stays open, which is designed for multi-day testing before switchover. This pipeline only keeps the second instance running for the duration of the sync itself.
- Blue/Green is a general-purpose upgrade tool (engine version bumps, parameter changes, replica topology) — more surface area than a one-off storage fix needs.