# DataSaaS Pro Platform Compatibility Matrix (v1.0.0-rc3)

This document outlines the supported operating systems, web browsers, and hardware requirements verified for the DataSaaS Pro platform release.

---

## 💻 Operating System Compatibility

The Dockerised environment has been tested and validated across the following platforms:

| Operating System | Engine Host | Docker Version | Compatibility Status |
| :--- | :--- | :---: | :---: |
| **Windows 10 / 11** | WSL2 (Ubuntu 22.04 backend) | 29.5.x | **Fully Compatible** |
| **Ubuntu 20.04 / 22.04 LTS**| Native Docker Engine | 26.x / 27.x / 29.x | **Fully Compatible** |
| **macOS (Intel & Apple Silicon)**| Docker Desktop (Lima/Rosetta) | 27.x+ | **Fully Compatible** |

---

## 🌐 Web Browser Compatibility

The React frontend UI has been verified for styling compliance, DOM performance, dynamic chart renderings, and API request handling:

| Browser | OS Platform | Rendering Engine | Compatibility Status | Verified Features |
| :--- | :--- | :---: | :---: | :--- |
| **Google Chrome (v115+)** | Windows, Ubuntu, macOS | Blink | **Fully Compatible** | AG-Grid scrolling, Framer-motion transitions, SSE and WebSockets. |
| **Mozilla Firefox (v110+)**| Windows, Ubuntu, macOS | Gecko | **Fully Compatible** | SVG asset scaling, file dropzone overlays, file download streams. |
| **Microsoft Edge (v115+)** | Windows, macOS | Blink | **Fully Compatible** | Chart.js canvases rendering, dark-mode styling triggers. |
| **Apple Safari (v16+)** | macOS, iOS | WebKit | **Compatible** | Basic grid animations and report generation exports. |

---

## 🔌 Hardware Resource Specifications

To ensure optimal Polars database processing and AutoML models compilation:

* **Minimum Specifications**:
  * **CPU**: Dual-Core x86_64 or ARM64 processor (e.g. Apple M1).
  * **RAM**: 8 GB physical memory (allowing 4 GB allocation for Celery/FastAPI Docker containers).
  * **Disk Space**: 10 GB free storage (to accommodate Docker image caches and datasets).
* **Recommended Specifications**:
  * **CPU**: Quad-Core processor or higher.
  * **RAM**: 16 GB physical memory.
  * **Disk Space**: 20 GB solid-state drive (SSD).
