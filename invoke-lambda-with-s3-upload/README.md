# invoke-lambda-with-s3-upload

An event-driven CSV ingestion pipeline on AWS: a file lands in S3, that triggers a
Lambda function, and the Lambda parses the file and writes structured rows into a
PostgreSQL database on RDS — with the database credential fetched at runtime from
Secrets Manager rather than stored as plaintext.

All infrastructure (VPC, subnets, RDS, S3, Lambda, IAM, Secrets Manager) is written
from scratch in modular Terraform, and all the automation around it — building a
Lambda layer for a native Python dependency, wiring runtime secret retrieval, and
end-to-end testing — is custom Python/bash. The CSV parsing and row-insert logic
were provided as fixed application code; everything else here — the infra design,
the module boundaries, the layer build process, and the Secrets Manager integration
— was built independently.

## What it does

1. A CSV file is uploaded to an S3 bucket.
2. The upload triggers a Lambda function via an S3 event notification.
3. Lambda downloads the file, parses it (`parser.py`), and writes the rows into a
   Postgres table on RDS (`db.py`), using `db.py`'s `get_db_config()` /
   `insert_transactions()` helpers.
4. The DB password is never stored as a plain environment variable — Lambda fetches
   it at runtime from AWS Secrets Manager (`get_db_password()` in `db.py`, with
   in-memory caching across warm invocations).

## Repo structure

```
infra/                   # Terraform — fully written, applied, and verified
├── main.tf               # root module — wires network, rds, s3, lambda, secrets
├── variables.tf
├── outputs.tf
├── providers.tf
├── terraform.tfvars      # not committed — see terraform.tfvars.example
└── modules/
    ├── network/           # VPC, 2 private subnets, route table, S3 Gateway endpoint
    ├── rds/                # SG, DB subnet group, RDS Postgres instance
    ├── s3/                 # data bucket + notification config
    ├── lambda/             # SG, IAM role/policies, function, layer attachment
    └── secrets/            # Secrets Manager secret storing the DB password (JSON blob)

scripts/
└── build_layer.sh        # builds the psycopg2 Lambda layer via Docker
                            # (public.ecr.aws/sam/build-python3.13 — NOT the runtime image)

src/
├── lambda_function.py    # entry point — lambda_handler(event, context)
├── parser.py              # CSV validation/parsing
├── db.py                  # DB config, connection, schema, insert logic,
                            # + get_db_password() (Secrets Manager fetch/cache)
└── test.py                # throwaway local script used to inspect the real
                            # get_secret_value() response shape before finishing
                            # get_db_password() — not part of the deployed pipeline
```

## Design decisions

- **No NAT gateway.** Private subnets rely on a free **S3 Gateway endpoint** for
  Lambda to reach S3, avoiding the ongoing per-hour cost of a NAT gateway for a
  workload that (mostly) only needs to reach S3.
- **Secrets Manager stores a JSON blob**, not a raw string
  (`{"password": "..."}`), so the same secret can hold additional related values
  (e.g. username) later without changing its shape or the code that reads it.
- **Runtime secret fetch, not a plaintext env var.** Terraform provisions the
  secret and grants the Lambda role `secretsmanager:GetSecretValue` on it
  specifically (least-privilege, scoped to one ARN); `db.py` fetches and caches
  the password in memory on first use per warm Lambda instance, rather than
  re-fetching on every invocation.
- **Lambda layer built for the target platform, not the dev machine.**
  `psycopg2-binary` includes a compiled C extension, so it's built inside a Docker
  container matching Lambda's actual runtime OS/architecture — building it locally
  (especially on Apple Silicon) produces binaries Lambda can't load.
- **Modular Terraform** — network, rds, s3, lambda, and secrets are separate
  modules with explicit outputs/inputs; cross-module resources (the RDS↔Lambda
  security group rule, the S3→Lambda trigger) live in the root module, which is
  where cross-cutting dependencies belong.

## Setup

1. Build the Lambda layer:
   ```bash
   ./scripts/build_layer.sh
   ```
   Produces `scripts/lambda-layer/layer.zip`.

2. Package the function code (from repo root):
   ```bash
   zip -j lambda_function.zip src/lambda_function.py src/parser.py src/db.py
   ```

3. Copy `infra/terraform.tfvars.example` to `infra/terraform.tfvars` and fill in
   real values (VPC CIDR, DB credentials, project name, path to
   `lambda_function.zip`, etc.).

4. Deploy:
   ```bash
   cd infra
   terraform init
   terraform validate
   terraform plan
   terraform apply
   ```

## Testing

Upload a CSV matching the required columns to the S3 bucket:

```
transaction_id,transaction_date,vendor_name,amount,currency,category,description,status
```

(`transaction_id`, `transaction_date`, `vendor_name`, `amount`, `status` are required;
`transaction_date` must be `YYYY-MM-DD`; `amount` must parse as a number.)

Then check:
- **CloudWatch Logs** (`/aws/lambda/<project_name>-lambda`) for execution output
- **RDS** — the `vendor_transactions` table for inserted rows