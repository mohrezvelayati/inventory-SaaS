# Operations Runbook

## Monitoring

- Render health path: `/api/v1/health/ready/`
- External uptime: hourly while the backend is free; every five minutes after
  upgrading. Alert only after two consecutive failures to tolerate deploys.
- Sentry: separate backend/frontend projects, `send_default_pii=false`, and no
  request bodies, tokens, OTPs, passwords, or full phone numbers.
- First checks for an incident: Render events, structured application logs,
  readiness, database status, deployed SHA, and Sentry regression list.

## Portfolio demo recovery

- The shared demo account is intentionally writable and may contain visitor
  changes until the next backend deploy/container restart.
- To rebuild it immediately, run
  `DEMO_MODE_ENABLED=true python manage.py seed_demo --reset` in the backend
  environment. The operation is atomic and targets only the internally marked
  demo tenant.
- One-click login does not depend on the public username or password, so a
  visitor profile edit cannot disable the demo entry button.

## Backup and restore

Do not treat a backup as valid until it has been restored.

1. Upgrade PostgreSQL before the free database expiry and confirm managed PITR.
2. Record the retention window and responsible owner.
3. For a manual encrypted export, obtain the external URL without copying it to
   shell history, run `pg_dump --format=custom`, encrypt the result, and store it
   outside Render with restricted access.
4. Restore into a temporary PostgreSQL database with `pg_restore --clean
   --if-exists`, run migrations, and execute the smoke checklist against it.
5. Record date, duration, row-count sanity checks, operator, and deletion of the
   temporary database. Never restore over production for a drill.

## Rollback

1. Stop new releases and capture the failing deploy SHA and logs.
2. If code-only, roll back both the Render web service and Static Site to their
   previous known-good SHAs, then rerun health and smoke checks.
3. Database migrations must use expand/contract changes. Do not reverse a
   destructive migration during an incident without a verified backup.
4. If data is corrupt, place the service in maintenance mode, restore to a new
   database, verify it, then switch `DATABASE_URL` and rotate the old credential.
5. Re-enable auto-deploy only after the fix is merged and CI passes.

## Secret rotation

- Rotate immediately after suspected exposure and on ownership changes.
- `SECRET_KEY` rotation invalidates signed Django data and JWTs; schedule it and
  notify users that they must sign in again.
- Rotate database, Sentry, and Kavenegar credentials independently; update the
  relevant Render environment variables, redeploy, verify, then revoke the old
  value.
- Never paste secret values into issues, commits, screenshots, or logs.

## Incident response

1. Classify impact: availability, authentication, tenant isolation, inventory,
   or data integrity.
2. For suspected cross-tenant exposure or stock corruption, disable writes or
   enable maintenance mode immediately and preserve logs.
3. Roll back only code-safe failures; restore data only from a verified backup.
4. After recovery, document timeline, affected stores, root cause, corrective
   tests, and follow-up owner without including customer PII.
