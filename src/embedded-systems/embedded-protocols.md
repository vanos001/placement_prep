# Embedded Communication Protocols: I2C, SPI, UART, CAN, Modbus, 1-Wire

Embedded systems don't talk to each other the way servers do. There is no TCP, no kernel socket layer, no stack taller than a few hundred bytes. Instead, microcontrollers exchange bytes over short, specialized serial buses — each one tuned to a particular trade-off between wire count, speed, distance, noise immunity, addressing scheme, and silicon cost. This page covers the six protocols that show up again and again in real hardware: **I2C**, **SPI**, **UART**, **CAN**, **Modbus**, and **1-Wire** — their electrical, framing, and arbitration layers; real code to drive them; and a decision rubric for picking one.

For higher-level protocol coverage (MQTT, CoAP, BLE) see [IoT](./iot.md); for peripheral-register access patterns see [Peripherals](./peripherals.md).

> **Interview one-liner:** "I2C is a 2-wire open-drain bus with 7-bit addresses and ACK/NAK per byte; SPI is a 4-wire master-slave bus with one chip select per slave and 4 clock-mode (CPOL/CPHA) choices; UART is async point-to-point with a pre-agreed baud rate; CAN is differential with bitwise arbitration by ID (lowest ID wins); Modbus is a master-slave RTU-over-RS-485 or TCP protocol with function codes; 1-Wire uses a single open-drain data line with parasitic power."

## I2C (Inter-Integrated Circuit)

### Electrical and topology

I2C is a **multi-master, half-duplex, open-drain** bus using two wires: **SDA** (data) and **SCL** (clock). Both lines are pulled high by pull-up resistors (typically 4.7 kΩ for 100 kHz, 1–2 kΩ for 400 kHz) and actively driven low by the talker of the moment. Because no device ever drives the line high, there is no electrical contention — if two devices speak at once the result is simply "the bus goes low," which the protocol turns into a collision-detection and arbitration mechanism.

```
   Vcc
    |
   [R] 4.7k (SDA)        +--[R] 4.7k (SCL)--+ Vcc
    |                    |
    +---+---+---+-------+---+---+---+
        |   |   |           |   |
       M1  M2  S1          S2  S3   (master/slave are equal on the wire)
```

A transaction begins with a master driving SDA low while SCL is high (a **START condition** — impossible to confuse with normal data, because data changes only while SCL is low). The master then clocks 7 address bits and an R/W bit; the addressed slave replies with **ACK** (pulling SDA low during the 9th clock cycle) or **NAK** (leaving it high). Data bytes follow the same 8-bits-plus-ACK pattern. The master ends the transaction with a **STOP condition** — SDA rising while SCL is high.

### Addressing

I2C uses 7-bit addresses (`0x00`–`0x7E`; several are reserved). The 8th bit of the address byte is R/W. With 7-bit addresses you can theoretically have 112 devices on one bus. 10-bit addressing extends this when an address byte starts with `0b11110xx`.

I2C is a true multi-master bus. Arbitration works because of the open-drain topology: every master samples SDA after driving it. If a master writes a `1` but reads `0`, it knows another master is transmitting a `0` and yields. The winner is the lowest address being transmitted — a perfect priority-by-address scheme with no bandwidth loss on collision. The same wired-AND mechanism gives **clock synchronization**: every master drives SCL low for its low-time and the bus stays low until the longest low-time expires. Slaves can also do **clock stretching** — holding SCL low to slow down a too-fast master. Some controllers implement this poorly (notably older STM32 revisions), so check the errata.

### Speeds

| Mode | Bit rate | Notes |
|---|---|---|
| Standard | 100 kHz | Original 1982 spec |
| Fast | 400 kHz | Most common |
| Fast Plus | 1 MHz | Tighter rise-time budget; lower pull-ups |
| High Speed | 3.4 MHz | Requires active pull-up drivers, special signaling |
| Ultra Fast | 5 MHz | Push-pull, unidirectional, no ACK |

### Code: reading a sensor over I2C (STM32 HAL)

