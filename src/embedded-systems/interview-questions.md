# Embedded Systems — Interview Questions

A curated collection of interview questions organized by difficulty, covering the full range of embedded systems topics.

## Beginner

1. **What is an embedded system?** Give three examples from your daily life.
2. **What is the difference between RAM and Flash memory on a microcontroller?** Why do MCUs need both?
3. **Explain GPIO.** How would you configure a pin as an output and toggle it?
4. **What is a register?** How does a program interact with hardware registers?
5. **What does `volatile` do in C?** Why is it important when programming hardware?
6. **What is an interrupt?** Describe the sequence of events when an interrupt fires.
7. **What is a baud rate?** How does it relate to UART communication?
8. **What is PWM?** Give a practical application.
9. **Explain the difference between a microcontroller and a microprocessor.**
10. **What is an ADC?** If you have a 12-bit ADC with a 3.3V reference, what is the smallest voltage change it can detect?

## Intermediate

11. **Compare SPI and I2C.** When would you choose one over the other? Consider speed, wiring complexity, and device count.
12. **What is DMA?** Describe a scenario where DMA significantly improves system performance.
13. **What is priority inversion?** Explain with a three-task example and describe how priority inheritance solves it.
14. **Why should ISRs be kept short?** What techniques can you use to defer processing?
15. **What is a watchdog timer?** How would you implement multi-task monitoring in an RTOS-based system?
16. **Explain memory-mapped I/O.** How does the CPU distinguish between a memory access and a peripheral register access?
17. **What is the NVIC?** How does it handle nested interrupts on Cortex-M?
18. **Describe the boot process on an ARM Cortex-M.** What are the first two values read from flash?
19. **What is a mutex in FreeRTOS?** How does it differ from a binary semaphore?
20. **What is a bootloader?** Describe a safe firmware update mechanism.

## Advanced

21. **Design a system that reads temperature from an I2C sensor every 100ms and sends it over UART.** Describe your task architecture, buffer management, and error handling in an RTOS.
22. **How would you implement OTA firmware updates for a battery-powered IoT device?** Address security, atomicity, power-loss recovery, and rollback.
23. **Explain how you would profile and optimize the power consumption of an embedded device.** What tools and techniques would you use?
24. **What is the worst-case interrupt latency on a Cortex-M4?** What factors affect it?
25. **Describe how you would implement a lock-free single-producer, single-consumer ring buffer** for passing data between an ISR and a task.
26. **You have a hard real-time system that must respond to an external event within 50µs.** How would you guarantee this deadline architecturally and verify it?
27. **What is tickless idle in FreeRTOS?** How does it work, and what are its limitations?
28. **Explain the ARM TrustZone security architecture.** How would you use it to protect firmware intellectual property and secure communication keys?
29. **Compare CAN bus arbitration to CSMA/CD (Ethernet).** Why is CAN better suited for real-time control systems?
30. **A field-deployed device is experiencing random reboots.** Walk through your debugging methodology from data collection to root cause analysis.

## Comparison Questions

31. **RTOS vs bare-metal**: When would you use each? What is the overhead of an RTOS context switch?
32. **Polling vs interrupt-driven I/O**: What are the trade-offs in terms of CPU usage, latency, and complexity?
33. **FreeRTOS heap schemes (heap_1 through heap_5)**: Which would you use for a safety-critical medical device?
34. **JTAG vs SWD**: Why does ARM recommend SWD for Cortex-M debugging?
35. **Cooperative vs preemptive scheduling**: What are the advantages of each in a hard real-time system?

## Common Traps

36. **"I'd use `malloc` to allocate memory dynamically."** → Embedded firmware typically avoids dynamic allocation. Explain why and describe alternatives.
37. **"I'd put a `printf` in the ISR to debug it."** → ISRs must be fast and non-blocking. `printf` can deadlock. Explain proper ISR debugging techniques.
38. **"A semaphore and a mutex are the same thing."** → They are not. A mutex has ownership semantics and priority inheritance. A semaphore does not.
39. **"I'll use a global variable to share data between the ISR and main loop."** → Without `volatile` and proper synchronization, the compiler may optimize away reads or reorder accesses.
40. **"I'll set all tasks to high priority for best responsiveness."** → This defeats the purpose of priority-based scheduling. Only truly time-critical tasks should be at the highest priority.