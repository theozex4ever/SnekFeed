# Phone play-testing

## Stream the desktop game

The normal Python/pygame game can run on a computer in its own 1120×720 virtual
display and stream to a phone through TigerVNC, websockify and noVNC. This uses
the existing game loop without gameplay changes. noVNC
[supports mobile browsers and touch gestures](https://github.com/novnc/noVNC).
The phone does not need Python or an APK.

Server provisioning is machine-local and is not included in this repository.
To configure a stream:

1. Connect the host computer and phone to the same Tailscale network.
2. Run TigerVNC on a separate virtual display with a 1120×720 canvas, keeping
   its VNC listener on loopback. Share this display rather than the host desktop.
3. Launch the game on that display. Set `SDL_VIDEODRIVER=x11` and `DISPLAY` to
   the virtual display so SDL does not select the host's Wayland session.
4. Serve noVNC with websockify, proxying to the loopback VNC listener. Bind the
   browser listener to the host's Tailscale address, or use
   [Tailscale Serve](https://tailscale.com/docs/reference/tailscale-cli/serve)
   for private HTTPS access.
5. Open the noVNC URL on the phone. For example, replace `HOST_TAILSCALE_IP` and
   `PORT` in this template with the local server configuration:

```text
http://HOST_TAILSCALE_IP:PORT/vnc.html?autoconnect=1&resize=scale&reconnect=1
```

Turn the phone sideways. Tap to click; hold briefly before dragging to emulate
holding the mouse button when stroking Snek. The noVNC sidebar includes fullscreen
and a keyboard. If the picture does not fit, select **Settings → Scaling mode →
Local scaling**. Reopening the link reconnects to the same running game.

## What this tests

Use this for the normal game's economy, interactions and layout. Rendering and
simulation run on the computer, so network delay affects responsiveness. A basic
noVNC stream does not carry music or sound effects and cannot measure native
phone performance or Android lifecycle behavior. Desktop hints still say “Click”.
Set `SDL_AUDIODRIVER=dummy` when launching the game if host audio is unwanted.

A local browser port would require changes to the synchronous game loop and
browser save handling. Streaming lets the existing desktop game run unchanged.

## Saves and session lifetime

Use a separate save for play-testing. On Linux, set `XDG_DATA_HOME` to a dedicated
directory before launching the game; its save will be under `snekfeed/save.json`
inside that directory. This keeps the ordinary desktop save separate.

Autosave runs every 30 seconds. Closing a browser tab leaves the game running and
earning at its normal rate. Multiple clients share control of the same game.
Shut the game down through its quit event so it saves before stopping the virtual
display. Restart the game after source changes to play the updated code.
The host must stay awake and connected to Tailscale while testing.
