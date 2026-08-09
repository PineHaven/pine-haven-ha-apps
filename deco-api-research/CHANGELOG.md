# Changelog

## 0.1.1

- Read Supervisor's root-only options file before entering the restricted
  `deco-research` runtime account.
- Fail closed if the process cannot permanently drop its startup privileges.
- Add regression tests for the privilege transition and startup ordering.

## 0.1.0

- Add disarmed-by-default Home Assistant App shell.
- Add the two-call read-only Deco connection smoke probe.
- Add redacted status/health ingress endpoints.
- Add source-level wire-operation and redaction tests.
- Require explicit acknowledgement of Deco's exclusive owner session.
- Limit the armed smoke test to one two-read cycle.
