#!/usr/bin/env python3
#   cloudflare-ddns.py
#   Summary: Access your home network remotely via a custom domain name without a static IP!
#   Description: Access your home network remotely via a custom domain
#                Access your home network remotely via a custom domain
#                A small, 🕵️ privacy centric, and ⚡
#                lightning fast multi-architecture Docker image for self hosting projects.

__version__ = "1.0.2"

import json
import os
import signal
import sys
import threading
import time
import requests

CONFIG_PATH = os.environ.get('CONFIG_PATH', os.getcwd())


class GracefulExit:
    def __init__(self):
        self.kill_now = threading.Event()
        signal.signal(signal.SIGINT, self.exit_gracefully)
        signal.signal(signal.SIGTERM, self.exit_gracefully)

    def exit_gracefully(self, signum, frame):
        print("🛑 Stopping main thread...")
        self.kill_now.set()


def deleteEntries(type):
    # Helper function for deleting A or AAAA records
    # in the case of no IPv4 or IPv6 connection, yet
    # existing A or AAAA records are found.
    for option in config["cloudflare"]:
        answer = cf_api(
            "zones/" + option['zone_id'] +
            "/dns_records?per_page=100&type=" + type,
            "GET", option)
        if answer is None or answer["result"] is None:
            time.sleep(5)
            return
        for record in answer["result"]:
            identifier = str(record["id"])
            cf_api(
                "zones/" + option['zone_id'] + "/dns_records/" + identifier,
                "DELETE", option)
            print("🗑️ Deleted stale record " + identifier)


def getIPsFromCN():
    a = None
    aaaa = None
    global ipv4_enabled
    global ipv6_enabled
    global purgeUnknownRecords
    if ipv4_enabled:
        try:
            json = requests.get(
                "https://4.ipw.cn/api/ip/myip?json").json()
            a = json["IP"]
        except Exception:
            global shown_ipv4_warning
            if not shown_ipv4_warning:
                shown_ipv4_warning = True
                print("🧩 IPv4 not detected via ip.cn, trying ipplus360")
            # Try secondary IP check
            try:
                json = requests.get("https://www.ipplus360.com/getIP").json()
                a = json["data"]
            except Exception:
                global shown_ipv4_warning_secondary
                if not shown_ipv4_warning_secondary:
                    shown_ipv4_warning_secondary = True
                    print("🧩 IPv4 not detected via ipplus360. ")
                if purgeUnknownRecords:
                    deleteEntries("A")
    if ipv6_enabled:
        try:
            json = requests.get(
                "https://6.ipw.cn/api/ip/myip?json").json()
            aaaa = json["IP"]
        except Exception:
            global shown_ipv6_warning
            if not shown_ipv6_warning:
                shown_ipv6_warning = True
                print("🧩 IPv6 not detected via ipw.cn, trying myip.la")
            try:
                json = requests.get(
                    "https://v6.myip.la/json").json()
                aaaa = json["ip"]
            except Exception:
                global shown_ipv6_warning_secondary
                if not shown_ipv6_warning_secondary:
                    shown_ipv6_warning_secondary = True
                    print(
                        "🧩 IPv6 not detected via 1.0.0.1. Verify your ISP or DNS provider isn't blocking Cloudflare's IPs.")
                if purgeUnknownRecords:
                    deleteEntries("AAAA")
    ips = {}
    if (a is not None):
        ips["ipv4"] = {
            "type": "A",
            "ip": a
        }
    if (aaaa is not None):
        ips["ipv6"] = {
            "type": "AAAA",
            "ip": aaaa
        }
    return ips


def getIPs():
    ips = None
    global get_ip_from_CN
    if get_ip_from_CN:
        ips = getIPsFromCN()
        if not ips or len(ips) == 0:
            ips = getIPsFromCloudFlare()
    else:
        ips = getIPsFromCloudFlare()
    return ips

