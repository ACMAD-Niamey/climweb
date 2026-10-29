# Access and Secrets Management

This guide governs institutional ownership, least privilege, secure transfer, rotation, and offboarding. It never records
secret values.

## Systems in scope

- GitHub organization, repository, Actions environments, deploy keys, and branch protection;
- production hosting and SSH;
- domain registrar, DNS, and TLS/certbot host access;
- Wagtail superusers, groups, editors, reviewers, and staff accounts;
- database, backup storage, public media, RCC data, private exports, and staff reports;
- SMTP/Mailgun, newsletter, reCAPTCHA, analytics, and monitoring;
- Google Cloud/Workspace service accounts, Calendar/Meet, and Shared Drive;
- ACMAD/SGBD/THREDDS or other protected source services.

## Register fields

For each system record institutional owner, technical custodian, approved access level, successor, MFA status, recovery
contacts, billing/renewal owner, secret storage location, last access review, last rotation, and offboarding result.

Store this metadata in the handover register. Store the actual credential only in the approved secret manager or direct
transfer channel.

## Provisioning

1. Use a named institutional account where the service supports it.
2. Grant the minimum role required.
3. Require MFA for privileged human access.
4. Use separate service accounts for machine integrations.
5. Restrict keys by environment and purpose.
6. Record approval, owner, issue date, rotation date, and recovery process.
7. Test access without copying secrets into documentation or chat.

## Repository and environment rules

- Never commit `.env`, service-account JSON, SSH private keys, TLS private keys, database dumps, access tokens, or exported
  personal data.
- Use `.env.sample` for names and safe examples only.
- Mount secret files read-only and outside public/static/media paths.
- Avoid commands that print fully resolved Compose environments into shared logs.
- Treat Git history as permanent; deleting a current file does not remove an exposed secret from history.

If a secret is exposed, revoke/rotate first, then investigate and clean history through an approved incident process.

## Rotation

For each rotation:

1. Create the replacement under the correct institutional owner.
2. Deploy it through the approved secret channel.
3. Recreate/reload only affected services.
4. Run the integration health and acceptance tests.
5. Revoke the old credential.
6. Review logs for failed or unauthorized use.
7. Record completion and next rotation date.

Avoid simultaneous rotation of unrelated integrations unless a coordinated incident requires it.

## Offboarding

On role change or departure:

- remove personal access and sessions;
- transfer institutional ownership/recovery/billing contacts;
- rotate credentials the person could copy;
- remove GitHub, SSH, CMS, DNS, Google, email, backup, and monitoring access as applicable;
- preserve audit records;
- verify service accounts and automation continue to work;
- record approver and completion date.

Staff workspace offboarding and platform-account disabling are separate controls; use the Staff Workspace guide.

## Quarterly access review

- Reconcile active people with approved roles.
- Review superusers, repository admins, deploy keys, SSH keys, service accounts, and recovery contacts.
- Confirm branch/environment protections.
- Test emergency access without revealing credentials.
- Verify secret files are excluded from Git and backups have equivalent restrictions.
- Close orphaned accounts and record exceptions with owners/dates.
