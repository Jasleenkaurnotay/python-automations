# python-automations

A growing collection of small, real DevOps automation scripts — each one
built hands-on, then hardened through a proper code review pass (bugs
found, tradeoffs made deliberately, and gaps documented rather than
hidden).

Every folder below is a self-contained exercise with its own README
covering what it does, why it's built the way it is, and what's
intentionally left as a known limitation.

## Projects

| Folder | What it does |
|---|---|
| [`iam-key-rotation/`](./iam-key-rotation) | Lambda function that rotates IAM access keys older than a configurable threshold, storing new credentials in Secrets Manager before deleting the old key. |
| [`invoke-lambda-with-s3-upload/`](./invoke-lambda-with-s3-upload) | 🚧 In progress — Lambda triggered by an S3 upload event. |

## Why this repo exists

Most "automation script" repos show only the finished, working version.
This one tracks something slightly different: the process of finding the
edge cases a first draft misses (race conditions, API limits, retries on
partial failure) and making an explicit call on what to fix now versus
what to leave as a documented follow-up. Each project README reflects
that — including a "known limitations" section that's honest about
what's not handled yet.

## Structure

Each exercise lives in its own folder:

```
python-automations/
├── iam-key-rotation/
│   ├── iam_key_rotation.py
│   └── README.md
├── invoke-lambda-with-s3-upload/
│   └── README.md
└── README.md   ← you are here
```

New exercises get added the same way: a new folder, its own script(s),
and its own README following the same format.