```c
#define LSM6DSL_ADDR   (0x6A << 1)        /* 7-bit addr shifted left; R/W in bit 0 */
#define WHO_AM_I_REG   0x0F

HAL_StatusTypeDef status;
uint8_t reg = WHO_AM_I_REG;
uint8_t id;

/* Send the register pointer, then re-START and read one byte. */
status = HAL_I2C_Master_Transmit(&hi2c1, LSM6DSL_ADDR, &reg, 1, 100);
if (status != HAL_OK) return status;
status = HAL_I2C_Master_Receive(&hi2c1, LSM6DSL_ADDR, &id, 1, 100);
/* id should be 0x6A for the LSM6DSL */
```

On Linux the same call is one `ioctl(I2C_RDWR)` against `/dev/i2c-1` with two `struct i2c_msg` entries (write-the-register, read-the-value), but the framing model is identical.

### Common pitfalls

- **Address confusion**: manufacturers quote 7-bit addresses, but the STM32 HAL expects them left-shifted by 1 (the R/W bit goes in bit 0). Many bug reports are just this mismatch.
- **Pull-up sizing**: compute from bus capacitance (50–400 pF) and target rise time (≤ 300 ns for 400 kHz); too small wastes current, too large prevents reaching `Vih` before the next clock.
- **Stuck bus**: a slave holding SDA low (e.g. after a reset mid-transaction) hangs the bus. Recovery is to clock SCL nine times and send a STOP.

## SPI (Serial Peripheral Interface)

### Topology and signaling

SPI is **full-duplex, master-slave, single-master (typically)** over four wires:

- **SCLK** — clock, generated by master
- **MOSI** (Master Out, Slave In) — data from master to slave
- **MISO** (Master In, Slave Out) — data from slave to master
- **CS/SS** (Chip Select / Slave Select) — active-low, one per slave

```
                SCLK --------+----+----+----+
                MOSI --+---->|    |>    |>   |
                MISO <----+--+----+----+----+
                 CS0 --------'
                 CS1 -----------'
                 CS2 --------------'
                 CS3 -----------------'
                          Slave0  Slave1  Slave2  Slave3
```

There is **no addressing** — selection is by chip select. The master clocks data out on MOSI on one edge of SCLK and reads data in on MISO on the other edge. After 8 clocks a byte has been exchanged.

### Four clock modes (CPOL, CPHA)

SPI has **no inherent framing** beyond the byte — the contract between master and slave is set by two configuration bits:

| Mode | CPOL | CPHA | Idle SCLK | Sample edge |
|---|---|---|---|---|
| 0 | 0 | 0 | Low | Rising (leading) |
| 1 | 0 | 1 | Low | Falling (trailing) |
| 2 | 1 | 0 | High | Falling (leading) |
| 3 | 1 | 1 | High | Rising (trailing) |

CPOL sets SCLK idle polarity; CPHA selects which edge samples data. The slave's datasheet specifies the required mode. Most modern sensors use Mode 0 or Mode 3. Getting this wrong gives plausible-looking data with off-by-one bit shifts — one of the more exasperating SPI bugs.

### Speeds and lengths

SPI is fast — typically 1–50 MHz, with some controllers reaching 100+ MHz. As a synchronous protocol, length is limited by **clock skew**: the round-trip time of SCLK→slave→MISO must be less than one clock period. At 50 MHz that's 20 ns, so the bus is board-level only (~10 cm). Longer runs need slower clocks.

### Code: SPI transfer (STM32 HAL)

```c
#define MAX31855_BUF 4

uint8_t tx[MAX31855_BUF] = { 0, 0, 0, 0 };
uint8_t rx[MAX31855_BUF];

HAL_GPIO_WritePin(GPIOA, GPIO_PIN_4, GPIO_PIN_RESET);   /* CS low */
HAL_SPI_TransmitReceive(&hspi1, tx, rx, MAX31855_BUF, 100);
HAL_GPIO_WritePin(GPIOA, GPIO_PIN_4, GPIO_PIN_SET);     /* CS high  */

/* rx[0..3] now holds 32-bit thermocouple reading from MAX31855 */
```

The `CS low → exchange → CS high` sequence *is* the SPI transaction. Some slaves (e.g. ADCs) want CS toggled between bytes; others (Flash) hold CS low for the whole command+address+data sequence. The datasheet decides.

Modern variants like **Quad SPI (QSPI)** and **Octal SPI (OSPI)** add 4 or 8 data lines for high-throughput flash in modern SoCs, but the framing model is unchanged — extra pins, same protocol.

