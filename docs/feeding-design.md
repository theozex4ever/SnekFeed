# Feeding design

Scope: deepen feeding in the checkout based on local main
`b0d1ac8c9b7b27a7909eb2d4c4340bc3e8a616e1`. Gameplay policy and ownership
and interface below were accepted during the design discussion. Shared
understanding was confirmed before implementation was authorized.

## Accepted choices

- All outstanding snacks reserve their fill, including claimed snacks. A
  reservation ends at meal credit or cancellation.
- Manual admission keeps the existing soft tummy limit: current tummy plus
  existing reservations must be below 100; the proposed snack's fill need not
  fit completely. Meal credit clamps tummy fill and grants full growth, mood,
  and eaten-snack count.
- The manual limit remains eight outstanding snacks, including falling,
  waiting, and claimed snacks.
- A butterfly feast always delivers three free best-unlocked snacks, bypassing
  both admission limits. Those snacks count toward reservations and outstanding
  snack count once delivered.
- A successful shed cancels every outstanding snack without refund or meal
  credit. No completion from the previous run may credit the new run. Preserve
  GameState's existing reset and retained cumulative counters.
- Auto Bowl waits until there are no outstanding snacks, including claimed
  snacks. Preserve its peckish threshold, best unlocked choice, half-hearts
  spending limit, and cooldown. Serving coordinates payment, creation, and
  cooldown inside feeding.
- Preserve current meal-start behavior: an awake Snek can start eating at full
  tummy; a sleeping Snek with full tummy leaves snacks waiting. Do not add a
  hard meal-start gate.
- Feeding owns authoritative claiming, chewing progress, the half-second meal
  duration, completion, and meal credit. Snek retains nearest-snack selection,
  movement, and drawing, and requests a claim when it reaches a snack.

## Selected interface

A concrete pygame-free Feeding module takes the existing GameState directly.
It uses named operations rather than a generic command interface or a separate
operation for each frame phase:

```python
Feeding(state)
feeding.eligibility(key)
feeding.buy(key)
feeding.feast()
feeding.claim(snack_id)
feeding.advance(dt, landed_ids=())
feeding.shed()
feeding.snacks
```

- `eligibility` returns the current manual admission decision and its denial
  reason: outstanding cap, locked snack, tummy full, or insufficient hearts.
  It is read-only. `buy` rechecks admission when invoked, then charges and
  creates an outstanding snack together. Its result identifies the new snack
  or the denial. Admission checks retain the existing floor-cap-first behavior.
- `feast` creates the three free snacks and exposes them in current observations.
  Game does not choose their number or snack kind.
- `claim` returns whether it accepted a waiting snack. Only one snack may be
  claimed at a time. Successful claiming starts elapsed chewing time at zero;
  it neither credits the meal nor releases its reservation.
- `advance` accepts landing observations, checks Auto Bowl, and advances the
  existing claimed snack. It returns already-applied meal credits with snack
  identity, snack kind, and levels gained for presentation. A meal is credited
  once after half a second; bite progress retains the existing 0.45-second
  animation progression. Callers never report meal completion.
- `shed` delegates to GameState.shed and cancels outstanding snacks only when
  the economy reset succeeds. It returns the existing scale gain. Confirmation
  timing remains owned by shop interaction.
- `snacks` exposes immutable observations of outstanding snacks: identity,
  snack kind, serving source, feast ordinal, lifecycle phase, and chewing
  progress. It does not expose mutation authority.

This interface provides depth by hiding payment, reservation, capacity,
claiming, timing, meal credit, Auto Bowl suppression, and cancellation behind
one seam. Callers gain leverage from named operations; lifecycle policy gains
locality. No new adapter or presentation module is justified.

## Presentation and observation contract

- Allocate stable snack identities that are never reused within a Feeding
  instance, including after shed. Retain that instance across sheds.
- Repeated or stale landing reports have no effect. Claims for absent snacks,
  invalid phases, or while another snack is claimed return False without effects.
- Unknown snack kinds and negative or nonfinite elapsed time are programmer
  errors, rejected before mutation.
- Game retains existing Food presentation objects keyed by snack identity.
  Their membership follows feeding observations; their positions and fall
  motion remain presentation state. Bite appearance derives from feeding
  observations rather than independent lifecycle decisions; the old Food.taken
  flag is removed.
- Create presentation objects when new identities appear, choosing placement
  once. Preserve existing manual random placement at height 180, bowl-relative
  placement at height 60, and feast random placement at heights 200, 260, 320.
