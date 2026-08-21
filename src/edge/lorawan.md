# LoRaWAN Deep Dive

## Overview

LoRaWAN is a Low-Power Wide-Area Network (LPWAN) stack built on top of Semtech's proprietary **LoRa** modulation. It targets battery-powered sensors that need to send a few bytes a day across kilometres of range with a coin cell that lasts years. This chapter unpacks the four layers — physical, MAC, network server, and regional regulation — and contrasts LoRaWAN against its 3GPP cousins NB-IoT and LTE-M.

```
Application (LoRaWAN payload, encrypted)
────────────────────────────────────────
MAC layer   (Class A / B / C, Join, ADR)
────────────────────────────────────────
LoRa PHY    (CSS, SF7..SF12, sub-GHz ISM)
────────────────────────────────────────
ISM Band    (EU 868 / US 915 / AS 923 MHz)
```

## The LoRa Physical Layer

### Chirp Spread Spectrum (CSS)

LoRa modulation encodes data into **chirps** — signals whose frequency linearly sweeps across the band. A "down-chirp" sweeps from `f_max` to `f_min`; an "up-chirp" sweeps the opposite way. Symbols are encoded by the *starting frequency offset* of the chirp, so a receiver can decode by looking at the rate of change of instantaneous frequency. This gives LoRa two notable properties:

1. **Processing gain**: the receiver can integrate energy over a long chirp (milliseconds) and pull a signal out from below the noise floor. A LoRa signal at SNR of −20 dB (signal 100× weaker than noise) is still decodable at high spreading factors.
2. **Immunity to Doppler and multipath**: chirps are robust to time/frequency shifts because two chirps with different offsets produce a beat at a constant frequency that is easy to detect via FFT.

### Spreading Factors SF7–SF12

The **Spreading Factor (SF)** sets the chirp duration: each increment of SF doubles the time on air (and halves the bit rate) but adds ~2.5 dB of link budget. Semtech's SX1276 supports SF6–SF12; LoRaWAN restricts to SF7–SF12 for regulatory reasons.

| SF | Time on air for 12-byte payload (BW=125 kHz) | Bit rate (approx) | Link budget |
|----|----------------------------------------------|--------------------|-------------|
| 7  | ~29 ms  | 5470 bps | 132 dB |
| 8  | ~52 ms  | 3125 bps | 134 dB |
| 9  | ~100 ms | 1760 bps | 137 dB |
| 10 | ~200 ms | 980 bps  | 139 dB |
| 11 | ~400 ms | 540 bps  | 141 dB |
| 12 | ~991 ms | 295 bps  | 144 dB |

Orthogonal SFs are *non-interfering* in the same channel — that's the magic of CSS: SF7 and SF8 can coexist on the same 125 kHz channel without collisions, doubling spectral efficiency.

### Sub-GHz ISM Bands

LoRaWAN runs on **regional** ISM bands. The main ones:

| Region | Band | Mandatory channels | Max EIRP | Duty cycle limit |
|--------|------|--------------------|----------|-------------------|
| EU868  | 863–870 MHz | 3 channels @ 868.1/868.3/868.5 MHz | 14 dBm | 1% per sub-band |
| US915  | 902–928 MHz | 8 uplink sub-bands × 8 channels + 8 downlink | 30 dBm | No duty cycle; FHSS |
| AS923  | 915–928 MHz | 2 channels @ 923.2/923.4 | 16 dBm | 1% |
| CN470  | 470–510 MHz | 8 uplink + 2 downlink | 17 dBm | regulated per sub-band |
| IN865  | 865–867 MHz | 3 channels @ 865.0625/865.4025/865.9850 | 30 dBm | 1% |

The US915 plan is special: regulations there have no duty-cycle limit, but the FCC requires frequency hopping. US915 specifies 64 uplink channels split into 8 sub-bands of 8 channels each (plus 8 downlink channels). Devices hop pseudorandomly across the sub-band.

### Bandwidth and Data Rate

Three channel bandwidths are used: **125 kHz, 250 kHz, 500 kHz**. The actual data rate is `(SF) / (2^SF / BW)`. Higher BW gives higher throughput but needs more link budget; **DR0–DR5** in EU868 encode combinations of SF and BW (DR0 = SF12/125 kHz, ~250 bps; DR5 = SF7/125 kHz, ~5470 bps).

## LoRaWAN MAC

### Topology: Star-of-Stars

