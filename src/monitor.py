import logging
from ping3 import ping
from pysnmp.hlapi import (
    getCmd,
    SnmpEngine,
    CommunityData,
    UdpTransportTarget,
    ContextData,
    ObjectType,
    ObjectIdentity,
)
import yaml
import time
from datetime import datetime

# --- Logging Setup ---
logging.basicConfig(
    filename='network_monitor.log',
    format='%(asctime)s [%(levelname)s] %(message)s',
    level=logging.INFO
)

# --- Load Devices ---
def load_devices(config_file='devices.yaml'):
    with open(config_file, 'r') as f:
        config = yaml.safe_load(f)
    return config.get('devices', [])

# --- Ping Status Check ---
def is_reachable(ip):
    response = ping(ip, timeout=2)
    return response is not None

# --- SNMP Uptime Poll ---
def get_snmp_uptime(ip, community):
    iterator = getCmd(
        SnmpEngine(),
        CommunityData(community, mpModel=0),  # SNMP v2c
        UdpTransportTarget((ip, 161), timeout=2, retries=1),
        ContextData(),
        ObjectType(ObjectIdentity('1.3.6.1.2.1.1.3.0'))  # sysUpTime
    )

    errorIndication, errorStatus, errorIndex, varBinds = next(iterator)
    if errorIndication:
        logging.warning(f"SNMP error on {ip}: {errorIndication}")
        return None
    elif errorStatus:
        logging.warning(f"SNMP status error on {ip}: {errorStatus.prettyPrint()}")
        return None
    else:
        for varBind in varBinds:
            return str(varBind[1])  # Uptime string

# --- Poll One Device ---
def poll_device(device):
    name = device['name']
    ip = device['ip']
    reachable = is_reachable(ip)

    if reachable:
        status_msg = f"{name} ({ip}) is UP"
        logging.info(status_msg)

        if device.get('snmp'):
            uptime = get_snmp_uptime(ip, device['community'])
            if uptime:
                logging.info(f"{name} SNMP Uptime: {uptime}")
            else:
                logging.warning(f"{name} SNMP Uptime could not be retrieved.")
    else:
        status_msg = f"{name} ({ip}) is DOWN"
        logging.error(status_msg)

# --- Main Loop ---
def poll_all_devices(devices):
    logging.info("Starting network polling cycle...")
    for device in devices:
        try:
            poll_device(device)
        except Exception as e:
            logging.exception(f"Error polling {device['name']}: {e}")
    logging.info("Polling cycle complete.\n")

if __name__ == "__main__":
    devices = load_devices()

    while True:
        poll_all_devices(devices)
        time.sleep(60)  # Poll every 60 seconds (or integrate with scheduler)