- Present meal credits using the matching Food position before removing its
  presentation object. Reconcile against current observations to add new
  objects, update appearance, and remove absent identities.
- Snek retains nearest waiting-snack selection, movement, and sleep behavior.
  It requests a claim when reaching a snack and observes authoritative chewing
  progress. Remove its independent completion timer and completed-food return.
  On observing its meal complete, it returns to idle without further movement
  that frame, preserving its existing eating branch behavior.

## Frame ordering

1. GameState.tick advances the existing economy, digestion, mood, and cooldown.
2. Existing Food physics advances and reports landings.
3. Feeding.advance accepts landings, checks Auto Bowl, then advances the
   already-claimed meal and applies completion credit.
4. Game presents meal credits and reconciles Food presentations. Snek updates
   movement and may claim a waiting snack.

A new claim receives no elapsed time from the frame before its claim. Auto Bowl
can refill on the frame after the final meal completes. A newly served bowl
snack receives no retroactive physics update. Feeding hides bowl-versus-credit
ordering; callers keep economy, physics, feeding, and movement in this sequence.

## Integration constraints

- GameState remains the real in-process economy dependency. Preserve its
  pygame-free behavior and useful depth; no new adapter is justified here.
- Shop interaction owns hit geometry, current skin eligibility, and shed
  confirmation timing. It consumes feeding eligibility instead of duplicating
  reservation or capacity policy.
- Save recovery owns decoding, validation, persistence, timestamps, and offline
  recovery. Feeding must not extend the save format or move those rules.
- Outstanding snacks currently exist only during a running session. No change
  to that persistence behavior is proposed.
- Sibling worktrees may also edit game.py. Integration is sequential after
  settled design and review; no sibling merges or PR publication are authorized.
- GLOSSARY.md additions in this checkout describe feeding only and must be
  reconciled with sibling glossary additions during integration.

## Required game.py edits

- Construction: establish feeding ownership of outstanding snacks rather than
  storing lifecycle state only in Game.foods.
- Snack actions: replace floor checks, purchase, pending-fill computation, and
  separate drop with a feeding operation and presentation of its outcome.
- Feast reward: offer the three snacks through feeding; keep butterfly reward
  selection and visual placement outside the feeding policy.
- Update: report landings to feeding.advance, present meal credits, reconcile
  Food objects, and let Snek request claims. Keep food physics and Snek movement
  outside feeding.
- Meal feedback: consume completed meal results without calling GameState.eat
  again; retain swallow, crumbs, hearts, growth feedback, and level notices.
- Shed: route the confirmed action through feeding.shed so successful economy
  reset and feeding cancellation are coordinated; retain shop confirmation
  ownership, Snek reset, effects, and existing persistence calls.
- Draw: read feeding eligibility for snack rows and use presentation objects for
  food drawing. Remove Game.pending_fill once no caller needs it.

## Test surface

The interface will be the test surface for purchases through meal credit,
purchases while chewing, Auto Bowl while food waits or is claimed, feast
capacity policy, and shedding mid-meal. Existing independent economy behavior
also remains covered.

Include denial without payment, reservations during chewing, exactly-once meal
credit, clamped fill with full growth, blocked bowl serving while any snack is
outstanding, next-frame refill, feast exceptions and subsequent reservations,
successful shed mid-meal, rejected shed preserving meals, and stale observations
after shed. Use the real GameState and the same feeding interface as callers;
no pygame simulation or test-only lifecycle operations are required.

## Implementation status

All design questions Q1–Q10 were accepted using the recommended answers, and
the complete shared understanding was confirmed. The feeding module and its
Game, Snek, and UI integration implement this design. Integration with sibling
branches remains sequential and separate from this implementation.

## Validation and review

- `python -m pytest -q`: all 37 tests pass, including 20 feeding tests through
  the selected interface and the existing economy tests.
- `python -m mypy snekfeed/feeding.py --follow-imports=silent`: passes.
  Wider checking of feeding, Game, Snek, and UI reports eight existing errors,
  compared with eleven in the base's Game, Snek, and UI. No new errors were
  introduced; unrelated existing typing problems remain outside this change.
- Headless pygame checks exercised purchase through actual landing, movement,
  chewing, meal credit, and drawing; feast placement and rendering; confirmed
  shed during chewing with no late credit; Auto Bowl placement with no
  retroactive physics; and all four UI tabs.
- Feeding also imports and runs with site packages disabled, confirming that
  its real GameState dependency needs no pygame adapter.
- Separate Standards and Spec reviews of the staged change against the fixed
  base reported no findings on either axis.
