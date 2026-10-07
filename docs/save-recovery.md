# Save recovery

The recovery module remains in `snekfeed/state.py`. Its interface is
`recover(path, now=None) -> Recovery` and `save(state, path, now=None) -> bool`.
The seam concentrates decoding, validation, file protection, persistence, and
offline recovery. This depth gives callers leverage through one startup call
and improves locality for recovery rules. Files are the test surface; no
additional adapter is needed. `load` remains a validated, read-only operation.

## Behavior

- Version 1 and unversioned saves are supported. Unknown fields are ignored;
  missing fields use defaults. Invalid known fields reject the whole save.
- Numbers are finite and nonnegative; counts are integers, excluding booleans.
  Level starts at one, tummy/mood obey their maxima, care obeys configured
  maxima, and XP is below the current level's requirement. Derived requirements,
  costs, income, and capped recovery totals must remain finite; there are no new
  economy caps. Existing skin eligibility and fallback remain in GameState.
- A malformed save is copied byte for byte into a uniquely named sibling
  `save.json.rejected-*.bak` before fresh progress may be saved. The original
  remains until the next successful save. Preservation failure disables saving
  for that session. Unsupported versions and read failures also disable saving
  without replacing the existing file. A missing save starts normally.
- Supported saves receive the existing capped offline credit, then an immediate
  checkpoint. The result reports full time away and earned hearts. Missing
  timestamps grant no credit; timestamp zero is valid; future timestamps grant
  no credit. Existing mood/tummy adjustments, frenzy clearing, and bowl cooldown
  behavior are preserved.
- Failed checkpoints retain recovered progress in memory and retry through
  ordinary saves. A restart before a successful checkpoint can recover the same
  disk interval again.
- Saving uses the existing `.tmp` write followed by replacement. Failed writes
  preserve the previous save and leave the timestamp unchanged by `save`.
  Offline recovery still advances its in-memory time cursor as before.
  Game reports save failure without aborting play, and always closes pygame on
  exit. Expected filesystem and data errors produce failure; programming errors
  are not broadly swallowed.

## Sequential integration with sibling work

Required `game.py` edits are confined to startup (`recover`, state, saving
permission, welcome result and warning), a shared `_save_progress` helper, and
replacing the save call at shed, autosave, and exit. Exit guarantees pygame
cleanup. Welcome thresholds and drawing remain owned by Game/UI. Apply these
edits sequentially alongside sibling changes rather than replacing whole Game
methods from another branch.

Feeding owns paid/queued/claimed/eaten snack semantics and capacity policy.
This change does not persist floor snacks or change those rules. If feeding
introduces persisted fields, their encoding and validation need explicit
integration here; new structured fields must not fall through numeric validation.
Shop interaction owns current skin eligibility and shed confirmation timing.
Recovery keeps using the existing GameState eligibility rule and does not add
another owner. The `time away` and `offline credit` additions to `GLOSSARY.md`
are limited to this candidate and need integration with sibling glossary edits.
