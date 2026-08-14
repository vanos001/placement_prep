# Embedded Peripherals and Communication Protocols

Embedded microcontrollers communicate with the outside world through **peripherals**—hardware blocks integrated on-chip that handle I/O independently of the CPU. Understanding these peripherals is fundamental to embedded programming.

## Communication Protocols

### GPIO (General-Purpose I/O)

GPIO pins are the simplest peripheral: each pin can be configured as input or output. Outputs drive high or low voltage levels; inputs read external signals. GPIO is used for LEDs, buttons, relays, and simple digital signaling.

### UART (Universal Asynchronous Receiver/Transmitter)

UART is a point-to-point, asynchronous serial protocol. There is no shared clock—both sides agree on a baud rate (e.g., 9600, 115200). Data is framed as: start bit (low), 5–9 data bits, optional parity bit, 1–2 stop bits. UART is full-duplex with separate TX and RX lines.

**Common use cases**: Debug console logging, GPS modules, Bluetooth modules, Modbus communication.

### SPI (Serial Peripheral Interface)

SPI is a synchronous, full-duplex bus with one master and one or more slaves. It uses four signals: SCLK (clock), MOSI (master-out-slave-in), MISO (master-in-slave-out), and SS/CS (slave select—active low). The master generates the clock and selects the slave by pulling its CS line low.

SPI supports clock speeds from a few hundred kHz to tens of MHz. There is no standard framing—protocol is device-specific. Each additional slave requires a separate CS line.

**Common use cases**: SD cards, display controllers, flash memory, ADC/DAC chips, IMU sensors.

### I2C (Inter-Integrated Circuit)

I2C is a synchronous, half-duplex, multi-master bus using only two wires: SDA (data) and SCL (clock). Every device has a unique 7-bit (or 10-bit) address. Communication uses start/stop conditions and acknowledges (ACK/NACK) after each byte.

I2C supports three speeds: Standard mode (100 kbps), Fast mode (400 kbps), and Fast Mode Plus (1 Mbps).

**Common use cases**: Temperature sensors, EEPROMs, real-time clocks, battery monitors, OLED displays.

### CAN (Controller Area Network)

CAN is a robust, differential serial bus designed for automotive and industrial environments. It uses bitwise arbitration on the bus—nodes transmit simultaneously, and the node with the highest-priority ID wins without collision. CAN frames include a priority-based ID, up to 8 bytes of data, and CRC error checking. CAN FD (Flexible Data-rate) extends this to 64 bytes and higher speeds.

**Common use cases**: Automotive in-vehicle networks, industrial automation, medical equipment.

## Protocol Comparison

| Protocol | Wires | Speed | Topology | Duplex | Max Devices |
|----------|-------|-------|----------|--------|-------------|
| UART | 2 (TX, RX) | ~115200 bps typical | Point-to-point | Full | 2 |
| SPI | 4 + 1/slave | 1–50 Mbps | Star (per CS) | Full | Limited by CS pins |
| I2C | 2 (SDA, SCL) | 100 kbps–1 Mbps | Multi-drop bus | Half | 127 (7-bit addr) |
| CAN | 2 (CANH, CANL) | 1 Mbps (classical) | Multi-drop bus | Half | ~110 |

## Interrupts and Timers

### Interrupts

An interrupt is a hardware signal that causes the CPU to temporarily halt current execution and jump to an **Interrupt Service Routine (ISR)**. On Cortex-M, the NVIC manages priorities (0 = highest). Key rules:

- ISRs must be **short and fast**—defer processing to the main loop or RTOS task
- ISRs must be **reentrant** if the same interrupt can nest
- Never call blocking functions or `printf` from an ISR
- Use volatile variables to share data between ISRs and main code

### Timers

Hardware timers count clock cycles and can generate interrupts at specific counts. Uses include:

- **Periodic timing**: Generating regular intervals (e.g., 1 ms tick for an RTOS)
- **Input capture**: Measuring pulse width (e.g., PWM duty cycle reading)
- **Output compare**: Generating precise pulse timing (e.g., stepper motor step signals)

