# Networking Vendor & Open-Source Reference Library

This page is a verified index of primary sources for computer networks: official documentation, developer and API portals, source repositories, SDKs, downloadable or offline documentation, a two-track learning path, and free-access research literature.

It is a **navigation layer**, not a tutorial. Where the rest of this book explains a concept, this page tells you which document to open to get the authoritative answer, and in what order to read things. Every link was HTTP-verified on the date shown below; sources that block automated checkers but work in a browser are flagged rather than silently dropped.

**196 vendors and projects** plus **196 education & reference-implementation resources**, across 18 categories — documentation, developer portals, GitHub orgs, SDKs, and downloadable/offline doc bundles.

Every link was HTTP-verified on **2026-10-07**. Direct PDF links were additionally verified by content-type.

> **Verification caveats.** Some sites return 403/406 to automated clients but load fine in a browser: Arista, Cisco, Juniper, Ciena, Dell, Huawei, Intel, Ericsson, Keysight, UfiSpace, Cacti, Aruba/HPE, Equinix, Allied Telesis, ui.com, APNIC Academy, NANOG. Two require a login (Mist API portal, Radware support) and return 401. The Ansible and Zeek documentation sites rate-limited our checker (429) rather than failing. savannah.nongnu.org and trex-tgn.cisco.com were unreachable from our network, so GitHub entry points are given for lwIP and TRex.

## Contents