```
 ┌────────┐                                                  ┌──────────┐
 │ Device │ ──┐                                          ┌──▶│App server│
 └────────┘   │  ┌──────────┐   UDP/Pkt Forwarder  ┌────┴───┴──────────┘
              ├──┤  Gateway │──────────────────────▶│   Network Server  │──▶ App
 ┌────────┐   │  │ (RF ←→ IP)                     │ (MIC, dedup, ADR,  │
 │ Device │ ──┘  └──────────┘                     │  Join, downlink Q) │
 └────────┘                                         └────────────────────┘
        Radio (LoRa)                                       IP
```

- **End devices** talk LoRa to *any* gateway within range. They never speak IP.
- **Gateways** are dumb radio-to-IP bridges: they receive LoRa frames and forward them as JSON-over-UDP "Packet Forwarder" messages to the network server. A gateway does not decode the LoRaWAN payload, just the LoRa radio header.
- **Network Server** is the brains: deduplicates (multiple gateways may hear the same uplink), checks the MIC (Message Integrity Code), forwards the decrypted payload to the application server, and schedules downlinks.

Multiple gateways hearing the same frame is a feature, not a bug — the network server picks the best-received copy for uplink, and the best gateway for the next downlink.

### Device Classes

| Class | Listening behaviour | Latency | Power |
|-------|----------------------|---------|-------|
| **A** | Two RX windows after every uplink | seconds–minutes (until next uplink) | Lowest |
| **B** | Class A + scheduled receive slots (beacons every 128 s) | Seconds | Medium |
| **C** | Continuous RX2 listening (except while transmitting) | Sub-second | Highest |

#### Class A

```
Time ──────────────────────────────────────────▶
   │  Uplink (RX1 timing, 1 s after end of TX)
   │             │RX1 (SF12 or RX1DR)  
   │             │   if downlink → done
   │             │              │RX2 (SF12 / 869.525 MHz)
   │             │              │   if downlink → done
   │             │              │       No downlink → sleep until next event
   ▼                          ▼
```

The two RX windows (`RX1` 1 s after uplink; `RX2` 2 s after, on a fixed SF12 frequency) give the network server a chance to piggyback downlink onto the device's existing wake-ups. This is what makes 10-year battery life feasible: the radio is on for less than 1% of the time.

#### Class B

A Class B device locks to a **beacon** broadcast by the gateway every 128 s. The beacon carries time + GPS coordinates + ping-slot period. Between beacons, the device wakes for short *ping slots* (e.g. every 8 s for ~30 ms each), allowing the network server to push downlink with bounded latency without waiting for an uplink.

#### Class C

The radio stays in RX whenever it isn't transmitting. Used for actuators (smart-valve, smart-lock, smart-streetlight) where mains power is available. A Class C device can be commanded immediately, but a Class A device may not respond for hours.

### Join (OTAA)

Activation is performed by **Over-The-Air Activation (OTAA)** rather than hard-coding the session keys (ABP). Three identifiers are required:

- **DevEUI** — a 64-bit globally-unique device identifier (often MAC-derived from the radio chip's unique ID).
- **AppEUI / JoinEUI** — a 64-bit identifier of the Join Server (the entity that holds the root keys).
- **AppKey** — a 128-bit AES root key, stored on the device and (out-of-band) in the Join Server.

```
Device                              Network Server         Join Server
  │                                   │                        │
  │ JoinRequest{DevEUI, JoinEUI,      │                        │
  │   DevNonce, MIC(AppKey, msg)}     │                        │
  ├──────────────────────────────────▶│ (forwards)            │
  │                                   │───────────────────────▶│
  │                                   │  (derives DevAddr,     │
  │                                   │   NwkSKey, AppSKey     │
  │                                   │   from AppKey +        │
  │                                   │   DevNonce + AppNonce) │
  │                                   │◀───── session keys ────│
  │◀── JoinAccept{Encrypted with      │                        │
  │     AppKey: JoinAppNonce,         │                        │
  │     DevAddr, DLSettings,          │                        │
  │     RxDelay, CFList, MIC}         │                        │
  │                                   │                        │
  │   (device derives NwkSKey and     │                        │
  │    AppSKey from AppKey + AppNonce  │                        │
  │    + NetID + DevNonce using        │                        │
  │    AES-CMAC / AES-128)             │                        │
  │                                   │                        │
  │══════════ Encrypted data session ═════════════════════════│
```

`DevNonce` is a random 16-bit generated by the device and stored; the network server rejects duplicates to prevent replay. Session keys are **derived** (`NwkSKey = AES-CMAC(AppKey, 0x01 | AppNonce | NetID | DevNonce | padding)`; `AppSKey` is the same construction with the leading byte `0x02`) — never transmitted in the clear. The JoinAccept payload is encrypted with AppKey itself, so an eavesdropper sees nothing useful.

**NwkSKey** is used to compute and verify the MIC of every frame (integrity). **AppSKey** is used to encrypt/decrypt the application payload (confidentiality) using AES in counter mode (LoRaWAN 1.0.x) or AES-CTR with a frame-counter-derived nonce (1.1, with separate NwkSEncKey, SNwkSIntKey, FNwkSIntKey).

## Network Server Internals

### Deduplication

Because every gateway in range forwards the same uplink, the network server may receive N copies within ~10 ms. It de-duplicates by `(DevAddr, FCnt, payload)` and picks the one with the best `SNR` and `RSSI`. The choice is later used by **ADR** to set the appropriate SF for future uplinks.

### Downlink Scheduling

Downlinks are tricky in LoRaWAN because the gateway is half-duplex — transmitting a downlink blocks all uplink reception. The network server picks one (and only one) gateway to send the downlink. If it has multiple downlinks queued for the same device, they are coalesced into a single MAC-layer frame (a "mac in mac" piggybacked onto a network-layer ack).

### Frame Counters and Replay Protection

Every frame carries a 32-bit `FCnt` (`FCntUp` for uplink, `FCntDown` for downlink). The receiver only accepts `FCnt > last_seen_FCnt` (with a small window for in-flight reordering). On loss of session state, the device must re-join to get fresh counters — which is why Class A devices without OTAA can get stuck on reboot in ABP mode.

## Adaptive Data Rate (ADR)

ADR is the algorithm that automatically picks the SF, bandwidth, and TX power for each device so as to minimise time-on-air while maintaining a link margin. The principle: if your signal is consistently strong, drop the SF to save battery; if it gets worse, raise it back.

The LoRaWAN backend (network server) maintains a sliding window of the last 20 uplinks per device and computes:

- **SNR margin** = `SNR_max − SNR_required − margin_noise_floor`, where `SNR_required` is the per-SF sensitivity (e.g. SF12 ≈ −20 dB, SF7 ≈ −7.5 dB at BW=125 kHz).
- If `SNR_margin > 0`, the link has margin → **lower** SF.
- If `SNR_margin < 0`, the link is fragile → **raise** SF.

The network server sends a `LinkADRReq` MAC command in a downlink to set the new `DR` (data rate), `TxPower`, and `ChMask`. The device responds with `LinkADRAns` acknowledging the change. The algorithm is described in the LoRaWAN Backend Interfaces specification (TS001.1).

A simplified view:

```
last_20_snr = [4, 6, 5, 7, 5, 8, 6, 5, 7, 6, ...]
snr_margin = min(last_20_snr) - snr_required_for_current_SF
if snr_margin > 3 dB and current_SF > SF7:
    current_SF -= 1                 # drop a factor
    send LinkADRReq(device, new_dr)
elif snr_margin < 0:
    current_SF += 1
    send LinkADRReq(device, new_dr)
```

The device can also request ADR by setting the `ADR` flag in uplink; without it, the server leaves DR alone.

## Duty Cycle and Regulatory Limits

In EU868, the **1% duty-cycle** rule (per sub-band) dominates all design choices. A device that transmits for `T_air` seconds must then remain silent for `99 × T_air` seconds before transmitting again in the same sub-band.

For a 12-byte payload at SF7 (29 ms on air), 1% duty cycle → minimum 2.9 s between uplinks → a hard ceiling of about 20 messages/min, with deep implications:

- Real-time sensor streaming is impossible. LoRaWAN is *uplink-bursty* — events, not streams.
- The downlink budget is *also* regulated: gateways can't continuously beacon either.

In US915 the FCC takes a different tack — no duty cycle, but require **frequency hopping** across ≥50 channels if you use more than 400 ms of dwell time in any 20 s window. The MAC's `TxParamSetupReq`/`DutyCycleReq` commands let the network server push these regional constraints onto the device.

## LoRaWAN vs NB-IoT vs LTE-M

| Property              | LoRaWAN                            | NB-IoT (Cat-NB1)            | LTE-M (Cat-M1)            |
|-----------------------|------------------------------------|-----------------------------|----------------------------|
| Spectrum              | Unlicensed ISM (sub-GHz)           | Licensed LTE in-band/guard   | Licensed LTE in-band       |
| Modulation            | CSS (LoRa)                         | OFDMA down / SC-FDMA up     | OFDMA / SC-FDMA            |
| Range (urban)         | 2–5 km                             | 1–10 km                     | 1–5 km                     |
| Range (rural, LoS)    | 10–15 km (up to 40 km)             | up to 35 km                 | up to 11 km                |
| Peak uplink           | 50 kbps (SF7)                     | 62 kbps (multi-tone)        | 1 Mbps (Cat-M1) / 7 Mbps (eMTC) |
| Power (TX peak)       | ~25 mW (14 dBm EIRP)              | 23 dBm                      | 23 dBm / 20 dBm            |
| Battery life          | 5–10 years (coin cell, 12 msgs/day)| 10 years (PSM, eDRX)        | 5–10 years (PSM, eDRX)     |
| Latency (typical)     | 1–10 s (Class A)                  | 1.6–10 s                    | 50–100 ms                  |
| Mobility              | Limited (no handover)              | Limited (cell reselection) | Full (HO)                  |
| Cost per device       | €1–3 module                       | €3–6                        | €5–10                      |
| Operator              | Private / community / Sigfox-style | Cellular MNO                 | Cellular MNO               |
| QoS                   | Best-effort                        | Guaranteed by LTE scheduler  | Guaranteed                 |
| Best for              | Agri, util metering, asset track   | Smart meter (deep indoor), gas | Wearables, alarms, fleet  |

**NB-IoT** shines for deep-indoor coverage (a +20 dB MCL boost over LTE gives it basement-level reception) and for industrial metering where you can rely on cellular operators and don't want to deploy your own gateways. **LTE-M** has higher data rates and full mobility, making it suitable for wearables and trackers that move through cell boundaries. **LoRaWAN** is unbeatable for private deployments (agriculture, oil & gas, water) where the operator owns the radio network and doesn't want to pay per-device cellular fees.

## Interview Angle

> **"A 12-byte sensor payload takes 991 ms on air at SF12. How do you reduce time-on-air without losing range?"**

Two answers: (1) raise the data rate via ADR by lowering SF — but only if link budget allows, which ADR determines from SNR history. (2) Use **channel diversity** in EU868 — three default channels at 868.1/868.3/868.5 are independent for duty cycle, so the device can spread its 1% across each (technically each sub-band), giving 3× more messages per hour. (3) Consider switching to a wider 250 kHz channel where regulatory bodies permit (US915). (4) Compress the payload — LoRaWAN has a payload-size-fee, so packing 6 floats into 12 bytes (rather than JSON's 80) is a multiplier on every battery.

> **"Why are there three RX windows in Class A?"**

RX1 (1 s) is the first chance to send a downlink on the same channel/SF as the uplink. RX2 (2 s) is the *fixed* window on a known SF12 channel (EU 868.525 MHz @ 0.1% DC by region) — even if the uplink's SF was so high that the gateway couldn't synthesise a faster downlink in time, RX2 gives a guaranteed window. RX2 being high-latency/high-link-budget means the network server can use it even for devices near the edge of coverage.

## Key References

- LoRaWAN 1.0.4 Specification (LoRa Alliance) — https://lora-alliance.org/resource_hub/lorawan-104-specification/
- LoRaWAN 1.1 Specification — https://lora-alliance.org/resource_hub/lorawan-11-specification/
- LoRaWAN Backend Interfaces v1.0 — https://lora-alliance.org/resource_hub/lorawan-backend-interface-v1-0/
- Semtech SX1276 Datasheet (LoRa modulation, registers) — https://semtech.my.salesforce.com/sfc/p/E00000000JelG/a/2R0000001R3M/a/0b4000000K4SyA
- Semtech "LoRa Modulation Basics" AN1200.22 — https://semtech.my.salesforce.com/sfc/p/E00000000JelG/a/2R0000001R3M/a/0b4000000K4Swl
- The Things Network — "LoRaWAN" docs — https://www.thethingsnetwork.org/docs/lorawan/
- The Things Industries — "LoRaWAN Airtime Calculator" — https://www.loratools.nl/#/airtime
- 3GPP TS 36.300 (NB-IoT and LTE-M overall description) — https://www.3gpp.org/dynareport/36-300.htm