## UART (Universal Asynchronous Receiver-Transmitter)

UART is **asynchronous, full-duplex, point-to-point** over two signal lines (**TX** and **RX**), with no shared clock. Both ends agree on a baud rate; the receiver re-synchronizes on each start bit.

### Framing

A UART frame:

```
   idle ----| s | d0 | d1 | d2 | d3 | d4 | d5 | d6 | d7 | p | stop |
            start   <-----  data bits  ----->      parity  stop
```

- **Start bit** — one bit time at logic 0, falling edge signals frame start.
- **Data bits** — 5 to 9 bits, LSB first by convention.
- **Parity bit** — optional: even, odd, mark, space, or none.
- **Stop bit(s)** — one or two bit times at logic 1, ensures the line returns to idle before the next frame's start edge.

The "8N1" frame is the universal default: 8 data bits, no parity, 1 stop bit.

### Baud rate

The baud rate is the bit rate in bps. Common rates: 9600, 19200, 38400, 57600, 115200, 230400, 460800, 921600, 1 Mbaud, 3 Mbaud. The receiver samples each bit at its midpoint, so a **baud-rate mismatch of more than ~2–3%** drifts the sample point past the bit boundary by the last data bit and causes framing errors. Pick a crystal whose frequency divides cleanly by your baud generator; classic 11.0592 MHz crystals for 8051s exist precisely because they divide evenly by both 9600 and 115200.

### Distance

UART alone is short-range — a few meters at most. To go further, the line is converted to differential signalling:

RS-232 is single-ended at ±12 V (good to ~15 m); RS-485 is differential (multi-drop, up to 32 unit loads, ~1200 m at 115200). RS-485 is the standard physical layer for industrial Modbus-RTU because it is noise-immune, multi-drop, and bus-capable.

### Code: DMA-driven UART receive ring

```c
#define RX_BUF_SIZE 256
uint8_t rx_buf[RX_BUF_SIZE];

/* Start DMA receive into the ring buffer. */
HAL_UART_Receive_DMA(&huart1, rx_buf, RX_BUF_SIZE);

/* In the IDLE-line interrupt, compute how many bytes arrived
   since the last check and feed them to your line parser. */
void HAL_UARTEx_RxEventCallback(UART_HandleTypeDef *huart, uint16_t size) {
    uint16_t head = RX_BUF_SIZE - __HAL_DMA_GET_COUNTER(huart->hdmarx);
    /* tail .. head is the new bytes. */
    consume(rx_buf, /*tail=*/g_tail, /*head=*/head);
    g_tail = head;
}
```

Idle-line detection plus DMA is the production-grade pattern for streaming UART protocols (Modbus-RTU, GPS NMEA, AT commands) — much lower CPU overhead than per-byte IRQ.

### Common pitfalls

- **Baud mismatch** shows up as `~` characters in the console (0x7E shifted by one bit).
- **Grounding** is mandatory; an isolated RS-485 transceiver fixes "ground lift" problems in industrial settings.
- **Overrun errors** when the receive ISR can't keep up — switch to DMA.

## CAN (Controller Area Network)

CAN is the **differential, multi-master, message-priority-bus** designed by Bosch in 1986 for automotive use. It is the only one of the six protocols here designed from scratch for *noise* and *determinism*.

### Electrical

CAN uses two wires, **CANH** and **CANL**, driven differentially. Two bus states exist:

- **Dominant** (logic 0) — CANH ≈ 3.5 V, CANL ≈ 1.5 V (2 V differential)
- **Recessive** (logic 1) — both ≈ 2.5 V (0 V differential)

The bus is a wired-AND: if *any* node drives dominant, the bus is dominant. Termination is 120 Ω at each end (a single 60 Ω measurement between CANH and CANL with the bus powered down indicates two terminators present).

```
   +120Ω ---[CANH]----+-----+-----+-----+---[CANH]--- 120Ω+
                     node1 node2 node3 node4
   +120Ω ---[CANL]----+-----+-----+-----+---[CANL]--- 120Ω+
```

### Arbitration

CAN arbitration is the genius of the protocol. Every frame starts with the **arbitration field** = 11-bit ID (Standard) or 29-bit (Extended) + RTR bit. When two nodes start transmitting simultaneously, each one transmits and reads back the bus. If a node writes a `1` (recessive) but reads `0` (dominant), it loses and stops. **The lowest ID wins** — so CAN IDs double as priorities. Higher-priority messages (e.g. brake command) get a low ID.

