# Radio

Radio is an optional installable app built as `build/node-apps/radio.zx`.
It requires host API 18, which adds owner-scoped `AudioStartHost`,
`AudioStopHost`, `AudioStateHost` and `AudioVolumeHost` effects. A package
can start an HTTPS audio stream, observe its state, set volume and stop its
own playback. Starting a new stream replaces the current stream; explicit
Stop and volume changes apply only to the owning app. Closing or uninstalling
the owning app, or switching accounts, cancels playback. Navigating away
keeps it playing. Playback does not start automatically after a restart.

The bundle owns the station catalogue, controls and saved station/volume.
Its three stations publish MP3 links for external players: Ambient Sleeping
Pill, a.m. ambient and Ambient Modern. Audio goes directly from their HTTPS
servers to the device. There are no website launchers or recording/relay
servers. SomaFM and Sleep Radio are excluded because their published app
usage terms do not authorize this integration.

The native player decodes a bounded MP3 buffer through raylib's existing
decoder. Android uses MediaPlayer and the existing media-playback foreground
service; the browser uses an audio element and follows browser background
policies. Radio keeps playing across Inner Breeze app navigation and takes
precedence over a practice's preselected music while active. Stop cancels
network connections and pending retries. A local development install uses
the normal `INBE_NODE_APP_FILE` mechanism; publication remains separate.
