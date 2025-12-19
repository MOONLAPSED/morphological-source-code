```md

MSC₁ — Morphological Source Code (with SQL)

SQL provides persistence

MSC provides interpretation

Reflexivity is simulated

This is the transitional form.

MSC₂ — MSC + QSD (no SQL)

No tables

No rows

No schema

State is:

in-memory

morphic

observer-relative

Persistence is:

snapshot

projection

compression

This is the native form.
              ┌──────────────────────┐
              │   BYTEWORD REGISTER   │
              └─────────┬────────────┘
                        │ broadcast
     ┌──────────────────┼──────────────────┐
     │                  │                  │
┌────▼────┐        ┌────▼────┐        ┌────▼────┐
│ Gauge 0 │        │ Gauge 1 │  ...   │ Gauge 7 │
│ (Black) │        │ (White) │        │ (Blue/C)│
└────┬────┘        └────┬────┘        └────┬────┘
     │ projection             projection
     └──────────────┬──────────────┬──────┘
                    ▼              ▼
              ┌──────────────────────────┐
              │   SPINOR / SQL BOUNDARY   │
              └──────────────────────────┘
```