```
   Node A ID = 0x100:  0001 0000 0000   <-- wins
   Node B ID = 0x200:  0010 0000 0000   <-- bit 10 is 1 vs A's 0 → B backs off
```

This is **CSMA/CD+AMP** (Collision Detection + Arbitration on Message Priority). Crucially, *no* bandwidth is lost to the collision — the winner continues without retransmission. Contrast Ethernet, where a collision aborts both frames and both retry after a random backoff.

### Frame format

A standard data frame:

```
| SOF | 11-bit ID | RTR | IDE | r0 | DLC | 0..8 data bytes | CRC | CRC delim | ACK | ACK delim | EOF |
   1     11        1     1     1    4    0..64 bits          15    1           1    1            7
```

- **SOF** — start of frame, 1 dominant bit.
- **Arbitration field** — ID + RTR (Remote Transmission Request; RTR=1 means "request data" with no payload).
- **Control** — IDE (Identifier Extension, 0=standard 11-bit), r0 reserved, DLC (0–8 bytes).
- **Data** — 0–8 bytes (64 bytes in CAN FD).
- **CRC** — 15-bit CRC + 1-bit delimiter.
- **ACK** — sender writes recessive; any node that received correctly writes dominant. If the ACK bit is read as recessive, the sender knows no one acknowledged (ACK error).
- **EOF** — 7 recessive bits.

**Bit stuffing**: after five consecutive same-polarity bits, the sender inserts one opposite-polarity bit. This guarantees enough transitions for PLL clock recovery. Bit-stuffed frames are destuffed by the receiver.

### CAN FD

**CAN FD** (Flexible Data-rate) extends classical CAN: payload up to 64 bytes, two bit-rate phases (arbitration at standard 1 Mbps, data phase at up to 5–8 Mbps), and a stronger 17/21-bit CRC. CAN FD is backward-incompatible at the protocol level but coexists on the wire with classical CAN frames.

### Code: filter setup + transmit (STM32 HAL)

```c
CAN_FilterTypeDef filter = {
    .FilterIdHigh = 0, .FilterIdLow = 0,
    .FilterMaskIdHigh = 0, .FilterMaskIdLow = 0,
    .FilterFIFOAssignment = CAN_RX_FIFO0,
    .FilterBank = 0,
    .FilterMode = CAN_FILTERMODE_IDMASK,
    .FilterScale = CAN_FILTERSCALE_32BIT,
    .FilterActivation = ENABLE,
};
HAL_CAN_ConfigFilter(&hcan1, &filter);
HAL_CAN_Start(&hcan1);

CAN_TxHeaderTypeDef tx = {
    .StdId = 0x123, .IDE = CAN_ID_STD,
    .RTR = CAN_RTR_DATA, .DLC = 8,
};
uint8_t data[8] = { 1, 2, 3, 4, 5, 6, 7, 8 };
uint32_t mailbox;
HAL_CAN_AddTxMessage(&hcan1, &tx, data, &mailbox);
```

Filter banks let the controller reject unwanted IDs *in hardware* before they hit the CPU — important on a busy automotive bus where only a few IDs matter to your ECU.

## Modbus

**Modbus** (Modicon, 1979) is a **master-slave, request-response** protocol layered over either UART+RS-485 (**Modbus RTU**) or TCP (**Modbus TCP**). It is the lingua franca of industrial PLCs, energy meters, drives, and process sensors.

### Frame format (RTU)

```
+-----------+----------------+--------+----------+
| Slave Addr| Function Code  | Data   | CRC-16   |
| (1 byte)  | (1 byte)       | (var)  | (2 byte) |
+-----------+----------------+--------+----------+
```

Frame boundaries are demarcated by **silence**: a gap of ≥ 3.5 character times ends a frame. This is why idle-line detection on UART is essential for Modbus-RTU. A 9600-baud frame with 8N1 needs ~4 ms of silence to mark the boundary.

### Common function codes