### PWM (Pulse Width Modulation)

PWM generates a digital signal with a variable duty cycle to simulate analog output. A timer drives a counter, and an output compare register sets the toggle point. PWM controls LED brightness, motor speed, and servo position.

```
Duty cycle = (ON time / Period) × 100%

Example: 50% duty cycle at 1 kHz → 500 µs high, 500 µs low
```

## ADC/DAC

**ADC (Analog-to-Digital Converter)** converts continuous voltage to discrete digital values. Key parameters: resolution (8/10/12/16-bit), sample rate (kSPS to MSPS), and reference voltage. Common techniques include successive approximation (SAR) and sigma-delta.

**DAC (Digital-to-Analog Converter)** does the reverse. Used for audio output, waveform generation, and control loops. Most MCUs have limited DAC channels; external DACs are common for high-fidelity applications.

## Memory-Mapped I/O

On ARM and x86, peripherals are accessed by reading and writing to **memory addresses** in a dedicated peripheral address range. The hardware decodes these addresses and routes them to peripheral registers instead of RAM.

```c
// STM32-style memory-mapped GPIO
#define GPIOA_BASE  0x40020000UL
#define GPIOA_MODER ((volatile uint32_t *)(GPIOA_BASE + 0x00))
#define GPIOA_ODR   ((volatile uint32_t *)(GPIOA_BASE + 0x14))

// Set PA5 as output (bits 11:10 = 01)
*GPIOA_MODER = (*GPIOA_MODER & ~(3U << 10)) | (1U << 10);

// Toggle PA5
*GPIOA_ODR ^= (1U << 5);
```

The `volatile` keyword is essential—it tells the compiler not to optimize away or reorder these accesses.

## DMA (Direct Memory Access)

DMA is a hardware controller that transfers data between peripherals and memory (or memory-to-memory) without CPU involvement. The CPU initiates a DMA transfer by configuring source, destination, and count, then the DMA controller handles the transfer autonomously.

**Benefits**:
- Frees CPU for application logic
- Reduces power consumption (CPU can stay in sleep)
- Enables high-throughput data streams (e.g., ADC streaming, UART at high baud)

**Common use**: ADC circular buffer, SPI Tx/Rx with large buffers, UART receive into a ring buffer.

## Code Example: GPIO Toggle (STM32-Style)

```c
#include "stm32f4xx.h"

void delay_ms(uint32_t ms) {
    // Simplified: uses SysTick for ~1ms delay
    SysTick->LOAD = (SystemCoreClock / 1000) - 1;
    SysTick->VAL = 0;
    SysTick->CTRL = SysTick_CTRL_ENABLE_Msk;
    for (uint32_t i = 0; i < ms; i++) {
        while (!(SysTick->CTRL & SysTick_CTRL_COUNTFLAG_Msk));
    }
    SysTick->CTRL = 0;
}

int main(void) {
    // Enable clock for GPIOA
    RCC->AHB1ENR |= RCC_AHB1ENR_GPIOAEN;

    // Configure PA5 as output (user LED on Nucleo boards)
    GPIOA->MODER &= ~(3U << 10);   // Clear mode bits for PA5
    GPIOA->MODER |=  (1U << 10);   // Set to general-purpose output

    while (1) {
        GPIOA->ODR ^= (1U << 5);    // Toggle PA5
        delay_ms(500);
    }
}
```

## Interview Questions

1. What is the difference between SPI and I2C? When would you choose one over the other?
2. Why must GPIO register accesses use `volatile`?
3. Explain how I2C addressing works. What happens with an NACK?
4. What is DMA and when would you use it in an embedded application?
5. Why should ISRs be kept as short as possible?
6. How does CAN bus arbitration work without a clock line?
7. What is the difference between polling and interrupt-driven I/O?
8. How does PWM control motor speed? What resolution do you need for smooth control?
9. Explain the relationship between ADC resolution, reference voltage, and measurement precision.
10. You need to read a temperature sensor every 100 ms via I2C. Describe your approach using DMA and a timer.