- [1. Enterprise switching, routing & campus](#1-enterprise-switching-routing--campus) — 17
- [2. Cloud-managed networking, Wi-Fi & SMB](#2-cloud-managed-networking-wi-fi--smb) — 16
- [3. Service provider, optical, broadband & carrier](#3-service-provider-optical-broadband--carrier) — 12
- [4. Mobile, 5G core & RAN](#4-mobile-5g-core--ran) — 11
- [5. Network security, firewalls, ADC & SASE](#5-network-security-firewalls-adc--sase) — 14
- [6. Cloud, edge, CDN & overlay networks](#6-cloud-edge-cdn--overlay-networks) — 14
- [7. Whitebox NOS, silicon & DPUs](#7-whitebox-nos-silicon--dpus) — 8
- [8. DNS, DHCP, IPAM & source of truth](#8-dns-dhcp-ipam--source-of-truth) — 15
- [9. Monitoring, observability & telemetry](#9-monitoring-observability--telemetry) — 16
- [10. Test, measurement, simulation & labs](#10-test-measurement-simulation--labs) — 14
- [11. SDN, NFV & network orchestration](#11-sdn-nfv--network-orchestration) — 8
- [12. Cloud-native & Kubernetes networking](#12-cloud-native--kubernetes-networking) — 17
- [13. Routing daemons & protocol stacks](#13-routing-daemons--protocol-stacks) — 6
- [14. Packet capture, IDS/IPS & analysis](#14-packet-capture-idsips--analysis) — 9
- [15. Internet infrastructure, registries & standards](#15-internet-infrastructure-registries--standards) — 9
- [16. Vendor-neutral automation frameworks](#16-vendor-neutral-automation-frameworks) — 7
- [17. Embedded / router operating systems](#17-embedded--router-operating-systems) — 3
- [18. Education & reference implementations](#18-education--reference-implementations) — 196 (64 basic / 132 advanced)


## 1. Enterprise switching, routing & campus

### Arista Networks

- **Docs:** [arista.com/en/support/product-documentation](https://www.arista.com/en/support/product-documentation)
- **Developer / API:** [aristanetworks.github.io/cloudvision-apis](https://aristanetworks.github.io/cloudvision-apis/)
- **GitHub:** [github.com/aristanetworks](https://github.com/aristanetworks) • [github.com/arista-eosplus](https://github.com/arista-eosplus)
- **SDKs & repos:** pyeapi [github.com/arista-eosplus/pyeapi](https://github.com/arista-eosplus/pyeapi) • goeapi [github.com/aristanetworks/goeapi](https://github.com/aristanetworks/goeapi) • cloudvision-python [github.com/aristanetworks/cloudvision-python](https://github.com/aristanetworks/cloudvision-python) • AVD (Ansible) [github.com/aristanetworks/ansible-avd](https://github.com/aristanetworks/ansible-avd) + [avd.arista.com](https://avd.arista.com/)
- **Downloadable / offline:** Full EOS User Manual as PDF/ePub per release from the docs page (arista.com/assets/data/pdf/user-manual/um-books/)
- *Note:* TOI release notes: [arista.com/en/support/toi](https://www.arista.com/en/support/toi)

### Cisco Systems

- **Docs:** [developer.cisco.com/docs](https://developer.cisco.com/docs/)
- **Developer / API:** [developer.cisco.com](https://developer.cisco.com/)
- **GitHub:** [github.com/CiscoDevNet](https://github.com/CiscoDevNet)
- **SDKs & repos:** Code Exchange [developer.cisco.com/codeexchange](https://developer.cisco.com/codeexchange/) • pyATS/Genie [github.com/CiscoTestAutomation](https://github.com/CiscoTestAutomation) • ACI/DC [github.com/datacenter](https://github.com/datacenter) • NX-OS [developer.cisco.com/docs/nx-os](https://developer.cisco.com/docs/nx-os/) • Terraform ACI [registry.terraform.io/providers/…](https://registry.terraform.io/providers/CiscoDevNet/aci/latest/docs)
- **Downloadable / offline:** Every doc page has a PDF button; product doc roots at [cisco.com/c/en/us/support/all-products.html](https://www.cisco.com/c/en/us/support/all-products.html)
- *Note:* Free always-on sandboxes: [developer.cisco.com/site/sandbox](https://developer.cisco.com/site/sandbox/)

### Juniper Networks

- **Docs:** [juniper.net/documentation](https://www.juniper.net/documentation/)
- **Developer / API:** [juniper.net/documentation/…](https://www.juniper.net/documentation/us/en/software/junos-pyez/)
- **GitHub:** [github.com/Juniper](https://github.com/Juniper)
- **SDKs & repos:** Junos PyEZ [github.com/Juniper/py-junos-eznc](https://github.com/Juniper/py-junos-eznc) • Ansible [github.com/juniper/ansible-junos-stdlib](https://github.com/juniper/ansible-junos-stdlib) • API ref [junos-pyez.readthedocs.io](https://junos-pyez.readthedocs.io/)
- **Downloadable / offline:** PDF per guide, e.g. PyEZ Developer Guide [juniper.net/documentation/…](https://www.juniper.net/documentation/us/en/software/junos-pyez/junos-pyez-developer/junos-pyez-developer.pdf) • Day One books (free PDFs) [juniper.net/documentation/en_US/day-one-books](https://www.juniper.net/documentation/en_US/day-one-books/)

### Nokia (SR OS / SR Linux)

- **Docs:** [documentation.nokia.com](https://documentation.nokia.com/)
- **Developer / API:** [network.developer.nokia.com](https://network.developer.nokia.com/)
- **GitHub:** [github.com/nokia](https://github.com/nokia) • [github.com/srl-labs](https://github.com/srl-labs)
- **SDKs & repos:** Learn SR Linux [learn.srlinux.dev](https://learn.srlinux.dev/) • container image [github.com/nokia/srlinux-container-image](https://github.com/nokia/srlinux-container-image) • NDK Python [github.com/nokia/srlinux-ndk-py](https://github.com/nokia/srlinux-ndk-py) • YANG [github.com/nokia/srlinux-yang-models](https://github.com/nokia/srlinux-yang-models) • SR OS gRPC [github.com/Nokia/sros-grpc-services](https://github.com/Nokia/sros-grpc-services) • Ansible [github.com/nokia/sros-ansible](https://github.com/nokia/sros-ansible)
- **Downloadable / offline:** SR Linux doc set [documentation.nokia.com/srlinux](https://documentation.nokia.com/srlinux/) • Nokia Infocenter [infocenter.nokia.com](https://infocenter.nokia.com/) (PDF bundles, login for some)
- *Note:* Also owns Infinera since 2025

### HPE Aruba Networking

- **Docs:** [arubanetworking.hpe.com/techdocs](https://arubanetworking.hpe.com/techdocs/)
- **Developer / API:** [developer.arubanetworks.com](https://developer.arubanetworks.com/)
- **GitHub:** [github.com/aruba](https://github.com/aruba) • [github.com/HPENetworking](https://github.com/HPENetworking)
- **SDKs & repos:** pyaoscx [github.com/aruba/pyaoscx](https://github.com/aruba/pyaoscx) • pycentral, pyclearpass, pyedgeconnect, pyafc, pyhpeuxi, pyhpesse • aoscxgo (Go) • Terraform + Ansible collections
- **Downloadable / offline:** PDF per guide on the TechDocs portal; HPE dev portal [developer.hpe.com](https://developer.hpe.com/)
- *Note:* Dev Hub mirror: [devhub.arubanetworks.com](https://devhub.arubanetworks.com/)

### Extreme Networks

- **Docs:** [documentation.extremenetworks.com](https://documentation.extremenetworks.com/)
- **Developer / API:** [developer.extremecloudiq.com](https://developer.extremecloudiq.com/)
- **GitHub:** [github.com/extremenetworks](https://github.com/extremenetworks)
- **SDKs & repos:** ExtremeCloud IQ OpenAPI + Python/Java/Go/JS/C# SDKs [github.com/extremenetworks/…](https://github.com/extremenetworks/ExtremeCloudIQ-OpenAPI-Specification) • EXOS_Apps [github.com/extremenetworks/EXOS_Apps](https://github.com/extremenetworks/EXOS_Apps)
- **Downloadable / offline:** PDF guides, e.g. Extreme API with Python [documentation.extremenetworks.com/api_python/…](https://documentation.extremenetworks.com/api_python/Extreme_API.pdf)
- *Note:* Docs home: [extremenetworks.com/support/documentation-home](https://www.extremenetworks.com/support/documentation-home)

### NVIDIA Networking (Mellanox / Cumulus)

- **Docs:** [docs.nvidia.com/networking-ethernet-software](https://docs.nvidia.com/networking-ethernet-software/)
- **Developer / API:** [networking-docs.nvidia.com/doca](https://networking-docs.nvidia.com/doca/)
- **GitHub:** [github.com/CumulusNetworks](https://github.com/CumulusNetworks) • [github.com/NVIDIA](https://github.com/NVIDIA)
- **SDKs & repos:** Cumulus Linux [docs.nvidia.com/networking-ethernet-software/…](https://docs.nvidia.com/networking-ethernet-software/cumulus-linux/) • ifupdown2 [github.com/CumulusNetworks/ifupdown2](https://github.com/CumulusNetworks/ifupdown2) • DOCA platform [github.com/NVIDIA/doca-platform](https://github.com/NVIDIA/doca-platform)
- **Downloadable / offline:** 'Download the User Guide' PDF link on each Cumulus Linux doc version • solutions docs [networking-docs.nvidia.com/…](https://networking-docs.nvidia.com/networking-solutions)
- *Note:* Docs-as-code repo: [github.com/CumulusNetworks/docs](https://github.com/CumulusNetworks/docs)

### Huawei (Enterprise Datacom)

- **Docs:** [support.huawei.com/enterprise/en/index.html](https://support.huawei.com/enterprise/en/index.html)
- **Developer / API:** [info.support.huawei.com/info-finder](https://info.support.huawei.com/info-finder/)
- **GitHub:** [github.com/HuaweiDatacomm](https://github.com/HuaweiDatacomm) • [github.com/Huawei](https://github.com/Huawei)
- **SDKs & repos:** Ansible / NETCONF / YANG collections under HuaweiDatacomm
- **Downloadable / offline:** PDF product docs via the enterprise support portal (free account)

### Dell Technologies (SmartFabric OS10)

- **Docs:** [infohub.delltechnologies.com](https://infohub.delltechnologies.com/)
- **Developer / API:** [dell.com/support/…](https://www.dell.com/support/kbdoc/en-us/000134326/networking-support)
- **GitHub:** [github.com/Dell-Networking](https://github.com/Dell-Networking) • [github.com/dell](https://github.com/dell)
- **SDKs & repos:** OS10 Ansible collections, SmartFabric automation
- **Downloadable / offline:** PDF manuals under dell.com/support/manuals per platform

### Alcatel-Lucent Enterprise

- **Docs:** [al-enterprise.com/en/support](https://www.al-enterprise.com/en/support)
- **GitHub:** [github.com/al-enterprise](https://github.com/al-enterprise)
- **SDKs & repos:** OmniSwitch AOS REST/CLI automation samples
- **Downloadable / offline:** PDF user guides on the support portal

### Allied Telesis

- **Docs:** [alliedtelesis.com/us/en/documents](https://www.alliedtelesis.com/us/en/documents)
- **GitHub:** [github.com/alliedtelesis](https://github.com/alliedtelesis)
- **SDKs & repos:** AlliedWare Plus Ansible modules
- **Downloadable / offline:** PDF command/config guides in the document library

### Edgecore Networks

- **Docs:** [edge-core.com](https://www.edge-core.com/)
- **GitHub:** [github.com/edge-core](https://github.com/edge-core)
- **SDKs & repos:** ONIE / SONiC / OcNOS images and build tooling
- **Downloadable / offline:** Datasheets + install guides per SKU
- *Note:* Leading whitebox ODM

### UfiSpace

- **Docs:** [ufispace.com](https://www.ufispace.com/)
- **SDKs & repos:** Whitebox cell-site / aggregation routers (DDC, SONiC)
- **Downloadable / offline:** Datasheets via product pages

### Pica8

- **Docs:** [pica8.com](https://www.pica8.com/)
- **Developer / API:** [docs.pica8.com](https://docs.pica8.com/)
- **SDKs & repos:** PicOS REST + Ansible
- **Downloadable / offline:** Online PicOS doc set

### Aviz Networks

- **Docs:** [aviznetworks.com](https://aviznetworks.com/)
- **SDKs & repos:** SONiC support services, ONES observability
- **Downloadable / offline:** Gated behind sales contact

### DENT

- **Docs:** [dent.dev](https://dent.dev/)
- **GitHub:** [github.com/dentproject](https://github.com/dentproject)
- **SDKs & repos:** dentOS [github.com/dentproject/dentOS](https://github.com/dentproject/dentOS) — Linux-kernel-native switch NOS (LF project)
- **Downloadable / offline:** GitHub docs tree
- *Note:* Retail/edge switching NOS

### ZTE

- **Docs:** [support.zte.com.cn](https://support.zte.com.cn/)
- **Developer / API:** [zte.com.cn/global/support.html](https://www.zte.com.cn/global/support.html)
- **GitHub:** [github.com/zte](https://github.com/zte)
- **SDKs & repos:** Limited public SDK presence
- **Downloadable / offline:** Login-gated PDF library


## 2. Cloud-managed networking, Wi-Fi & SMB

### Cisco Meraki

- **Docs:** [documentation.meraki.com](https://documentation.meraki.com/)
- **Developer / API:** [developer.cisco.com/meraki](https://developer.cisco.com/meraki/)
- **GitHub:** [github.com/meraki](https://github.com/meraki)
- **SDKs & repos:** Dashboard API SDKs in Python/Go/Ruby/JS, Postman collections, webhook templates
- **Downloadable / offline:** Printable doc pages; OpenAPI spec downloadable from the dev portal
- *Note:* Zero-gating, best-in-class REST docs

### Juniper Mist

- **Docs:** [juniper.net/documentation/product/us/en/mist](https://www.juniper.net/documentation/product/us/en/mist/)
- **Developer / API:** [api.mist.com/api/v1/docs/Home](https://api.mist.com/api/v1/docs/Home)
- **GitHub:** [github.com/mistsys](https://github.com/mistsys)
- **SDKs & repos:** mistapi Python [github.com/tmunzer/mistapi_python](https://github.com/tmunzer/mistapi_python) • examples [github.com/tmunzer/mist_library](https://github.com/tmunzer/mist_library) • open docs mirror [doc.mist-lab.fr](https://doc.mist-lab.fr/)
- **Downloadable / offline:** Juniper PDF doc sets for Mist Wired/Wireless Assurance
- *Note:* Official API ref requires login

### RUCKUS Networks (Belden)

- **Docs:** [docs.ruckus.cloud](https://docs.ruckus.cloud/)
- **Developer / API:** [docs.ruckus.cloud/api](https://docs.ruckus.cloud/api)
- **GitHub:** [support.ruckuswireless.com](https://support.ruckuswireless.com/)
- **SDKs & repos:** RUCKUS One public REST API docs; SmartZone/vSZ API guides on the support portal
- **Downloadable / offline:** PDF guides on support.ruckuswireless.com
- *Note:* CommScope → Vistance Networks (Jan 2026) → Belden (Jul 2026)

### Cambium Networks

- **Docs:** [support.cambiumnetworks.com](https://support.cambiumnetworks.com/)
- **Developer / API:** [cambiumnetworks.com/support](https://www.cambiumnetworks.com/support/)
- **GitHub:** [github.com/Cambiumnetworks](https://github.com/Cambiumnetworks)
- **SDKs & repos:** cnMaestro REST API, device API samples
- **Downloadable / offline:** PDF user guides per product family

### Ubiquiti

- **Docs:** [help.ui.com](https://help.ui.com/)
- **Developer / API:** [developer.ui.com](https://developer.ui.com/)
- **GitHub:** [github.com/Ubiquiti](https://github.com/Ubiquiti) • [github.com/ui](https://github.com/ui)
- **SDKs & repos:** UniFi Network API, Site Manager API, UniFi OS integrations
- **Downloadable / offline:** Datasheets & specs [ui.com/download](https://www.ui.com/download/) • [techspecs.ui.com](https://techspecs.ui.com/)

### MikroTik

- **Docs:** [help.mikrotik.com/docs](https://help.mikrotik.com/docs/)
- **GitHub:** [github.com/MikroTik](https://github.com/MikroTik)
- **SDKs & repos:** RouterOS REST API + binary API; strong community SDKs (librouteros, routeros-api)
- **Downloadable / offline:** Printable/exportable wiki pages

### NETGEAR

- **Docs:** [netgear.com/support/home/downloads](https://www.netgear.com/support/home/downloads)
- **SDKs & repos:** Insight cloud API (partner program)
- **Downloadable / offline:** Per-model PDF manuals + firmware in the download centre

### TP-Link / Omada

- **Docs:** [tp-link.com/us/support/download](https://www.tp-link.com/us/support/download/)
- **Developer / API:** [omadanetworks.com](https://www.omadanetworks.com/)
- **SDKs & repos:** Omada Controller Open API (documented in controller UI)
- **Downloadable / offline:** Per-model PDF user guides + firmware

### Zyxel

- **Docs:** [zyxel.com/global/en/support/download](https://www.zyxel.com/global/en/support/download)
- **SDKs & repos:** Nebula cloud API
- **Downloadable / offline:** PDF manuals + firmware in the download centre

### D-Link

- **Docs:** [support.dlink.com](https://support.dlink.com/)
- **SDKs & repos:** Nuclias cloud API
- **Downloadable / offline:** Per-model PDF manuals

### Peplink

- **Docs:** [peplink.com/support](https://www.peplink.com/support/)
- **SDKs & repos:** InControl 2 API, router REST API
- **Downloadable / offline:** PDF manuals + knowledge base

### Cradlepoint (Ericsson)

- **Docs:** [customer.cradlepoint.com](https://customer.cradlepoint.com/)
- **Developer / API:** [developer.cradlepoint.com](https://developer.cradlepoint.com/)
- **SDKs & repos:** NetCloud Manager REST API, SDK for on-router apps
- **Downloadable / offline:** PDF guides via the customer portal

### Digi International

- **Docs:** [docs.digi.com](https://docs.digi.com/)
- **GitHub:** [github.com/digidotcom](https://github.com/digidotcom)
- **SDKs & repos:** Digi Remote Manager APIs, XBee Python/Java libraries, ConnectCore BSPs
- **Downloadable / offline:** PDF user guides per product

### Teltonika Networks

- **Docs:** [wiki.teltonika-networks.com](https://wiki.teltonika-networks.com/)
- **Developer / API:** [wiki.teltonika-networks.com/view/Main_Page](https://wiki.teltonika-networks.com/view/Main_Page)
- **SDKs & repos:** RutOS JSON-RPC + REST API, RMS API; OpenWrt-based
- **Downloadable / offline:** Exportable wiki, PDF datasheets

### TIP OpenWiFi

- **Docs:** [telecominfraproject.com](https://telecominfraproject.com/)
- **Developer / API:** [github.com/Telecominfraproject](https://github.com/Telecominfraproject)
- **GitHub:** [github.com/Telecominfraproject](https://github.com/Telecominfraproject)
- **SDKs & repos:** Full open-source cloud controller + AP firmware [github.com/Telecominfraproject/…](https://github.com/Telecominfraproject/wlan-cloud-ucentral-deploy)
- **Downloadable / offline:** READMEs + OpenAPI specs in-repo
- *Note:* Disaggregated Wi-Fi stack

### Nile

- **Docs:** [nilesecure.com](https://nilesecure.com/)
- **SDKs & repos:** Docs gated behind customer portal


## 3. Service provider, optical, broadband & carrier

### Ciena

- **Docs:** [ciena.com/support](https://www.ciena.com/support)
- **Developer / API:** [ciena.com/products/mcp](https://www.ciena.com/products/mcp)
- **GitHub:** [github.com/ciena](https://github.com/ciena)
- **SDKs & repos:** MCP / Blue Planet REST APIs; ONOS & OpenDaylight contributions
- **Downloadable / offline:** PDF product docs via support portal

### Adtran (incl. ADVA)

- **Docs:** [adtran.com/en/products-and-services](https://www.adtran.com/en/products-and-services)
- **Developer / API:** [portal.adtran.com](https://portal.adtran.com/)
- **SDKs & repos:** Mosaic One / Ensemble orchestration APIs
- **Downloadable / offline:** PDF docs via the Adtran support portal
- *Note:* Merged with ADVA Optical 2022

### Ribbon Communications

- **Docs:** [ribboncommunications.com/global-services](https://ribboncommunications.com/global-services)
- **SDKs & repos:** Ribbon Analytics / SBC REST APIs
- **Downloadable / offline:** PDF docs via customer portal
- *Note:* Includes ECI optical transport

### Calix

- **Docs:** [calix.com](https://www.calix.com/)
- **SDKs & repos:** Calix Cloud APIs, SMx orchestration
- **Downloadable / offline:** PDF docs via Calix Support Cloud

### Harmonic

- **Docs:** [harmonicinc.com/technical-support](https://www.harmonicinc.com/technical-support/)
- **SDKs & repos:** cOS vCMTS / CableOS APIs
- **Downloadable / offline:** PDF docs via support portal

### Infinera

- **Docs:** [nokia.com/optical-networks](https://www.nokia.com/optical-networks/)
- **GitHub:** [github.com/infinera](https://github.com/infinera)
- **SDKs & repos:** Now part of Nokia — infinera.com 301s to Nokia Optical Networks
- **Downloadable / offline:** See Nokia
- *Note:* Acquisition closed 2025

### DriveNets

- **Docs:** [docs.drivenets.com](https://docs.drivenets.com/)
- **GitHub:** [github.com/DriveNets](https://github.com/DriveNets)
- **SDKs & repos:** Network Cloud / DNOS APIs
- **Downloadable / offline:** Online doc set

### Arrcus

- **Docs:** [arrcus.com](https://arrcus.com/)
- **GitHub:** [github.com/arrcus](https://github.com/arrcus)
- **SDKs & repos:** ArcOS docs are partner-gated

### RtBrick

- **Docs:** [rtbrick.com/docs](https://www.rtbrick.com/docs/)
- **SDKs & repos:** Fully open RBFS docs incl. REST/CTRLD API reference
- **Downloadable / offline:** Online doc set, printable
- *Note:* Unusually open for a carrier vendor

### IP Infusion

- **Docs:** [docs.ipinfusion.com](https://docs.ipinfusion.com/)
- **Developer / API:** [ipinfusion.com/support](https://www.ipinfusion.com/support/)
- **GitHub:** [github.com/ipinfusion](https://github.com/ipinfusion)
- **SDKs & repos:** OcNOS NETCONF/gNMI/REST
- **Downloadable / offline:** PDF doc bundles per OcNOS release

### Lumen

- **Docs:** [developer.lumen.com](https://developer.lumen.com/)
- **SDKs & repos:** Dynamic Connections / NaaS APIs
- **Downloadable / offline:** OpenAPI specs downloadable from the portal

### Equinix

- **Docs:** [developer.equinix.com](https://developer.equinix.com/)
- **Developer / API:** [developer.equinix.com/docs](https://developer.equinix.com/docs)
- **GitHub:** [github.com/equinix](https://github.com/equinix)
- **SDKs & repos:** Fabric & Metal Terraform providers, Go/Python SDKs
- **Downloadable / offline:** OpenAPI specs downloadable


## 4. Mobile, 5G core & RAN

### Ericsson

- **Docs:** [ericsson.com/en/developer](https://www.ericsson.com/en/developer)
- **GitHub:** [github.com/Ericsson](https://github.com/Ericsson)
- **SDKs & repos:** Ericsson Network Manager APIs, codebase incl. CodeChecker and other OSS
- **Downloadable / offline:** Partner-gated PDF product docs
- *Note:* Also owns Cradlepoint

### Samsung Networks

- **Docs:** [samsung.com/global/business/networks](https://www.samsung.com/global/business/networks/)
- **SDKs & repos:** vRAN / Core orchestration APIs (operator-gated)
- **Downloadable / offline:** Public whitepapers & datasheets

### Mavenir

- **Docs:** [mavenir.com](https://www.mavenir.com/)
- **GitHub:** [github.com/mavenir](https://github.com/mavenir)
- **SDKs & repos:** Cloud-native IMS/5GC, Open RAN components
- **Downloadable / offline:** Public whitepapers

### Rakuten Symphony

- **Docs:** [symphony.rakuten.com](https://symphony.rakuten.com/)
- **SDKs & repos:** Symworld platform APIs
- **Downloadable / offline:** Public solution briefs

### Open5GS

- **Docs:** [open5gs.org/open5gs/docs](https://open5gs.org/open5gs/docs/)
- **GitHub:** [github.com/open5gs/open5gs](https://github.com/open5gs/open5gs)
- **SDKs & repos:** Complete open-source 4G EPC + 5G Core (C), WebUI, Docker/K8s deploys
- **Downloadable / offline:** Full docs online, repo cloneable offline
- *Note:* Most-used open 5G core

### free5GC

- **Docs:** [free5gc.org](https://free5gc.org/)
- **Developer / API:** [free5gc.org/guide](https://free5gc.org/guide/)
- **GitHub:** [github.com/free5gc/free5gc](https://github.com/free5gc/free5gc)
- **SDKs & repos:** Go-based 5G Core (R15/R16), per-NF repos
- **Downloadable / offline:** Guide + wiki

### srsRAN

- **Docs:** [docs.srsran.com](https://docs.srsran.com/)
- **GitHub:** [github.com/srsran/srsRAN_Project](https://github.com/srsran/srsRAN_Project)
- **SDKs & repos:** Open-source 5G CU/DU/RU, srsRAN_4G, O-RAN compliant
- **Downloadable / offline:** PDF manual [docs.srsran.com/_/downloads/en/latest/pdf](https://docs.srsran.com/_/downloads/en/latest/pdf/)

### OpenAirInterface (OAI)

- **Docs:** [openairinterface.org](https://openairinterface.org/)
- **Developer / API:** [gitlab.eurecom.fr/oai/openairinterface5g](https://gitlab.eurecom.fr/oai/openairinterface5g)
- **GitHub:** [gitlab.eurecom.fr/oai/openairinterface5g](https://gitlab.eurecom.fr/oai/openairinterface5g)
- **SDKs & repos:** Full 4G/5G RAN + CN reference implementation (OSA)
- **Downloadable / offline:** In-repo docs, downloadable
- *Note:* Academic/industry reference stack

### Magma

- **Docs:** [magmacore.org](https://magmacore.org/)
- **Developer / API:** [docs.magmacore.org](https://docs.magmacore.org/)
- **GitHub:** [github.com/magma/magma](https://github.com/magma/magma)
- **SDKs & repos:** Open mobile core (LTE/5G) for access-agnostic deployments
- **Downloadable / offline:** Docs site + repo
- *Note:* Linux Foundation project

### O-RAN Software Community

- **Docs:** [docs.o-ran-sc.org](https://docs.o-ran-sc.org/)
- **GitHub:** [gerrit.o-ran-sc.org](https://gerrit.o-ran-sc.org/)
- **SDKs & repos:** Near-RT RIC, Non-RT RIC, xApps/rApps, O-DU/O-CU
- **Downloadable / offline:** Per-release doc sets on docs.o-ran-sc.org
- *Note:* LF + O-RAN Alliance

### UERANSIM

- **Docs:** [github.com/aligungr/UERANSIM](https://github.com/aligungr/UERANSIM)
- **Developer / API:** [github.com/aligungr/UERANSIM/wiki](https://github.com/aligungr/UERANSIM/wiki)
- **GitHub:** [github.com/aligungr/UERANSIM](https://github.com/aligungr/UERANSIM)
- **SDKs & repos:** Open-source 5G UE and gNB simulator
- **Downloadable / offline:** Wiki
- *Note:* Pairs with Open5GS/free5GC


## 5. Network security, firewalls, ADC & SASE

### Fortinet

- **Docs:** [docs.fortinet.com](https://docs.fortinet.com/)
- **Developer / API:** [fndn.fortinet.net](https://fndn.fortinet.net/)
- **GitHub:** [github.com/fortinet](https://github.com/fortinet)
- **SDKs & repos:** FortiOS Ansible & Terraform providers, fortiosapi (Python)
- **Downloadable / offline:** PDF download button on every doc.fortinet.com guide
- *Note:* FNDN API reference needs a free account

### Palo Alto Networks

- **Docs:** [docs.paloaltonetworks.com](https://docs.paloaltonetworks.com/)
- **Developer / API:** [pan.dev](https://pan.dev/)
- **GitHub:** [github.com/PaloAltoNetworks](https://github.com/PaloAltoNetworks)
- **SDKs & repos:** pan-os-python [github.com/PaloAltoNetworks/pan-os-python](https://github.com/PaloAltoNetworks/pan-os-python) • Terraform & Ansible providers • all OpenAPI specs open on pan.dev
- **Downloadable / offline:** PDF per guide, e.g. [docs.paloaltonetworks.com/pan-os/…](https://docs.paloaltonetworks.com/pan-os/11-1/pan-os-admin)
- *Note:* Arguably the best vendor dev portal in networking

### Check Point

- **Docs:** [sc1.checkpoint.com/documents/…](https://sc1.checkpoint.com/documents/latest/APIs/index.html)
- **GitHub:** [github.com/CheckPointSW](https://github.com/CheckPointSW)
- **SDKs & repos:** cp_mgmt Ansible collection, Terraform provider, cpapi Python
- **Downloadable / offline:** PDF admin guides via support.checkpoint.com

### F5

- **Docs:** [techdocs.f5.com](https://techdocs.f5.com/)
- **Developer / API:** [clouddocs.f5.com](https://clouddocs.f5.com/)
- **GitHub:** [github.com/F5Networks](https://github.com/F5Networks)
- **SDKs & repos:** f5-common-python (iControl REST), AS3 / Declarative Onboarding, Ansible + Terraform
- **Downloadable / offline:** PDF per guide on techdocs.f5.com

### NetScaler (Citrix)

- **Docs:** [docs.netscaler.com](https://docs.netscaler.com/)
- **Developer / API:** [developer-docs.netscaler.com](https://developer-docs.netscaler.com/)
- **GitHub:** [github.com/netscaler](https://github.com/netscaler) • [github.com/citrix](https://github.com/citrix)
- **SDKs & repos:** NITRO SDKs (Python/Java/.NET), Ansible collection, Terraform provider
- **Downloadable / offline:** PDF export on docs.netscaler.com

### A10 Networks

- **Docs:** [documentation.a10networks.com](https://documentation.a10networks.com/)
- **Developer / API:** [glm.a10networks.com](https://glm.a10networks.com/)
- **GitHub:** [github.com/a10networks](https://github.com/a10networks)
- **SDKs & repos:** acos-client (Python), Ansible collection, Terraform provider
- **Downloadable / offline:** PDF doc bundles per ACOS release
- *Note:* Support: [support.a10networks.com](https://support.a10networks.com/)

### Radware

- **Docs:** [support.radware.com](https://support.radware.com/)
- **GitHub:** [github.com/Radware](https://github.com/Radware)
- **SDKs & repos:** vDirect / Alteon REST automation
- **Downloadable / offline:** Login-gated PDFs

### Zscaler

- **Docs:** [help.zscaler.com](https://help.zscaler.com/)
- **Developer / API:** [help.zscaler.com/zia/api](https://help.zscaler.com/zia/api)
- **GitHub:** [github.com/zscaler](https://github.com/zscaler)
- **SDKs & repos:** zscaler-sdk-python, zscaler-sdk-go, Terraform & Ansible providers
- **Downloadable / offline:** Printable doc pages, OpenAPI specs

### Netskope

- **Docs:** [docs.netskope.com](https://docs.netskope.com/)
- **GitHub:** [github.com/netskopeoss](https://github.com/netskopeoss)
- **SDKs & repos:** REST API v2, Terraform provider, log shippers
- **Downloadable / offline:** Printable doc pages

### Cato Networks

- **Docs:** [api.catonetworks.com/documentation](https://api.catonetworks.com/documentation/)
- **GitHub:** [github.com/catonetworks](https://github.com/catonetworks)
- **SDKs & repos:** Public GraphQL API docs, Terraform provider, Python examples
- **Downloadable / offline:** GraphQL schema downloadable

### Versa Networks

- **Docs:** [docs.versa-networks.com](https://docs.versa-networks.com/)
- **GitHub:** [github.com/versa-networks](https://github.com/versa-networks)
- **SDKs & repos:** Director REST API, Ansible/Terraform samples
- **Downloadable / offline:** PDF guides

### Netgate (pfSense / TNSR)

- **Docs:** [docs.netgate.com/pfsense/en/latest](https://docs.netgate.com/pfsense/en/latest/)
- **Developer / API:** [docs.netgate.com/tnsr/en/latest](https://docs.netgate.com/tnsr/en/latest/)
- **GitHub:** [github.com/pfsense](https://github.com/pfsense) • [github.com/netgate](https://github.com/netgate)
- **SDKs & repos:** pfSense source; TNSR RESTCONF API
- **Downloadable / offline:** Docs are Sphinx — downloadable builds from the repo

### OPNsense

- **Docs:** [docs.opnsense.org](https://docs.opnsense.org/)
- **Developer / API:** [docs.opnsense.org/development/api.html](https://docs.opnsense.org/development/api.html)
- **GitHub:** [github.com/opnsense](https://github.com/opnsense)
- **SDKs & repos:** Full core source, documented REST API, Ansible collection
- **Downloadable / offline:** Sphinx docs, repo cloneable
- *Note:* Fully open source

### VyOS

- **Docs:** [docs.vyos.io/en/latest](https://docs.vyos.io/en/latest/)
- **Developer / API:** [docs.vyos.io/en/latest/automation](https://docs.vyos.io/en/latest/automation/)
- **GitHub:** [github.com/vyos](https://github.com/vyos)
- **SDKs & repos:** HTTP API, vyos.configsession, Ansible/Terraform
- **Downloadable / offline:** Sphinx docs; rolling ISO builds free
- *Note:* Open source router OS


## 6. Cloud, edge, CDN & overlay networks

### Cloudflare

- **Docs:** [developers.cloudflare.com](https://developers.cloudflare.com/)
- **Developer / API:** [developers.cloudflare.com/api](https://developers.cloudflare.com/api/)
- **GitHub:** [github.com/cloudflare](https://github.com/cloudflare)
- **SDKs & repos:** cloudflare-python, cloudflare-go, Terraform provider, Wrangler
- **Downloadable / offline:** Full OpenAPI schema downloadable from the API docs

### Akamai

- **Docs:** [techdocs.akamai.com](https://techdocs.akamai.com/)
- **Developer / API:** [techdocs.akamai.com/home/…](https://techdocs.akamai.com/home/page/products-tools-a-z)
- **GitHub:** [github.com/akamai](https://github.com/akamai)
- **SDKs & repos:** EdgeGrid auth libs (Python/Go/Node/Java), Akamai CLI, Terraform provider
- **Downloadable / offline:** OpenAPI specs downloadable per API

### Fastly

- **Docs:** [developer.fastly.com](https://developer.fastly.com/)
- **Developer / API:** [developer.fastly.com/reference/api](https://developer.fastly.com/reference/api/)
- **GitHub:** [github.com/fastly](https://github.com/fastly)
- **SDKs & repos:** fastly-py, go-fastly, Terraform provider, Compute SDKs
- **Downloadable / offline:** OpenAPI-generated SDKs under [github.com/fastly](https://github.com/fastly) (e.g. [github.com/fastly/fastly-py](https://github.com/fastly/fastly-py))

### Tailscale

- **Docs:** [tailscale.com/kb](https://tailscale.com/kb)
- **Developer / API:** [tailscale.com/api](https://tailscale.com/api)
- **GitHub:** [github.com/tailscale/tailscale](https://github.com/tailscale/tailscale)
- **SDKs & repos:** Full Go client source, tsnet embeddable library, Terraform provider
- **Downloadable / offline:** Repo cloneable; static binaries per release

### ZeroTier

- **Docs:** [docs.zerotier.com](https://docs.zerotier.com/)
- **Developer / API:** [docs.zerotier.com/api](https://docs.zerotier.com/api/)
- **GitHub:** [github.com/zerotier/ZeroTierOne](https://github.com/zerotier/ZeroTierOne)
- **SDKs & repos:** Central API, libzt embeddable SDK
- **Downloadable / offline:** OpenAPI spec in repo

### WireGuard

- **Docs:** [wireguard.com](https://www.wireguard.com/)
- **Developer / API:** [wireguard.com/xplatform](https://www.wireguard.com/xplatform/)
- **GitHub:** [git.zx2c4.com/wireguard-tools](https://git.zx2c4.com/wireguard-tools/)
- **SDKs & repos:** In-kernel implementation + wireguard-tools, wgctrl-go
- **Downloadable / offline:** Whitepaper PDF [wireguard.com/papers/wireguard.pdf](https://www.wireguard.com/papers/wireguard.pdf)

### Netmaker

- **Docs:** [docs.netmaker.io](https://docs.netmaker.io/)
- **GitHub:** [github.com/gravitl/netmaker](https://github.com/gravitl/netmaker)
- **SDKs & repos:** WireGuard mesh orchestration, REST API, Helm charts
- **Downloadable / offline:** Docs site + repo

### Headscale

- **Docs:** [headscale.net](https://headscale.net/)
- **Developer / API:** [headscale.net/stable/ref/api](https://headscale.net/stable/ref/api/)
- **GitHub:** [github.com/juanfont/headscale](https://github.com/juanfont/headscale)
- **SDKs & repos:** Open-source Tailscale control-server implementation
- **Downloadable / offline:** Docs site + repo

### Nebula (Slack)

- **Docs:** [github.com/slackhq/nebula](https://github.com/slackhq/nebula)
- **Developer / API:** [nebula.defined.net/docs](https://nebula.defined.net/docs/)
- **GitHub:** [github.com/slackhq/nebula](https://github.com/slackhq/nebula)
- **SDKs & repos:** Go overlay networking library + binaries
- **Downloadable / offline:** Repo docs

### OpenZiti

- **Docs:** [netfoundry.io/docs/openziti](https://netfoundry.io/docs/openziti/)
- **GitHub:** [github.com/openziti](https://github.com/openziti)
- **SDKs & repos:** Zero-trust overlay with SDKs in Go, C, Python, Java, Swift, .NET
- **Downloadable / offline:** Docs site + repo

### OpenVPN

- **Docs:** [openvpn.net/community-resources](https://openvpn.net/community-resources/)
- **GitHub:** [github.com/OpenVPN/openvpn](https://github.com/OpenVPN/openvpn)
- **SDKs & repos:** Community edition source, management interface API
- **Downloadable / offline:** man pages + repo docs

### strongSwan

- **Docs:** [docs.strongswan.org](https://docs.strongswan.org/)
- **GitHub:** [github.com/strongswan/strongswan](https://github.com/strongswan/strongswan)
- **SDKs & repos:** IPsec/IKEv2 stack, VICI control API with Python/Ruby/Perl bindings
- **Downloadable / offline:** Docs site + repo

### Aviatrix

- **Docs:** [docs.aviatrix.com](https://docs.aviatrix.com/)
- **GitHub:** [github.com/AviatrixSystems](https://github.com/AviatrixSystems)
- **SDKs & repos:** Terraform provider, Controller REST API
- **Downloadable / offline:** Printable doc pages

### Alkira

- **Docs:** [github.com/alkiranet](https://github.com/alkiranet)
- **GitHub:** [github.com/alkiranet](https://github.com/alkiranet)
- **SDKs & repos:** Terraform provider, Go SDK
- *Note:* Doc site is customer-gated


## 7. Whitebox NOS, silicon & DPUs

### SONiC (Linux Foundation)

- **Docs:** [sonic-net.github.io/SONiC](https://sonic-net.github.io/SONiC/)
- **GitHub:** [github.com/sonic-net/SONiC](https://github.com/sonic-net/SONiC)
- **SDKs & repos:** sonic-buildimage [github.com/sonic-net/sonic-buildimage](https://github.com/sonic-net/sonic-buildimage) • sonic-mgmt • SAI • gNMI container
- **Downloadable / offline:** HLD design docs [github.com/sonic-net/SONiC/tree/master/doc](https://github.com/sonic-net/SONiC/tree/master/doc) (markdown, cloneable)
- *Note:* The dominant open NOS

### Broadcom

- **Docs:** [docs.broadcom.com](https://docs.broadcom.com/)
- **GitHub:** [github.com/Broadcom](https://github.com/Broadcom)
- **SDKs & repos:** SAI (Switch Abstraction Interface) contributions, SDKLT
- **Downloadable / offline:** PDF datasheets/manuals via docs.broadcom.com

### Marvell

- **Docs:** [marvell.com/support.html](https://www.marvell.com/support.html)
- **GitHub:** [github.com/Marvell-switching](https://github.com/Marvell-switching)
- **SDKs & repos:** Prestera SAI + Linux switchdev drivers
- **Downloadable / offline:** PDF datasheets (some NDA-gated)

### Intel

- **Docs:** [intel.com/content/…](https://www.intel.com/content/www/us/en/developer/topic-technology/networking/overview.html)
- **GitHub:** [github.com/intel](https://github.com/intel)
- **SDKs & repos:** DPDK, IPDK, Tofino/P4 tooling, ethernet drivers
- **Downloadable / offline:** PDF programmer guides & datasheets

### NVIDIA DOCA (BlueField DPU)

- **Docs:** [networking-docs.nvidia.com/doca](https://networking-docs.nvidia.com/doca/)
- **GitHub:** [github.com/NVIDIA/doca-platform](https://github.com/NVIDIA/doca-platform)
- **SDKs & repos:** DOCA SDK (C/Python), DPF for Kubernetes, DOCA Flow/Comm Channel
- **Downloadable / offline:** Per-version doc archive, SDK downloads from NVIDIA developer zone

### AMD Pensando

- **Docs:** [amd.com/en/products/accelerators.html](https://www.amd.com/en/products/accelerators.html)
- **GitHub:** [github.com/Netronome](https://github.com/Netronome)
- **SDKs & repos:** DSC/DPU SmartNIC; P4 pipeline; Netronome lineage repos
- **Downloadable / offline:** Product briefs; SDK via partner program
- *Note:* The old /accelerators/pensando.html path now 404s; AMD folded Pensando into the accelerators hub.

### Open Networking Foundation

- **Docs:** [opennetworking.org](https://opennetworking.org/)
- **Developer / API:** [docs.onosproject.org](https://docs.onosproject.org/)
- **GitHub:** [github.com/opennetworkinglab](https://github.com/opennetworkinglab)
- **SDKs & repos:** ONOS, Stratum [github.com/stratum/stratum](https://github.com/stratum/stratum), SD-RAN, Aether
- **Downloadable / offline:** Per-project doc sets

### P4 Language Consortium

- **Docs:** [p4.org](https://p4.org/)
- **Developer / API:** [github.com/p4lang/p4-spec](https://github.com/p4lang/p4-spec)
- **GitHub:** [github.com/p4lang](https://github.com/p4lang)
- **SDKs & repos:** p4c compiler, BMv2 behavioural model, PI, p4runtime
- **Downloadable / offline:** Spec PDFs/HTML in [github.com/p4lang/p4-spec](https://github.com/p4lang/p4-spec)


## 8. DNS, DHCP, IPAM & source of truth

### Infoblox

- **Docs:** [docs.infoblox.com](https://docs.infoblox.com/)
- **GitHub:** [github.com/infobloxopen](https://github.com/infobloxopen)
- **SDKs & repos:** infoblox-client (Python), Terraform provider, Ansible collection, WAPI docs
- **Downloadable / offline:** PDF guides on docs.infoblox.com

### BlueCat Networks

- **Docs:** [docs.bluecatnetworks.com](https://docs.bluecatnetworks.com/)
- **SDKs & repos:** Address Manager REST v2 API, Terraform provider
- **Downloadable / offline:** PDF guides

### EfficientIP

- **Docs:** [efficientip.com/resources](https://efficientip.com/resources/)
- **SDKs & repos:** SOLIDserver REST API, Ansible/Terraform
- **Downloadable / offline:** PDF datasheets & guides

### IBM NS1 Connect

- **Docs:** [developer.ibm.com/apis/…](https://developer.ibm.com/apis/catalog/ns1--ibm-ns1-connect-api/Introduction)
- **GitHub:** [github.com/ns1](https://github.com/ns1)
- **SDKs & repos:** ns1-python, ns1-go, Terraform provider
- **Downloadable / offline:** OpenAPI spec downloadable
- *Note:* NS1 acquired by IBM

### BIND 9 (ISC)

- **Docs:** [bind9.readthedocs.io](https://bind9.readthedocs.io/)
- **Developer / API:** [bind9.readthedocs.io/en/…](https://bind9.readthedocs.io/en/latest/dnssec-guide.html)
- **GitHub:** [isc.org/bind](https://www.isc.org/bind/)
- **SDKs & repos:** Reference nameserver; libdns, rndc control channel
- **Downloadable / offline:** PDF ARM [bind9.readthedocs.io/_/downloads/en/latest/pdf](https://bind9.readthedocs.io/_/downloads/en/latest/pdf/)

### ISC Kea DHCP

- **Docs:** [kea.readthedocs.io](https://kea.readthedocs.io/)
- **Developer / API:** [kea.readthedocs.io/en/latest/api.html](https://kea.readthedocs.io/en/latest/api.html)
- **GitHub:** [isc.org/kea](https://www.isc.org/kea/)
- **SDKs & repos:** Modern DHCPv4/v6 with REST control agent and hooks API
- **Downloadable / offline:** PDF ARM [kea.readthedocs.io/_/downloads/en/latest/pdf](https://kea.readthedocs.io/_/downloads/en/latest/pdf/)

### PowerDNS

- **Docs:** [doc.powerdns.com](https://doc.powerdns.com/)
- **Developer / API:** [doc.powerdns.com/authoritative/http-api](https://doc.powerdns.com/authoritative/http-api/)
- **GitHub:** [github.com/PowerDNS/pdns](https://github.com/PowerDNS/pdns)
- **SDKs & repos:** Authoritative + Recursor + dnsdist, full HTTP API
- **Downloadable / offline:** Sphinx docs, repo cloneable

### NLnet Labs Unbound

- **Docs:** [unbound.docs.nlnetlabs.nl](https://unbound.docs.nlnetlabs.nl/)
- **GitHub:** [github.com/NLnetLabs/unbound](https://github.com/NLnetLabs/unbound)
- **SDKs & repos:** Validating recursive resolver, libunbound, Python/pythonmod
- **Downloadable / offline:** PDF [unbound.docs.nlnetlabs.nl/_/…](https://unbound.docs.nlnetlabs.nl/_/downloads/en/latest/pdf/)

### Knot DNS (CZ.NIC)

- **Docs:** [knot-dns.cz/documentation](https://www.knot-dns.cz/documentation/)
- **Developer / API:** [knot-dns.cz/docs/latest/html](https://www.knot-dns.cz/docs/latest/html/)
- **GitHub:** [gitlab.nic.cz/knot/knot-dns](https://gitlab.nic.cz/knot/knot-dns)
- **SDKs & repos:** Authoritative server + Knot Resolver, libknot control API
- **Downloadable / offline:** HTML/PDF doc builds per release

### CoreDNS

- **Docs:** [coredns.io/manual/toc](https://coredns.io/manual/toc/)
- **Developer / API:** [coredns.io/plugins](https://coredns.io/plugins/)
- **GitHub:** [github.com/coredns/coredns](https://github.com/coredns/coredns)
- **SDKs & repos:** Plugin-based DNS in Go; default Kubernetes DNS
- **Downloadable / offline:** Docs site + repo
- *Note:* CNCF graduated

### dnsmasq

- **Docs:** [thekelleys.org.uk/dnsmasq/doc.html](https://thekelleys.org.uk/dnsmasq/doc.html)
- **Developer / API:** [thekelleys.org.uk/dnsmasq/docs](https://thekelleys.org.uk/dnsmasq/docs/)
- **SDKs & repos:** Lightweight DNS/DHCP/TFTP for edge & embedded
- **Downloadable / offline:** man page + tarball docs

### NetBox

- **Docs:** [docs.netbox.dev/en/stable](https://docs.netbox.dev/en/stable/)
- **Developer / API:** [docs.netbox.dev/en/…](https://docs.netbox.dev/en/stable/integrations/rest-api/)
- **GitHub:** [github.com/netbox-community/netbox](https://github.com/netbox-community/netbox)
- **SDKs & repos:** pynetbox, go-netbox, Ansible collection, Terraform provider
- **Downloadable / offline:** MkDocs site; repo cloneable for offline
- *Note:* The de-facto network source of truth

### Nautobot

- **Docs:** [docs.nautobot.com](https://docs.nautobot.com/)
- **Developer / API:** [docs.nautobot.com/projects/core/en/stable](https://docs.nautobot.com/projects/core/en/stable/)
- **GitHub:** [github.com/nautobot/nautobot](https://github.com/nautobot/nautobot)
- **SDKs & repos:** pynautobot, Ansible collection, Golden Config & Device Onboarding apps
- **Downloadable / offline:** MkDocs site; repo cloneable
- *Note:* NetBox fork with an app framework

### phpIPAM

- **Docs:** [phpipam.net](https://phpipam.net/)
- **Developer / API:** [phpipam.net/api/api_documentation](https://phpipam.net/api/api_documentation/)
- **GitHub:** [github.com/phpipam/phpipam](https://github.com/phpipam/phpipam)
- **SDKs & repos:** Open-source IPAM with REST API
- **Downloadable / offline:** Online docs

### NIPAP

- **Docs:** [spritelink.github.io/NIPAP](https://spritelink.github.io/NIPAP/)
- **GitHub:** [github.com/SpriteLink/NIPAP](https://github.com/SpriteLink/NIPAP)
- **SDKs & repos:** XML-RPC API, pynipap, CLI
- **Downloadable / offline:** GitHub pages docs


## 9. Monitoring, observability & telemetry

### Cisco ThousandEyes

- **Docs:** [docs.thousandeyes.com](https://docs.thousandeyes.com/)
- **Developer / API:** [developer.cisco.com/thousandeyes](https://developer.cisco.com/thousandeyes/)
- **GitHub:** [github.com/thousandeyes](https://github.com/thousandeyes)
- **SDKs & repos:** OpenAPI spec + Python/Go/Java SDKs, Terraform provider
- **Downloadable / offline:** OpenAPI spec downloadable

### Kentik

- **Docs:** [kb.kentik.com](https://kb.kentik.com/)
- **GitHub:** [github.com/kentik](https://github.com/kentik)
- **SDKs & repos:** kentik-api-python, Go SDK, ktranslate
- **Downloadable / offline:** Printable KB

### SolarWinds

- **Docs:** [documentation.solarwinds.com](https://documentation.solarwinds.com/)
- **Developer / API:** [github.com/solarwinds/OrionSDK](https://github.com/solarwinds/OrionSDK)
- **GitHub:** [github.com/solarwinds](https://github.com/solarwinds)
- **SDKs & repos:** OrionSDK — SWIS API, PowerShell module, orionsdk Python
- **Downloadable / offline:** PDF admin guides

### NetScout

- **Docs:** [netscout.com/support-services](https://www.netscout.com/support-services)
- **GitHub:** [github.com/netscout](https://github.com/netscout)
- **SDKs & repos:** nGeniusONE REST API (customer-gated)
- **Downloadable / offline:** Customer portal

### LibreNMS

- **Docs:** [docs.librenms.org](https://docs.librenms.org/)
- **Developer / API:** [docs.librenms.org/API](https://docs.librenms.org/API/)
- **GitHub:** [github.com/librenms/librenms](https://github.com/librenms/librenms)
- **SDKs & repos:** Full REST API, auto-discovery, 200+ device OS definitions
- **Downloadable / offline:** MkDocs site; repo cloneable
- *Note:* Best open-source SNMP NMS

### Zabbix

- **Docs:** [zabbix.com/documentation/current/en](https://www.zabbix.com/documentation/current/en)
- **Developer / API:** [zabbix.com/documentation/current/en/manual/api](https://www.zabbix.com/documentation/current/en/manual/api)
- **GitHub:** [github.com/zabbix](https://github.com/zabbix)
- **SDKs & repos:** JSON-RPC API, zabbix_utils Python, official templates repo
- **Downloadable / offline:** Per-version doc trees; sources downloadable

### Icinga

- **Docs:** [icinga.com/docs](https://icinga.com/docs/)
- **Developer / API:** [icinga.com/docs/…](https://icinga.com/docs/icinga-2/latest/doc/12-icinga2-api/)
- **GitHub:** [github.com/Icinga](https://github.com/Icinga)
- **SDKs & repos:** Icinga 2 REST API, Director, Icinga DB
- **Downloadable / offline:** Docs per module; repo cloneable

### Checkmk

- **Docs:** [docs.checkmk.com/latest/en](https://docs.checkmk.com/latest/en/)
- **Developer / API:** [docs.checkmk.com/latest/en/rest_api.html](https://docs.checkmk.com/latest/en/rest_api.html)
- **GitHub:** [github.com/Checkmk/checkmk](https://github.com/Checkmk/checkmk)
- **SDKs & repos:** REST API, agent plugins, Python check API
- **Downloadable / offline:** PDF export of the handbook per version

### Cacti

- **Docs:** [cacti.net](https://www.cacti.net/)
- **Developer / API:** [github.com/Cacti/documentation](https://github.com/Cacti/documentation)
- **GitHub:** [github.com/Cacti/cacti](https://github.com/Cacti/cacti)
- **SDKs & repos:** RRDtool-based graphing, plugin architecture
- **Downloadable / offline:** Docs repo cloneable

### ntopng / ntop

- **Docs:** [ntop.org/guides/ntopng](https://www.ntop.org/guides/ntopng/)
- **Developer / API:** [ntop.org/guides/ntopng/api](https://www.ntop.org/guides/ntopng/api/)
- **GitHub:** [github.com/ntop/ntopng](https://github.com/ntop/ntopng)
- **SDKs & repos:** ntopng REST API, nProbe, PF_RING, Lua scripting
- **Downloadable / offline:** Guides also published as PDF/ePub

### Akvorado

- **Docs:** [github.com/akvorado/akvorado](https://github.com/akvorado/akvorado)
- **Developer / API:** [demo.akvorado.net/docs](https://demo.akvorado.net/docs)
- **GitHub:** [github.com/akvorado/akvorado](https://github.com/akvorado/akvorado)
- **SDKs & repos:** NetFlow/IPFIX/sFlow collector with ClickHouse + BMP enrichment
- **Downloadable / offline:** In-repo docs

### pmacct

- **Docs:** [pmacct.net](http://www.pmacct.net/)
- **GitHub:** [github.com/pmacct/pmacct](https://github.com/pmacct/pmacct)
- **SDKs & repos:** Flow accounting (NetFlow/IPFIX/sFlow/BMP/BGP) toolkit
- **Downloadable / offline:** Docs tarball + in-repo

### Netdisco

- **Docs:** [netdisco.org](https://netdisco.org/)
- **Developer / API:** [github.com/netdisco/netdisco/wiki](https://github.com/netdisco/netdisco/wiki)
- **GitHub:** [github.com/netdisco/netdisco](https://github.com/netdisco/netdisco)
- **SDKs & repos:** L2/L3 discovery, SNMP::Info library, REST API
- **Downloadable / offline:** Wiki + repo

### Oxidized

- **Docs:** [github.com/ytti/oxidized](https://github.com/ytti/oxidized)
- **Developer / API:** [github.com/ytti/oxidized/tree/master/docs](https://github.com/ytti/oxidized/tree/master/docs)
- **GitHub:** [github.com/ytti/oxidized](https://github.com/ytti/oxidized)
- **SDKs & repos:** Config backup for 130+ platforms, REST + hooks
- **Downloadable / offline:** In-repo markdown docs
- *Note:* RANCID successor

### Prometheus snmp_exporter

- **Docs:** [github.com/prometheus/snmp_exporter](https://github.com/prometheus/snmp_exporter)
- **GitHub:** [github.com/prometheus/snmp_exporter](https://github.com/prometheus/snmp_exporter)
- **SDKs & repos:** SNMP → Prometheus bridge with MIB generator
- **Downloadable / offline:** In-repo docs

### Telegraf (InfluxData)

- **Docs:** [docs.influxdata.com/telegraf](https://docs.influxdata.com/telegraf/)
- **Developer / API:** [github.com/influxdata/telegraf](https://github.com/influxdata/telegraf)
- **GitHub:** [github.com/influxdata/telegraf](https://github.com/influxdata/telegraf)
- **SDKs & repos:** gNMI, SNMP, sFlow, NetFlow input plugins
- **Downloadable / offline:** Per-plugin READMEs in repo


## 10. Test, measurement, simulation & labs

### Keysight (incl. Ixia & Spirent)

- **Docs:** [keysight.com/us/en/support.html](https://www.keysight.com/us/en/support.html)
- **Developer / API:** [github.com/open-traffic-generator](https://github.com/open-traffic-generator)
- **GitHub:** [github.com/open-traffic-generator](https://github.com/open-traffic-generator)
- **SDKs & repos:** IxNetwork/IxLoad REST APIs, snappi (OTG Python SDK), Open Traffic Generator model
- **Downloadable / offline:** PDF user guides via Keysight support
- *Note:* Keysight acquired Spirent — spirent.com now redirects to keysight.com

### VIAVI Solutions

- **Docs:** [viavisolutions.com/en-us/support](https://www.viavisolutions.com/en-us/support)
- **SDKs & repos:** TeraVM, Observer platform APIs
- **Downloadable / offline:** PDF manuals via support

### EXFO

- **Docs:** [exfo.com/en/support](https://www.exfo.com/en/support/)
- **SDKs & repos:** Nova / Worx platform APIs
- **Downloadable / offline:** PDF manuals via support

### GNS3

- **Docs:** [docs.gns3.com](https://docs.gns3.com/)
- **Developer / API:** [gns3-server.readthedocs.io](https://gns3-server.readthedocs.io/)
- **GitHub:** [github.com/GNS3](https://github.com/GNS3)
- **SDKs & repos:** GNS3 server REST API, gns3fy Python client
- **Downloadable / offline:** Docs site + appliance files [gns3.com/software/download](https://www.gns3.com/software/download)

### EVE-NG

- **Docs:** [eve-ng.net/index.php/documentation](https://www.eve-ng.net/index.php/documentation/)
- **SDKs & repos:** XML-RPC/REST API in Pro edition
- **Downloadable / offline:** PDF cookbook downloads

### Cisco Modeling Labs (CML)

- **Docs:** [developer.cisco.com/docs/modeling-labs](https://developer.cisco.com/docs/modeling-labs/)
- **GitHub:** [github.com/CiscoDevNet](https://github.com/CiscoDevNet)
- **SDKs & repos:** virl2_client Python SDK, Terraform provider
- **Downloadable / offline:** OpenAPI spec served by the controller

### Containerlab

- **Docs:** [containerlab.dev](https://containerlab.dev/)
- **Developer / API:** [containerlab.dev/manual/kinds](https://containerlab.dev/manual/kinds/)
- **GitHub:** [github.com/srl-labs/containerlab](https://github.com/srl-labs/containerlab)
- **SDKs & repos:** Multi-vendor container/VM lab orchestration; huge kind library
- **Downloadable / offline:** MkDocs site; repo cloneable
- *Note:* Now the default way to lab modern NOSes

### netlab (ipSpace)

- **Docs:** [netlab.tools](https://netlab.tools/)
- **Developer / API:** [netlab.tools/module](https://netlab.tools/module/)
- **GitHub:** [github.com/ipspace/netlab](https://github.com/ipspace/netlab)
- **SDKs & repos:** Topology-as-code on top of containerlab/libvirt with Ansible config gen
- **Downloadable / offline:** Docs site + repo

### Batfish

- **Docs:** [batfish.readthedocs.io](https://batfish.readthedocs.io/)
- **Developer / API:** [batfish.readthedocs.io/en/…](https://batfish.readthedocs.io/en/latest/notebooks/interacting.html)
- **GitHub:** [github.com/batfish/batfish](https://github.com/batfish/batfish)
- **SDKs & repos:** pybatfish — offline config analysis and intent verification
- **Downloadable / offline:** Sphinx docs + Jupyter notebooks in repo
- *Note:* Pre-deployment config correctness

### Mininet

- **Docs:** [mininet.org](https://mininet.org/)
- **Developer / API:** [mininet.org/api](https://mininet.org/api/)
- **GitHub:** [github.com/mininet/mininet](https://github.com/mininet/mininet)
- **SDKs & repos:** Python API for emulated SDN topologies
- **Downloadable / offline:** Walkthrough + API docs

### ns-3

- **Docs:** [nsnam.org/documentation](https://www.nsnam.org/documentation/)
- **Developer / API:** [nsnam.org/docs](https://www.nsnam.org/docs/)
- **GitHub:** [gitlab.com/nsnam/ns-3-dev](https://gitlab.com/nsnam/ns-3-dev)
- **SDKs & repos:** Discrete-event network simulator, Python bindings
- **Downloadable / offline:** PDF manual/tutorial per release, e.g. [nsnam.org/docs/…](https://www.nsnam.org/docs/release/3.41/manual/ns-3-manual.pdf)

### OMNeT++ / INET

- **Docs:** [omnetpp.org/documentation](https://omnetpp.org/documentation/)
- **Developer / API:** [inet.omnetpp.org/docs](https://inet.omnetpp.org/docs/)
- **GitHub:** [github.com/omnetpp/omnetpp](https://github.com/omnetpp/omnetpp)
- **SDKs & repos:** Simulation framework with INET protocol models
- **Downloadable / offline:** PDF manuals downloadable

### iperf3 (ESnet)

- **Docs:** [iperf.fr](https://iperf.fr/)
- **Developer / API:** [software.es.net/iperf](https://software.es.net/iperf/)
- **GitHub:** [github.com/esnet/iperf](https://github.com/esnet/iperf)
- **SDKs & repos:** Throughput testing, libiperf C API, JSON output
- **Downloadable / offline:** man page + repo

### Cisco TRex

- **Docs:** [github.com/cisco-system-traffic-generator/…](https://github.com/cisco-system-traffic-generator/trex-core)
- **Developer / API:** [trex-tgn.cisco.com/trex/doc](https://trex-tgn.cisco.com/trex/doc/)
- **GitHub:** [github.com/cisco-system-traffic-generator/…](https://github.com/cisco-system-traffic-generator/trex-core)
- **SDKs & repos:** DPDK-based stateful/stateless traffic generator, Python automation API
- **Downloadable / offline:** Docs + repo
- *Note:* trex-tgn.cisco.com did not resolve from our verification network; the GitHub repo is the reliable entry point and carries the same docs.


## 11. SDN, NFV & network orchestration

### OpenDaylight

- **Docs:** [docs.opendaylight.org](https://docs.opendaylight.org/)
- **Developer / API:** [docs.opendaylight.org/en/…](https://docs.opendaylight.org/en/latest/developer-guides/)
- **GitHub:** [github.com/opendaylight](https://github.com/opendaylight)
- **SDKs & repos:** Java SDN controller, RESTCONF/NETCONF southbound, MD-SAL
- **Downloadable / offline:** Per-release doc sets
- *Note:* LF Networking

### ONAP

- **Docs:** [docs.onap.org](https://docs.onap.org/)
- **Developer / API:** [docs.onap.org/en/latest/guides/onap-developer](https://docs.onap.org/en/latest/guides/onap-developer/)
- **GitHub:** [github.com/onap](https://github.com/onap)
- **SDKs & repos:** Full network automation/orchestration platform (SO, SDNC, DCAE, Policy)
- **Downloadable / offline:** Per-release doc sets, downloadable
- *Note:* LF Networking

### Tungsten Fabric

- **Docs:** [tungstenfabric.github.io/website](https://tungstenfabric.github.io/website/)
- **GitHub:** [github.com/tungstenfabric](https://github.com/tungstenfabric)
- **SDKs & repos:** Multi-cloud SDN (ex Juniper Contrail), vRouter, REST API
- **Downloadable / offline:** Docs site + repo

### FD.io VPP

- **Docs:** [s3-docs.fd.io/vpp](https://s3-docs.fd.io/vpp/)
- **Developer / API:** [fd.io](https://fd.io/)
- **GitHub:** [github.com/FDio/vpp](https://github.com/FDio/vpp)
- **SDKs & repos:** Vector Packet Processing userspace dataplane; C/Python/Go API bindings
- **Downloadable / offline:** Per-version doc sets on s3-docs.fd.io

### Anuket (ex OPNFV)

- **Docs:** [docs.anuket.io](https://docs.anuket.io/)
- **GitHub:** [github.com/anuket-project](https://github.com/anuket-project)
- **SDKs & repos:** NFVI reference architectures, CNTT, test suites
- **Downloadable / offline:** Per-release doc sets
- *Note:* LF Networking

### Nephio

- **Docs:** [nephio.org](https://nephio.org/)
- **Developer / API:** [docs.nephio.org](https://docs.nephio.org/)
- **GitHub:** [github.com/nephio-project](https://github.com/nephio-project)
- **SDKs & repos:** Kubernetes-native intent-driven telco automation
- **Downloadable / offline:** Docs site + repo
- *Note:* LF Networking

### ONOS

- **Docs:** [docs.onosproject.org](https://docs.onosproject.org/)
- **GitHub:** [github.com/opennetworkinglab/onos](https://github.com/opennetworkinglab/onos)
- **SDKs & repos:** Carrier-grade SDN controller, P4Runtime/gNMI southbound
- **Downloadable / offline:** Wiki/doc site

### Stratum

- **Docs:** [github.com/stratum/stratum](https://github.com/stratum/stratum)
- **GitHub:** [github.com/stratum/stratum](https://github.com/stratum/stratum)
- **SDKs & repos:** Thin switch OS exposing P4Runtime, gNMI, gNOI
- **Downloadable / offline:** In-repo docs


## 12. Cloud-native & Kubernetes networking

### Cilium

- **Docs:** [docs.cilium.io](https://docs.cilium.io/)
- **Developer / API:** [docs.cilium.io/en/stable/api](https://docs.cilium.io/en/stable/api/)
- **GitHub:** [github.com/cilium/cilium](https://github.com/cilium/cilium)
- **SDKs & repos:** eBPF CNI, Hubble observability, Tetragon, Gateway API, cilium CLI
- **Downloadable / offline:** Sphinx docs per version; repo cloneable
- *Note:* CNCF graduated

### Calico (Tigera)

- **Docs:** [docs.tigera.io/calico/latest/about](https://docs.tigera.io/calico/latest/about/)
- **Developer / API:** [docs.tigera.io/calico/latest/reference](https://docs.tigera.io/calico/latest/reference/)
- **GitHub:** [github.com/projectcalico/calico](https://github.com/projectcalico/calico)
- **SDKs & repos:** calicoctl, eBPF/iptables dataplanes, BGP peering with the fabric
- **Downloadable / offline:** Docs site; repo cloneable

### Flannel

- **Docs:** [github.com/flannel-io/flannel](https://github.com/flannel-io/flannel)
- **Developer / API:** [github.com/flannel-io/…](https://github.com/flannel-io/flannel/blob/master/Documentation/)
- **GitHub:** [github.com/flannel-io/flannel](https://github.com/flannel-io/flannel)
- **SDKs & repos:** Simple L3 overlay CNI
- **Downloadable / offline:** In-repo docs

### Multus CNI

- **Docs:** [github.com/k8snetworkplumbingwg/multus-cni](https://github.com/k8snetworkplumbingwg/multus-cni)
- **Developer / API:** [github.com/k8snetworkplumbingwg/…](https://github.com/k8snetworkplumbingwg/multus-cni/tree/master/docs)
- **GitHub:** [github.com/k8snetworkplumbingwg/multus-cni](https://github.com/k8snetworkplumbingwg/multus-cni)
- **SDKs & repos:** Multi-interface pods — the telco/NFV standard
- **Downloadable / offline:** In-repo docs

### Kube-OVN

- **Docs:** [kubeovn.github.io/docs](https://kubeovn.github.io/docs/)
- **GitHub:** [github.com/kubeovn/kube-ovn](https://github.com/kubeovn/kube-ovn)
- **SDKs & repos:** OVN-based CNI with VPC, subnets, QoS, multi-cluster
- **Downloadable / offline:** Docs site
- *Note:* CNCF

### OVN

- **Docs:** [docs.ovn.org](https://docs.ovn.org/)
- **Developer / API:** [docs.ovn.org/en/latest/ref](https://docs.ovn.org/en/latest/ref/)
- **GitHub:** [github.com/ovn-org/ovn](https://github.com/ovn-org/ovn)
- **SDKs & repos:** Logical switching/routing on OVS; OVSDB northbound
- **Downloadable / offline:** PDF [docs.ovn.org/_/downloads/en/latest/pdf](https://docs.ovn.org/_/downloads/en/latest/pdf/)

### Open vSwitch

- **Docs:** [docs.openvswitch.org](https://docs.openvswitch.org/)
- **Developer / API:** [docs.openvswitch.org/en/latest/ref](https://docs.openvswitch.org/en/latest/ref/)
- **GitHub:** [github.com/openvswitch/ovs](https://github.com/openvswitch/ovs)
- **SDKs & repos:** OVSDB protocol, ovs-vsctl/ofctl, DPDK datapath
- **Downloadable / offline:** PDF [docs.openvswitch.org/_/downloads/en/latest/pdf](https://docs.openvswitch.org/_/downloads/en/latest/pdf/)

### Antrea

- **Docs:** [antrea.io/docs](https://antrea.io/docs/)
- **GitHub:** [github.com/antrea-io/antrea](https://github.com/antrea-io/antrea)
- **SDKs & repos:** OVS-based CNI with Antrea-native policies, Theia observability
- **Downloadable / offline:** Docs site
- *Note:* CNCF

### MetalLB

- **Docs:** [metallb.io](https://metallb.io/)
- **Developer / API:** [metallb.io/apis](https://metallb.io/apis/)
- **GitHub:** [github.com/metallb/metallb](https://github.com/metallb/metallb)
- **SDKs & repos:** Bare-metal LoadBalancer via ARP/NDP or BGP
- **Downloadable / offline:** Docs site

### Submariner

- **Docs:** [submariner.io/getting-started](https://submariner.io/getting-started/)
- **Developer / API:** [submariner.io/operations](https://submariner.io/operations/)
- **GitHub:** [github.com/submariner-io](https://github.com/submariner-io)
- **SDKs & repos:** Cross-cluster L3 connectivity and service discovery
- **Downloadable / offline:** Docs site

### Envoy

- **Docs:** [envoyproxy.io/docs](https://www.envoyproxy.io/docs)
- **Developer / API:** [envoyproxy.io/docs/envoy/latest/api/api](https://www.envoyproxy.io/docs/envoy/latest/api/api)
- **GitHub:** [github.com/envoyproxy/envoy](https://github.com/envoyproxy/envoy)
- **SDKs & repos:** xDS APIs, go-control-plane, Gateway API implementation
- **Downloadable / offline:** Sphinx docs per version
- *Note:* CNCF graduated

### Istio

- **Docs:** [istio.io/latest/docs](https://istio.io/latest/docs/)
- **Developer / API:** [istio.io/latest/docs/reference](https://istio.io/latest/docs/reference/)
- **GitHub:** [github.com/istio/istio](https://github.com/istio/istio)
- **SDKs & repos:** istioctl, client-go, Ambient & sidecar modes
- **Downloadable / offline:** Docs site

### Linkerd

- **Docs:** [linkerd.io/docs](https://linkerd.io/docs/)
- **Developer / API:** [linkerd.io/2/reference](https://linkerd.io/2/reference/)
- **GitHub:** [github.com/linkerd/linkerd2](https://github.com/linkerd/linkerd2)
- **SDKs & repos:** Rust micro-proxy service mesh, linkerd CLI
- **Downloadable / offline:** Docs site

### NGINX

- **Docs:** [nginx.org/en/docs](https://nginx.org/en/docs/)
- **Developer / API:** [nginx.org/en/…](https://nginx.org/en/docs/http/ngx_http_api_module.html)
- **GitHub:** [github.com/nginx/nginx](https://github.com/nginx/nginx)
- **SDKs & repos:** Core source, NGINX Plus REST API, njs scripting, Ingress controller
- **Downloadable / offline:** Docs site; source tarballs

### HAProxy

- **Docs:** [docs.haproxy.org](https://docs.haproxy.org/)
- **Developer / API:** [haproxy.org/download](https://www.haproxy.org/download/)
- **GitHub:** [github.com/haproxy/haproxy](https://github.com/haproxy/haproxy)
- **SDKs & repos:** Data Plane API, Runtime API, Kubernetes Ingress controller
- **Downloadable / offline:** Per-version config manual, downloadable

### Traefik

- **Docs:** [doc.traefik.io/traefik](https://doc.traefik.io/traefik/)
- **Developer / API:** [doc.traefik.io/traefik/routing/overview](https://doc.traefik.io/traefik/routing/overview/)
- **GitHub:** [github.com/traefik/traefik](https://github.com/traefik/traefik)
- **SDKs & repos:** Dynamic provider model, Gateway API, Traefik Hub API
- **Downloadable / offline:** Docs site

### Caddy

- **Docs:** [caddyserver.com/docs](https://caddyserver.com/docs/)
- **Developer / API:** [caddyserver.com/docs/api](https://caddyserver.com/docs/api)
- **GitHub:** [github.com/caddyserver/caddy](https://github.com/caddyserver/caddy)
- **SDKs & repos:** Admin REST API, Go modules, automatic HTTPS
- **Downloadable / offline:** Docs site


## 13. Routing daemons & protocol stacks

### FRRouting

- **Docs:** [docs.frrouting.org](https://docs.frrouting.org/)
- **Developer / API:** [docs.frrouting.org/projects/…](https://docs.frrouting.org/projects/dev-guide/en/latest/)
- **GitHub:** [github.com/FRRouting/frr](https://github.com/FRRouting/frr)
- **SDKs & repos:** BGP/OSPF/IS-IS/PIM/BFD stack used inside SONiC, Cumulus, VyOS, DENT
- **Downloadable / offline:** Sphinx docs per version; repo cloneable
- *Note:* The most important open routing stack

### BIRD

- **Docs:** [bird.network.cz](https://bird.network.cz/)
- **Developer / API:** [bird.network.cz/?get_doc&v=20&f=bird.html](https://bird.network.cz/?get_doc&v=20&f=bird.html)
- **GitHub:** [gitlab.nic.cz/labs/bird](https://gitlab.nic.cz/labs/bird)
- **SDKs & repos:** Lightweight BGP/OSPF/RIP/Babel daemon, widely used at IXPs
- **Downloadable / offline:** User guide HTML/PDF per release

### OpenBGPD

- **Docs:** [openbgpd.org](https://www.openbgpd.org/)
- **Developer / API:** [man.openbsd.org/bgpd](https://man.openbsd.org/bgpd)
- **SDKs & repos:** OpenBSD BGP daemon, portable builds for Linux/FreeBSD
- **Downloadable / offline:** man pages, source tarballs

### GoBGP

- **Docs:** [github.com/osrg/gobgp](https://github.com/osrg/gobgp)
- **Developer / API:** [github.com/osrg/gobgp/tree/master/docs](https://github.com/osrg/gobgp/tree/master/docs)
- **GitHub:** [github.com/osrg/gobgp](https://github.com/osrg/gobgp)
- **SDKs & repos:** BGP implementation in Go with a gRPC API — great for building controllers
- **Downloadable / offline:** In-repo docs

### ExaBGP

- **Docs:** [github.com/Exa-Networks/exabgp](https://github.com/Exa-Networks/exabgp)
- **Developer / API:** [github.com/Exa-Networks/exabgp/wiki](https://github.com/Exa-Networks/exabgp/wiki)
- **GitHub:** [github.com/Exa-Networks/exabgp](https://github.com/Exa-Networks/exabgp)
- **SDKs & repos:** BGP-to-text/API gateway; scriptable route injection, flowspec
- **Downloadable / offline:** Wiki + repo

### Holo

- **Docs:** [github.com/holo-routing/holo](https://github.com/holo-routing/holo)
- **Developer / API:** [holo-routing.github.io](https://holo-routing.github.io/)
- **GitHub:** [github.com/holo-routing/holo](https://github.com/holo-routing/holo)
- **SDKs & repos:** Rust routing stack, YANG-native with NETCONF/gRPC management
- **Downloadable / offline:** Repo + site
- *Note:* Newer, fully model-driven


## 14. Packet capture, IDS/IPS & analysis

### Wireshark

- **Docs:** [wireshark.org/docs](https://www.wireshark.org/docs/)
- **Developer / API:** [wireshark.org/docs/wsdg_html_chunked](https://www.wireshark.org/docs/wsdg_html_chunked/)
- **GitHub:** [gitlab.com/wireshark/wireshark](https://gitlab.com/wireshark/wireshark)
- **SDKs & repos:** Lua & C dissector APIs, tshark, editcap, extcap
- **Downloadable / offline:** PDF User's Guide [wireshark.org/download/…](https://www.wireshark.org/download/docs/Wireshark%20User%27s%20Guide.pdf) • all formats at [wireshark.org/download/docs](https://www.wireshark.org/download/docs/)

### tcpdump / libpcap

- **Docs:** [tcpdump.org](https://www.tcpdump.org/)
- **Developer / API:** [tcpdump.org/manpages](https://www.tcpdump.org/manpages/)
- **GitHub:** [github.com/the-tcpdump-group/tcpdump](https://github.com/the-tcpdump-group/tcpdump)
- **SDKs & repos:** libpcap C API — the foundation of nearly all capture tooling
- **Downloadable / offline:** man pages + source tarballs

### Suricata

- **Docs:** [docs.suricata.io](https://docs.suricata.io/)
- **Developer / API:** [docs.suricata.io/en/latest/output/eve](https://docs.suricata.io/en/latest/output/eve/)
- **GitHub:** [github.com/OISF/suricata](https://github.com/OISF/suricata)
- **SDKs & repos:** IDS/IPS/NSM, EVE JSON output, Lua scripting, suricata-update
- **Downloadable / offline:** PDF [docs.suricata.io/_/downloads/en/latest/pdf](https://docs.suricata.io/_/downloads/en/latest/pdf/)

### Snort 3

- **Docs:** [docs.snort.org](https://docs.snort.org/)
- **GitHub:** [github.com/snort3/snort3](https://github.com/snort3/snort3)
- **SDKs & repos:** Rule language, LuaJIT config, plugin SDK
- **Downloadable / offline:** Downloadable manuals from docs.snort.org

### Zeek

- **Docs:** [docs.zeek.org](https://docs.zeek.org/)
- **Developer / API:** [docs.zeek.org/en/current/scripting](https://docs.zeek.org/en/current/scripting/)
- **GitHub:** [github.com/zeek/zeek](https://github.com/zeek/zeek)
- **SDKs & repos:** Zeek scripting language, Broker API, zkg package manager
- **Downloadable / offline:** Sphinx docs; PDF via docs.zeek.org/_/downloads/
- *Note:* Network security monitoring

### Scapy

- **Docs:** [scapy.readthedocs.io](https://scapy.readthedocs.io/)
- **Developer / API:** [scapy.readthedocs.io/en/latest/api/scapy.html](https://scapy.readthedocs.io/en/latest/api/scapy.html)
- **GitHub:** [github.com/secdev/scapy](https://github.com/secdev/scapy)
- **SDKs & repos:** Python packet crafting/dissection — the automation Swiss-army knife
- **Downloadable / offline:** PDF [scapy.readthedocs.io/_/downloads/en/latest/pdf](https://scapy.readthedocs.io/_/downloads/en/latest/pdf/)

### Nmap

- **Docs:** [nmap.org/docs.html](https://nmap.org/docs.html)
- **Developer / API:** [nmap.org/book/nse-api.html](https://nmap.org/book/nse-api.html)
- **GitHub:** [github.com/nmap/nmap](https://github.com/nmap/nmap)
- **SDKs & repos:** NSE (Lua scripting engine), libnmap parsers, Ncat/Ndiff
- **Downloadable / offline:** Full book online [nmap.org/book/toc.html](https://nmap.org/book/toc.html)

### nftables / netfilter

- **Docs:** [wiki.nftables.org](https://wiki.nftables.org/)
- **Developer / API:** [wiki.nftables.org/wiki-nftables/…](https://wiki.nftables.org/wiki-nftables/index.php/Main_Page)
- **GitHub:** [git.netfilter.org](https://git.netfilter.org/)
- **SDKs & repos:** libnftnl, libmnl, conntrack-tools
- **Downloadable / offline:** Wiki + man pages
- *Note:* Linux packet filtering

### DPDK

- **Docs:** [doc.dpdk.org/guides](https://doc.dpdk.org/guides/)
- **Developer / API:** [doc.dpdk.org/api](https://doc.dpdk.org/api/)
- **GitHub:** [github.com/DPDK/dpdk](https://github.com/DPDK/dpdk)
- **SDKs & repos:** Userspace poll-mode drivers and packet libraries
- **Downloadable / offline:** Per-release guide trees [doc.dpdk.org](https://doc.dpdk.org/) (HTML/PDF)


## 15. Internet infrastructure, registries & standards

### IETF / RFC Editor

- **Docs:** [ietf.org/standards/rfcs](https://www.ietf.org/standards/rfcs/)
- **Developer / API:** [datatracker.ietf.org](https://datatracker.ietf.org/)
- **GitHub:** [github.com/ietf-tools](https://github.com/ietf-tools)
- **SDKs & repos:** Datatracker API, xml2rfc, I-D tooling
- **Downloadable / offline:** Bulk RFC download [rfc-editor.org/retrieve/bulk](https://www.rfc-editor.org/retrieve/bulk/)
- *Note:* The source of truth for protocols

### IEEE 802

- **Docs:** [standards.ieee.org/ieee/802](https://standards.ieee.org/ieee/802/)
- **Developer / API:** [ieee802.org](https://www.ieee802.org/)
- **SDKs & repos:** 802.1/802.3/802.11 working-group drafts
- **Downloadable / offline:** Many standards free via IEEE GET program

### OpenConfig

- **Docs:** [openconfig.net](https://www.openconfig.net/)
- **Developer / API:** [openconfig.net/docs](https://openconfig.net/docs/)
- **GitHub:** [github.com/openconfig](https://github.com/openconfig)
- **SDKs & repos:** YANG models [github.com/openconfig/public](https://github.com/openconfig/public) • gNMI/gNOI/gNSI • gnmic [github.com/openconfig/gnmic](https://github.com/openconfig/gnmic)
- **Downloadable / offline:** Model releases as tarballs [github.com/openconfig/public/releases](https://github.com/openconfig/public/releases)
- *Note:* The cross-vendor model standard

### PeeringDB

- **Docs:** [docs.peeringdb.com](https://docs.peeringdb.com/)
- **Developer / API:** [docs.peeringdb.com/api_specs](https://docs.peeringdb.com/api_specs/)
- **GitHub:** [github.com/peeringdb/peeringdb](https://github.com/peeringdb/peeringdb)
- **SDKs & repos:** REST API, peeringdb-py client
- **Downloadable / offline:** Full DB sync via API

### RIPE NCC

- **Docs:** [ripe.net/manage-ips-and-asns](https://www.ripe.net/manage-ips-and-asns/)
- **Developer / API:** [atlas.ripe.net/docs](https://atlas.ripe.net/docs/)
- **GitHub:** [github.com/RIPE-NCC](https://github.com/RIPE-NCC)
- **SDKs & repos:** RIPE Atlas API + Sagan/Cousteau libraries, RIPEstat API, RPKI tooling
- **Downloadable / offline:** Bulk whois/RPKI data dumps

### NLnet Labs Routinator

- **Docs:** [routinator.docs.nlnetlabs.nl](https://routinator.docs.nlnetlabs.nl/)
- **Developer / API:** [routinator.docs.nlnetlabs.nl/en/…](https://routinator.docs.nlnetlabs.nl/en/stable/api-endpoints.html)
- **GitHub:** [github.com/NLnetLabs/routinator](https://github.com/NLnetLabs/routinator)
- **SDKs & repos:** RPKI relying-party validator in Rust with HTTP API + RTR server
- **Downloadable / offline:** PDF [routinator.docs.nlnetlabs.nl/_/…](https://routinator.docs.nlnetlabs.nl/_/downloads/en/stable/pdf/)

### MANRS

- **Docs:** [manrs.org](https://manrs.org/)
- **SDKs & repos:** Routing security norms, observatory data
- **Downloadable / offline:** Reports as PDF

### RouteViews

- **Docs:** [routeviews.org/routeviews](https://www.routeviews.org/routeviews/)
- **Developer / API:** [archive.routeviews.org](http://archive.routeviews.org/)
- **SDKs & repos:** Global BGP table archives (MRT)
- **Downloadable / offline:** Bulk MRT dumps [archive.routeviews.org](http://archive.routeviews.org/)

### Linux kernel networking

- **Docs:** [docs.kernel.org/networking](https://docs.kernel.org/networking/)
- **GitHub:** [git.kernel.org](https://git.kernel.org/)
- **SDKs & repos:** netlink, XDP/eBPF, switchdev, tc, DSA
- **Downloadable / offline:** Kernel docs build to PDF/HTML from source


## 16. Vendor-neutral automation frameworks

### NAPALM

- **Docs:** [napalm.readthedocs.io](https://napalm.readthedocs.io/)
- **Developer / API:** [napalm.readthedocs.io/en/latest/base.html](https://napalm.readthedocs.io/en/latest/base.html)
- **GitHub:** [github.com/napalm-automation/napalm](https://github.com/napalm-automation/napalm)
- **SDKs & repos:** Unified multi-vendor driver API (EOS, Junos, IOS, IOS-XR, NX-OS)
- **Downloadable / offline:** PDF [napalm.readthedocs.io/_/…](https://napalm.readthedocs.io/_/downloads/en/latest/pdf/)

### Netmiko

- **Docs:** [netmiko.readthedocs.io](https://netmiko.readthedocs.io/)
- **Developer / API:** [ktbyers.github.io/netmiko](https://ktbyers.github.io/netmiko/)
- **GitHub:** [github.com/ktbyers/netmiko](https://github.com/ktbyers/netmiko)
- **SDKs & repos:** SSH automation for 100+ platforms
- **Downloadable / offline:** PDF [netmiko.readthedocs.io/_/…](https://netmiko.readthedocs.io/_/downloads/en/latest/pdf/)

### Nornir

- **Docs:** [nornir.readthedocs.io](https://nornir.readthedocs.io/)
- **Developer / API:** [nornir.readthedocs.io/en/latest/api/index.html](https://nornir.readthedocs.io/en/latest/api/index.html)
- **GitHub:** [github.com/nornir-automation/nornir](https://github.com/nornir-automation/nornir)
- **SDKs & repos:** Pure-Python, inventory-driven automation framework
- **Downloadable / offline:** Sphinx docs; repo cloneable

### Ansible network collections

- **Docs:** [docs.ansible.com/ansible/latest/network](https://docs.ansible.com/ansible/latest/network/)
- **Developer / API:** [docs.ansible.com/ansible/latest/collections](https://docs.ansible.com/ansible/latest/collections/)
- **GitHub:** [github.com/ansible-collections](https://github.com/ansible-collections)
- **SDKs & repos:** ansible.netcommon plus per-vendor collections (cisco.ios, arista.eos, junipernetworks.junos, nokia.srlinux, ...)
- **Downloadable / offline:** Full docs tarball per Ansible release

### ncclient

- **Docs:** [ncclient.readthedocs.io](https://ncclient.readthedocs.io/)
- **Developer / API:** [ncclient.readthedocs.io/en/latest/manager.html](https://ncclient.readthedocs.io/en/latest/manager.html)
- **GitHub:** [github.com/ncclient/ncclient](https://github.com/ncclient/ncclient)
- **SDKs & repos:** Python NETCONF client used underneath PyEZ and many vendor SDKs
- **Downloadable / offline:** Sphinx docs

### pyATS / Genie (Cisco)

- **Docs:** [developer.cisco.com/pyats](https://developer.cisco.com/pyats/)
- **Developer / API:** [pubhub.devnetcloud.com/media/pyats/docs](https://pubhub.devnetcloud.com/media/pyats/docs/)
- **GitHub:** [github.com/CiscoTestAutomation](https://github.com/CiscoTestAutomation)
- **SDKs & repos:** Test automation + parsers for 100s of show commands across vendors
- **Downloadable / offline:** Docs on pubhub; pip-installable
- *Note:* Free for all, not Cisco-only

### gNMIc

- **Docs:** [gnmic.openconfig.net](https://gnmic.openconfig.net/)
- **Developer / API:** [gnmic.openconfig.net/user_guide/…](https://gnmic.openconfig.net/user_guide/configuration_intro/)
- **GitHub:** [github.com/openconfig/gnmic](https://github.com/openconfig/gnmic)
- **SDKs & repos:** gNMI CLI + collector with Prometheus/Kafka/InfluxDB outputs
- **Downloadable / offline:** MkDocs site; single Go binary


## 17. Embedded / router operating systems

### OpenWrt

- **Docs:** [openwrt.org/docs/start](https://openwrt.org/docs/start)
- **Developer / API:** [openwrt.org/docs/guide-developer/start](https://openwrt.org/docs/guide-developer/start)
- **GitHub:** [github.com/openwrt/openwrt](https://github.com/openwrt/openwrt)
- **SDKs & repos:** UCI config system, ubus IPC, LuCI, full SDK + ImageBuilder
- **Downloadable / offline:** Wiki exportable; SDK/ImageBuilder tarballs per target
- *Note:* Powers a huge share of SMB/CPE gear

### hostapd / wpa_supplicant

- **Docs:** [w1.fi/hostapd](https://w1.fi/hostapd/)
- **Developer / API:** [w1.fi/wpa_supplicant](https://w1.fi/wpa_supplicant/)
- **GitHub:** [w1.fi/cgit/hostap](https://w1.fi/cgit/hostap/)
- **SDKs & repos:** The Wi-Fi AP/station reference implementation; control interface API
- **Downloadable / offline:** Source tarballs + man pages

### SONiC — see section 7

- **Docs:** [sonic-net.github.io/SONiC](https://sonic-net.github.io/SONiC/)
- **GitHub:** [github.com/sonic-net/SONiC](https://github.com/sonic-net/SONiC)


## 18. Education & reference implementations

Two tracks: **Basic** for building fundamentals, **Advanced** for reading and extending real implementations. Everything here is free and publicly accessible.


### Basic

*64 resources across 7 topics.*


#### Start here — free, complete books

- **[Beej's Guide to Network Programming](https://beej.us/guide/bgnet/html/)** — The classic free intro to BSD sockets in C. Read this before any other code.
- **[Computer Networks: A Systems Approach (Peterson & Davie)](https://book.systemsapproach.org/)** — Full university textbook, free and open. Source: [github.com/SystemsApproach/book](https://github.com/SystemsApproach/book)
- **[High Performance Browser Networking (Ilya Grigorik)](https://hpbn.co/)** — Free O'Reilly book on TCP, TLS, UDP, HTTP/2, WebRTC from the performance angle.
- **[The Internet Explained From First Principles](https://explained-from-first-principles.com/internet/)** — One enormous, superbly-referenced page covering the whole stack.
- **[Linux Network Administrators Guide](https://tldp.org/LDP/nag2/index.html)** — Dated but still the clearest explanation of Linux networking fundamentals.
- **[Nmap Network Scanning (free online)](https://nmap.org/book/)** — The full book, free — also the best practical guide to host/port discovery.


#### Protocol fundamentals — the RFCs you should actually read

- **[RFC 1180 — A TCP/IP Tutorial](https://www.rfc-editor.org/rfc/rfc1180.html)** — The gentlest possible on-ramp. Start here.
- **[RFC 791 — Internet Protocol (IPv4)](https://www.rfc-editor.org/rfc/rfc791.html)** — The original IP spec, still readable.
- **[RFC 826 — ARP](https://www.rfc-editor.org/rfc/rfc826.html)** — Three pages. Explains the whole L2/L3 binding problem.
- **[RFC 768 — UDP](https://www.rfc-editor.org/rfc/rfc768.html)** — Three pages, and most of it is the header diagram.
- **[RFC 9293 — TCP (2022 consolidated spec)](https://www.rfc-editor.org/rfc/rfc9293.html)** — Supersedes RFC 793. This is the TCP spec to read today.
- **[RFC 1122 — Requirements for Internet Hosts](https://www.rfc-editor.org/rfc/rfc1122.html)** — What a correct host implementation must do. Hugely clarifying.
- **[RFC 1034 — DNS concepts](https://www.rfc-editor.org/rfc/rfc1034.html)** — Pair with RFC 1035 for the wire format.
- **[RFC 2131 — DHCP](https://www.rfc-editor.org/rfc/rfc2131.html)**
- **[RFC 8200 — IPv6](https://www.rfc-editor.org/rfc/rfc8200.html)**
- **[RFC 9110 — HTTP Semantics](https://www.rfc-editor.org/rfc/rfc9110.html)** — The 2022 rewrite of the HTTP core.
- **[RFC index & bulk download](https://www.rfc-editor.org/retrieve/bulk/)** — Grab the entire RFC series for offline reading.
- **[IETF Datatracker](https://datatracker.ietf.org/)** — Track drafts, working groups, and the standards process itself.
- **[IANA protocol registries](https://www.iana.org/protocols)** — The authoritative list of every port, protocol number, and code point.


#### Visual / intuitive explainers

- **[Julia Evans' networking zines](https://wizardzines.com/)** — Short illustrated guides on tcpdump, DNS, TLS, containers and networking.
- **[Julia Evans' blog](https://jvns.ca/)** — Deep-but-friendly posts on how networking actually behaves in practice.
- **[How DNS Works (comic)](https://howdns.works/)** — A recursive-resolution walkthrough you'll never forget.
- **[HTTP/3 Explained (Daniel Stenberg)](https://http3-explained.haxx.se/)** — Free book on QUIC and HTTP/3 by the curl author.
- **[Practical Networking](https://www.practicalnetworking.net/)** — Excellent free article series — especially the 'Stateless vs Stateful' and TLS pieces.
- **[Ben Eater (YouTube)](https://www.youtube.com/@BenEater)** — Builds a network stack and Ethernet from first principles on breadboards.


#### Hands-on labs you can run today

- **[Wireshark sample captures](https://wiki.wireshark.org/SampleCaptures)** — Hundreds of real pcaps covering nearly every protocol.
- **[Kurose & Ross Wireshark labs](https://gaia.cs.umass.edu/kurose_ross/wireshark.php)** — Structured capture-and-analyse exercises mapped to the textbook.
- **[Netresec public PCAP index](https://www.netresec.com/?page=PcapFiles)** — Large curated index of publicly available packet captures.
- **[Containerlab quickstart](https://containerlab.dev/quickstart/)** — Spin up a real multi-vendor topology in about five minutes.
- **[Learn SR Linux tutorials](https://learn.srlinux.dev/tutorials/)** — Free, container-based, no licence — the easiest way into a modern NOS.
- **[Mininet walkthrough](https://mininet.org/walkthrough/)** — Emulate a whole SDN topology on one laptop.
- **[OpenFlow tutorial (Mininet)](https://github.com/mininet/openflow-tutorial/wiki)** — The original hands-on SDN introduction.
- **[Hurricane Electric IPv6 Certification](https://ipv6.he.net/certification/)** — Free, graded, genuinely teaches you IPv6 by making you deploy it.
- **[LARTC — Linux Advanced Routing & Traffic Control HOWTO](https://lartc.org/)** — Still the reference for `ip`, policy routing and `tc`.


#### Free vendor training & developer learning

- **[Cisco DevNet Learning Labs](https://developer.cisco.com/learning/)** — Free guided labs for APIs, Python, NETCONF, model-driven telemetry.
- **[Cisco Networking Academy](https://www.netacad.com/)** — Free intro networking/CCNA-track courses.
- **[Juniper Learning Portal](https://learningportal.juniper.net/)** — Free Open Learning tracks and Day One books.
- **[Arista training](https://www.arista.com/en/training)** — Free EOS and CloudVision self-paced content.
- **[Kirk Byers' free Python for Network Engineers](https://pynet.twb-tech.com/)** — The course that got most network engineers into automation. Repo: [github.com/ktbyers/pynet](https://github.com/ktbyers/pynet)
- **[Awesome Network Automation](https://github.com/networktocode/awesome-network-automation)** — Curated index of tools, talks, books and communities.


#### University courses — undergraduate, full public materials

- **[Stanford CS144 — Introduction to Computer Networking](https://cs144.github.io/)** — The single best self-study course in this field. Lectures, slides and labs are fully public, and you finish with a working TCP in C++.
- **[CS144 lab handouts (PDF)](https://cs144.github.io/assignments/check0.pdf)** — Start at Checkpoint 0 (`webget`) and build up through Checkpoint 7 to a complete TCP. Skeleton code: [github.com/cs144](https://github.com/cs144)
- **[Berkeley CS168 — The Internet: Architecture and Protocols](https://cs168.io/)** — Full public site with lecture notes, discussions and projects. Exceptionally well-written notes.
- **[Berkeley EE122 — Introduction to Communication Networks](https://inst.eecs.berkeley.edu/~ee122/)** — Older but complete archive of slides and assignments.
- **[Brown CSCI 1680 — Computer Networks](https://cs.brown.edu/courses/csci1680/)** — Assignments have you implement IP and TCP from scratch; handouts are public.
- **[CMU 15-441 — Computer Networks](https://www.cs.cmu.edu/~prs/15-441-F16/)** — The famous project sequence: build a router, a reliable transport, and a P2P app.
- **[Princeton COS 461 — Computer Networks](https://www.cs.princeton.edu/courses/archive/spring20/cos461/)** — Taught by the authors of much of the SDN literature. Also: [cs.princeton.edu/courses/…](https://www.cs.princeton.edu/courses/archive/spring18/cos461/)
- **[UW CSE 461 — Introduction to Computer Communication Networks](https://courses.cs.washington.edu/courses/cse461/)** — Every offering's slides and projects are archived publicly.
- **[UCSD CSE 123 — Computer Networks](https://cseweb.ucsd.edu/classes/sp23/cse123-a/)** — Clear lecture decks and a router-building project.
- **[UIUC CS/ECE 438 — Communication Networks](https://courses.engr.illinois.edu/cs438/)** — Public course site with MPs (machine problems) in C.
- **[Cambridge — Computer Networking (Part IB)](https://www.cl.cam.ac.uk/teaching/2425/CompNet/)** — Concise, rigorous British-style lecture notes.
- **[ETH Zürich — Communication Networks](https://comm-net.ethz.ch/)** — Outstanding public course site: slides, videos, and a mini-internet project where students run real ASes and peer with each other.
- **[UMass — Kurose & Ross companion site](https://gaia.cs.umass.edu/kurose_ross/index.php)** — Slides, interactive problems and the Wireshark lab set for the standard textbook.


#### Open courseware & MOOCs (free to audit)

- **[MIT OpenCourseWare — networking courses](https://ocw.mit.edu/search/?q=computer+networks)** — Full lecture notes, assignments and exams, no enrolment.
- **[MIT 6.829 — Computer Networks (OCW archive)](https://ocw.mit.edu/courses/6-829-computer-networks-fall-2002/)** — Complete graduate course materials, free.
- **[MIT 6.02 — Digital Communication Systems](https://ocw.mit.edu/courses/6-02-introduction-to-eecs-ii-digital-communication-systems-fall-2012/)** — Starts at bits-on-a-wire and works up to networks — great for filling in physical-layer gaps.
- **[MIT 6.033 — Computer System Engineering](https://ocw.mit.edu/courses/6-033-computer-system-engineering-spring-2018/)** — The systems-design reasoning that underpins network architecture.
- **[NPTEL — Computer Networks and Internet Protocol (IIT Kharagpur)](https://nptel.ac.in/courses/106105183)** — Free, full-semester Indian university course with video lectures and graded assignments.
- **[NPTEL — Computer Networks (IIT Kharagpur, classic)](https://nptel.ac.in/courses/106105081)** — Long-running reference course; all videos free.
- **[NPTEL — Computer Networks (IISc/IIT Madras)](https://nptel.ac.in/courses/106106091)** — Alternative treatment, also free.
- **[NPTEL online certification](https://onlinecourses.nptel.ac.in/e-learning/preview/noc24_cs35)** — Run the course with deadlines and an optional proctored certificate.
- **[Coursera — Computer Communications specialisation](https://www.coursera.org/learn/computer-networking)** — Free to audit.
- **[edX — computer networking catalogue](https://www.edx.org/learn/computer-networking)** — University-run courses, most free to audit.
- **[Georgia Tech CS 6250 — Computer Networks (OMSCS)](https://omscs.gatech.edu/cs-6250-computer-networks)** — Syllabus and project list are public; the SDN/Mininet assignments are widely mirrored.


### Advanced

*132 resources across 14 topics.*


#### Reference TCP/IP stack implementations (read the source)

- **[Linux kernel `net/` tree](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/net)** — The reference implementation for most of the modern internet.
- **[Linux networking docs](https://docs.kernel.org/networking/)** — Maintainer-written docs for every subsystem: netlink, XDP, switchdev, DSA, tc.
- **[CS144 Minnow — build your own TCP](https://github.com/cs144)** — C++ skeleton + tests; finish it and you have a real, interoperable TCP.
- **[lwIP — lightweight TCP/IP](https://github.com/lwip-tcpip/lwip)** — The embedded-systems standard TCP/IP stack. The Savannah project page was unreachable from our network; git mirror at [cgit.git.savannah.nongnu.org/cgit/lwip.git](https://cgit.git.savannah.nongnu.org/cgit/lwip.git)
- **[picoTCP](https://github.com/tass-belgium/picotcp)** — Small, modular, readable embedded stack.
- **[smoltcp (Rust)](https://github.com/smoltcp-rs/smoltcp)** — Heapless, `no_std` stack — exceptionally clean code. Docs: [docs.rs/smoltcp](https://docs.rs/smoltcp/)
- **[gVisor netstack (Go)](https://github.com/google/gvisor/tree/master/pkg/tcpip)** — A complete userspace TCP/IP stack in Go; used in production at Google.


#### QUIC, HTTP/3 and transport research

- **[RFC 9000 — QUIC transport](https://www.rfc-editor.org/rfc/rfc9000.html)**
- **[RFC 9114 — HTTP/3](https://www.rfc-editor.org/rfc/rfc9114.html)**
- **[Cloudflare quiche (Rust)](https://github.com/cloudflare/quiche)** — Production QUIC + HTTP/3, powers Cloudflare's edge.
- **[quic-go](https://github.com/quic-go/quic-go)** — The Go reference implementation.
- **[Microsoft MsQuic (C)](https://github.com/microsoft/msquic)** — Cross-platform, used in Windows and .NET.
- **[ngtcp2](https://github.com/ngtcp2/ngtcp2)** — C implementation paired with nghttp3.
- **[picoquic](https://github.com/private-octopus/picoquic)** — Minimal research-grade implementation — good for reading.
- **[LSQUIC](https://github.com/litespeedtech/lsquic)**
- **[Google BBR congestion control](https://github.com/google/bbr)** — Source, papers and measurement data for BBR v1–v3.


#### Kernel-bypass & high-performance datapaths

- **[eBPF.io](https://ebpf.io/)** — The hub for eBPF concepts, projects and learning paths.
- **[Linux BPF documentation](https://docs.kernel.org/bpf/)** — Verifier, maps, program types — authoritative.
- **[XDP hands-on tutorial](https://github.com/xdp-project/xdp-tutorial)** — Progressive lessons from 'drop a packet' to a working XDP router.
- **[libbpf](https://github.com/libbpf/libbpf)** — The canonical C loader library; CO-RE lives here.
- **[cilium/ebpf (Go)](https://github.com/cilium/ebpf)** — Pure-Go eBPF library — the usual choice for Go tooling.
- **[BCC toolkit](https://github.com/iovisor/bcc)** — Dozens of ready-made tracing tools; great for reading real BPF programs.
- **[Katran (Meta)](https://github.com/facebookincubator/katran)** — XDP-based L4 load balancer handling internet-scale traffic.
- **[DPDK sample applications](https://doc.dpdk.org/guides/sample_app_ug/)** — l3fwd, ipsec-secgw, pipeline — the canonical fast-path examples.
- **[FD.io VPP](https://s3-docs.fd.io/vpp/)** — Vector packet processing; a full userspace router you can read and extend.
- **[netmap](https://github.com/luigirizzo/netmap)** — The original high-rate packet I/O framework; the paper is essential reading.
- **[Snabb](https://github.com/snabbco/snabb)** — Networking toolkit written in LuaJIT — surprisingly fast and very readable.
- **[Click Modular Router](https://github.com/kohler/click)** — The research router architecture that influenced everything after it.


#### Programmable data planes & switch abstraction

- **[P4 tutorials](https://github.com/p4lang/tutorials)** — Hands-on exercises: build a router, ECMP, INT, load balancer in P4.
- **[P4 specifications](https://github.com/p4lang/p4-spec)** — P4_16 language spec, PSA, PNA, portable architectures.
- **[BMv2 behavioural model](https://github.com/p4lang/behavioral-model)** — Software P4 target — your test bench.
- **[P4Runtime](https://github.com/p4lang/p4runtime)** — The control-plane API for P4 targets.
- **[Stratum](https://github.com/stratum/stratum)** — Thin switch OS exposing P4Runtime/gNMI/gNOI — a reference SDN NOS.
- **[SAI — Switch Abstraction Interface](https://github.com/opencomputeproject/SAI)** — The vendor-neutral ASIC API underneath SONiC. Read `inc/` first.
- **[ONIE](https://github.com/opencomputeproject/onie)** — Open Network Install Environment — how whitebox switches boot.
- **[OCP Networking project](https://www.opencompute.org/projects/networking)** — Open hardware specs for switches and optics.
- **[Linux switchdev](https://docs.kernel.org/networking/switchdev.html)** — How hardware switch offload works in the kernel.
- **[Linux DSA](https://docs.kernel.org/networking/dsa/)** — Distributed Switch Architecture for embedded switch chips.


#### Routing protocol implementations to study

- **[FRRouting](https://github.com/FRRouting/frr)** — The most widely deployed open routing stack. Dev guide: [docs.frrouting.org/projects/…](https://docs.frrouting.org/projects/dev-guide/en/latest/)
- **[BIRD](https://gitlab.nic.cz/labs/bird)** — Compact, fast, heavily used at IXPs and route servers.
- **[OpenBGPD](https://www.openbgpd.org/)** — OpenBSD's BGP daemon — famously clean, security-first C.
- **[GoBGP](https://github.com/osrg/gobgp)** — BGP in Go with a gRPC API; ideal base for building a controller. Docs: [github.com/osrg/gobgp/tree/master/docs](https://github.com/osrg/gobgp/tree/master/docs)
- **[RustyBGP](https://github.com/osrg/rustybgp)** — Async Rust BGP implementation from the GoBGP author.
- **[ExaBGP](https://github.com/Exa-Networks/exabgp)** — Turns BGP into a text/JSON API — the standard tool for route injection and anycast health checks.
- **[Holo](https://github.com/holo-routing/holo)** — Rust, YANG-native routing stack with NETCONF/gRPC — the most modern design here.
- **[XORP](https://github.com/greearb/xorp.ct)** — Historic extensible routing platform; still instructive architecturally.
- **[RFC 4271 — BGP-4](https://www.rfc-editor.org/rfc/rfc4271.html)**
- **[RFC 2328 / RFC 5340 — OSPFv2 / OSPFv3](https://www.rfc-editor.org/rfc/rfc2328.html)** — v3: [rfc-editor.org/rfc/rfc5340.html](https://www.rfc-editor.org/rfc/rfc5340.html)
- **[RFC 1195 — IS-IS for IP](https://www.rfc-editor.org/rfc/rfc1195.html)**
- **[RFC 5880 — BFD](https://www.rfc-editor.org/rfc/rfc5880.html)**


#### Overlays, fabrics & segment routing

- **[RFC 7348 — VXLAN](https://www.rfc-editor.org/rfc/rfc7348.html)**
- **[RFC 8926 — Geneve](https://www.rfc-editor.org/rfc/rfc8926.html)**
- **[RFC 7432 — BGP MPLS-based EVPN](https://www.rfc-editor.org/rfc/rfc7432.html)**
- **[RFC 8365 — EVPN as a network virtualisation overlay](https://www.rfc-editor.org/rfc/rfc8365.html)** — The EVPN-VXLAN fabric blueprint.
- **[RFC 8402 — Segment Routing architecture](https://www.rfc-editor.org/rfc/rfc8402.html)**
- **[RFC 8986 — SRv6 network programming](https://www.rfc-editor.org/rfc/rfc8986.html)**
- **[RFC 3031 — MPLS architecture](https://www.rfc-editor.org/rfc/rfc3031.html)**
- **[Open vSwitch internals](https://github.com/openvswitch/ovs/tree/master/lib)** — Megaflow caching and the userspace/kernel split are worth studying.
- **[OVN](https://docs.ovn.org/)** — Logical network abstraction built on OVS; the model behind many clouds.
- **[SONiC architecture docs](https://github.com/sonic-net/SONiC/tree/master/doc)** — Per-feature high-level design docs — a rare look inside a production NOS.


#### Model-driven networking: YANG, NETCONF, gNMI

- **[RFC 7950 — YANG 1.1](https://www.rfc-editor.org/rfc/rfc7950.html)**
- **[RFC 6241 — NETCONF](https://www.rfc-editor.org/rfc/rfc6241.html)**
- **[RFC 8040 — RESTCONF](https://www.rfc-editor.org/rfc/rfc8040.html)**
- **[RFC 8345 — Network topology data model](https://www.rfc-editor.org/rfc/rfc8345.html)**
- **[YangModels/yang — the public model repository](https://github.com/YangModels/yang)** — Standard and vendor YANG models, all in one place.
- **[OpenConfig models](https://github.com/openconfig/public)** — The cross-vendor model set. Releases: [github.com/openconfig/public/releases](https://github.com/openconfig/public/releases)
- **[gNMI reference](https://github.com/openconfig/gnmi)** — Protobuf definitions and Go reference client/server.
- **[gNOI](https://github.com/openconfig/gnoi)** — Operational RPCs: reboot, cert rotation, file transfer, ping.
- **[ygot](https://github.com/openconfig/ygot)** — Generate Go structs from YANG — how most gNMI tooling is built.
- **[KNE — Kubernetes Network Emulation](https://github.com/openconfig/kne)** — Run vendor NOS containers in K8s for model/API conformance testing.
- **[Ondatra + FeatureProfiles](https://github.com/openconfig/featureprofiles)** — OpenConfig's vendor-conformance test suite — the real interop benchmark.
- **[libyang](https://github.com/CESNET/libyang)** — The C YANG parser nearly everything else links against.
- **[sysrepo](https://github.com/sysrepo/sysrepo)** — YANG-backed configuration datastore.
- **[Netopeer2](https://github.com/CESNET/netopeer2)** — Reference NETCONF server implementation.
- **[pySROS (Nokia)](https://github.com/nokia/pysros)** — Vendor model-driven Python SDK worth reading as a design example.
- **[gnxi](https://github.com/google/gnxi)** — Reference gNMI/gNOI clients and a target implementation for testing.


#### Telemetry, flow & measurement at scale

- **[gNMIc](https://gnmic.openconfig.net/user_guide/configuration_intro/)** — Collector + CLI; the practical entry point to streaming telemetry.
- **[goflow2](https://github.com/netsampler/goflow2)** — High-throughput NetFlow/IPFIX/sFlow decoder in Go.
- **[go-ipfix (VMware)](https://github.com/vmware/go-ipfix)** — IPFIX library and collector.
- **[vflow (Verizon)](https://github.com/VerizonDigital/vflow)** — Production-scale flow collector.
- **[sFlow.org + sflowtool](https://sflow.org/)** — Spec and reference tooling: [github.com/sflow/sflowtool](https://github.com/sflow/sflowtool)
- **[Telegraf gNMI input](https://github.com/influxdata/telegraf/tree/master/plugins/inputs/gnmi)** — Reference gNMI subscription consumer.
- **[jtimon (Juniper)](https://github.com/Juniper/jtimon)** — Vendor telemetry client, useful as a protocol example.
- **[cisco-gnmi-python](https://github.com/cisco-ie/cisco-gnmi-python)**
- **[ANTA (Arista)](https://anta.arista.com/)** — Automated network test framework — a good model for validation-as-code. Repo: [github.com/aristanetworks/anta](https://github.com/aristanetworks/anta)
- **[SuzieQ](https://github.com/netenglabs/suzieq)** — Multi-vendor network observability and time-travel state queries.


#### Verification, correctness & testing

- **[Batfish](https://github.com/batfish/batfish)** — Builds a model of your network from configs and proves properties about it.
- **[pybatfish](https://github.com/batfish/pybatfish)** — Python API + notebooks; start with the 'interacting' notebook.
- **[Open Traffic Generator / snappi](https://github.com/open-traffic-generator)** — Vendor-neutral traffic-generation model backed by Keysight and others.
- **[Cisco TRex](https://github.com/cisco-system-traffic-generator/trex-core)** — DPDK stateful/stateless generator with a Python automation API.
- **[ns-3](https://gitlab.com/nsnam/ns-3-dev)** — Discrete-event simulator used for most networking research papers.
- **[OMNeT++ / INET](https://github.com/omnetpp/omnetpp)**
- **[FAUCET](https://docs.faucet.nz/en/latest/)** — Production OpenFlow controller with an unusually rigorous test suite. Repo: [github.com/faucetsdn/faucet](https://github.com/faucetsdn/faucet)
- **[Ryu](https://github.com/faucetsdn/ryu)** — The classic Python SDN controller — still the clearest OpenFlow codebase.
- **[POX](https://github.com/noxrepo/pox)** — Minimal Python OpenFlow controller, ideal for teaching.


#### RDMA, AI fabrics & time synchronisation

- **[rdma-core](https://github.com/linux-rdma/rdma-core)** — libibverbs/librdmacm userspace — the RDMA programming reference.
- **[NVIDIA NCCL](https://github.com/NVIDIA/nccl)** — Collective comms library; its topology detection is where AI-fabric design meets code.
- **[Ultra Ethernet Consortium](https://ultraethernet.org/)** — The emerging standard for AI/HPC Ethernet fabrics.
- **[NVIDIA DOCA](https://networking-docs.nvidia.com/doca/)** — DPU programming model: Flow, Comm Channel, DPA.
- **[linuxptp](https://github.com/richardcochran/linuxptp)** — IEEE 1588 PTP implementation — the reference for time sync on Linux.


#### University courses — graduate & research-level

- **[MIT 6.829 — Computer Networks](https://web.mit.edu/6.829/)** — Graduate reading list of the canonical papers, with problem sets.
- **[Stanford CS244 — Advanced Topics in Networking](https://web.stanford.edu/class/cs244/)** — The course whose entire project is *reproducing* published network research.
- **[Reproducing Network Research (CS244 project blog)](https://reproducingnetworkresearch.wordpress.com/)** — Years of student write-ups re-implementing famous papers — the best way to learn how to read a networking paper critically.
- **[CMU 15-744 — Computer Networks (graduate)](https://www.cs.cmu.edu/~dga/15-744/)** — Dave Andersen's reading list; strong on measurement and data-centre topics.
- **[Princeton COS 561 — Advanced Computer Networks](https://www.cs.princeton.edu/courses/archive/fall16/cos561/)** — Jennifer Rexford's course — SDN, verification, and programmable data planes.
- **[UW CSE 561 — Computer Communication and Networks](https://courses.cs.washington.edu/courses/cse561/)** — Graduate paper-reading course with public archives.
- **[UCSD CSE 222A — Computer Communication Networks](https://cseweb.ucsd.edu/classes/wi22/cse222A-a/)** — Research-paper seminar with a substantial systems project.
- **[ETH Zürich — Advanced Topics in Communication Networks](https://adv-net.ethz.ch/)** — P4, programmable data planes and network verification, with hands-on exercises. Code: [github.com/nsg-ethz](https://github.com/nsg-ethz)
- **[MIT 6.5840 / 6.824 — Distributed Systems](https://pdos.csail.mit.edu/6.824/)** — Not strictly networking, but essential adjacent material: Raft, replication, consistency. Labs are public.
- **[Stanford Secure Computer Systems group](https://www.scs.stanford.edu/)** — Course archives and papers on systems and network security.


#### Research papers, venues & reading lists

- **[ACM SIGCOMM](https://www.sigcomm.org/)** — The flagship networking conference; most proceedings are open access.
- **[SIGCOMM conference archives](https://conferences.sigcomm.org/sigcomm/2024/)** — Papers, slides and talk videos per year.
- **[ACM SIGCOMM Computer Communication Review](https://ccronline.sigcomm.org/)** — Short, readable papers and editorials — a good entry point to the literature.
- **[USENIX NSDI](https://www.usenix.org/conference/nsdi26)** — Networked Systems Design & Implementation; **all papers are free**. Past editions: [usenix.org/conferences/byname/178](https://www.usenix.org/conferences/byname/178)
- **[USENIX ;login:](https://www.usenix.org/publications/loginonline)** — Practitioner-facing write-ups of research results.
- **[Papers We Love](https://github.com/papers-we-love/papers-we-love)** — Curated classic CS papers including a networking section.
- **[NetSys group code (Berkeley)](https://github.com/NetSys/)** — Reference implementations accompanying published research.
- **[IRTF — Internet Research Task Force](https://www.irtf.org/)** — Where pre-standards research happens; research groups at [datatracker.ietf.org/rg](https://datatracker.ietf.org/rg/)


#### Operator, registry & standards-body training

- **[NSRC — Network Startup Resource Center](https://learn.nsrc.org/)** — Free, genuinely excellent operator-grade workshop materials on routing, DNS, IXPs and network management. Main site: [nsrc.org](https://nsrc.org/)
- **[RIPE NCC Academy](https://academy.ripe.net/)** — Free courses and certifications on IPv6, BGP, RPKI and routing security.
- **[RIPE NCC training](https://www.ripe.net/training/)** — Workshop materials and recordings.
- **[APNIC Academy](https://academy.apnic.net/)** — Free Asia-Pacific operator training — IPv6, BGP, DNSSEC, network security.
- **[Internet Society learning](https://www.internetsociety.org/learning/)** — Courses on internet infrastructure, routing security and MANRS.
- **[IETF Hackathons](https://www.ietf.org/meeting/hackathons/)** — Build running code against draft standards alongside the spec authors. Code: [github.com/IETF-Hackathon](https://github.com/IETF-Hackathon)


#### Operator-grade engineering reading

- **[APNIC Blog](https://blog.apnic.net/)** — Consistently the best technical writing on routing, DNS and measurement.
- **[RIPE Labs](https://labs.ripe.net/)** — Measurement-driven research from the RIPE NCC.
- **[Geoff Huston / Potaroo](https://www.potaroo.net/)** — Annual BGP and DNS state-of-the-internet analyses.
- **[ipSpace blog (Ivan Pepelnjak)](https://blog.ipspace.net/)** — Rigorous, opinionated, and usually right about design trade-offs.
- **[netdevops.me (Roman Dodin)](https://netdevops.me/)** — Practical modern network automation and NOS tooling.
- **[Packet Pushers](https://packetpushers.net/)** — Podcasts and write-ups across the whole industry.
- **[NANOG](https://nanog.org/)** — Operator conference — the archives and mailing list are a goldmine.
- **[ACM SIGCOMM](https://conferences.sigcomm.org/sigcomm/)** — Where most of this field's foundational papers were published.


---

## Verified direct PDF / offline bundles

These were confirmed to return `application/pdf` (or a bulk archive):

- **Junos PyEZ Developer Guide** — [juniper.net/documentation/…](https://www.juniper.net/documentation/us/en/software/junos-pyez/junos-pyez-developer/junos-pyez-developer.pdf)
- **Juniper Day One: PyEZ Cookbook** — [juniper.net/documentation/…](https://www.juniper.net/documentation/en_US/day-one-books/DO_PyEZ_Cookbook.pdf)
- **Extreme API with Python** — [documentation.extremenetworks.com/api_python/…](https://documentation.extremenetworks.com/api_python/Extreme_API.pdf)
- **Wireshark User's Guide** — [wireshark.org/download/…](https://www.wireshark.org/download/docs/Wireshark%20User%27s%20Guide.pdf)
- **BIND 9 ARM** — [bind9.readthedocs.io/_/downloads/en/latest/pdf](https://bind9.readthedocs.io/_/downloads/en/latest/pdf/)
- **ISC Kea ARM** — [kea.readthedocs.io/_/downloads/en/latest/pdf](https://kea.readthedocs.io/_/downloads/en/latest/pdf/)
- **Unbound manual** — [unbound.docs.nlnetlabs.nl/_/…](https://unbound.docs.nlnetlabs.nl/_/downloads/en/latest/pdf/)
- **Routinator manual** — [routinator.docs.nlnetlabs.nl/_/…](https://routinator.docs.nlnetlabs.nl/_/downloads/en/stable/pdf/)
- **Suricata manual** — [docs.suricata.io/_/downloads/en/latest/pdf](https://docs.suricata.io/_/downloads/en/latest/pdf/)
- **Scapy manual** — [scapy.readthedocs.io/_/downloads/en/latest/pdf](https://scapy.readthedocs.io/_/downloads/en/latest/pdf/)
- **Open vSwitch manual** — [docs.openvswitch.org/_/downloads/en/latest/pdf](https://docs.openvswitch.org/_/downloads/en/latest/pdf/)
- **OVN manual** — [docs.ovn.org/_/downloads/en/latest/pdf](https://docs.ovn.org/_/downloads/en/latest/pdf/)
- **NAPALM manual** — [napalm.readthedocs.io/_/…](https://napalm.readthedocs.io/_/downloads/en/latest/pdf/)
- **Netmiko manual** — [netmiko.readthedocs.io/_/…](https://netmiko.readthedocs.io/_/downloads/en/latest/pdf/)
- **srsRAN manual** — [docs.srsran.com/_/downloads/en/latest/pdf](https://docs.srsran.com/_/downloads/en/latest/pdf/)
- **ns-3 manual** — [nsnam.org/docs/…](https://www.nsnam.org/docs/release/3.41/manual/ns-3-manual.pdf)
- **RFC bulk download** — [rfc-editor.org/retrieve/bulk](https://www.rfc-editor.org/retrieve/bulk/)
- **OpenConfig model releases** — [github.com/openconfig/public/releases](https://github.com/openconfig/public/releases)
- **SONiC HLD design docs** — [github.com/sonic-net/SONiC/tree/master/doc](https://github.com/sonic-net/SONiC/tree/master/doc)

### Offline-doc tricks worth knowing

- **Read the Docs projects**: append `/_/downloads/en/latest/pdf/` to the docs root for a PDF, or `/htmlzip/` for an offline HTML bundle. Works for NAPALM, Netmiko, Scapy, Suricata, BIND, Kea, Unbound, Routinator, OVS, OVN, srsRAN.
- **MkDocs/Sphinx projects on GitHub** (NetBox, Nautobot, containerlab, LibreNMS, Cilium, FRR): `git clone` the repo and build locally — the `docs/` tree is the site.
- **Vendor portals** (Cisco, Fortinet, Palo Alto, F5, NetScaler, Juniper, Extreme, Aruba): nearly every guide page has a **PDF / Download** button in the top-right of the doc viewer.
- **Arista**: full EOS User Manual is published as a single PDF and ePub per release from the product-documentation page.
- **OpenWrt**: use the per-target **ImageBuilder** and **SDK** tarballs for fully offline builds; the wiki exports via `/_export/xhtmlbody/<page>`.

## Recent ownership / branding changes to be aware of

- **Infinera → Nokia** (closed 2025). `infinera.com` now 301s to Nokia Optical Networks.
- **RUCKUS**: CommScope → renamed **Vistance Networks** (Jan 2026) → sold to **Belden** (closed 1 Jul 2026). Docs still at `docs.ruckus.cloud`; `developer.ruckuswireless.com` no longer resolves.
- **Spirent → Keysight**. `spirent.com` and `support.spirent.com` now redirect into keysight.com.
- **NS1 → IBM**. API docs moved to the IBM developer API catalog.
- **ADVA → Adtran** (merged 2022); **ECI → Ribbon**.
- **Cradlepoint → Ericsson**; **Silver Peak → HPE Aruba**; **Pensando → AMD**; **Mellanox/Cumulus → NVIDIA**.
- **OpenZiti docs** moved under `netfoundry.io/docs/openziti/`.

## If you only bookmark ten

1. **pan.dev** (Palo Alto) — every OpenAPI spec public, no login.
2. **developer.cisco.com** — docs + free always-on sandboxes + Code Exchange.
3. **learn.srlinux.dev** (Nokia) — docs-as-code, open repo, free container image.
4. **developer.cisco.com/meraki** — complete REST docs, first-party SDKs, zero gating.
5. **developer.extremecloudiq.com** — OpenAPI 3.0 with generated SDKs in five languages.
6. **developer.arubanetworks.com** — 50+ public repos, seven first-party Python SDKs.
7. **openconfig.net** + **github.com/openconfig** — the vendor-neutral model layer.
8. **containerlab.dev** — lab anything from any vendor in minutes.
9. **docs.netbox.dev** — source of truth everything else plugs into.
10. **sonic-net.github.io/SONiC** — the open NOS the hyperscalers actually run.

---

## Related sections of this book

- [Computer Networks](../networks/overview.md) — the explanatory chapters this index points out from
- [Reference Libraries index](./README.md) — the other topic indexes