| FC | Name | Operation |
|----|------|-----------|
| 01 | Read Coils | Read N boolean outputs (relay coils) |
| 02 | Read Discrete Inputs | Read N boolean inputs (read-only) |
| 03 | Read Holding Registers | Read N 16-bit read/write registers |
| 04 | Read Input Registers | Read N 16-bit read-only registers |
| 05 | Write Single Coil | Write one boolean |
| 06 | Write Single Register | Write one 16-bit register |
| 15 | Write Multiple Coils | Write N booleans |
| 16 | Write Multiple Registers | Write N 16-bit registers |
| 23 | Read/Write Multiple Registers | Atomic read+write |

The function-code space is small and well-defined; that is its strength. The data model is a simple four-table view: **coils** (read/write booleans), **discrete inputs** (read-only booleans), **holding registers** (read/write 16-bit), **input registers** (read-only 16-bit). Every device maps its parameters into these tables at fixed addresses documented in the device's Modbus map.

### Modbus TCP

Modbus TCP replaces the serial framing with a TCP packet on port 502. A 7-byte MBAP header replaces the slave address+CRC: transaction ID (2) + protocol ID (2) + length (2) + unit ID (1). CRC is dropped — TCP already guarantees integrity. The Unit ID routes to a slave behind a TCP-to-RTU gateway. Modbus TCP is the cheapest way to expose an industrial device to an IT network, which is both its appeal and its security hazard (no authentication, no encryption by default).

### Code: read holding registers with pymodbus

```python
from pymodbus.client import ModbusTcpClient

c = ModbusTcpClient('192.168.1.50', port=502)
c.connect()
rr = c.read_holding_registers(address=0x00, count=4, slave=1)
if rr.isError():
    print("Modbus error:", rr)
else:
    print("registers:", rr.registers)
c.close()
```

For RTU replace `ModbusTcpClient` with `ModbusSerialClient(method='rtu', port='/dev/ttyUSB0', baudrate=9600, timeout=1)`.

Modbus has **no security model**. Modbus TCP should never be exposed to the open Internet; production deployments use gateway devices that wrap Modbus in TLS or VPN tunnels.

## 1-Wire

**1-Wire** (Dallas/Maxim, late 1980s) is a **single-data-wire bus with parasitic power**. One pin (plus ground) suffices for both signaling and powering small devices like the DS18B20 temperature sensor or iButton.

### Electrical and timing

The bus is open-drain with a 4.7 kΩ pull-up. The master drives the line low to signal a "low" bit or to start a timing slot. To signal a `1` the master releases the line and the pull-up brings it high. Devices draw power from the data line during the high periods, storing charge on an internal capacitor to ride through the low periods — this is **parasitic power**.

Timing is critical: a write-1 slot is 6 µs low followed by 64 µs of release; a write-0 slot is 60 µs low followed by 10 µs release; a read slot is 1 µs low pulse from the master, then the slave holds low (0) or releases (1) within a 15 µs sampling window.

### Addressing and discovery

Every 1-Wire device ships with a factory-lasered **64-bit ROM address** containing 8-bit family code + 48-bit serial + 8-bit CRC. The discovery protocol (**Search ROM**) uses the same arbitration trick as CAN: the master asks every device to send bit N and then its complement; if they differ, the master picks one branch and remembers the conflict point for the next iteration. The full discovery of N devices on a bus takes ~75 ms of bit-banging.

### Code: bit-bang reset + write/read

```c
int ow_reset(void) {
    int presence;
    PIN_OUTPUT();  PIN_LOW();          /* pull bus low */
    delay_us(480);
    PIN_INPUT();                         /* release                       */
    delay_us(70);
    presence = !PIN_READ();              /* slave pulls low = presence    */
    delay_us(410);
    return presence;
}

void ow_write_bit(int bit) {
    PIN_OUTPUT();  PIN_LOW();
    if (bit) {
        delay_us(6);   PIN_INPUT();   delay_us(64);   /* write-1 slot */
    } else {
        delay_us(60); PIN_INPUT();   delay_us(10);   /* write-0 slot */
    }
}

int ow_read_bit(void) {
    int bit;
    PIN_OUTPUT(); PIN_LOW();
    delay_us(1);
    PIN_INPUT();
    delay_us(14);
    bit = PIN_READ();
    delay_us(45);
    return bit;
}
```

Once you can read and write bits, byte-level primitives are eight calls. The DS18B20 temperature conversion is: `reset` → `Skip ROM (0xCC)` → `Convert T (0x44)` → wait 750 ms → `reset` → `Skip ROM` → `Read Scratchpad (0xBE)` → read 9 bytes (CRC-8 verified).