def get_host_ipv4(host):
    import socket
    try:
        info = socket.getaddrinfo(host, None, socket.AF_INET)
        ip = info[0][4][0]
        return ip
    except socket.gaierror:
        print("There was an error resolving the hostname for IPv6.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
    return None


def get_host_ipv6(host):
    import socket
    try:
        info = socket.getaddrinfo(host, None, socket.AF_INET6)
        ip = info[0][4][0]
        return ip
    except socket.gaierror:
        print("There was an error resolving the hostname for IPv6.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
    return None


def getIPsFromCloudFlare():
    a = None
    aaaa = None
    global ipv4_enabled
    global ipv6_enabled
    global purgeUnknownRecords
    if ipv4_enabled:
        try:
            a = requests.get(
                "https://1.1.1.1/cdn-cgi/trace").text.split("\n")
            a.pop()
            a = dict(s.split("=") for s in a)["ip"]
        except Exception:
            global shown_ipv4_warning
            if not shown_ipv4_warning:
                shown_ipv4_warning = True
                print("🧩 IPv4 not detected via 1.1.1.1, trying 1.0.0.1")
            # Try secondary IP check
            try:
                a = requests.get(
                    "https://1.0.0.1/cdn-cgi/trace").text.split("\n")
                a.pop()
                a = dict(s.split("=") for s in a)["ip"]
            except Exception:
                global shown_ipv4_warning_secondary
                if not shown_ipv4_warning_secondary:
                    shown_ipv4_warning_secondary = True
                    print(
                        "🧩 IPv4 not detected via 1.0.0.1. Verify your ISP or DNS provider isn't blocking Cloudflare's IPs.")
                if purgeUnknownRecords:
                    deleteEntries("A")
    if ipv6_enabled:
        try:
            aaaa = requests.get(
                "https://[2606:4700:4700::1111]/cdn-cgi/trace").text.split("\n")
            aaaa.pop()
            aaaa = dict(s.split("=") for s in aaaa)["ip"]
        except Exception:
            global shown_ipv6_warning
            if not shown_ipv6_warning:
                shown_ipv6_warning = True
                print("🧩 IPv6 not detected via 1.1.1.1, trying 1.0.0.1")
            try:
                aaaa = requests.get(
                    "https://[2606:4700:4700::1001]/cdn-cgi/trace").text.split("\n")
                aaaa.pop()
                aaaa = dict(s.split("=") for s in aaaa)["ip"]
            except Exception:
                global shown_ipv6_warning_secondary
                if not shown_ipv6_warning_secondary:
                    shown_ipv6_warning_secondary = True
                    print(
                        "🧩 IPv6 not detected via 1.0.0.1. Verify your ISP or DNS provider isn't blocking Cloudflare's IPs.")
                if purgeUnknownRecords:
                    deleteEntries("AAAA")
    ips = {}
    
    if (a is not None):
        ips["ipv4"] = {
            "type": "A",
            "ip": a
        }
    if (aaaa is not None):
        ips["ipv6"] = {
            "type": "AAAA",
            "ip": aaaa
        }
    return ips


def commitRecord(ip):
    global ttl
    global wrong_ipv4s
    global wrong_ipv6s
    if ip["type"] == 'ipv4':
        for wrong in wrong_ipv4s:
            get_ip = get_host_ipv4(wrong)
            if get_ip == ip['ip']:
                return
    if ip["type"] == 'ipv6':
        for wrong in wrong_ipv6s:
            get_ip = get_host_ipv6(wrong)
            if get_ip == ip['ip']:
                return
    for option in config["cloudflare"]:
        subdomains = option["subdomains"]
        response = cf_api("zones/" + option['zone_id'], "GET", option)
        if response is None or response["result"]["name"] is None:
            time.sleep(5)
            return
        base_domain_name = response["result"]["name"]
        for subdomain in subdomains:
            try:
                name = subdomain["name"].lower().strip()
                proxied = subdomain["proxied"]
            except:
                name = subdomain
                proxied = option["proxied"]
            fqdn = base_domain_name
            # Check if name provided is a reference to the root domain
            if name != '' and name != '@':
                fqdn = name + "." + base_domain_name
            record = {
                "type": ip["type"],
                "name": fqdn,
                "content": ip["ip"],
                "proxied": proxied,
                "ttl": ttl
            }
            dns_records = cf_api(
                "zones/" + option['zone_id'] +
                "/dns_records?per_page=100&type=" + ip["type"],
                "GET", option)
            identifier = None
            modified = False
            duplicate_ids = []
            if dns_records is not None:
                for r in dns_records["result"]:
                    if (r["name"] == fqdn):
                        if identifier:
                            if r["content"] == ip["ip"]:
                                duplicate_ids.append(identifier)
                                identifier = r["id"]
                            else:
                                duplicate_ids.append(r["id"])
                        else:
                            identifier = r["id"]
                            if r['content'] != record['content'] or r['proxied'] != record[
                                'proxied']:
                                modified = True
            if identifier:
                if modified:
                    print("📡 Updating record " + str(record))
                    response = cf_api(
                        "zones/" + option['zone_id'] +
                        "/dns_records/" + identifier,
                        "PUT", option, {}, record)
            else:
                print("➕ Adding new record " + str(record))
                response = cf_api(
                    "zones/" + option['zone_id'] + "/dns_records", "POST", option, {}, record)
            if purgeUnknownRecords:
                for identifier in duplicate_ids:
                    identifier = str(identifier)
                    print("🗑️ Deleting stale record " + identifier)
                    response = cf_api(
                        "zones/" + option['zone_id'] +
                        "/dns_records/" + identifier,
                        "DELETE", option)
    return True


def updateLoadBalancer(ip):
    for option in config["load_balancer"]:
        pools = cf_api('user/load_balancers/pools', 'GET', option)

        if pools:
            idxr = dict((p['id'], i) for i, p in enumerate(pools['result']))
            idx = idxr.get(option['pool_id'])

            origins = pools['result'][idx]['origins']

            idxr = dict((o['name'], i) for i, o in enumerate(origins))
            idx = idxr.get(option['origin'])

            origins[idx]['address'] = ip['ip']
            data = {'origins': origins}

            response = cf_api(f'user/load_balancers/pools/{option["pool_id"]}', 'PATCH', option, {},
                              data)


def cf_api(endpoint, method, config, headers={}, data=False):
    api_token = config['authentication']['api_token']
    if api_token != '' and api_token != 'api_token_here':
        headers = {
            "Authorization": "Bearer " + api_token, **headers
        }
    else:
        headers = {
            "X-Auth-Email": config['authentication']['api_key']['account_email'],
            "X-Auth-Key": config['authentication']['api_key']['api_key'],
        }
    try:
        if (data == False):
            response = requests.request(
                method, "https://api.cloudflare.com/client/v4/" + endpoint, headers=headers)
        else:
            response = requests.request(
                method, "https://api.cloudflare.com/client/v4/" + endpoint,
                headers=headers, json=data)

        if response.ok:
            return response.json()
        else:
            print("😡 Error sending '" + method +
                  "' request to '" + response.url + "':")
            print(response.text)
            return None
    except Exception as e:
        print("😡 An exception occurred while sending '" +
              method + "' request to '" + endpoint + "': " + str(e))
        return None


def updateIPs(ips):
    for ip in ips.values():
        commitRecord(ip)
        # updateLoadBalancer(ip)


if __name__ == '__main__':
    shown_ipv4_warning = False
    shown_ipv4_warning_secondary = False
    shown_ipv6_warning = False
    shown_ipv6_warning_secondary = False
    ipv4_enabled = True
    ipv6_enabled = True
    purgeUnknownRecords = False
    get_ip_from_CN = True  # 优先从国内获取ip，防止1.1.1.1无法访问，或者他加了代理，获取到的是代理的ip
    wrong_ipv4s = None  # 错误的ip，如果获取到这个ip，则不进去上报，这个上报会有问题
    wrong_ipv6s = None  # 错误的ip，如果获取到这个ip，则不进去上报，这个上报会有问题

    if sys.version_info < (3, 5):
        raise Exception("🐍 This script requires Python 3.5+")

    config = None
    try:
        with open(os.path.join(CONFIG_PATH, "config.json")) as config_file:
            config = json.loads(config_file.read())
    except:
        print("😡 Error reading config.json")
        # wait 10 seconds to prevent excessive logging on docker auto restart
        time.sleep(10)

    if config is not None:
        get_ip_from_CN = config.get('get_ip_from_CN')
        wrong_ipv4s = config.get('wrong_ipv4s')
        wrong_ipv6s = config.get('wrong_ipv6s')
        try:
            ipv4_enabled = config["a"]
            ipv6_enabled = config["aaaa"]
        except:
            ipv4_enabled = True
            ipv6_enabled = True
            print(
                "⚙️ Individually disable IPv4 or IPv6 with new config.json options. Read more about it here: https://github.com/timothymiller/cloudflare-ddns/blob/master/README.md")
        try:
            purgeUnknownRecords = config["purgeUnknownRecords"]
        except:
            purgeUnknownRecords = False
            print("⚙️ No config detected for 'purgeUnknownRecords' - defaulting to False")
        try:
            ttl = int(config["ttl"])
        except:
            ttl = 300  # default Cloudflare TTL
            print(
                "⚙️ No config detected for 'ttl' - defaulting to 300 seconds (5 minutes)")
        if ttl < 30:
            ttl = 1  #
            print("⚙️ TTL is too low - defaulting to 1 (auto)")
        if (len(sys.argv) > 1):
            if (sys.argv[1] == "--repeat"):
                if ipv4_enabled and ipv6_enabled:
                    print(
                        "🕰️ Updating IPv4 (A) & IPv6 (AAAA) records every " + str(ttl) + " seconds")
                elif ipv4_enabled and not ipv6_enabled:
                    print("🕰️ Updating IPv4 (A) records every " +
                          str(ttl) + " seconds")
                elif ipv6_enabled and not ipv4_enabled:
                    print("🕰️ Updating IPv6 (AAAA) records every " +
                          str(ttl) + " seconds")
                next_time = time.time()
                killer = GracefulExit()
                prev_ips = None
                while True:
                    updateIPs(getIPs())
                    if killer.kill_now.wait(ttl):
                        break
            else:
                print("❓ Unrecognized parameter '" +
                      sys.argv[1] + "'. Stopping now.")
        else:
            updateIPs(getIPs())
