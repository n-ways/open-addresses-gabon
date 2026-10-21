# Security and personal data

## Reporting a problem

Write to **hello@nways.ng** with "Security" or "Données personnelles" in the subject. Please do not open a public issue for:

- a weakness in the server (`server/`) or the engine that could let someone issue, change or retire codes without a key, read data that should not be served, or stop a deployment;
- personal data found anywhere in this repository (the registry holds places, never people: a name, a phone number or a household detail in it is a defect);
- a home whose publication puts someone at risk.

Say what you found, where (file, line, endpoint or code), and how to reproduce it. We acknowledge every report within three working days, tell you what we will do, and credit you when the fix is published unless you prefer otherwise. Please give us reasonable time to fix a problem before you make it public.

## What a deployment must do

- Keep issuing keys (`ISSUE_KEYS`) secret, one per office or system, long and random; never put them in the repository or in a URL. Revoke a key by removing it from the list and restarting.
- Serve the API only over TLS when it is reachable from outside the machine (server/README.md, "Behind a reverse proxy").
- Back up an issuing deployment's database every day; it is the only record of the codes it issued.
- Run read-only unless designated as the issuer (CONTRIBUTING.md, "The issuer rule").

## Personal data

The published registry carries no personal data: for each compound, its code, area, entrance point, spot code and building profile. The server stores, for each code it issues, a hash of the issuing key, never the key itself and never anything about the person who asked. Data protection in Gabon falls under Loi n° 001/2011 as amended by Loi n° 025/2023, overseen by the APDPVP (docs/existing-systems.md).
