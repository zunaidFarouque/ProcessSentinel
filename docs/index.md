# ProcessSentinel 2.0 — Documentation & User Guide

Welcome to the official documentation for **ProcessSentinel 2.0**, a modular, rule-based Windows watchdog engine and desktop dashboard designed for monitoring long-running computational batches, background daemons, simulations, and lab workstation health.

ProcessSentinel operates silently in the background, continuously evaluating user-defined conditions, and instantly dispatches rich mobile push notifications directly to your smartphone or desktop via [ntfy.sh](https://ntfy.sh).

---

## 📑 Documentation Index

Explore the documentation guides below:

1. **[Getting Started & Portable Setup](getting-started.md)**  
   System requirements, portable installation, folder structure, and first-time setup walkthrough.
2. **[Mobile Push Notifications Setup (Android & iOS)](mobile-setup.md)**  
   Step-by-step instructions for installing the free, privacy-friendly ntfy mobile app, subscribing to topics, and receiving instant alerts.
3. **[Complete Monitors Guide & Reference](monitors-guide.md)**  
   Detailed catalog of all 8 monitor types, their exact configuration parameters, operational logic, and state management.
4. **[Notification Channels & Alert Routing](channels-and-routing.md)**  
   How topic aliases work, setting a global default channel, and overriding channels per monitor.
5. **[Real-World Use Cases & Cookbooks](use-cases.md)**  
   Practical setup recipes for 3D render batches, machine learning training runs, GIS/CAD data pipelines, and database servers.
6. **[Configuration & Backup Guide](configuration.md)**  
   How `config.json` is persisted, the automatic self-healing backup system, and exporting/importing configurations across workstations.
7. **[Release Engineering & Maintainer Guide](release-guide.md)**  
   Automated packaging, release scripts (`release.ps1` / `release.bat`), and Scoop bucket synchronization.

---

## 🎯 What Makes ProcessSentinel Different?

Unlike traditional generic server monitors or simple task checkers, ProcessSentinel was engineered specifically for workstation workloads and laboratory automation:

* **Stateful High-Watermark Tracking:** When running batch simulations that close windows one by one (e.g. 10 → 9 → 8), ProcessSentinel detects each downward transition without spamming duplicate alerts, and sends a critical alert when the entire batch concludes.
* **I/O Heartbeat Stall Detection:** Many crashed or deadlocked processes remain running in Task Manager with 0% CPU without exiting. ProcessSentinel tracks target output files/logs and alerts you if writing ceases beyond a freshness window.
* **Cascading Storage Warnings:** Multi-tiered storage monitoring alerts you early (e.g. Warning at 50 GB, Critical at 20 GB, Fatal at 5 GB) so overnight renders or training logs don't fill your NVMe SSD.
* **Zero Cloud Sign-Up Required:** Uses open-source `ntfy.sh` (or your own self-hosted ntfy server) for push notifications. No accounts, API tokens, credit cards, or passwords required.
* **100% Truly Portable:** Runs without installation. The `.exe`, `config.json`, and supporting libraries remain contained in their own portable directory.
* **Non-Blocking Modern UI:** Built with CustomTkinter. Network tests, background polling, and configuration transfers happen asynchronously so the interface stays snappy.

---

## 🚀 Quick Start in 60 Seconds

1. **Launch `ProcessSentinel.exe`**: The dashboard opens in Dark Mode.
2. **Configure Your Mobile Channel**:
   * Switch to the **Notification Channels** tab.
   * Enter your desired topic name (e.g., `https://ntfy.sh/my-custom-lab-watch-99`).
   * Click **Test Alert** to verify your phone receives the alert instantly.
3. **Add a Monitor**:
   * Switch to the **Active Monitors** tab and click **+ Add New Monitor**.
   * Pick any monitor (e.g., *Storage Free Space* on `C:` or *Process Step-Down* for `blender.exe`).
4. **Click "▶ START ENGINE"**:
   * The status changes to **● RUNNING**. ProcessSentinel is now actively safeguarding your tasks!

---

*Need assistance or found a bug? Check out the [GitHub Issues](https://github.com/zunaidFarouque/ProcessSentinel/issues).*
