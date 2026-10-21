# Scenario: cloud-identity-compromise-v1

Fictional cloud identity compromise, provider-neutral. Seven stages:

```text
S1 Initial access
S2 MFA manipulation
S3 Discovery
S4 Privilege escalation
S5 Persistence
S6 Sensitive access
S7 Data staging
```

Fixture files (scenario definition, stage weights, seeded event templates) are
implemented in the deterministic-slice phase. All identities, resources, and IP
addresses are fictional or from reserved documentation ranges
(192.0.2.0/24, 198.51.100.0/24, 203.0.113.0/24). Every generated event is
marked `synthetic: true`.
