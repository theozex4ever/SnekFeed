# Shop interaction

The existing UI module provides the interaction seam through `click(pos, st)`
and `update(dt, mouse)`. Fixed Shed and skin hit geometry exists at construction;
drawing consumes it. Neither entering Shed nor changing unlocks requires a draw
before the next click. This gives the interface depth and callers leverage while
keeping geometry, eligibility checks, and confirmation timing in one place for
locality. There is no separate adapter.

`GameState.shed_gain()` and `GameState.unlocked_skins()` supply current economy
facts. UI does not calculate unlock rules or mutate economy state. Skin hit
testing filters all configured slots against current unlocks on each click.

## Confirmation and action results

- An eligible first Shed click arms confirmation for three update seconds and
  returns `("noop",)`. It is consumed silently by game routing.
- An eligible second click while armed consumes confirmation and returns
  `("shed",)`. Two clicks in one event batch can confirm without a rendered prompt.
- Expiry is based on accumulated `UI.update` time, preserving the main loop's
  capped delta and event-before-update ordering. Drawing never advances it.
- Every tab click cancels confirmation, including clicking the active tab. Skin,
  mute, and outside clicks do not cancel it.
- An unavailable Shed click returns `("deny",)` without arming or cancelling an
  existing window. Eligibility is checked again on each click.
- A currently unlocked skin returns `("skin", key)`. Locked skins and no hit return
  `None`. Welcome-card dismissal continues to consume its click with `("noop",)`.

Returned actions are executed synchronously against the same current state.
They are not stored authorizations: deferring them would require revisiting this
interface. Game routing assigns an accepted skin. `Feeding.shed()` (which wraps `GameState.shed()`) is the
authority for executing a shed; a zero gain causes denial without visual resets.

## Integration with sibling work

Required edits in `snekfeed/game.py` are limited to two areas:

1. `mouse_down` supplies `self.st` to `self.ui.click(pos, self.st)`.
2. `do_action` handles the `deny` result and treats `shed` as already confirmed.
   It no longer reads or writes UI confirmation. The shed itself runs through
   `Feeding.shed()`, which resets the economy and cancels outstanding snacks. Snek
   reset, effects, toast, sound, and the immediate save trigger stay in game routing.

The existing `self.ui.update(dt, self.mouse)` call advances confirmation time.
Keep its ordering relative to input when integrating the other candidates.

Feeding owns paid, queued, claimed, and eaten snack semantics and capacity policy.
This change retains existing snack actions and feeding-facing calls. If feeding
changes floor ownership, adapt the existing post-shed clearing operation to that
owner's reset interface during sequential integration; do not add a second rule.

Save recovery owns decoding, validation, persistence, timestamps, and offline
recovery. The confirmed-shed save trigger stays at its existing integration point;
consume any replacement persistence interface there when integrating that work.

`GLOSSARY.md` adds only **Shed confirmation**. Reconcile that addition with sibling
glossary changes during sequential integration. No sibling branches are merged
here.

## Verification

`tests/test_shop_interaction.py` exercises the caller interface without initializing
a display, including before-render clicks, expiry, tab cancellation, changing
unlocks after a draw, locked skins, and synchronous game routing. Drawing checks
use software surfaces and font initialization only. Economy tests continue to
exercise the pygame-free `GameState` module.
