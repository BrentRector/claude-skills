---
type: regex
target: last_message
pattern: '<TargetFrameworks>|<TargetFramework>[^<]*(netstandard|net4)'
match: not_contains
---
