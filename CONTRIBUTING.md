# Contributing

N-Ways Addressing for Gabon welcomes corrections and proposals from communes, ministries, La Poste, mapping agencies, researchers, developers and residents. This page says what can change, how to propose it, and what never changes.

## What never changes

- **An issued code.** A code is never moved, renumbered or given to another compound, and a retired number is never given again (engine/SPEC.md §7). A proposal that would change an issued code is declined; the fix is a retirement, an alias or a new code.
- **The zones and their indices.** If the State redraws a département, codes keep their zone; only the place name shown beside them changes.
- **The one-issuer rule.** New codes come from one designated issuer only (see below).

## What you can propose

| Proposal | How it is decided |
|---|---|
| A wrong entrance, a missing compound, two homes under one code, a code where nobody lives | By evidence from the ground: residents' and visitors' confirmations settle it (GOVERNANCE.md, rule 4). Open an issue with the code and what is wrong. |
| An area's plate name (the short name in the code) | A commune may choose once for an area that carries a provisional name; any other rename follows engine/SPEC.md §2.4 and `tools/rename-areas.py`. Send the commune's decision with the areas it covers. |
| An official address (a street name or door number of a commune's plan) | Shown first, exactly as written, once its source is known. Send the source. |
| A source, a fact or a figure in the documents | Open a pull request against `docs/` or `SOURCES.md` with the source; every statement in the paper must be checkable. |
| Code: the engine, the server, the tools | Open a pull request with tests. A change to the engine must keep every conformance vector (`python3 engine/reference/test_ga.py`); a change to the server must keep its tests and the round trip (`python3 -m unittest discover -s server/tests -t .`). |
| A translation or a correction of the French | Pull request against `docs/paper.fr.md` or the French text of the other files. |

## How to send it

- **Issues and pull requests** on this repository (https://github.com/n-ways/open-addresses-gabon).
- **By email** to hello@nways.ng, for institutions that prefer a letter or cannot use GitHub. Write in French or English.
- For a security problem or personal data, do not open a public issue: see [SECURITY.md](SECURITY.md).

Contributions are accepted under the licences of the part they change (LICENSING.md): Apache 2.0 for code, ODbL 1.0 for data, CC BY 4.0 for documents. By sending one you confirm you have the right to license it so.

## The issuer rule

Codes are numbered from shared national ranges, one per name (engine/SPEC.md §2.4, §6.5). Two issuers working from the same registry would each see the same free number and give it to two homes. So:

- only the issuer designated by the State of Gabon or by N-WAYS LIMITED issues codes (today N-WAYS LIMITED);
- anyone may run the server in `server/` read-only, for look-ups, verification and spot codes, and it answers exactly as the published registry does;
- a deployment issues only once it has been designated in writing, and then N-Ways stops issuing for Gabon from the same day (server/README.md, "One issuer").

## Checks before a pull request

```sh
python3 engine/reference/test_ga.py                    # the engine and its vectors
python3 -m unittest discover -s server/tests -t .      # the server
python3 tools/vectors.py && git diff --exit-code engine/reference/vectors.json   # vectors unchanged
```
