# Security Policy

## Project status

Pokemon Card Wishlist is currently in active development.

The current milestone is `M1 — Repository foundation`. Discovery tooling and the Primal Clash vertical-slice fixtures are validated, but application, database, infrastructure, deployment, authentication, backup, and remote-access controls have not yet been implemented.

Security procedures will be expanded as infrastructure and application components are introduced.

## Supported versions

No public production release is currently supported.

| Version                      | Supported      |
| ---------------------------- | -------------- |
| Unreleased development state | Limited        |
| `v0.1.0`                     | Planned        |
| Earlier versions             | Not applicable |

Security support for release versions will be defined before the first public release.

## Reporting a vulnerability

Do not report suspected vulnerabilities in a public GitHub issue.

Use GitHub private vulnerability reporting when it is enabled for the repository.

If private reporting is not available, contact the project owner through a private channel listed on the project owner's GitHub profile.

Include the following information where possible:

* a clear description of the issue;
* the affected component or file;
* steps required to reproduce the issue;
* expected and actual behaviour;
* potential impact;
* relevant logs or screenshots with secrets removed;
* suggested mitigation, when known.

Do not include passwords, tokens, private keys, personal data, database contents, backup archives, or other sensitive material in the report.

## Response process

After receiving a security report, the project owner will:

1. acknowledge the report;
2. review whether the issue is reproducible;
3. assess the affected scope and potential impact;
4. identify temporary mitigation where practical;
5. prepare and validate a fix;
6. update relevant documentation;
7. publish a security advisory when appropriate.

Because this is currently a learning project maintained by one owner, no guaranteed response or remediation time is provided.

## Security scope

Relevant security areas include:

* accidental exposure of PostgreSQL;
* public exposure of NocoDB or administrative interfaces;
* weak or committed credentials;
* leaked environment files;
* insecure Docker or Docker Compose configuration;
* excessive container privileges;
* unsafe file permissions;
* insecure remote-access configuration;
* unprotected backup files;
* incomplete restore procedures;
* dependency vulnerabilities;
* unsafe handling of imported source data;
* cross-site scripting or formula-injection risks in imported or exported data;
* unauthorised modification of catalogue or wishlist data.

## Security baseline

The project follows these baseline requirements:

* PostgreSQL must not be exposed directly to the public internet.
* Application access should remain private during the MVP.
* Tailscale is the proposed remote-access method and must be validated before acceptance.
* Secrets must remain outside the repository.
* Strong, unique credentials must be used.
* Environment files containing secrets must not be committed.
* Containers should run with the minimum required privileges.
* Host and container software should be kept updated.
* Persistent data must use restricted file permissions.
* Database, image, and configuration backups must be protected.
* Backup restoration must be tested.
* Actual exposed ports and services must be documented.
* Imported data must not be treated as trusted application input without validation.

## Secrets and sensitive files

Do not commit:

* passwords;
* API tokens;
* private keys;
* authentication cookies;
* database connection strings containing credentials;
* Tailscale authentication keys;
* `.env` files containing secrets;
* database dumps containing private data;
* unencrypted backup archives;
* private certificates;
* local machine configuration containing personal information.

Use example files with placeholders where configuration documentation is required.

Example:

```text
POSTGRES_USER=replace_me
POSTGRES_PASSWORD=replace_me
POSTGRES_DB=pokemon_wishlist
```

Real values must be stored outside version control.

## Network exposure

The planned MVP deployment is private and self-hosted.

Expected network rules:

* PostgreSQL is reachable only by required local containers or trusted private hosts.
* NocoDB is not exposed through public router port forwarding.
* Remote access is provided through an approved private-access mechanism.
* Unnecessary ports remain closed.
* Administrative interfaces are not available anonymously.
* Network exposure is reviewed after each infrastructure change.

Public internet access for the MVP application is outside the approved scope.

## Dependency and container security

When dependencies or container images are added:

* use maintained versions;
* avoid unpinned floating versions where reproducibility matters;
* review release notes before major upgrades;
* remove unused packages and services;
* review known vulnerabilities where practical;
* document accepted risks;
* test upgrades before applying them to persistent production data.

Dependency updates must not be described as validated until the application and data workflow have been tested.

## Data and import security

Imported catalogue and marketplace files are external input.

Import processes should:

* validate expected structure and data types;
* reject malformed records explicitly;
* preserve raw source evidence;
* avoid executing imported content;
* avoid unsafe dynamic SQL;
* prevent CSV formula injection where exported values may begin with spreadsheet control characters;
* record rejected, unmatched, ambiguous, and duplicate-like records;
* avoid silently correcting unsupported values;
* produce validation evidence.

Raw files must not be assumed trustworthy merely because they come from a known source.

## Backup security

Backups must cover, where applicable:

* PostgreSQL data;
* card images;
* Docker and application configuration;
* required restore documentation.

A backup stored only on the same SSD as the active system does not protect against device or disk failure.

Backup files should:

* be stored in a separate location;
* be protected from unauthorised access;
* avoid exposing credentials;
* use encryption where appropriate;
* follow a documented retention policy;
* be tested through a restore procedure.

Backup and restore controls remain planned until they are implemented and validated during later milestones.

## Security limitations

The following controls are not yet implemented or validated:

* application authentication;
* role and permission configuration;
* final network exposure;
* container hardening;
* automated dependency scanning;
* automated secret scanning;
* database backup scheduling;
* backup encryption;
* restore testing;
* incident-response automation;
* production monitoring;
* public vulnerability reporting configuration.

These items must not be described as implemented until evidence exists.

## Disclosure

Please allow reasonable time for investigation and remediation before publicly disclosing a vulnerability.

Responsible reporting helps protect project data, infrastructure, and future users.
