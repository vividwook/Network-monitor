import logging
from ping3 import ping
from pysnmp.hlapi import (
    getCmd,
    nextCmd,
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
from dotenv import load_dotenv
from time import time as now

load_dotenv()



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
        CommunityData(community, mpModel=0),
        UdpTransportTarget((ip, 161), timeout=2, retries=1),
        ContextData(),
        ObjectType(ObjectIdentity('1.3.6.1.2.1.1.3.0'))  # sysUpTime
    )
    errI, errS, errX, vbs = next(iterator)
    if errI or errS:
        logging.warning(f"SNMP issue on {ip}: {errI or errS.prettyPrint()}")
        return None
    for _, val in vbs:
        try: return int(str(val))  # Timeticks → centiseconds (int)
        except: return None

def get_up_interfaces(ip, community):
    engine = SnmpEngine()
    target = UdpTransportTarget((ip, 161), timeout=2, retries=1)
    auth   = CommunityData(community, mpModel=0)
    ctx    = ContextData()

    IF_NAME     = '1.3.6.1.2.1.31.1.1.1.1'  # ifName
    IF_DESCR    = '1.3.6.1.2.1.2.2.1.2'     # ifDescr (fallback)
    IF_OPERSTAT = '1.3.6.1.2.1.2.2.1.8'     # ifOperStatus (1 up)

    names, oper = {}, {}

    for (eI, eS, eX, vbs) in nextCmd(engine, auth, target, ctx, ObjectType(ObjectIdentity(IF_NAME)), lexicographicMode=False):
        if eI or eS: break
        for oid, val in vbs:
            try: names[int(oid.prettyPrint().split('.')[-1])] = str(val)
            except: pass

    if not names:
        for (eI, eS, eX, vbs) in nextCmd(engine, auth, target, ctx, ObjectType(ObjectIdentity(IF_DESCR)), lexicographicMode=False):
            if eI or eS: break
            for oid, val in vbs:
                try: names[int(oid.prettyPrint().split('.')[-1])] = str(val)
                except: pass

    for (eI, eS, eX, vbs) in nextCmd(engine, auth, target, ctx, ObjectType(ObjectIdentity(IF_OPERSTAT)), lexicographicMode=False):
        if eI or eS: break
        for oid, val in vbs:
            try: oper[int(oid.prettyPrint().split('.')[-1])] = int(val)
            except: pass

    up = [n for idx, n in names.items() if oper.get(idx) == 1]
    up.sort()
    return up