Use 1-Wire when a single GPIO is all you can spare (e.g. one-wire temperature sensing on a fan). It loses on bandwidth (15 kbps max), tight bit-bang timing is fragile on top of an RTOS without disabling interrupts, and the protocol is single-master only.

## Comparison & When To Use Each

| Protocol | Wires | Max speed | Distance | Topology | Power | Multi-master | Std cost |
|---|---|---|---|---|---|---|---|
| **I2C** | 2 | 3.4 MHz | ~1 m | Bus | External pull-ups | Yes | Low |
| **SPI** | 4 + 1/slave | 50+ MHz | <1 m | Star (per CS) | Through master | No | Lowest |
| **UART** | 2 (+GND) | 3 Mbaud | 15 m (RS-232), 1200 m (RS-485) | P2P (RS-485 multidrop) | External | No | Low |
| **CAN** | 2 | 1 Mbps (classical), 8 Mbps (FD) | 40 m @ 1 Mbps, 1 km @ 50 kbps | Bus (differential) | External | Yes (with arbitration) | Medium (transceiver cost) |
| **Modbus** | over UART/TCP | baud-rate / 100Mb TCP | per UART/TCP | Master-slave | External | No (master only) | Medium |
| **1-Wire** | 1 (+GND) | 15 kbps | 100 m | Bus | Parasitic | No | Lowest |

### Decision rubric

```
How many wires can you spare?
|
+-- 1 wire only ----------------------------------------------------- 1-Wire
|
+-- 2 wires, on-board chips, multi-master ---------------------------- I2C
|
+-- 2 wires, long distance, multi-drop industrial --------------------- RS-485 + Modbus RTU
|
+-- 3+ wires, very fast, on-board, single master -------------------- SPI
|
+-- 2 wires, asynchronous, debug console / one-to-one -------------- UART
|
+-- 2 wires, noisy, deterministic priority, automotive/industrial -- CAN
|
+-- Ethernet/IP available, IT integration --------------------------- Modbus TCP (with TLS)
```

Real systems mix them. A modern automotive ECU might have CAN to the body network, LIN to the wipers, SPI to its accelerometer, I2C to its EEPROM and PMIC, UART to a debug console, and 1-Wire to a single battery-thermometer chip. The art is picking the simplest protocol that meets the noise, distance, and determinism requirements of each link.

## References

