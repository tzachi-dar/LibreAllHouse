import socket
import concurrent.futures
import errno
from datetime import datetime


def check_ip(ip, port):
    """
    Checks a single IP. 
    Reachable if: Connection successful OR Connection Refused.
    Unreachable if: Timeout or No Route to Host.
    """
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(20.0)
            result_code = s.connect_ex((ip, port))
            
            # 0 = Success
            # ECONNREFUSED = Target is up, but port is closed
            # WSAECONNREFUSED = Windows version of Connection Refused
            if result_code == 0 or result_code == errno.ECONNREFUSED or result_code == 10061:
                return "*"
            else:
                return "-"
    except Exception:
        return "-"

def main():
    # Configuration
    #               router          rpi4-salon    zero-new        zero-kitchecn-new    zero-snir-new   rpi-libre-sim  rpi3-mirpeset    tzachi-glinux2
    target_ips = ["192.168.4.1", "192.168.4.5", "192.168.4.10",     "192.168.4.12",   "192.168.4.117", "192.168.4.6", "192.168.4.107"] #, "192.168.4.157"]
    target_port = 50007

    # Use multithreading to run all checks at once
    with concurrent.futures.ThreadPoolExecutor() as executor:
        results = list(executor.map(lambda ip: check_ip(ip, target_port), target_ips))

    # Formatting Output
    print("                        ","  ".join(target_ips))
    
    status_line = []
    count = 0
    for i, ip in enumerate(target_ips):
        padding = " " * (len(ip) // 2)
        status_line.append(f"{padding}{results[i]}{padding}")
        if results[i] == "*":
            count += 1
    if count == len(target_ips):
        header = "###"
    else:
        header = "##"
    print(header, datetime.now().strftime("%d-%m-%Y - %H:%M:%S"), " ".join(status_line))

if __name__ == "__main__":
    main()