def format_uptime(centisecs):
    try:
        total = int(str(centisecs)) / 100
        h = int(total // 3600)
        m = int((total % 3600) // 60)
        s = total % 60
        return f"{h}h {m}m {s:.2f}s"
    except Exception:
        return None

def format_bytes(n: int) -> str:
    try:
        n = int(n)
    except Exception:
        return str(n)
    for unit in ['B','KB','MB','GB','TB']:
        if n < 1024:
            return f"{n:.1f}{unit}"
        n /= 1024
    return f"{n:.1f}PB"


def get_cpu_usage_percent(ip, community):
    """
    Average of HOST-RESOURCES-MIB::hrProcessorLoad (percent).
    OID: 1.3.6.1.2.1.25.3.3.1.2
    """
    engine = SnmpEngine()
    target = UdpTransportTarget((ip, 161), timeout=2, retries=1)
    auth   = CommunityData(community, mpModel=0)
    ctx    = ContextData()
    HR_CPU = '1.3.6.1.2.1.25.3.3.1.2'

    values = []
    for (eI, eS, eX, vbs) in nextCmd(
        engine, auth, target, ctx,
        ObjectType(ObjectIdentity(HR_CPU)),
        lexicographicMode=False
    ):
        if eI or eS:
            return None
        for _, val in vbs:
            try:
                values.append(int(val))
            except Exception:
                pass

    if not values:
        return None
    return int(sum(values) / len(values))


def get_storage_usage(ip, community):
    """
    Returns list of dicts:
    [{name, total_bytes, used_bytes, used_pct}], filtered to useful entries.
    Uses HOST-RESOURCES-MIB hrStorage* columns.
    """
    engine = SnmpEngine()
    target = UdpTransportTarget((ip, 161), timeout=2, retries=1)
    auth   = CommunityData(community, mpModel=0)
    ctx    = ContextData()

    HR_NAME  = '1.3.6.1.2.1.25.2.3.1.3'  # hrStorageDescr
    HR_ALLOC = '1.3.6.1.2.1.25.2.3.1.4'  # hrStorageAllocationUnits
    HR_SIZE  = '1.3.6.1.2.1.25.2.3.1.5'  # hrStorageSize
    HR_USED  = '1.3.6.1.2.1.25.2.3.1.6'  # hrStorageUsed

    names, alloc, size, used = {}, {}, {}, {}

    # Walk each column
    for oid_base, bucket in [(HR_NAME, names), (HR_ALLOC, alloc), (HR_SIZE, size), (HR_USED, used)]:
        for (eI, eS, eX, vbs) in nextCmd(
            engine, auth, target, ctx,
            ObjectType(ObjectIdentity(oid_base)),
            lexicographicMode=False
        ):
            if eI or eS:
                break
            for oid, val in vbs:
                try:
                    idx = int(oid.prettyPrint().split('.')[-1])
                    bucket[idx] = val
                except Exception:
                    pass

    rows = []
    for idx, nm in names.items():
        try:
            au   = int(alloc.get(idx, 1))  # bytes per block
            totb = int(size.get(idx, 0)) * au
            usedb= int(used.get(idx, 0)) * au
            pct  = int((usedb / totb) * 100) if totb > 0 else 0
            name = str(nm)
            rows.append({
                "name": name,
                "total_bytes": totb,
                "used_bytes": usedb,
                "used_pct": pct
            })
        except Exception:
            continue

    # Optional: filter to likely disks/flash; Arista often labels as 'flash', 'bootflash', '/', etc.
    interesting = []
    for r in rows:
        lname = r["name"].lower()
        if any(k in lname for k in ["flash", "bootflash", "root", "/", "filesystem"]):
            interesting.append(r)
    # If filter removed everything, fall back to top few by size
    if not interesting:
        interesting = sorted(rows, key=lambda x: x["total_bytes"], reverse=True)[:3]

    # Sort by used percent, high first
    interesting.sort(key=lambda x: x["used_pct"], reverse=True)
    return interesting


def poll_device(device):
    
    name = device['name']
    ip = device['ip']

    reachable = is_reachable(ip)

    result = {
        "name": name,
        "ip": ip,
        "reachable": bool(reachable),
        "uptime_raw": None,
        "uptime_fmt": None,
        "if_up": [],
        "if_up_count": 0,
        "cpu_pct": None,
        "disks": [],
        "checked_at": datetime.utcnow().isoformat() + "Z",
    }

    if reachable and device.get('snmp') and device.get('community'):
        # uptime
        uptime = get_snmp_uptime(ip, device['community'])
        if uptime is not None:
            result["uptime_raw"] = uptime
            result["uptime_fmt"] = format_uptime(uptime)

        # interfaces
        try:
            up_ifaces = get_up_interfaces(ip, device['community'])
            result["if_up"] = up_ifaces
            result["if_up_count"] = len(up_ifaces)
        except Exception:
            logging.exception(f"SNMP ifTable fetch failed on {ip}")

        # CPU
        try:
            cpu = get_cpu_usage_percent(ip, device['community'])
            result["cpu_pct"] = cpu
        except Exception:
            logging.exception(f"SNMP CPU fetch failed on {ip}")

        # Storage
        try:
            disks = get_storage_usage(ip, device['community'])
            result["disks"] = disks
        except Exception:
            logging.exception(f"SNMP storage fetch failed on {ip}")

    elif not reachable:
        logging.error(f"{name} ({ip}) is DOWN")

    return result



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
