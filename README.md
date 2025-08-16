# Network Monitor

A lightweight **network monitoring tool** built with **Python** and **Flask**, designed to check the health of network devices through **ping** and **SNMP polling**, and present results on a simple **web dashboard**.

---

##  Overview

This project monitors network devices and provides visibility into their current status. It performs:

- **Reachability checks** via ICMP (ping)  
- **SNMP polling** to collect metrics such as:  
  - Device uptime  
  - Interface operational status  
  - CPU utilization  
  - Storage usage  
- **Logging** of network events and errors for troubleshooting  
- **Web dashboard** to display real-time device status using Flask  
- **API endpoint** (`/api/status`) to retrieve device health in JSON format  

Devices are configured in a YAML file (`devices.yaml`), making the system easily extensible to new network nodes.

---

##  Features

-  **Ping-based reachability detection**  
-  **SNMP v2c support** for metrics collection  
-  **Formatted uptime, CPU, and disk usage** reporting  
-  **Logs stored in `network_monitor.log`** for auditing & troubleshooting  
-  **Web-based dashboard** (Flask + Jinja2 templates)  
-  **REST API endpoint** for programmatic access to device health  
-  **Dockerized setup** for easy deployment  

---

##  Skills & Technologies Demonstrated

- **Python Development**
  - Network automation & monitoring (`ping3`, `pysnmp`)  
  - Data formatting for uptime, storage, CPU metrics  
  - Structured logging with `logging`  

- **Flask Web Development**
  - REST API (`/api/status`)  
  - Web dashboard with Jinja2 templating  

- **Configuration Management**
  - YAML-based device definitions (`devices.yaml`)  
  - `.env` environment variable handling with `python-dotenv`  

- **Containerization**
  - `Dockerfile` for packaging the app into a portable container  
  - Deployment-ready for cloud or on-prem environments  

- **Monitoring & Alerting Foundations**
  - Health checks  
  - Log analysis  
  - Extensible architecture for email/SMS alert integration  

---

##  Future Improvements

- Email/SMS alerting for downtime events
- Support for SNMPv3 authentication
- Telemetry based monitoring
