## MarkDownLanguageProtocol_Server.py's directory

Yes, MDLPS, that's right.


```
┌─────────────────────────────────────────────┐
│  IDE (External Observer)                    │
│  - Sees: __enter__ starts                   │
│  - Sees: __exit__ completes                 │
│  - Does NOT see: bulk computation           │
└──────────────────┬──────────────────────────┘
                   │ (read-only, post-facto)
                   ▼
┌─────────────────────────────────────────────┐
│  RuntimeQuine (Parent)                      │
│  __enter__:                                 │
│    - Parse document                         │
│    - Step Turing tape                       │
│    - Accumulate fossils (RAM only)          │
│  __exit__:                                  │
│    - Spawn child with fossils               │
│    - Die (out of scope)                     │
└──────────────────┬──────────────────────────┘
                   │ (one-way, write-only)
                   ▼
┌─────────────────────────────────────────────┐
│  SQLWriter (Child)                          │
│  __init__(fossils):                         │
│    - Receive arguments from dead parent     │
│  commit(db):                                │
│    - Atomic SQL transaction                 │
│    - Fossils → byteword_artifact            │
│  (Then die, spawn grandchild if needed)     │
└─────────────────────────────────────────────┘
```

**The chain:**
```
Document → RuntimeQuine₀ → SQLWriter₀ → RuntimeQuine₁ → SQLWriter₁ → ...
