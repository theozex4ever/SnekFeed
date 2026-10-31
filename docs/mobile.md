# Mobile (Android)

The phone build runs the same game code through python-for-android (see
`buildozer.spec`). `snekfeed/device.py` is the only place that knows where the
game runs; other modules ask it questions rather than checking the platform.

## Display

The layout stays a fixed 1120x720 landscape canvas. On Android it opens with
`SCALED | FULLSCREEN`, so SDL scales the canvas to the screen with letterboxing
and maps touch positions back onto the canvas. Hit geometry is unchanged.
Orientation is locked to either landscape direction. Touch builds give text a
`MIN_TOUCH_TEXT` floor, and the mute button accepts a finger-sized hit area.
Android has no fontconfig, so it uses pygame's bundled font.

## Input

SDL turns the first finger into left-button mouse events, so tapping and
stroking reuse the mouse path. A lifted finger is not hovering: touch release
clears the pointer, so rows don't stay lifted and Snek stops watching the spot.
Prompts say "Tap" instead of "Click". The back button (`AC_BACK`) behaves like
`Esc`: it closes the welcome-back card if one is open, otherwise it saves and quits.
`SNEKFEED_TOUCH=1` previews touch wording and pointer behaviour on a desktop.
Targeting API 36 would route back through predictive back, which SDL2 never
sees, so the manifest opts out with `android:enableOnBackInvokedCallback="false"`
(`tools/android/manifest_application_arguments.xml`).

## Background

Android may kill a backgrounded app without warning, and SDL blocks the main
loop while the app is in the background. The game therefore saves on entering
the background and stops updating and drawing. On return it credits the
background interval with the ordinary offline rule (`GameState.credit_away`:
50%, capped at 8 hours, mood and tummy adjusted, frenzy cleared), shows or adds
to the welcome-back card using the startup thresholds, and checkpoints. Credit
is measured from the wall-clock moment of backgrounding, not from the last
save, so a failed or disabled save cannot inflate it. If the process dies in the
background, the next launch recovers from the background save as usual.
Repeated background or foreground events are ignored until the state changes.

If Android dropped the GL context while backgrounded, SDL reports
`RENDER_DEVICE_RESET`; the game calls `set_mode` again, which rebuilds pygame's
scaled renderer and texture. Game state and cached software surfaces survive.
Once a quit or termination arrives, later events in the batch are ignored (SDL
can queue a foreground event behind the quit) and the loop exits through the
saving path without another frame. If the app is still suspended then, the
exit credits the background interval before saving, because that save moves
the save cursor to the moment of exit.

## Signing

Android only installs an update signed with the same key as the installed
app, and uninstalling deletes the save. CI therefore signs every debug APK
with one keystore from the `ANDROID_DEBUG_KEYSTORE_BASE64` secret and refuses
to build without it.

Saves live in app-private storage: `$ANDROID_PRIVATE/snekfeed/save.json`.
