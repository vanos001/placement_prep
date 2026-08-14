# Firmware Development

Firmware is the software that runs directly on embedded hardware, often with no OS abstraction layer. It encompasses everything from the first instruction executed after power-on to the application logic.

## Boot Process

When an ARM Cortex-M MCU resets, the processor reads the initial stack pointer from address `0x00000000` and the reset vector (PC) from address `0x00000004`. Execution jumps to the reset handler, which:

1. **Initializes the data section**: Copies initialized data from Flash to RAM
2. **Zero-fills the BSS section**: Sets uninitialized global/static variables to zero
3. **Calls `main()`**: The C runtime entry point

```
Power-on → CPU reads 0x00000000 (SP) and 0x00000004 (Reset Vector)
  → Reset handler → .data init → .bss zero-fill → main()
    → Application superloop or RTOS scheduler
```

### Bootloader

A **bootloader** is a small piece of firmware that runs before the main application. It handles:

- **Platform initialization**: Clocks, pins, external memories
- **Firmware update validation**: Checks integrity (CRC, signature verification) of the application image
- **Application launch**: Jumps to the application if valid; stays in bootloader mode otherwise

The bootloader/application boundary is defined at link time—each has its own vector table. Common patterns:
- **Single slot with fallback**: One app region; bootloader reverts to factory image on corruption
- **Dual-bank (A/B)**: Two app regions; update writes to the inactive bank, then swaps

## Firmware Update Strategies

### Over-the-Air (OTA)

OTA updates deliver new firmware over a network (Wi-Fi, BLE, LoRaWAN). Key challenges:

- **Secure boot**: Verify the firmware image signature before executing
- **Atomicity**: Ensure a failed update does not brick the device
- **Bandwidth**: Firmware may be larger than available RAM—use chunked streaming writes
- **Rollback**: If the new firmware fails health checks, revert to the previous version

### Dual-Bank Updates

Dual-bank (A/B) partitioning provides safe, interruptible updates:

```
Flash Layout:
[Bootloader][App A (active)][App B (inactive)][Metadata]

Update flow:
1. Download firmware to App B region
2. Verify CRC/signature
3. Set metadata flag to boot from B
4. Reboot → bootloader launches App B
5. App B runs health check; if pass, mark B as permanent
6. If fail, bootloader reverts to App A
```

## Watchdog Timers

A **watchdog timer (WDT)** is a hardware timer that must be periodically "kicked" (reset) by software. If the software fails to kick it within the timeout period, the WDT triggers a system reset.

Watchdogs protect against:
- Infinite loops or deadlocks in application code
- RTOS scheduler hangs
- Radiation-induced bit flips that corrupt control flow
- Power supply glitches

**Important**: The watchdog must be kicked from a task **independent** of the task that might hang. If the same task both does work and kicks the watchdog, a hang in that task will also halt the kick. In RTOS systems, a dedicated low-priority monitor task is common.

```c
void vMonitorTask(void *pvParams) {
    for (;;) {
        // Check that all critical tasks have reported in
        if (task_heartbeat_ok()) {
            WDT->KR = 0xAAAA;  // Kick the watchdog
        }
        vTaskDelay(pdMS_TO_TICKS(1000));
    }
}
```

## Power Management

### Sleep Modes

ARM Cortex-M defines several low-power states, and silicon vendors add vendor-specific modes:

| Mode | CPU | Flash | SRAM | Peripherals | Wake Source | Current |
|------|-----|-------|------|-------------|-------------|---------|
| Run | Active | Active | Active | Active | — | Full |
| Sleep | Gated | Active | Retained | Active | Interrupt | ~µA–mA |
| Deep Sleep | Gated | Gated | Retained/partial | Gated | EXTI, RTC | ~µA |
| Standby | Off | Off | Lost | Off | Reset pin, RTC | ~100 nA–µA |
| Shutdown | Off | Off | Lost | Off | Reset pin only | ~10 nA |

### Strategies

- **Tickless idle**: When all RTOS tasks are blocked, disable the SysTick timer and enter deep sleep. Wake on the next scheduled timeout. FreeRTOS supports this via `configUSE_TICKLESS_IDLE`.
- **Peripheral power gating**: Disable clocks to unused peripherals via RCC registers
- **Voltage scaling**: Lower the core supply voltage when performance requirements are low
- **Event-driven design**: Replace polling with interrupt-driven or DMA-based data acquisition

## Debugging: JTAG and SWD

### JTAG (Joint Test Action Group)

Originally designed for board-level testing (boundary scan), JTAG provides debug access: halt/resume CPU, read/write memory and registers, set breakpoints, and single-step. Requires 4–5 signals (TCK, TMS, TDI, TDO, TRST).

### SWD (Serial Wire Debug)

ARM's 2-pin alternative to JTAG. Uses SWDIO (bidirectional data) and SWCLK (clock). Supports the same debug capabilities as JTAG in half the pin count. SWD is the standard debug interface for Cortex-M devices.

Both interfaces are accessed through debug probes (ST-Link, J-Link, CMSIS-DAP) and tools like GDB, OpenOCD, and vendor-specific IDEs.

## Interview Questions

1. Explain what happens when an ARM Cortex-M microcontroller powers on. What are the first instructions executed?
2. What is a bootloader and why is it used instead of jumping directly to the application?
3. Describe a dual-bank firmware update strategy. How do you handle a failed update?
4. What is the purpose of a watchdog timer? Can it cause problems?
5. Explain tickless idle. Why does it matter for battery-powered devices?
6. What is the difference between JTAG and SWD?
7. How would you securely verify a firmware update received over the air?
8. Why shouldn't the same task that does work also be responsible for kicking the watchdog?
9. What happens to SRAM contents during deep sleep? How do you decide what to retain?
10. A device reboots randomly in the field. How would you diagnose this using firmware?