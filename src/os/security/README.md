# OS Security

## Overview

Operating system security encompasses the mechanisms and policies that protect the system's resources — memory, files, devices, and processes — from unauthorized access, misuse, and attacks. The OS is the foundation of system security; if the OS is compromised, everything above it is vulnerable.

## Motivation

Why is OS security critical?

1. **Multi-user isolation**: Multiple users share the same system; the OS must prevent one user from accessing another's data.
2. **Malicious software**: Viruses, rootkits, and exploits attempt to subvert the OS to gain unauthorized access.
3. **Confidentiality**: Sensitive data (passwords, financial records) must be protected from unauthorized reading.
4. **Integrity**: System files and user data must not be tampered with.
5. **Availability**: The system must remain functional even under attack (DoS prevention).

## Security Threats

```
┌──────────────────────────────────────────────────────────────┐
│                    OS Security Threats                        │
│                                                              │
│  ┌──────────────────┐  ┌──────────────────┐  ┌────────────┐ │
│  │  Unauthorized    │  │  Privilege       │  │  Denial of │ │
│  │  Access          │  │  Escalation      │  │  Service   │ │
│  ├──────────────────┤  ├──────────────────┤  ├────────────┤ │
│  │ • Reading files  │  │ • Buffer overflow│  │ • Fork bomb│ │
│  │ • Accessing      │  │ • Kernel exploit │  │ • Resource │ │
│  │   other users'   │  │ • Setuid abuse   │  │   exhaust  │ │
│  │   data           │  │ • Race condition │  │ • CPU hog  │ │
│  │ • Eavesdropping  │  │ • Symlink attack │  │ • Memory   │ │
│  │   network        │  │ • TOCTOU         │  │   leak     │ │
│  └──────────────────┘  └──────────────────┘  └────────────┘ │
│                                                              │
│  ┌──────────────────┐  ┌──────────────────┐  ┌────────────┐ │
│  │  Code Injection  │  │  Information     │  │  Insider   │ │
│  │                  │  │  Leakage         │  │  Threat    │ │
│  ├──────────────────┤  ├──────────────────┤  ├────────────┤ │
│  │ • Buffer overflow│  │ • Side channels  │  │ • Malicious│ │
│  │ • Shellcode      │  │ • Spectre/       │  │   admin    │ │
│  │ • ROP chains     │  │   Meltdown       │  │ • Accidental│ │
│  │ • Format string  │  │ • Log exposure   │  │   data leak│ │
│  └──────────────────┘  └──────────────────┘  └────────────┘ │
└──────────────────────────────────────────────────────────────┘
```

## Security Principles

### Principle of Least Privilege

Every process should have the minimum privileges necessary to perform its function. A web server doesn't need access to `/etc/shadow`.

### Defense in Depth

Multiple layers of security — if one fails, others provide protection:
```
┌─────────────────────────────────────┐
│  Application Security               │  ← Input validation
├─────────────────────────────────────┤
│  OS Access Control (DAC/MAC)        │  ← File permissions, SELinux
├─────────────────────────────────────┤
│  Kernel Hardening                   │  ← ASLR, DEP, stack canaries
├─────────────────────────────────────┤
│  Hardware Security                  │  ← NX bit, TPM, secure boot
└─────────────────────────────────────┘
```

### Fail-Safe Defaults

Default to deny access. Access must be explicitly granted.

### Economy of Mechanism

Keep security mechanisms simple and small — easier to audit and less likely to have bugs.

### Complete Mediation

Every access must be checked. No caching of access decisions that could become stale.

## Topics in This Chapter

| Topic | Description |
|-------|-------------|
| [Access Control](access-control.md) | DAC, MAC, RBAC models |
| [Capabilities](capabilities.md) | Linux capabilities system |
| [SELinux](selinux.md) | Security-Enhanced Linux |

## Security Mechanisms Overview

```
┌──────────────────────────────────────────────────────────────┐
│              Linux Security Stack                              │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐    │
│  │  Traditional Unix Security                            │    │
│  │  • Owner/Group/Other permissions (rwx)                │    │
│  │  • UID/GID-based access control                       │    │
│  │  • setuid/setgid bits                                 │    │
│  └──────────────────────────────────────────────────────┘    │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐    │
│  │  Linux Capabilities                                   │    │
│  │  • Split root privileges into fine-grained units      │    │
│  │  • CAP_NET_ADMIN, CAP_SYS_PTRACE, etc.               │    │
│  └──────────────────────────────────────────────────────┘    │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐    │
│  │  LSM (Linux Security Modules) Framework               │    │
│  │  ┌────────┐  ┌────────┐  ┌────────┐  ┌────────┐     │    │
│  │  │ SELinux│  │AppArmor│  │Smack   │  │ Tomoyo │     │    │
│  │  │  (MAC) │  │(path-  │  │(label) │  │(domain)│     │    │
│  │  │        │  │ based) │  │        │  │        │     │    │
│  │  └────────┘  └────────┘  └────────┘  └────────┘     │    │
│  └──────────────────────────────────────────────────────┘    │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐    │
│  │  Kernel Hardening                                     │    │
│  │  • ASLR (Address Space Layout Randomization)          │    │
│  │  • DEP/NX (Data Execution Prevention)                 │    │
│  │  • Stack canaries (StackGuard/ProPolice)              │    │
│  │  • SMEP/SMAP (Supervisor Mode Execution/Access Prot.) │    │
│  │  • KASLR (Kernel ASLR)                                │    │
│  │  • seccomp (syscall filtering)                        │    │
│  └──────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────┘
```

## Quick Revision

- **DAC**: Owner-based permissions, can be overridden by owner
- **MAC**: Policy-based, even root can't override
- **Capabilities**: Fine-grained root privilege splitting
- **SELinux**: Label-based MAC enforcement
- **ASLR**: Randomize memory layout to prevent exploits
- **DEP/NX**: Mark memory non-executable to prevent code injection
- **seccomp**: Restrict which syscalls a process can make

## Cross-References

- [Access Control](access-control.md) — DAC, MAC, RBAC in detail
- [Capabilities](capabilities.md) — Linux capabilities deep dive
- [SELinux](selinux.md) — SELinux architecture and usage


## Cross References

- [Access Control](../os/security/access-control.md)
- [Capabilities](../os/security/capabilities.md)
- [SELinux](../os/security/selinux.md)
- [Namespaces](../os/containers/namespaces.md)
