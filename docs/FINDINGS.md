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
| 8009        | tcp   | `FireTVDefaultMediaReceiver` — Amazon **Fling** receiver. **Not Google Cast**: an mDNS browse shows no `_googlecast._tcp` from the TV. | no (proprietary) |
| 7000        | tcp   | AirPlay receiver (`com.apple.airplay.amazon.airplay`, `EniraService`) | yes — AirPlay clients |
| 1900        | udp   | DIAL / SSDP (`com.amazon.dialservice`)              | **yes — verified live.** REST endpoint answers per-app queries; see DIAL notes below. |
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
2. **DIAL** — launch streaming apps by name over HTTP. **Verified on this unit:**
   the endpoint is live and answers per-app queries (`dial list`).

**Ruled out on this unit (tested):**
- **Google Cast** — no `_googlecast._tcp` advertised; port 8009 is Amazon Fling.
  The former `cast` module was removed.
- **Matter** — Casting-only, see above.

The `toshiba_tv.matter` module is kept only as a generic python-matter-server client
for devices that *are* commissionable; it does not apply to this TV.

## DIAL notes (from a live `dial list`)

- `Netflix` → reports a state (`running`/`stopped`) — fully working.
- `YouTube` → HTTP **403** on GET. This is YouTube's known DIAL behaviour (it
  refuses status queries without its own headers); the app is present and
  `POST /YouTube` (launch) still works. Reported as `present-403`.
- PrimeVideo / Hulu / Disney / HBOMax / Max → 404: those apps don't register a DIAL
  name on Fire TV. Launch them over ADB instead (`launch <package>`).

## mDNS note

A LAN-wide `dns-sd` browse showed `_amzn-wplay._tcp` (WhisperPlay — the TV),
`_airplay._tcp` (the TV), and also `_matter._tcp` / `_matterd._udp`. The Matter
records were **not attributed to the TV's IP** in that browse and may belong to another
device on the network; they are not evidence the TV is commissionable.

## Scope / safety

Everything here is read-only inspection and documented/standard control protocols on
an owner-operated device on a private LAN. No root, no secure-boot bypass, no firmware
modification. The device serial from `getprop` is intentionally not recorded in this
repo.
