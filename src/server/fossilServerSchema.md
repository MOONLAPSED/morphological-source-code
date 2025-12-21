# Fossil morphogen ISA draft-work
# © 2025 Moonlapsed https://github.com/MOONLAPSED/Cognosis | CC ND && BSD-3 | SEE LICENCE
| Fossil ISA | Typical CLI           | BW² Detritus Form                     | Turing Analogy                                    |
| ---------- | --------------------- | ------------------------------------- | ------------------------------------------------- |
| OPEN       | `fossil open`         | `[ByteWord_repo, ByteWord_workspace]` | Init tape cursor                                  |
| CLOSE      | `fossil close`        | `[BW_substrate, BW_null]`             | Tape detach / noop                                |
| INIT       | `fossil init`         | `[BW_new_repo, BW_meta]`              | Tape genesis, PC=0                                |
| DESCRIBE   | `fossil info`         | `[BW_ID, BW_hash]`                    | Read-only fetch (memory query)                    |
| COMMIT     | `fossil commit`       | `[BW_delta, BW_authority]`            | Collapse → store on tape                          |
| AMEND      | `fossil amend`        | `[BW_last_commit, BW_delta]`          | GOTO local PC → rewrite                           |
| BRANCH     | `fossil branch`       | `[BW_tip, BW_name]`                   | Fork tape branch (PC split)                       |
| MERGE      | `fossil merge`        | `[BW_head1, BW_head2]`                | Deterministic merge → new PC                      |
| TIMELINE   | `fossil timeline`     | `[BW_cursor, BW_bounds]`              | Enumerate reachable tape cells                    |
| UPDATE     | `fossil update`       | `[BW_commit, BW_registers]`           | Load commit → registers (rehydration)             |
| REVERT     | `fossil revert`       | `[BW_prev_commit, BW_registers]`      | Undo → backward jump (GOTO analog)                |
| CLEAN      | `fossil clean`        | `[BW_workspace, BW_flags]`            | Reset tape → zero state                           |
| SCRUB      | `fossil scrub`        | `[BW_garbage, BW_metadata]`           | GC unreachable detritus (erase paths)             |
| SNAPSHOT   | `fossil snapshot`     | `[BW_marker, BW_meta]`                | Marker → read-only tape label                     |
| TAG        | `fossil tag`          | `[BW_commit, BW_label]`               | Annotate cell in tape                             |
| COMMENT    | `fossil comment`      | `[BW_commit, BW_string]`              | Optional tape metadata                            |
| ANNOTATE   | `fossil annotate`     | `[BW_commit, BW_struct]`              | Typed metadata for boundary registers             |
| PROVENANCE | `fossil provenance`   | `[BW_cursor, BW_ancestry]`            | Trace tape dependency graph                       |
| USER       | `fossil user`         | `[BW_action, BW_identity]`            | Inject agent identity into PC                     |
| CAPABILITY | `fossil capabilities` | `[BW_action, BW_constraints]`         | Set boundary constraints (like conditional jumps) |
| VERIFY     | `fossil verify`       | `[BW_commit, BW_checksum]`            | Assert tape invariant                             |
| POLICY     | `fossil policy`       | `[BW_commit, BW_rules]`               | Guard tape region → conditional branch            |
| READ       | `fossil cat`          | `[BW_commit, BW_register]`            | Load instruction / ByteWord into PC               |
| WRITE      | `fossil push`         | `[BW_register, BW_commit]`            | Store instruction → tape                          |
| NOOP       | `NOP`                 | `[BW_null, BW_null]`                  | Explicit no-op / align PC                         |


Turing/GOTO semantics

PC (program counter) = current Fossil branch + detritus cursor.

Jumps / GOTO = UPDATE, REVERT, MERGE → modify PC explicitly.

Registers = BW²:

First ByteWord = “working value”

Second ByteWord = “inner product / relational state”

This gives all 25 ops meaning in a boundary TM:

Every commit → tape cell written

Every update → PC rehydrated

Every merge / branch → conditional GOTO / fork

SCRUB / CLEAN → tape erasure / reset

Annotation ops → metadata on tape (type-level, no runtime side effect)

Effectively:
```
tape[cell] = BW²(detritus)
PC = timeline pointer
instruction(tape[cell]) = Fossil ISA op
execute → rehydrate + possibly branch / erase / annotate
```
BW² ensures reversible semantics: XOR inner product / ByteWord composition means you can “uncommit” locally if you preserve prior BW² snapshot.

Example “Detritus Program”:
```
[0] COMMIT(BW_delta1, BW_author1)
[1] UPDATE(BW_commit0, BW_registers)
[2] MERGE(BW_branchA, BW_branchB)
[3] SCRUB(BW_garbage, BW_meta)
[4] REVERT(BW_commit0, BW_registers)
[5] TAG(BW_commit2, BW_label)
[6] NOOP
[7] WRITE(BW_reg0, BW_commit3)
...
```
Linear, but semantically rich:

line numbers = temporal markers (GOTO analogs)

BW² = registers / relational state → allows local computation / morphic evolution

detritus doubles as boundary memory / program / ephemerality layer