- [NXP/Philips I2C Specification (UM10204 v7.1)](https://www.nxp.com/docs/en/user-guide/UM10204.pdf) — the authoritative I2C spec, including 10-bit addressing, Fast Plus, Hs, and Ultra Fast modes.
- [Motorola MC68HC11 Reference Manual, Section 8 (SPI)](https://www.nxp.com/files/microcontrollers/doc/ref_manual/M68HC11RM.pdf) — the original SPI documentation by Motorola; defines CPOL/CPHA, the four modes.
- [Bosch CAN Specification 2.0B](https://www.bosch-mobility.com/en/mobility/mobility-services/mobility-software/can/) — the canonical CAN 2.0A/B specification.
- [CiA 301 — CANopen application layer and communication profile](https://www.can-cia.org/standards/specifications/) — the CAN-in-Automation standard that builds a higher-level protocol on CAN.
- [Modbus Application Protocol Specification V1.1b3 (Modbus Organization)](https://modbus.org/specs.php) — official RTU/ASCII/TCP framing and function-code definitions.
- [Modbus over Serial Line Specification V1.02](https://modbus.org/specs.php) — RTU framing, 3.5-char silence, CRC-16 polynomial.
- [Maxim Integrated (Analog Devices) Application Note 126 — 1-Wire Search Algorithm](https://www.analog.com/en/resources/technical-articles/appnote-an126.html) — the canonical walk-through of the 1-Wire Search ROM algorithm.
- [Texas Instruments SLLA270 — RS-485 Design Guide](https://www.ti.com/lit/an/slla270/slla270.pdf) — termination, failsafe biasing, multi-drop topologies.
- [Embedded.com — "I2C, SPI, UART demystified" (Jack Ganssle)](https://www.embedded.com/i2c-spi-uart-demystified/) — practical perspective from one of the long-time embedded columnists.

## Interview Questions

1. **Why does I2C require pull-up resistors but SPI does not?**
   I2C uses open-drain outputs: no device ever drives the line high; pull-ups do. This gives wired-AND behavior, which is what makes I2C multi-master arbitration and clock synchronization work. SPI uses push-pull outputs and a single-master model; the master's driver pulls high or low directly, so no pull-up is needed (and one would actually slow the rise time and reduce achievable speed).

2. **Explain I2C arbitration. What happens if two masters start a transaction at the same time?**
   Each master transmits and reads back SDA. When a master writes a 1 (recessive) but reads a 0 (dominant), it has lost arbitration and stops. The winner is the lowest address currently being transmitted — i.e. arbitration is by message address, with no collision bandwidth loss. The loser waits for STOP and retries.

3. **What are the four SPI modes? How do you pick one?**
   CPOL selects SCLK idle polarity; CPHA selects which edge samples data. The four combinations are modes 0–3. The slave's datasheet specifies the required mode — pick by matching. A symptom of a wrong mode is plausible-looking data with off-by-one bit shifts (e.g. reading 0x80 from a register that should read 0x01).

4. **Why does UART need a pre-agreed baud rate, and what is the maximum acceptable baud mismatch?**
   UART has no shared clock; the receiver re-synchronizes on each start bit and samples each subsequent bit at its midpoint. The cumulative drift over 10 bit times must stay within ±½ a bit. Practical tolerance is ±2–3% — beyond that, the last data bit is sampled outside its boundary and a framing error results. Crystals like 11.0592 MHz exist because they divide cleanly by common baud rates; an 8 MHz internal RC oscillator with ±5% drift will not reliably do 115200.

5. **How does CAN arbitration work? Why is there no collision-induced bandwidth loss?**
   CAN IDs also serve as priorities. When two nodes start transmitting, each compares its written bit to the read-back bus. If a recessive write (1) reads as dominant (0), the node has lost and stops. The lowest ID wins, and the winner keeps transmitting without restart — so the collision "lost" zero bandwidth. By contrast Ethernet CSMA/CD aborts both frames and retries with a random backoff, costing bandwidth on collision.

6. **What is bit-stuffing in CAN and why is it needed?**
   After 5 consecutive same-polarity bits, the sender inserts one opposite-polarity stuff bit. This guarantees enough transitions for the receiver's PLL to recover the clock. Without stuffing, a long run of 0s could cause clock drift and lose synchronization. Receivers de-stuff transparently; stuff bits do not appear in the CRC computation.

7. **Describe the Modbus-RTU frame format and how the receiver knows where one frame ends and the next begins.**
   Slave address (1 byte) + function code (1 byte) + data (variable) + CRC-16 (2 bytes). A frame is bounded by silence: ≥ 3.5 character times of idle on the line marks the end. The receiver uses an idle-line timeout interrupt to know "the frame is complete" before checking the CRC.

8. **How does the 1-Wire Search ROM algorithm discover all devices on a bus without prior knowledge of addresses?**
   The master sends Search ROM and reads two bits from each device: the true bit and its complement. (0,1) means all devices agree on that bit; (0,0) means a conflict — some devices have 0, some have 1. The master picks one branch (say 0), sends it back, and all devices with a 1 at that bit go silent. The master records the conflict point; on the next iteration it goes down the same branch up to that point then takes the other branch. After enough iterations all 64-bit addresses are enumerated. Arbitration uses the same wired-AND rule as CAN.

9. **You have a STM32, a DS18B20 temperature sensor, a SD card, an OLED display, a Bluetooth module, and a Linux host connected via RS-485. Pick protocols for each.**
   DS18B20 needs 1-Wire (it's the only thing the chip speaks). SD card needs SPI for full performance (or SDIO if the SoC has the controller). OLED display is typically I²C or SPI; pick I²C if pin count is tight, SPI for refresh rate. Bluetooth module (HC-05, nRF52) speaks UART AT commands. Linux host over RS-485 → UART to a transceiver (e.g. MAX485) running Modbus RTU. Total pin budget: 1 (1-Wire) + 4 (SPI) + 2 (I²C OLED) + 2 (UART BT) + 2 (UART/RS-485) = 11 pins, all on a single STM32G4 or L4.
