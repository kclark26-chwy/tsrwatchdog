# Toshiba Fire TV — reverse-engineering findings

Target: **Toshiba 4K Fire TV**, device `AFTHA004` (Amazon codename **hazel**).
Software: **Fire OS 7** (`PS7717.5741N`), Android 9, security patch 2026-03-01,
`release-keys`. SoC/platform: **Amlogic** (DroidLogic Android TV stack).

All findings below were gathered on a TV the owner controls, over the LAN, using
ADB (authorized via the on-screen "Allow USB debugging" prompt) and by pulling and
decompiling four system APKs.

## Local network surface

Listening sockets (`0.0.0.0` / `::`, i.e. reachable from the LAN):

| Port        | Proto | Service / package                                   | Usable from code |
|-------------|-------|-----------------------------------------------------|------------------|
| 5555        | tcp   | ADB (`adbd`)                                        | yes — primary control path |
| 8009        | tcp   | `FireTVDefaultMediaReceiver` — **unverified**. 8009 is the Chromecast port, but Fire TV does not officially support Google Cast; this is likely Amazon's *Fling* receiver, not Cast. | unknown until tested |
| 7000        | tcp   | AirPlay receiver (`com.apple.airplay.amazon.airplay`, `EniraService`) | yes — AirPlay clients |
| 1900        | udp   | DIAL / SSDP (`com.amazon.dialservice`)              | yes — DIAL REST, app launch by name |
| 5353        | udp   | mDNS (Cast / AirPlay / Whisperplay advertisement)   | discovery |
| 60000       | tcp   | WhisperLink (`com.amazon.whisperlink.core.android`) | Amazon proprietary (Fire TV phone-remote app) |
| 5541 / 5550 | udp   | WhisperPlay discovery                               | Amazon proprietary |

Everything else listening was loopback-only or an ephemeral per-process port.

## Running services of interest

(From `dumpsys activity services`.)

- `com.amazon.tv.mattercohost/.ContentAppAgentService` — **Matter Casting** only.
  The TV is a Matter *Casting Video Player* (a receiver that phone apps cast to,
  showing a PIN on connect). It is **not** a commissionable Matter device: there is
  no `MT:` setup code in Settings and it cannot be added to a home controller for
  power / volume. Verified on this unit — no Matter entry exists in Settings.
- `com.amazon.tv.devicecontrol/.quicksettings.SoundbarProvider` — HDMI-CEC + IR
  control of external gear (the "Equipment Control" settings page).
- `com.apple.airplay.amazon.airplay/.EniraService` — AirPlay.
- `com.droidlogic.tvinput/.services.{Hdmi1,Hdmi2,AV1,ADTV}InputService`,
  `com.droidlogic/.DroidLogicPowerService`,
  `com.amazon.tv.settings.amlogic/.AmlOemSettings` — the Amlogic hardware layer that
  actually switches inputs and drives power/picture. This is the Toshiba/Amlogic-
  specific hardware abstraction.
- `com.droidlogic/.NetflixService` — Netflix ESN / wake integration.

## APK analysis

Pulled and decompiled with jadx:

- **`com.amazon.dialservice`** — thin JNI shim; the DIAL implementation lives in
  `libcom_amazon_dialservice.so`. No need to decompile: DIAL is a published standard
  (SSDP discovery on 1900 → per-app REST endpoint). App launch and state query.
- **`com.amazon.tv.devicecontrol`** — large app (6.9 MB dex + 3.5 MB native lib).
  It is **Alexa-cloud driven**: smart-home "skills" (`com.amazon.devicecontrol.skills`)
  and `DownchannelOperation`s receive directives from Amazon and translate them into
  CEC/IR actions. Not a clean local API. Notable: it contains `com.amazon.infrared`,
  confirming an **on-board IR blaster** — the TV can emit IR to control a soundbar/AVR.
  The IR directive wire format is reconstructed in `ir_emitter_directive.proto`.
- **`com.amazon.tv.matter`** — Matter data-model classes. Confirms the TV is a Matter
  device (the modern local-control route).
- **`com.amazon.whisperlink.core.android`** — Amazon's proprietary device-to-device
  framework (the Fire TV phone-remote app, Alexa device targeting). Port 60000.

## IR blaster directive format

See [`ir_emitter_directive.proto`](ir_emitter_directive.proto) for the reconstructed
protobuf. Summary: an emit directive carries one or more `IrCode`s, each with a
carrier frequency (Hz), duty cycle, repeat count, emitter channel, and a pulse-count
sequence (`default_code`, plus a `toggle_code` for toggle-bit protocols like RC5/RC6),
with inter-burst idle timings. This payload is pushed from Alexa's cloud, so it is a
documentation artifact rather than a local control vector.

## Practical control paths (recommended order)

1. **ADB** (port 5555) — working today. Remote keys, launch apps, inspect state,
   screenshots, and wake from sleep (`input keyevent WAKEUP`). See the `toshiba_tv`
   package in this repo.
2. **DIAL** — launch streaming apps by name over HTTP. Likely works (Fire TV
   supports DIAL) but not yet verified on this unit.
3. **Google Cast** (`pychromecast`) — **unverified, probably not Cast.** See the port
   table; port 8009 is likely Amazon Fling. Test before relying on it.

**Not viable on this unit:** Matter (Casting-only, see above). The `toshiba_tv.matter`
module is kept as a generic python-matter-server client but does not apply to this TV.

## Scope / safety

Everything here is read-only inspection and documented/standard control protocols on
an owner-operated device on a private LAN. No root, no secure-boot bypass, no firmware
modification. The device serial from `getprop` is intentionally not recorded in this
repo.
