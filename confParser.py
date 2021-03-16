import math
import sys
import re
import ipaddress
import sqlite3
import os
import shutil
import uuid
import datetime
import time
import paramiko
import telnetlib
import socket
import getpass
import multiprocessing
import xlsxwriter

from ciscoconfparse import CiscoConfParse

debug = True                    # Turn on to see debugging messages
debugSQL = False                # Turn on to see raw SQL request messages
DBUpdateDisable = False         # Turn on to disable writing (insert/update/delete) to DB

DBFormatVersion = 2             # Specifies current format (columns and their order) of data storing in DB and lists
                                # Changes whenever the core dictionaried below are changed do disable backward compatibility

#####################################################################################################################################################
###################################################      Core dictionaries (DO NOT CHANGE)      #####################################################
#####################################################################################################################################################

# Defining dictionaries of persistent list indexes to access required list values by names
SyntaxDict = {
    "Hist": 0,
    "IOS-XR": 0,
    "IOS": 0,
    "VRP": 0,
    "SR-OS": 0
}

i = 0
for value in SyntaxDict:
    SyntaxDict[value] = int(i)
    i = i + 1

NodesDict =  {
    "NodeID": [0, "TEXT NOT NULL,"],
    "Hostname": [0, "TEXT NOT NULL,"],
    "CLISyntax": [0, "TEXT NOT NULL,"],
    "SysAddr": [0, "TEXT,"],
    "SWDescr": [0, "TEXT,"],
    "SourceFile": [0, "TEXT,"],
    "Comments": [0, "TEXT,"],
    "LastUpdatedTime": [0, "TEXT,"],
    "LastUpdatedBy": [0, "TEXT"]
}

i = 0
for value in NodesDict:
    NodesDict[value][0] = int(i)
    i = i + 1

InterfacesDict =  {
    "IfID": [0, "TEXT NOT NULL,"],
    "NodeID": [0, "TEXT NOT NULL,"],
    "Hostname": [0, "TEXT NOT NULL,"],
    "CLISyntax": [0, "TEXT NOT NULL,"],
    "IfNumber": [0, "TEXT,"],
    "ParentIfName": [0, "TEXT,"],
    "IfName": [0, "TEXT,"],
    "IfDescr": [0, "TEXT,"],
    "IfType": [0, "TEXT,"],
    "IfMode": [0, "TEXT,"],
    "PortName": [0, "TEXT,"],
    "PortType": [0, "TEXT,"],
    "PortBinding": [0, "TEXT,"],
    "SFPType": [0, "TEXT,"],
    "SFPSN": [0, "TEXT,"],
    "TxLevel": [0, "TEXT,"],
    "RxLevel": [0, "TEXT,"],
    "Encap": [0, "TEXT,"],
    "VLAN": [0, "TEXT,"],
    "LAGID": [0, "TEXT,"],
    "LAGMode": [0, "TEXT,"],
    "BridgeID": [0, "TEXT,"],
    "StateAdm": [0, "TEXT,"],
    "StateLink": [0, "TEXT,"],
    "ServiceID": [0, "TEXT,"],
    "ServiceName": [0, "TEXT,"],
    "ServiceDescr": [0, "TEXT,"],
    "ServiceType": [0, "TEXT,"],
    "ServiceSDP": [0, "TEXT,"],
    "StateIPv4": [0, "TEXT,"],
    "StateIPv6": [0, "TEXT,"],
    "L2MTU": [0, "TEXT,"],
    "L3MTU": [0, "TEXT,"],
    "IPV4Addr": [0, "TEXT,"],
    "IPV4Subnet": [0, "TEXT,"],
    "IPV6Addr": [0, "TEXT,"],
    "IPV6Subnet": [0, "TEXT,"],
    "BFD": [0, "TEXT,"],
    "OSPFv2": [0, "TEXT,"],
    "OSPFv3": [0, "TEXT,"],
    "ISIS": [0, "TEXT,"],
    "BGP": [0, "TEXT,"],
    "LDP": [0, "TEXT,"],
    "RSVP": [0, "TEXT,"],
    "QoSIn": [0, "TEXT,"],
    "QoSOut": [0, "TEXT,"],
    "SyncE": [0, "TEXT,"],
    "CDP": [0, "TEXT,"],
    "LLDP": [0, "TEXT,"],
    "Comments": [0, "TEXT,"],
    "LastUpdatedTime": [0, "TEXT,"],
    "LastUpdatedBy": [0, "TEXT"]
}

i = 0
for value in InterfacesDict:
    InterfacesDict[value][0] = int(i)
    i = i + 1

PeeringDict =  {
    "PeeringID": [0, "TEXT NOT NULL,"],
    "PeeringType": [0, "TEXT NOT NULL,"],
    "PeeringAdmState": [0, "TEXT,"],
    "PeeringState": [0, "TEXT,"],
    "NodeID": [0, "TEXT NOT NULL,"],
    "Hostname": [0, "TEXT NOT NULL,"],
    "SysAddr": [0, "TEXT,"],
    "CLISyntax": [0, "TEXT NOT NULL,"],
    "LocalAS": [0, "TEXT,"],
    "PeerDescr": [0, "TEXT,"],
    "IfID": [0, "TEXT,"],
    "IfName": [0, "TEXT,"],
    "IfDescr": [0, "TEXT,"],
    "PortBinding": [0, "TEXT,"],
    "PortName": [0, "TEXT,"],
    "PortDescr": [0, "TEXT,"],
    "IPV4Addr": [0, "TEXT,"],
    "IPV4Subnet": [0, "TEXT,"],
    "IPV6Addr": [0, "TEXT,"],
    "IPV6Subnet": [0, "TEXT,"],
    "NodeIDRemote": [0, "TEXT,"],
    "HostnameRemote": [0, "TEXT,"],
    "SysAddrRemote": [0, "TEXT,"],
    "CLISyntaxRemote": [0, "TEXT,"],
    "ASRemote": [0, "TEXT,"],
    "PeerDescrRemote": [0, "TEXT,"],
    "IfIDRemote": [0, "TEXT,"],
    "IfNameRemote": [0, "TEXT,"],
    "IfDescrRemote": [0, "TEXT,"],
    "PortBindingRemote": [0, "TEXT,"],
    "PortNameRemote": [0, "TEXT,"],
    "PortDescrRemote": [0, "TEXT,"],
    "IPV4AddrRemote": [0, "TEXT,"],
    "IPV4SubnetRemote": [0, "TEXT,"],
    "IPV6AddrRemote": [0, "TEXT,"],
    "IPV6SubnetRemote": [0, "TEXT,"],
    "Comments": [0, "TEXT,"],
    "LastUpdatedTime": [0, "TEXT,"],
    "LastUpdatedBy": [0, "TEXT"]
}

i = 0
for value in PeeringDict:
    PeeringDict[value][0] = int(i)
    i = i + 1

CommandsDict =  {
    "IOS": [
        [ "show version", 30 ],
        # [ "terminal length 0", 30 ],
        [ "", 30 ],
        [ "show running-config", 300 ],
        [ "show bootvar", 30 ],
        [ "show interfaces", 60 ],
        [ "show inventory", 60 ],
        [ "show ip interface", 60 ],
        [ "show ipv6 interface", 60 ],
        [ "show mac address-table detail", 60 ],
        [ "show mpls interfaces detail", 60 ],
        [ "show cdp neighbors detail", 60 ],
        [ "show lldp neighbors detail", 60 ],
        [ "show bfd neighbors details", 60 ],
        [ "show ip ospf", 60 ],
        [ "show ip ospf neighbor detail", 60 ],
        [ "show ip ospf interface", 60 ],
        [ "show ip ospf database router", 300 ],
        [ "show ip ospf database network", 300 ],
        [ "show ip ospf database summary", 300 ],
        [ "show ip ospf database asbr-summary", 300 ],
        [ "show ip ospf database external", 300 ],
        [ "show ip ospf database nssa-external", 300 ],
        [ "show ipv6 ospf", 60 ],
        [ "show ipv6 ospf neighbor detail", 60 ],
        [ "show ipv6 ospf interface", 60 ],
        [ "show ospfv3 database router", 300 ],
        [ "show ospfv3 database network", 300 ],
        [ "show ospfv3 database prefix", 300 ],
        [ "show ospfv3 database inter-area", 300 ],
        [ "show ospfv3 database external", 300 ],
        [ "show ospfv3 database nssa-external", 300 ],
        [ "show isis", 60 ],
        [ "show isis neighbors detail", 60 ],
        [ "show isis database detail", 300 ],
        [ "show mpls ldp neighbor detail", 60 ],
        [ "show ip bgp neighbors", 60 ],
        [ "show ip route", 300 ],
        [ "show ip route summary", 60 ],
        [ "show ip cef", 300 ],
        [ "show ip cef summary", 60 ],
        [ "show ipv6 route", 300 ],
        [ "show ipv6 route summary", 60 ],
        [ "show ipv6 cef", 300 ],
        [ "show ipv6 cef summary", 60 ],
        [ "show mpls ip binding", 300 ],
        [ "show mpls forwarding-table", 300 ],
        [ "show ip arp", 60 ],
        [ "show ipv6 neighbors", 60 ],
        [ "show vrf", 60 ],
        [ "show ip route vrf {vrf-name}", 300 ],
        [ "show ip route vrf {vrf-name} summary", 60 ],
        [ "show ip cef vrf {vrf-name}", 300 ],
        [ "show ip cef vrf {vrf-name} summary", 60 ],
        [ "show ipv6 route vrf {vrf-name}", 300 ],
        [ "show ipv6 route vrf {vrf-name} summary", 60 ],
        [ "show ipv6 cef vrf {vrf-name}", 300 ],
        [ "show ip cef vrf {vrf-name} summary", 60 ],
        [ "show ip arp vrf {vrf-name}", 60 ],
        [ "show ipv6 neighbors vrf {vrf-name}", 60 ],
        [ "show l2vpn service all", 60 ],
        [ "show xconnect all detail", 60 ],
        [ "show bgp vrf {vrf-name} summary", 60 ]
    ],
    "IOS-XR": [
        [ "show version", 30 ],
        # [ "terminal length 0", 30 ],
        [ "", 30 ],
        [ "show running-config", 300 ],
        [ "show variables boot", 30 ],
        [ "show interfaces", 60 ],
        [ "show inventory", 60 ],
        [ "show ipv4 interface", 60 ],
        [ "show ipv6 interface", 60 ],
        [ "show mpls interfaces detail", 60 ],
        [ "show rsvp interface detail", 60 ],
        [ "show rsvp session detail", 300 ],
        [ "show cdp neighbors detail", 60 ],
        [ "show lldp neighbors detail", 60 ],
        [ "show bfd session detail", 60 ],
        [ "show ospf", 60 ],
        [ "show ospf neighbor detail", 60 ],
        [ "show ospf interface", 60 ],
        [ "show ospf database router", 300 ],
        [ "show ospf database network", 300 ],
        [ "show ospf database summary", 300 ],
        [ "show ospf database asbr-summary", 300 ],
        [ "show ospf database external", 300 ],
        [ "show ospf database nssa-external", 300 ],
        [ "show ospfv3", 60 ],
        [ "show ospfv3 neighbor detail", 60 ],
        [ "show ospfv3 interface", 60 ],
        [ "show ospfv3 database router", 300 ],
        [ "show ospfv3 database network", 300 ],
        [ "show ospfv3 database prefix", 300 ],
        [ "show ospfv3 database inter-area", 300 ],
        [ "show ospfv3 database external", 300 ],
        [ "show ospfv3 database nssa-external", 300 ],
        [ "show isis", 60 ],
        [ "show isis adjacency detail", 60 ],
        [ "show isis interface", 60 ],
        [ "show isis database detail", 300 ],
        [ "show mpls ldp neighbor detail", 60 ],
        [ "show rsvp neighbors detail", 60 ],
        [ "show bgp neighbors", 60 ],
        [ "show route ipv4", 300 ],
        [ "show route ipv4 summary detail", 60 ],
        [ "show cef ipv4", 300 ],
        [ "show cef ipv4 summary", 60 ],
        [ "show route ipv6", 300 ],
        [ "show route ipv6 summary detail", 60 ],
        [ "show cef ipv6", 300 ],
        [ "show cef ipv6 summary", 60 ],
        [ "show mpls ldp bindings", 300 ],
        [ "show mpls ldp bindings summary", 60 ],
        [ "show mpls forwarding", 300 ],
        [ "show mpls forwarding summary", 60 ],
        [ "show arp", 60 ],
        [ "show ipv6 neighbors", 60 ],
        [ "show vrf all", 60 ],
        [ "show route vrf {vrf-name} ipv4", 300 ],
        [ "show route vrf {vrf-name} ipv4 summary detail", 60 ],
        [ "show cef vrf {vrf-name} ipv4", 300 ],
        [ "show cef vrf {vrf-name} ipv4 summary", 60 ],
        [ "show route vrf {vrf-name} ipv6", 300 ],
        [ "show route vrf {vrf-name} ipv6 summary detail", 60 ],
        [ "show cef vrf {vrf-name} ipv6", 300 ],
        [ "show cef vrf {vrf-name} ipv6 summary", 60 ],
        [ "show arp vrf {vrf-name}", 60 ],
        [ "show l2vpn xconnect detail", 60 ],
        [ "show ospf vrf all neighbor detail", 60 ],
        [ "show ospfv3 vrf all neighbor detail", 60 ],
        [ "show bgp vrf all neighbors", 60 ]
    ],
    "VRP": [
        [ "display version", 30 ],
        # [ "screen-length 0 temporary", 30],
        [ "", 30 ],
        [ "display current-configuration", 300 ],
        [ "display interface", 60 ],
        [ "display interface phy-option", 60 ],
        [ "display inventory board", 60 ],
        [ "display ip interface", 60 ],
        [ "display ipv6 interface", 60 ],
        [ "display mpls interface verbose", 60 ],
        [ "display mpls rsvp interface", 60 ],
        [ "display lldp neighbor", 60 ],
        [ "display bfd session all verbose", 60 ],
        [ "display mpls rsvp-te bfd session all", 60 ],
        [ "display ospf brief", 60 ],
        [ "display ospf peer", 60 ],
        [ "display ospf lsdb router", 300 ],
        [ "display ospf lsdb network", 300 ],
        [ "display ospf lsdb summary", 300 ],
        [ "display ospf lsdb asbr", 300 ],
        [ "display ospf lsdb nssa", 300 ],
        [ "display ospf lsdb ase", 300 ],
        [ "display ospfv3 peer", 60 ],
        [ "display ospfv3 lsdb router", 300 ],
        [ "display ospfv3 lsdb inter-prefix", 300 ],
        [ "display ospfv3 lsdb network", 300 ],
        [ "display ospfv3 lsdb intra-prefix", 300 ],
        [ "display ospfv3 lsdb inter-router", 300 ],
        [ "display ospfv3 lsdb nssa", 300 ],
        [ "display ospfv3 lsdb external", 300 ],
        [ "display isis peer verbose", 60 ],
        [ "display isis interface", 60 ],
        [ "display isis interface verbose", 60 ],
        [ "display isis lsdb verbose", 300 ],
        [ "display mpls ldp peer verbose", 60 ],
        [ "display mpls rsvp-te peer", 60 ],
        [ "display bgp peer verbose", 60 ],
        [ "display ip routing-table", 300 ],
        [ "display ip routing-table statistics", 60 ],
        [ "display ip vpn-instance", 60 ],
        [ "display ip routing-table vpn-instance {vpn-name}", 300 ],
        [ "display ip routing-table vpn-instance {vpn-name} statistics", 60 ]
    ],
    "SR-OS": [
        [ "show version", 30 ],
        # [ "environment no more", 30 ],
        [ "", 30 ],
        [ "admin display-config", 300 ],
        [ "show bof", 30 ],
        [ "show system information", 30 ],
        [ "show port", 60 ],
        [ "show port {port-id} optical detail", 60 ],
        [ "show card detail", 60 ],
        [ "show router \"{router-name}\" interface detail", 60 ],
        [ "show router {service-id} interface detail", 60 ],
        [ "show router mpls interface detail", 60 ],
        [ "show router rsvp interface detail", 60 ],
        [ "show router ldp interface detail", 60 ],
        [ "show router mpls lsp detail", 300 ],
        [ "show system lldp neighbor", 60 ],
        [ "show port {port-id} ethernet lldp remote-info detail", 60 ],
        [ "show router bfd session", 60 ],
        [ "show router ospf all status", 60 ],
        [ "show router ospf all neighbor detail", 60 ],
        [ "show router ospf interface detail", 60 ],
        [ "show router ospf all database type router detail", 300 ],
        [ "show router ospf all database type network detail", 300 ],
        [ "show router ospf all database type summary detail", 300 ],
        [ "show router ospf all database type asbr-summary detail", 300 ],
        [ "show router ospf all database type nssa detail", 300 ],
        [ "show router ospf all database type external detail", 300 ],
        [ "show router ospf3 all status", 60 ],
        [ "show router ospf3 all neighbor detail", 60 ],
        [ "show router ospf3 interface detail", 60 ],
        [ "show router ospf3 all database type router detail", 300 ],
        [ "show router ospf3 all database type inter-area-pfx detail", 300 ],
        [ "show router ospf3 all database type network detail", 300 ],
        [ "show router ospf3 all database type intra-area-pfx detail", 300 ],
        [ "show router ospf3 all database type inter-area-rtr detail", 300 ],
        [ "show router ospf3 all database type nssa detail", 300 ],
        [ "show router ospf3 all database type external detail", 300 ],
        [ "show router isis all status", 60 ],
        [ "show router isis all adjacency detail", 60 ],
        [ "show router isis interface detail", 60 ],
        [ "show router isis all database detail", 300 ],
        [ "show router ldp session detail", 60 ],
        [ "show router rsvp neighbor detail", 60 ],
        [ "show router bgp neighbor", 60 ],
        [ "show router \"{router-name}\" route-table ipv4", 300 ],
        [ "show router \"{router-name}\" route-table ipv4 summary", 60 ],
        [ "show router \"{router-name}\" fib {card-id} ipv4", 300 ],
        [ "show router \"Base\" fib {card-id} summary ipv4", 60 ],
        [ "show router \"{router-name}\" route-table ipv6", 300 ],
        [ "show router \"{router-name}\" route-table ipv6 summary", 60 ],
        [ "show router \"{router-name}\" fib {card-id} ipv6", 300 ],
        [ "show router \"Base\" fib {card-id} summary ipv6", 60 ],
        [ "show router \"{router-name}\" ldp bindings detail", 300 ],
        [ "show router \"{router-name}\" ldp bindings summary", 60 ],
        [ "show router \"{router-name}\" arp", 60 ],
        [ "show router \"{router-name}\" neighbor", 60 ],
        [ "show service service-using", 60 ],
        [ "show service id {vprn-id} all", 60 ],
        [ "show service id {ies-id} all", 60 ],
        [ "show router {vprn-id} route-table ipv4", 300 ],
        [ "show router {vprn-id} route-table ipv4 summary", 60 ],
        [ "show router {vprn-id} fib {card-id} ipv4", 300 ],
        [ "show router {vprn-id} route-table ipv6", 300 ],
        [ "show router {vprn-id} route-table ipv6 summary", 60 ],
        [ "show router {vprn-id} fib {card-id} ipv6", 300 ],
        [ "show router {vprn-id} arp", 60 ],
        [ "show router {vprn-id} arp summary", 60 ],
        [ "show router {vprn-id} neighbor", 60 ],
        [ "show router {vprn-id} neighbor summary", 60 ],
        [ "show service id {vpls-id} all", 60 ],
        [ "show service id {xpipe-id} all", 60 ],
        [ "show service sdp detail", 60 ],
        [ "show router {vprn-id} ospf all neighbor detail", 60 ],
        [ "show router {vprn-id} ospf3 all neighbor detail", 60 ],
        [ "show router {vprn-id} bgp neighbor", 60 ]
    ]

}

PortsDict =  {
    "SSH": [ 22 ],
    "Telnet": [ 23 ]
}

shellPromptRegex = r"(\r*\n|^)[a-zA-Z0-9\-\._:@\{\}~\/\\ \t\*<\[]*[a-zA-Z0-9\-\._:@\{\}~\/\\\t\*](>|#|\$|\%|\])[a-zA-Z0-9\-\._:@\{\}~\/\\ \t]*(\r*\n|$)"
shellPromptRegexEmptyLine = r"(\r*\n|^)[a-zA-Z0-9\-\._:@\{\}~\/\\ \t\*<\[]*[a-zA-Z0-9\-\._:@\{\}~\/\\\t\*](>|#|\$|\%|\]) *(\r*\n|$)"

#####################################################################################################################################################
###########################################################      Execute CLI command      ###########################################################
#####################################################################################################################################################
def execCLICommand(connectionCursor, protocol, command, execTimeout):
    startTime = time.time()
    if execTimeout is None: execTimeout = 30
    pagingTimeout = 20
    readTimeout = 0.1
    waitTimeout = 20

    outputText = []

    escapes = ''.join([chr(char) for char in range(1, 32)])
    translator = str.maketrans('', '', escapes)
    outputStream = ""
    outputStream1 = ""
    # Sending Ctrl+C + Ctrl+Z to abort any commands in progress and exit to top level
    if protocol == "ssh":
        connectionCursor.send("\x03\x26\n")
    if protocol == "telnet":
        connectionCursor.write(b"\x03\x26\n")
    time.sleep(0.1)
    # print("1")
    # Cleaning terminal contents before execution
    if protocol == "ssh":
        while connectionCursor.recv_ready():
            try:
                execTime = time.time() - startTime
                if ( execTime > execTimeout ):
                    print("Error: command \"" + command + "\" execution has timed out")
                    connectionCursor.send("\x03\n")
                    return [ 1, outputText, execTime]
                connectionCursor.settimeout(readTimeout)
                outputChunk = connectionCursor.recv(1000).decode("utf-8")
                # print(outputChunk)
                outputStream1 = outputStream1 + outputChunk
            except:
                print("   Connection error: ", sys.exc_info()[0])
    if protocol == "telnet":
        terminalRead = 0
        outputChunk = ""
        while terminalRead == 0:
            try:
                execTime = time.time() - startTime
                if ( execTime > execTimeout ):
                    print("Error: command \"" + command + "\" execution has timed out")
                    connectionCursor.write(b"\x03\n")
                    return [ 1, outputText, execTime]
                terminalLine = ""
                terminalLine = connectionCursor.read_until(b"\n",readTimeout).decode('utf-8')
                if (terminalLine == ""):
                    terminalRead = 1
                outputStream1 = outputStream1 + terminalLine
            except:
                print("   Connection error: ", sys.exc_info()[0])

    # Checking if terminal is alive
    # print("2")
    outputStream2 = ""
    terminalActive = False
    for attempt in range(0,20):
        # Sending empty line to see response
        if protocol == "ssh":
            connectionCursor.send("\n")
        if protocol == "telnet":
            connectionCursor.write(b"\n")
        time.sleep(0.1)

        # Reading terminal to get CLI prefix
        if protocol == "ssh":
            waitTime = 0
            while not connectionCursor.recv_ready():
                execTime = time.time() - startTime
                if ( execTime > execTimeout ):
                    print("Error: command \"" + command + "\" execution has timed out")
                    connectionCursor.send("\x03\n")
                    return [ 2, outputText, execTime]
                time.sleep(0.1)
                waitTime = waitTime + 0.1
                if waitTime >= waitTimeout:
                    print("Error: command \"" + command + "\" execution procedure has timed out while attempting to get CLI prefix")
                    break
        if protocol == "ssh":
            while connectionCursor.recv_ready():
                try:
                    execTime = time.time() - startTime
                    if ( execTime > execTimeout ):
                        print("Error: command \"" + command + "\" execution has timed out")
                        connectionCursor.send("\x03\n")
                        return [ 3, outputText, execTime]
                    connectionCursor.settimeout(readTimeout)
                    outputChunk = connectionCursor.recv(1000).decode("utf-8")
                    outputStream2 = outputStream2 + outputChunk
                    if not connectionCursor.recv_ready():
                        time.sleep(0.1)
                except:
                    print("   Connection error: ", sys.exc_info()[0])
        if protocol == "telnet":
            terminalRead = 0
            outputChunk = ""
            while terminalRead == 0:
                try:
                    execTime = time.time() - startTime
                    if ( execTime > execTimeout ):
                        print("Error: command \"" + command + "\" execution has timed out")
                        connectionCursor.write(b"\x03\n")
                        return [ 3, outputText, execTime]
                    terminalLine = ""
                    terminalLine = connectionCursor.read_until(b"\n",readTimeout).decode('utf-8')
                    if (terminalLine == ""):
                        terminalRead = 1
                    else:
                        outputStream2 = outputStream2 + terminalLine
                except:
                    print("   Connection error: ", sys.exc_info()[0])

        for line in re.split(r"\r*\n",outputStream2)[-1:]:
            line = re.sub(r"\x1b\[K( |\x08)*\x1b\[K","",line)                       # Cisco IOS-XR garbage line
            line = re.sub(r"\x1b\[K","",line)                                       # Cisco IOS-XR garbage line
            line = re.sub(r"\x1b\[42D +\x1b\[42D","",line)                          # Huawei VRP garbage line
            line = re.sub(r" *\[1D","",line)                                        # Huawei VRP garbage line
            line = line.translate(translator)
            line = line.lstrip().rstrip()
        # if ( re.search(shellPromptRegexEmptyLine,outputStream2.replace("\r","")) ):
            if ( re.search(shellPromptRegexEmptyLine,line) ):
                # shellPrompt = re.search(shellPromptRegexEmptyLine,outputStream2.replace("\r","")).group().lstrip().rstrip()
                shellPrompt = re.search(shellPromptRegexEmptyLine,line).group()
                # print("shellPrompt")
                # print(shellPrompt)
                terminalActive = True
                break
        # else:
        #     time.sleep(0.5)
        if terminalActive == False:
            time.sleep(0.1)
        else:
            break

    if ( not terminalActive ):
        print("Error: terminal not responding while trying to execute command \"" + command + "\"")
        return [ 3, outputText, execTime]
    else:
        # Sending command
        if protocol == "ssh":
            # connectionCursor.send("\n" + command + "\n")
            connectionCursor.send(command + "\n")
        if protocol == "telnet":
            # connectionCursor.write(b"\n" + command.encode('ascii') + b"\n")
            connectionCursor.write(command.encode('ascii') + b"\n")
        time.sleep(0.1)
        # Reading command output
        # print("3")
        pageRead = 0
        pagingTime = 0
        pageNumber = 1
        pageReadTime = time.time()
        outputStream3 = ""
        lastData = []
        while pageRead == 0:
            # print(outputPage)
            outputPage = ""
            # cycleStartTime = time.time()
            if protocol == "ssh":
                waitTime = 0
                # Waiting for data
                while not connectionCursor.recv_ready():
                    execTime = time.time() - startTime
                    if ( execTime > execTimeout ):
                        print("Error: command \"" + command + "\" execution has timed out")
                        connectionCursor.send("\x03\n")
                        timeSpent = round(execTime)
                        timeLeft = round(execTimeout - round(execTime))
                        linesCount = len(re.split(r"\r*\n",outputStream3))
                        print(f"Lines read: {linesCount:>8}, pages read: {pageNumber:>4}, time spent[s]: {timeSpent:>4}, time left[s]: {timeLeft:>4}.                                    ", end="\n")
                        return [ 4, outputText, execTime]
                    time.sleep(0.1)
                    # print("waiting")
                    waitTime = waitTime + 0.1
                    if waitTime >= waitTimeout:
                        print("Error: command \"" + command + "\" execution procedure has timed out while attempting to execute target command")
                        # print(outputStream)
                        break
                while connectionCursor.recv_ready():
                    try:
                        execTime = time.time() - startTime
                        if ( execTime > execTimeout ):
                            print("Error: command \"" + command + "\" execution has timed out")
                            connectionCursor.send("\x03\n")
                            timeSpent = round(execTime)
                            timeLeft = round(execTimeout - round(execTime))
                            linesCount = len(re.split(r"\r*\n",outputStream3))
                            print(f"Lines read: {linesCount:>8}, pages read: {pageNumber:>4}, time spent[s]: {timeSpent:>4}, time left[s]: {timeLeft:>4}.                                    ", end="\n")
                            return [ 4, outputText, execTime]
                        connectionCursor.settimeout(readTimeout)
                        outputChunk = ""
                        outputChunk = connectionCursor.recv(1000).decode("utf-8")
                        # print(outputChunk)
                        outputPage = outputPage + outputChunk
                        if not connectionCursor.recv_ready():
                            time.sleep(0.1)
                    except:
                        print("   Connection error: ", sys.exc_info()[0])
                        # return None
            if protocol == "telnet":
                terminalRead = 0
                while terminalRead == 0:
                    try:
                        execTime = time.time() - startTime
                        if ( execTime > execTimeout ):
                            print("Error: command \"" + command + "\" execution has timed out")
                            connectionCursor.write(b"\x03\n")
                            timeSpent = round(execTime)
                            timeLeft = round(execTimeout - round(execTime))
                            linesCount = len(re.split(r"\r*\n",outputStream3))
                            print(f"Lines read: {linesCount:>8}, pages read: {pageNumber:>4}, time spent[s]: {timeSpent:>4}, time left[s]: {timeLeft:>4}.                                    ", end="\n")
                            return [ 4, outputText, execTime]
                        terminalLine = ""
                        terminalLine = connectionCursor.read_until(b"\n",readTimeout/5).decode('utf-8')
                        # print(terminalLine)
                        if (terminalLine == ""):
                            terminalRead = 1
                        else:
                            outputPage = outputPage + terminalLine
                    except:
                        print("   Connection error: ", sys.exc_info()[0])

            outputStream3 = outputStream3 + outputPage
            # print(outputPage)
            # Check last 3 lines for end of output or paging signs
            pagingSignFound = 0
            # print("vv")
            if len(outputStream3) > 0:
                # for line in re.split(r"\r*\n",outputStream3)[:-3:-1]:
                for line in re.split(r"\r*\n",outputStream3)[-1:]:
                    # print("lastLine")
                    # print(line)
                    line = re.sub(r"\x1b\[K( |\x08)*\x1b\[K","",line)                       # Cisco IOS-XR garbage line
                    line = re.sub(r"\x1b\[K","",line)                                       # Cisco IOS-XR garbage line
                    line = re.sub(r"\x1b\[42D +\x1b\[42D","",line)                          # Huawei VRP garbage line
                    line = re.sub(r" *\[1D","",line)                                        # Huawei VRP garbage line
                    line = line.translate(translator)
                    line = line.lstrip().rstrip()
                    # print(line)
                    # If command was to logout from remote device we expect different endings
                    if ( re.search(r"logout|quit|exit",command) ):
                        # Check if last N strings contain empty shell prompt
                        if ( re.search(shellPromptRegexEmptyLine,line) ):
                            pageRead = 1
                            break
                    else:
                        # Check if last N strings contain local shell prompt without command
                        if ( re.search(re.escape(shellPrompt) + r"( |\$)*$",line) ):
                            # print(line)
                            pageRead = 1
                            break
                    # Check if last N strings contain paging request
                    if (( re.search(r" *-- *(M|m)ore *-- *|(P|p)ress any key|(C|c)ontinue",line) ) and ( re.split(r"\r*\n",outputStream3)[-20:-1] != lastData )):
                        # print("lastData before:")
                        # print(lastData)
                        lastData = re.split(r"\r*\n",outputStream3)[-20:-1]
                        # print("lastData after:")
                        # print(lastData)
                        pagingTime = 0
                        pageNumber += 1
                        execTime = time.time() - startTime
                        timeSpent = round(execTime)
                        timeLeft = round(execTimeout - round(execTime))
                        linesCount = len(re.split(r"\r*\n",outputStream3))
                        # print(f"Lines read: {linesCount},\t\tpages read: {pageNumber},\t\ttime spent[s]: {timeSpent},\t\ttime left[s]: {timeLeft}", end="\r")
                        print(f"Lines read: {linesCount:>8}, pages read: {pageNumber:>4}, time spent[s]: {timeSpent:>4}, time left[s]: {timeLeft:>4}. Press Ctrl+C to abort this command.", end="\r")
                        # Increasing execTimeout on a value of last cycle run time to wait until paging ends
                        pagingSignFound = 1
                        # Sending space to scroll paging
                        if protocol == "ssh":
                            connectionCursor.send(" " * 100)
                        if protocol == "telnet":
                            connectionCursor.write(b" " * 100)
                        time.sleep(0.2)
                        break
                        # break
            # print("^^")

            if ( pageRead == 0 and pagingSignFound == 0 ):
                # Reading the output once again several times if we missed something
                time.sleep(0.1)
                pagingTime = pagingTime + 1
            elif ( pageRead == 1 ):
                break

            # Check paging timeout to not loop endlessly
            if pagingTime >= pagingTimeout*10:
                if protocol == "ssh":
                    connectionCursor.send("\x03\n")
                if protocol == "telnet":
                    connectionCursor.write(b"\x03\n")
                print("Error: output paging has timed out")
                timeLeft = round(execTimeout - round(execTime))
                linesCount = len(re.split(r"\r*\n",outputStream3))
                print(f"Lines read: {linesCount:>8}, pages read: {pageNumber:>4}, time spent[s]: {timeSpent:>4}, time left[s]: {timeLeft:>4}.                                    ", end="\n")
                return [ 5, outputText, execTime]

            if pagingSignFound == 1:
                execTime = time.time() - startTime
                execTimeout = execTimeout + time.time() - pageReadTime
                pageReadTime = time.time()

            linesCount = len(re.split(r"\r*\n",outputStream3))
            timeSpent = round(execTime)
            execTime = time.time() - startTime
            timeLeft = round(execTimeout - round(execTime))
            print(f"Lines read: {linesCount:>8}, pages read: {pageNumber:>4}, time spent[s]: {timeSpent:>4}, time left[s]: {timeLeft:>4}. Press Ctrl+C to abort this command.", end="\r")

        # Stream preparation
        outputStream = shellPrompt + outputStream3
        outputStream = re.sub(r"(\r)+","\r",outputStream)
        tempText = outputStream.split("\r\n")

        # Splitting text to a list
        for outputLine in tempText:
            # Protocol-specific text pre-modifications
            if ( protocol == "ssh" ):
                pass
            if ( protocol == "telnet" ):
                pass

            # Removing paging lines and special symbols
            outputLine = re.sub(r" *-* *More *-* *","",outputLine)                              # Cisco/Huawei paging line
            outputLine = re.sub(r"\x1b\[K( |\x08)*\x1b\[K","",outputLine)                       # Cisco IOS-XR garbage line
            outputLine = re.sub(r"\x1b\[K","",outputLine)                                       # Cisco IOS-XR garbage line
            outputLine = re.sub(r" *\x08+ +\x08+","",outputLine)                                # Cisco paging line
            outputLine = re.sub(r"\x1b\[42D +\x1b\[42D","",outputLine)                          # Huawei VRP garbage line
            outputLine = re.sub(r" *\[1D","",outputLine)                                        # Huawei VRP garbage line
            outputLine = re.sub(r" *Press any key to continue [a-zA-Z \(\)\.]+","",outputLine)  # Nokia paging line
            outputLine = re.sub(r"\r+ +\r+","",outputLine)                                      # Nokia paging line
            outputLine = re.sub(r" +(\r)+","",outputLine)                                       # Empty line
            outputLine = outputLine.translate(translator)

            # Protocol-specific text post-modifications
            if ( protocol == "ssh" ):
                outputLine = re.sub(r"\x00","",outputLine)  # Nokia paging line
                pass
            if ( protocol == "telnet" ):
                pass

            outputLine = outputLine.rstrip()

            outputText.append(outputLine)

        # Removing last line with CLI Prefix
        # outputText.pop()

        execTime = time.time() - startTime
        timeSpent = round(execTime)
        timeLeft = round(execTimeout - round(execTime))
        linesCount = len(re.split(r"\r*\n",outputStream3))
        # print(f"Lines read:{linesCount},\t\tpages read: {pageNumber},\t\ttime spent[s]: {timeSpent},\t\ttime left[s]: {timeLeft}", end="\n")
        print(f"Lines read: {linesCount:>8}, pages read: {pageNumber:>4}, time spent[s]: {timeSpent:>4}, time left[s]: {timeLeft:>4}.                                    ", end="\n")
        return [ 0, outputText, execTime]

#####################################################################################################################################################
#####################################################################################################################################################
#####################################################################################################################################################


#####################################################################################################################################################
###########################################################      Poll neighbor      ###########################################################
#####################################################################################################################################################
def pollNeighbor(connectionCursor,protocol,login,password1,password2,remoteAddr,srcIfName,CLISyntax,execTimeout):
    startTime = time.time()
    if execTimeout is None: execTimeout = 60
    readTimeout = 0.1
    waitTimeout = 60

    escapes = ''.join([chr(char) for char in range(1, 32)])
    translator = str.maketrans('', '', escapes)

    remoteOutputText = []
    remoteHostname = ""
    remoteSysAddr = ""
    remoteCLISyntax = ""
    remoteProtocol = ""

    # Define commands depending on syntax
    commandSSHConnect = ""
    commandTelnetConnect = ""
    # Syntax: Cisco IOS
    if CLISyntax == "IOS":
        commandSSHConnect = "ssh -l "+ login + " " + remoteAddr
        commandTelnetConnect = "telnet " + remoteAddr + " /source-interface " + srcIfName
    # Syntax: Cisco IOS-XR
    elif CLISyntax == "IOS-XR":
        if srcIfName != "":
            commandSSHConnect = "ssh " + remoteAddr + " source-interface " + srcIfName + " username " + login
            commandTelnetConnect = "telnet " + remoteAddr + " source-interface " + srcIfName
        else:
            commandSSHConnect = "ssh " + remoteAddr + " username " + login
    # Syntax: ALU/Nokia SR-OS
    elif (CLISyntax == "SR-OS"):
        commandSSHConnect = "ssh -l "+ login + " " + remoteAddr
        commandTelnetConnect = "telnet " + remoteAddr
    # Syntax: Huawei VRP
    elif (CLISyntax == "VRP"):
        # TBD
        pass

    outputStream = ""
    outputStream1 = ""
    # Sending Ctrl+C + Ctrl+Z to abort any commands in progress and exit to top level
    if protocol == "ssh":
        connectionCursor.send("\x03\x26\n")
    if protocol == "telnet":
        connectionCursor.write(b"\x03\x26\n")
    time.sleep(0.1)
    # print("1")
    # Cleaning terminal contents before execution
    if protocol == "ssh":
        while connectionCursor.recv_ready():
            try:
                execTime = time.time() - startTime
                if ( execTime > execTimeout ):
                    print("Error: remote connection to " + remoteAddr + " has timed out")
                    connectionCursor.send("\x03\n")
                    return [ 1, remoteProtocol, remoteHostname, remoteSysAddr, remoteCLISyntax, remoteOutputText, execTime]
                connectionCursor.settimeout(readTimeout)
                outputChunk = connectionCursor.recv(1000).decode("utf-8")
                # print(outputChunk)
                outputStream1 = outputStream1 + outputChunk
            except:
                print("   Connection error: ", sys.exc_info()[0])
    if protocol == "telnet":
        terminalRead = 0
        outputChunk = ""
        while terminalRead == 0:
            try:
                execTime = time.time() - startTime
                if ( execTime > execTimeout ):
                    print("Error: remote connection to " + remoteAddr + " has timed out")
                    connectionCursor.write(b"\x03\n")
                    return [ 1, remoteProtocol, remoteHostname, remoteSysAddr, remoteCLISyntax, remoteOutputText, execTime]
                terminalLine = ""
                terminalLine = connectionCursor.read_until(b"\n",readTimeout).decode('utf-8')
                if (terminalLine == ""):
                    terminalRead = 1
                outputStream1 = outputStream1 + terminalLine
            except:
                print("   Connection error: ", sys.exc_info()[0])

    # Checking if terminal is alive
    # print("2")
    outputStream2 = ""
    terminalActive = False
    for attempt in range(0,20):
        # Sending empty line to see response
        if protocol == "ssh":
            connectionCursor.send("\n")
        if protocol == "telnet":
            connectionCursor.write(b"\n")
        time.sleep(0.1)

        # Reading terminal to get CLI prefix
        if protocol == "ssh":
            waitTime = 0
            while not connectionCursor.recv_ready():
                execTime = time.time() - startTime
                if ( execTime > execTimeout ):
                    print("Error: remote connection to " + remoteAddr + " has timed out")
                    connectionCursor.send("\x03\n")
                    return [ 2, remoteProtocol, remoteHostname, remoteSysAddr, remoteCLISyntax, remoteOutputText, execTime]
                time.sleep(0.1)
                waitTime = waitTime + 0.1
                if waitTime >= waitTimeout:
                    print("Error: remote connection to " + remoteAddr + " has timed out while attempting to get CLI prefix")
                    break
        if protocol == "ssh":
            while connectionCursor.recv_ready():
                try:
                    execTime = time.time() - startTime
                    if ( execTime > execTimeout ):
                        print("Error: remote connection to " + remoteAddr + " has timed out")
                        connectionCursor.send("\x03\n")
                        return [ 2, remoteProtocol, remoteHostname, remoteSysAddr, remoteCLISyntax, remoteOutputText, execTime]
                    connectionCursor.settimeout(readTimeout)
                    outputChunk = connectionCursor.recv(1000).decode("utf-8")
                    outputStream2 = outputStream2 + outputChunk
                    if not connectionCursor.recv_ready():
                        time.sleep(0.1)
                except:
                    print("   Connection error: ", sys.exc_info()[0])
        if protocol == "telnet":
            terminalRead = 0
            outputChunk = ""
            while terminalRead == 0:
                try:
                    execTime = time.time() - startTime
                    if ( execTime > execTimeout ):
                        print("Error: remote connection to " + remoteAddr + " has timed out")
                        connectionCursor.write(b"\x03\n")
                        return [ 2, remoteProtocol, remoteHostname, remoteSysAddr, remoteCLISyntax, remoteOutputText, execTime]
                    terminalLine = ""
                    terminalLine = connectionCursor.read_until(b"\n",readTimeout).decode('utf-8')
                    if (terminalLine == ""):
                        terminalRead = 1
                    else:
                        outputStream2 = outputStream2 + terminalLine
                except:
                    print("   Connection error: ", sys.exc_info()[0])

        for line in re.split(r"\r*\n",outputStream2)[-1:]:
            line = re.sub(r"\x1b\[K( |\x08)*\x1b\[K","",line)                       # Cisco IOS-XR garbage line
            line = re.sub(r"\x1b\[K","",line)                                       # Cisco IOS-XR garbage line
            line = re.sub(r"\x1b\[42D +\x1b\[42D","",line)                          # Huawei VRP garbage line
            line = re.sub(r" *\[1D","",line)                                        # Huawei VRP garbage line
            line = line.translate(translator)
            line = line.lstrip().rstrip()
        # if ( re.search(shellPromptRegexEmptyLine,outputStream2.replace("\r","")) ):
            if ( re.search(shellPromptRegexEmptyLine,line) ):
                # shellPrompt = re.search(shellPromptRegexEmptyLine,outputStream2.replace("\r","")).group().lstrip().rstrip()
                localShellPrompt = re.search(shellPromptRegexEmptyLine,line).group()
                # print("shellPrompt")
                # print(shellPrompt)
                terminalActive = True
                break
        # else:
        #     time.sleep(0.5)
        if terminalActive == False:
            time.sleep(0.1)
        else:
            break

    if ( not terminalActive ):
        print("Error: terminal not responding while trying to connect to " + remoteAddr)
        return [ 3, remoteProtocol, remoteHostname, remoteSysAddr, remoteCLISyntax, remoteOutputText, execTime]
    else:
        # First try SSH and then Telnet
        outputStream3 = ""
        for attempt in range(2):
            if attempt == 0:
                command = commandSSHConnect
                remoteProtocol = "SSH"
            else:
                command = commandTelnetConnect
                remoteProtocol = "Telnet"

            # Sending command
            if protocol == "ssh":
                # connectionCursor.send("\n" + command + "\n")
                connectionCursor.send(command + "\n")
            if protocol == "telnet":
                # connectionCursor.write(b"\n" + command.encode('ascii') + b"\n")
                connectionCursor.write(command.encode('ascii') + b"\n")

            print(f"Sending command {command}")
            time.sleep(1)

            # Reading command output and waiting for password prompt
            connectionSuccess = 0
            while connectionSuccess == 0:
                # time.sleep(1)
                outputPage = ""
                if protocol == "ssh":
                    waitTime = 0
                    # Waiting for data
                    while not connectionCursor.recv_ready():
                        execTime = time.time() - startTime
                        if ( execTime > execTimeout ):
                            print("Error: command \"" + command + "\" execution has timed out")
                            connectionCursor.send("\x03\n")
                            connectionSuccess = -1
                            break
                        time.sleep(0.1)
                        waitTime = waitTime + 0.1
                        if waitTime >= waitTimeout:
                            print("Error: command \"" + command + "\" execution procedure has timed out while attempting to execute target command")
                            break
                    while connectionCursor.recv_ready():
                        try:
                            execTime = time.time() - startTime
                            if ( execTime > execTimeout ):
                                print("Error: command \"" + command + "\" execution has timed out")
                                connectionCursor.send("\x03\n")
                                connectionSuccess = -1
                                break
                            connectionCursor.settimeout(readTimeout)
                            outputChunk = ""
                            outputChunk = connectionCursor.recv(1000).decode("utf-8")
                            # print(outputChunk)
                            outputPage = outputPage + outputChunk
                            if not connectionCursor.recv_ready():
                                time.sleep(0.1)
                        except:
                            print("   Connection error: ", sys.exc_info()[0])
                            # return None
                if protocol == "telnet":
                    terminalRead = 0
                    while terminalRead == 0:
                        try:
                            execTime = time.time() - startTime
                            if ( execTime > execTimeout ):
                                print("Error: command \"" + command + "\" execution has timed out")
                                connectionCursor.write(b"\x03\n")
                                connectionSuccess = -1
                                break
                            terminalLine = ""
                            terminalLine = connectionCursor.read_until(b"\n",readTimeout/5).decode('utf-8')
                            # print(terminalLine)
                            if (terminalLine == ""):
                                terminalRead = 1
                            else:
                                outputPage = outputPage + terminalLine
                        except:
                            print("   Connection error: ", sys.exc_info()[0])

                outputStream3 = outputStream3 + outputPage
                remoteOutputText.extend(re.split(r"\r*\n",outputPage))

                # Check text lines for login/password or shell prompts
                if len(outputStream3) > 0:
                    for line in re.split(r"\r*\n",outputStream3)[-1:]:
                        if re.search(r"((E|e)rror|(F|f)ail|(R|r)efuse|(N|n)ot +allowed)",line):
                            print(f"Received a line with error \"{line}\"")
                            connectionSuccess = -1
                            # Aborting previous commands
                            if protocol == "ssh":
                                connectionCursor.send("\x03\n")
                            if protocol == "telnet":
                                connectionCursor.write(b"\x03\n")
                            time.sleep(3)
                            break
                        elif re.search(r"(Y|y)es(/(N|n)o)?",line):
                            print(f"Received yes/no prompt \"{line}\"")
                            # Accepting remote key
                            if protocol == "ssh":
                                connectionCursor.send("yes\n")
                            if protocol == "telnet":
                                connectionCursor.write(b"yes\n")
                            time.sleep(1)
                            break
                        elif re.search(r"((L|l)ogin|((U|u)ser)?(N|n)ame)",line):
                            print(f"Received username request \"{line}\"")
                            # Sending login
                            if protocol == "ssh":
                                connectionCursor.send(login + "\n")
                            if protocol == "telnet":
                                connectionCursor.write(login.encode('ascii') + b"\n")
                            time.sleep(1)
                            break
                        elif re.search(r"(P|p)ass(word)?",line):
                            print(f"Received password request \"{line}\"")
                            # Sending password
                            if protocol == "ssh":
                                connectionCursor.send(password1 + "\n")
                            if protocol == "telnet":
                                connectionCursor.write(password1.encode('ascii') + b"\n")
                            time.sleep(1)
                            break
                        # Detect if output contains local shell prompt without command (connection failed)
                        elif ( re.search(re.escape(localShellPrompt) + r"( |\$)*$",line) ):
                            print(f"Received local shell prompt \"{line}\"")
                            connectionSuccess = -1
                            break
                        # Detect if output contains any other shell prompt without command (connection succedeed)
                        elif ( re.search(shellPromptRegexEmptyLine,line) ):
                            print(f"Received remote shell prompt \"{line}\"")
                            connectionSuccess = 1
                            break

            # Check if we are connected, then proceed
            if connectionSuccess == 1:
                break

        remoteOutputText.extend(re.split(r"\r*\n",outputStream1 + outputStream2 + outputStream3))

        if connectionSuccess != 1:
            if protocol == "ssh":
                connectionCursor.send("\x03")
            if protocol == "telnet":
                connectionCursor.write(b"\x03")

            print("Error: remote connection to " + remoteAddr + " failed")
            execTime = time.time() - startTime
            return [ 5, remoteProtocol, remoteHostname, remoteSysAddr, remoteCLISyntax, remoteOutputText, execTime]
        else:

            # Determine SW version and CLI syntax
            remoteCLISyntax = ""
            # Issuing a Cisco/Nokia style command
            for attempt in range(0,2):
                remoteVersionLines = []
                print("Executing remote command \"" + str(CommandsDict["IOS"][0][0]) + "\"")
                output = execCLICommand(connectionCursor, protocol, CommandsDict["IOS"][0][0], CommandsDict["IOS"][0][1])
                remoteVersionLines.extend(output[1])
                if output[0] == 0: break

            # Trying to find shell prompt
            remoteShellPrompt = ""
            for line in remoteVersionLines:
                if not re.match(r"^#+.*#+$",line):
                    # Syntax: all
                    if re.search(shellPromptRegex,line):
                        remoteShellPrompt = line.lstrip().rstrip()
                        remoteShellPrompt = re.split(r"((>|#|\$|\%))", remoteShellPrompt)[0] + re.split(r"((>|#|\$|\%))", remoteShellPrompt)[1]
                    if remoteShellPrompt != "":
                        print("Found remote shell prompt: "+remoteShellPrompt)
                        break

            # Trying to find CLI syntax of Cisco/Nokia node
            for line in remoteVersionLines:
                searchExpression = r'.*Cisco IOS XR'
                if re.match(searchExpression,line):
                    remoteCLISyntax = "IOS-XR"
                    break
                searchExpression = r'.*Cisco IOS((-| )XE)? '
                if re.match(searchExpression,line):
                    remoteCLISyntax = "IOS"
                    break
                searchExpression = r'.*TiMOS-'
                if re.match(searchExpression,line):
                    remoteCLISyntax = "SR-OS"
                    break

            if remoteCLISyntax == "":
                # Issuing a Huawei style command
                for attempt in range(0,2):
                    remoteVersionLines = []
                    print("Executing remote command \"" + str(CommandsDict["VRP"][0][0]) + "\"")
                    output = execCLICommand(connectionCursor, protocol, CommandsDict["VRP"][0][0], CommandsDict["VRP"][0][1])
                    remoteVersionLines.extend(output[1])
                    if output[0] == 0: break

                # Trying to find CLI syntax of Hiawei node
                for line in remoteVersionLines:
                    searchExpression = r'.*VRP \(R\) software'
                    if re.match(searchExpression,line):
                        remoteCLISyntax = "VRP"
                        break

            remoteOutputText.extend(remoteVersionLines)
            if remoteCLISyntax == "":
                print("Could not determine remote CLI syntax, skipping to next remote node")
                remoteOutputText = remoteVersionLines.copy()
                command3 = "exit"
                print("Executing remote command \"" + str(command3) + "\"")
                output3 = execCLICommand(connectionCursor, protocol, command3, 10)
                if not ( re.search(re.escape(localShellPrompt) + r"( |\$)*$",output3[-1]) ):
                    command3 = "logout"
                    print("Executing remote command \"" + str(command3) + "\"")
                    output3 = execCLICommand(connectionCursor, protocol, command3, 10)
                remoteOutputText.extend(output3[1])
                execTime = time.time() - startTime
                return [ 0, remoteProtocol, remoteHostname, remoteSysAddr, remoteCLISyntax, remoteOutputText, execTime]
            else:
                print("Using following command syntax for this remote node: "+remoteCLISyntax)

            remoteEnableLines = []
            # Vendor-specific preparation phase
            if remoteCLISyntax == "IOS":
                if re.search(r'>',remoteShellPrompt):

                    for attempt in range(0,2):
                        print("Executing remote command \"enable\"")
                        output = execCLICommand(connectionCursor, protocol, "enable\n" + password2, 20)
                        remoteEnableLines.extend(output[1])
                        remoteOutputText.extend(remoteEnableLines)
                        if output[0] == 0: break

                    # if debug:
                    #     with open("./" + outputPath + "/debugText.txt", 'a') as debugTextFile:
                    #         debugTextFile.write("\n".join(str(item) for item in enableLines))

                    remoteShellPrompt = remoteShellPrompt.replace(">","#")
                    searchExpression = re.escape(remoteShellPrompt)
                    match = 0
                    for line in output[1]:
                        if re.search(searchExpression, line):
                            match = 1
                            break
                    if match == 1:
                        for attempt in range(0,2):
                            remoteVersionLines = []
                            print("Executing remote command \"" + str(CommandsDict["IOS"][0][0]) + "\"")
                            output = execCLICommand(connectionCursor, protocol, CommandsDict["IOS"][0][0], CommandsDict["IOS"][0][1])
                            remoteVersionLines.extend(output[1])
                            remoteOutputText.extend(remoteVersionLines)
                            if output[0] == 0: break

                        print("Using new remote shell prompt: "+remoteShellPrompt)


                    else:
                        print("Could not activate enable mode, skipping to next node")
                        execTime = time.time() - startTime
                        return [ 0, remoteProtocol, remoteHostname, remoteSysAddr, remoteCLISyntax, remoteOutputText, execTime]



            # Send required commands
            if remoteCLISyntax == "IOS" or remoteCLISyntax == "IOS-XR":
                command1 = "show run | i hostname"
                print("Executing remote command \"" + str(command1) + "\"")
                output1 = execCLICommand(connectionCursor, protocol, command1, 10)
                remoteOutputText.extend(output1[1])
                for line in output1[1]:
                    if re.match(r"^ *hostname ",line):
                        remoteHostname = line.split("hostname ")[1].split()[0]
                        break
                command2 = "show running-config interface Loopback0 | i address"
                print("Executing remote command \"" + str(command2) + "\"")
                output2 = execCLICommand(connectionCursor, protocol, command2, 10)
                remoteOutputText.extend(output2[1])
                for line in output2[1]:
                    if re.match(r"^ *ip(v4)? address ",line):
                        remoteSysAddr = line.split("address ")[1].split()[0].split("/")[0]
                        break
                command3 = "exit"
                print("Executing remote command \"" + str(command3) + "\"")
                output3 = execCLICommand(connectionCursor, protocol, command3, 10)
                remoteOutputText.extend(output3[1])

            if remoteCLISyntax == "SR-OS":
                command1 = "admin display-config | match \"        name\""
                print("Executing remote command \"" + str(command1) + "\"")
                output1 = execCLICommand(connectionCursor, protocol, command1, 10)
                remoteOutputText.extend(output1[1])
                for line in output1[1]:
                    if re.match(r"^ *name ",line):
                        remoteHostname = line.split("name ")[1].split()[0].replace("\"","")
                        break
                command2 = "admin display-config | match \"interface \\\"system\\\"\" context children | match address"
                print("Executing remote command \"" + str(command2) + "\"")
                output2 = execCLICommand(connectionCursor, protocol, command2, 10)
                remoteOutputText.extend(output2[1])
                for line in output2[1]:
                    if re.match(r"^ *address ",line):
                        remoteSysAddr = line.split("address ")[1].split()[0].split("/")[0]
                        break
                command3 = "logout"
                print("Executing remote command \"" + str(command3) + "\"")
                output3 = execCLICommand(connectionCursor, protocol, command3, 10)
                remoteOutputText.extend(output3[1])

            # print(output1)
            # print(output2)

    execTime = time.time() - startTime
    return [ 0, remoteProtocol, remoteHostname, remoteSysAddr, remoteCLISyntax, remoteOutputText, execTime]

#####################################################################################################################################################
#####################################################################################################################################################
#####################################################################################################################################################



#####################################################################################################################################################
###########################################################      Print help function      ###########################################################
#####################################################################################################################################################
def printHelpFunc():
    print("""
confParser script v3.2 2021-03-10

This script is used to parse text files with output of router's show-commands into structured data. Script supports syntaxes of Cisco IOS/IOS-XE,
IOS-XR, Huawei VRP and Nokia/ALU SR-OS.

There are several actions available:

    -h|--help       Print help


    -c|--collect    {login} {IPv4 addresses list/file} {output directory name}

            Collect text output from a set of show commands and save it into output directory for future use. To begin login, router's management
            IPv4 adress and output directory path must be specified. Password and enable password will be asked in prompt.

            If it is required to collect output for multiple routers in a single run there are multiple options that can be combined:
            1) You can set adress argument as an individual adress (e.g. 1.1.1.1 or 1.1.1.1/32)
            2) You can set adress argument as a subnet using "/" notation (e.g. 10.0.0.0/30): it will make script going though the all
               adresses in this subnet and collecting required data.
            3) You can set adress as a range between two adresses (separated by "-") (e.g. 2.2.2.2-2.2.2.10)
            4) You can provide path to a text file containing list of addresses, address ranges or subnets mentioned in 1)-3) or file containing
               current router configuration with BGP peers which addresses will be used as input.

            Combining any of these options in terminal requires using a "," separator without spaces (e.g. 1.1.1.1,10.0.0.0/30,2.2.2.2-2.2.2.10),
            while combining them in a file requires using a new line for each input.

            Appropriate CLI syntax (to issue correct commands) is detected automatically using "show|display version" output.

    -p|--parse      {input directory/directory+filename} {output database directory+name} [default CLI syntax] [clean]

            Parse manually collected show outputs into a SQLite database. Specify either a path to single config file or a path to directory with
            multiple config/show files. Output database must be specified as well.

            To save input data recognized and filtered by script into a separate files use optional "clean" argument. These files will be stored in
            ./clean_input directory.

            Each node must use separate input file containing output of the following commands (* marks required data):
            > Cisco IOS/IOS-XE, IOS-XR:
                - *show version - used to recognize SW version and CLI syntax
                - *show running-config
                - show interfaces
                - show inventory
                - show ip interface (IOS/IOS-XE)
                - show ipv4 interface (IOS-XR)
                - show ipv6 interface
            > Huawei VRP:
                - *display version - used to recognize SW version and CLI syntax
                - *display current-configuration
                - display interface
                - display ip interface
                - display ipv6 interface
            > Nokia/ALU SR-OS:
                - *show version - used to recognize SW version and CLI syntax
                - *admin display-config
                - show port
                - show port <port-id> optical
                - show router interface detail

            Note: "show/display version" is used to define parsing syntax and is mandatory if no default syntax is specified or default syntax does
            not match actual syntax of the file being parsed. So if you want to parse only a config file without any other show outputs - specify
            default syntax: """+", ".join(str(k) for k,v in SyntaxDict.items() if k != "Hist")+
    """

    -o|--output     {database dir+name} {output dir+filename} [target CLI syntax]

            Print data from database to .csv or .xlsx file (file extension must be specified). Data with specified target CLI syntax is considered
            a destination configuration (e.g. for a node swap/replacement), while data related to all other syntaxes - is a source config. If no
            target CLI syntax specified all config/data is cosidered source. Source config/data will be displayed on the left side (table) of output
            file, and destination config/data - on the right side (table).

            Supported target CLI syntax keys are: """+", ".join(str(k) for k,v in SyntaxDict.items() if k != "Hist")+"""
    """)
#####################################################################################################################################################
#####################################################################################################################################################
#####################################################################################################################################################






#####################################################################################################################################################
###########################################################        Parse function         ###########################################################
#####################################################################################################################################################
def parseFunc(inputFiles,outputDB,defaultCLISyntax,genClean):
    print("Parsing...\r\n")

    outputCursor = outputDB.cursor()

    for showFilePath in inputFiles: # Select new file to parse
        if debug: print("debug: Reading file "+str(showFilePath))
        showFileContent = open(showFilePath,"r",newline ='\r')
        showFileLines = showFileContent.readlines()
        lineNumber = 0
        nextFile = 0
        redirectOutputTo = "default"
        CLIDelimiter = ""

        versionLines = []                   # Extracted version output lines from input file
        configLines = []                    # Extracted configuration output lines from input file
        configLines2 = []                   # Extracted configuration output lines from input file when inpur file is a config file only
        PHYInterfacesLines = []             # Extracted physical interface output lines from input file
        IPInterfacesLines = []              # Extracted IPv4/IPv6 interface output lines from input file
        MPLSInterfacesLines = []            # Extracted MPLS/LDP/RSVP interface output lines from input file
        CDPNeighborsLines = []              # Extracted CDP neighbors output lines from input file
        LLDPNeighborsLines = []             # Extracted LLDP neighbors output lines from input file
        BFDNeighborsLines = []              # Extracted BFD neighbors output lines from input file
        OSPFv2NeighborsLines = []           # Extracted OSPFv2 neighbors output lines from input file
        OSPFv2LSDBLines = []                # Extracted OSPFv2 LSDB output lines from input file
        OSPFv3NeighborsLines = []           # Extracted OSPFv3 neighbors output lines from input file
        OSPFv3LSDBLines = []                # Extracted OSPFv3 LSDB output lines from input file
        ISISNeighborsLines = []             # Extracted IS-IS neighbors output lines from input file
        ISISLSDBLines = []                  # Extracted IS-IS LSDB output lines from input file
        LDPNeighborsLines = []              # Extracted LDP neighbors output lines from input file
        RSVPNeighborsLines = []             # Extracted RSVP neighbors output lines from input file
        BGPNeighborsLines = []              # Extracted BGP neighbors output lines from input file
        L3VPNServiceLines = []              # Extracted L3VPNs output lines from input file
        L2VPNServiceLines = []              # Extracted L2VPNs output lines from input file
        VPLSServiceLines = []               # Extracted VPLS output lines from input file

        for line in showFileLines:
            lineNumber = lineNumber + 1

            # if debug: print(line)

            # Remove paging from log (Cisco/Huawei)
            if re.search(r"(---- )|(--)More(--)|( ----)",line):
                # Huawei
                line = line.replace("  ---- More ----[42D                                          [42D","")
                # Cisco IOS-XR
                line = line.replace("[K --More--           [K","")
                # Cisco IOS
                line = line.replace(" --More--         ","")

            # Remove aux symbols from Putty log
            # line = line.replace("\x00\r","") # NULCR
            # line = line.replace("\x00","") # NUL
            # line = line.replace("","") # BS
            # line = line.replace("","") # BEL
            line = line.replace("[1C ","") # [1D
            line = line.replace("[1Cr","") # [1D
            line = line.replace("[1C","") # [1D
            line = line.replace("[1D ","") # [1D
            line = line.replace("[1Dr","") # [1D
            line = line.replace("[1D","") # [1D
            line = line.replace("[2D ","") # [2D
            line = line.replace("[2Dr","") # [2D
            line = line.replace("[2D","") # [2D


            # Remove paging from log (Nokia)
            if re.search(r"(---- )|(--)More(--)|( ----)",line):
                # Nokia
                line = line.replace("Press any key to continue (Q to quit)                                      \r","")

            # Remove right spacing and escape symbols
            line = line.rstrip()
            line = line.replace("\t","    ")                                   # Replace tabulation to four spaces
            escapes = ''.join([chr(char) for char in range(1, 32)])
            translator = str.maketrans('', '', escapes)
            line = line.translate(translator)

            # if debug: print(line)

            # if debug:
            #     if re.search(r'(N|n)o',input("Press any key to do for the next interface, or \"no\" to stop:\r\n")):
            #         print("Stopping parsing")
            #         sys.exit()

            # Match version output
            # Syntax: Cisco IOS/IOS-XE/IOS-XR, ALU/Nokia SR-OS
            if re.search(r'(#|>)[ ]*sh(o(w)?)? +ver(s(i(o(n)?)?)?)?',line):
                if redirectOutputTo != "version":
                    if debug: print("debug: "+ redirectOutputTo +" output ends at line "+str(lineNumber)+": "+line)
                if debug: print("debug: Found version output beginning at line "+str(lineNumber)+": "+line)
                redirectOutputTo = "version"
                versionLines.append(line)
                if re.search(r'>',line):
                    CLIDelimiter = line.split(">")[0]+">"
                else:
                    if re.search(r'#',line):
                        CLIDelimiter = line.split("#")[0]+"#"
                if CLIDelimiter != "":
                    print("Found CLI delimiter beginning at line "+str(lineNumber)+": "+CLIDelimiter)
                    continue
                # else:
                #     print("Could not find CLI delimiter in file "+str(showFilePath))
                #     break

            # Syntax: Huawei VRP
            if re.search(r'(#|>)[ ]*dis(p(l(a(y)?)?)?)? +ver(s(i(o(n)?)?)?)?',line):
                if redirectOutputTo != "version":
                    if debug: print("debug: "+ redirectOutputTo +" output ends at line "+str(lineNumber)+": "+line)
                if debug: print("debug: Found version output beginning at line "+str(lineNumber)+": "+line)
                redirectOutputTo = "version"
                versionLines.append(line)
                if re.search(r'>',line):
                    CLIDelimiter = line.split(">")[0]+">"
                else:
                    if re.search(r'#',line):
                        CLIDelimiter = line.split("#")[0]+"#"
                if CLIDelimiter != "":
                    print("Found CLI delimiter beginning at line "+str(lineNumber)+": "+CLIDelimiter)
                    continue
                else:
                    print("Could not find CLI delimiter in file "+str(showFilePath))
                    break

            if defaultCLISyntax != "":
                configLines2.append(line)

            # Match configuration output
            # Syntax: Cisco IOS/IOS-XE/Cisco IOS-XR
            searchExpression = r""+re.escape(CLIDelimiter)+"[ ]*sh(o(w)?)? +run(n(i(n(g(-(c(o(n(f(i(g)?)?)?)?)?)?)?)?)?)?)?"
            if re.search(searchExpression,line):
                if redirectOutputTo != "config":
                    if debug: print("debug: "+ redirectOutputTo +" output ends at line "+str(lineNumber)+": "+line)
                if debug: print("debug: Found config output beginning at line "+str(lineNumber)+": "+line)
                redirectOutputTo = "config"
                configLines.append(line)
                continue
            # Syntax: Huawei VRP
            searchExpression = r""+re.escape(CLIDelimiter)+"[ ]*dis(p(l(a(y)?)?)?)? +cur(r(e(n(t(-(c(o(n(f(i(g)?)?)?)?)?)?)?)?)?)?)?"
            if re.search(searchExpression,line):
                if redirectOutputTo != "config":
                    if debug: print("debug: "+ redirectOutputTo +" output ends at line "+str(lineNumber)+": "+line)
                if debug: print("debug: Found config output beginning at line "+str(lineNumber)+": "+line)
                redirectOutputTo = "config"
                configLines.append(line)
                continue
            # Syntax: ALU/Nokia SR-OS
            searchExpression = r""+re.escape(CLIDelimiter)+"[ ]*adm(i|in)* +disp(l(a(y(-(c(o(n(f(i(g)?)?)?)?)?)?)?)?)?)?"
            if re.search(searchExpression,line):
                if redirectOutputTo != "config":
                    if debug: print("debug: "+ redirectOutputTo +" output ends at line "+str(lineNumber)+": "+line)
                if debug: print("debug: Found config output beginning at line "+str(lineNumber)+": "+line)
                redirectOutputTo = "config"
                configLines.append(line)
                continue

            # Match PHY interface output
            # Syntax: Cisco IOS/IOS-XE/Cisco IOS-XR
            searchExpression = r""+re.escape(CLIDelimiter)+"[ ]*sh(o(w)?)? +int(e(r(f(a(c(e)?)?)?)?)?)?"
            if re.search(searchExpression,line):
                if redirectOutputTo != "PHYInterfaces":
                    if debug: print("debug: "+ redirectOutputTo +" output ends at line "+str(lineNumber)+": "+line)
                if debug: print("debug: Found PHY interface output beginning at line "+str(lineNumber)+": "+line)
                redirectOutputTo = "PHYInterfaces"
                PHYInterfacesLines.append(line)
                continue
            searchExpression = r""+re.escape(CLIDelimiter)+"[ ]*sh(o(w)?)? +inv(e(n(t(o(r(y)?)?)?)?)?)?"
            if re.search(searchExpression,line):
                if redirectOutputTo != "PHYInterfaces":
                    if debug: print("debug: "+ redirectOutputTo +" output ends at line "+str(lineNumber)+": "+line)
                if debug: print("debug: Found PHY interface output beginning at line "+str(lineNumber)+": "+line)
                redirectOutputTo = "PHYInterfaces"
                PHYInterfacesLines.append(line)
                continue
            # Syntax: Huawei VRP
            searchExpression = r""+re.escape(CLIDelimiter)+"[ ]*dis(p(l(a(y)?)?)?)? +int(e(r(f(a(c(e)?)?)?)?)?)?"
            if re.search(searchExpression,line):
                if redirectOutputTo != "PHYInterfaces":
                    if debug: print("debug: "+ redirectOutputTo +" output ends at line "+str(lineNumber)+": "+line)
                if debug: print("debug: Found PHY interface output beginning at line "+str(lineNumber)+": "+line)
                redirectOutputTo = "PHYInterfaces"
                PHYInterfacesLines.append(line)
                continue
            # searchExpression = r""+re.escape(CLIDelimiter)+
            # if re.search(r'(#|>)[ ]*dis(p(l(a(y)?)?)?)? +int(e(r(f(a(c(e)?)?)?)?)?)? +ph(y(-(o(p(t(i(o(n)?)?)?)?)?)?)?)?',line):
            #     if debug: print("debug: Found PHY interface output beginning at line "+str(lineNumber)+": "+line)
            #     redirectOutputTo = "PHYInterfaces"
            #     PHYInterfacesLines.append(line)
            #     continue
            # Syntax: ALU/Nokia SR-OS
            searchExpression = r""+re.escape(CLIDelimiter)+"[ ]*sh(o(w)?)? +po(r(t)?)?"
            if re.search(searchExpression,line):
                if redirectOutputTo != "PHYInterfaces":
                    if debug: print("debug: "+ redirectOutputTo +" output ends at line "+str(lineNumber)+": "+line)
                if debug: print("debug: Found PHY interface output beginning at line "+str(lineNumber)+": "+line)
                redirectOutputTo = "PHYInterfaces"
                PHYInterfacesLines.append(line)
                continue
            # searchExpression = r""+re.escape(CLIDelimiter)+
            # if re.search(r'(#|>)[ ]*sh(o(w)?)? +po(r(t)?)? +(esat-)?[0-9]{1,2}/[0-9]{1,2}/(c)?[0-9]{1,2}(/(u)?[0-9]{1,2})?( +o(p(t(i(c(a(l)?)?)?)?)?)?)?',line):
            #     if debug: print("debug: Found PHY interface output beginning at line "+str(lineNumber)+": "+line)
            #     redirectOutputTo = "PHYInterfaces"
            #     PHYInterfacesLines.append(line)
            #     continue


            # Match IPv4/v6 interface output
            # Syntax: Cisco IOS/IOS-XE/IOS-XR
            searchExpression = r""+re.escape(CLIDelimiter)+"[ ]*sh(o(w)?)? +ip(v(4|6))? +int(e(r(f(a(c(e)?)?)?)?)?)?"
            if re.search(searchExpression,line):
                if redirectOutputTo != "IPInterfaces":
                    if debug: print("debug: "+ redirectOutputTo +" output ends at line "+str(lineNumber)+": "+line)
                if debug: print("debug: Found IP interfaces output beginning at line "+str(lineNumber)+": "+line)
                redirectOutputTo = "IPInterfaces"
                IPInterfacesLines.append(line)
                continue
            # Syntax: Huawei VRP
            searchExpression = r""+re.escape(CLIDelimiter)+"[ ]*dis(p(l(a(y)?)?)?)? +ip(v6)? +int(e(r(f(a(c(e)?)?)?)?)?)?"
            if re.search(searchExpression,line):
                if redirectOutputTo != "IPInterfaces":
                    if debug: print("debug: "+ redirectOutputTo +" output ends at line "+str(lineNumber)+": "+line)
                if debug: print("debug: Found IP interfaces output beginning at line "+str(lineNumber)+": "+line)
                redirectOutputTo = "IPInterfaces"
                IPInterfacesLines.append(line)
                continue
            # Syntax: ALU/Nokia SR-OS
            searchExpression = r""+re.escape(CLIDelimiter)+"[ ]*sh(o(w)?)? +ro(u(t(e(r)?)?)?)? +int(e(r(f(a(c(e)?)?)?)?)?)? de(t(a(i(l)?)?)?)?"
            if re.search(searchExpression,line):
                if redirectOutputTo != "IPInterfaces":
                    if debug: print("debug: "+ redirectOutputTo +" output ends at line "+str(lineNumber)+": "+line)
                if debug: print("debug: Found IP interfaces output beginning at line "+str(lineNumber)+": "+line)
                redirectOutputTo = "IPInterfaces"
                IPInterfacesLines.append(line)
                continue

            # Match unknown command output
            # Syntax: all
            searchExpression = r"^"+re.escape(CLIDelimiter)
            if re.search(searchExpression,line):
                # if debug: print("debug: Found unknown output beginning at line "+str(lineNumber)+": "+line)
                if redirectOutputTo != "default":
                    if debug: print("debug: "+ redirectOutputTo +" output ends at line "+str(lineNumber)+": "+line)
                redirectOutputTo = "default"
                continue


            # Redirect already classified output to appropriate list
            if redirectOutputTo == "version":
                versionLines.append(line)
                # if debug: print("version: "+str(lineNumber)+": "+line)
                continue
            if redirectOutputTo == "config":
                configLines.append(line)
                continue
            if redirectOutputTo == "PHYInterfaces":
                PHYInterfacesLines.append(line)
                continue
            if redirectOutputTo == "IPInterfaces":
                IPInterfacesLines.append(line)
                continue
            if redirectOutputTo == "MPLSInterfaces":
                MPLSInterfacesLines.append(line)
                continue
            if redirectOutputTo == "CDPNeighbors":
                CDPNeighborsLines.append(line)
                continue
            if redirectOutputTo == "LLDPNeighbors":
                LLDPNeighborsLines.append(line)
                continue
            if redirectOutputTo == "BFDNeighbors":
                BFDNeighborsLines.append(line)
                continue
            if redirectOutputTo == "OSPFv2Neighbors":
                OSPFv2NeighborsLines.append(line)
                continue
            if redirectOutputTo == "OSPFv2LSDB":
                OSPFv2LSDBLines.append(line)
                continue
            if redirectOutputTo == "OSPFv3Neighbors":
                OSPFv3NeighborsLines.append(line)
                continue
            if redirectOutputTo == "OSPFv3LSDB":
                OSPFv3LSDBLines.append(line)
                continue
            if redirectOutputTo == "ISISNeighbors":
                ISISNeighborsLines.append(line)
                continue
            if redirectOutputTo == "ISISLSDB":
                ISISLSDBLines.append(line)
                continue
            if redirectOutputTo == "LDPNeighbors":
                LDPNeighborsLines.append(line)
                continue
            if redirectOutputTo == "RSVPNeighbors":
                RSVPNeighborsLines.append(line)
                continue
            if redirectOutputTo == "BGPNeighbors":
                BGPNeighborsLines.append(line)
                continue
            if redirectOutputTo == "L3VPNService":
                L3VPNServiceLines.append(line)
                continue
            if redirectOutputTo == "L2VPNService":
                L2VPNServiceLines.append(line)
                continue
            if redirectOutputTo == "VPLSService":
                VPLSServiceLines.append(line)
                continue
            if redirectOutputTo == "OSPFv2Neighbors":
                OSPFv2NeighborsLines.append(line)
                continue
            if redirectOutputTo == "OSPFv3Neighbors":
                OSPFv3NeighborsLines.append(line)
                continue
            if redirectOutputTo == "BGPNeighbors":
                BGPNeighborsLines.append(line)
                continue

        if debug: input("Input file processed. Press any key proceed.\r\n")

        # # if debug: print("debug: Printing versionLines\r\n"+str(versionLines))
        # if debug: print("debug: Printing configLinesToParser\r\n"+str(configLinesToParser))
        # if debug: print("debug: Printing PHYInterfacesLines\r\n"+str(PHYInterfacesLines))
        # if debug: print("debug: Printing IPInterfacesLines\r\n"+str(IPInterfacesLines))
        # if debug: print("debug: Printing MPLSInterfacesLines\r\n"+str(MPLSInterfacesLines))
        # if debug: print("debug: Printing CDPNeighborsLines\r\n"+str(CDPNeighborsLines))
        # if debug: print("debug: Printing LLDPNeighborsLines\r\n"+str(LLDPNeighborsLines))
        # if debug: print("debug: Printing BFDNeighborsLines\r\n"+str(BFDNeighborsLines))
        # if debug: print("debug: Printing OSPFv2NeighborsLines\r\n"+str(OSPFv2NeighborsLines))
        # if debug: print("debug: Printing OSPFv2LSDBLines\r\n"+str(OSPFv2LSDBLines))
        # if debug: print("debug: Printing OSPFv3NeighborsLines\r\n"+str(OSPFv3NeighborsLines))
        # if debug: print("debug: Printing OSPFv3LSDBLines\r\n"+str(OSPFv3LSDBLines))
        # if debug: print("debug: Printing ISISNeighborsLines\r\n"+str(ISISNeighborsLines))
        # if debug: print("debug: Printing ISISLSDBLines\r\n"+str(ISISLSDBLines))
        # if debug: print("debug: Printing LDPNeighborsLines\r\n"+str(LDPNeighborsLines))
        # if debug: print("debug: Printing RSVPNeighborsLines\r\n"+str(RSVPNeighborsLines))
        # if debug: print("debug: Printing BGPNeighborsLines\r\n"+str(BGPNeighborsLines))
        # if debug: print("debug: Printing L3VPNServiceLines\r\n"+str(L3VPNServiceLines))
        # if debug: print("debug: Printing L2VPNServiceLines\r\n"+str(L2VPNServiceLines))
        # if debug: print("debug: Printing VPLSServiceLines\r\n"+str(VPLSServiceLines))
        # if debug: print("debug: Printing OSPFv2NeighborsLines\r\n"+str(OSPFv2NeighborsLines))
        # if debug: print("debug: Printing OSPFv3NeighborsLines\r\n"+str(OSPFv3NeighborsLines))
        # if debug: print("debug: Printing BGPNeighborsLines\r\n"+str(BGPNeighborsLines))

        CLISyntax = ""                  # Stores CLI syntax for correct parsing and matching
        SWDescr = ""                    # Stores SW description line from show|display version
        SysAddr = ""                    # Stores system/loopback0 address

        # print("1111: len(versionLines) = "+str(len(versionLines)))
        # print(versionLines)
        if len(versionLines) == 0:
            if defaultCLISyntax != "":
                print("Could not determine parsing syntax in file "+showFilePath+", using default one specified")
                CLISyntax = defaultCLISyntax
                # if len(configLines) == 0:
                configLines = configLines2
            else:
                input("Could not determine parsing syntax in file "+showFilePath+" and no default syntax specified, press any key to skip to the next file\r\n")
                continue
        else:
            for obj2 in versionLines:       # Determine configuration syntax
                searchExpression = r'.*Cisco IOS XR'
                if re.match(searchExpression,obj2):
                    SWDescr = obj2
                    CLISyntax = "IOS-XR"
                    break
                searchExpression = r'.*Cisco IOS(-| XE)? '
                if re.match(searchExpression,obj2):
                    SWDescr = obj2
                    CLISyntax = "IOS"
                    break
                searchExpression = r'.*VRP \(R\) software'
                if re.match(searchExpression,obj2):
                    SWDescr = obj2
                    CLISyntax = "VRP"
                    break
                searchExpression = r'.*TiMOS-'
                if re.match(searchExpression,obj2):
                    SWDescr = obj2
                    CLISyntax = "SR-OS"
                    break

            SWDescr = SWDescr.replace("#","")
            SWDescr = SWDescr.replace("!","")
            SWDescr = SWDescr.rstrip()
            SWDescr = SWDescr.lstrip()
            print("Found following software description: "+SWDescr)

            if CLISyntax == "":
                input("Could not determine parsing syntax in file "+showFilePath+" and no default syntax specified, press any key to skip to the next file\r\n")
                continue

        print("Using following parsing syntax for this node: "+CLISyntax)

        if len(configLines) == 0:
            input("Could not find router's configuration in file "+showFilePath+", press any key to skip to the next file\r\n")
            continue
        else:
            configLinesToParser = []
            for line in configLines:                            # Cleaning configLines before parsing
                if not re.match(r'^ *[#!]',line):                # Remove all comments
                    if not re.match(r'echo "',line):            # Remove SR-OS echo lines
                        if not re.match(r'^$',line):            # Remove empty lines
                            if CLISyntax == "SR-OS":
                                line = line.replace("    "," ")     # Replace SR-OS indentation to single spaces
                            configLinesToParser.append(line)


            # if debug: print("debug: Printing configLinesToParser\r\n"+str(configLinesToParser))

            cfg = CiscoConfParse(configLinesToParser)    # Parse configLines using CiscoConfParse library
            #if debug: print("debug: cfg: "+str(cfg))

            if ((CLIDelimiter == "") or (re.match(r"^[#>]$",CLIDelimiter))):
                Hostname = os.path.split(showFilePath)[1]
            else:
                Hostname = CLIDelimiter

            if debug: print("debug: Setting Hostname to: "+Hostname)


            # Find Hostname
            # Syntax: Cisco IOS/IOS-XE/IOS-XR
            if ((CLISyntax == "IOS") or (CLISyntax == "IOS-XR")):
                for obj1 in cfg.find_objects("^hostname"):       # Find node's Hostname from config
                    if debug: print("debug: obj1: "+str(obj1))
                    Hostname = obj1.text.split(" ")[1]
                    if debug: print("debug: Found Hostname in configuration file and updated to: "+Hostname)
                    break
            # Syntax: Huawei VRP
            if (CLISyntax == "VRP"):
                for obj1 in cfg.find_objects("^sysname"):       # Find node's Hostname from config
                    if debug: print("debug: obj1: "+str(obj1))
                    Hostname = obj1.text.split(" ")[1]
                    if debug: print("debug: Found Hostname in configuration file and updated to: "+Hostname)
                    break
            # Syntax: ALU/Nokia SR-OS
            if (CLISyntax == "SR-OS"):
                for obj1 in cfg.find_objects(" *name"):       # Find node's Hostname from config
                    print(obj1)
                    if debug: print("debug: obj1: "+str(obj1))
                    Hostname = obj1.text.split(" \"")[1].split("\"")[0]
                    if debug: print("debug: Found Hostname in configuration file and updated to: "+Hostname)
                    break

            # Find system/loopback0 address
            # Syntax: Cisco IOS-XR
            if (CLISyntax == "IOS-XR"):
                for obj1 in cfg.find_objects("^interface Loopback0"):       # Find node's system/loopback0 address from config
                    if debug: print("debug: obj1: "+str(obj1))
                    for obj2 in obj1.re_search_children("ipv4 address "):    #Find all IPv4 addresses associated with current interface (IOS-XR syntax)
                        if debug: print("debug: obj2: "+str(obj2))
                        if re.search(r"/",obj2.text):
                            SysAddr = obj2.text.split("ipv4 address ")[1].split("/")[0]
                        else:
                            SysAddr = obj2.text.split("ipv4 address ")[1].split(" ")[0]
                        if debug: print("debug: SysAddr: "+str(SysAddr))
                        break
                    break
            # Syntax: Cisco IOS/IOS-XE
            if (CLISyntax == "IOS"):
                for obj1 in cfg.find_objects("^interface Loopback0"):       # Find node's system/loopback0 address from config
                    if debug: print("debug: obj1: "+str(obj1))
                    for obj2 in obj1.re_search_children("ip address "):    #Find all IPv4 addresses associated with current interface (IOS/IOS-XE syntax)
                        if debug: print("debug: obj2: "+str(obj2))
                        if re.search("/",obj2.text):
                            SysAddr = obj2.text.split("ip address ")[1].split("/")[0]
                        else:
                            SysAddr = obj2.text.split("ip address ")[1].split(" ")[0]
                        if debug: print("debug: SysAddr: "+str(SysAddr))
                        break
                    break
            # Syntax: Huawei VRP
            if (CLISyntax == "VRP"):
                for obj1 in cfg.find_objects("^interface LoopBack0"):       # Find node's system/loopback0 address from config
                    if debug: print("debug: obj1: "+str(obj1))
                    for obj2 in obj1.re_search_children("ip address "):    #Find all IPv4 addresses associated with current interface (VRP syntax)
                        if debug: print("debug: obj2: "+str(obj2))
                        SysAddr = obj2.text.split("address ")[1].split(" ")[0]
                        if debug: print("debug: SysAddr: "+str(SysAddr))
                        break
                    break
            # Syntax: ALU/Nokia SR-OS
            if (CLISyntax == "SR-OS"):
                for obj1 in cfg.find_objects("^ *interface \"system\""):       # Find node's system/loopback0 address from config
                    if debug: print("debug: obj1: "+str(obj1))
                    for obj2 in obj1.re_search_children("address "):    #Find all IPv4 addresses associated with current interface (SR-OS syntax)
                        if debug: print("debug: obj2: "+str(obj2))
                        SysAddr = obj2.text.split("address ")[1].split("/")[0]
                        if debug: print("debug: SysAddr: "+str(SysAddr))
                        break
                    break

            if genClean == 1:
                # Generating clean input file for node
                if os.path.isfile("./clean_input") == True:
                    print("Could not create directory ./clean_input")
                else:
                    if os.path.isdir("./clean_input") == False:
                        os.mkdir("./clean_input")

                    cleanInputFileName = str(Hostname +"_"+ SysAddr +"_"+ time.strftime("%Y%m%d_%H%M%S")+".txt")

                    with open("./clean_input/"+cleanInputFileName, 'w') as cleanInputFile:
                        cleanInputFile.write("\n".join(str(item) for item in versionLines))
                        cleanInputFile.write("\n".join(str(item) for item in configLines))
                        cleanInputFile.write("\n".join(str(item) for item in PHYInterfacesLines))
                        cleanInputFile.write("\n".join(str(item) for item in IPInterfacesLines))
                        cleanInputFile.write("\n".join(str(item) for item in MPLSInterfacesLines))
                        cleanInputFile.write("\n".join(str(item) for item in CDPNeighborsLines))
                        cleanInputFile.write("\n".join(str(item) for item in LLDPNeighborsLines))
                        cleanInputFile.write("\n".join(str(item) for item in BFDNeighborsLines))
                        cleanInputFile.write("\n".join(str(item) for item in OSPFv2NeighborsLines))
                        cleanInputFile.write("\n".join(str(item) for item in OSPFv2LSDBLines ))
                        cleanInputFile.write("\n".join(str(item) for item in OSPFv3NeighborsLines))
                        cleanInputFile.write("\n".join(str(item) for item in OSPFv3LSDBLines ))
                        cleanInputFile.write("\n".join(str(item) for item in ISISNeighborsLines))
                        cleanInputFile.write("\n".join(str(item) for item in ISISLSDBLines ))
                        cleanInputFile.write("\n".join(str(item) for item in LDPNeighborsLines))
                        cleanInputFile.write("\n".join(str(item) for item in RSVPNeighborsLines))
                        cleanInputFile.write("\n".join(str(item) for item in BGPNeighborsLines))
                        cleanInputFile.write("\n".join(str(item) for item in L3VPNServiceLines))
                        cleanInputFile.write("\n".join(str(item) for item in L2VPNServiceLines))
                        cleanInputFile.write("\n".join(str(item) for item in VPLSServiceLines))
                    cleanInputFile.close()

                    if debug:
                        cleanInputDebugFileName = str(Hostname +"_"+ SysAddr +"_debug_config_"+ time.strftime("%Y%m%d_%H%M%S")+".txt")
                        with open("./clean_input/"+cleanInputDebugFileName, 'w') as cleanInputDebugFileName:
                            cleanInputDebugFileName.write("\n".join(str(item) for item in configLinesToParser))
                        cleanInputDebugFileName.close()


                    if debug: input("Generated a clean input file "+cleanInputFileName+" for the node. Press any key proceed.\r\n")

#####################################################################################################################################################
################################################                  Creating DB structure                  ############################################
#####################################################################################################################################################
            # Creating Nodes table
            DBQuery="""CREATE TABLE IF NOT EXISTS Nodes (\n"""
            for value1 in NodesDict:
                DBQuery = DBQuery + "\t\t" + str(value1) + " " + str(NodesDict[value1][1]) + "\n"
            DBQuery = DBQuery + "\t\t, PRIMARY KEY(NodeID)\n"
            DBQuery = DBQuery + "\t\t)\n"
            if debugSQL: print("debug: DBQuery: "+str(DBQuery))
            outputCursor.execute(DBQuery)
            outputDB.commit()

            # Creating historical Interfaces table
            DBQuery="""CREATE TABLE IF NOT EXISTS Interfaces"""+str(SyntaxDict["Hist"])+""" (\n"""
            for value2 in InterfacesDict:
                DBQuery = DBQuery + "\t\t" + str(value2) + " " + str(InterfacesDict[value2][1]) + "\n"
            DBQuery = DBQuery + "\t\t)\n"
            if debugSQL: print("debug: DBQuery: "+str(DBQuery))
            outputCursor.execute(DBQuery)
            outputDB.commit()

            # Creating historical Peering table
            DBQuery="""CREATE TABLE IF NOT EXISTS Peering"""+str(SyntaxDict["Hist"])+""" (\n"""
            for value2 in PeeringDict:
                DBQuery = DBQuery + "\t\t" + str(value2) + " " + str(PeeringDict[value2][1]) + "\n"
            DBQuery = DBQuery + "\t\t)\n"
            if debugSQL: print("debug: DBQuery: "+str(DBQuery))
            outputCursor.execute(DBQuery)
            outputDB.commit()

            # Creating set of tables for each CLI syntax recognized by script
            for value1 in SyntaxDict:

                if value1 == "Hist": continue

                # Creating multiple Interfaces tables
                DBQuery="""CREATE TABLE IF NOT EXISTS Interfaces"""+str(SyntaxDict[value1])+""" (\n"""
                for value2 in InterfacesDict:
                    DBQuery = DBQuery + "\t\t" + str(value2) + " " + str(InterfacesDict[value2][1]) + "\n"
                DBQuery = DBQuery + "\t\t, PRIMARY KEY(IfID)\n"
                DBQuery = DBQuery + "\t\t)\n"
                if debugSQL: print("debug: DBQuery: "+str(DBQuery))
                outputCursor.execute(DBQuery)
                outputDB.commit()

                # Creating multiple Peering tables
                DBQuery="""CREATE TABLE IF NOT EXISTS Peering"""+str(SyntaxDict[value1])+""" (\n"""
                for value2 in PeeringDict:
                    DBQuery = DBQuery + "\t\t" + str(value2) + " " + str(PeeringDict[value2][1]) + "\n"
                DBQuery = DBQuery + "\t\t, PRIMARY KEY(PeeringID)\n"
                DBQuery = DBQuery + "\t\t)\n"
                if debugSQL: print("debug: DBQuery: "+str(DBQuery))
                outputCursor.execute(DBQuery)
                outputDB.commit()

                # Creating multiple Routing tables - TBD


            # Checking if the node already exists
            DBQuery="""SELECT *
                        FROM Nodes
                        WHERE Hostname = '"""+str(Hostname)+"""' AND CLISyntax = '"""+str(CLISyntax)+"""'
                        ORDER BY LastUpdatedTime DESC
                        """
            if debugSQL: print("debug: DBQuery: "+str(DBQuery))
            outputCursor.execute(DBQuery)
            DBResponse=outputCursor.fetchone()
            if debugSQL: print("debug: DBResponse: "+str(DBResponse))

            if DBResponse is None:
                NodeID = str(uuid.uuid4())
            else:
                NodeID = DBResponse[NodesDict["NodeID"][0]]

            if DBResponse is None:
                DBQuery="""INSERT INTO Nodes (
                            NodeID,
                            Hostname,
                            CLISyntax,
                            SysAddr,
                            SWDescr,
                            SourceFile,
                            LastUpdatedTime,
                            LastUpdatedBy
                            )
                            VALUES
                            (
                            '"""+str(NodeID)+"""',
                            '"""+str(Hostname)+"""',
                            '"""+str(CLISyntax)+"""',
                            '"""+str(SysAddr)+"""',
                            '"""+str(SWDescr)+"""',
                            '"""+str(os.path.split(showFilePath)[1])+"""',
                            '"""+str(datetime.datetime.today())+"""',
                            '"""+str(getpass.getuser())+"""'
                            )"""
                if debugSQL: print("debug: DBQuery: "+str(DBQuery))
                if not DBUpdateDisable: outputCursor.execute(DBQuery)
                outputDB.commit()
            else:
                if DBResponse[NodesDict["SysAddr"][0]] != SysAddr:
                    print("Node system address changed to "+SysAddr+" - updating.")
                    DBQuery="""UPDATE Nodes
                                SET
                                    SysAddr = '"""+str(SysAddr)+"""',
                                    LastUpdatedTime = '"""+str(datetime.datetime.today())+"""',
                                    LastUpdatedBy = '"""+str(getpass.getuser())+"""'
                                WHERE
                                    NodeID = '"""+NodeID+"""'
                                    """
                    if debugSQL: print("debug: DBQuery: "+str(DBQuery))
                    if not DBUpdateDisable: outputCursor.execute(DBQuery)
                if DBResponse[NodesDict["SourceFile"][0]] != str(os.path.split(showFilePath)[1]):
                    print("Node source file changed to "+str(os.path.split(showFilePath)[1])+" - updating.")
                    DBQuery="""UPDATE Nodes
                                SET
                                    SourceFile = '"""+str(os.path.split(showFilePath)[1])+"""',
                                    LastUpdatedTime = '"""+str(datetime.datetime.today())+"""',
                                    LastUpdatedBy = '"""+str(getpass.getuser())+"""'
                                WHERE
                                    NodeID = '"""+NodeID+"""'
                                    """
                    if debugSQL: print("debug: DBQuery: "+str(DBQuery))
                    if not DBUpdateDisable: outputCursor.execute(DBQuery)
                if DBResponse[NodesDict["SWDescr"][0]] != SWDescr:
                    print("Node SW description changed to "+SWDescr+" - updating.")
                    DBQuery="""UPDATE Nodes
                                SET
                                    SWDescr = '"""+str(SWDescr)+"""',
                                    LastUpdatedTime = '"""+str(datetime.datetime.today())+"""',
                                    LastUpdatedBy = '"""+str(getpass.getuser())+"""'
                                WHERE
                                    NodeID = '"""+NodeID+"""'
                                    """
                    if debugSQL: print("debug: DBQuery: "+str(DBQuery))
                    if not DBUpdateDisable: outputCursor.execute(DBQuery)
                outputDB.commit()
            if debug: input("Node updated in the database. Press any key proceed.\r\n")


#####################################################################################################################################################
###################################################           Find all interfaces in config file           ##########################################
#####################################################################################################################################################

            IfNumber = 0
            IfNew = 0
            IfUpdated = 0
            IfKept = 0
            IfDeleted = 0
            IDMatched = []
            InterfacesParseAll = []

#####################################################################################################################################################
###################################################                  Cisco IOS-XR parsing                  ##########################################
#####################################################################################################################################################
            # Syntax: Cisco IOS-XR
            if (CLISyntax == "IOS-XR"):
                if debug: print("debug: Using IOS-XR syntax to parse file")
                # Find node's interfaces from config
                for obj1 in cfg.find_objects(r"^interface"):
                    if re.search(" preconfigure ",obj1.text): continue
                    duplicate = []
                    for obj2 in cfg.find_objects(r"^interface"):
                        if obj1.text.split("interface ")[1].split(" ")[0] == obj2.text.split("interface ")[1].split(" ")[0]:
                            duplicate.append(str(obj2))

                    if len(duplicate) > 1:
                        print("File "+str(os.path.split(inputPath)[1])+" contains duplicate interface lines: "+str(duplicate)+", skipping this file")
                        nextFile = 1
                        break

                    IfNumber = IfNumber + 1
                    InterfacesParse = [""] * len(InterfacesDict)
                    if debug: print("debug: obj1: "+str(obj1))

                    InterfacesParse[InterfacesDict["NodeID"][0]] = NodeID
                    InterfacesParse[InterfacesDict["Hostname"][0]] = Hostname
                    InterfacesParse[InterfacesDict["CLISyntax"][0]] = CLISyntax
                    InterfacesParse[InterfacesDict["IfNumber"][0]] = str(IfNumber).zfill(4)
                    InterfacesParse[InterfacesDict["IfName"][0]] = obj1.text.split("interface ")[1].split(" ")[0]

                    # Check if interface is a subinterface of another one
                    if re.search(r'\.',InterfacesParse[InterfacesDict["IfName"][0]]):
                        InterfacesParse[InterfacesDict["ParentIfName"][0]] = InterfacesParse[InterfacesDict["IfName"][0]].split(".")[0]
                        InterfacesParse[InterfacesDict["PortName"][0]] = InterfacesParse[InterfacesDict["IfName"][0]].split(".")[0]
                        InterfacesParse[InterfacesDict["IfType"][0]] = "SubIf"
                    else:
                        # Check if interface is physical port
                        if re.search(r'([Gg]ig[Ee]|[Ee]thernet)',InterfacesParse[InterfacesDict["IfName"][0]]):
                            InterfacesParse[InterfacesDict["PortName"][0]] = InterfacesParse[InterfacesDict["IfName"][0]]
                            InterfacesParse[InterfacesDict["IfType"][0]] = "Port"
                            if re.search(r'[Hh]undred[Gg]ig(abit)?E',InterfacesParse[InterfacesDict["IfName"][0]]):
                                InterfacesParse[InterfacesDict["PortType"][0]] = "100GE"
                            else:
                                if re.search(r'[Tt]en[Gg]ig(abit)?E',InterfacesParse[InterfacesDict["IfName"][0]]):
                                    InterfacesParse[InterfacesDict["PortType"][0]] = "10GE"
                                else:
                                    if re.search(r'[Gg]igabit',InterfacesParse[InterfacesDict["IfName"][0]]):
                                        InterfacesParse[InterfacesDict["PortType"][0]] = "1GE"
                                    else:
                                        if re.search(r'[Ff]ast',InterfacesParse[InterfacesDict["IfName"][0]]):
                                            InterfacesParse[InterfacesDict["PortType"][0]] = "100ME"
                                        else:
                                            InterfacesParse[InterfacesDict["PortType"][0]] = ""

                    # Check if interface is a loopback
                    if re.search(r"[Ll]oop[Bb]ack",InterfacesParse[InterfacesDict["IfName"][0]]):
                        InterfacesParse[InterfacesDict["IfType"][0]] = "Loopback"

                    # Check if interface is a bundle
                    if re.search(r'[Bb]undle-[Ee]ther',InterfacesParse[InterfacesDict["IfName"][0]]):
                        InterfacesParse[InterfacesDict["PortName"][0]] = InterfacesParse[InterfacesDict["IfName"][0]]
                        InterfacesParse[InterfacesDict["LAGID"][0]] = str(InterfacesParse[InterfacesDict["IfName"][0]].split("ther")[1].split(".")[0])
                        InterfacesParse[InterfacesDict["IfType"][0]] = "LAG"

                    # Check if interface is l2tpansport interface
                    if re.search(r'l2transport',obj1.text.split("interface ")[1]):
                        InterfacesParse[InterfacesDict["IfName"][0]] = InterfacesParse[InterfacesDict["IfName"][0]].split(" ")[0]
                        InterfacesParse[InterfacesDict["ServiceType"][0]] = "L2VPN"
                        if InterfacesParse[InterfacesDict["IfType"][0]] != "":
                            InterfacesParse[InterfacesDict["IfType"][0]] = InterfacesParse[InterfacesDict["IfType"][0]] + "|"

                        InterfacesParse[InterfacesDict["IfType"][0]] = InterfacesParse[InterfacesDict["IfType"][0]] + "L2VPN"
                        InterfacesParse[InterfacesDict["IfMode"][0]] = "Access"

                        for obj200 in cfg.find_objects(r"^l2vpn"):
                            for obj201 in obj200.re_search_children("bridge "):
                                for obj202 in obj201.re_search_children("bridge-domain "):
                                    searchExpression = InterfacesParse[InterfacesDict["IfName"][0]] + r"$"
                                    for obj203 in obj202.re_search_children(searchExpression):
                                        InterfacesParse[InterfacesDict["ServiceName"][0]] = obj202.text.split("bridge-domain ")[1].split()[0]
                                        for obj204 in obj202.re_search_children("neighbor "):
                                            InterfacesParse[InterfacesDict["ServiceSDP"][0]] = obj204.text.split("neighbor ")[1].lstrip().rstrip().replace(" pw-id ",":")


                    # Find description associated with current interface
                    for obj2 in obj1.re_search_children("description "):
                        InterfacesParse[InterfacesDict["IfDescr"][0]] = str(obj2.text.split("description ")[1].replace("\"",""))
                        break

                    # Find encapsulation associated with current interface
                    for obj2 in obj1.re_search_children(r"^ *encapsulation "):
                        if InterfacesParse[InterfacesDict["VLAN"][0]] != "": InterfacesParse[InterfacesDict["VLAN"][0]] = InterfacesParse[InterfacesDict["VLAN"][0]] + "|"
                        if re.search("second-dot1q ",obj2.text):
                            if ((InterfacesParse[InterfacesDict["Encap"][0]] == "dot1q") or (InterfacesParse[InterfacesDict["Encap"][0]] == "")):
                                InterfacesParse[InterfacesDict["Encap"][0]] = "qinq"
                            InterfacesParse[InterfacesDict["VLAN"][0]] = InterfacesParse[InterfacesDict["VLAN"][0]] + (str(obj2.text.split(" dot1q ")[1].split(" second-dot1q ")[0].lstrip().rstrip().replace(" , ","|"))) + "." + str(obj2.text.split(" second-dot1q ")[1].lstrip().rstrip().replace(" , ","|"))
                        else:
                            if re.search("dot1q ",obj2.text):
                                if InterfacesParse[InterfacesDict["Encap"][0]] == "":
                                    InterfacesParse[InterfacesDict["Encap"][0]] = "dot1q"
                                InterfacesParse[InterfacesDict["VLAN"][0]] = InterfacesParse[InterfacesDict["VLAN"][0]] + str(obj2.text.split(" dot1q ")[1].lstrip().rstrip().replace(" , ","|"))
                            else:
                                if re.search("untagged",obj2.text):
                                    if InterfacesParse[InterfacesDict["Encap"][0]] == "":
                                        InterfacesParse[InterfacesDict["Encap"][0]] = "null"
                                    InterfacesParse[InterfacesDict["VLAN"][0]] = InterfacesParse[InterfacesDict["VLAN"][0]] + "0"

                    # If encapsulation was not specified set it to default
                    if (((InterfacesParse[InterfacesDict["IfType"][0]] == "Port") or (InterfacesParse[InterfacesDict["IfType"][0]] == "LAG")) and len(obj1.re_search_children("service instance ")) == 0):
                        if InterfacesParse[InterfacesDict["Encap"][0]] == "":
                            InterfacesParse[InterfacesDict["Encap"][0]] = "null"
                        if InterfacesParse[InterfacesDict["VLAN"][0]] == "":
                            InterfacesParse[InterfacesDict["VLAN"][0]] = "0"

                    # Find LAG associated with current interface
                    for obj2 in obj1.re_search_children("bundle id "):
                        InterfacesParse[InterfacesDict["LAGID"][0]] = str(obj2.text.split("bundle id ")[1].split(" ")[0])
                        if re.search("active",obj2.text):
                            InterfacesParse[InterfacesDict["LAGMode"][0]] = "Active"
                        else:
                            if re.search("passive",obj2.text):
                                InterfacesParse[InterfacesDict["LAGMode"][0]] = "Passive"

                        for obj3 in cfg.find_objects(r"^interface Bundle-Ether"+str(InterfacesParse[InterfacesDict["LAGID"][0]])):
                            InterfacesParse[InterfacesDict["ParentIfName"][0]] = obj3.text.split("interface ")[1]
                            break
                        break

                    # Find subinterfaces and respective VLANs associated with current interface
                    for obj40 in cfg.find_objects(r"^interface"):
                        searchExpression = r"^ *interface " + InterfacesParse[InterfacesDict["IfName"][0]] + r"[\. $]"
                        if re.match(searchExpression,obj40.text):
                            # print("FOUND")
                            for obj3 in obj40.re_search_children(r"^ *encapsulation "):
                                if InterfacesParse[InterfacesDict["VLAN"][0]] != "": InterfacesParse[InterfacesDict["VLAN"][0]] = InterfacesParse[InterfacesDict["VLAN"][0]] + "|"
                                if re.search("second-dot1q ",obj3.text):
                                    if ((InterfacesParse[InterfacesDict["Encap"][0]] == "dot1q") or (InterfacesParse[InterfacesDict["Encap"][0]] == "")):
                                        InterfacesParse[InterfacesDict["Encap"][0]] = "qinq"
                                    InterfacesParse[InterfacesDict["VLAN"][0]] = InterfacesParse[InterfacesDict["VLAN"][0]] + (str(obj3.text.split(" dot1q ")[1].split(" second-dot1q ")[0].lstrip().rstrip().replace(" , ","|"))) + "." + str(obj3.text.split(" second-dot1q ")[1].lstrip().rstrip().replace(" , ","|"))
                                else:
                                    if re.search("dot1q ",obj3.text):
                                        if InterfacesParse[InterfacesDict["Encap"][0]] == "":
                                            InterfacesParse[InterfacesDict["Encap"][0]] = "dot1q"
                                        InterfacesParse[InterfacesDict["VLAN"][0]] = InterfacesParse[InterfacesDict["VLAN"][0]] + str(obj3.text.split(" dot1q ")[1].lstrip().rstrip().replace(" , ","|"))
                                    else:
                                        if re.search("untagged",obj3.text):
                                            if InterfacesParse[InterfacesDict["Encap"][0]] == "":
                                                InterfacesParse[InterfacesDict["Encap"][0]] = "null"
                                            InterfacesParse[InterfacesDict["VLAN"][0]] = InterfacesParse[InterfacesDict["VLAN"][0]] + "0"

                    # Find admin state associated with current interface
                    for obj2 in obj1.re_search_children(r" +shutdown"):
                        if str(obj2.text.split(" ")[1]):
                            InterfacesParse[InterfacesDict["StateAdm"][0]] = "Dis"
                        else:
                            InterfacesParse[InterfacesDict["StateAdm"][0]] = "En"
                    if InterfacesParse[InterfacesDict["StateAdm"][0]] == "":
                        InterfacesParse[InterfacesDict["StateAdm"][0]] = "En"

                    # Find L3VPN service associated with current interface
                    for obj2 in obj1.re_search_children("vrf "):
                        InterfacesParse[InterfacesDict["ServiceName"][0]] = str(obj2.text.split("vrf ")[1])
                        InterfacesParse[InterfacesDict["ServiceType"][0]] = "L3VPN"

                    # Find L2 MTU associated with current interface
                    for obj2 in obj1.re_search_children(r"^ +mtu"):
                        InterfacesParse[InterfacesDict["L2MTU"][0]]  = str(obj2.text.split("mtu ")[1])
                        break

                    # Find L3 MTU associated with current interface
                    for obj2 in obj1.re_search_children(r"^ +ipv4 mtu"):
                        InterfacesParse[InterfacesDict["L3MTU"][0]]  = str(obj2.text.split("mtu ")[1])
                        break

                    # Find all IPv4 addresses associated with current interface
                    for obj2 in obj1.re_search_children("ipv4 address "):
                        rawInput = obj2.text.split("ipv4 address ")[1].lstrip().rstrip()
                        rawInput = rawInput.replace(" ","/")
                        ipadd = ipaddress.ip_interface(str(rawInput))
                        if InterfacesParse[InterfacesDict["IPV4Addr"][0]] == "":
                            InterfacesParse[InterfacesDict["IPV4Addr"][0]] = str(ipadd)
                        else:
                            InterfacesParse[InterfacesDict["IPV4Addr"][0]] = InterfacesParse[InterfacesDict["IPV4Addr"][0]] + "|" + str(ipadd)
                        if InterfacesParse[InterfacesDict["IPV4Subnet"][0]] == "":
                            InterfacesParse[InterfacesDict["IPV4Subnet"][0]] = str(ipadd.network)
                        else:
                            InterfacesParse[InterfacesDict["IPV4Subnet"][0]] = InterfacesParse[InterfacesDict["IPV4Subnet"][0]] + "|"+ str(ipadd.network)

                    # Find all IPv6 addresses associated with current interface
                    for obj2 in obj1.re_search_children("ipv6 address "):
                        rawInput = obj2.text.split("ipv6 address ")[1].lstrip().rstrip()
                        ipadd = ipaddress.ip_interface(str(line))
                        if InterfacesParse[InterfacesDict["IPV6Addr"][0]] == "":
                            InterfacesParse[InterfacesDict["IPV6Addr"][0]] = str(ipadd)
                        else:
                            InterfacesParse[InterfacesDict["IPV6Addr"][0]] = InterfacesParse[InterfacesDict["IPV6Addr"][0]] + "|" + str(ipadd)
                        if InterfacesParse[InterfacesDict["IPV6Subnet"][0]] == "":
                            InterfacesParse[InterfacesDict["IPV6Subnet"][0]] = str(ipadd.network)
                        else:
                            InterfacesParse[InterfacesDict["IPV6Subnet"][0]] = InterfacesParse[InterfacesDict["IPV6Subnet"][0]] + "|" + str(ipadd.network)

                    # Check if interface is a L3 interface
                    if ((InterfacesParse[InterfacesDict["IPV4Addr"][0]] != "") or (InterfacesParse[InterfacesDict["IPV6Addr"][0]] != "")):
                        if InterfacesParse[InterfacesDict["PortBinding"][0]] == "":
                            if InterfacesParse[InterfacesDict["VLAN"][0]] == "":
                                InterfacesParse[InterfacesDict["PortBinding"][0]] = InterfacesParse[InterfacesDict["PortName"][0]]
                            else:
                                InterfacesParse[InterfacesDict["PortBinding"][0]] = InterfacesParse[InterfacesDict["PortName"][0]] + ":" + InterfacesParse[InterfacesDict["VLAN"][0]]
                        # Mark interface as Network/Hybrid if it has any IPv4/v6 addresses assigned and no VRF assigned and create port binding for it
                        if (InterfacesParse[InterfacesDict["ServiceName"][0]] == ""):
                            if InterfacesParse[InterfacesDict["IfType"][0]] == "":
                                InterfacesParse[InterfacesDict["IfType"][0]] = "L3"
                            else:
                                InterfacesParse[InterfacesDict["IfType"][0]] = InterfacesParse[InterfacesDict["IfType"][0]] + "|L3"
                            InterfacesParse[InterfacesDict["IfMode"][0]] = "Network"
                        # Mark interface as Access if it has any IPv4/v6 addresses and VRF assigned and create port binding for it
                        else:
                            if InterfacesParse[InterfacesDict["IfType"][0]] == "":
                                InterfacesParse[InterfacesDict["IfType"][0]] = "L3VPN"
                            else:
                                InterfacesParse[InterfacesDict["IfType"][0]] = InterfacesParse[InterfacesDict["IfType"][0]] + "|L3VPN"
                            InterfacesParse[InterfacesDict["IfMode"][0]] = "Access"

                    # Check if interface has any port binding assigned
                    if ((InterfacesParse[InterfacesDict["ServiceName"][0]] != "") or (InterfacesParse[InterfacesDict["ServiceID"][0]] != "")):
                        if InterfacesParse[InterfacesDict["PortBinding"][0]] == "":
                            if InterfacesParse[InterfacesDict["VLAN"][0]] == "":
                                InterfacesParse[InterfacesDict["PortBinding"][0]] = InterfacesParse[InterfacesDict["PortName"][0]]
                            else:
                                for vlan in InterfacesParse[InterfacesDict["VLAN"][0]].split("|"):
                                    if InterfacesParse[InterfacesDict["PortBinding"][0]] != "":
                                        InterfacesParse[InterfacesDict["PortBinding"][0]] = InterfacesParse[InterfacesDict["PortBinding"][0]] + "|"
                                    InterfacesParse[InterfacesDict["PortBinding"][0]] = InterfacesParse[InterfacesDict["PortBinding"][0]] + InterfacesParse[InterfacesDict["PortName"][0]] + ":" + vlan


                    # Find all OSPF processes and areas where this interface is participating
                    ospfList = []
                    # ospfLine = []

                    bfdList = []
                    # bfdLine = []

                    # Find all OSPF processes associated with interface
                    for obj10 in cfg.find_objects(r"router ospf"):
                        ospfPID = ""
                        ospfRID = ""
                        ospfVRFList = []
                        ospfLine = []

                        ospfBFDMinTmr = ""
                        ospfBFDMultTmr = ""
                        bfdLine = []

                        ospfVRFList.append(obj10)
                        ospfPID = str(obj10.text.split("ospf ")[1].split(" ")[0])
                        ospfLine.append(ospfPID)

                        bfdLine.append("ospf")
                        bfdLine.append(ospfPID)

                        # Create a list of base entities (GRT + all VRFs) where areas can be located
                        for obj70 in obj10.re_search_children(r"vrf"):
                            ospfVRFList.append(obj70)

                        # Look through all OSPF areas in and outside VRFs
                        for ospfVRF in ospfVRFList:

                            # Find all OSPF global parameters

                            for obj101 in ospfVRF.re_search_children("router-id"):
                                ospfRID = obj101.text.split("router-id ")[1].split()[0].lstrip().rstrip()

                            for obj101 in ospfVRF.re_search_children("bfd fast-detect"):
                                if re.match(r"^ *bfd fast-detect *$",obj101.text):
                                    ospfBFDState = "En"
                                if re.match(r"^ *no bfd fast-detect *$",obj101.text):
                                    ospfBFDState = "Dis"

                            for obj101 in ospfVRF.re_search_children("bfd minimum-interval"):
                                ospfBFDMinTmr = obj101.text.lstrip().rstrip().split("bfd minimum-interval ")[1]

                            for obj101 in ospfVRF.re_search_children("bfd multiplier"):
                                ospfBFDMultTmr = obj101.text.lstrip().rstrip().split("bfd multiplier ")[1]


                            # First we will look for the area where interface is primary
                            ospfIfType1 = ""
                            ospfIfType2 = "Bcast"
                            ospfIfMode = "Act"
                            ospfBFDState = "Dis"
                            ospfPriority = ""
                            ospfMetric = ""
                            ospfHello = ""
                            ospfDead = ""
                            ospfRetransmit = ""
                            ospfAuth = ""
                            ospfIfState = "En"

                            area = ""
                            for obj11 in ospfVRF.re_search_children(r"area "):

                                area = int(obj11.text.split("area ")[1])
                                area = ipaddress.ip_address(area)

                                for obj101 in obj11.re_search_children("bfd fast-detect"):
                                    if re.match(r"^ *bfd fast-detect *$",obj101.text):
                                        ospfBFDState = "En"
                                    if re.match(r"^ *no bfd fast-detect *$",obj101.text):
                                        ospfBFDState = "Dis"

                                for obj101 in obj11.re_search_children("bfd minimum-interval"):
                                    ospfBFDMinTmr = obj101.text.lstrip().rstrip().split("bfd minimum-interval ")[1]

                                for obj101 in obj11.re_search_children("bfd multiplier"):
                                    ospfBFDMultTmr = obj101.text.lstrip().rstrip().split("bfd multiplier ")[1]

                                # print("Looking in PID:" + ospfPID + " VRF:" + str(VRF) + " Area:" + str(int(area)))

                                # Find current interface configured as primary within an area
                                searchExpression = InterfacesParse[InterfacesDict["IfName"][0]] + r"$"
                                # print(len(obj11.re_search_children(searchExpression)))
                                # print("Number of interfaces in area " + str(int(area)) + ":" + str(len(obj11.re_search_children(r"interface "))))

                                # if len(obj11.re_search_children(r"interface ")) == 0:
                                    # print(obj11.re_search_children(r".*"))
                                for obj12 in obj11.re_search_children(searchExpression):
                                    # print("Match found in PID:" + ospfPID + " VRF:" + VRF + " Area:" + str(int(area)))

                                    if re.search(r"multi-area-interface",obj12.text):
                                        continue
                                    else:
                                        # Find all OSPF parameters for this primary interface

                                        ospfLine.append(ospfRID)

                                        for obj13 in obj12.re_search_children("network "):
                                            ospfIfType1 = str(obj13.text.split("network ")[1].split(" ")[0].lstrip().rstrip())
                                            ospfIfType2 = ""
                                            if ospfIfType1 == "point-to-point":
                                                ospfIfType2 = "PtP"
                                            else:
                                                if ospfIfType1 == "point-to-multipoint":
                                                    ospfIfType2 = "PtMP"
                                                else:
                                                    ospfIfType2 = ospfIfType1
                                            break
                                        ospfLine.append(ospfIfType2)
                                        for obj13 in obj12.re_search_children("passive"):
                                            if re.match(r"^ *passive enable *$",obj13.text):
                                                ospfIfMode = "Pass"
                                            if re.match(r"^ *no passive enable *$",obj13.text):
                                                ospfIfMode = "Act"
                                            break
                                        ospfLine.append(ospfIfMode)
                                        for obj13 in obj12.re_search_children("bfd fast-detect"):
                                            if re.match(r"^ *bfd fast-detect *$",obj13.text):
                                                ospfBFDState = "En"
                                            if re.match(r"^ *no bfd fast-detect *$",obj13.text):
                                                ospfBFDState = "Dis"
                                            break
                                        if ospfBFDState == "": ospfBFDState = "Dis"

                                        for obj101 in obj12.re_search_children("bfd fast-detect"):
                                            if re.match(r"^ *bfd fast-detect *$",obj101.text):
                                                ospfBFDState = "En"
                                            if re.match(r"^ *no bfd fast-detect *$",obj101.text):
                                                ospfBFDState = "Dis"
                                        ospfLine.append(ospfBFDState)
                                        for obj101 in obj12.re_search_children("bfd minimum-interval"):
                                            ospfBFDMinTmr = obj101.text.lstrip().rstrip().split("bfd minimum-interval ")[1]

                                        for obj101 in obj12.re_search_children("bfd multiplier"):
                                            ospfBFDMultTmr = obj101.text.lstrip().rstrip().split("bfd multiplier ")[1]

                                        bfdLine.append(ospfBFDMinTmr)
                                        bfdLine.append(ospfBFDMultTmr)

                                        for obj13 in obj12.re_search_children("priority "):
                                            ospfPriority = str(obj13.text.split("priority ")[1].split(" ")[0].lstrip().rstrip())
                                            break
                                        ospfLine.append(ospfPriority)
                                        for obj13 in obj12.re_search_children("cost "):
                                            ospfMetric = str(obj13.text.split("cost ")[1].split(" ")[0].lstrip().rstrip())
                                            break
                                        ospfLine.append(ospfMetric)
                                        for obj13 in obj12.re_search_children("hello-interval "):
                                            ospfHello = str(obj13.text.split("hello-interval ")[1].split(" ")[0].lstrip().rstrip())
                                            break
                                        ospfLine.append(ospfHello)
                                        for obj13 in obj12.re_search_children("dead-interval "):
                                            ospfDead = str(obj13.text.split("dead-interval ")[1].split(" ")[0].lstrip().rstrip())
                                            break
                                        ospfLine.append(ospfDead)
                                        for obj13 in obj12.re_search_children("retransmit-interval "):
                                            ospfRetransmit = str(obj13.text.split("retransmit-interval ")[1].split(" ")[0].lstrip().rstrip())
                                            break
                                        ospfLine.append(ospfRetransmit)
                                        for obj13 in obj12.re_search_children("authentication "):
                                            ospfAuth = str(obj13.text.split("authentication ")[1].split(" ")[0].lstrip().rstrip())
                                            break
                                        ospfLine.append(ospfAuth)
                                        for obj13 in obj12.re_search_children("shutdown"):
                                            ospfIfState = "Dis"
                                            break

                                        ospfAreaList = []
                                        ospfAreaList.append([int(area),"*",""])
                                        if ospfIfState == "Dis":
                                            ospfAreaList[0][2] = "(Dis)"
                                        else:
                                            ospfAreaList[0][2] = ""

                                        ospfLine.append(ospfAreaList)

                                        ospfList.append(ospfLine)
                                        bfdList.append(bfdLine)

                                        break

                            # Now we will look for all other areas where interface is secondary

                            area = ""
                            # Look through all OSPF areas
                            for obj11 in obj10.re_search_children(r"area "):
                                area = int(obj11.text.split("area ")[1])
                                area = ipaddress.ip_address(area)

                                ospfLine = []
                                ospfPriority = ""
                                ospfMetric = ""
                                ospfHello = ""
                                ospfDead = ""
                                ospfRetransmit = ""
                                ospfAuth = ""
                                ospfIfState = "En"

                                # Find current interface configured as secondary within an area
                                searchExpression = InterfacesParse[InterfacesDict["IfName"][0]] + r"$"
                                for obj12 in obj11.re_search_children(searchExpression):
                                    if re.search(r"multi-area-interface",obj12.text):
                                        # Find all OSPF parameters for this secondary interface
                                        ospfLine.append(ospfPID)        # Set to same value as on primary configuration
                                        ospfLine.append(ospfRID)        # Set to same value as on primary configuration
                                        ospfLine.append(ospfIfType2)    # Set to same value as on primary configuration
                                        ospfLine.append(ospfIfMode)     # Set to same value as on primary configuration
                                        ospfLine.append(ospfBFDState)   # Set to same value as on primary configuration
                                        for obj13 in obj12.re_search_children("priority "):
                                            ospfPriority = str(obj13.text.split("priority ")[1].split(" ")[0].lstrip().rstrip())
                                            break
                                        ospfLine.append(ospfPriority)
                                        for obj13 in obj12.re_search_children("cost "):
                                            ospfMetric = str(obj13.text.split("cost ")[1].split(" ")[0].lstrip().rstrip())
                                            break
                                        ospfLine.append(ospfMetric)
                                        for obj13 in obj12.re_search_children("hello-interval "):
                                            ospfHello = str(obj13.text.split("hello-interval ")[1].split(" ")[0].lstrip().rstrip())
                                            break
                                        ospfLine.append(ospfHello)
                                        for obj13 in obj12.re_search_children("dead-interval "):
                                            ospfDead = str(obj13.text.split("dead-interval ")[1].split(" ")[0].lstrip().rstrip())
                                            break
                                        ospfLine.append(ospfDead)
                                        for obj13 in obj12.re_search_children("retransmit-interval "):
                                            ospfRetransmit = str(obj13.text.split("retransmit-interval ")[1].split(" ")[0].lstrip().rstrip())
                                            break
                                        ospfLine.append(ospfRetransmit)
                                        for obj13 in obj12.re_search_children("authentication "):
                                            ospfAuth = str(obj13.text.split("authentication ")[1].split(" ")[0].lstrip().rstrip())
                                            break
                                        ospfLine.append(ospfAuth)
                                        for obj13 in obj12.re_search_children("shutdown"):
                                            ospfIfState = "Dis"
                                            break

                                        ospfAreaList = []
                                        ospfAreaList.append([int(area),"",""])
                                        if ospfIfState == "Dis":
                                            ospfAreaList[0][2] = "(Dis)"
                                        else:
                                            ospfAreaList[0][2] = ""
                                        ospfLine.append(ospfAreaList)

                                        lineNumber = 0
                                        match = 0
                                        for ospfLineCheck in ospfList:
                                            if ((ospfLineCheck[4] == ospfBFDState) and (ospfLineCheck[5] == ospfPriority) and (ospfLineCheck[6] == ospfMetric) and (ospfLineCheck[7] == ospfHello)
                                                and (ospfLineCheck[8] == ospfDead) and (ospfLineCheck[9] == ospfRetransmit) and (ospfLineCheck[10] == ospfAuth)):

                                                ospfList[lineNumber][11].extend(ospfAreaList)
                                                match = 1
                                                break

                                            lineNumber = lineNumber + 1

                                        if match == 0:
                                            ospfList.append(ospfLine)


                        # Sort all areas inside the ospfList
                        # print(ospfList)
                        lineNumber = 0
                        for ospfLineCheck in ospfList:
                            # print(ospfList[lineNumber][10])
                            ospfList[lineNumber][11].sort(key=lambda x: x[0])
                            lineNumber = lineNumber + 1

                        # ospfList.sort(key=lambda x: x[10])


                        # Print OSPF data for each OSPF process where this interface is enabled
                        if len(ospfList) > 0:
                            ospfOutputLine = ""
                            for ospfLine in ospfList:
                                # print(ospfLine)
                                if ospfOutputLine != "":
                                    ospfOutputLine = ospfOutputLine + ";"

                                # ospfOutputLine = ospfOutputLine + "pid:"+str(ospfLine[0]) + "|type:"+str(ospfLine[1]) + "|mode:"+str(ospfLine[2]) + "|bfd:"+str(ospfLine[3]) + "|prio:"+str(ospfLine[4]) + "|metr:"+str(ospfLine[5]) + "|hello:"+str(ospfLine[6]) + "|dead:"+str(ospfLine[7]) + "|retr:"+str(ospfLine[8]) + "|auth:"+str(ospfLine[9])

                                ospfOutputLine = ospfOutputLine + "pid:"+str(ospfLine[0])
                                if ospfLine[1] != "": ospfOutputLine = ospfOutputLine + "|rid:"+str(ospfLine[1])
                                ospfOutputLine = ospfOutputLine + "|type:"+str(ospfLine[2]) + "|mode:"+str(ospfLine[3]) + "|bfd:"+str(ospfLine[4])
                                if ospfLine[5] != "": ospfOutputLine = ospfOutputLine + "|prio:" + str(ospfLine[5])
                                if ospfLine[6] != "": ospfOutputLine = ospfOutputLine + "|metr:" + str(ospfLine[6])
                                if ((ospfLine[7] != "") or (ospfLine[8] != "") or (ospfLine[9] != "")):
                                    if ospfLine[7] == "": ospfLine[7] = "def"
                                    if ospfLine[8] == "": ospfLine[8] = "def"
                                    if ospfLine[9] == "": ospfLine[9] = "def"
                                    ospfOutputLine = ospfOutputLine + "|ospf_tmr:" + str(ospfLine[7]) + " " + str(ospfLine[8]) + " " + str(ospfLine[9])
                                if ospfLine[10] != "": ospfOutputLine = ospfOutputLine + "|auth:" + str(ospfLine[10])

                                if len(ospfLine) > 11:
                                    ospfOutputLine = ospfOutputLine + "|areas:"

                                    ospfOutputLine2 = ""
                                    for area in ospfLine[11]:
                                        if ospfOutputLine2 == "":
                                            ospfOutputLine2 = str(area[0]) + str(area[1]) + str(area[2])
                                        else:
                                            ospfOutputLine2 = ospfOutputLine2 + " " + str(area[0]) + str(area[1]) + str(area[2])

                                    ospfOutputLine = ospfOutputLine + ospfOutputLine2

                            if InterfacesParse[InterfacesDict["OSPFv2"][0]] != "": InterfacesParse[InterfacesDict["OSPFv2"][0]] = InterfacesParse[InterfacesDict["OSPFv2"][0]] + ";"
                            InterfacesParse[InterfacesDict["OSPFv2"][0]] = InterfacesParse[InterfacesDict["OSPFv2"][0]] + ospfOutputLine


                            # Print BFD timers for each OSPF process where this interface is enabled
                            if len(bfdList) > 0:
                                bfdOutputLine = ""
                                for bfdLine in bfdList:
                                    if bfdOutputLine != "":
                                        bfdOutputLine = bfdOutputLine + ";"
                                    if (( bfdLine[2] != "" ) or ( bfdLine[3] != "" )):
                                        if bfdLine[2] == "": ospfLine[2] = "def"
                                        if bfdLine[3] == "": ospfLine[3] = "def"
                                        bfdOutputLine = bfdOutputLine + "type:"+str(bfdLine[0]) + "|pid:"+str(bfdLine[1]) + "|tmr:"+str(bfdLine[2])+" "+str(bfdLine[2])+" "+str(bfdLine[3])

                                InterfacesParse[InterfacesDict["BFD"][0]] = bfdOutputLine


                    # Find if LDP is enabled on this interface
                    for obj10 in cfg.find_objects(r"^mpls ldp"):
                        # print(obj10)
                        LDPIfAdmState = ""
                        LDPIPv4AdmState = ""
                        LDPIPv6AdmState = ""

                        searchExpression = InterfacesParse[InterfacesDict["IfName"][0]] + r"$"
                        for obj12 in obj10.re_search_children(searchExpression):
                            # print(obj12)
                            for obj13 in obj12.re_search_children(r"shutdown"):
                                LDPIfAdmState = "if:Dis"
                                break
                            if LDPIfAdmState == "":
                                LDPIfAdmState = "if:En"

                        if LDPIfAdmState != "":
                            for obj12 in obj10.re_search_children(r"address-family ipv4"):
                                LDPIPv4AdmState = "ipv4:En"
                            # if LDPIPv4AdmState == "": LDPIPv4AdmState = "ipv4:Dis"
                            for obj12 in obj10.re_search_children(r"address-family ipv6"):
                                LDPIPv6AdmState = "ipv6:En"
                            # if LDPIPv6AdmState == "": LDPIPv6AdmState = "ipv6:Dis"


                        if LDPIfAdmState != "":
                            InterfacesParse[InterfacesDict["LDP"][0]] = LDPIfAdmState
                        if LDPIPv4AdmState != "":
                            InterfacesParse[InterfacesDict["LDP"][0]] = InterfacesParse[InterfacesDict["LDP"][0]] + "|" + LDPIPv4AdmState
                        if LDPIPv6AdmState != "":
                            InterfacesParse[InterfacesDict["LDP"][0]] = InterfacesParse[InterfacesDict["LDP"][0]] + "|" + LDPIPv6AdmState

                        # print(InterfacesParse[InterfacesDict["LDP"][0]])


                    # Find QoS input policy associated with current interface
                    for obj2 in obj1.re_search_children("service-policy input"):
                        InterfacesParse[InterfacesDict["QoSIn"][0]] = str(obj2.text.split("service-policy input ")[1])
                        break

                    # Find QoS output policy associated with current interface
                    for obj2 in obj1.re_search_children("service-policy output"):
                        InterfacesParse[InterfacesDict["QoSOut"][0]] = str(obj2.text.split("service-policy output ")[1])
                        break

                    # Find if SyncE enabled on current interface
                    for obj2 in obj1.re_search_children("synchronization"):
                        InterfacesParse[InterfacesDict["SyncE"][0]] = "En"
                        # Find SyncE configuration on current interface
                        for obj3 in obj2.re_search_children(r".*"):
                            InterfacesParse[InterfacesDict["SyncE"][0]] = InterfacesParse[InterfacesDict["SyncE"][0]] + "|" + str(obj3.text.lstrip().rstrip())
                            # break
                        break

                    # Find if CDP is enabled on current interface
                    for obj2 in obj1.re_search_children("cdp"):
                        InterfacesParse[InterfacesDict["CDP"][0]] = "En"
                        break

                    # Find if LLDP is enabled on current interface
                    for obj2 in obj1.re_search_children("lldp"):
                        InterfacesParse[InterfacesDict["LLDP"][0]] = "En"
                        break

                    #########################################################################################################################################
                    #                                                    Post-processing for interfaces                                                     #
                    #########################################################################################################################################

                    # Sort VLANs for Ports
                    if re.search(r"(Port|LAG)",InterfacesParse[InterfacesDict["IfType"][0]]):
                        if re.search(r"\|",InterfacesParse[InterfacesDict["VLAN"][0]]):
                            # print(InterfacesParse[InterfacesDict["VLAN"][0]])
                            # print(InterfacesParse[InterfacesDict["VLAN"][0]].split("|"))
                            # print(sorted(InterfacesParse[InterfacesDict["VLAN"][0]].split("|")))
                            VLANList = []
                            for value in InterfacesParse[InterfacesDict["VLAN"][0]].split("|"):
                                VLANList.append(value)
                            VLANList = sorted(VLANList, key=float)

                            InterfacesParse[InterfacesDict["VLAN"][0]] = ""
                            # VLANList = VLANList.sort()
                            # print(VLANList)
                            for value in VLANList:
                                if InterfacesParse[InterfacesDict["VLAN"][0]] != "": InterfacesParse[InterfacesDict["VLAN"][0]] = InterfacesParse[InterfacesDict["VLAN"][0]] + "|"
                                InterfacesParse[InterfacesDict["VLAN"][0]] = InterfacesParse[InterfacesDict["VLAN"][0]] + str(value)

                    # Sort BridgeIDs for Ports
                    if re.search(r"Port",InterfacesParse[InterfacesDict["IfType"][0]]):
                        if re.search(r"\|",InterfacesParse[InterfacesDict["BridgeID"][0]]):
                            # print(InterfacesParse[InterfacesDict["VLAN"][0]])
                            # print(InterfacesParse[InterfacesDict["VLAN"][0]].split("|"))
                            # print(sorted(InterfacesParse[InterfacesDict["VLAN"][0]].split("|")))
                            BridgeList = []
                            for value in InterfacesParse[InterfacesDict["BridgeID"][0]].split("|"):
                                BridgeList.append(value)
                            BridgeList = sorted(BridgeList, key=float)

                            InterfacesParse[InterfacesDict["BridgeID"][0]] = ""
                            # VLANList = VLANList.sort()
                            # print(BridgeList)
                            for value in BridgeList:
                                if InterfacesParse[InterfacesDict["BridgeID"][0]] != "": InterfacesParse[InterfacesDict["BridgeID"][0]] = InterfacesParse[InterfacesDict["BridgeID"][0]] + "|"
                                InterfacesParse[InterfacesDict["BridgeID"][0]] = InterfacesParse[InterfacesDict["BridgeID"][0]] + str(value)




                    InterfacesParse = [element.rstrip().lstrip() for element in InterfacesParse]
                    InterfacesParseAll.append(InterfacesParse)


#####################################################################################################################################################
###################################################               Cisco IOS/IOS-XE parsing               ############################################
#####################################################################################################################################################

            # Syntax: Cisco IOS/IOS-XE
            if (CLISyntax == "IOS"):
                if debug: print("debug: Using IOS syntax to parse file")
                # Find node's interfaces from config
                for obj1 in cfg.find_objects(r"^interface"):
                    duplicate = []
                    for obj2 in cfg.find_objects(r"^interface"):
                        if obj1.text.split("interface ")[1].split(" ")[0] == obj2.text.split("interface ")[1].split(" ")[0]:
                            duplicate.append(str(obj2))

                    if len(duplicate) > 1:
                        print("File "+str(os.path.split(inputPath)[1])+" contains duplicate interface lines: "+str(duplicate)+", skipping this file")
                        nextFile = 1
                        break

                    IfNumber = IfNumber + 1
                    InterfacesParse = [""] * len(InterfacesDict)
                    if debug: print("debug: obj1: "+str(obj1))

                    InterfacesParse[InterfacesDict["NodeID"][0]] = NodeID
                    InterfacesParse[InterfacesDict["Hostname"][0]] = Hostname
                    InterfacesParse[InterfacesDict["CLISyntax"][0]] = CLISyntax
                    InterfacesParse[InterfacesDict["IfNumber"][0]] = str(IfNumber).zfill(4)
                    InterfacesParse[InterfacesDict["IfName"][0]] = obj1.text.split("interface ")[1].split()[0]

                    # Check if interface is a subinterface of another one
                    if re.search(r'\.',InterfacesParse[InterfacesDict["IfName"][0]]):
                        InterfacesParse[InterfacesDict["ParentIfName"][0]] = InterfacesParse[InterfacesDict["IfName"][0]].split(".")[0]
                        InterfacesParse[InterfacesDict["PortName"][0]] = InterfacesParse[InterfacesDict["IfName"][0]].split(".")[0]
                        InterfacesParse[InterfacesDict["IfType"][0]] = "SubIf"
                    else:
                        # Check if interface is physical port
                        if re.search(r'([Gg]ig[Ee]|[Ee]thernet)',InterfacesParse[InterfacesDict["IfName"][0]]):
                            InterfacesParse[InterfacesDict["PortName"][0]] = InterfacesParse[InterfacesDict["IfName"][0]]
                            InterfacesParse[InterfacesDict["IfType"][0]] = "Port"
                            if re.search(r'[Hh]undred[Gg]ig(abit)?E',InterfacesParse[InterfacesDict["IfName"][0]]):
                                InterfacesParse[InterfacesDict["PortType"][0]] = "100GE"
                            else:
                                if re.search(r'[Tt]en[Gg]ig(abit)?E',InterfacesParse[InterfacesDict["IfName"][0]]):
                                    InterfacesParse[InterfacesDict["PortType"][0]] = "10GE"
                                else:
                                    if re.search(r'[Gg]igabit',InterfacesParse[InterfacesDict["IfName"][0]]):
                                        InterfacesParse[InterfacesDict["PortType"][0]] = "1GE"
                                    else:
                                        if re.search(r'[Ff]ast',InterfacesParse[InterfacesDict["IfName"][0]]):
                                            InterfacesParse[InterfacesDict["PortType"][0]] = "100ME"
                                        else:
                                            InterfacesParse[InterfacesDict["PortType"][0]] = ""


                        # Check if interface is a bundle
                        if re.search(r'(P|p)ort-(C|C)hannel',InterfacesParse[InterfacesDict["IfName"][0]]):
                            InterfacesParse[InterfacesDict["PortName"][0]] = InterfacesParse[InterfacesDict["IfName"][0]]
                            InterfacesParse[InterfacesDict["LAGID"][0]] = str(InterfacesParse[InterfacesDict["IfName"][0]].split("hannel")[1].split(".")[0])
                            InterfacesParse[InterfacesDict["IfType"][0]] = "LAG"


                    # Check if interface is a loopback
                    if re.search(r"[Ll]oop[Bb]ack",InterfacesParse[InterfacesDict["IfName"][0]]):
                        InterfacesParse[InterfacesDict["IfType"][0]] = "Loopback"

                    # Check if interface is a BDI
                    if re.search(r'BDI',InterfacesParse[InterfacesDict["IfName"][0]]):
                        # print(InterfacesParse[InterfacesDict["IfName"][0]])
                        InterfacesParse[InterfacesDict["BridgeID"][0]] = str(InterfacesParse[InterfacesDict["IfName"][0]].split("BDI")[1].split(".")[0])
                        InterfacesParse[InterfacesDict["IfType"][0]] = "Bridge"
                        # Find port with wich ports this BDI is associated
                        for obj10 in cfg.find_objects(r"^interface"):

                            tempPortBinding = ""
                            tempVLAN = ""
                            tempEncap = ""
                            # Find bridge-domain IDs and respective VLANs associated with current interface
                            for obj11 in obj10.re_search_children("service instance "):
                                for obj12 in obj11.re_search_children("bridge-domain "):
                                    if InterfacesParse[InterfacesDict["BridgeID"][0]] == obj12.text.split("bridge-domain ")[1].split()[0]:

                                        tempPortBinding = obj10.text.split("interface ")[1]

                                        if InterfacesParse[InterfacesDict["PortName"][0]] == "":
                                            InterfacesParse[InterfacesDict["PortName"][0]] = tempPortBinding
                                        else:
                                            InterfacesParse[InterfacesDict["PortName"][0]] = InterfacesParse[InterfacesDict["PortName"][0]] + "|" + tempPortBinding

                                        for obj13 in obj11.re_search_children(r"^ *encapsulation "):
                                            if re.search("second-dot1q ",obj13.text):
                                                tempVLAN = (str(obj13.text.split("dot1q ")[1].split(" ")[0]) + "." + str(obj13.text.split("second-dot1q ")[1].split(" ")[0]))
                                                tempEncap = "qinq"

                                            else:
                                                if re.search("dot1q ",obj13.text):
                                                    tempVLAN = str(obj13.text.split("dot1q ")[1].split(" ")[0])
                                                    tempEncap = "dot1q"
                                                    # tempPortBinding = tempPortBinding + ":" + obj13.text.split("dot1q ")[1].split(" ")[0]
                                                else:
                                                    tempVLAN = "0"
                                                    tempEncap = "null"
                                                    # tempPortBinding = tempPortBinding + ":" + obj13.text.split("dot1q ")[1].split(" ")[0]
                                            tempPortBinding = tempPortBinding + ":" + tempVLAN


                                        if tempPortBinding != "":
                                            if InterfacesParse[InterfacesDict["PortBinding"][0]] == "":
                                                InterfacesParse[InterfacesDict["PortBinding"][0]] = tempPortBinding
                                            else:
                                                InterfacesParse[InterfacesDict["PortBinding"][0]] = InterfacesParse[InterfacesDict["PortBinding"][0]] + "|" + tempPortBinding

                                        if tempEncap != "":
                                            if InterfacesParse[InterfacesDict["Encap"][0]] == "":
                                                InterfacesParse[InterfacesDict["Encap"][0]] = tempEncap
                                            else:
                                                InterfacesParse[InterfacesDict["Encap"][0]] = InterfacesParse[InterfacesDict["Encap"][0]] + "|" + tempEncap

                                        if tempVLAN != "":
                                            if InterfacesParse[InterfacesDict["VLAN"][0]] == "":
                                                InterfacesParse[InterfacesDict["VLAN"][0]] = tempVLAN
                                            else:
                                                InterfacesParse[InterfacesDict["VLAN"][0]] = InterfacesParse[InterfacesDict["VLAN"][0]] + "|" + tempVLAN

                                        break


                    # Find description associated with current interface
                    for obj2 in obj1.re_search_children("description "):
                        InterfacesParse[InterfacesDict["IfDescr"][0]] = str(obj2.text.split("description ")[1].replace("\"",""))
                        break

                    # Find encapsulation associated with current interface
                    for obj2 in obj1.re_search_children(r"^ *encapsulation "):
                        if InterfacesParse[InterfacesDict["VLAN"][0]] != "": InterfacesParse[InterfacesDict["VLAN"][0]] = InterfacesParse[InterfacesDict["VLAN"][0]] + "|"
                        if re.search("second-dot1q ",obj2.text):
                            if ((InterfacesParse[InterfacesDict["Encap"][0]] == "dot1q") or (InterfacesParse[InterfacesDict["Encap"][0]] == "")):
                                InterfacesParse[InterfacesDict["Encap"][0]] = "qinq"
                            InterfacesParse[InterfacesDict["VLAN"][0]] = InterfacesParse[InterfacesDict["VLAN"][0]] + (str(obj2.text.split(" dot1q ")[1].split(" second-dot1q ")[0].lstrip().rstrip().replace(" , ","|"))) + "." + str(obj2.text.split(" second-dot1q ")[1].lstrip().rstrip().replace(" , ","|"))
                        else:
                            if re.search("dot1q ",obj2.text):
                                if InterfacesParse[InterfacesDict["Encap"][0]] == "":
                                    InterfacesParse[InterfacesDict["Encap"][0]] = "dot1q"
                                InterfacesParse[InterfacesDict["VLAN"][0]] = InterfacesParse[InterfacesDict["VLAN"][0]] + str(obj2.text.split(" dot1q ")[1].lstrip().rstrip().replace(" , ","|"))
                            else:
                                if re.search("untagged",obj2.text):
                                    if InterfacesParse[InterfacesDict["Encap"][0]] == "":
                                        InterfacesParse[InterfacesDict["Encap"][0]] = "null"
                                    InterfacesParse[InterfacesDict["VLAN"][0]] = InterfacesParse[InterfacesDict["VLAN"][0]] + "0"
                    # for obj2 in obj1.re_search_children("encapsulation"):
                    #     if re.search(" second-dot1q ",obj2.text):
                    #         InterfacesParse[InterfacesDict["Encap"][0]] = "qinq"
                    #         InterfacesParse[InterfacesDict["VLAN"][0]] = (str(obj2.text.split("dot1q ")[1].split(" ")[0]) + "." + str(obj2.text.split("second-dot1q ")[1].split(" ")[0]))
                    #     else:
                    #         if re.search(" dot1q ",obj2.text):
                    #             InterfacesParse[InterfacesDict["Encap"][0]] = "dot1q"
                    #             InterfacesParse[InterfacesDict["VLAN"][0]] = str(obj2.text.split("dot1q ")[1].split(" ")[0])
                    #         else:
                    #             if re.search(" untagged",obj2.text):
                    #                 InterfacesParse[InterfacesDict["Encap"][0]] = "null"
                    #                 InterfacesParse[InterfacesDict["VLAN"][0]] = "0"
                    #     break

                    # If encapsulation was not specified set it to default
                    if (((InterfacesParse[InterfacesDict["IfType"][0]] == "Port") or (InterfacesParse[InterfacesDict["IfType"][0]] == "LAG")) and len(obj1.re_search_children("service instance ")) == 0):
                        if InterfacesParse[InterfacesDict["Encap"][0]] == "":
                            InterfacesParse[InterfacesDict["Encap"][0]] = "null"
                        if InterfacesParse[InterfacesDict["VLAN"][0]] == "":
                            InterfacesParse[InterfacesDict["VLAN"][0]] = "0"

                    # Find LAG associated with current interface
                    for obj2 in obj1.re_search_children("channel-group "):
                        InterfacesParse[InterfacesDict["LAGID"][0]] = str(obj2.text.split("channel-group ")[1].split(" ")[0])
                        if re.search("active",obj2.text):
                            InterfacesParse[InterfacesDict["LAGMode"][0]] = "Active"
                        else:
                            if re.search("passive",obj2.text):
                                InterfacesParse[InterfacesDict["LAGMode"][0]] = "Passive"

                        for obj3 in cfg.find_objects(r"^interface (P|p)ort-(C|c)hannel"+str(InterfacesParse[InterfacesDict["LAGID"][0]])):
                            InterfacesParse[InterfacesDict["ParentIfName"][0]] = obj3.text.split("interface ")[1]
                            break
                        break

                    # Find bridge-domain IDs and respective VLANs associated with current interface
                    for obj2 in obj1.re_search_children("service instance "):
                        for obj3 in obj2.re_search_children("bridge-domain "):
                            if InterfacesParse[InterfacesDict["BridgeID"][0]] != "": InterfacesParse[InterfacesDict["BridgeID"][0]] = InterfacesParse[InterfacesDict["BridgeID"][0]] + "|"
                            InterfacesParse[InterfacesDict["BridgeID"][0]] = InterfacesParse[InterfacesDict["BridgeID"][0]] + str(obj3.text.split("bridge-domain ")[1].split()[0])
                            # if InterfacesParse[InterfacesDict["BridgeID"][0]] == "":
                            #     InterfacesParse[InterfacesDict["BridgeID"][0]] = str(obj3.text.split("bridge-domain ")[1].split(" ")[0])
                            # else:
                            #     InterfacesParse[InterfacesDict["BridgeID"][0]] = InterfacesParse[InterfacesDict["BridgeID"][0]] + "|" + str(obj3.text.split("bridge-domain ")[1])

                        for obj3 in obj2.re_search_children(r"^ *encapsulation "):
                            if InterfacesParse[InterfacesDict["VLAN"][0]] != "": InterfacesParse[InterfacesDict["VLAN"][0]] = InterfacesParse[InterfacesDict["VLAN"][0]] + "|"
                            if re.search("second-dot1q ",obj3.text):
                                if ((InterfacesParse[InterfacesDict["Encap"][0]] == "dot1q") or (InterfacesParse[InterfacesDict["Encap"][0]] == "")):
                                    InterfacesParse[InterfacesDict["Encap"][0]] = "qinq"
                                # if InterfacesParse[InterfacesDict["VLAN"][0]] == "":
                                #     InterfacesParse[InterfacesDict["VLAN"][0]] = (str(obj3.text.split("dot1q ")[1].split(" ")[0]) + ":" + str(obj3.text.split("second-dot1q ")[1].split(" ")[0]))
                                # else:
                                InterfacesParse[InterfacesDict["VLAN"][0]] = InterfacesParse[InterfacesDict["VLAN"][0]] + (str(obj3.text.split("dot1q ")[1].split(" ")[0]) + "." + str(obj3.text.split("second-dot1q ")[1].split(" ")[0]))
                            else:
                                if re.search("dot1q ",obj3.text):
                                    if InterfacesParse[InterfacesDict["Encap"][0]] == "":
                                        InterfacesParse[InterfacesDict["Encap"][0]] = "dot1q"
                                    # if InterfacesParse[InterfacesDict["VLAN"][0]] == "":
                                    #     InterfacesParse[InterfacesDict["VLAN"][0]] = str(obj3.text.split("dot1q ")[1].split(" ")[0])
                                    # else:
                                    InterfacesParse[InterfacesDict["VLAN"][0]] = InterfacesParse[InterfacesDict["VLAN"][0]] + str(obj3.text.split("dot1q ")[1].split(" ")[0])
                                else:
                                    if re.search("untagged",obj3.text):
                                        if InterfacesParse[InterfacesDict["Encap"][0]] == "":
                                            InterfacesParse[InterfacesDict["Encap"][0]] = "null"
                                        # if InterfacesParse[InterfacesDict["VLAN"][0]] == "":
                                        #     InterfacesParse[InterfacesDict["VLAN"][0]] = str(obj3.text.split("dot1q ")[1].split(" ")[0])
                                        # else:
                                        InterfacesParse[InterfacesDict["VLAN"][0]] = InterfacesParse[InterfacesDict["VLAN"][0]] + "0"


                    # Find subinterfaces and respective VLANs associated with current interface
                    for obj40 in cfg.find_objects(r"^interface"):
                        searchExpression = r"^ *interface " + InterfacesParse[InterfacesDict["IfName"][0]] + r"\.[0-9]+$"
                        if re.match(searchExpression,obj40.text):
                            # print("FOUND")
                            for obj3 in obj40.re_search_children(r"^ *encapsulation "):
                                if InterfacesParse[InterfacesDict["VLAN"][0]] != "": InterfacesParse[InterfacesDict["VLAN"][0]] = InterfacesParse[InterfacesDict["VLAN"][0]] + "|"
                                if re.search("second-dot1q ",obj3.text):
                                    if ((InterfacesParse[InterfacesDict["Encap"][0]] == "dot1q") or (InterfacesParse[InterfacesDict["Encap"][0]] == "")):
                                        InterfacesParse[InterfacesDict["Encap"][0]] = "qinq"
                                    InterfacesParse[InterfacesDict["VLAN"][0]] = InterfacesParse[InterfacesDict["VLAN"][0]] + (str(obj3.text.split("dot1q ")[1].split(" ")[0]) + "." + str(obj3.text.split("second-dot1q ")[1].split(" ")[0]))
                                else:
                                    if re.search("dot1q ",obj3.text):
                                        if InterfacesParse[InterfacesDict["Encap"][0]] == "":
                                            InterfacesParse[InterfacesDict["Encap"][0]] = "dot1q"
                                        InterfacesParse[InterfacesDict["VLAN"][0]] = InterfacesParse[InterfacesDict["VLAN"][0]] + str(obj3.text.split("dot1q ")[1].split(" ")[0])
                                    else:
                                        if re.search("untagged",obj3.text):
                                            if InterfacesParse[InterfacesDict["Encap"][0]] == "":
                                                InterfacesParse[InterfacesDict["Encap"][0]] = "null"
                                            InterfacesParse[InterfacesDict["VLAN"][0]] = InterfacesParse[InterfacesDict["VLAN"][0]] + "0"


                    # Find admin state associated with current interface
                    for obj2 in obj1.re_search_children(r"^ +shutdown"):
                        if str(obj2.text.split(" ")[1]):
                            InterfacesParse[InterfacesDict["StateAdm"][0]] = "Dis"
                        else:
                            InterfacesParse[InterfacesDict["StateAdm"][0]] = "En"
                    if InterfacesParse[InterfacesDict["StateAdm"][0]] == "":
                        InterfacesParse[InterfacesDict["StateAdm"][0]] = "En"

                    # Find L3VPN service associated with current interface
                    for obj2 in obj1.re_search_children("vrf forwarding"):
                        InterfacesParse[InterfacesDict["ServiceName"][0]] = str(obj2.text.split("vrf forwarding ")[1])
                        InterfacesParse[InterfacesDict["ServiceType"][0]] = "L3VPN"

                    # Find L2 MTU associated with current interface
                    for obj2 in obj1.re_search_children(r"^ +mtu"):
                        InterfacesParse[InterfacesDict["L2MTU"][0]]  = str(obj2.text.split("mtu ")[1])
                        break

                    # Find L3 MTU associated with current interface
                    for obj2 in obj1.re_search_children(r"^ +ip mtu"):
                        InterfacesParse[InterfacesDict["L3MTU"][0]]  = str(obj2.text.split("mtu ")[1])
                        break

                    # Find all IPv4 addresses associated with current interface
                    for obj2 in obj1.re_search_children("ip address "):
                        rawInput = obj2.text.split("ip address ")[1].split("secondary")[0].lstrip().rstrip()
                        rawInput = rawInput.replace(" ","/")
                        ipadd = ipaddress.ip_interface(str(rawInput))
                        if InterfacesParse[InterfacesDict["IPV4Addr"][0]] == "":
                            InterfacesParse[InterfacesDict["IPV4Addr"][0]] = str(ipadd)
                        else:
                            InterfacesParse[InterfacesDict["IPV4Addr"][0]] = InterfacesParse[InterfacesDict["IPV4Addr"][0]] + "|" + str(ipadd)
                        if InterfacesParse[InterfacesDict["IPV4Subnet"][0]] == "":
                            InterfacesParse[InterfacesDict["IPV4Subnet"][0]] = str(ipadd.network)
                        else:
                            InterfacesParse[InterfacesDict["IPV4Subnet"][0]] = InterfacesParse[InterfacesDict["IPV4Subnet"][0]] + "|"+ str(ipadd.network)

                    # Find all IPv6 addresses associated with current interface
                    for obj2 in obj1.re_search_children("ipv6 address "):
                        rawInput = obj2.text.split("ipv6 address ")[1].lstrip().rstrip()
                        ipadd = ipaddress.ip_interface(str(line))
                        if InterfacesParse[InterfacesDict["IPV6Addr"][0]] == "":
                            InterfacesParse[InterfacesDict["IPV6Addr"][0]] = str(ipadd)
                        else:
                            InterfacesParse[InterfacesDict["IPV6Addr"][0]] = InterfacesParse[InterfacesDict["IPV6Addr"][0]] + "|" + str(ipadd)
                        if InterfacesParse[InterfacesDict["IPV6Subnet"][0]] == "":
                            InterfacesParse[InterfacesDict["IPV6Subnet"][0]] = str(ipadd.network)
                        else:
                            InterfacesParse[InterfacesDict["IPV6Subnet"][0]] = InterfacesParse[InterfacesDict["IPV6Subnet"][0]] + "|" + str(ipadd.network)

                    # Check if interface is a L3 interface
                    if ((InterfacesParse[InterfacesDict["IPV4Addr"][0]] != "") or (InterfacesParse[InterfacesDict["IPV6Addr"][0]] != "")):
                        if InterfacesParse[InterfacesDict["PortBinding"][0]] == "":
                            if InterfacesParse[InterfacesDict["VLAN"][0]] == "":
                                InterfacesParse[InterfacesDict["PortBinding"][0]] = InterfacesParse[InterfacesDict["PortName"][0]]
                            else:
                                InterfacesParse[InterfacesDict["PortBinding"][0]] = InterfacesParse[InterfacesDict["PortName"][0]] + ":" + InterfacesParse[InterfacesDict["VLAN"][0]]
                        # Mark interface as Network/Hybrid if it has any IPv4/v6 addresses assigned and no VRF assigned and create port binding for it
                        if (InterfacesParse[InterfacesDict["ServiceName"][0]] == ""):
                            if InterfacesParse[InterfacesDict["IfType"][0]] == "":
                                InterfacesParse[InterfacesDict["IfType"][0]] = "L3"
                            else:
                                InterfacesParse[InterfacesDict["IfType"][0]] = InterfacesParse[InterfacesDict["IfType"][0]] + "|L3"
                            InterfacesParse[InterfacesDict["IfMode"][0]] = "Network"
                        # Mark interface as Access if it has any IPv4/v6 addresses and VRF assigned and create port binding for it
                        else:
                            if InterfacesParse[InterfacesDict["IfType"][0]] == "":
                                InterfacesParse[InterfacesDict["IfType"][0]] = "L3VPN"
                            else:
                                InterfacesParse[InterfacesDict["IfType"][0]] = InterfacesParse[InterfacesDict["IfType"][0]] + "|L3VPN"
                            InterfacesParse[InterfacesDict["IfMode"][0]] = "Access"

                    # Check if interface has any port binding assigned
                    if ((InterfacesParse[InterfacesDict["ServiceName"][0]] != "") or (InterfacesParse[InterfacesDict["ServiceID"][0]] != "")):
                        if InterfacesParse[InterfacesDict["PortBinding"][0]] == "":
                            if InterfacesParse[InterfacesDict["VLAN"][0]] == "":
                                InterfacesParse[InterfacesDict["PortBinding"][0]] = InterfacesParse[InterfacesDict["PortName"][0]]
                            else:
                                InterfacesParse[InterfacesDict["PortBinding"][0]] = InterfacesParse[InterfacesDict["PortName"][0]] + ":" + InterfacesParse[InterfacesDict["VLAN"][0]]

                    # Find QoS input policy associated with current interface
                    for obj2 in obj1.re_search_children("service-policy input"):
                        InterfacesParse[InterfacesDict["QoSIn"][0]] = str(obj2.text.split("service-policy input ")[1])
                        break

                    # Find QoS output policy associated with current interface
                    for obj2 in obj1.re_search_children("service-policy output"):
                        InterfacesParse[InterfacesDict["QoSOut"][0]] = str(obj2.text.split("service-policy output ")[1])
                        break

                    # Find if SyncE enabled on current interface
                    for obj2 in obj1.re_search_children("synchronization"):
                        InterfacesParse[InterfacesDict["SyncE"][0]] = "En"
                        # Find SyncE configuration on current interface
                        for obj3 in obj2.re_search_children(r".*"):
                            InterfacesParse[InterfacesDict["SyncE"][0]] = InterfacesParse[InterfacesDict["SyncE"][0]] + "|" + str(obj3.text)
                            # break
                        break

                    # Find if CDP is enabled on current interface
                    for obj2 in obj1.re_search_children("cdp"):
                        InterfacesParse[InterfacesDict["CDP"][0]] = "En"
                        break

                    # Find if LLDP is enabled on current interface
                    for obj2 in obj1.re_search_children("lldp"):
                        InterfacesParse[InterfacesDict["LLDP"][0]] = "En"
                        break

                    # Find all OSPF processes and areas where this interface is participating
                    ospfList = []

                    # Find all OSPF processes associated with interface
                    for obj10 in obj1.re_search_children(r"ip ospf [0-9]+"):
                        ospfLine = []
                        ospfPID = ""
                        ospfRID = ""
                        ospfPID = str(obj10.text.split("ip ospf ")[1].split(" ")[0])
                        ospfLine.append(ospfPID)

                        ospfIfType1 = ""
                        ospfIfType2 = "Bcast"
                        ospfIfMode = "Act"
                        ospfBFDState = "Dis"
                        ospfPriority = ""
                        ospfMetric = ""
                        ospfHello = ""
                        ospfDead = ""
                        ospfRetransmit = ""
                        ospfAuth = ""

                        # Find all OSPF interface parameters
                        for obj11 in obj1.re_search_children("ip ospf network "):
                            ospfIfType1 = str(obj11.text.split("ip ospf network ")[1].split(" ")[0].lstrip().rstrip())
                            ospfIfType2 = ""
                            if ospfIfType1 == "point-to-point":
                                ospfIfType2 = "PtP"
                            else:
                                if ospfIfType1 == "point-to-multipoint":
                                    ospfIfType2 = "PtMP"
                                else:
                                    ospfIfType2 = ospfIfType1
                            break

                        for obj100 in cfg.find_objects(r"^router ospf "+ospfPID+r" *$"):
                            for obj101 in obj100.re_search_children("router-id"):
                                ospfRID = obj101.text.split("router-id ")[1].split()[0].lstrip().rstrip()
                                break
                            for obj101 in obj100.re_search_children("passive-interface default"):
                                if re.match(r"^ *no passive-interface default *$",obj101.text):
                                    ospfIfMode = "Act"
                                if re.match(r"^ *passive-interface default *$",obj101.text):
                                    ospfIfMode = "Pass"

                            searchExpression = InterfacesParse[InterfacesDict["IfName"][0]] + r"$"
                            for obj101 in obj100.re_search_children(searchExpression):
                                if re.search(r"^ *no passive-interface *.*$",obj101.text):
                                    ospfIfMode = "Act"
                                if re.search(r"^ *passive-interface *.*$",obj101.text):
                                    ospfIfMode = "Pass"

                            for obj101 in obj100.re_search_children("bfd all-interfaces"):
                                if re.match(r"^ *bfd all-interfaces *$",obj101.text):
                                    ospfBFDState = "En"
                                if re.match(r"^ *no bfd all-interfaces *$",obj101.text):
                                    ospfBFDState = "Dis"
                        ospfLine.append(ospfRID)
                        ospfLine.append(ospfIfType2)
                        ospfLine.append(ospfIfMode)

                        for obj11 in obj1.re_search_children("ip ospf bfd"):
                            if re.match(r"^ *ip ospf bfd *$",obj11.text):
                                ospfBFDState = "En"
                            if re.match(r"^ *ip ospf bfd disable *$",obj11.text):
                                ospfBFDState = "Dis"
                            break
                        ospfLine.append(ospfBFDState)
                        for obj11 in obj1.re_search_children("ip ospf priority "):
                            ospfPriority = str(obj11.text.split("ip ospf priority ")[1].split(" ")[0].lstrip().rstrip())
                            break
                        ospfLine.append(ospfPriority)
                        for obj11 in obj1.re_search_children("ip ospf cost "):
                            ospfMetric = str(obj11.text.split("ip ospf cost ")[1].split(" ")[0].lstrip().rstrip())
                            break
                        ospfLine.append(ospfMetric)
                        for obj11 in obj1.re_search_children("ip ospf hello-interval "):
                            ospfHello = str(obj11.text.split("ip ospf hello-interval ")[1].split(" ")[0].lstrip().rstrip())
                            break
                        ospfLine.append(ospfHello)
                        for obj11 in obj1.re_search_children("ip ospf dead-interval "):
                            ospfDead = str(obj11.text.split("ip ospf dead-interval ")[1].split(" ")[0].lstrip().rstrip())
                            break
                        ospfLine.append(ospfDead)
                        for obj11 in obj1.re_search_children("ip ospf retransmit-interval "):
                            ospfRetransmit = str(obj11.text.split("ip ospf retransmit-interval ")[1].split(" ")[0].lstrip().rstrip())
                            break
                        ospfLine.append(ospfRetransmit)
                        for obj11 in obj1.re_search_children("ip ospf authentication "):
                            ospfAuth = str(obj11.text.split("ip ospf authentication ")[1].split(" ")[0].lstrip().rstrip())
                            break
                        ospfLine.append(ospfAuth)

                        ospfAreaList = []
                        area = ""
                        # Find all OSPF primary areas
                        for obj11 in obj1.re_search_children("ip ospf "+ospfPID+" area"):
                            area = obj11.text.split("area ")[1]
                            area = ipaddress.ip_address(int(area))

                            ospfAreaList.append([int(area),"*"])

                        # Find all OSPF multi-areas
                        for obj11 in obj1.re_search_children(r"ip ospf multi-area"):
                            area = obj11.text.split("area ")[1]
                            area = ipaddress.ip_address(int(area))

                            ospfAreaList.append([int(area),""])

                        ospfAreaList.sort(key=lambda x: x[0])
                        ospfLine.append(ospfAreaList)

                        ospfList.append(ospfLine)

                    if len(ospfList) > 0:
                        ospfOutputLine = ""
                        for ospfLine in ospfList:
                            # print(ospfLine)
                            if ospfOutputLine != "":
                                ospfOutputLine = ospfOutputLine + ";"

                            ospfOutputLine = ospfOutputLine + "pid:"+str(ospfLine[0])
                            if ospfLine[1] != "": ospfOutputLine = ospfOutputLine + "|rid:" + str(ospfLine[1])
                            ospfOutputLine = ospfOutputLine + "|type:"+str(ospfLine[2]) + "|mode:"+str(ospfLine[3]) + "|bfd:"+str(ospfLine[4])
                            if ospfLine[5] != "": ospfOutputLine = ospfOutputLine + "|prio:" + str(ospfLine[5])
                            if ospfLine[6] != "": ospfOutputLine = ospfOutputLine + "|metr:" + str(ospfLine[6])
                            if ((ospfLine[7] != "") or (ospfLine[8] != "") or (ospfLine[9] != "")):
                                if ospfLine[7] == "": ospfLine[7] = "def"
                                if ospfLine[8] == "": ospfLine[8] = "def"
                                if ospfLine[9] == "": ospfLine[9] = "def"
                                ospfOutputLine = ospfOutputLine + "|ospf_tmr:" + str(ospfLine[7]) + " " + str(ospfLine[8]) + " " + str(ospfLine[9])
                            if ospfLine[10] != "": ospfOutputLine = ospfOutputLine + "|auth:" + str(ospfLine[10])

                            if len(ospfLine) > 11:
                                ospfOutputLine = ospfOutputLine + "|areas:"

                                ospfOutputLine2 = ""
                                for area in ospfLine[11]:
                                    if ospfOutputLine2 == "":
                                        ospfOutputLine2 = str(area[0]) + str(area[1])
                                    else:
                                        ospfOutputLine2 = ospfOutputLine2 + " " + str(area[0]) + str(area[1])

                                ospfOutputLine = ospfOutputLine + ospfOutputLine2

                        InterfacesParse[InterfacesDict["OSPFv2"][0]] = ospfOutputLine


                    # Find BFD timers associated with current interface
                    for obj2 in obj1.re_search_children(r"bfd interval"):
                        if InterfacesParse[InterfacesDict["BFD"][0]] != "":
                            InterfacesParse[InterfacesDict["BFD"][0]] = InterfacesParse[InterfacesDict["BFD"][0]] + "|"
                        InterfacesParse[InterfacesDict["BFD"][0]] = "if_tmr:" + obj2.text.lstrip().rstrip().replace("bfd interval ","").replace(" min_rx "," ").replace(" multiplier "," ")
                        break
                    # Find BFD template associated with current interface
                    for obj2 in obj1.re_search_children(r"bfd template"):
                        if InterfacesParse[InterfacesDict["BFD"][0]] != "":
                            InterfacesParse[InterfacesDict["BFD"][0]] = InterfacesParse[InterfacesDict["BFD"][0]] + "|"
                        InterfacesParse[InterfacesDict["BFD"][0]] = InterfacesParse[InterfacesDict["BFD"][0]] + "if_tmpl:" + obj2.text.lstrip().rstrip().split("bfd template ")[1].split(" ")[0]
                        break


                    LDPIfAdmState = ""
                    LDPIPv4AdmState = ""
                    LDPIPv6AdmState = ""
                    # Find if LDP is enabled on this interface
                    for obj10 in obj1.re_search_children(r"mpls ip"):
                        LDPIfAdmState = "if:En"
                        LDPIPv4AdmState = "ipv4:En"

                        if LDPIfAdmState != "":
                            InterfacesParse[InterfacesDict["LDP"][0]] = LDPIfAdmState
                        if LDPIPv4AdmState != "":
                            InterfacesParse[InterfacesDict["LDP"][0]] = InterfacesParse[InterfacesDict["LDP"][0]] + "|" + LDPIPv4AdmState
                        if LDPIPv6AdmState != "":
                            InterfacesParse[InterfacesDict["LDP"][0]] = InterfacesParse[InterfacesDict["LDP"][0]] + "|" + LDPIPv6AdmState

                        break



                    #########################################################################################################################################
                    #                                                    Post-processing for interfaces                                                     #
                    #########################################################################################################################################

                    # Sort VLANs for Ports
                    if re.search(r"(Port|LAG)",InterfacesParse[InterfacesDict["IfType"][0]]):
                        if re.search(r"\|",InterfacesParse[InterfacesDict["VLAN"][0]]):
                            # print(InterfacesParse[InterfacesDict["VLAN"][0]])
                            # print(InterfacesParse[InterfacesDict["VLAN"][0]].split("|"))
                            # print(sorted(InterfacesParse[InterfacesDict["VLAN"][0]].split("|")))
                            VLANList = []
                            for value in InterfacesParse[InterfacesDict["VLAN"][0]].split("|"):
                                VLANList.append(value)
                            VLANList = sorted(VLANList, key=float)

                            InterfacesParse[InterfacesDict["VLAN"][0]] = ""
                            # VLANList = VLANList.sort()
                            # print(VLANList)
                            for value in VLANList:
                                if InterfacesParse[InterfacesDict["VLAN"][0]] != "": InterfacesParse[InterfacesDict["VLAN"][0]] = InterfacesParse[InterfacesDict["VLAN"][0]] + "|"
                                InterfacesParse[InterfacesDict["VLAN"][0]] = InterfacesParse[InterfacesDict["VLAN"][0]] + str(value)

                    # Sort BridgeIDs for Ports
                    if re.search(r"Port",InterfacesParse[InterfacesDict["IfType"][0]]):
                        if re.search(r"\|",InterfacesParse[InterfacesDict["BridgeID"][0]]):
                            # print(InterfacesParse[InterfacesDict["VLAN"][0]])
                            # print(InterfacesParse[InterfacesDict["VLAN"][0]].split("|"))
                            # print(sorted(InterfacesParse[InterfacesDict["VLAN"][0]].split("|")))
                            BridgeList = []
                            for value in InterfacesParse[InterfacesDict["BridgeID"][0]].split("|"):
                                BridgeList.append(value)
                            BridgeList = sorted(BridgeList, key=float)

                            InterfacesParse[InterfacesDict["BridgeID"][0]] = ""
                            # VLANList = VLANList.sort()
                            # print(BridgeList)
                            for value in BridgeList:
                                if InterfacesParse[InterfacesDict["BridgeID"][0]] != "": InterfacesParse[InterfacesDict["BridgeID"][0]] = InterfacesParse[InterfacesDict["BridgeID"][0]] + "|"
                                InterfacesParse[InterfacesDict["BridgeID"][0]] = InterfacesParse[InterfacesDict["BridgeID"][0]] + str(value)


                    InterfacesParse = [element.rstrip().lstrip() for element in InterfacesParse]


                    InterfacesParseAll.append(InterfacesParse)

                    # Find EVCs associated with current interface and save them as separate interface
                    for obj2 in obj1.re_search_children("service instance "):

                        IfNumber = IfNumber + 1
                        InterfacesParse = [""] * len(InterfacesDict)
                        if debug: print("debug: obj2: "+str(obj2))

                        InterfacesParse[InterfacesDict["NodeID"][0]] = NodeID
                        InterfacesParse[InterfacesDict["Hostname"][0]] = Hostname
                        InterfacesParse[InterfacesDict["CLISyntax"][0]] = CLISyntax
                        InterfacesParse[InterfacesDict["IfNumber"][0]] = str(IfNumber).zfill(4)
                        # InterfacesParse[InterfacesDict["ParentIfName"][0]] = obj1.text.split("interface ")[1].split(" ")[0]
                        InterfacesParse[InterfacesDict["IfName"][0]] = str(obj1.text.split("interface ")[1].split(" ")[0]) + " EVC " + str(obj2.text.split("service instance ")[1].split(" ")[0])
                        InterfacesParse[InterfacesDict["PortName"][0]] = obj1.text.split("interface ")[1].split(" ")[0]
                        InterfacesParse[InterfacesDict["IfType"][0]] = "EVC"
                        InterfacesParse[InterfacesDict["PortBinding"][0]] = InterfacesParse[InterfacesDict["PortName"][0]]

                        # Find description associated with current EVC
                        for obj3 in obj2.re_search_children("description "):
                            InterfacesParse[InterfacesDict["IfDescr"][0]] = str(obj3.text.split("description ")[1].replace("\"",""))
                            break

                        # Find encapsulation associated with current EVC
                        for obj3 in obj2.re_search_children(r"^ *encapsulation"):
                            if re.search(" second-dot1q ",obj3.text):
                                InterfacesParse[InterfacesDict["Encap"][0]] = "qinq"
                                InterfacesParse[InterfacesDict["VLAN"][0]] = (str(obj3.text.split("dot1q ")[1].split(" ")[0]) + "." + str(obj3.text.split("second-dot1q ")[1].split(" ")[0]))
                                InterfacesParse[InterfacesDict["PortBinding"][0]] = InterfacesParse[InterfacesDict["PortBinding"][0]] + ":" + InterfacesParse[InterfacesDict["VLAN"][0]]
                            else:
                                if re.search(" dot1q ",obj3.text):
                                    InterfacesParse[InterfacesDict["Encap"][0]] = "dot1q"
                                    InterfacesParse[InterfacesDict["VLAN"][0]] = str(obj3.text.split("dot1q ")[1].split(" ")[0])
                                    InterfacesParse[InterfacesDict["PortBinding"][0]] = InterfacesParse[InterfacesDict["PortBinding"][0]] + ":" + InterfacesParse[InterfacesDict["VLAN"][0]]
                            break

                        # Find bridge-domain associated with current EVC
                        for obj3 in obj2.re_search_children("bridge-domain "):
                            if InterfacesParse[InterfacesDict["IfType"][0]] != "": InterfacesParse[InterfacesDict["IfType"][0]] = InterfacesParse[InterfacesDict["IfType"][0]] + "|"
                            InterfacesParse[InterfacesDict["IfType"][0]] = InterfacesParse[InterfacesDict["IfType"][0]] + "L3"

                            if InterfacesParse[InterfacesDict["BridgeID"][0]] == "":
                                InterfacesParse[InterfacesDict["BridgeID"][0]] = str(obj3.text.split("bridge-domain ")[1].split()[0])
                            else:
                                InterfacesParse[InterfacesDict["BridgeID"][0]] = InterfacesParse[InterfacesDict["BridgeID"][0]] + "|" + str(obj3.text.split("bridge-domain ")[1].split()[0])


                        # Find a parent BDI interface if exists
                        for obj30 in cfg.find_objects(r"^interface "):
                            searchExpression = r"^interface BDI" + InterfacesParse[InterfacesDict["BridgeID"][0]] + r"$"
                            if re.match(searchExpression,obj30.text):
                                InterfacesParse[InterfacesDict["ParentIfName"][0]] = obj30.text.split("interface ")[1].split(" ")[0]

                        # Find associated xconnect if exists
                        for obj3 in obj2.re_search_children(r"^ *xconnect "):
                            if InterfacesParse[InterfacesDict["IfType"][0]] != "": InterfacesParse[InterfacesDict["IfType"][0]] = InterfacesParse[InterfacesDict["IfType"][0]] + "|"
                            InterfacesParse[InterfacesDict["IfType"][0]] = InterfacesParse[InterfacesDict["IfType"][0]] + "L2"
                            InterfacesParse[InterfacesDict["ServiceType"][0]] = "L2VPN"

                            if InterfacesParse[InterfacesDict["ServiceSDP"][0]] != "": InterfacesParse[InterfacesDict["ServiceSDP"][0]] = InterfacesParse[InterfacesDict["ServiceSDP"][0]] + "|"
                            InterfacesParse[InterfacesDict["ServiceSDP"][0]] = InterfacesParse[InterfacesDict["ServiceSDP"][0]] + obj3.text.split("xconnect ")[1].split()[0] + ":" + obj3.text.split("xconnect ")[1].split(" ")[1]

                            for obj4 in obj3.re_search_children(r"^ *mtu "):
                                if InterfacesParse[InterfacesDict["L2MTU"][0]] != "": InterfacesParse[InterfacesDict["L2MTU"][0]] = InterfacesParse[InterfacesDict["L2MTU"][0]] + "|"
                                InterfacesParse[InterfacesDict["L2MTU"][0]] = InterfacesParse[InterfacesDict["L2MTU"][0]] + obj4.text.split("mtu ")[1].split()[0]

                        InterfacesParse = [element.rstrip().lstrip() for element in InterfacesParse]
                        InterfacesParseAll.append(InterfacesParse)

#####################################################################################################################################################
###################################################                  Huawei VRP parsing               ###############################################
#####################################################################################################################################################
            # Syntax: Huawei VRP parsing
            if (CLISyntax == "VRP"):
                if debug: print("debug: Using Huawei VRP syntax to parse file")
                # Find node's interfaces from config
                for obj1 in cfg.find_objects(r"^interface"):
                    duplicate = []
                    for obj2 in cfg.find_objects(r"^interface"):
                        if obj1.text.split("interface ")[1].split(" ")[0] == obj2.text.split("interface ")[1].split(" ")[0]:
                            duplicate.append(str(obj2))

                    if len(duplicate) > 1:
                        print("File "+str(os.path.split(inputPath)[1])+" contains duplicate interface lines: "+str(duplicate)+", skipping this file")
                        nextFile = 1
                        break

                    IfNumber = IfNumber + 1
                    InterfacesParse = [""] * len(InterfacesDict)
                    if debug: print("debug: obj1: "+str(obj1))

                    InterfacesParse[InterfacesDict["NodeID"][0]] = NodeID
                    InterfacesParse[InterfacesDict["Hostname"][0]] = Hostname
                    InterfacesParse[InterfacesDict["CLISyntax"][0]] = CLISyntax
                    InterfacesParse[InterfacesDict["IfNumber"][0]] = str(IfNumber).zfill(4)
                    InterfacesParse[InterfacesDict["IfName"][0]] = obj1.text.split("interface ")[1].split(" ")[0]

                    # Check if interface is a subinterface of another one
                    if re.search(r'\.',InterfacesParse[InterfacesDict["IfName"][0]]):
                        InterfacesParse[InterfacesDict["ParentIfName"][0]] = InterfacesParse[InterfacesDict["IfName"][0]].split(".")[0]
                    else:
                        # Check if interface is physical port
                        if re.search(r'[Vv]irtual',InterfacesParse[InterfacesDict["IfName"][0]]) is None:
                            if re.search(r'([Gg]ig[Ee]|[Ee]thernet)',InterfacesParse[InterfacesDict["IfName"][0]]):
                                InterfacesParse[InterfacesDict["PortName"][0]] = InterfacesParse[InterfacesDict["IfName"][0]]
                                InterfacesParse[InterfacesDict["IfType"][0]] = "Port"
                                if re.search(r'[Hh]undred[Gg]igE',InterfacesParse[InterfacesDict["IfName"][0]]):
                                    InterfacesParse[InterfacesDict["PortType"][0]] = "100GE"
                                else:
                                    if re.search(r'[Tt]en[Gg]igE',InterfacesParse[InterfacesDict["IfName"][0]]):
                                        InterfacesParse[InterfacesDict["PortType"][0]] = "10GE"
                                    else:
                                        if re.search(r'[Gg]igabit',InterfacesParse[InterfacesDict["IfName"][0]]):
                                            InterfacesParse[InterfacesDict["PortType"][0]] = "1GE"
                                        else:
                                            if re.search(r'[Ff]ast',InterfacesParse[InterfacesDict["IfName"][0]]):
                                                InterfacesParse[InterfacesDict["PortType"][0]] = "100ME"
                                            else:
                                                InterfacesParse[InterfacesDict["PortType"][0]] = ""

                    # Check if interface is a bundle
                    if re.search(r'[Ee]th-[Tt]runk',InterfacesParse[InterfacesDict["IfName"][0]]):
                        InterfacesParse[InterfacesDict["LAGID"][0]] = str(InterfacesParse[InterfacesDict["IfName"][0]].split("runk")[1].split(".")[0])
                        InterfacesParse[InterfacesDict["IfType"][0]] = "LAG"

                    # Check if interface is L2 VC interface
                    if re.search(r'[Vv]irtual-[Ee]thernet',InterfacesParse[InterfacesDict["IfName"][0]]):
                        InterfacesParse[InterfacesDict["ServiceType"][0]] = "L2VPN"
                        if InterfacesParse[InterfacesDict["IfType"][0]] == "":
                            InterfacesParse[InterfacesDict["IfType"][0]] = "L2VPN SAP"
                            InterfacesParse[InterfacesDict["IfMode"][0]] = "Access"

                    # Check if interface is RSVP Tunnel interface
                    if re.search(r'Tunnel',InterfacesParse[InterfacesDict["IfName"][0]]):
                        InterfacesParse[InterfacesDict["IfType"][0]] = "RSVP Tunnel"
                        InterfacesParse[InterfacesDict["IfMode"][0]] = "Network"

                    # Find description associated with current interface
                    for obj2 in obj1.re_search_children("description "):
                        InterfacesParse[InterfacesDict["IfDescr"][0]] = str(obj2.text.split("description ")[1].replace("\"",""))
                        break

                    # Find encapsulation associated with current interface
                    for obj2 in obj1.re_search_children("vlan-type "):
                        InterfacesParse[InterfacesDict["Encap"][0]] = str(obj2.text.split("vlan-type ")[1].split(" ")[0])
                        InterfacesParse[InterfacesDict["VLAN"][0]] = str(obj2.text.split("vlan-type ")[1].split(" ")[1])
                        break

                    # Find LAG associated with current interface
                    for obj2 in obj1.re_search_children("eth-trunk "):
                        InterfacesParse[InterfacesDict["LAGID"][0]] = str(obj2.text.split("eth-trunk")[1])
                        for obj3 in cfg.find_objects(r"^interface [Ee]th-[Tt]runk"+str(InterfacesParse[InterfacesDict["LAGID"][0]]+"$")):
                            InterfacesParse[InterfacesDict["ParentIfName"][0]] = obj3.text.split("Eth-Trunk")[1]
                            break
                        break

                    # Find admin state associated with current interface
                    for obj2 in obj1.re_search_children(r"shutdown"):
                        if obj2.re_search(r"undo"):
                            InterfacesParse[InterfacesDict["StateAdm"][0]] = "En"
                        else:
                            InterfacesParse[InterfacesDict["StateAdm"][0]] = "Dis"

                    # Find L3VPN service associated with current interface
                    for obj2 in obj1.re_search_children("ip binding vpn-instance"):
                        InterfacesParse[InterfacesDict["ServiceName"][0]] = str(obj2.text.split("vpn-instance ")[1])
                        InterfacesParse[InterfacesDict["ServiceType"][0]] = "L3VPN"
                        if InterfacesParse[InterfacesDict["IfType"][0]] == "":
                            if re.search(r"[Ll]oop[Bb]ack",InterfacesParse[InterfacesDict["IfName"][0]]):
                                InterfacesParse[InterfacesDict["IfType"][0]] = "L3VPN Loopback"
                            else:
                                InterfacesParse[InterfacesDict["IfType"][0]] = "L3VPN SAP"
                                InterfacesParse[InterfacesDict["IfMode"][0]] = "Access"
                            break

                    # Check if interface is a non-VRF loopback
                    if InterfacesParse[InterfacesDict["ServiceName"][0]] == "":
                        if re.search(r"[Ll]oop[Bb]ack",InterfacesParse[InterfacesDict["IfName"][0]]):
                            InterfacesParse[InterfacesDict["IfType"][0]] = "Loopback"
                            InterfacesParse[InterfacesDict["IfMode"][0]] = "Network"

                    # Find L2 MTU associated with current interface
                    for obj2 in obj1.re_search_children(r"^ +mtu"):
                        InterfacesParse[InterfacesDict["L2MTU"][0]]  = str(obj2.text.split("mtu ")[1])
                        break

                    # Find L3 MTU associated with current interface
                    for obj2 in obj1.re_search_children(r"^ +ipv4 mtu"):
                        InterfacesParse[InterfacesDict["L3MTU"][0]]  = str(obj2.text.split("mtu ")[1])
                        break

                    # Find all IPv4 addresses associated with current interface
                    for obj2 in obj1.re_search_children("ip address "):
                        if re.search("ip address unnumbered interface", obj2.text):
                            InterfacesParse[InterfacesDict["ParentIfName"][0]] = obj2.text.split("unnumbered interface ")[1]
                            InterfacesParse[InterfacesDict["IPV4Addr"][0]] = InterfacesParse[InterfacesDict["ParentIfName"][0]]
                        else:
                            rawInput = obj2.text.split("ip address ")[1].split("sub")[0].lstrip().rstrip()
                            rawInput = rawInput.replace(" ","/")
                            ipadd = ipaddress.ip_interface(str(rawInput))
                            if InterfacesParse[InterfacesDict["IPV4Addr"][0]] == "":
                                InterfacesParse[InterfacesDict["IPV4Addr"][0]] = str(ipadd)
                            else:
                                InterfacesParse[InterfacesDict["IPV4Addr"][0]] = InterfacesParse[InterfacesDict["IPV4Addr"][0]] + "|" + str(ipadd)
                            if InterfacesParse[InterfacesDict["IPV4Subnet"][0]] == "":
                                InterfacesParse[InterfacesDict["IPV4Subnet"][0]] = str(ipadd.network)
                            else:
                                InterfacesParse[InterfacesDict["IPV4Subnet"][0]] = InterfacesParse[InterfacesDict["IPV4Subnet"][0]] + "|"+ str(ipadd.network)

                            # print(rawInput, ipadd, InterfacesParse[InterfacesDict["IPV4Addr"][0]],InterfacesParse[InterfacesDict["IPV4Subnet"][0]])
                            # input("Stop")


                        # Mark interface as Network/Hybrid if it has any addresses assigned
                        if InterfacesParse[InterfacesDict["IfType"][0]] == "":
                            InterfacesParse[InterfacesDict["IfType"][0]] = "L3"
                            InterfacesParse[InterfacesDict["IfMode"][0]] = "Network"


                    # Find all IPv6 addresses associated with current interface
                    for obj2 in obj1.re_search_children("ipv6 address "):
                        rawInput = obj2.text.split("ipv6 address ")[1].lstrip().rstrip()
                        ipadd = ipaddress.ip_interface(str(line))
                        if InterfacesParse[InterfacesDict["IPV6Addr"][0]] == "":
                            InterfacesParse[InterfacesDict["IPV6Addr"][0]] = str(ipadd)
                        else:
                            InterfacesParse[InterfacesDict["IPV6Addr"][0]] = InterfacesParse[InterfacesDict["IPV6Addr"][0]] + "|" + str(ipadd)
                        if InterfacesParse[InterfacesDict["IPV6Subnet"][0]] == "":
                            InterfacesParse[InterfacesDict["IPV6Subnet"][0]] = str(ipadd.network)
                        else:
                            InterfacesParse[InterfacesDict["IPV6Subnet"][0]] = InterfacesParse[InterfacesDict["IPV6Subnet"][0]] + "|" + str(ipadd.network)

                        # Mark interface as Network/Hybrid if it has any addresses assigned
                        if InterfacesParse[InterfacesDict["IfType"][0]] == "":
                            InterfacesParse[InterfacesDict["IfType"][0]] == "L3"
                            InterfacesParse[InterfacesDict["IfMode"][0]] = "Network"

                    # Find QoS input policy associated with current interface
                    for obj2 in obj1.re_search_children(r"^ *traffic-policy .* in"):
                        InterfacesParse[InterfacesDict["QoSIn"][0]] = str(obj2.text.split("traffic-policy ")[1].split(" ")[0])
                        break

                    # Find QoS output policy associated with current interface
                    for obj2 in obj1.re_search_children(r"^ *traffic-policy .* out"):
                        InterfacesParse[InterfacesDict["QoSOut"][0]] = str(obj2.text.split("traffic-policy ")[1].split(" ")[0])
                        break

                    # Find if SyncE enabled on current interface
                    # for obj2 in obj1.re_search_children("synchronization"):
                    #     InterfacesParse[InterfacesDict["SyncE"][0]] = "Enabled"
                    #     # Find SyncE configuration on current interface
                    #     for obj3 in obj2.re_search_children():
                    #         InterfacesParse[InterfacesDict["SyncE"][0]] = InterfacesParse[InterfacesDict["SyncE"][0]] + "|" + str(obj3.text)
                    #         break
                    #     break

                    # Find if LLDP is enabled on current interface
                    for obj2 in obj1.re_search_children("lldp"):
                        InterfacesParse[InterfacesDict["LLDP"][0]] = "En"
                        break


                    # Find all ISIS processes and areas where this interface is participating
                    isisList = []
                    bfdList = []

                    # Find all ISIS processes associated with interface
                    # for obj10 in obj1.re_search_children(r"isis"):
                    for obj10 in obj1.re_search_children(r"isis enable [0-9]+"):
                        isisLine = []
                        isisPID = ""
                        isisSID = ""
                        isisArea = ""
                        isisPID = str(obj10.text.split("isis enable ")[1].split(" ")[0])
                        isisLine.append(isisPID)

                        isisIfType1 = ""
                        isisIfType2 = "Bcast"
                        isisIfMode = "Act"
                        isisBFDState = "Dis"

                        bfdLine = []
                        isisBFDMinTxTmr = ""
                        isisBFDMinRxTmr = ""
                        isisBFDMultTmr = ""

                        isisLevelCapability = "L1/2"
                        isisL1Priority = ""
                        isisL2Priority = ""
                        isisL1Metric = ""
                        isisL2Metric = ""
                        isisL1Hello = ""
                        isisL2Hello = ""
                        isisL1HelloMult = ""
                        isisL2HelloMult = ""
                        isisRetransmit = ""
                        isisIfAuth = ""
                        isisL1Auth = ""
                        isisL2Auth = ""
                        isisIfState = "En"

                        bfdLine.append("isis")
                        bfdLine.append(isisPID)

                        # Find all ISIS interface parameters
                        for obj11 in obj1.re_search_children("isis circuit-type "):
                            isisIfType1 = str(obj11.text.split("isis circuit-type ")[1].split(" ")[0].lstrip().rstrip())
                            isisIfType2 = ""
                            if isisIfType1 == "p2p":
                                isisIfType2 = "PtP"
                            else:
                                isisIfType2 = isisIfType1
                            break

                        for obj11 in obj1.re_search_children("isis silent"):
                            isisIfMode = "Pass"
                            break

                        for obj100 in cfg.find_objects(r"^isis "+isisPID+r" *$"):
                            for obj110 in obj100.re_search_children("is-level "):
                                if re.match(r"^ *is-level *level-1$",obj110.text):
                                    isisLevelCapability = "L1"
                                else:
                                    if re.match(r"^ *is-level *level-2$",obj110.text):
                                        isisLevelCapability = "L2"
                                    else:
                                        if re.match(r"^ *is-level *level-1-2$",obj110.text):
                                            isisLevelCapability = "L1/2"
                                        else:
                                            isisLevelCapability = obj110.text.split("is-level  ")[1]
                                break
                            for obj101 in obj100.re_search_children("network-entity"):
                                isisSID = obj101.text.split("network-entity ")[1].split()[0].lstrip().rstrip()
                                break
                            for obj101 in obj100.re_search_children("bfd all-interfaces"):
                                if re.search(r"enable",obj101.text):
                                    isisBFDState = "En"
                                if re.search(r"min-tx-interval ",obj101.text):
                                    isisBFDMinTxTmr = obj101.text.lstrip().rstrip().split("min-tx-interval ")[1].split()[0]
                                if re.search(r"min-rx-interval ",obj101.text):
                                    isisBFDMinRxTmr = obj101.text.lstrip().rstrip().split("min-rx-interval ")[1].split()[0]
                                if re.search(r"detect-multiplier ",obj101.text):
                                    isisBFDMultTmr = obj101.text.lstrip().rstrip().split("detect-multiplier ")[1].split()[0]


                        isisLine.append(isisSID)
                        isisLine.append(isisArea)
                        isisLine.append(isisIfType2)
                        isisLine.append(isisIfMode)

                        for obj101 in obj1.re_search_children("bfd "):
                            if re.search(r"enable",obj101.text):
                                isisBFDState = "En"
                            if re.search(r"min-tx-interval ",obj101.text):
                                isisBFDMinTxTmr = obj101.text.lstrip().rstrip().split("min-tx-interval ")[1].split()[0]
                            if re.search(r"min-rx-interval ",obj101.text):
                                isisBFDMinRxTmr = obj101.text.lstrip().rstrip().split("min-rx-interval ")[1].split()[0]
                            if re.search(r"detect-multiplier ",obj101.text):
                                isisBFDMultTmr = obj101.text.lstrip().rstrip().split("detect-multiplier ")[1].split()[0]
                        isisLine.append(isisBFDState)

                        for obj11 in obj1.re_search_children("isis circuit-level "):
                            if re.match(r"^ *isis circuit-level *level-1$",obj11.text):
                                isisLevelCapability = "L1"
                            else:
                                if re.match(r"^ *isis circuit-level *level-2$",obj11.text):
                                    isisLevelCapability = "L2"
                                else:
                                    if re.match(r"^ *isis circuit-level *level-1-2$",obj11.text):
                                        isisLevelCapability = "L1/2"
                                    else:
                                        isisLevelCapability = obj11.text.split("level-capability ")[1]
                            break

                        for obj11 in obj1.re_search_children("isis timer lsp-retransmit "):
                            isisRetransmit = str(obj11.text.split("isis timer lsp-retransmit ")[1].split(" ")[0].lstrip().rstrip())
                            break

                        isisLine.append(isisLevelCapability)
                        isisLine.append(isisIfState)
                        isisLine.append(isisRetransmit)
                        isisLine.append(isisIfAuth)
                        bfdLine.append(isisBFDMinTxTmr)
                        bfdLine.append(isisBFDMinRxTmr)
                        bfdLine.append(isisBFDMultTmr)

                        for obj11 in obj1.re_search_children(r"isis dis-priority "):
                            if re.search(r"level-1",obj11.text):
                                isisL1Priority = str(obj11.text.split("isis dis-priority ")[1].split(" ")[0].lstrip().rstrip())
                            elif re.search(r"level-2",obj11.text):
                                isisL2Priority = str(obj11.text.split("isis dis-priority ")[1].split(" ")[0].lstrip().rstrip())
                            else:
                                isisL1Priority = str(obj11.text.split("isis dis-priority ")[1].split(" ")[0].lstrip().rstrip())
                                isisL2Priority = isisL1Priority
                            break

                        for obj11 in obj1.re_search_children("isis cost "):
                            if re.search(r"level-1",obj11.text):
                                isisL1Metric = str(obj11.text.split("isis cost ")[1].split(" ")[0].lstrip().rstrip())
                            elif re.search(r"level-2",obj11.text):
                                isisL2Metric = str(obj11.text.split("isis cost ")[1].split(" ")[0].lstrip().rstrip())
                            else:
                                isisL1Metric = str(obj11.text.split("isis cost ")[1].split(" ")[0].lstrip().rstrip())
                                isisL2Metric = isisL1Metric
                            break

                        for obj11 in obj1.re_search_children("isis timer hello "):
                            if re.search(r"level-1",obj11.text):
                                isisL1Hello = str(obj11.text.split("isis timer hello ")[1].split(" ")[0].lstrip().rstrip())
                            elif re.search(r"level-2",obj11.text):
                                isisL2Hello = str(obj11.text.split("isis timer hello ")[1].split(" ")[0].lstrip().rstrip())
                            else:
                                isisL1Hello = str(obj11.text.split("isis timer hello ")[1].split(" ")[0].lstrip().rstrip())
                                isisL2Hello = isisL1Hello
                            break

                        for obj11 in obj1.re_search_children("isis timer holding-multiplier "):
                            if re.search(r"level-1",obj11.text):
                                isisL1HelloMult = str(obj11.text.split("isis timer holding-multiplier ")[1].split(" ")[0].lstrip().rstrip())
                            elif re.search(r"level-2",obj11.text):
                                isisL2HelloMult = str(obj11.text.split("isis timer holding-multiplier ")[1].split(" ")[0].lstrip().rstrip())
                            else:
                                isisL1HelloMult = str(obj11.text.split("isis timer holding-multiplier ")[1].split(" ")[0].lstrip().rstrip())
                                isisL2HelloMult = isisL1HelloMult
                            break

                        for obj11 in obj1.re_search_children("isis authentication-mode "):
                            if re.search(r"level-1",obj11.text):
                                isisL1Auth = str(obj11.text.split("isis authentication-mode ")[1].split(" ")[0].lstrip().rstrip())
                            elif re.search(r"level-2",obj11.text):
                                isisL2Auth = str(obj11.text.split("isis authentication-mode ")[1].split(" ")[0].lstrip().rstrip())
                            else:
                                isisL1Auth = str(obj11.text.split("isis authentication-mode ")[1].split(" ")[0].lstrip().rstrip())
                                isisL2Auth = isisL1Auth
                            break

                        isisLine.append(isisL1Priority)
                        isisLine.append(isisL1Metric)
                        isisLine.append(isisL1Hello)
                        isisLine.append(isisL1HelloMult)
                        isisLine.append(isisL1Auth)

                        isisLine.append(isisL2Priority)
                        isisLine.append(isisL2Metric)
                        isisLine.append(isisL2Hello)
                        isisLine.append(isisL2HelloMult)
                        isisLine.append(isisL2Auth)

                        isisList.append(isisLine)
                        print(bfdLine)
                        bfdList.append(bfdLine)

                        if len(isisList) > 0:
                            isisOutputLine = ""
                            for isisLine in isisList:
                                # print(isisLine)
                                if isisOutputLine != "":
                                    isisOutputLine = isisOutputLine + ";"

                                isisOutputLine = isisOutputLine + "pid:"+str(isisLine[0])
                                if isisLine[1] != "": isisOutputLine = isisOutputLine + "|sid:"+str(isisLine[1])
                                isisOutputLine = isisOutputLine + "|area:"+str(isisLine[2]) + "|type:"+str(isisLine[3]) + "|mode:"+str(isisLine[4]) + "|bfd:"+str(isisLine[5]) + "|cap:"+str(isisLine[6]) + "|if_state:"+str(isisLine[7])
                                if isisLine[8] != "": isisOutputLine = isisOutputLine + "|retr:" + str(isisLine[8])
                                if isisLine[9] != "": isisOutputLine = isisOutputLine + "|if_auth:" + str(isisLine[9])
                                if isisLine[10] != "": isisOutputLine = isisOutputLine + "|l1_pri:" + str(isisLine[10])
                                if isisLine[15] != "": isisOutputLine = isisOutputLine + "|l2_pri:" + str(isisLine[15])
                                if isisLine[11] != "": isisOutputLine = isisOutputLine + "|l1_metr:" + str(isisLine[11])
                                if isisLine[16] != "": isisOutputLine = isisOutputLine + "|l2_metr:" + str(isisLine[16])
                                if ((isisLine[12] != "") or (isisLine[13] != "")):
                                    if isisLine[12] == "": isisLine[11] = "def"
                                    if isisLine[13] == "": isisLine[12] = "def"
                                    isisOutputLine = isisOutputLine + "|isis_l1_tmr:" + str(isisLine[12]) + " " + str(isisLine[13])
                                if ((isisLine[17] != "") or (isisLine[18] != "")):
                                    if isisLine[17] == "": isisLine[17] = "def"
                                    if isisLine[18] == "": isisLine[18] = "def"
                                    isisOutputLine = isisOutputLine + "|isis_l2_tmr:" + str(isisLine[17]) + " " + str(isisLine[18])
                                if isisLine[14] != "": isisOutputLine = isisOutputLine + "|l1_auth:" + str(isisLine[14])
                                if isisLine[19] != "": isisOutputLine = isisOutputLine + "|l2_auth:" + str(isisLine[19])

                            InterfacesParse[InterfacesDict["ISIS"][0]] = isisOutputLine

                            # Print BFD timers for each ISIS process where this interface is enabled
                            if len(bfdList) > 0:
                                bfdOutputLine = ""
                                for bfdLine in bfdList:
                                    if bfdOutputLine != "":
                                        bfdOutputLine = bfdOutputLine + ";"
                                    if (( bfdLine[2] != "" ) or ( bfdLine[3] != "" )):
                                        if bfdLine[2] == "": ospfLine[2] = "def"
                                        if bfdLine[3] == "": ospfLine[3] = "def"
                                        bfdOutputLine = bfdOutputLine + "type:"+str(bfdLine[0]) + "|pid:"+str(bfdLine[1]) + "|tmr:"+str(bfdLine[2])+" "+str(bfdLine[3])+" "+str(bfdLine[4])

                                InterfacesParse[InterfacesDict["BFD"][0]] = bfdOutputLine

                    # Find if BFD timers on current interface for OSPF
                    # BFD = ""
                    # for obj10 in cfg.find_objects(r"^router ospf"):
                    #     # print(obj10.text)
                    #     for obj11 in obj10.re_search_children("area"):
                    #         # print(obj11.text)
                    #         for obj12 in obj11.re_search_children(InterfacesParse[InterfacesDict["IfName"][0]]):
                    #             # print(obj12.text)
                    #             if ((obj10.re_search_children("^bfd fast-detect")) or (obj12.re_search_children("bfd fast-detect"))):
                    #                 obj13 = obj12.re_search_children("^bfd minimum-interval")[0]
                    #                 # print(obj13.text)
                    #                 if obj13:
                    #                     BFD = "OSPF " + obj10.text.split("ospf ")[1] + ":" + obj13.text.split("minimum-interval ")[1] + "|" + obj13.text.split("minimum-interval ")[1]
                    #                 else:
                    #                     BFD = "OSPF:100|100"
                    #                 obj13 = obj12.re_search_children("bfd multiplier")[0]
                    #                 if obj13:
                    #                     BFD = BFD + "|" + obj13.text.split("multiplier ")[1]
                    #                 else:
                    #                     BFD = BFD + "|3"

                    #     for obj11 in obj10.re_search_children("vrf"):
                    #         # print(obj11.text)
                    #         for obj12 in obj11.re_search_children("area"):
                    #             # print(obj12.text)
                    #             for obj13 in obj12.re_search_children(InterfacesParse[InterfacesDict["IfName"][0]]):
                    #                 # print(obj13.text)
                    #                 if ((obj10.re_search_children("bfd fast-detect")) or (obj13.re_search_children("bfd fast-detect"))):
                    #                     obj14 = obj13.re_search_children("bfd minimum-interval")[0]
                    #                     # print(obj14.text)
                    #                     if obj14:
                    #                         BFD = "OSPF " + obj10.text.split("ospf ")[1] + ":" + obj14.text.split("minimum-interval ")[1] + "|" + obj14.text.split("minimum-interval ")[1]
                    #                     else:
                    #                         BFD = "OSPF:100|100"
                    #                     obj14 = obj13.re_search_children("bfd multiplier")[0]
                    #                     if obj14:
                    #                         BFD = BFD + "|" + obj14.text.split("multiplier ")[1]
                    #                     else:
                    #                         BFD = BFD + "|3"


                    # if InterfacesParse[InterfacesDict["BFD"][0]] == "":
                    #     InterfacesParse[InterfacesDict["BFD"][0]] = BFD
                    # else:
                    #     InterfacesParse[InterfacesDict["BFD"][0]] = InterfacesParse[InterfacesDict["BFD"][0]] + "," + BFD

                    InterfacesParse = [element.rstrip().lstrip() for element in InterfacesParse]
                    InterfacesParseAll.append(InterfacesParse)


#####################################################################################################################################################
###################################################                Nokia/ALU SR-OS parsing                 ##########################################
#####################################################################################################################################################
            # Syntax: Nokia/ALU SR-OS
            if (CLISyntax == "SR-OS"):
                if debug: print("debug: Using SR-OS syntax to parse file")

                # Enter "config" domain section
                for obj1 in cfg.find_objects(r"^configure"):

                    # Find node's ports from config
                    for obj2 in obj1.re_search_children(r" +port +"):
                        duplicate = []
                        for obj3 in obj1.re_search_children(r" +port +"):
                            if obj3.text.split("port ")[1] == obj2.text.split("port ")[1]:
                                duplicate.append(str(obj3))

                        if len(duplicate) > 1:
                            print("File "+str(os.path.split(inputPath)[1])+" contains duplicate port lines: "+str(duplicate)+", skipping this file")
                            nextFile = 1
                            break

                        IfNumber = IfNumber + 1
                        if debug: print("debug: obj2: "+str(obj2))

                        InterfacesParse = [""] * len(InterfacesDict)
                        InterfacesParse[InterfacesDict["NodeID"][0]] = NodeID
                        InterfacesParse[InterfacesDict["Hostname"][0]] = Hostname
                        InterfacesParse[InterfacesDict["CLISyntax"][0]] = CLISyntax
                        InterfacesParse[InterfacesDict["IfNumber"][0]] = str(IfNumber).zfill(4)
                        InterfacesParse[InterfacesDict["IfName"][0]] = obj2.text.split("port ")[1]
                        InterfacesParse[InterfacesDict["PortName"][0]] = InterfacesParse[InterfacesDict["IfName"][0]]

                        # Check if interface is connector
                        if re.search(r'.*/c[0-9]+$',InterfacesParse[InterfacesDict["IfName"][0]]):
                            InterfacesParse[InterfacesDict["IfType"][0]] = "Connector"
                        else:
                            InterfacesParse[InterfacesDict["IfType"][0]] = "Port"


                        # Find description associated with current port
                        for obj3 in obj2.re_search_children("description "):
                            InterfacesParse[InterfacesDict["IfDescr"][0]] = str(obj3.text.split("description ")[1].replace("\"",""))
                            break

                        # Find admin state associated with current port
                        for obj3 in obj2.re_search_children(r"shutdown"):
                            if obj3.re_search(r"no "):
                                InterfacesParse[InterfacesDict["StateAdm"][0]] = "En"
                            else:
                                InterfacesParse[InterfacesDict["StateAdm"][0]] = "Dis"

                        for obj3 in obj2.re_search_children("ethernet"):
                            # Get port mode
                            for obj4 in obj3.re_search_children("mode"):
                                # print(obj4)
                                if obj4.text.split("mode ")[1] == "hybrid":
                                    InterfacesParse[InterfacesDict["IfMode"][0]] = "Hybrid"
                                if obj4.text.split("mode ")[1] == "network":
                                    InterfacesParse[InterfacesDict["IfMode"][0]] = "Network"
                                if obj4.text.split("mode ")[1] == "access":
                                    InterfacesParse[InterfacesDict["IfMode"][0]] = "Access"
                                break

                            # Get port speed
                            for obj4 in obj3.re_search_children("speed"):
                                # print(obj4)
                                tempSpeed = obj4.text.split("speed")[1].rstrip().lstrip()
                                if tempSpeed == "100":
                                    InterfacesParse[InterfacesDict["PortType"][0]] = "100ME"
                                if tempSpeed == "1000":
                                    InterfacesParse[InterfacesDict["PortType"][0]] = "1GE"
                                if tempSpeed == "10000":
                                    InterfacesParse[InterfacesDict["PortType"][0]] = "10GE"
                                if tempSpeed == "100000":
                                    InterfacesParse[InterfacesDict["PortType"][0]] = "100GE"
                                break

                            # Get port encapsulation
                            for obj4 in obj3.re_search_children("encap-type"):
                                # print(obj4)
                                InterfacesParse[InterfacesDict["Encap"][0]] = obj4.text.split("encap-type ")[1]
                                break

                            # Get all VLANs associated with this port
                            # searchExpression = r"(sap " + InterfacesParse[InterfacesDict["IfName"][0]] + r"(:.*| )create|port " + InterfacesParse[InterfacesDict["IfName"][0]] + "(:|$))"
                            # (sap 1/1/14(:.*| )create|port 1/1/1(:|$))
                            searchExpression1 = r"port " + InterfacesParse[InterfacesDict["IfName"][0]] + r"(:|$)"
                            for obj19 in cfg.find_objects(r" *router"):
                                for obj20 in obj19.re_search_children(r" *interface"):
                                    for obj21 in obj20.re_search_children(searchExpression1):
                                        tempVLAN = ""
                                        if re.search(":",obj21.text):
                                            tempVLAN = obj21.text.split(":")[1].split(" ")[0]
                                        else:
                                            tempVLAN = "null"

                                        if InterfacesParse[InterfacesDict["VLAN"][0]] != "": InterfacesParse[InterfacesDict["VLAN"][0]] = InterfacesParse[InterfacesDict["VLAN"][0]] + "|"
                                        InterfacesParse[InterfacesDict["VLAN"][0]] = InterfacesParse[InterfacesDict["VLAN"][0]] + tempVLAN

                            searchExpression2 = r"sap " + InterfacesParse[InterfacesDict["IfName"][0]] + r"(:.*| )create"
                            for obj22 in cfg.find_objects(searchExpression2):
                                # print(obj20)
                                tempVLAN = ""
                                if re.search(":",obj22.text):
                                    tempVLAN = obj22.text.split(":")[1].split(" ")[0]
                                else:
                                    tempVLAN = "null"

                                if InterfacesParse[InterfacesDict["VLAN"][0]] != "": InterfacesParse[InterfacesDict["VLAN"][0]] = InterfacesParse[InterfacesDict["VLAN"][0]] + "|"
                                InterfacesParse[InterfacesDict["VLAN"][0]] = InterfacesParse[InterfacesDict["VLAN"][0]] + tempVLAN


                            # Find LAG associated with this port
                            for obj10 in obj1.re_search_children(r" +lag +"):
                                for obj11 in obj10.re_search_children(r" +port +"):
                                    # print(obj11)
                                    if obj11.text.split("port ")[1] == InterfacesParse[InterfacesDict["IfName"][0]]:
                                        InterfacesParse[InterfacesDict["LAGID"][0]] = obj10.text.split("lag ")[1]
                                        InterfacesParse[InterfacesDict["ParentIfName"][0]] = obj10.text
                                        break

                            # Find L2 MTU parameters associated with current port
                            for obj4 in obj3.re_search_children(r"mtu"):
                                InterfacesParse[InterfacesDict["L2MTU"][0]] = obj4.text.split("mtu ")[1]
                                break

                            # Get port LLDP state
                            for obj4 in obj3.re_search_children("lldp"):
                                # print(obj4)
                                InterfacesParse[InterfacesDict["LLDP"][0]] = "En"
                                break

                            # Get port egress QoS policy
                            for obj4 in obj3.re_search_children("egress-port-qos-policy"):
                                # print(obj4)
                                InterfacesParse[InterfacesDict["QoSOut"][0]] = obj4.text.split("egress-port-qos-policy ")[1].replace("\"","")
                                break

                            # Get port ingress QoS policy
                            for obj4 in obj3.re_search_children("ingress-port-qos-policy"):
                                # print(obj4)
                                InterfacesParse[InterfacesDict["QoSIn"][0]] = obj4.text.split("ingress-port-qos-policy ")[1].replace("\"","")
                                break
                        # print(InterfacesParse)




                        #########################################################################################################################################
                        #                                                    Post-processing for ports                                                     #
                        #########################################################################################################################################

                        # Sort VLANs for Ports
                        if re.search(r"Port",InterfacesParse[InterfacesDict["IfType"][0]]):
                            if re.search(r"\|",InterfacesParse[InterfacesDict["VLAN"][0]]):
                                VLANList = []
                                for value in InterfacesParse[InterfacesDict["VLAN"][0]].split("|"):
                                    if re.search(r"\*",value):
                                        value = value.replace("*","9999")
                                    VLANList.append(value)
                                VLANList = sorted(VLANList, key=float)

                                InterfacesParse[InterfacesDict["VLAN"][0]] = ""
                                # VLANList = VLANList.sort()
                                # print(VLANList)
                                for value in VLANList:
                                    if re.search("9999",value):
                                        value = value.replace("9999","*")
                                    if InterfacesParse[InterfacesDict["VLAN"][0]] != "": InterfacesParse[InterfacesDict["VLAN"][0]] = InterfacesParse[InterfacesDict["VLAN"][0]] + "|"
                                    InterfacesParse[InterfacesDict["VLAN"][0]] = InterfacesParse[InterfacesDict["VLAN"][0]] + str(value)



                        InterfacesParse = [element.rstrip().lstrip() for element in InterfacesParse]
                        InterfacesParseAll.append(InterfacesParse)



                    # Find node's LAGs from config
                    for obj2 in obj1.re_search_children(r" +lag +"):
                        duplicate = []
                        for obj3 in obj1.re_search_children(r" +lag +"):
                            if obj3.text.lstrip().rstrip() == obj2.text.lstrip().rstrip():
                                duplicate.append(str(obj3))

                        if len(duplicate) > 1:
                            print("File "+str(os.path.split(inputPath)[1])+" contains duplicate port lines: "+str(duplicate)+", skipping this file")
                            nextFile = 1
                            break

                        IfNumber = IfNumber + 1
                        if debug: print("debug: obj2: "+str(obj2))

                        InterfacesParse = [""] * len(InterfacesDict)
                        InterfacesParse[InterfacesDict["NodeID"][0]] = NodeID
                        InterfacesParse[InterfacesDict["Hostname"][0]] = Hostname
                        InterfacesParse[InterfacesDict["CLISyntax"][0]] = CLISyntax
                        InterfacesParse[InterfacesDict["IfNumber"][0]] = str(IfNumber).zfill(4)
                        InterfacesParse[InterfacesDict["IfName"][0]] = obj2.text.lstrip().rstrip()
                        InterfacesParse[InterfacesDict["LAGID"][0]] = InterfacesParse[InterfacesDict["IfName"][0]].split("lag ")[1]
                        InterfacesParse[InterfacesDict["PortName"][0]] = str("lag-"+InterfacesParse[InterfacesDict["LAGID"][0]])
                        InterfacesParse[InterfacesDict["IfType"][0]] = "LAG"

                        # Find description associated with current LAG
                        for obj3 in obj2.re_search_children("description "):
                            InterfacesParse[InterfacesDict["IfDescr"][0]] = str(obj3.text.split("description ")[1].replace("\"",""))
                            break

                        # Find admin state associated with current LAG
                        for obj3 in obj2.re_search_children(r"shutdown"):
                            if obj3.re_search(r"no "):
                                InterfacesParse[InterfacesDict["StateAdm"][0]] = "En"
                            else:
                                InterfacesParse[InterfacesDict["StateAdm"][0]] = "Dis"

                        # Find mode associated with current LAG
                        for obj3 in obj2.re_search_children("mode"):
                            # print(obj3)
                            if obj3.text.split("mode ")[1] == "hybrid":
                                InterfacesParse[InterfacesDict["IfMode"][0]] = "Hybrid"
                            if obj3.text.split("mode ")[1] == "network":
                                InterfacesParse[InterfacesDict["IfMode"][0]] = "Network"
                            if obj3.text.split("mode ")[1] == "access":
                                InterfacesParse[InterfacesDict["IfMode"][0]] = "Access"
                            break

                        # Get LAG encapsulation
                        for obj3 in obj2.re_search_children("encap-type"):
                            # print(obj3)
                            InterfacesParse[InterfacesDict["Encap"][0]] = obj3.text.split("encap-type ")[1]
                            break

                        # Get LACP mode
                        for obj3 in obj2.re_search_children("lacp"):
                            # print(obj3)
                            if obj3.re_search(r"active"):
                                InterfacesParse[InterfacesDict["LAGMode"][0]] = "Active"
                            else:
                                if obj3.re_search(r"passive"):
                                    InterfacesParse[InterfacesDict["LAGMode"][0]] = "Passive"
                            break

                        # Get all VLANs associated with this LAG
                        # searchExpression = r"(sap " + InterfacesParse[InterfacesDict["IfName"][0]] + r"(:.*| )create|port " + InterfacesParse[InterfacesDict["IfName"][0]] + "(:|$))"
                        # (sap 1/1/14(:.*| )create|port 1/1/1(:|$))
                        searchExpression1 = r"port " + InterfacesParse[InterfacesDict["IfName"][0]].replace(" ","-") + r"(:|$)"
                        for obj19 in cfg.find_objects(r" *router"):
                            for obj20 in obj19.re_search_children(r" *interface"):
                                for obj21 in obj20.re_search_children(searchExpression1):
                                    tempVLAN = ""
                                    if re.search(":",obj21.text):
                                        tempVLAN = obj21.text.split(":")[1].split(" ")[0]
                                    else:
                                        tempVLAN = "null"

                                    if InterfacesParse[InterfacesDict["VLAN"][0]] != "": InterfacesParse[InterfacesDict["VLAN"][0]] = InterfacesParse[InterfacesDict["VLAN"][0]] + "|"
                                    InterfacesParse[InterfacesDict["VLAN"][0]] = InterfacesParse[InterfacesDict["VLAN"][0]] + tempVLAN

                        searchExpression2 = r"sap " + InterfacesParse[InterfacesDict["IfName"][0]].replace(" ","-") + r"(:.*| )create"
                        for obj22 in cfg.find_objects(searchExpression2):
                            # print(obj20)
                            tempVLAN = ""
                            if re.search(":",obj22.text):
                                tempVLAN = obj22.text.split(":")[1].split(" ")[0]
                            else:
                                tempVLAN = "null"

                            if InterfacesParse[InterfacesDict["VLAN"][0]] != "": InterfacesParse[InterfacesDict["VLAN"][0]] = InterfacesParse[InterfacesDict["VLAN"][0]] + "|"
                            InterfacesParse[InterfacesDict["VLAN"][0]] = InterfacesParse[InterfacesDict["VLAN"][0]] + tempVLAN

                        #########################################################################################################################################
                        #                                                    Post-processing for LAGs                                                     #
                        #########################################################################################################################################

                        # Sort VLANs for LAGs
                        if re.search(r"LAG",InterfacesParse[InterfacesDict["IfType"][0]]):
                            if re.search(r"\|",InterfacesParse[InterfacesDict["VLAN"][0]]):
                                VLANList = []
                                for value in InterfacesParse[InterfacesDict["VLAN"][0]].split("|"):
                                    if re.search(r"\*",value):
                                        value = value.replace("*","9999")
                                    VLANList.append(value)
                                VLANList = sorted(VLANList, key=float)

                                InterfacesParse[InterfacesDict["VLAN"][0]] = ""
                                for value in VLANList:
                                    if re.search("9999",value):
                                        value = value.replace("9999","*")
                                    if InterfacesParse[InterfacesDict["VLAN"][0]] != "": InterfacesParse[InterfacesDict["VLAN"][0]] = InterfacesParse[InterfacesDict["VLAN"][0]] + "|"
                                    InterfacesParse[InterfacesDict["VLAN"][0]] = InterfacesParse[InterfacesDict["VLAN"][0]] + str(value)


                        # print(InterfacesParse)
                        InterfacesParse = [element.rstrip().lstrip() for element in InterfacesParse]
                        InterfacesParseAll.append(InterfacesParse)

                    # Find node's network interfaces from config
                    for obj2 in obj1.re_search_children(r"router Base"):
                        for obj3 in obj2.re_search_children(r"interface"):
                            duplicate = []
                            for obj4 in obj2.re_search_children(r"interface"):
                                if obj4.text.split("interface ")[1] == obj3.text.split("interface ")[1]:
                                    duplicate.append(str(obj3))

                            if len(duplicate) > 1:
                                print("File "+str(os.path.split(inputPath)[1])+" contains duplicate interface lines: "+str(duplicate)+", skipping this file")
                                nextFile = 1
                                break

                            IfNumber = IfNumber + 1
                            if debug: print("debug: obj3: "+str(obj3))

                            InterfacesParse = [""] * len(InterfacesDict)
                            InterfacesParse[InterfacesDict["NodeID"][0]] = NodeID
                            InterfacesParse[InterfacesDict["Hostname"][0]] = Hostname
                            InterfacesParse[InterfacesDict["CLISyntax"][0]] = CLISyntax
                            InterfacesParse[InterfacesDict["IfNumber"][0]] = str(IfNumber).zfill(4)
                            InterfacesParse[InterfacesDict["IfName"][0]] = obj3.text.split("interface ")[1].replace("\"","")
                            InterfacesParse[InterfacesDict["IfMode"][0]] = "Network"

                            # Check if interface is a system or loopback interface
                            if re.match(r'system',InterfacesParse[InterfacesDict["IfName"][0]]):
                                InterfacesParse[InterfacesDict["IfType"][0]] = "Loopback"
                            else:
                                for obj4 in obj3.re_search_children("loopback"):
                                    InterfacesParse[InterfacesDict["IfType"][0]] = "Loopback"
                                    break

                            # Find description associated with current interface
                            for obj4 in obj3.re_search_children("description "):
                                InterfacesParse[InterfacesDict["IfDescr"][0]] = str(obj4.text.split("description ")[1].replace("\"",""))
                                break

                            # Find admin state associated with current interface
                            for obj4 in obj3.re_search_children(r"shutdown"):
                                if obj4.re_search(r"no "):
                                    InterfacesParse[InterfacesDict["StateAdm"][0]] = "En"
                                else:
                                    InterfacesParse[InterfacesDict["StateAdm"][0]] = "Dis"

                            # Find BFD parameters associated with current interface
                            for obj4 in obj3.re_search_children(r"bfd"):
                                InterfacesParse[InterfacesDict["BFD"][0]] = "if_tmr:" + obj4.text.lstrip().rstrip().replace("bfd ","").replace(" receive "," ").replace(" multiplier "," ").replace(" type "," ")
                                break

                            # Find all IPv4 addresses associated with current interface
                            for obj4 in obj3.re_search_children(r"^ *address "):
                                rawInput = obj4.text.split("address ")[1].lstrip().rstrip()
                                rawInput = rawInput.replace(" ","/")
                                ipadd = ipaddress.ip_interface(str(rawInput))
                                if InterfacesParse[InterfacesDict["IPV4Addr"][0]] == "":
                                    InterfacesParse[InterfacesDict["IPV4Addr"][0]] = str(ipadd)
                                else:
                                    InterfacesParse[InterfacesDict["IPV4Addr"][0]] = InterfacesParse[InterfacesDict["IPV4Addr"][0]] + "|" + str(ipadd)
                                if InterfacesParse[InterfacesDict["IPV4Subnet"][0]] == "":
                                    InterfacesParse[InterfacesDict["IPV4Subnet"][0]] = str(ipadd.network)
                                else:
                                    InterfacesParse[InterfacesDict["IPV4Subnet"][0]] = InterfacesParse[InterfacesDict["IPV4Subnet"][0]] + "|"+ str(ipadd.network)

                            # Find all IPv6 addresses associated with current interface
                            for obj4 in obj3.re_search_children(r"^ *ipv6 address "):
                                rawInput = obj4.text.split("ipv6 address ")[1].lstrip().rstrip()
                                ipadd = ipaddress.ip_interface(str(line))
                                if InterfacesParse[InterfacesDict["IPV6Addr"][0]] == "":
                                    InterfacesParse[InterfacesDict["IPV6Addr"][0]] = str(ipadd)
                                else:
                                    InterfacesParse[InterfacesDict["IPV6Addr"][0]] = InterfacesParse[InterfacesDict["IPV6Addr"][0]] + "|" + str(ipadd)
                                if InterfacesParse[InterfacesDict["IPV6Subnet"][0]] == "":
                                    InterfacesParse[InterfacesDict["IPV6Subnet"][0]] = str(ipadd.network)
                                else:
                                    InterfacesParse[InterfacesDict["IPV6Subnet"][0]] = InterfacesParse[InterfacesDict["IPV6Subnet"][0]] + "|" + str(ipadd.network)


                            # Check if interface is a L3 interface
                            if ((InterfacesParse[InterfacesDict["IPV4Addr"][0]] != "") or (InterfacesParse[InterfacesDict["IPV6Addr"][0]] != "")):
                                # Mark interface as Network/Hybrid if it has any IPv4/v6 addresses assigned
                                if InterfacesParse[InterfacesDict["IfType"][0]] == "":
                                    InterfacesParse[InterfacesDict["IfType"][0]] = "L3"
                                # if ((InterfacesParse[InterfacesDict["IfType"][0]] == "Port") or (InterfacesParse[InterfacesDict["IfType"][0]] == "LAG") or (InterfacesParse[InterfacesDict["IfType"][0]] == "Bridge")):
                                else:
                                    InterfacesParse[InterfacesDict["IfType"][0]] = InterfacesParse[InterfacesDict["IfType"][0]] + "|L3"

                            # Find L3 MTU parameters associated with current interface
                            for obj4 in obj3.re_search_children(r"ip-mtu"):
                                InterfacesParse[InterfacesDict["L3MTU"][0]] = obj4.text.split("ip-mtu ")[1]
                                break

                            # Find QoS input policy associated with current interface
                            for obj4 in obj3.re_search_children(r"^ *ingress"):
                                for obj5 in obj4.re_search_children(r"(.*qos.*)|(.*remark.*)"):
                                    if InterfacesParse[InterfacesDict["QoSIn"][0]] == "":
                                        InterfacesParse[InterfacesDict["QoSIn"][0]] = obj5.text.lstrip().rstrip().split(" ")[1].replace("\"","")
                                    else:
                                        InterfacesParse[InterfacesDict["QoSIn"][0]] = InterfacesParse[InterfacesDict["QoSIn"][0]] + "|" + obj5.text.lstrip().rstrip().split(" ")[1].replace("\"","")

                            # Find QoS output policy associated with current interface
                            for obj4 in obj3.re_search_children(r"^ *egress"):
                                for obj5 in obj4.re_search_children(r"(.*qos.*)|(.*remark.*)"):
                                    if InterfacesParse[InterfacesDict["QoSOut"][0]] == "":
                                        InterfacesParse[InterfacesDict["QoSOut"][0]] = obj5.text.lstrip().rstrip().split(" ")[1].replace("\"","")
                                    else:
                                        InterfacesParse[InterfacesDict["QoSOut"][0]] = InterfacesParse[InterfacesDict["QoSOut"][0]] + "|" + obj5.text.lstrip().rstrip().split(" ")[1].replace("\"","")

                            # Find port/LAG associated with current interface
                            for obj4 in obj3.re_search_children(r"^ *port"):
                                # print(obj4.text)
                                InterfacesParse[InterfacesDict["PortBinding"][0]] = obj4.text.split("port ")[1]
                                if obj4.re_search(r":"):
                                    InterfacesParse[InterfacesDict["PortName"][0]] = InterfacesParse[InterfacesDict["PortBinding"][0]].split(":")[0]
                                    InterfacesParse[InterfacesDict["VLAN"][0]] = InterfacesParse[InterfacesDict["PortBinding"][0]].split(":")[1]
                                    if obj4.re_search(r"\."):
                                        InterfacesParse[InterfacesDict["Encap"][0]] = "qinq"
                                    else:
                                        InterfacesParse[InterfacesDict["Encap"][0]] = "dot1q"
                                else:
                                    InterfacesParse[InterfacesDict["Encap"][0]] = "null"
                                    InterfacesParse[InterfacesDict["PortName"][0]] = InterfacesParse[InterfacesDict["PortBinding"][0]]

                                if obj4.re_search(r"lag-"):
                                    # InterfacesParse[InterfacesDict["LAGID"][0]] = InterfacesParse[InterfacesDict["PortName"][0]].split("lag-")[1]
                                    # InterfacesParse[InterfacesDict["ParentIfName"][0]] = "lag " + InterfacesParse[InterfacesDict["LAGID"][0]]
                                    InterfacesParse[InterfacesDict["ParentIfName"][0]] = "lag " + InterfacesParse[InterfacesDict["PortName"][0]].split("lag-")[1]
                                else:
                                    InterfacesParse[InterfacesDict["ParentIfName"][0]] = InterfacesParse[InterfacesDict["PortName"][0]]


                            # Find all OSPF processes and areas where this interface is participating
                            ospfList = []
                            # Find all OSPF processes associated with interface
                            for obj10 in obj2.re_search_children(r"ospf "):
                                ospfLine = []
                                ospfPID = ""
                                ospfRID = ""
                                ospfPID = str(obj10.text.split("ospf ")[1].split()[0])
                                ospfLine.append(ospfPID)

                                if len(obj10.text.split("ospf ")[1].split()) > 1:
                                    ospfRID = str(obj10.text.split("ospf ")[1].split()[1])
                                ospfLine.append(ospfRID)

                                # First we will look for the area where interface is primary
                                ospfIfType1 = ""
                                ospfIfType2 = "Bcast"
                                ospfIfMode = "Act"
                                ospfBFDState = "Dis"
                                ospfPriority = ""
                                ospfMetric = ""
                                ospfHello = ""
                                ospfDead = ""
                                ospfRetransmit = ""
                                ospfAuth = ""
                                ospfIfState = "Dis"

                                area = ""
                                # Look through all OSPF areas
                                for obj11 in obj10.re_search_children(r"area "):
                                    area = obj11.text.split("area ")[1]
                                    area = ipaddress.ip_address(area)

                                    # Find current interface configured as primary within an area
                                    searchExpression = r"\""+ InterfacesParse[InterfacesDict["IfName"][0]] + r"\""
                                    for obj12 in obj11.re_search_children(searchExpression):
                                        if re.search(r"secondary",obj12.text):
                                            continue
                                        else:
                                            # Find all OSPF parameters for this primary interface
                                            for obj13 in obj12.re_search_children("interface-type "):
                                                ospfIfType1 = str(obj13.text.split("interface-type ")[1].split(" ")[0].lstrip().rstrip())
                                                ospfIfType2 = ""
                                                if ospfIfType1 == "point-to-point":
                                                    ospfIfType2 = "PtP"
                                                else:
                                                    if ospfIfType1 == "point-to-multipoint":
                                                        ospfIfType2 = "PtMP"
                                                    else:
                                                        ospfIfType2 = ospfIfType1
                                                break
                                            ospfLine.append(ospfIfType2)
                                            for obj13 in obj12.re_search_children("passive"):
                                                if re.match(r"^ *passive *$",obj13.text):
                                                    ospfIfMode = "Pass"
                                                if re.match(r"^ *no passive *$",obj13.text):
                                                    ospfIfMode = "Act"
                                                break
                                            ospfLine.append(ospfIfMode)
                                            for obj13 in obj12.re_search_children("bfd-enable"):
                                                if re.match(r"^ *bfd-enable *$",obj13.text):
                                                    ospfBFDState = "En"
                                                if re.match(r"^ *no bfd-enable *$",obj13.text):
                                                    ospfBFDState = "Dis"
                                                break
                                            ospfLine.append(ospfBFDState)
                                            for obj13 in obj12.re_search_children("priority "):
                                                ospfPriority = str(obj13.text.split("priority ")[1].split(" ")[0].lstrip().rstrip())
                                                break
                                            ospfLine.append(ospfPriority)
                                            for obj13 in obj12.re_search_children("metric "):
                                                ospfMetric = str(obj13.text.split("metric ")[1].split(" ")[0].lstrip().rstrip())
                                                break
                                            ospfLine.append(ospfMetric)
                                            for obj13 in obj12.re_search_children("hello-interval "):
                                                ospfHello = str(obj13.text.split("hello-interval ")[1].split(" ")[0].lstrip().rstrip())
                                                break
                                            ospfLine.append(ospfHello)
                                            for obj13 in obj12.re_search_children("dead-interval "):
                                                ospfDead = str(obj13.text.split("dead-interval ")[1].split(" ")[0].lstrip().rstrip())
                                                break
                                            ospfLine.append(ospfDead)
                                            for obj13 in obj12.re_search_children("retransmit-interval "):
                                                ospfRetransmit = str(obj13.text.split("retransmit-interval ")[1].split(" ")[0].lstrip().rstrip())
                                                break
                                            ospfLine.append(ospfRetransmit)
                                            for obj13 in obj12.re_search_children("authentication-type "):
                                                ospfAuth = str(obj13.text.split("authentication-type ")[1].split(" ")[0].lstrip().rstrip())
                                                break
                                            ospfLine.append(ospfAuth)
                                            for obj13 in obj12.re_search_children("no shutdown"):
                                                ospfIfState = "En"
                                                break

                                            ospfAreaList = []
                                            ospfAreaList.append([int(area),"*",""])
                                            if ospfIfState == "Dis":
                                                ospfAreaList[0][2] = "(Dis)"
                                            else:
                                                ospfAreaList[0][2] = ""

                                            ospfLine.append(ospfAreaList)

                                            ospfList.append(ospfLine)

                                            break

                                # Now we will look for all other areas where interface is secondary

                                area = ""
                                # Look through all OSPF areas
                                for obj11 in obj10.re_search_children(r"area "):
                                    area = obj11.text.split("area ")[1]
                                    area = ipaddress.ip_address(area)

                                    ospfLine = []
                                    ospfBFDState = "Dis"
                                    ospfPriority = ""
                                    ospfMetric = ""
                                    ospfHello = ""
                                    ospfDead = ""
                                    ospfRetransmit = ""
                                    ospfAuth = ""
                                    ospfIfState = "Dis"

                                    # Find current interface configured as secondary within an area
                                    searchExpression = r"\""+ InterfacesParse[InterfacesDict["IfName"][0]] + r"\""
                                    for obj12 in obj11.re_search_children(searchExpression):
                                        if re.search(r"secondary",obj12.text):
                                            # Find all OSPF parameters for this secondary interface
                                            ospfLine.append(ospfPID)        # Set to same value as on primary configuration
                                            ospfLine.append(ospfRID)        # Set to same value as on primary configuration
                                            ospfLine.append(ospfIfType2)    # Set to same value as on primary configuration
                                            ospfLine.append(ospfIfMode)     # Set to same value as on primary configuration
                                            for obj13 in obj12.re_search_children("bfd-enable"):
                                                if re.match(r"^ *bfd-enable *$",obj13.text):
                                                    ospfBFDState = "En"
                                                if re.match(r"^ *no bfd-enable *$",obj13.text):
                                                    ospfBFDState = "Dis"
                                                break
                                            ospfLine.append(ospfBFDState)
                                            for obj13 in obj12.re_search_children("priority "):
                                                ospfPriority = str(obj13.text.split("priority ")[1].split(" ")[0].lstrip().rstrip())
                                                break
                                            ospfLine.append(ospfPriority)
                                            for obj13 in obj12.re_search_children("metric "):
                                                ospfMetric = str(obj13.text.split("metric ")[1].split(" ")[0].lstrip().rstrip())
                                                break
                                            ospfLine.append(ospfMetric)
                                            for obj13 in obj12.re_search_children("hello-interval "):
                                                ospfHello = str(obj13.text.split("hello-interval ")[1].split(" ")[0].lstrip().rstrip())
                                                break
                                            ospfLine.append(ospfHello)
                                            for obj13 in obj12.re_search_children("dead-interval "):
                                                ospfDead = str(obj13.text.split("dead-interval ")[1].split(" ")[0].lstrip().rstrip())
                                                break
                                            ospfLine.append(ospfDead)
                                            for obj13 in obj12.re_search_children("retransmit-interval "):
                                                ospfRetransmit = str(obj13.text.split("retransmit-interval ")[1].split(" ")[0].lstrip().rstrip())
                                                break
                                            ospfLine.append(ospfRetransmit)
                                            for obj13 in obj12.re_search_children("authentication-type "):
                                                ospfAuth = str(obj13.text.split("authentication-type ")[1].split(" ")[0].lstrip().rstrip())
                                                break
                                            ospfLine.append(ospfAuth)
                                            for obj13 in obj12.re_search_children("no shutdown"):
                                                ospfIfState = "En"
                                                break

                                            ospfAreaList = []
                                            ospfAreaList.append([int(area),"",""])
                                            if ospfIfState == "Dis":
                                                ospfAreaList[0][2] = "(Dis)"
                                            else:
                                                ospfAreaList[0][2] = ""
                                            ospfLine.append(ospfAreaList)

                                            lineNumber = 0
                                            match = 0
                                            for ospfLineCheck in ospfList:
                                                if ((ospfLineCheck[4] == ospfBFDState) and (ospfLineCheck[5] == ospfPriority) and (ospfLineCheck[6] == ospfMetric) and (ospfLineCheck[7] == ospfHello)
                                                    and (ospfLineCheck[8] == ospfDead) and (ospfLineCheck[9] == ospfRetransmit) and (ospfLineCheck[10] == ospfAuth)):

                                                    ospfList[lineNumber][11].extend(ospfAreaList)
                                                    match = 1
                                                    break

                                                lineNumber = lineNumber + 1

                                            if match == 0:
                                                ospfList.append(ospfLine)

                            # Sort all areas inside the ospfList
                            # print(ospfList)
                            lineNumber = 0
                            for ospfLineCheck in ospfList:
                                ospfList[lineNumber][11].sort(key=lambda x: x[0])
                                lineNumber = lineNumber + 1

                            # ospfList.sort(key=lambda x: x[10])


                            if len(ospfList) > 0:
                                ospfOutputLine = ""
                                for ospfLine in ospfList:
                                    # print(ospfLine)
                                    if ospfOutputLine != "":
                                        ospfOutputLine = ospfOutputLine + ";"

                                    # ospfOutputLine = ospfOutputLine + "pid:"+str(ospfLine[0]) + "|type:"+str(ospfLine[1]) + "|mode:"+str(ospfLine[2]) + "|bfd:"+str(ospfLine[3]) + "|prio:"+str(ospfLine[4]) + "|metr:"+str(ospfLine[5]) + "|hello:"+str(ospfLine[6]) + "|dead:"+str(ospfLine[7]) + "|retr:"+str(ospfLine[8]) + "|auth:"+str(ospfLine[9])

                                    ospfOutputLine = ospfOutputLine + "pid:"+str(ospfLine[0])
                                    if ospfLine[1] != "": ospfOutputLine = ospfOutputLine + "|rid:"+str(ospfLine[1])
                                    ospfOutputLine = ospfOutputLine + "|type:"+str(ospfLine[2]) + "|mode:"+str(ospfLine[3]) + "|bfd:"+str(ospfLine[4])
                                    if ospfLine[5] != "": ospfOutputLine = ospfOutputLine + "|prio:" + str(ospfLine[5])
                                    if ospfLine[6] != "": ospfOutputLine = ospfOutputLine + "|metr:" + str(ospfLine[6])
                                    if ((ospfLine[7] != "") or (ospfLine[8] != "") or (ospfLine[9] != "")):
                                        if ospfLine[7] == "": ospfLine[7] = "def"
                                        if ospfLine[8] == "": ospfLine[8] = "def"
                                        if ospfLine[9] == "": ospfLine[9] = "def"
                                        ospfOutputLine = ospfOutputLine + "|ospf_tmr:" + str(ospfLine[7]) + " " + str(ospfLine[8]) + " " + str(ospfLine[9])
                                    if ospfLine[10] != "": ospfOutputLine = ospfOutputLine + "|auth:" + str(ospfLine[10])

                                    if len(ospfLine) > 11:
                                        ospfOutputLine = ospfOutputLine + "|areas:"

                                        ospfOutputLine2 = ""
                                        for area in ospfLine[11]:
                                            if ospfOutputLine2 == "":
                                                ospfOutputLine2 = str(area[0]) + str(area[1]) + str(area[2])
                                            else:
                                                ospfOutputLine2 = ospfOutputLine2 + " " + str(area[0]) + str(area[1]) + str(area[2])

                                        ospfOutputLine = ospfOutputLine + ospfOutputLine2

                                InterfacesParse[InterfacesDict["OSPFv2"][0]] = ospfOutputLine



                            # Find all IS-IS processes where this interface is participating
                            isisList = []
                            # Find all OSPF processes associated with interface
                            for obj10 in obj2.re_search_children(r"isis "):
                                isisLine = []

                                isisPID = ""
                                isisPID = str(obj10.text.split("isis ")[1].split()[0])
                                isisLine.append(isisPID)

                                isisSID = ""
                                for obj11 in obj10.re_search_children(r"system-id "):
                                    isisSID = obj11.text.split("system-id ")[1].lstrip().rstrip()
                                isisLine.append(isisSID)

                                isisArea = ""
                                for obj11 in obj10.re_search_children(r"area-id "):
                                    isisArea = obj11.text.split("area-id ")[1].lstrip().rstrip()
                                isisLine.append(isisArea)

                                isisLevelCapability = "L1/2"
                                for obj11 in obj10.re_search_children("level-capability"):
                                    if re.match(r"^ *level-capability *level-1$",obj11.text):
                                        isisLevelCapability = "L1"
                                    else:
                                        if re.match(r"^ *level-capability *level-2$",obj11.text):
                                            isisLevelCapability = "L2"
                                        else:
                                            if re.match(r"^ *level-capability *level-1/2$",obj11.text):
                                                isisLevelCapability = "L1/2"
                                            else:
                                                isisLevelCapability = obj13.text.split("level-capability ")[1]
                                    break

                                isisIfType1 = ""
                                isisIfType2 = "Bcast"
                                isisIfMode = "Act"
                                isisBFDState = "Dis"

                                isisL1Priority = ""
                                isisL2Priority = ""
                                isisL1Metric = ""
                                isisL2Metric = ""
                                isisL1Hello = ""
                                isisL2Hello = ""
                                isisL1HelloMult = ""
                                isisL2HelloMult = ""
                                isisRetransmit = ""
                                isisIfAuth = ""
                                isisL1Auth = ""
                                isisL2Auth = ""
                                isisIfState = "Dis"

                                # Find current interface
                                searchExpression = r"\""+ InterfacesParse[InterfacesDict["IfName"][0]] + r"\""
                                for obj11 in obj10.re_search_children(searchExpression):

                                    # Find all ISIS parameters for this interface
                                    for obj13 in obj11.re_search_children("interface-type "):
                                        isisIfType1 = str(obj13.text.split("interface-type ")[1].split(" ")[0].lstrip().rstrip())
                                        isisIfType2 = ""
                                        if isisIfType1 == "point-to-point":
                                            isisIfType2 = "PtP"
                                        else:
                                            if isisIfType1 == "point-to-multipoint":
                                                isisIfType2 = "PtMP"
                                            else:
                                                isisIfType2 = isisIfType1
                                        break
                                    isisLine.append(isisIfType2)
                                    for obj13 in obj11.re_search_children("passive"):
                                        if re.match(r"^ *passive *$",obj13.text):
                                            isisIfMode = "Pass"
                                        else:
                                            if re.match(r"^ *no passive *$",obj13.text):
                                                isisIfMode = "Act"
                                        break
                                    isisLine.append(isisIfMode)
                                    for obj13 in obj11.re_search_children("bfd-enable"):
                                        if re.match(r"^ *bfd-enable.*$",obj13.text):
                                            if re.search(r"ip",obj13.text):
                                                isisBFDState = "En " + obj13.text.split("bfd-enable ")[1]
                                            else:
                                                isisBFDState = "En"
                                        if re.match(r"^ *no bfd-enable.*$",obj13.text):
                                            isisBFDState = "Dis"
                                        break
                                    isisLine.append(isisBFDState)
                                    for obj13 in obj11.re_search_children("level-capability"):
                                        if re.match(r"^ *level-capability *level-1$",obj13.text):
                                            isisLevelCapability = "L1"
                                        else:
                                            if re.match(r"^ *level-capability *level-2$",obj13.text):
                                                isisLevelCapability = "L2"
                                            else:
                                                if re.match(r"^ *level-capability *level-1/2$",obj13.text):
                                                    isisLevelCapability = "L1/2"
                                                else:
                                                    isisLevelCapability = obj13.text.split("level-capability ")[1]
                                        break
                                    isisLine.append(isisLevelCapability)
                                    for obj13 in obj11.re_search_children("no shutdown"):
                                        isisIfState = "En"
                                        break
                                    isisLine.append(isisIfState)
                                    for obj13 in obj11.re_search_children("retransmit-interval "):
                                        isisRetransmit = str(obj13.text.split("retransmit-interval ")[1].lstrip().rstrip())
                                        break
                                    isisLine.append(isisRetransmit)
                                    for obj13 in obj11.re_search_children("hello-authentication-type "):
                                        isisIfAuth = str(obj13.text.split("hello-authentication-type ")[1].lstrip().rstrip())
                                        break
                                    isisLine.append(isisIfAuth)

                                    # Get L1 parameters
                                    for obj12 in obj11.re_search_children("level 1"):
                                        for obj13 in obj12.re_search_children("priority "):
                                            isisL1Priority = str(obj13.text.split("priority ")[1].split(" ")[0].lstrip().rstrip())
                                            break

                                        for obj13 in obj12.re_search_children("metric "):
                                            isisL1Metric = str(obj13.text.split("metric ")[1].split(" ")[0].lstrip().rstrip())
                                            break

                                        for obj13 in obj12.re_search_children("hello-interval "):
                                            isisL1Hello = str(obj13.text.split("hello-interval ")[1].split(" ")[0].lstrip().rstrip())
                                            break

                                        for obj13 in obj12.re_search_children("hello-multiplier "):
                                            isisL1HelloMult = str(obj13.text.split("hello-multiplier ")[1].split(" ")[0].lstrip().rstrip())
                                            break

                                        for obj13 in obj12.re_search_children("hello-authentication-type "):
                                            isisL1Auth = str(obj13.text.split("hello-authentication-type ")[1].split(" ")[0].lstrip().rstrip())
                                            break

                                    isisLine.append(isisL1Priority)
                                    isisLine.append(isisL1Metric)
                                    isisLine.append(isisL1Hello)
                                    isisLine.append(isisL1HelloMult)
                                    isisLine.append(isisL1Auth)

                                    # Get L2 parameters
                                    for obj12 in obj11.re_search_children("level 2"):
                                        for obj13 in obj12.re_search_children("priority "):
                                            isisL2Priority = str(obj13.text.split("priority ")[1].split(" ")[0].lstrip().rstrip())
                                            break

                                        for obj13 in obj12.re_search_children("metric "):
                                            isisL2Metric = str(obj13.text.split("metric ")[1].split(" ")[0].lstrip().rstrip())
                                            break

                                        for obj13 in obj12.re_search_children("hello-interval "):
                                            isisL2Hello = str(obj13.text.split("hello-interval ")[1].split(" ")[0].lstrip().rstrip())
                                            break

                                        for obj13 in obj12.re_search_children("hello-multiplier "):
                                            isisL2HelloMult = str(obj13.text.split("hello-multiplier ")[1].split(" ")[0].lstrip().rstrip())
                                            break

                                        for obj13 in obj12.re_search_children("hello-authentication-type "):
                                            isisL2Auth = str(obj13.text.split("hello-authentication-type ")[1].split(" ")[0].lstrip().rstrip())
                                            break


                                    isisLine.append(isisL2Priority)
                                    isisLine.append(isisL2Metric)
                                    isisLine.append(isisL2Hello)
                                    isisLine.append(isisL2HelloMult)
                                    isisLine.append(isisL2Auth)

                                    isisList.append(isisLine)
                                    break

                            if len(isisList) > 0:
                                isisOutputLine = ""
                                for isisLine in isisList:
                                    print(isisLine)
                                    if isisOutputLine != "":
                                        isisOutputLine = isisOutputLine + ";"

                                    isisOutputLine = isisOutputLine + "pid:"+str(isisLine[0])
                                    if isisLine[1] != "": isisOutputLine = isisOutputLine + "|sid:"+str(isisLine[1])
                                    isisOutputLine = isisOutputLine + "|area:"+str(isisLine[2]) + "|type:"+str(isisLine[3]) + "|mode:"+str(isisLine[4]) + "|bfd:"+str(isisLine[5]) + "|cap:"+str(isisLine[6]) + "|if_state:"+str(isisLine[7])
                                    if isisLine[8] != "": isisOutputLine = isisOutputLine + "|retr:" + str(isisLine[8])
                                    if isisLine[9] != "": isisOutputLine = isisOutputLine + "|if_auth:" + str(isisLine[9])
                                    if isisLine[10] != "": isisOutputLine = isisOutputLine + "|l1_pri:" + str(isisLine[10])
                                    if isisLine[15] != "": isisOutputLine = isisOutputLine + "|l2_pri:" + str(isisLine[15])
                                    if isisLine[11] != "": isisOutputLine = isisOutputLine + "|l1_metr:" + str(isisLine[11])
                                    if isisLine[16] != "": isisOutputLine = isisOutputLine + "|l2_metr:" + str(isisLine[16])
                                    if ((isisLine[12] != "") or (isisLine[13] != "")):
                                        if isisLine[12] == "": isisLine[11] = "def"
                                        if isisLine[13] == "": isisLine[12] = "def"
                                        isisOutputLine = isisOutputLine + "|isis_l1_tmr:" + str(isisLine[12]) + " " + str(isisLine[13])
                                    if ((isisLine[17] != "") or (isisLine[18] != "")):
                                        if isisLine[17] == "": isisLine[17] = "def"
                                        if isisLine[18] == "": isisLine[18] = "def"
                                        isisOutputLine = isisOutputLine + "|isis_l2_tmr:" + str(isisLine[17]) + " " + str(isisLine[18])
                                    if isisLine[14] != "": isisOutputLine = isisOutputLine + "|l1_auth:" + str(isisLine[14])
                                    if isisLine[19] != "": isisOutputLine = isisOutputLine + "|l2_auth:" + str(isisLine[19])

                                InterfacesParse[InterfacesDict["ISIS"][0]] = isisOutputLine


                            # Find if LDP is enabled on this interface
                            for obj10 in obj2.re_search_children(r"ldp"):
                                for obj11 in obj10.re_search_children(r"interface-parameters"):
                                    LDPIfAdmState = ""
                                    LDPIPv4AdmState = ""
                                    LDPIPv6AdmState = ""
                                    searchExpression = r"\""+ InterfacesParse[InterfacesDict["IfName"][0]] + r"\""
                                    for obj12 in obj11.re_search_children(searchExpression):
                                        # if obj12.text.split("interface ")[1].split("\"")[1] == obj3.text.split("interface ")[1].split("\"")[1]:
                                        for obj13 in obj12.re_search_children(r"shutdown"):
                                            if obj13.re_search(r"no "):
                                                LDPIfAdmState = "if:En"
                                            else:
                                                LDPIfAdmState = "if:Dis"
                                        for obj13 in obj12.re_search_children(r"ipv4"):
                                            for obj14 in obj13.re_search_children(r"shutdown"):
                                                if obj14.re_search(r"no "):
                                                    LDPIPv4AdmState = "ipv4:En"
                                                else:
                                                    LDPIPv4AdmState = "ipv4:Dis"
                                        for obj13 in obj12.re_search_children(r"ipv6"):
                                            for obj14 in obj13.re_search_children(r"shutdown"):
                                                if obj14.re_search(r"no "):
                                                    LDPIPv6AdmState = "ipv6:En"
                                                else:
                                                    LDPIPv6AdmState = "ipv6:Dis"

                                if LDPIfAdmState != "":
                                    InterfacesParse[InterfacesDict["LDP"][0]] = LDPIfAdmState
                                if LDPIPv4AdmState != "":
                                    InterfacesParse[InterfacesDict["LDP"][0]] = InterfacesParse[InterfacesDict["LDP"][0]] + "|" + LDPIPv4AdmState
                                if LDPIPv6AdmState != "":
                                    InterfacesParse[InterfacesDict["LDP"][0]] = InterfacesParse[InterfacesDict["LDP"][0]] + "|" + LDPIPv6AdmState


                            # Find all MPLS/RSVP parameters for this interface
                            # rsvpList = []
                            # # Go to MPLS process first
                            # for obj10 in obj2.re_search_children(r"mpls "):
                            #     rsvpLine = []

                            #     mplsIfState = ""
                            #     mplsIfAdmGroup = ""
                            #     rsvpIfState = ""
                            #     rsvpIfSubscription = ""
                            #     rsvpIfRefreshReduction = ""
                            #     rsvpIfReliableDelivery = ""

                            #     # Find current interface
                            #     searchExpression = r"\""+ InterfacesParse[InterfacesDict["IfName"][0]] + r"\""
                            #     for obj11 in obj10.re_search_children(searchExpression):



                            # print(InterfacesParse)
                            InterfacesParse = [element.rstrip().lstrip() for element in InterfacesParse]
                            InterfacesParseAll.append(InterfacesParse)




                    # Find node's SAP interfaces from config
                    for obj2 in obj1.re_search_children(r"service"):
                        # Find VPRN SAPs
                        for obj3 in obj2.re_search_children(r"vprn"):
                            for obj4 in obj3.re_search_children(r"interface"):
                                # for obj5 in obj4.re_search_children(r".*"):
                                #     print(obj5)
                                if len(obj4.re_search_children(r".*")) == 0: continue
                                duplicate = []
                                for obj5 in obj4.re_search_children(r"interface"):
                                    if obj4.text.split("interface ")[1].split(" create")[0] == obj5.text.split("interface ")[1].split(" create")[0]:
                                        duplicate.append(str(obj4))

                                if len(duplicate) > 1:
                                    print("File "+str(os.path.split(inputPath)[1])+" contains duplicate interface lines: "+str(duplicate)+", skipping this file")
                                    nextFile = 1
                                    break

                                IfNumber = IfNumber + 1
                                if debug: print("debug: obj4: "+str(obj4))

                                InterfacesParse = [""] * len(InterfacesDict)
                                InterfacesParse[InterfacesDict["NodeID"][0]] = NodeID
                                InterfacesParse[InterfacesDict["Hostname"][0]] = Hostname
                                InterfacesParse[InterfacesDict["CLISyntax"][0]] = CLISyntax
                                InterfacesParse[InterfacesDict["IfNumber"][0]] = str(IfNumber).zfill(4)
                                InterfacesParse[InterfacesDict["IfName"][0]] = obj4.text.split("interface ")[1].split(" create")[0].replace("\"","")
                                # InterfacesParse[InterfacesDict["IfType"][0]] = "L3VPN SAP"
                                InterfacesParse[InterfacesDict["IfMode"][0]] = "Access"
                                InterfacesParse[InterfacesDict["ServiceID"][0]] = obj3.text.split("vprn ")[1].split(" name")[0] + ":" + obj3.text.split("customer ")[1].split(" create")[0]
                                InterfacesParse[InterfacesDict["ServiceType"][0]] = "VPRN"
                                InterfacesParse[InterfacesDict["ServiceName"][0]] = obj3.text.split("name ")[1].split(" customer")[0].replace("\"","")

                                # Check if interface is a loopback interface
                                for obj5 in obj4.re_search_children("loopback"):
                                    InterfacesParse[InterfacesDict["IfType"][0]] = "Loopback"
                                    break

                                for obj10 in obj3.re_search_children(r"description"):
                                    InterfacesParse[InterfacesDict["ServiceDescr"][0]] = obj10.text.split("description ")[1].replace("\"","")

                                # Find description associated with current interface
                                for obj5 in obj4.re_search_children("description "):
                                    InterfacesParse[InterfacesDict["IfDescr"][0]] = str(obj5.text.split("description ")[1].replace("\"",""))
                                    break

                                # Find admin state associated with current interface
                                for obj5 in obj4.re_search_children(r"shutdown"):
                                    if obj5.re_search(r"no "):
                                        InterfacesParse[InterfacesDict["StateAdm"][0]] = "En"
                                    else:
                                        InterfacesParse[InterfacesDict["StateAdm"][0]] = "Dis"

                                if InterfacesParse[InterfacesDict["StateAdm"][0]] == "":
                                    InterfacesParse[InterfacesDict["StateAdm"][0]] = "En"

                                # Find BFD parameters associated with current interface
                                for obj5 in obj4.re_search_children(r"bfd"):
                                    InterfacesParse[InterfacesDict["BFD"][0]] = "if_tmr:" + obj5.text.lstrip().rstrip().replace("bfd ","").replace(" receive "," ").replace(" multiplier "," ").replace(" type "," ")
                                    break

                                # Find all IPv4 addresses associated with current interface
                                for obj5 in obj4.re_search_children(r"^ *address "):
                                    rawInput = obj5.text.split("address ")[1].lstrip().rstrip()
                                    rawInput = rawInput.replace(" ","/")
                                    ipadd = ipaddress.ip_interface(str(rawInput))
                                    if InterfacesParse[InterfacesDict["IPV4Addr"][0]] == "":
                                        InterfacesParse[InterfacesDict["IPV4Addr"][0]] = str(ipadd)
                                    else:
                                        InterfacesParse[InterfacesDict["IPV4Addr"][0]] = InterfacesParse[InterfacesDict["IPV4Addr"][0]] + "|" + str(ipadd)
                                    if InterfacesParse[InterfacesDict["IPV4Subnet"][0]] == "":
                                        InterfacesParse[InterfacesDict["IPV4Subnet"][0]] = str(ipadd.network)
                                    else:
                                        InterfacesParse[InterfacesDict["IPV4Subnet"][0]] = InterfacesParse[InterfacesDict["IPV4Subnet"][0]] + "|"+ str(ipadd.network)

                                # Find all IPv6 addresses associated with current interface
                                for obj5 in obj4.re_search_children(r"^ *ipv6 address "):
                                    rawInput = obj5.text.split("ipv6 address ")[1].lstrip().rstrip()
                                    ipadd = ipaddress.ip_interface(str(line))
                                    if InterfacesParse[InterfacesDict["IPV6Addr"][0]] == "":
                                        InterfacesParse[InterfacesDict["IPV6Addr"][0]] = str(ipadd)
                                    else:
                                        InterfacesParse[InterfacesDict["IPV6Addr"][0]] = InterfacesParse[InterfacesDict["IPV6Addr"][0]] + "|" + str(ipadd)
                                    if InterfacesParse[InterfacesDict["IPV6Subnet"][0]] == "":
                                        InterfacesParse[InterfacesDict["IPV6Subnet"][0]] = str(ipadd.network)
                                    else:
                                        InterfacesParse[InterfacesDict["IPV6Subnet"][0]] = InterfacesParse[InterfacesDict["IPV6Subnet"][0]] + "|" + str(ipadd.network)

                                # Check if interface is a L3 interface
                                if ((InterfacesParse[InterfacesDict["IPV4Addr"][0]] != "") or (InterfacesParse[InterfacesDict["IPV6Addr"][0]] != "")):
                                    # Mark interface as Network/Hybrid if it has any IPv4/v6 addresses assigned
                                    if InterfacesParse[InterfacesDict["IfType"][0]] == "":
                                        InterfacesParse[InterfacesDict["IfType"][0]] = "L3VPN SAP"
                                    # if ((InterfacesParse[InterfacesDict["IfType"][0]] == "Port") or (InterfacesParse[InterfacesDict["IfType"][0]] == "LAG") or (InterfacesParse[InterfacesDict["IfType"][0]] == "Bridge")):
                                    else:
                                        InterfacesParse[InterfacesDict["IfType"][0]] = InterfacesParse[InterfacesDict["IfType"][0]] + "|L3VPN SAP"

                                # Find L3 MTU parameters associated with current interface
                                for obj5 in obj4.re_search_children(r"ip-mtu"):
                                    InterfacesParse[InterfacesDict["L3MTU"][0]] = obj5.text.split("ip-mtu ")[1]
                                    break

                                # Find port/LAG associated with current interface
                                for obj5 in obj4.re_search_children(r"^ *sap"):
                                    if InterfacesParse[InterfacesDict["PortBinding"][0]] != "": InterfacesParse[InterfacesDict["PortBinding"][0]] = InterfacesParse[InterfacesDict["PortBinding"][0]] + "|"
                                    tempPortBinding = obj5.text.split("sap ")[1].split(" create")[0]
                                    InterfacesParse[InterfacesDict["PortBinding"][0]] = InterfacesParse[InterfacesDict["PortBinding"][0]] + tempPortBinding
                                    if obj5.re_search(r":"):
                                        if InterfacesParse[InterfacesDict["PortName"][0]] != "": InterfacesParse[InterfacesDict["PortName"][0]] = InterfacesParse[InterfacesDict["PortName"][0]] + "|"
                                        if InterfacesParse[InterfacesDict["Encap"][0]] != "": InterfacesParse[InterfacesDict["Encap"][0]] = InterfacesParse[InterfacesDict["Encap"][0]] + "|"
                                        if InterfacesParse[InterfacesDict["VLAN"][0]] != "": InterfacesParse[InterfacesDict["VLAN"][0]] = InterfacesParse[InterfacesDict["VLAN"][0]] + "|"
                                        InterfacesParse[InterfacesDict["PortName"][0]] = InterfacesParse[InterfacesDict["PortName"][0]] + tempPortBinding.split(":")[0]
                                        InterfacesParse[InterfacesDict["VLAN"][0]] = InterfacesParse[InterfacesDict["VLAN"][0]] + tempPortBinding.split(":")[1]
                                        if obj5.re_search(r"\."):
                                            InterfacesParse[InterfacesDict["Encap"][0]] = InterfacesParse[InterfacesDict["Encap"][0]] + "qinq"
                                        else:
                                            InterfacesParse[InterfacesDict["Encap"][0]] = InterfacesParse[InterfacesDict["Encap"][0]] + "dot1q"
                                    else:
                                        InterfacesParse[InterfacesDict["Encap"][0]] = "Null"
                                        InterfacesParse[InterfacesDict["PortName"][0]] = InterfacesParse[InterfacesDict["PortBinding"][0]]

                                    if obj5.re_search(r"lag"):
                                        InterfacesParse[InterfacesDict["LAGID"][0]] = InterfacesParse[InterfacesDict["PortName"][0]].split("lag-")[1]
                                        InterfacesParse[InterfacesDict["ParentIfName"][0]] = "lag " + InterfacesParse[InterfacesDict["LAGID"][0]]
                                    else:
                                        InterfacesParse[InterfacesDict["ParentIfName"][0]] = InterfacesParse[InterfacesDict["PortName"][0]]

                                    # Find QoS input policy associated with current interface
                                    for obj6 in obj5.re_search_children(r"^ *ingress"):
                                        for obj7 in obj6.re_search_children(r"(.*qos.*)|(.*remark.*)"):
                                            if InterfacesParse[InterfacesDict["QoSIn"][0]] == "":
                                                InterfacesParse[InterfacesDict["QoSIn"][0]] = obj7.text.lstrip().rstrip().split(" ")[1].replace("\"","")
                                            else:
                                                InterfacesParse[InterfacesDict["QoSIn"][0]] = InterfacesParse[InterfacesDict["QoSIn"][0]] + "|" + obj7.text.lstrip().rstrip().split(" ")[1].replace("\"","")

                                    # Find QoS output policy associated with current interface
                                    for obj6 in obj5.re_search_children(r"^ *egress"):
                                        for obj7 in obj6.re_search_children(r"(.*qos.*)|(.*remark.*)"):
                                            if InterfacesParse[InterfacesDict["QoSOut"][0]] == "":
                                                InterfacesParse[InterfacesDict["QoSOut"][0]] = obj7.text.lstrip().rstrip().split(" ")[1].replace("\"","")
                                            else:
                                                InterfacesParse[InterfacesDict["QoSOut"][0]] = InterfacesParse[InterfacesDict["QoSOut"][0]] + "|" + obj7.text.lstrip().rstrip().split(" ")[1].replace("\"","")


                                # Find VPLS service associated with current interface
                                for obj5 in obj4.re_search_children(r"^ *vpls"):
                                    vplsServiceName = obj5.text.split("\"")[1]
                                    if InterfacesParse[InterfacesDict["IfType"][0]] != "": InterfacesParse[InterfacesDict["IfType"][0]] = InterfacesParse[InterfacesDict["IfType"][0]] + "|"
                                    InterfacesParse[InterfacesDict["IfType"][0]] = InterfacesParse[InterfacesDict["IfType"][0]] + "VPLS SAP"
                                    # Go to service section
                                    for obj50 in obj1.re_search_children(r"service"):
                                        # Find relevant VPLS service
                                        for obj51 in obj50.re_search_children(r"vpls.*\""+vplsServiceName+r"\""):
                                            vplsServiceID = obj51.text.split("vpls ")[1].split(" name")[0] + ":" + obj51.text.split("customer ")[1].split(" create")[0]

                                            vplsServiceDescr = ""
                                            for obj5 in obj51.re_search_children(r"^ *description"):
                                                vplsServiceDescr = obj51.text.split("\"")[1].split()[0]
                                                if InterfacesParse[InterfacesDict["ServiceDescr"][0]] != "": InterfacesParse[InterfacesDict["ServiceDescr"][0]] = InterfacesParse[InterfacesDict["ServiceDescr"][0]] + "|"
                                                InterfacesParse[InterfacesDict["ServiceDescr"][0]] = InterfacesParse[InterfacesDict["ServiceDescr"][0]] + vplsServiceDescr

                                            if InterfacesParse[InterfacesDict["ParentIfName"][0]] != "": InterfacesParse[InterfacesDict["ParentIfName"][0]] = InterfacesParse[InterfacesDict["ParentIfName"][0]] + "|"
                                            InterfacesParse[InterfacesDict["ParentIfName"][0]] = InterfacesParse[InterfacesDict["ParentIfName"][0]] + "vpls:" + vplsServiceID + ":" + vplsServiceName

                                            if InterfacesParse[InterfacesDict["ServiceID"][0]] != "": InterfacesParse[InterfacesDict["ServiceID"][0]] = InterfacesParse[InterfacesDict["ServiceID"][0]] + "|"
                                            InterfacesParse[InterfacesDict["ServiceID"][0]] = InterfacesParse[InterfacesDict["ServiceID"][0]] + vplsServiceID

                                            if InterfacesParse[InterfacesDict["ServiceName"][0]] != "": InterfacesParse[InterfacesDict["ServiceName"][0]] = InterfacesParse[InterfacesDict["ServiceName"][0]] + "|"
                                            InterfacesParse[InterfacesDict["ServiceName"][0]] = InterfacesParse[InterfacesDict["ServiceName"][0]] + vplsServiceName

                                            if InterfacesParse[InterfacesDict["ServiceType"][0]] != "": InterfacesParse[InterfacesDict["ServiceType"][0]] = InterfacesParse[InterfacesDict["ServiceType"][0]] + "|"
                                            InterfacesParse[InterfacesDict["ServiceType"][0]] = InterfacesParse[InterfacesDict["ServiceType"][0]] + "VPLS"

                                            # Find VPLS SAPs from config
                                            for obj5 in obj51.re_search_children(r"^ *sap"):
                                                if InterfacesParse[InterfacesDict["PortBinding"][0]] != "": InterfacesParse[InterfacesDict["PortBinding"][0]] = InterfacesParse[InterfacesDict["PortBinding"][0]] + "|"
                                                tempPortBinding = obj5.text.split("sap ")[1].split(" create")[0]
                                                InterfacesParse[InterfacesDict["PortBinding"][0]] = InterfacesParse[InterfacesDict["PortBinding"][0]] + tempPortBinding
                                                if obj5.re_search(r":"):
                                                    if InterfacesParse[InterfacesDict["PortName"][0]] != "": InterfacesParse[InterfacesDict["PortName"][0]] = InterfacesParse[InterfacesDict["PortName"][0]] + "|"
                                                    if InterfacesParse[InterfacesDict["Encap"][0]] != "": InterfacesParse[InterfacesDict["Encap"][0]] = InterfacesParse[InterfacesDict["Encap"][0]] + "|"
                                                    if InterfacesParse[InterfacesDict["VLAN"][0]] != "": InterfacesParse[InterfacesDict["VLAN"][0]] = InterfacesParse[InterfacesDict["VLAN"][0]] + "|"
                                                    InterfacesParse[InterfacesDict["PortName"][0]] = InterfacesParse[InterfacesDict["PortName"][0]] + tempPortBinding.split(":")[0]
                                                    InterfacesParse[InterfacesDict["VLAN"][0]] = InterfacesParse[InterfacesDict["VLAN"][0]] + tempPortBinding.split(":")[1]
                                                    if obj5.re_search(r"\."):
                                                        InterfacesParse[InterfacesDict["Encap"][0]] = InterfacesParse[InterfacesDict["Encap"][0]] + "qinq"
                                                    else:
                                                        InterfacesParse[InterfacesDict["Encap"][0]] = InterfacesParse[InterfacesDict["Encap"][0]] + "dot1q"
                                                else:
                                                    InterfacesParse[InterfacesDict["Encap"][0]] = "Null"
                                                    InterfacesParse[InterfacesDict["PortName"][0]] = InterfacesParse[InterfacesDict["PortBinding"][0]]

                                                # if obj5.re_search(r"lag"):
                                                #     InterfacesParse[InterfacesDict["LAGID"][0]] = InterfacesParse[InterfacesDict["PortName"][0]].split("lag-")[1]
                                                #     InterfacesParse[InterfacesDict["ParentIfName"][0]] = "lag " + InterfacesParse[InterfacesDict["LAGID"][0]]
                                                # else:
                                                #     InterfacesParse[InterfacesDict["ParentIfName"][0]] = InterfacesParse[InterfacesDict["PortName"][0]]

                                                # Find QoS input policy associated with current interface
                                                for obj6 in obj5.re_search_children(r"^ *ingress"):
                                                    for obj7 in obj6.re_search_children(r"(.*qos.*)|(.*remark.*)"):
                                                        if InterfacesParse[InterfacesDict["QoSIn"][0]] == "":
                                                            InterfacesParse[InterfacesDict["QoSIn"][0]] = obj7.text.lstrip().rstrip().split(" ")[1].replace("\"","")
                                                        else:
                                                            InterfacesParse[InterfacesDict["QoSIn"][0]] = InterfacesParse[InterfacesDict["QoSIn"][0]] + "|" + obj7.text.lstrip().rstrip().split(" ")[1].replace("\"","")

                                                # Find QoS output policy associated with current interface
                                                for obj6 in obj5.re_search_children(r"^ *egress"):
                                                    for obj7 in obj6.re_search_children(r"(.*qos.*)|(.*remark.*)"):
                                                        if InterfacesParse[InterfacesDict["QoSOut"][0]] == "":
                                                            InterfacesParse[InterfacesDict["QoSOut"][0]] = obj7.text.lstrip().rstrip().split(" ")[1].replace("\"","")
                                                        else:
                                                            InterfacesParse[InterfacesDict["QoSOut"][0]] = InterfacesParse[InterfacesDict["QoSOut"][0]] + "|" + obj7.text.lstrip().rstrip().split(" ")[1].replace("\"","")


                                # Find all OSPF processes and areas where this interface is participating
                                ospfList = []
                                ospfLine = []
                                ospfRID = ""
                                # Find all OSPF processes associated with interface
                                for obj10 in obj3.re_search_children(r"ospf "):
                                    if len(obj10.text.split("ospf ")) > 1:
                                        ospfRID = str(obj10.text.split("ospf ")[1].split(" ")[0])
                                    ospfLine.append(ospfRID)

                                    # First we will look for the area where interface is primary
                                    ospfIfType1 = ""
                                    ospfIfType2 = "Bcast"
                                    ospfIfMode = "Act"
                                    ospfBFDState = "Dis"
                                    ospfPriority = ""
                                    ospfMetric = ""
                                    ospfHello = ""
                                    ospfDead = ""
                                    ospfRetransmit = ""
                                    ospfAuth = ""
                                    ospfIfState = "Dis"

                                    area = ""
                                    # Look through all OSPF areas
                                    for obj11 in obj10.re_search_children(r"area "):
                                        area = obj11.text.split("area ")[1]
                                        area = ipaddress.ip_address(area)

                                        # Find current interface configured as primary within an area
                                        searchExpression = r"\""+ InterfacesParse[InterfacesDict["IfName"][0]] + r"\""
                                        for obj12 in obj11.re_search_children(searchExpression):
                                            if re.search(r"secondary",obj12.text):
                                                continue
                                            else:
                                                # Find all OSPF parameters for this primary interface
                                                for obj13 in obj12.re_search_children("interface-type "):
                                                    ospfIfType1 = str(obj13.text.split("interface-type ")[1].split(" ")[0].lstrip().rstrip())
                                                    ospfIfType2 = ""
                                                    if ospfIfType1 == "point-to-point":
                                                        ospfIfType2 = "PtP"
                                                    else:
                                                        if ospfIfType1 == "point-to-multipoint":
                                                            ospfIfType2 = "PtMP"
                                                        else:
                                                            ospfIfType2 = ospfIfType1
                                                    break
                                                ospfLine.append(ospfIfType2)
                                                for obj13 in obj12.re_search_children("passive"):
                                                    if re.match(r"^ *passive *$",obj13.text):
                                                        ospfIfMode = "Pass"
                                                    if re.match(r"^ *no passive *$",obj13.text):
                                                        ospfIfMode = "Act"
                                                    break
                                                ospfLine.append(ospfIfMode)
                                                for obj13 in obj12.re_search_children("bfd-enable"):
                                                    if re.match(r"^ *bfd-enable *$",obj13.text):
                                                        ospfBFDState = "En"
                                                    if re.match(r"^ *no bfd-enable *$",obj13.text):
                                                        ospfBFDState = "Dis"
                                                    break
                                                ospfLine.append(ospfBFDState)
                                                for obj13 in obj12.re_search_children("priority "):
                                                    ospfPriority = str(obj13.text.split("priority ")[1].split(" ")[0].lstrip().rstrip())
                                                    break
                                                ospfLine.append(ospfPriority)
                                                for obj13 in obj12.re_search_children("metric "):
                                                    ospfMetric = str(obj13.text.split("metric ")[1].split(" ")[0].lstrip().rstrip())
                                                    break
                                                ospfLine.append(ospfMetric)
                                                for obj13 in obj12.re_search_children("hello-interval "):
                                                    ospfHello = str(obj13.text.split("hello-interval ")[1].split(" ")[0].lstrip().rstrip())
                                                    break
                                                ospfLine.append(ospfHello)
                                                for obj13 in obj12.re_search_children("dead-interval "):
                                                    ospfDead = str(obj13.text.split("dead-interval ")[1].split(" ")[0].lstrip().rstrip())
                                                    break
                                                ospfLine.append(ospfDead)
                                                for obj13 in obj12.re_search_children("retransmit-interval "):
                                                    ospfRetransmit = str(obj13.text.split("retransmit-interval ")[1].split(" ")[0].lstrip().rstrip())
                                                    break
                                                ospfLine.append(ospfRetransmit)
                                                for obj13 in obj12.re_search_children("authentication-type "):
                                                    ospfAuth = str(obj13.text.split("authentication-type ")[1].split(" ")[0].lstrip().rstrip())
                                                    break
                                                ospfLine.append(ospfAuth)
                                                for obj13 in obj12.re_search_children("no shutdown"):
                                                    ospfIfState = "En"
                                                    break

                                                ospfAreaList = []
                                                ospfAreaList.append([int(area),"*",""])
                                                if ospfIfState == "Dis":
                                                    ospfAreaList[0][2] = "(Dis)"
                                                else:
                                                    ospfAreaList[0][2] = ""

                                                ospfLine.append(ospfAreaList)

                                                ospfList.append(ospfLine)

                                                break

                                    # Now we will look for all other areas where interface is secondary

                                    area = ""
                                    # Look through all OSPF areas
                                    for obj11 in obj10.re_search_children(r"area "):
                                        area = obj11.text.split("area ")[1]
                                        area = ipaddress.ip_address(area)

                                        ospfLine = []
                                        ospfBFDState = "Dis"
                                        ospfPriority = ""
                                        ospfMetric = ""
                                        ospfHello = ""
                                        ospfDead = ""
                                        ospfRetransmit = ""
                                        ospfAuth = ""
                                        ospfIfState = "Dis"

                                        # Find current interface configured as secondary within an area
                                        searchExpression = r"\""+ InterfacesParse[InterfacesDict["IfName"][0]] + r"\""
                                        for obj12 in obj11.re_search_children(searchExpression):
                                            if re.search(r"secondary",obj12.text):
                                                # Find all OSPF parameters for this secondary interface
                                                ospfLine.append(ospfRID)        # Set to same value as on primary configuration
                                                ospfLine.append(ospfIfType2)    # Set to same value as on primary configuration
                                                ospfLine.append(ospfIfMode)     # Set to same value as on primary configuration
                                                for obj13 in obj12.re_search_children("bfd-enable"):
                                                    if re.match(r"^ *bfd-enable *$",obj13.text):
                                                        ospfBFDState = "En"
                                                    if re.match(r"^ *no bfd-enable *$",obj13.text):
                                                        ospfBFDState = "Dis"
                                                    break
                                                ospfLine.append(ospfBFDState)
                                                for obj13 in obj12.re_search_children("priority "):
                                                    ospfPriority = str(obj13.text.split("priority ")[1].split(" ")[0].lstrip().rstrip())
                                                    break
                                                ospfLine.append(ospfPriority)
                                                for obj13 in obj12.re_search_children("metric "):
                                                    ospfMetric = str(obj13.text.split("metric ")[1].split(" ")[0].lstrip().rstrip())
                                                    break
                                                ospfLine.append(ospfMetric)
                                                for obj13 in obj12.re_search_children("hello-interval "):
                                                    ospfHello = str(obj13.text.split("hello-interval ")[1].split(" ")[0].lstrip().rstrip())
                                                    break
                                                ospfLine.append(ospfHello)
                                                for obj13 in obj12.re_search_children("dead-interval "):
                                                    ospfDead = str(obj13.text.split("dead-interval ")[1].split(" ")[0].lstrip().rstrip())
                                                    break
                                                ospfLine.append(ospfDead)
                                                for obj13 in obj12.re_search_children("retransmit-interval "):
                                                    ospfRetransmit = str(obj13.text.split("retransmit-interval ")[1].split(" ")[0].lstrip().rstrip())
                                                    break
                                                ospfLine.append(ospfRetransmit)
                                                for obj13 in obj12.re_search_children("authentication-type "):
                                                    ospfAuth = str(obj13.text.split("authentication-type ")[1].split(" ")[0].lstrip().rstrip())
                                                    break
                                                ospfLine.append(ospfAuth)
                                                for obj13 in obj12.re_search_children("no shutdown"):
                                                    ospfIfState = "En"
                                                    break

                                                ospfAreaList = []
                                                ospfAreaList.append([int(area),"",""])
                                                if ospfIfState == "Dis":
                                                    ospfAreaList[0][2] = "(Dis)"
                                                else:
                                                    ospfAreaList[0][2] = ""
                                                ospfLine.append(ospfAreaList)

                                                lineNumber = 0
                                                match = 0
                                                for ospfLineCheck in ospfList:
                                                    if ((ospfLineCheck[3] == ospfBFDState) and (ospfLineCheck[4] == ospfPriority) and (ospfLineCheck[5] == ospfMetric) and (ospfLineCheck[6] == ospfHello)
                                                        and (ospfLineCheck[7] == ospfDead) and (ospfLineCheck[8] == ospfRetransmit) and (ospfLineCheck[9] == ospfAuth)):

                                                        ospfList[lineNumber][10].extend(ospfAreaList)
                                                        match = 1
                                                        break

                                                    lineNumber = lineNumber + 1

                                                if match == 0:
                                                    ospfList.append(ospfLine)

                                # Sort all areas inside the ospfList
                                # print(ospfList)
                                lineNumber = 0
                                for ospfLineCheck in ospfList:
                                    ospfList[lineNumber][10].sort(key=lambda x: x[0])
                                    lineNumber = lineNumber + 1

                                # ospfList.sort(key=lambda x: x[10])


                                if len(ospfList) > 0:
                                    ospfOutputLine = ""
                                    for ospfLine in ospfList:
                                        # print(ospfLine)
                                        if ospfOutputLine != "":
                                            ospfOutputLine = ospfOutputLine + ";"

                                        # ospfOutputLine = ospfOutputLine + "pid:"+str(ospfLine[0]) + "|type:"+str(ospfLine[1]) + "|mode:"+str(ospfLine[2]) + "|bfd:"+str(ospfLine[3]) + "|prio:"+str(ospfLine[4]) + "|metr:"+str(ospfLine[5]) + "|hello:"+str(ospfLine[6]) + "|dead:"+str(ospfLine[7]) + "|retr:"+str(ospfLine[8]) + "|auth:"+str(ospfLine[9])

                                        ospfOutputLine = ospfOutputLine + "rid:"+str(ospfLine[0]) + "|type:"+str(ospfLine[1]) + "|mode:"+str(ospfLine[2]) + "|bfd:"+str(ospfLine[3])
                                        if ospfLine[4] != "": ospfOutputLine = ospfOutputLine + "|prio:" + str(ospfLine[4])
                                        if ospfLine[5] != "": ospfOutputLine = ospfOutputLine + "|metr:" + str(ospfLine[5])
                                        if ((ospfLine[6] != "") or (ospfLine[7] != "") or (ospfLine[8] != "")):
                                            if ospfLine[6] == "": ospfLine[6] = "def"
                                            if ospfLine[7] == "": ospfLine[7] = "def"
                                            if ospfLine[8] == "": ospfLine[8] = "def"
                                            ospfOutputLine = ospfOutputLine + "|ospf_tmr:" + str(ospfLine[6]) + " " + str(ospfLine[7]) + " " + str(ospfLine[8])
                                        if ospfLine[9] != "": ospfOutputLine = ospfOutputLine + "|auth:" + str(ospfLine[9])

                                        if len(ospfLine) > 10:
                                            ospfOutputLine = ospfOutputLine + "|areas:"

                                            ospfOutputLine2 = ""
                                            for area in ospfLine[10]:
                                                if ospfOutputLine2 == "":
                                                    ospfOutputLine2 = str(area[0]) + str(area[1]) + str(area[2])
                                                else:
                                                    ospfOutputLine2 = ospfOutputLine2 + " " + str(area[0]) + str(area[1]) + str(area[2])

                                            ospfOutputLine = ospfOutputLine + ospfOutputLine2

                                    InterfacesParse[InterfacesDict["OSPFv2"][0]] = ospfOutputLine


                                # print(InterfacesParse)
                                InterfacesParse = [element.rstrip().lstrip() for element in InterfacesParse]
                                InterfacesParseAll.append(InterfacesParse)


                        # Find ePipe SAPs
                        for obj3 in obj2.re_search_children(r"epipe"):

                            sdpList = []
                            # Find all SDP associated with the service
                            for obj4 in obj3.re_search_children(r"sdp"):

                                sdpLine = []

                                sdpType = ""
                                sdpID = obj4.text.split("sdp ")[1].split(":")[0]
                                sdpLine.append(sdpID)

                                sdpNH = ""
                                sdpKA = ""
                                sdpVC = obj4.text.split("sdp ")[1].split(":")[1].split()[0]
                                sdpState = "Dis"

                                for obj5 in obj4.re_search_children(r"shutdown"):
                                    if obj5.re_search(r"no "):
                                        sdpState = "En"
                                    else:
                                        sdpState = "Dis"

                                searchExpression = r"^ *sdp " + str(sdpID)
                                for obj90 in obj2.re_search_children(searchExpression):
                                    sdpType = obj90.text.split(str(sdpID))[1].split()[0]
                                    for obj91 in obj90.re_search_children(r"^ *far-end"):
                                        sdpNH = obj91.text.split("far-end ")[1].split()[0]
                                    for obj91 in obj90.re_search_children(r"^ *keep-alive"):
                                        for obj92 in obj91.re_search_children(r"shutdown"):
                                            if obj92.re_search(r"no "):
                                                sdpKA = "En"
                                            else:
                                                sdpKA = "Dis"
                                    if sdpState == "En":
                                        for obj91 in obj90.re_search_children(r"^ *shutdown"):
                                                sdpState = "Dis"

                                sdpLine.append(sdpType)
                                sdpLine.append(sdpState)
                                sdpLine.append(sdpNH)
                                sdpLine.append(sdpVC)
                                sdpLine.append(sdpKA)

                                sdpList.append(sdpLine)


                            for obj4 in obj3.re_search_children(r"sap"):
                                # for obj5 in obj4.re_search_children(r".*"):
                                #     print(obj5)
                                # if len(obj4.re_search_children(r".*")) == 0: continue
                                duplicate = []
                                for obj5 in obj4.re_search_children(r"sap"):
                                    if obj4.text.split("sap ")[1].split(" create")[0] == obj5.text.split("sap ")[1].split(" create")[0]:
                                        duplicate.append(str(obj4))

                                if len(duplicate) > 1:
                                    print("File "+str(os.path.split(inputPath)[1])+" contains duplicate interface lines: "+str(duplicate)+", skipping this file")
                                    nextFile = 1
                                    break

                                IfNumber = IfNumber + 1
                                if debug: print("debug: obj4: "+str(obj4))

                                InterfacesParse = [""] * len(InterfacesDict)
                                InterfacesParse[InterfacesDict["NodeID"][0]] = NodeID
                                InterfacesParse[InterfacesDict["Hostname"][0]] = Hostname
                                InterfacesParse[InterfacesDict["CLISyntax"][0]] = CLISyntax
                                InterfacesParse[InterfacesDict["IfNumber"][0]] = str(IfNumber).zfill(4)
                                # InterfacesParse[InterfacesDict["IfName"][0]] = obj4.text.split("sap ")[1].split(" create")[0].replace("\"","") + "_epipe" + obj3.text.split("epipe ")[1].split(" name")[0]
                                InterfacesParse[InterfacesDict["IfName"][0]] = obj4.text.split("sap ")[1].split(" create")[0].replace("\"","")
                                InterfacesParse[InterfacesDict["IfType"][0]] = "L2VPN SAP"
                                InterfacesParse[InterfacesDict["IfMode"][0]] = "Access"
                                InterfacesParse[InterfacesDict["ServiceID"][0]] = obj3.text.split("epipe ")[1].split(" name")[0] + ":" + obj3.text.split("customer ")[1].split(" create")[0]
                                InterfacesParse[InterfacesDict["ServiceName"][0]] = obj3.text.split("name ")[1].split(" customer")[0].replace("\"","")
                                InterfacesParse[InterfacesDict["ServiceType"][0]] = "ePipe"
                                for obj10 in obj3.re_search_children(r"description"):
                                    InterfacesParse[InterfacesDict["ServiceDescr"][0]] = obj10.text.split("\"")[1].replace("\"","")

                                # Find admin state associated with current interface
                                for obj5 in obj4.re_search_children(r"shutdown"):
                                    if obj5.re_search(r"no "):
                                        InterfacesParse[InterfacesDict["StateAdm"][0]] = "En"
                                    else:
                                        InterfacesParse[InterfacesDict["StateAdm"][0]] = "Dis"


                                if len(sdpList) > 0:
                                    sdpOutputLine = ""
                                    for sdpLine in sdpList:
                                        if sdpOutputLine != "":
                                            sdpOutputLine = sdpOutputLine + ";"

                                        sdpOutputLine = sdpOutputLine + "id:"+str(sdpLine[0]) + "|type:"+str(sdpLine[1]) + "|state:"+str(sdpLine[2]) + "|next-hop:"+str(sdpLine[3]) + "|vc-id:"+str(sdpLine[4]) + "|keepalive:"+str(sdpLine[5])

                                    InterfacesParse[InterfacesDict["ServiceSDP"][0]] = sdpOutputLine


                                # Find L2 MTU parameters associated with current interface
                                for obj10 in obj3.re_search_children(r"service-mtu"):
                                    InterfacesParse[InterfacesDict["L2MTU"][0]] = obj10.text.split("service-mtu ")[1]
                                    break

                                # Find port/LAG associated with current interface
                                InterfacesParse[InterfacesDict["PortBinding"][0]] = obj4.text.split("sap ")[1].split(" create")[0]
                                if obj4.re_search(r":"):
                                    InterfacesParse[InterfacesDict["PortName"][0]] = InterfacesParse[InterfacesDict["PortBinding"][0]].split(":")[0]
                                    InterfacesParse[InterfacesDict["VLAN"][0]] = InterfacesParse[InterfacesDict["PortBinding"][0]].split(":")[1]
                                    if obj4.re_search(r"\."):
                                        InterfacesParse[InterfacesDict["Encap"][0]] = "qinq"
                                    else:
                                        InterfacesParse[InterfacesDict["Encap"][0]] = "dot1q"
                                else:
                                    InterfacesParse[InterfacesDict["Encap"][0]] = "Null"
                                    InterfacesParse[InterfacesDict["PortName"][0]] = InterfacesParse[InterfacesDict["PortBinding"][0]]

                                if obj4.re_search(r"lag"):
                                    InterfacesParse[InterfacesDict["LAGID"][0]] = InterfacesParse[InterfacesDict["PortName"][0]].split("lag-")[1]

                                # print(InterfacesParse)
                                InterfacesParse = [element.rstrip().lstrip() for element in InterfacesParse]
                                InterfacesParseAll.append(InterfacesParse)

                        # Find VPLS SAPs
                        for obj3 in obj2.re_search_children(r"vpls"):

                            sdpList = []
                            # Find all SDP associated with the service
                            for obj4 in obj3.re_search_children(r"sdp"):

                                sdpLine = []

                                sdpType = ""
                                sdpID = obj4.text.split("sdp ")[1].split(":")[0]
                                sdpLine.append(sdpID)

                                sdpNH = ""
                                sdpKA = ""
                                sdpVC = obj4.text.split("sdp ")[1].split(":")[1].split()[0]
                                sdpState = "Dis"

                                for obj5 in obj4.re_search_children(r"shutdown"):
                                    if obj5.re_search(r"no "):
                                        sdpState = "En"
                                    else:
                                        sdpState = "Dis"

                                searchExpression = r"^ *sdp " + str(sdpID)
                                for obj90 in obj2.re_search_children(searchExpression):
                                    sdpType = obj90.text.split(str(sdpID))[1].split()[0]
                                    for obj91 in obj90.re_search_children(r"^ *far-end"):
                                        sdpNH = obj91.text.split("far-end ")[1].split()[0]
                                    for obj91 in obj90.re_search_children(r"^ *keep-alive"):
                                        for obj92 in obj91.re_search_children(r"shutdown"):
                                            if obj92.re_search(r"no "):
                                                sdpKA = "En"
                                            else:
                                                sdpKA = "Dis"
                                    if sdpState == "En":
                                        for obj91 in obj90.re_search_children(r"^ *shutdown"):
                                                sdpState = "Dis"

                                sdpLine.append(sdpType)
                                sdpLine.append(sdpState)
                                sdpLine.append(sdpNH)
                                sdpLine.append(sdpVC)
                                sdpLine.append(sdpKA)

                                sdpList.append(sdpLine)

                            for obj4 in obj3.re_search_children(r"sap"):
                                # if len(obj4.re_search_children(r".*")) == 0: continue
                                duplicate = []
                                for obj5 in obj4.re_search_children(r"sap"):
                                    if obj4.text.split("sap ")[1].split(" create")[0] == obj5.text.split("sap ")[1].split(" create")[0]:
                                        duplicate.append(str(obj4))

                                if len(duplicate) > 1:
                                    print("File "+str(os.path.split(inputPath)[1])+" contains duplicate interface lines: "+str(duplicate)+", skipping this file")
                                    nextFile = 1
                                    break

                                IfNumber = IfNumber + 1
                                if debug: print("debug: obj4: "+str(obj4))

                                InterfacesParse = [""] * len(InterfacesDict)
                                InterfacesParse[InterfacesDict["NodeID"][0]] = NodeID
                                InterfacesParse[InterfacesDict["Hostname"][0]] = Hostname
                                InterfacesParse[InterfacesDict["CLISyntax"][0]] = CLISyntax
                                InterfacesParse[InterfacesDict["IfNumber"][0]] = str(IfNumber).zfill(4)
                                # InterfacesParse[InterfacesDict["IfName"][0]] = obj4.text.split("sap ")[1].split(" create")[0].replace("\"","") + "_vpls" + obj3.text.split("vpls ")[1].split(" name")[0]
                                InterfacesParse[InterfacesDict["IfName"][0]] = obj4.text.split("sap ")[1].split(" create")[0].replace("\"","")
                                InterfacesParse[InterfacesDict["IfType"][0]] = "VPLS SAP"
                                InterfacesParse[InterfacesDict["IfMode"][0]] = "Access"
                                InterfacesParse[InterfacesDict["ServiceID"][0]] = obj3.text.split("vpls ")[1].split(" name")[0] + ":" + obj3.text.split("customer ")[1].split(" create")[0]
                                InterfacesParse[InterfacesDict["ServiceName"][0]] = obj3.text.split("name ")[1].split(" customer")[0].replace("\"","")
                                InterfacesParse[InterfacesDict["ServiceType"][0]] = "VPLS"
                                for obj10 in obj3.re_search_children(r"description"):
                                    InterfacesParse[InterfacesDict["ServiceDescr"][0]] = obj10.text.split("description ")[1].replace("\"","")

                                # Find admin state associated with current interface
                                for obj5 in obj4.re_search_children(r"shutdown"):
                                    if obj5.re_search(r"no "):
                                        InterfacesParse[InterfacesDict["StateAdm"][0]] = "En"
                                    else:
                                        InterfacesParse[InterfacesDict["StateAdm"][0]] = "Dis"

                                if len(sdpList) > 0:
                                    sdpOutputLine = ""
                                    for sdpLine in sdpList:
                                        if sdpOutputLine != "":
                                            sdpOutputLine = sdpOutputLine + ";"

                                        sdpOutputLine = sdpOutputLine + "id:"+str(sdpLine[0]) + "|type:"+str(sdpLine[1]) + "|state:"+str(sdpLine[2]) + "|next-hop:"+str(sdpLine[3]) + "|vc-id:"+str(sdpLine[4]) + "|keepalive:"+str(sdpLine[5])

                                    InterfacesParse[InterfacesDict["ServiceSDP"][0]] = sdpOutputLine


                                # Find L2 MTU parameters associated with current interface
                                for obj10 in obj3.re_search_children(r"service-mtu"):
                                    InterfacesParse[InterfacesDict["L2MTU"][0]] = obj10.text.split("service-mtu ")[1]
                                    break

                                # Find port/LAG associated with current interface
                                InterfacesParse[InterfacesDict["PortBinding"][0]] = obj4.text.split("sap ")[1].split(" create")[0]
                                if obj4.re_search(r":"):
                                    InterfacesParse[InterfacesDict["PortName"][0]] = InterfacesParse[InterfacesDict["PortBinding"][0]].split(":")[0]
                                    InterfacesParse[InterfacesDict["VLAN"][0]] = InterfacesParse[InterfacesDict["PortBinding"][0]].split(":")[1]
                                    if obj4.re_search(r"\."):
                                        InterfacesParse[InterfacesDict["Encap"][0]] = "qinq"
                                    else:
                                        InterfacesParse[InterfacesDict["Encap"][0]] = "dot1q"
                                else:
                                    InterfacesParse[InterfacesDict["Encap"][0]] = "Null"
                                    InterfacesParse[InterfacesDict["PortName"][0]] = InterfacesParse[InterfacesDict["PortBinding"][0]]

                                if obj4.re_search(r"lag"):
                                    InterfacesParse[InterfacesDict["LAGID"][0]] = InterfacesParse[InterfacesDict["PortName"][0]].split("lag-")[1]

                                InterfacesParse[InterfacesDict["ParentIfName"][0]] = InterfacesParse[InterfacesDict["PortName"][0]]

                                # Find QoS input policy associated with current interface
                                for obj6 in obj4.re_search_children(r"^ *ingress"):
                                    for obj7 in obj6.re_search_children(r"(.*qos.*)|(.*remark.*)"):
                                        if InterfacesParse[InterfacesDict["QoSIn"][0]] == "":
                                            InterfacesParse[InterfacesDict["QoSIn"][0]] = obj7.text.lstrip().rstrip().split(" ")[1].replace("\"","")
                                        else:
                                            InterfacesParse[InterfacesDict["QoSIn"][0]] = InterfacesParse[InterfacesDict["QoSIn"][0]] + "|" + obj7.text.lstrip().rstrip().split(" ")[1].replace("\"","")

                                # Find QoS output policy associated with current interface
                                for obj6 in obj4.re_search_children(r"^ *egress"):
                                    for obj7 in obj6.re_search_children(r"(.*qos.*)|(.*remark.*)"):
                                        if InterfacesParse[InterfacesDict["QoSOut"][0]] == "":
                                            InterfacesParse[InterfacesDict["QoSOut"][0]] = obj7.text.lstrip().rstrip().split(" ")[1].replace("\"","")
                                        else:
                                            InterfacesParse[InterfacesDict["QoSOut"][0]] = InterfacesParse[InterfacesDict["QoSOut"][0]] + "|" + obj7.text.lstrip().rstrip().split(" ")[1].replace("\"","")

                                # print(InterfacesParse)
                                InterfacesParse = [element.rstrip().lstrip() for element in InterfacesParse]
                                InterfacesParseAll.append(InterfacesParse)



            if debug and nextFile == 0: input("Input file parsed. Press any key proceed.\r\n")

#####################################################################################################################################################
###################################################       Add/Update all parsed info in the DB        ###############################################
#####################################################################################################################################################

            if nextFile == 0:

                # Getting all existing interfaces of this node from DB with relevant CLI Syntax
                DBQuery="""SELECT *
                            FROM Interfaces"""+str(SyntaxDict[CLISyntax])+"""
                            WHERE NodeID = '"""+str(NodeID)+"""'
                            ORDER BY LastUpdatedTime DESC
                            """
                if debugSQL: print("debug: DBQuery: "+str(DBQuery))
                outputCursor.execute(DBQuery)
                DBResponse=outputCursor.fetchall()
                InterfacesDBAll=list(DBResponse)
                #if debugSQL: print("debug: DBResponse: "+str(DBResponse))

                # Getting all existing peerings of this node from DB - TBD



                # Getting all existing interfaces of this node from DB with other CLI Syntaxes
                InterfacesDBOther = []
                PeeringDBOther = []
                InterfacesDBHist = []
                PeeringDBHist = []
                # Getting all data for all supported syntaxes from the DB
                for value1 in SyntaxDict:
                    # Getting all existing interfaces from the DB, except historical
                    DBQuery="""SELECT * FROM Interfaces"""+str(SyntaxDict[value1])+""" WHERE Hostname = '"""+str(Hostname)+"""' ORDER BY LastUpdatedTime DESC\n"""
                    if debugSQL: print("debug: DBQuery: "+str(DBQuery))
                    outputCursor.execute(DBQuery)
                    DBResponse=outputCursor.fetchall()
                    if debugSQL: print("debug: DBResponse: "+str(DBResponse))
                    if value1 == "Hist":
                        InterfacesDBHist = list(DBResponse)
                    else:
                        if value1 != CLISyntax:
                            InterfacesDBOther.append(list(DBResponse))

                    # Getting all existing peerings from the DB, except historical
                    DBQuery="""SELECT * FROM Peering"""+str(SyntaxDict[value1])+""" WHERE Hostname = '"""+str(Hostname)+"""' ORDER BY LastUpdatedTime DESC\n"""
                    if debugSQL: print("debug: DBQuery: "+str(DBQuery))
                    outputCursor.execute(DBQuery)
                    DBResponse=outputCursor.fetchall()
                    if debugSQL: print("debug: DBResponse: "+str(DBResponse))
                    if value1 == "Hist":
                        PeeringDBHist = list(DBResponse)
                    else:
                        if value1 != CLISyntax:
                            PeeringDBOther.append(list(DBResponse))

                    # Getting all existing routing from the DB - TBD


                # Go through all interfaces parsed from file
                for obj3 in InterfacesParseAll:

                    match = 0
                    if InterfacesDBAll is not None:

                        # Go through all interfaces stored in a DB
                        for obj4 in InterfacesDBAll:

                            # Find if parsed interface name matches any stored in DB
                            if ((obj4[InterfacesDict["IfName"][0]] == obj3[InterfacesDict["IfName"][0]]) and (obj4[InterfacesDict["ServiceName"][0]] == obj3[InterfacesDict["ServiceName"][0]])):
                                match = 1
                                IDMatched.append(str(obj4[InterfacesDict["IfID"][0]]))

                                # Define a lisy of updatable interface value IDs (not all need to be updated|overwritten)
                                UpdatableIDs = []
                                for value in InterfacesDict:
                                    # if ((value != "IfID") and (value != "NodeID") and (value != "Hostname") and (value != "CLISyntax") and (value != "Comments") and (value != "LastUpdatedTime") and (value != "LastUpdatedBy")):
                                    if ((value != "IfID") and (value != "LastUpdatedTime") and (value != "LastUpdatedBy")):
                                        UpdatableIDs.append(value)

                                # Compare and update all values for this interface in DB (except IfID)
                                DBQuery="""UPDATE Interfaces"""+str(SyntaxDict[CLISyntax])+"""
                                                        SET"""
                                equal = 1

                                for value2 in UpdatableIDs:
                                    if (obj4[InterfacesDict[value2][0]] != obj3[InterfacesDict[value2][0]]):
                                        equal = 0
                                        DBQuery = DBQuery + "                                            "
                                        DBQuery = DBQuery + value2 + """ = '"""+str(obj3[InterfacesDict[value2][0]])+"""',\n"""
                                        print("Interface "+str(obj4[InterfacesDict["IfName"][0]])+" value "+str(value2)+" changed to "+str(obj3[InterfacesDict[value2][0]]))

                                DBQuery = DBQuery + "                                            LastUpdatedTime = '"""+str(datetime.datetime.today())+"""',
                                            LastUpdatedBy = '"""+str(getpass.getuser())+"""'
                                        WHERE
                                            IfID = '"""+obj4[InterfacesDict["IfID"][0]]+"""'
                                            """
                                # Sending SQL query to update changed interface values
                                if equal == 0:
                                    IfUpdated = IfUpdated + 1
                                    if debugSQL: print("debug: DBQuery: "+str(DBQuery))
                                    if not DBUpdateDisable: outputCursor.execute(DBQuery)
                                    outputDB.commit()

                                    # Move old values to historical table
                                    obj4 = list(obj4)
                                    obj4[InterfacesDict["LastUpdatedTime"][0]] = datetime.datetime.today()
                                    obj4[InterfacesDict["LastUpdatedBy"][0]] = getpass.getuser()

                                    DBQuery="""INSERT INTO Interfaces"""+str(SyntaxDict["Hist"])+""" (\n"""

                                    i = 1
                                    for value3 in InterfacesDict:
                                        DBQuery = DBQuery + "                                            "
                                        if i < len(InterfacesDict):
                                            DBQuery = DBQuery + value3 + ",\n"
                                        else:
                                            DBQuery = DBQuery + value3 + "\n"
                                        i = i + 1

                                    DBQuery = DBQuery + """                                                )
                                                            VALUES (\n"""

                                    i = 1
                                    for value3 in InterfacesDict:
                                        DBQuery = DBQuery + "                                            "
                                        if i < len(InterfacesDict):
                                            DBQuery = DBQuery + "'"+str(obj4[InterfacesDict[value3][0]])+"',\n"
                                        else:
                                            DBQuery = DBQuery + "'"+str(obj4[InterfacesDict[value3][0]])+"'\n"
                                        i = i + 1

                                    DBQuery = DBQuery + """                                                )\n"""

                                    if debugSQL: print("debug: "+str(DBQuery))
                                    #outputCursor.execute(DBQuery)
                                    #outputDB.commit()

                                else:
                                    IfKept = IfKept + 1
                                    if debug: print("debug: Interface "+str(obj3[InterfacesDict["IfName"][0]])+" found in DB, no update needed")

                                break

                    # Adding interface to DB if it was not found there previously
                    if match == 0:
                        if debug: print("debug: Interface "+str(obj3[InterfacesDict["IfName"][0]])+" not found in DB - creating")
                        IfNew = IfNew + 1

                        # Check if the same L3 interface is already created for another syntax
                        # print(len(InterfacesDBOther))
                        if InterfacesDBOther is not None:
                            for table in InterfacesDBOther:
                                # print(table)
                                for obj10 in table:
                                    # Check if interface has matching IPv4/v6 adresses
                                    if ( ( (obj3[InterfacesDict["IPV4Addr"][0]] != "") and (obj3[InterfacesDict["IPV4Addr"][0]] == obj10[InterfacesDict["IPV4Addr"][0]]) ) or ( (obj3[InterfacesDict["IPV6Addr"][0]] != "") and (obj3[InterfacesDict["IPV6Addr"][0]] == obj10[InterfacesDict["IPV6Addr"][0]]) ) ):
                                        if ( (obj3[InterfacesDict["ServiceName"][0]] != "") and (obj10[InterfacesDict["ServiceName"][0]] != "") ):
                                            serviceListSrc = obj3[InterfacesDict["ServiceName"][0]].split("|")
                                            serviceListDst = obj10[InterfacesDict["ServiceName"][0]].split("|")

                                            # Check if interface has matching services
                                            for service in serviceListSrc:
                                                if service in serviceListDst:
                                                    obj3[InterfacesDict["IfID"][0]] = obj10[InterfacesDict["IfID"][0]]
                                                    if debug: print("debug: Interface found for another syntax, creating new record in DB Interfaces"+str(SyntaxDict[CLISyntax])+" with previously used id: "+str(obj3[InterfacesDict["IfID"][0]]))
                                                    break
                                        else:
                                            if ( (obj3[InterfacesDict["ServiceName"][0]] == "") and (obj10[InterfacesDict["ServiceName"][0]] == "") ):
                                                obj3[InterfacesDict["IfID"][0]] = obj10[InterfacesDict["IfID"][0]]
                                                if debug: print("debug: Interface found for another syntax, creating new record in DB Interfaces"+str(SyntaxDict[CLISyntax])+" with previously used id: "+str(obj3[InterfacesDict["IfID"][0]]))
                                                break

                        # Check if the same interface was previously deleted
                        # print(len(InterfacesDBHist))
                        if obj3[InterfacesDict["IfID"][0]] == "":
                            if InterfacesDBHist is not None:
                                for obj11 in InterfacesDBHist:
                                    # print(obj11)
                                    if ((obj3[InterfacesDict["IfName"][0]] != "" ) and (obj3[InterfacesDict["IfName"][0]] == obj11[InterfacesDict["IfName"][0]])):
                                        obj3[InterfacesDict["IfID"][0]] = obj11[InterfacesDict["IfID"][0]]
                                        if debug: print("debug: Interface found from last historical record, creating new record in DB Interfaces"+str(SyntaxDict[CLISyntax])+" with previously used id: "+str(obj3[InterfacesDict["IfID"][0]]))
                                        break

                        # Check if ID is already present in the DB to prevent a conflict
                        conflict = 1
                        while conflict == 1:
                            DBQuery="""SELECT * FROM Interfaces"""+str(SyntaxDict[CLISyntax])+""" WHERE IfID = '"""+str(obj3[InterfacesDict["IfID"][0]])+"""'\n"""
                            if debugSQL: print("debug: DBQuery: "+str(DBQuery))
                            outputCursor.execute(DBQuery)
                            DBResponse=outputCursor.fetchall()
                            if debugSQL: print("debug: DBResponse: "+str(DBResponse))

                            # No conflicts found
                            if len(DBResponse) == 0:
                                conflict = 0
                            else:
                                newID = str(uuid.uuid4())
                                # Check if ID is already present in the DB to prevent a potential conflict
                                conflict2 = 1
                                while conflict2 == 1:
                                    DBQuery="""SELECT * FROM Interfaces"""+str(SyntaxDict[CLISyntax])+""" WHERE IfID = '"""+str(newID)+"""'\n"""
                                    if debugSQL: print("debug: DBQuery: "+str(DBQuery))
                                    outputCursor.execute(DBQuery)
                                    DBResponse2=outputCursor.fetchall()
                                    if debugSQL: print("debug: DBResponse: "+str(DBResponse2))

                                    # No conflicts found
                                    if len(DBResponse2) == 0:
                                        conflict2 = 0
                                        break
                                    else:
                                        newID = str(uuid.uuid4())

                                # print(DBResponse)
                                if debug: print("debug: Generated ID conflicts with interface " + DBResponse[0][InterfacesDict["IfName"][0]] + ", creating a new random id for it: "+str(newID))

                                DBQuery="""UPDATE Interfaces"""+str(SyntaxDict[CLISyntax])+"""
                                                        SET"""
                                DBQuery = DBQuery + "                                            "
                                DBQuery = DBQuery + """ IfID = '"""+str(newID)+"""',\n"""
                                DBQuery = DBQuery + "                                            LastUpdatedTime = '"""+str(datetime.datetime.today())+"""',
                                    LastUpdatedBy = '"""+str(getpass.getuser())+"""'
                                WHERE
                                    IfID = '"""+str(obj3[InterfacesDict["IfID"][0]])+"""'
                                    """
                                if debugSQL: print("debug: "+str(DBQuery))
                                if not DBUpdateDisable: outputCursor.execute(DBQuery)
                                outputDB.commit()

                                # Since we had to change ID of the existing interface we also need to updated it in matched list to not delete this interface if it is existing
                                if str(obj3[InterfacesDict["IfID"][0]]) in IDMatched:
                                    IDMatched[IDMatched.index(str(obj3[InterfacesDict["IfID"][0]]))] = str(newID)

                        # Since no other options worked we generate a new ID for the interface
                        if obj3[InterfacesDict["IfID"][0]] == "":
                            obj3[InterfacesDict["IfID"][0]] = str(uuid.uuid4())
                            if debug: print("debug: Interface is not found in other tables, creating new record in DB Interfaces"+str(SyntaxDict[CLISyntax])+" with a new random id: "+str(obj3[InterfacesDict["IfID"][0]]))

                            # Check if ID is already present in the DB to prevent a potential conflict
                            conflict = 1
                            while conflict == 1:
                                DBQuery="""SELECT * FROM Interfaces"""+str(SyntaxDict[CLISyntax])+""" WHERE IfID = '"""+str(obj3[InterfacesDict["IfID"][0]])+"""'\n"""
                                if debugSQL: print("debug: DBQuery: "+str(DBQuery))
                                outputCursor.execute(DBQuery)
                                DBResponse=outputCursor.fetchall()
                                if debugSQL: print("debug: DBResponse: "+str(DBResponse))

                                # No conflicts found
                                if len(DBResponse) == 0:
                                    conflict = 0
                                    break
                                else:
                                    obj3[InterfacesDict["IfID"][0]] = str(uuid.uuid4())
                                    if debug: print("debug: Generated ID conflicts with another one in the database, creating a new random id: "+str(obj3[InterfacesDict["IfID"][0]]))


                        obj3[InterfacesDict["LastUpdatedTime"][0]] = str(datetime.datetime.today())
                        obj3[InterfacesDict["LastUpdatedBy"][0]] = str(getpass.getuser())
                        IDMatched.append(obj3[InterfacesDict["IfID"][0]])

                        DBQuery="""INSERT INTO Interfaces"""+str(SyntaxDict[CLISyntax])+""" (\n"""

                        i = 1
                        for value3 in InterfacesDict:
                            DBQuery = DBQuery + "                                            "
                            if i < len(InterfacesDict):
                                DBQuery = DBQuery + value3 + ",\n"
                            else:
                                DBQuery = DBQuery + value3 + "\n"
                            i = i + 1

                        DBQuery = DBQuery + """                                            )
                                            VALUES (\n"""

                        i = 1
                        for value3 in InterfacesDict:
                            DBQuery = DBQuery + "                                            "
                            if i < len(InterfacesDict):
                                DBQuery = DBQuery + "'"+str(obj3[InterfacesDict[value3][0]])+"',\n"
                            else:
                                DBQuery = DBQuery + "'"+str(obj3[InterfacesDict[value3][0]])+"'\n"
                            i = i + 1

                        DBQuery = DBQuery + """                                                )\n"""

                        if debugSQL: print("debug: DBQuery: "+str(DBQuery))
                        if not DBUpdateDisable: outputCursor.execute(DBQuery)
                        outputDB.commit()

                if debug: input("Existing interfaces are updated in the database. Press any key proceed.\r\n")


#####################################################################################################################################################
###########################################       Remove all not found interfaces from the DB         ###############################################
#####################################################################################################################################################

                # Getting all existing interfaces of this node from DB with relevant CLI Syntax
                DBQuery="""SELECT *
                            FROM Interfaces"""+str(SyntaxDict[CLISyntax])+"""
                            WHERE NodeID = '"""+str(NodeID)+"""'
                            ORDER BY LastUpdatedTime DESC
                            """
                if debugSQL: print("debug: DBQuery: "+str(DBQuery))
                outputCursor.execute(DBQuery)
                DBResponse=outputCursor.fetchall()
                InterfacesDBAll=list(DBResponse)

                # Deleteng all the interfaces in DB that were not found in parsed values and moving then to historical DB
                if InterfacesDBAll is not None:
                    for obj3 in InterfacesDBAll:
                        match = 0
                        # if debug: print("debug: Checking interface <"+str(obj3[4])+"> / port <"+str(obj3[8])+">")
                        for obj4 in IDMatched:
                            if obj3[InterfacesDict["IfID"][0]] == obj4:
                                match = 1
                                break

                        if  match == 0:
                            if debug: print("debug: Interface "+str(obj3[InterfacesDict["IfName"][0]])+" not found in parsed files, moving it to historical table")
                            IfDeleted = IfDeleted + 1
                            DBQuery="""DELETE FROM Interfaces"""+str(SyntaxDict[CLISyntax])+"""
                                        WHERE
                                            IfID = '"""+obj3[InterfacesDict["IfID"][0]]+"""'
                                            """
                            if debugSQL: print("debug: "+str(DBQuery))
                            if not DBUpdateDisable: outputCursor.execute(DBQuery)
                            outputDB.commit()

                            obj3 = list(obj3)

                            obj3[InterfacesDict["LastUpdatedTime"][0]] = str(datetime.datetime.today())
                            obj3[InterfacesDict["LastUpdatedBy"][0]] = str(getpass.getuser())

                            DBQuery="""INSERT INTO Interfaces"""+str(SyntaxDict["Hist"])+""" (\n"""

                            i = 1
                            for value3 in InterfacesDict:
                                DBQuery = DBQuery + "                                            "
                                if i < len(InterfacesDict):
                                    DBQuery = DBQuery + value3 + ",\n"
                                else:
                                    DBQuery = DBQuery + value3 + "\n"
                                i = i + 1

                            DBQuery = DBQuery + """                                                )
                                                    VALUES (\n"""

                            i = 1
                            for value3 in InterfacesDict:
                                DBQuery = DBQuery + "                                            "
                                if i < len(InterfacesDict):
                                    DBQuery = DBQuery + "'"+str(obj3[InterfacesDict[value3][0]])+"',\n"
                                else:
                                    DBQuery = DBQuery + "'"+str(obj3[InterfacesDict[value3][0]])+"'\n"
                                i = i + 1

                            DBQuery = DBQuery + """                                                )\n"""

                            if debugSQL: print("debug: "+str(DBQuery))
                            if not DBUpdateDisable: outputCursor.execute(DBQuery)
                            outputDB.commit()

                    print("Total "+str(IfNumber)+" interfaces found from parsing. Total "+str(len(InterfacesDBAll))+" are already in database: "+str(IfNew)+" new, "+str(IfUpdated)+" updated, "+str(IfKept)+" are up to date, "+str(IfDeleted)+" deleted")
                    # if debug: print("debug: IfIDs matched "+str(IDMatched))

                if debug: input("Non-existing interfaces are deleted from the database. Press any key proceed.\r\n")

    outputDB.close()

#####################################################################################################################################################
#####################################################################################################################################################
#####################################################################################################################################################










#####################################################################################################################################################
###########################################################       Output function         ###########################################################
#####################################################################################################################################################
def outputFunc(inputDB,outputPath,fileFormat,targSyntax):
    print("Generating output\r\n")

    inputCursor = inputDB.cursor()

    # Getting all existing nodes from the DB
    # if debugSQL: print("debug: DBResponse: "+str(DBResponse))
    DBQuery="""SELECT *
                FROM Nodes
                ORDER BY Hostname ASC
                """
    if debugSQL: print("debug: DBQuery: "+str(DBQuery))
    inputCursor.execute(DBQuery)
    DBResponse=inputCursor.fetchall()
    NodesDBAll=DBResponse
    if debugSQL: print("debug: DBResponse: "+str(DBResponse))

    InterfacesDBSrcAll = []
    InterfacesDBHistAll = []
    InterfacesDBDstAll = []
    PeeringDBSrcAll = []
    PeeringDBHistAll = []
    PeeringDBDstAll = []
    # Getting all data for all supported syntaxes from the DB
    for value1 in SyntaxDict:

        # Getting all existing interfaces from the DB
        DBQuery="""SELECT * FROM Interfaces"""+str(SyntaxDict[value1])+""" ORDER BY Hostname ASC, CLISyntax ASC, IfNumber ASC\n"""
        if debugSQL: print("debug: DBQuery: "+str(DBQuery))
        inputCursor.execute(DBQuery)
        DBResponse=inputCursor.fetchall()
        if debugSQL: print("debug: DBResponse: "+str(DBResponse))
        if value1 == targSyntax:
            InterfacesDBDstAll = list(DBResponse)
        else:
            if value1 == "Hist":
                InterfacesDBHistAll.append(list(DBResponse))
            else:
                InterfacesDBSrcAll.append(list(DBResponse))

        # Getting all existing peerings from the DB
        DBQuery="""SELECT * FROM Peering"""+str(SyntaxDict[value1])+""" ORDER BY Hostname ASC, CLISyntax ASC, PeeringType ASC\n"""
        if debugSQL: print("debug: DBQuery: "+str(DBQuery))
        inputCursor.execute(DBQuery)
        DBResponse=inputCursor.fetchall()
        if debugSQL: print("debug: DBResponse: "+str(DBResponse))
        if value1 == targSyntax:
            PeeringDBDstAll = list(DBResponse)
        else:
            if value1 == "Hist":
                PeeringDBHistAll.append(list(DBResponse))
            else:
                PeeringDBSrcAll.append(list(DBResponse))

        # Getting all existing routing from the DB - TBD

    # Creating files
    if fileFormat == "csv":
        outputFile = open(("./"+outputPath),"w+",newline ='')
    if fileFormat == "xlsx":
        # with xlsxwriter.Workbook(outputPath) as outputFile:
        outputFile = xlsxwriter.Workbook(outputPath)

        headerSrc_format = outputFile.add_format()
        headerMid_format = outputFile.add_format()
        headerDst_format = outputFile.add_format()
        headerMatch_format = outputFile.add_format()

        lineSrc_format = outputFile.add_format()
        lineMid_format = outputFile.add_format()
        lineDst_format = outputFile.add_format()
        lineMatch_format = outputFile.add_format()

        headerSrc_format.set_font_name("Arial")
        headerSrc_format.set_align("center")
        headerSrc_format.set_align("vcenter")
        headerSrc_format.set_font_size("10")
        headerSrc_format.set_bold("bold")
        headerSrc_format.set_font_color("white")
        headerSrc_format.set_bg_color("black")
        headerSrc_format.set_num_format(49)

        headerMid_format.set_font_name("Arial")
        headerMid_format.set_align("center")
        headerMid_format.set_align("vcenter")
        headerMid_format.set_font_size("10")
        headerMid_format.set_bold("bold")
        headerMid_format.set_font_color("white")
        headerMid_format.set_bg_color("blue")
        headerMid_format.set_num_format(49)

        headerDst_format.set_font_name("Arial")
        headerDst_format.set_align("center")
        headerDst_format.set_align("vcenter")
        headerDst_format.set_font_size("10")
        headerDst_format.set_bold("bold")
        headerDst_format.set_font_color("white")
        headerDst_format.set_bg_color("green")
        headerDst_format.set_num_format(49)

        headerMatch_format.set_font_name("Arial")
        headerMatch_format.set_align("center")
        headerMatch_format.set_align("vcenter")
        headerMatch_format.set_font_size("10")
        headerMatch_format.set_bold("bold")
        headerMatch_format.set_font_color("white")
        headerMatch_format.set_bg_color("blue")
        headerMatch_format.set_num_format(49)

        lineSrc_format.set_font_name("Arial")
        lineSrc_format.set_font_size("9")
        lineSrc_format.set_align("vcenter")
        lineSrc_format.set_num_format(49)
        lineSrc_format.set_text_wrap()

        lineMid_format.set_font_name("Arial")
        lineMid_format.set_font_size("9")
        lineMid_format.set_align("vcenter")
        lineMid_format.set_font_color("blue")
        lineMid_format.set_text_wrap()

        lineDst_format.set_font_name("Arial")
        lineDst_format.set_font_size("9")
        lineDst_format.set_align("vcenter")
        lineDst_format.set_font_color("green")
        lineDst_format.set_num_format(49)
        lineDst_format.set_text_wrap()

        lineMatch_format.set_font_name("Arial")
        lineMatch_format.set_font_size("9")
        lineMatch_format.set_align("vcenter")
        lineMatch_format.set_font_color("red")
        lineMatch_format.set_bg_color("#C5D9F1")
        # lineMatch_format.set_num_format(49)

        if NodesDBAll is not None:
            NodesWorksheet = outputFile.add_worksheet("Nodes")
        if ((InterfacesDBSrcAll is not None) or (InterfacesDBDstAll is not None)):
            Interfaces1Worksheet = outputFile.add_worksheet("InterfacesData1")
            if targSyntax != "":
                Interfaces2Worksheet = outputFile.add_worksheet("InterfacesData2")
                InterfacesComparisonWorksheet = outputFile.add_worksheet("InterfacesComparison")
        # if InterfacesDBHistAll is not None:
        #     InterfacesHistWorksheet = outputFile.add_worksheet("InterfacesHist")


#####################################################################################################################################################
###########################################################         Nodes sheet           ###########################################################
#####################################################################################################################################################

    # Generating output header for Nodes
    lineNumber = 0
    valueNumber = 0
    for value in NodesDict:
        if fileFormat == "csv":
            value = value.replace(",","")
            # if valueNumber == (len(NodesDict) - 1):
            #     outputFile.write(str(value)+"\r\n")
            # else:
            #     outputFile.write(str(value)+",")
            if valueNumber == 0:
                outputFile.write(str(value))
            else:
                outputFile.write(","+str(value))
        if fileFormat == "xlsx":
            NodesWorksheet.write_string(lineNumber, valueNumber, str(value), headerSrc_format)
        # if debug: print("writing value "+str(value[1])+" in column "+str(valueNumber))
        valueNumber = valueNumber + 1

    if fileFormat == "csv": outputFile.write("\r\n")

    # Generating output values for Nodes
    lineNumber = 1
    for outputLine in NodesDBAll:
        valueNumber = 0
        for value in outputLine:
            if value is None: value = ""
            if fileFormat == "csv":
                value = value.replace(",","")
                if valueNumber == 0:
                    outputFile.write(str(value))
                else:
                    outputFile.write(","+str(value))
            if fileFormat == "xlsx":
                NodesWorksheet.write_string(lineNumber, valueNumber, str(value), lineSrc_format)
            # if debug: print("writing value "+str(value)+" in column "+str(valueNumber)+" on row "+str(lineNumber))
            valueNumber = valueNumber + 1

        if fileFormat == "csv": outputFile.write("\r\n")
        lineNumber = lineNumber + 1


#####################################################################################################################################################
######################################################          InterfacesData sheet           ######################################################
#####################################################################################################################################################

    # Generating output source header for Interfaces (contains interfaces of source syntaxes)
    lineNumber = 0
    valueNumber = 0
    for value in InterfacesDict:
        if fileFormat == "csv":
            value = value.replace(",","")
            if valueNumber == 0:
                outputFile.write(str(value))
            else:
                outputFile.write(","+str(value))
        if fileFormat == "xlsx":
            Interfaces1Worksheet.write_string(lineNumber, valueNumber, str(value), headerSrc_format)
            if targSyntax != "":
                Interfaces2Worksheet.write_string(lineNumber, valueNumber, str(value), headerSrc_format)
        # if debug: print("writing value "+str(value[1])+" in column "+str(valueNumber))
        valueNumber = valueNumber + 1

    # Generating output middle header for Interfaces (contains formulas for comparison|matching between source and destination)
    midHdrLenght = 3
    if fileFormat == "csv":
        outputFile.write(",Interface migrated")
        outputFile.write(",Difference in source")
        outputFile.write(",Difference in destination")
    if fileFormat == "xlsx":
        Interfaces1Worksheet.write_string(lineNumber, valueNumber, str("Migrated?"), headerMid_format)
        Interfaces1Worksheet.write_string(lineNumber, valueNumber+1, str("Difference in source"), headerMid_format)
        Interfaces1Worksheet.write_string(lineNumber, valueNumber+2, str("Difference in destination"), headerMid_format)
        if targSyntax != "":
            Interfaces2Worksheet.write_string(lineNumber, valueNumber, str("Migrated?"), headerMid_format)
            Interfaces2Worksheet.write_string(lineNumber, valueNumber+1, str("Difference in source"), headerMid_format)
            Interfaces2Worksheet.write_string(lineNumber, valueNumber+2, str("Difference in destination"), headerMid_format)
    # if debug: print("writing value "+str(value[1])+" in column "+str(valueNumber))
    valueNumber = valueNumber + midHdrLenght

    # Generating output destination header for Interfaces (contains interfaces of destination syntax)
    for value in InterfacesDict:
        if fileFormat == "csv":
            value = value.replace(",","")
            # if valueNumber == (2 * len(InterfacesDict) + midHdrLenght - 1):
            #     outputFile.write(str(value)+"\r\n")
            # else:
            #     outputFile.write(str(value)+",")
            outputFile.write(","+str(value))
        if fileFormat == "xlsx":
            Interfaces1Worksheet.write_string(lineNumber, valueNumber, str(value), headerDst_format)
            if targSyntax != "":
                Interfaces2Worksheet.write_string(lineNumber, valueNumber, str(value), headerDst_format)
        # if debug: print("writing value "+str(value[1])+" in column "+str(valueNumber))
        valueNumber = valueNumber + 1

    if fileFormat == "csv": outputFile.write("\r\n")

    # Generating output values for source Interfaces (contains interfaces of source syntaxes)
    lineNumber = 1
    IDMatched = []
    for InterfacesDBSrc in InterfacesDBSrcAll:
        for outputLine in InterfacesDBSrc:
            valueNumber = 0
            for value in outputLine:
                if value is None: value = ""
                if fileFormat == "csv":
                    value = value.replace(",","")
                    if valueNumber == 0:
                        outputFile.write(str(value))
                    else:
                        outputFile.write(","+str(value))
                if fileFormat == "xlsx":
                    value = value.replace(";","\r\n")
                    Interfaces1Worksheet.write_string(lineNumber, valueNumber, str(value), lineSrc_format)
                    if targSyntax != "":
                        Interfaces2Worksheet.write_string(lineNumber, valueNumber, str(value), lineSrc_format)
                # if debug: print("writing value "+str(value)+" in column "+str(valueNumber)+" on row "+str(lineNumber))
                valueNumber = valueNumber + 1

            # Generating output values for middle Interfaces (contains formulas for comparison|matching between source and destination)
            # Create formula, checking if interface is migrated to destination config
            Cell1Src = xlsxwriter.utility.xl_rowcol_to_cell(lineNumber, InterfacesDict["IfName"][0])  # Contains source IfID excel cell
            Cell1Dst = xlsxwriter.utility.xl_rowcol_to_cell(lineNumber, InterfacesDict["IfName"][0]+midHdrLenght+len(InterfacesDict))     # Contains destination IfID excel cell
            IfMigratedFromula = str("=IF(AND("+Cell1Src+"<>\"\","+Cell1Dst+"<>\"\"),\"Yes\",\"No\")")
            Cell2List = []   # Contains source and destination interfaces excel cells to be compared
            for value in InterfacesDict:
                # Exclude cells that are useless in comparison
                if ((value != "NodeID") and (value != "CLISyntax") and (value != "IfNumber") and (value != "ParentIfName") and (value != "IfName")
                        and (value != "PortName") and (value != "PortBinding") and (value != "SFPSN") and (value != "TxLevel") and (value != "RxLevel") and(value != "BridgeID")
                        and (value != "ServiceID") and (value != "ServiceDescr") and (value != "ServiceSDP") and (value != "CDP") and (value != "Comments") and (value != "LastUpdatedTime")
                        and (value != "LastUpdatedBy")):
                    Cell2Src = xlsxwriter.utility.xl_rowcol_to_cell(lineNumber, InterfacesDict[value][0])
                    Cell2Dst = xlsxwriter.utility.xl_rowcol_to_cell(lineNumber, InterfacesDict[value][0]+midHdrLenght+len(InterfacesDict))
                    Cell2List.append([Cell2Src,Cell2Dst])

            DiffSrcFromula = str("=IF(AND("+Cell1Src+"<>\"\","+Cell1Dst+"<>\"\"),CONCATENATE(")
            DiffDstFromula = str("=IF(AND("+Cell1Src+"<>\"\","+Cell1Dst+"<>\"\"),CONCATENATE(")
            j = 0
            for cellPair in Cell2List:
                if j < (len(Cell2List)-1):
                    DiffSrcFromula = DiffSrcFromula + str("IF(EXACT("+cellPair[0]+","+cellPair[1]+"),\"\",CONCATENATE("+cellPair[0]+",\"#\")),")
                    DiffDstFromula = DiffDstFromula + str("IF(EXACT("+cellPair[0]+","+cellPair[1]+"),\"\",CONCATENATE("+cellPair[1]+",\"#\")),")
                else:
                    DiffSrcFromula = DiffSrcFromula + str("IF(EXACT("+cellPair[0]+","+cellPair[1]+"),\"\",CONCATENATE("+cellPair[0]+",\"#\"))")
                    DiffDstFromula = DiffDstFromula + str("IF(EXACT("+cellPair[0]+","+cellPair[1]+"),\"\",CONCATENATE("+cellPair[1]+",\"#\"))")
                j = j + 1

            DiffSrcFromula = DiffSrcFromula + str("),\"\")")
            DiffDstFromula = DiffDstFromula + str("),\"\")")

            # if lineNumber == 3:
            #     print(len(Cell2List))
            #     print(DiffSrcFromula)
            #     print(DiffDstFromula)

            if fileFormat == "csv":
                outputFile.write(","+str(IfMigratedFromula.replace(",",";")))
                outputFile.write(","+str(DiffSrcFromula.replace(",",";")+","+DiffDstFromula.replace(",",";")))
            if fileFormat == "xlsx":
                Interfaces1Worksheet.write_formula(lineNumber, valueNumber, IfMigratedFromula, lineMid_format)
                Interfaces1Worksheet.write_formula(lineNumber, valueNumber+1, DiffSrcFromula, lineMid_format)
                Interfaces1Worksheet.write_formula(lineNumber, valueNumber+2, DiffDstFromula, lineMid_format)
                if targSyntax != "":
                    Interfaces2Worksheet.write_formula(lineNumber, valueNumber, IfMigratedFromula, lineMid_format)
                    Interfaces2Worksheet.write_formula(lineNumber, valueNumber+1, DiffSrcFromula, lineMid_format)
                    Interfaces2Worksheet.write_formula(lineNumber, valueNumber+2, DiffDstFromula, lineMid_format)
            valueNumber = valueNumber + midHdrLenght

            # Generating output values for destination interface matching particular source interface (matched by the same IfID)
            match = 0
            for outputLineDst in InterfacesDBDstAll:
                # print("Matching "+outputLine[InterfacesDict["IfID"][0]]+" to "+outputLineDst[InterfacesDict["IfID"][0]])
                if outputLineDst[InterfacesDict["IfID"][0]] == outputLine[InterfacesDict["IfID"][0]]:
                    match = 1
                    IDMatched.append(str(outputLineDst[InterfacesDict["IfID"][0]]))
                    for value in outputLineDst:
                        if value is None: value = ""
                        if fileFormat == "csv":
                            value = value.replace(",","")
                            outputFile.write(","+str(value))
                        if fileFormat == "xlsx":
                            value = value.replace(";","\r\n")
                            Interfaces1Worksheet.write_string(lineNumber, valueNumber, str(value), lineDst_format)
                            if targSyntax != "":
                                Interfaces2Worksheet.write_string(lineNumber, valueNumber, str(value), lineDst_format)
                        # if debug: print("writing value "+str(value)+" in column "+str(valueNumber)+" on row "+str(lineNumber))
                        valueNumber = valueNumber + 1
            if match == 0:
                for value in InterfacesDict:
                    if fileFormat == "csv":
                        outputFile.write(",")
                    if fileFormat == "xlsx":
                        Interfaces1Worksheet.write_string(lineNumber, valueNumber, str(""), lineDst_format)
                        if targSyntax != "":
                            Interfaces2Worksheet.write_string(lineNumber, valueNumber, str(""), lineDst_format)
                    # if debug: print("writing value "+str(value)+" in column "+str(valueNumber)+" on row "+str(lineNumber))
                    valueNumber = valueNumber + 1

            if fileFormat == "csv": outputFile.write("\r\n")
            lineNumber = lineNumber + 1

            # if lineNumber == 2: break


    # Generating output values for destination interface not matching any source interface
    for outputLineDst in InterfacesDBDstAll:
        if outputLineDst[InterfacesDict["IfID"][0]] not in IDMatched:
            valueNumber = 0
            for value in InterfacesDict:
                if fileFormat == "csv":
                    if valueNumber != 0:
                        outputFile.write(",")
                valueNumber = valueNumber + 1

            # Generating output values for middle Interfaces (contains formulas for comparison|matching between source and destination)
            # Create formula, checking if interface is migrated to destination config
            Cell1Src = xlsxwriter.utility.xl_rowcol_to_cell(lineNumber, InterfacesDict["IfName"][0])  # Contains source IfID excel cell
            Cell1Dst = xlsxwriter.utility.xl_rowcol_to_cell(lineNumber, InterfacesDict["IfName"][0]+midHdrLenght+len(InterfacesDict))     # Contains destination IfID excel cell
            IfMigratedFromula = str("=IF(AND("+Cell1Src+"<>\"\","+Cell1Dst+"<>\"\"),\"Yes\",\"No\")")
            Cell2List = []   # Contains source and destination interfaces excel cells to be compared
            for value in InterfacesDict:
                # Exclude cells that are useless in comparison
                if ((value != "NodeID") and (value != "CLISyntax") and (value != "IfNumber") and (value != "ParentIfName") and (value != "IfName")
                        and (value != "PortName") and (value != "PortBinding") and (value != "SFPSN") and (value != "TxLevel") and (value != "RxLevel") and(value != "BridgeID")
                        and (value != "ServiceID") and (value != "ServiceDescr") and (value != "ServiceSDP") and (value != "CDP") and (value != "Comments") and (value != "LastUpdatedTime")
                        and (value != "LastUpdatedBy")):
                    Cell2Src = xlsxwriter.utility.xl_rowcol_to_cell(lineNumber, InterfacesDict[value][0])
                    Cell2Dst = xlsxwriter.utility.xl_rowcol_to_cell(lineNumber, InterfacesDict[value][0]+midHdrLenght+len(InterfacesDict))
                    Cell2List.append([Cell2Src,Cell2Dst])

            DiffSrcFromula = str("=IF(AND("+Cell1Src+"<>\"\","+Cell1Dst+"<>\"\"),CONCATENATE(")
            DiffDstFromula = str("=IF(AND("+Cell1Src+"<>\"\","+Cell1Dst+"<>\"\"),CONCATENATE(")
            j = 0
            for cellPair in Cell2List:
                if j < (len(Cell2List)-1):
                    DiffSrcFromula = DiffSrcFromula + str("IF(EXACT("+cellPair[0]+","+cellPair[1]+"),\"\",CONCATENATE("+cellPair[0]+",\"#\")),")
                    DiffDstFromula = DiffDstFromula + str("IF(EXACT("+cellPair[0]+","+cellPair[1]+"),\"\",CONCATENATE("+cellPair[1]+",\"#\")),")
                else:
                    DiffSrcFromula = DiffSrcFromula + str("IF(EXACT("+cellPair[0]+","+cellPair[1]+"),\"\",CONCATENATE("+cellPair[0]+",\"#\"))")
                    DiffDstFromula = DiffDstFromula + str("IF(EXACT("+cellPair[0]+","+cellPair[1]+"),\"\",CONCATENATE("+cellPair[1]+",\"#\"))")
                j = j + 1

            DiffSrcFromula = DiffSrcFromula + str("),\"\")")
            DiffDstFromula = DiffDstFromula + str("),\"\")")

            if fileFormat == "csv":
                outputFile.write(","+str(IfMigratedFromula.replace(",",";")))
                outputFile.write(","+str(DiffSrcFromula.replace(",",";")+","+DiffDstFromula.replace(",",";")))
            if fileFormat == "xlsx":
                Interfaces1Worksheet.write_formula(lineNumber, valueNumber, IfMigratedFromula, lineMid_format)
                Interfaces1Worksheet.write_formula(lineNumber, valueNumber+1, DiffSrcFromula, lineMid_format)
                Interfaces1Worksheet.write_formula(lineNumber, valueNumber+2, DiffDstFromula, lineMid_format)
                if targSyntax != "":
                    Interfaces2Worksheet.write_formula(lineNumber, valueNumber, IfMigratedFromula, lineMid_format)
                    Interfaces2Worksheet.write_formula(lineNumber, valueNumber+1, DiffSrcFromula, lineMid_format)
                    Interfaces2Worksheet.write_formula(lineNumber, valueNumber+2, DiffDstFromula, lineMid_format)
            valueNumber = valueNumber + midHdrLenght


            # print("Matching "+outputLine[InterfacesDict["IfID"][0]]+" to "+outputLineDst[InterfacesDict["IfID"][0]])
            for value in outputLineDst:
                if value is None: value = ""
                if fileFormat == "csv":
                    value = value.replace(",","")
                    outputFile.write(","+str(value))
                if fileFormat == "xlsx":
                    value = value.replace(";","\r\n")
                    Interfaces1Worksheet.write_string(lineNumber, valueNumber, str(value), lineDst_format)
                    if targSyntax != "":
                        Interfaces2Worksheet.write_string(lineNumber, valueNumber, str(value), lineDst_format)
                # if debug: print("writing value "+str(value)+" in column "+str(valueNumber)+" on row "+str(lineNumber))
                valueNumber = valueNumber + 1

            if fileFormat == "csv": outputFile.write("\r\n")
            lineNumber = lineNumber + 1


#####################################################################################################################################################
#################################################           InterfacesComparison sheet             ##################################################
#####################################################################################################################################################

    if targSyntax != "":
        # Generating output source header for InterfacesComparison (contains interfaces of source syntaxes)
        lineNumber = 0
        valueNumber = 0
        for value in InterfacesDict:
            if fileFormat == "csv":

                value = value.replace(",","")
                if valueNumber == 0:
                    outputFile.write(str(value)+","+str(value))
                else:
                    outputFile.write(","+str(value)+","+str(value))

                # Exclude cells that are useless in comparison
                if ((value != "NodeID") and (value != "IfID") and (value != "CLISyntax") and (value != "IfNumber") and (value != "ParentIfName") and (value != "IfName") and (value != "PortName")
                            and (value != "SFPSN") and (value != "TxLevel") and (value != "RxLevel") and(value != "BridgeID") and (value != "ServiceID") and (value != "PortBinding")
                            and (value != "ServiceDescr") and (value != "ServiceSDP") and (value != "CDP") and (value != "Comments") and (value != "LastUpdatedTime")
                            and (value != "LastUpdatedBy")):

                    outputFile.write(",Match")

            if fileFormat == "xlsx":
                InterfacesComparisonWorksheet.write_string(lineNumber, valueNumber, str(value), headerSrc_format)
                InterfacesComparisonWorksheet.write_string(lineNumber, valueNumber+1, str(value), headerDst_format)
                # Exclude cells that are useless in comparison
                if ((value != "NodeID") and (value != "IfID") and (value != "CLISyntax") and (value != "IfNumber") and (value != "ParentIfName") and (value != "IfName") and (value != "PortName")
                            and (value != "SFPSN") and (value != "TxLevel") and (value != "RxLevel") and(value != "BridgeID") and (value != "ServiceID") and (value != "PortBinding")
                            and (value != "ServiceDescr") and (value != "ServiceSDP") and (value != "CDP") and (value != "Comments") and (value != "LastUpdatedTime")
                            and (value != "LastUpdatedBy")):

                    InterfacesComparisonWorksheet.write_string(lineNumber, valueNumber+2, "Match", headerMatch_format)
                    valueNumber = valueNumber + 1

            # if debug: print("writing value "+str(value[1])+" in column "+str(valueNumber))
            valueNumber = valueNumber + 2

        if fileFormat == "csv": outputFile.write("\r\n")

        # Generating output values for source InterfacesComparison (contains interfaces of source syntaxes)
        lineNumber = 1
        IDMatched = []
        for InterfacesDBSrc in InterfacesDBSrcAll:
            for outputLine in InterfacesDBSrc:
                match = 0
                valueNumberSource = 0
                valueNumberPrint = 0
                for valueSrc in outputLine:
                    if valueSrc is None: valueSrc = ""

                    # Generating output values for destination interface matching particular source interface (matched by the same IfID)
                    for outputLineDst in InterfacesDBDstAll:
                        valueNumberDestination = 0
                        # print("Matching "+outputLine[InterfacesDict["IfID"][0]]+" to "+outputLineDst[InterfacesDict["IfID"][0]])
                        if outputLineDst[InterfacesDict["IfID"][0]] == outputLine[InterfacesDict["IfID"][0]]:
                            match = 1
                            for valueDst in outputLineDst:
                                if valueNumberDestination == valueNumberSource:

                                    Cell3Src = xlsxwriter.utility.xl_rowcol_to_cell(lineNumber, valueNumberPrint)  # Contains source IfID excel cell
                                    Cell3Dst = xlsxwriter.utility.xl_rowcol_to_cell(lineNumber, valueNumberPrint+1)     # Contains destination IfID excel cell
                                    MatchFromula = str("=IF(AND("+Cell3Src+"<>\"\","+Cell3Dst+"<>\"\"),IF(EXACT("+Cell3Src+","+Cell3Dst+"),\"\",\"Not match\"),IF(OR("+Cell3Src+"<>\"\","+Cell3Dst+"<>\"\"),\"Missing\",\"\"))")

                                    if valueDst is None: valueDst = ""
                                    if fileFormat == "csv":
                                        valueSrc = valueSrc.replace(",","")
                                        valueDst = valueDst.replace(",","")

                                        if valueNumberSource == 0:
                                            outputFile.write(str(valueSrc)+","+str(valueDst))
                                        else:
                                            outputFile.write(","+str(valueSrc)+","+str(valueDst))

                                        for value in InterfacesDict:
                                            if InterfacesDict[value][0] == valueNumberDestination:
                                                # Exclude cells that are useless in comparison
                                                if ((value != "NodeID") and (value != "IfID") and (value != "CLISyntax") and (value != "IfNumber") and (value != "ParentIfName") and (value != "IfName") and (value != "PortName")
                                                            and (value != "SFPSN") and (value != "TxLevel") and (value != "RxLevel") and(value != "BridgeID") and (value != "ServiceID") and (value != "PortBinding")
                                                            and (value != "ServiceDescr") and (value != "ServiceSDP") and (value != "CDP") and (value != "Comments") and (value != "LastUpdatedTime")
                                                            and (value != "LastUpdatedBy")):

                                                    outputFile.write(","+str(MatchFromula.replace(",",";")))
                                                break

                                    if fileFormat == "xlsx":
                                        valueSrc = valueSrc.replace(";","\r\n")
                                        valueDst = valueDst.replace(";","\r\n")
                                        InterfacesComparisonWorksheet.write_string(lineNumber, valueNumberPrint, str(valueSrc), lineSrc_format)
                                        InterfacesComparisonWorksheet.write_string(lineNumber, valueNumberPrint+1, str(valueDst), lineDst_format)

                                        for value in InterfacesDict:
                                            if InterfacesDict[value][0] == valueNumberDestination:
                                                # Exclude cells that are useless in comparison
                                                if ((value != "NodeID") and (value != "IfID") and (value != "CLISyntax") and (value != "IfNumber") and (value != "ParentIfName") and (value != "IfName") and (value != "PortName")
                                                            and (value != "SFPSN") and (value != "TxLevel") and (value != "RxLevel") and(value != "BridgeID") and (value != "ServiceID") and (value != "PortBinding")
                                                            and (value != "ServiceDescr") and (value != "ServiceSDP") and (value != "CDP") and (value != "Comments") and (value != "LastUpdatedTime")
                                                            and (value != "LastUpdatedBy")):

                                                    InterfacesComparisonWorksheet.write_formula(lineNumber, valueNumberPrint+2, MatchFromula, lineMatch_format)
                                                    valueNumberPrint = valueNumberPrint + 1
                                                break

                                    # if debug: print("writing value "+str(value)+" in column "+str(valueNumber)+" on row "+str(lineNumber))

                                    valueNumberPrint = valueNumberPrint + 2
                                    break

                                valueNumberDestination = valueNumberDestination + 1

                    valueNumberSource = valueNumberSource + 1

                if match == 1:
                    if fileFormat == "csv": outputFile.write("\r\n")
                    lineNumber = lineNumber + 1


    outputFile.close()
#####################################################################################################################################################
#####################################################################################################################################################
#####################################################################################################################################################



#####################################################################################################################################################
###########################################################        Merge function         ###########################################################
#####################################################################################################################################################
def mergeFunc():
    print("Merging\r\n")

#####################################################################################################################################################
#####################################################################################################################################################
#####################################################################################################################################################



#####################################################################################################################################################
###########################################################       Collect function        ###########################################################
#####################################################################################################################################################
# def collectFunc(login,password,mgmtAddrList,outputPath,defaultCLISyntax,delay):
def collectFunc(login,password1,password2,hostAddr,outputPath,recursive):
    print("Trying to connect to " + str(hostAddr) + "...")
    startTime = time.time()
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    protocol = ""
    connectionCursor = ""
    SSHConnectionState = 0     # SSH connection not yet established
    TelnetConnectionState = 0     # Telnet connection not yet established
    # Establishing SSH connection
    for port in PortsDict["SSH"]: # Going though all defined SSH ports to establish connection
        print("Trying SSH to port " + str(port))
        try:
            client.connect(hostname=str(hostAddr), username=login, password=password1, port=str(port),look_for_keys=False, allow_agent=False, timeout=5)
            connectionCursor = client.invoke_shell()
            if connectionCursor != "":
                # print("connectionCursor " + str(connectionCursor))
                print("   Connection to port " + str(port) + " successfull")
                SSHConnectionState = 1     # SSH connection succeeded
                protocol = "ssh"
                time.sleep(1)              # Wait a bit while MotD loading
        except (paramiko.ssh_exception.AuthenticationException, paramiko.ssh_exception.BadAuthenticationType):
            print("   SSH authentication failed")
            SSHConnectionState = -1
            break
        except (socket.timeout, paramiko.ssh_exception.NoValidConnectionsError):
            print("   SSH connection to port " + str(port) + " timed out")
        except KeyboardInterrupt:
            break
        except:
            print("   Connection error: ", sys.exc_info()[0])

        if SSHConnectionState != 0: break

    if SSHConnectionState != 1:
        # Establishing Telnet connection
        for port in PortsDict["Telnet"]: # Going though all defined Telnet ports to establish connection
            print("Trying Telnet to port " + str(port))
            try:
                connectionCursor = telnetlib.Telnet(host=str(hostAddr), port=str(port), timeout=5)

                if connectionCursor != "":
                    # print("connectionCursor " + str(connectionCursor))
                    output1 = connectionCursor.expect([b'((U|u)ser)?name|(L|l)ogin'], timeout=3)
                    # print(output1[2].decode('utf-8'))
                    # print(output1)
                    if output1[0] == 0:
                        connectionCursor.write(login.encode('ascii') + b"\n")
                        time.sleep(1)
                        output2 = connectionCursor.expect([b'(P|p)assword'], timeout=3)
                        # print(output2[2].decode('utf-8'))
                        # print(output2)
                        if output2[0] == 0 :
                            connectionCursor.write(password1.encode('ascii') + b"\n")
                            time.sleep(1)
                            output3 = connectionCursor.expect([b'[a-zA-Z0-9\-_:]*(>|#)'], timeout=5)
                            # print(output3[2].decode('utf-8'))
                            # print(output3)
                            if output3[0] == 0:
                                connectionCursor.write(b"\n")
                                print("   Connection to port " + str(port) + " successfull")
                                TelnetConnectionState = 1     # Telnet connection succeeded
                                protocol = "telnet"
                                time.sleep(1)              # Wait a bit while MotD loading
                            else:
                                print("   Telnet authentication failed")
                                TelnetConnectionState = -1
                    else:
                        print("   No Telnet service found")
                        connectionCursor.close()
                        connectionCursor = ""
            except (socket.timeout):
                print("   Telnet connection to port " + str(port) + " timed out")
            except KeyboardInterrupt:
                break
            except:
                print("   Connection error: ", sys.exc_info()[0])

            if TelnetConnectionState != 0: break

    if (( connectionCursor != "" ) and ((TelnetConnectionState == 1) or (SSHConnectionState == 1))):

        # if (os.path.isfile("./" + outputPath + "/debugText.txt")):
        #     os.remove("./" + outputPath + "/debugText.txt")

        with open("./" + outputPath + "/debugText.txt", 'a') as debugTextFile:
            debugTextFile.write("\n\n#####\tDebug text for node " + str(hostAddr) + ". Created on " + str(datetime.datetime.today()) + ".\t#####\n\n")

        # Determine SW version and CLI syntax
        CLISyntax = ""

        # Issuing a Cisco/Nokia style command
        for attempt in range(0,2):
            versionLines = []
            versionLines.append("#####\tExecuting \"" + str(CommandsDict["IOS"][0][0]) + "\" with " + str(CommandsDict["IOS"][0][1]) + " second(s) timeout\t#####\n")
            print("Executing command \"" + str(CommandsDict["IOS"][0][0]) + "\"")
            output = execCLICommand(connectionCursor, protocol, CommandsDict["IOS"][0][0], CommandsDict["IOS"][0][1])
            # print("Collected "+ str(len(output[1])) + " lines of output")
            versionLines.extend(output[1])
            versionLines.append("\n#####\tExecuted with code " + str(output[0]) + " in " + str(round(output[2],2)) + " second(s)\t#####\n\n")
            if output[0] == 0: break

        # Trying to find shell prompt
        shellPrompt = ""
        for line in versionLines:
            if not re.match(r"^#+.*#+$",line):
                # Syntax: all
                if re.search(shellPromptRegex,line):
                    shellPrompt = line.lstrip().rstrip()
                    shellPrompt = re.split(r"((>|#|\$|\%))", shellPrompt)[0] + re.split(r"((>|#|\$|\%))", shellPrompt)[1]
                if shellPrompt != "":
                    print("Found shell prompt: "+shellPrompt)
                    break

        # Trying to find CLI syntax of Cisco/Nokia node
        for line in versionLines:
            searchExpression = r'.*Cisco IOS XR'
            if re.match(searchExpression,line):
                CLISyntax = "IOS-XR"
                break
            searchExpression = r'.*Cisco IOS((-| )XE)? '
            if re.match(searchExpression,line):
                CLISyntax = "IOS"
                break
            searchExpression = r'.*TiMOS-'
            if re.match(searchExpression,line):
                CLISyntax = "SR-OS"
                break


        if CLISyntax == "":
            # Issuing a Huawei style command

            for attempt in range(0,2):
                versionLines = []
                versionLines.append("#####\tExecuting \"" + str(CommandsDict["VRP"][0][0]) + "\" with " + str(CommandsDict["VRP"][0][1]) + " second(s) timeout\t#####\n")
                print("Executing command \"" + str(CommandsDict["VRP"][0][0]) + "\"")
                output = execCLICommand(connectionCursor, protocol, CommandsDict["VRP"][0][0], CommandsDict["VRP"][0][1])
                # print("Collected "+ str(len(output[1])) + " lines of output")
                versionLines.extend(output[1])
                versionLines.append("\n#####\tExecuted with code " + str(output[0]) + " in " + str(round(output[2],2)) + " second(s)\t#####\n\n")
                if output[0] == 0: break


            # Trying to find CLI syntax of Hiawei node
            for line in versionLines:
                searchExpression = r'.*VRP \(R\) software'
                if re.match(searchExpression,line):
                    CLISyntax = "VRP"
                    break

        # if debug:
        #     with open("./" + outputPath + "/debugText.txt", 'a') as debugTextFile:
        #         debugTextFile.write("\n".join(str(item) for item in versionLines))

        if CLISyntax == "":
            print("Could not determine CLI syntax, skipping to next node")
            return
        else:
            print("Using following command syntax for this node: "+CLISyntax)

        # Vendor-specific preparation phase
        enableLines = []
        if CLISyntax == "IOS":
            if re.search(r'>',shellPrompt):

                for attempt in range(0,2):
                    enableLines.append("#####\tExecuting \"enable\" with 20 second(s) timeout\t#####\n")
                    print("Executing command \"enable\"")
                    output = execCLICommand(connectionCursor, protocol, "enable\n" + password2, 20)
                    # print("Collected "+ str(len(output[1])) + " lines of output")
                    enableLines.extend(output[1])
                    enableLines.append("\n#####\tExecuted with code " + str(output[0]) + " in " + str(round(output[2],2)) + " second(s)\t#####\n\n")
                    if output[0] == 0: break

                # if debug:
                #     with open("./" + outputPath + "/debugText.txt", 'a') as debugTextFile:
                #         debugTextFile.write("\n".join(str(item) for item in enableLines))

                shellPrompt = shellPrompt.replace(">","#")
                # print("Looking for: " + shellPrompt.replace(">","#"))
                searchExpression = re.escape(shellPrompt)
                match = 0
                for line in output[1]:
                    if re.search(searchExpression, line):
                        match = 1
                        break
                if match == 1:
                    for attempt in range(0,2):
                        versionLines = []
                        versionLines.append("#####\tExecuting \"" + str(CommandsDict["IOS"][0][0]) + "\" with " + str(CommandsDict["IOS"][0][1]) + " second(s) timeout\t#####\n")
                        print("Executing command \"" + str(CommandsDict["IOS"][0][0]) + "\"")
                        output = execCLICommand(connectionCursor, protocol, CommandsDict["IOS"][0][0], CommandsDict["IOS"][0][1])
                        # print("Collected "+ str(len(output[1])) + " lines of output")
                        versionLines.extend(output[1])
                        versionLines.append("\n#####\tExecuted with code " + str(output[0]) + " in " + str(round(output[2],2)) + " second(s)\t#####\n\n")
                        if output[0] == 0: break

                    print("Using new shell prompt: "+shellPrompt)

                    # if debug:
                    #     with open("./" + outputPath + "/debugText.txt", 'a') as debugTextFile:
                    #         debugTextFile.write("\n".join(str(item) for item in versionLines))

                else:
                    print("Could not activate enable mode, skipping to next node")
                    return


        ################################################### Disable terminal paging ###################################################
        for attempt in range(0,2):
            termLengthLines = []
            termLengthLines.append("#####\tExecuting \"" + str(CommandsDict[CLISyntax][1][0]) + "\" with " + str(CommandsDict[CLISyntax][1][1]) + " second(s) timeout\t#####\n")
            print("Executing command \"" + str(CommandsDict[CLISyntax][1][0]) + "\"")
            output = execCLICommand(connectionCursor, protocol, CommandsDict[CLISyntax][1][0], CommandsDict[CLISyntax][1][1])
            # print("Collected "+ str(len(output[1])) + " lines of output")
            termLengthLines.extend(output[1])
            termLengthLines.append("\n#####\tExecuted with code " + str(output[0]) + " in " + str(round(output[2],2)) + " second(s)\t#####\n\n")
            if output[0] == 0: break

        ################################################### Show current configuration ###################################################
        for attempt in range(0,2):
            configLines = []
            configLines.append("#####\tExecuting \"" + str(CommandsDict[CLISyntax][2][0]) + "\" with " + str(CommandsDict[CLISyntax][2][1]) + " second(s) timeout\t#####\n")
            print("Executing command \"" + str(CommandsDict[CLISyntax][2][0]) + "\"")
            output = execCLICommand(connectionCursor, protocol, CommandsDict[CLISyntax][2][0], CommandsDict[CLISyntax][2][1])
            # print("Collected "+ str(len(output[1])) + " lines of output")
            configLines.extend(output[1])
            configLines.append("\n#####\tExecuted with code " + str(output[0]) + " in " + str(round(output[2],2)) + " second(s)\t#####\n\n")
            if output[0] == 0: break

        ################################################### Parse configuration ###################################################
        configLinesToParser = []
        for line in configLines:                                    # Cleaning configLines before parsing
            if not re.search(re.escape(shellPrompt) + r" *$",line):            # Remove shell prompt
                if not re.search(r'^ *[#!]',line):                  # Remove all comments
                    if not re.search(r'echo "',line):               # Remove SR-OS echo lines
                        if not re.search(r'^$',line):               # Remove empty lines
                            if CLISyntax == "SR-OS":
                                line = line.replace("    "," ")     # Replace SR-OS indentation to single spaces
                            configLinesToParser.append(line)

        cfg = CiscoConfParse(configLinesToParser)                   # Parse configLines using CiscoConfParse library

        ################################################### Find Hostname ###################################################
        Hostname = ""
        # Syntax: Cisco IOS/IOS-XE/IOS-XR
        if ((CLISyntax == "IOS") or (CLISyntax == "IOS-XR")):
            for obj1 in cfg.find_objects("^hostname"):       # Find node's Hostname from config
                # if debug: print("debug: obj1: "+str(obj1))
                Hostname = obj1.text.split(" ")[1]
                if debug: print("debug: Found Hostname in configuration file and updated to: "+Hostname)
                break
        # Syntax: Huawei VRP
        if (CLISyntax == "VRP"):
            for obj1 in cfg.find_objects("^sysname"):       # Find node's Hostname from config
                # if debug: print("debug: obj1: "+str(obj1))
                Hostname = obj1.text.split(" ")[1]
                if debug: print("debug: Found Hostname in configuration file and updated to: "+Hostname)
                break
        # Syntax: ALU/Nokia SR-OS
        if (CLISyntax == "SR-OS"):
            for obj1 in cfg.find_objects(" *name"):       # Find node's Hostname from config
                print(obj1)
                # if debug: print("debug: obj1: "+str(obj1))
                Hostname = obj1.text.split(" \"")[1].split("\"")[0]
                if debug: print("debug: Found Hostname in configuration file and updated to: "+Hostname)
                break
        # Setting default Hostname
        if Hostname == "":
            if re.search(":",shellPrompt):
                # Hostname = shellPrompt.split(":")[1].replace(r"[#>\|\.\,\ \\\/\:]","")
                Hostname = re.sub(r"[\.:@\{\}~\/\\ \t\*<\[>#\$\%\]]","",shellPrompt.split(":")[1])
            else:
                # Hostname = shellPrompt.replace(r"[#>\|\.\,\ \\\/\:]","")
                Hostname = re.sub(r"[\.:@\{\}~\/\\ \t\*<\[>#\$\%\]]","",shellPrompt)

        ################################################### Find system/loopback0 address ###################################################
        SysAddr = ""
        # Syntax: Cisco IOS-XR
        if (CLISyntax == "IOS-XR"):
            for obj1 in cfg.find_objects("^interface Loopback0"):       # Find node's system/loopback0 address from config
                # if debug: print("debug: obj1: "+str(obj1))
                for obj2 in obj1.re_search_children("ipv4 address "):    #Find all IPv4 addresses associated with current interface (IOS-XR syntax)
                    # if debug: print("debug: obj2: "+str(obj2))
                    if re.search(r"/",obj2.text):
                        SysAddr = obj2.text.split("ipv4 address ")[1].split("/")[0]
                    else:
                        SysAddr = obj2.text.split("ipv4 address ")[1].split(" ")[0]
                    if debug: print("debug: SysAddr: "+str(SysAddr))
                    break
                break
        # Syntax: Cisco IOS/IOS-XE
        if (CLISyntax == "IOS"):
            for obj1 in cfg.find_objects("^interface Loopback0"):       # Find node's system/loopback0 address from config
                # if debug: print("debug: obj1: "+str(obj1))
                for obj2 in obj1.re_search_children("ip address "):    #Find all IPv4 addresses associated with current interface (IOS/IOS-XE syntax)
                    # if debug: print("debug: obj2: "+str(obj2))
                    if re.search("/",obj2.text):
                        SysAddr = obj2.text.split("ip address ")[1].split("/")[0]
                    else:
                        SysAddr = obj2.text.split("ip address ")[1].split(" ")[0]
                    if debug: print("debug: SysAddr: "+str(SysAddr))
                    break
                break
        # Syntax: Huawei VRP
        if (CLISyntax == "VRP"):
            for obj1 in cfg.find_objects("^interface LoopBack0"):       # Find node's system/loopback0 address from config
                # if debug: print("debug: obj1: "+str(obj1))
                for obj2 in obj1.re_search_children("ip address "):    #Find all IPv4 addresses associated with current interface (VRP syntax)
                    # if debug: print("debug: obj2: "+str(obj2))
                    SysAddr = obj2.text.split("address ")[1].split(" ")[0]
                    if debug: print("debug: SysAddr: "+str(SysAddr))
                    break
                break
        # Syntax: ALU/Nokia SR-OS
        if (CLISyntax == "SR-OS"):
            for obj1 in cfg.find_objects("^ *interface \"system\""):       # Find node's system/loopback0 address from config
                # if debug: print("debug: obj1: "+str(obj1))
                for obj2 in obj1.re_search_children("address "):    #Find all IPv4 addresses associated with current interface (SR-OS syntax)
                    # if debug: print("debug: obj2: "+str(obj2))
                    SysAddr = obj2.text.split("address ")[1].split("/")[0]
                    if debug: print("debug: SysAddr: "+str(SysAddr))
                    break
                break

        ################################################### Create an output file for this node ###################################################

        outputFilePath = outputPath + "/" + Hostname + "_" + SysAddr + "_" + CLISyntax + "_" + datetime.datetime.today().strftime("%Y-%m-%d_%H-%M-%S") +".txt"
        if (os.path.isfile(outputFilePath)):
            os.remove(outputFilePath)

        print("Configuration parsed, creating output file.")

        with open(outputFilePath, 'a') as outputFile:
            outputFile.write("#####\tNode " + Hostname + "[" + str(SysAddr) + "]" + " via " + str(hostAddr) + " over " + protocol + " on " + datetime.datetime.today().strftime("%Y-%m-%d %H:%M:%S") +"\t#####\n")
            outputFile.write("\n".join(str(item) for item in versionLines))
            outputFile.write("\n".join(str(item) for item in enableLines))
            outputFile.write("\n".join(str(item) for item in termLengthLines))
            outputFile.write("\n".join(str(item) for item in configLines))

        ################################################### Parse interfaces and addresses from config ###################################################

        InterfacesParseAll = []

        if (CLISyntax == "IOS-XR"):
            # Perform 3 runs: 1st detects all IP/IPv6 interfaces, 2nd detects all other LAGs/BDIs, 3rd detects all ports left
            for run in range(0,2):
                for obj1 in cfg.find_objects(r"^interface"):
                    # Looking for GRT interfaces only
                    if (( not obj1.re_search_children(r"vrf |xconnect |l2vpn") ) and ( not re.search(r"l2transport",obj1.text))):
                        InterfacesParse = [""] * len(InterfacesDict)

                        if re.search(" preconfigure ",obj1.text): continue

                        InterfacesParse[InterfacesDict["IfName"][0]] = obj1.text.split("interface ")[1].split()[0]

                        # Find description associated with current interface
                        for obj2 in obj1.re_search_children("description "):
                            InterfacesParse[InterfacesDict["IfDescr"][0]] = str(obj2.text.split("description ")[1].replace("\"",""))
                            break

                        # Find all IPv4 addresses associated with current interface
                        for obj2 in obj1.re_search_children("ipv4 address "):
                            rawInput = obj2.text.split("ipv4 address ")[1].lstrip().rstrip()
                            rawInput = rawInput.replace(" ","/")
                            ipadd = ipaddress.ip_interface(str(rawInput))
                            if InterfacesParse[InterfacesDict["IPV4Addr"][0]] == "":
                                InterfacesParse[InterfacesDict["IPV4Addr"][0]] = str(ipadd)
                            else:
                                InterfacesParse[InterfacesDict["IPV4Addr"][0]] = InterfacesParse[InterfacesDict["IPV4Addr"][0]] + "|" + str(ipadd)
                            if InterfacesParse[InterfacesDict["IPV4Subnet"][0]] == "":
                                InterfacesParse[InterfacesDict["IPV4Subnet"][0]] = str(ipadd.network)
                            else:
                                InterfacesParse[InterfacesDict["IPV4Subnet"][0]] = InterfacesParse[InterfacesDict["IPV4Subnet"][0]] + "|"+ str(ipadd.network)

                        # Find all IPv6 addresses associated with current interface
                        for obj2 in obj1.re_search_children("ipv6 address "):
                            rawInput = obj2.text.split("ipv6 address ")[1].lstrip().rstrip()
                            ipadd = ipaddress.ip_interface(str(line))
                            if InterfacesParse[InterfacesDict["IPV6Addr"][0]] == "":
                                InterfacesParse[InterfacesDict["IPV6Addr"][0]] = str(ipadd)
                            else:
                                InterfacesParse[InterfacesDict["IPV6Addr"][0]] = InterfacesParse[InterfacesDict["IPV6Addr"][0]] + "|" + str(ipadd)
                            if InterfacesParse[InterfacesDict["IPV6Subnet"][0]] == "":
                                InterfacesParse[InterfacesDict["IPV6Subnet"][0]] = str(ipadd.network)
                            else:
                                InterfacesParse[InterfacesDict["IPV6Subnet"][0]] = InterfacesParse[InterfacesDict["IPV6Subnet"][0]] + "|" + str(ipadd.network)

                        # Check if interface is a bundle
                        if not re.search(r'[Bb]undle-[Ee]ther',InterfacesParse[InterfacesDict["IfName"][0]]):
                            if re.search(r'\.',InterfacesParse[InterfacesDict["IfName"][0]]):
                                InterfacesParse[InterfacesDict["PortName"][0]] = InterfacesParse[InterfacesDict["IfName"][0]].split(".")[0]
                            else:
                                InterfacesParse[InterfacesDict["PortName"][0]] = InterfacesParse[InterfacesDict["IfName"][0]]
                        else:
                            if re.search(r'\.',InterfacesParse[InterfacesDict["IfName"][0]]):
                                tempLAGID = str(InterfacesParse[InterfacesDict["IfName"][0]].split("ther")[1].split(".")[0])
                            else:
                                tempLAGID = str(InterfacesParse[InterfacesDict["IfName"][0]].split("ther")[1])

                            # Find ports associated with this LAG
                            for obj20 in cfg.find_objects(r"^interface"):
                                if (( not re.search(r'[Bb]undle-[Ee]ther',obj20.text) ) and ( not re.search(r'\.',obj20.text) )):
                                    searchExpression = r"^ *bundle id " + tempLAGID + r"[a-zA-Z ]*$"
                                    for obj21 in obj20.re_search_children(searchExpression):
                                        if InterfacesParse[InterfacesDict["PortName"][0]] != "":
                                            InterfacesParse[InterfacesDict["PortName"][0]] = InterfacesParse[InterfacesDict["PortName"][0]] + "|"
                                        InterfacesParse[InterfacesDict["PortName"][0]] = InterfacesParse[InterfacesDict["PortName"][0]] + obj20.text.split("interface ")[1].split()[0]
                                        break


                        # Addind only IP/IPv6 interfaces
                        if run == 0:
                            if (( InterfacesParse[InterfacesDict["IPV4Addr"][0]] != "" ) or (InterfacesParse[InterfacesDict["IPV6Addr"][0]] != "" )):
                                InterfacesParse = [element.rstrip().lstrip() for element in InterfacesParse]
                                # print(InterfacesParse)
                                InterfacesParseAll.append(InterfacesParse)
                        # Addind all other LAGs
                        if run == 1:
                            if (( InterfacesParse[InterfacesDict["IPV4Addr"][0]] == "" ) and (InterfacesParse[InterfacesDict["IPV6Addr"][0]] == "" )):
                                if re.search(r'[Bb]undle-[Ee]ther',InterfacesParse[InterfacesDict["IfName"][0]]):

                                    match = 0
                                    for line in InterfacesParseAll:
                                        if InterfacesParse[InterfacesDict["PortName"][0]] == line[InterfacesDict["PortName"][0]]:
                                            match = 1

                                    if match == 0:
                                        InterfacesParse = [element.rstrip().lstrip() for element in InterfacesParse]
                                        # print(InterfacesParse)
                                        InterfacesParseAll.append(InterfacesParse)

                        # Addind all other ports
                        if run == 1:
                            if (( InterfacesParse[InterfacesDict["IPV4Addr"][0]] == "" ) and (InterfacesParse[InterfacesDict["IPV6Addr"][0]] == "" )):
                                if not re.search(r'[Bb]undle-[Ee]ther',InterfacesParse[InterfacesDict["IfName"][0]]):

                                    match = 0
                                    for line in InterfacesParseAll:
                                        if InterfacesParse[InterfacesDict["PortName"][0]] in line[InterfacesDict["PortName"][0]]:
                                            match = 1

                                    if match == 0:
                                        InterfacesParse = [element.rstrip().lstrip() for element in InterfacesParse]
                                        # print(InterfacesParse)
                                        InterfacesParseAll.append(InterfacesParse)

        if (CLISyntax == "IOS"):
            # Perform 3 runs: 1st detects all IP/IPv6 interfaces, 2nd detects all other LAGs/BDIs, 3rd detects all ports left
            for run in range(0,2):
                for obj1 in cfg.find_objects(r"^interface"):
                    # Looking for non-VRF interfaces only
                    if (( not obj1.re_search_children(r"vrf |xconnect |l2vpn") ) and ( not re.search(r"l2transport",obj1.text))):
                        InterfacesParse = [""] * len(InterfacesDict)

                        InterfacesParse[InterfacesDict["IfName"][0]] = obj1.text.split("interface ")[1].split()[0]

                        # Find description associated with current interface
                        for obj2 in obj1.re_search_children("description "):
                            InterfacesParse[InterfacesDict["IfDescr"][0]] = str(obj2.text.split("description ")[1].replace("\"",""))
                            break

                        # Find all IPv4 addresses associated with current interface
                        for obj2 in obj1.re_search_children("ip address "):
                            rawInput = obj2.text.split("ip address ")[1].split("secondary")[0].lstrip().rstrip()
                            rawInput = rawInput.replace(" ","/")
                            ipadd = ipaddress.ip_interface(str(rawInput))
                            if InterfacesParse[InterfacesDict["IPV4Addr"][0]] == "":
                                InterfacesParse[InterfacesDict["IPV4Addr"][0]] = str(ipadd)
                            else:
                                InterfacesParse[InterfacesDict["IPV4Addr"][0]] = InterfacesParse[InterfacesDict["IPV4Addr"][0]] + "|" + str(ipadd)
                            if InterfacesParse[InterfacesDict["IPV4Subnet"][0]] == "":
                                InterfacesParse[InterfacesDict["IPV4Subnet"][0]] = str(ipadd.network)
                            else:
                                InterfacesParse[InterfacesDict["IPV4Subnet"][0]] = InterfacesParse[InterfacesDict["IPV4Subnet"][0]] + "|"+ str(ipadd.network)

                        # Find all IPv6 addresses associated with current interface
                        for obj2 in obj1.re_search_children("ipv6 address "):
                            rawInput = obj2.text.split("ipv6 address ")[1].lstrip().rstrip()
                            ipadd = ipaddress.ip_interface(str(line))
                            if InterfacesParse[InterfacesDict["IPV6Addr"][0]] == "":
                                InterfacesParse[InterfacesDict["IPV6Addr"][0]] = str(ipadd)
                            else:
                                InterfacesParse[InterfacesDict["IPV6Addr"][0]] = InterfacesParse[InterfacesDict["IPV6Addr"][0]] + "|" + str(ipadd)
                            if InterfacesParse[InterfacesDict["IPV6Subnet"][0]] == "":
                                InterfacesParse[InterfacesDict["IPV6Subnet"][0]] = str(ipadd.network)
                            else:
                                InterfacesParse[InterfacesDict["IPV6Subnet"][0]] = InterfacesParse[InterfacesDict["IPV6Subnet"][0]] + "|" + str(ipadd.network)

                        # Check if interface is not a bundle or BDI
                        if not re.search(r'([Pp]ort-[Cc]hannel)|BDI',InterfacesParse[InterfacesDict["IfName"][0]]):
                            if re.search(r'\.',InterfacesParse[InterfacesDict["IfName"][0]]):
                                InterfacesParse[InterfacesDict["PortName"][0]] = InterfacesParse[InterfacesDict["IfName"][0]].split(".")[0]
                            else:
                                InterfacesParse[InterfacesDict["PortName"][0]] = InterfacesParse[InterfacesDict["IfName"][0]]
                        else:
                            # Check if interface is a BDI
                            if re.search(r'BDI',InterfacesParse[InterfacesDict["IfName"][0]]):
                                tempBridgeID = str(InterfacesParse[InterfacesDict["IfName"][0]].split("BDI")[1].split(".")[0])
                                # Find ports associated with this Bridge
                                for obj20 in cfg.find_objects(r"^interface"):
                                    # Find bridge-domain IDs and respective VLANs associated with current interface
                                    for obj11 in obj20.re_search_children("service instance "):
                                        for obj12 in obj11.re_search_children("bridge-domain "):
                                            if tempBridgeID == obj12.text.split("bridge-domain ")[1].split()[0]:
                                                # Check if found interface is a bundle
                                                if re.search(r'[Pp]ort-[Cc]hannel',obj20.text.split("interface")[1]):
                                                    if re.search(r'\.',obj20.text.split("interface")[1]):
                                                        tempLAGID = str(obj20.text.split("interface")[1].split("nnel")[1].split(".")[0])
                                                    else:
                                                        tempLAGID = str(obj20.text.split("interface")[1].split("nnel")[1])

                                                        # Find ports associated with this LAG
                                                        for obj30 in cfg.find_objects(r"^interface"):
                                                            if (( not re.search(r'[Pp]ort-[Cc]hannel',obj30.text) ) and ( not re.search(r'\.',obj30.text) )):
                                                                searchExpression = r"^ *channel-group " + tempLAGID + r"[a-zA-Z ]*$"
                                                                for obj31 in obj30.re_search_children(searchExpression):
                                                                    if InterfacesParse[InterfacesDict["PortName"][0]] != "":
                                                                        InterfacesParse[InterfacesDict["PortName"][0]] = InterfacesParse[InterfacesDict["PortName"][0]] + "|"
                                                                    InterfacesParse[InterfacesDict["PortName"][0]] = InterfacesParse[InterfacesDict["PortName"][0]] + obj20.text.split("interface ")[1].split()[0]
                                                                    break
                                                else:
                                                    if InterfacesParse[InterfacesDict["PortName"][0]] != "":
                                                        InterfacesParse[InterfacesDict["PortName"][0]] = InterfacesParse[InterfacesDict["PortName"][0]] + "|"
                                                    InterfacesParse[InterfacesDict["PortName"][0]] = InterfacesParse[InterfacesDict["PortName"][0]] + obj20.text.split("interface ")[1].split()[0]
                            else:
                                # Check if interface is a bundle
                                if re.search(r'[Pp]ort-[Cc]hannel',InterfacesParse[InterfacesDict["IfName"][0]]):
                                    if re.search(r'\.',InterfacesParse[InterfacesDict["IfName"][0]]):
                                        tempLAGID = str(InterfacesParse[InterfacesDict["IfName"][0]].split("nnel")[1].split(".")[0])
                                    else:
                                        tempLAGID = str(InterfacesParse[InterfacesDict["IfName"][0]].split("nnel")[1])

                                    # Find ports associated with this LAG
                                    for obj20 in cfg.find_objects(r"^interface"):
                                        if (( not re.search(r'[Pp]ort-[Cc]hannel',obj20.text) ) and ( not re.search(r'\.',obj20.text) )):
                                            searchExpression = r"^ *channel-group " + tempLAGID + r"[a-zA-Z ]*$"
                                            for obj21 in obj20.re_search_children(searchExpression):
                                                if InterfacesParse[InterfacesDict["PortName"][0]] != "":
                                                    InterfacesParse[InterfacesDict["PortName"][0]] = InterfacesParse[InterfacesDict["PortName"][0]] + "|"
                                                InterfacesParse[InterfacesDict["PortName"][0]] = InterfacesParse[InterfacesDict["PortName"][0]] + obj20.text.split("interface ")[1].split()[0]
                                                break

                        # Addind only IP/IPv6 interfaces
                        if run == 0:
                            if (( InterfacesParse[InterfacesDict["IPV4Addr"][0]] != "" ) or (InterfacesParse[InterfacesDict["IPV6Addr"][0]] != "" )):
                                InterfacesParse = [element.rstrip().lstrip() for element in InterfacesParse]
                                # print(InterfacesParse)
                                InterfacesParseAll.append(InterfacesParse)
                        # Addind all other BDIs/LAGs
                        if run == 1:
                            if (( InterfacesParse[InterfacesDict["IPV4Addr"][0]] == "" ) and (InterfacesParse[InterfacesDict["IPV6Addr"][0]] == "" )):
                                if re.search(r'([Pp]ort-[Cc]hannel)|BDI',InterfacesParse[InterfacesDict["IfName"][0]]):

                                    match = 0
                                    for line in InterfacesParseAll:
                                        if InterfacesParse[InterfacesDict["PortName"][0]] == line[InterfacesDict["PortName"][0]]:
                                            match = 1

                                    if match == 0:
                                        InterfacesParse = [element.rstrip().lstrip() for element in InterfacesParse]
                                        # print(InterfacesParse)
                                        InterfacesParseAll.append(InterfacesParse)

                        # Addind all other ports
                        if run == 1:
                            if (( InterfacesParse[InterfacesDict["IPV4Addr"][0]] == "" ) and (InterfacesParse[InterfacesDict["IPV6Addr"][0]] == "" )):
                                if not re.search(r'([Pp]ort-[Cc]hannel)|BDI',InterfacesParse[InterfacesDict["IfName"][0]]):

                                    match = 0
                                    for line in InterfacesParseAll:
                                        if InterfacesParse[InterfacesDict["PortName"][0]] in line[InterfacesDict["PortName"][0]]:
                                            match = 1

                                    if match == 0:
                                        InterfacesParse = [element.rstrip().lstrip() for element in InterfacesParse]
                                        # print(InterfacesParse)
                                        InterfacesParseAll.append(InterfacesParse)

        if (CLISyntax == "VRP"):
            # Perform 3 runs: 1st detects all IP/IPv6 interfaces, 2nd detects all other LAGs/BDIs, 3rd detects all ports left
            for run in range(0,2):
                for obj1 in cfg.find_objects(r"^interface"):
                    # Looking for GRT interfaces only
                    if not obj1.re_search_children("ip binding vpn-instance"):
                        InterfacesParse = [""] * len(InterfacesDict)

                        InterfacesParse[InterfacesDict["IfName"][0]] = obj1.text.split("interface ")[1].split()[0]

                        # Find description associated with current interface
                        for obj2 in obj1.re_search_children("description "):
                            InterfacesParse[InterfacesDict["IfDescr"][0]] = str(obj2.text.split("description ")[1].replace("\"",""))
                            break

                        # Find all IPv4 addresses associated with current interface
                        for obj2 in obj1.re_search_children("ip address "):
                            if not re.search("ip address unnumbered interface", obj2.text):
                                rawInput = obj2.text.split("ip address ")[1].lstrip().rstrip()
                                rawInput = rawInput.replace(" ","/")
                                ipadd = ipaddress.ip_interface(str(rawInput))
                                if InterfacesParse[InterfacesDict["IPV4Addr"][0]] == "":
                                    InterfacesParse[InterfacesDict["IPV4Addr"][0]] = str(ipadd)
                                else:
                                    InterfacesParse[InterfacesDict["IPV4Addr"][0]] = InterfacesParse[InterfacesDict["IPV4Addr"][0]] + "|" + str(ipadd)
                                if InterfacesParse[InterfacesDict["IPV4Subnet"][0]] == "":
                                    InterfacesParse[InterfacesDict["IPV4Subnet"][0]] = str(ipadd.network)
                                else:
                                    InterfacesParse[InterfacesDict["IPV4Subnet"][0]] = InterfacesParse[InterfacesDict["IPV4Subnet"][0]] + "|"+ str(ipadd.network)

                        # Find all IPv6 addresses associated with current interface
                        for obj2 in obj1.re_search_children("ipv6 address "):
                            rawInput = obj2.text.split("ipv6 address ")[1].lstrip().rstrip()
                            ipadd = ipaddress.ip_interface(str(line))
                            if InterfacesParse[InterfacesDict["IPV6Addr"][0]] == "":
                                InterfacesParse[InterfacesDict["IPV6Addr"][0]] = str(ipadd)
                            else:
                                InterfacesParse[InterfacesDict["IPV6Addr"][0]] = InterfacesParse[InterfacesDict["IPV6Addr"][0]] + "|" + str(ipadd)
                            if InterfacesParse[InterfacesDict["IPV6Subnet"][0]] == "":
                                InterfacesParse[InterfacesDict["IPV6Subnet"][0]] = str(ipadd.network)
                            else:
                                InterfacesParse[InterfacesDict["IPV6Subnet"][0]] = InterfacesParse[InterfacesDict["IPV6Subnet"][0]] + "|" + str(ipadd.network)

                        # Check if interface is a bundle
                        if not re.search(r'[Ee]th-[Tt]runk',InterfacesParse[InterfacesDict["IfName"][0]]):
                            if re.search(r'\.',InterfacesParse[InterfacesDict["IfName"][0]]):
                                InterfacesParse[InterfacesDict["PortName"][0]] = InterfacesParse[InterfacesDict["IfName"][0]].split(".")[0]
                            else:
                                InterfacesParse[InterfacesDict["PortName"][0]] = InterfacesParse[InterfacesDict["IfName"][0]]
                        else:
                            if re.search(r'\.',InterfacesParse[InterfacesDict["IfName"][0]]):
                                tempLAGID = str(InterfacesParse[InterfacesDict["IfName"][0]].split("runk")[1].split(".")[0])
                            else:
                                tempLAGID = str(InterfacesParse[InterfacesDict["IfName"][0]].split("runk")[1])

                            # Find ports associated with this LAG
                            for obj20 in cfg.find_objects(r"^interface"):
                                if (( not re.search(r'[Ee]th-[Tt]runk',obj20.text) ) and ( not re.search(r'\.',obj20.text) )):
                                    searchExpression = r"^ *eth-trunk " + tempLAGID + r"[a-zA-Z ]*$"
                                    for obj21 in obj20.re_search_children(searchExpression):
                                        if InterfacesParse[InterfacesDict["PortName"][0]] != "":
                                            InterfacesParse[InterfacesDict["PortName"][0]] = InterfacesParse[InterfacesDict["PortName"][0]] + "|"
                                        InterfacesParse[InterfacesDict["PortName"][0]] = InterfacesParse[InterfacesDict["PortName"][0]] + obj20.text.split("interface ")[1].split()[0]
                                        break

                        # Addind only IP/IPv6 interfaces
                        if run == 0:
                            if (( InterfacesParse[InterfacesDict["IPV4Addr"][0]] != "" ) or (InterfacesParse[InterfacesDict["IPV6Addr"][0]] != "" )):
                                InterfacesParse = [element.rstrip().lstrip() for element in InterfacesParse]
                                # print(InterfacesParse)
                                InterfacesParseAll.append(InterfacesParse)
                        # Addind all other LAGs
                        if run == 1:
                            if (( InterfacesParse[InterfacesDict["IPV4Addr"][0]] == "" ) and (InterfacesParse[InterfacesDict["IPV6Addr"][0]] == "" )):
                                if re.search(r'[Ee]th-[Tt]runk',InterfacesParse[InterfacesDict["IfName"][0]]):

                                    match = 0
                                    for line in InterfacesParseAll:
                                        if InterfacesParse[InterfacesDict["PortName"][0]] == line[InterfacesDict["PortName"][0]]:
                                            match = 1

                                    if match == 0:
                                        InterfacesParse = [element.rstrip().lstrip() for element in InterfacesParse]
                                        # print(InterfacesParse)
                                        InterfacesParseAll.append(InterfacesParse)

                        # Addind all other ports
                        if run == 1:
                            if (( InterfacesParse[InterfacesDict["IPV4Addr"][0]] == "" ) and (InterfacesParse[InterfacesDict["IPV6Addr"][0]] == "" )):
                                if not re.search(r'[Ee]th-[Tt]runk',InterfacesParse[InterfacesDict["IfName"][0]]):

                                    match = 0
                                    for line in InterfacesParseAll:
                                        if InterfacesParse[InterfacesDict["PortName"][0]] in line[InterfacesDict["PortName"][0]]:
                                            match = 1

                                    if match == 0:
                                        InterfacesParse = [element.rstrip().lstrip() for element in InterfacesParse]
                                        # print(InterfacesParse)
                                        InterfacesParseAll.append(InterfacesParse)

        if (CLISyntax == "SR-OS"):
            for obj1 in cfg.find_objects(r"^configure"):
                for obj2 in obj1.re_search_children(r"router Base"):
                    # Looking for IP interfaces
                    for obj3 in obj2.re_search_children(r"interface"):
                        InterfacesParse = [""] * len(InterfacesDict)
                        InterfacesParse[InterfacesDict["IfName"][0]] = obj3.text.split("interface ")[1].replace("\"","")

                        # Find description associated with current interface
                        for obj4 in obj3.re_search_children("description "):
                            InterfacesParse[InterfacesDict["IfDescr"][0]] = str(obj4.text.split("description ")[1].replace("\"",""))
                            break

                        # Find all IPv4 addresses associated with current interface
                        for obj4 in obj3.re_search_children(r"^ *address "):
                            rawInput = obj4.text.split("address ")[1].lstrip().rstrip()
                            rawInput = rawInput.replace(" ","/")
                            ipadd = ipaddress.ip_interface(str(rawInput))
                            if InterfacesParse[InterfacesDict["IPV4Addr"][0]] == "":
                                InterfacesParse[InterfacesDict["IPV4Addr"][0]] = str(ipadd)
                            else:
                                InterfacesParse[InterfacesDict["IPV4Addr"][0]] = InterfacesParse[InterfacesDict["IPV4Addr"][0]] + "|" + str(ipadd)
                            if InterfacesParse[InterfacesDict["IPV4Subnet"][0]] == "":
                                InterfacesParse[InterfacesDict["IPV4Subnet"][0]] = str(ipadd.network)
                            else:
                                InterfacesParse[InterfacesDict["IPV4Subnet"][0]] = InterfacesParse[InterfacesDict["IPV4Subnet"][0]] + "|"+ str(ipadd.network)

                        # Find all IPv6 addresses associated with current interface
                        for obj4 in obj3.re_search_children(r"^ *ipv6 address "):
                            rawInput = obj4.text.split("ipv6 address ")[1].lstrip().rstrip()
                            ipadd = ipaddress.ip_interface(str(line))
                            if InterfacesParse[InterfacesDict["IPV6Addr"][0]] == "":
                                InterfacesParse[InterfacesDict["IPV6Addr"][0]] = str(ipadd)
                            else:
                                InterfacesParse[InterfacesDict["IPV6Addr"][0]] = InterfacesParse[InterfacesDict["IPV6Addr"][0]] + "|" + str(ipadd)
                            if InterfacesParse[InterfacesDict["IPV6Subnet"][0]] == "":
                                InterfacesParse[InterfacesDict["IPV6Subnet"][0]] = str(ipadd.network)
                            else:
                                InterfacesParse[InterfacesDict["IPV6Subnet"][0]] = InterfacesParse[InterfacesDict["IPV6Subnet"][0]] + "|" + str(ipadd.network)

                        # Find port/LAG associated with current interface
                        for obj4 in obj3.re_search_children(r"^ *port"):
                            # print(obj4.text)
                            InterfacesParse[InterfacesDict["PortBinding"][0]] = obj4.text.split("port ")[1]
                            if not obj4.re_search(r"lag-"):
                                if obj4.re_search(r":"):
                                    InterfacesParse[InterfacesDict["PortName"][0]] = InterfacesParse[InterfacesDict["PortBinding"][0]].split(":")[0]
                                else:
                                    InterfacesParse[InterfacesDict["PortName"][0]] = InterfacesParse[InterfacesDict["PortBinding"][0]]

                            else:
                                if obj4.re_search(r":"):
                                    tempLAGID = InterfacesParse[InterfacesDict["PortBinding"][0]].split("lag-")[1].split(":")[0]
                                else:
                                    tempLAGID = InterfacesParse[InterfacesDict["PortBinding"][0]].split("lag-")[1]

                                searchExpression = r"^ +lag " + tempLAGID + r" *$"
                                for obj20 in obj1.re_search_children(searchExpression):
                                    for obj21 in obj20.re_search_children(r"^ *port"):
                                        if InterfacesParse[InterfacesDict["PortName"][0]] != "":
                                            InterfacesParse[InterfacesDict["PortName"][0]] = InterfacesParse[InterfacesDict["PortName"][0]] + "|"

                                        InterfacesParse[InterfacesDict["PortName"][0]] = InterfacesParse[InterfacesDict["PortName"][0]] + obj21.text.split("port ")[1]

                        InterfacesParse = [element.rstrip().lstrip() for element in InterfacesParse]
                        InterfacesParseAll.append(InterfacesParse)

                # Looking for LAGs not assigned to any IP interfaces
                for obj2 in obj1.re_search_children(r" +lag +"):
                    InterfacesParse = [""] * len(InterfacesDict)
                    InterfacesParse[InterfacesDict["IfName"][0]] = obj2.text.lstrip().rstrip()

                    # Find description associated with current LAG
                    for obj3 in obj2.re_search_children("description "):
                        InterfacesParse[InterfacesDict["IfDescr"][0]] = str(obj3.text.split("description ")[1].replace("\"",""))
                        break

                    for obj20 in obj2.re_search_children(r" +port "):
                        tempInterfacesParse = InterfacesParse.copy()
                        tempInterfacesParse[InterfacesDict["PortName"][0]] = str(obj20.text.split("port ")[1].split(" ")[0])

                        match = 0
                        for line in InterfacesParseAll:
                            if tempInterfacesParse[InterfacesDict["PortName"][0]] in line[InterfacesDict["PortName"][0]].split("|"):
                                match = 1

                        if match == 0:
                            tempInterfacesParse = [element.rstrip().lstrip() for element in tempInterfacesParse]
                            InterfacesParseAll.append(tempInterfacesParse)

                # Looking for ports not assigned to any LAG or interface
                for obj2 in obj1.re_search_children(r" +port +"):
                    InterfacesParse = [""] * len(InterfacesDict)

                    InterfacesParse[InterfacesDict["IfName"][0]] = obj2.text.split("port ")[1]
                    InterfacesParse[InterfacesDict["PortName"][0]] = InterfacesParse[InterfacesDict["IfName"][0]]

                    # Find description associated with current port
                    for obj3 in obj2.re_search_children("description "):
                        InterfacesParse[InterfacesDict["IfDescr"][0]] = str(obj3.text.split("description ")[1].replace("\"",""))
                        break

                    match = 0
                    for line in InterfacesParseAll:
                        if InterfacesParse[InterfacesDict["PortName"][0]] in line[InterfacesDict["PortName"][0]].split("|"):
                            match = 1

                    if match == 0:
                        InterfacesParse = [element.rstrip().lstrip() for element in InterfacesParse]
                        InterfacesParseAll.append(InterfacesParse)

                    # # Find LAG associated with this port
                    # for obj10 in obj1.re_search_children(r" +lag +"):
                    #     searchExpression = r" +port " + InterfacesParse[InterfacesDict["IfName"][0]] + r" *$"
                    #     for obj11 in obj10.re_search_children(searchExpression):
                    #         InterfacesParse[InterfacesDict["LAGID"][0]] = obj10.text.split("lag ")[1]
                    #         break

                    # if InterfacesParse[InterfacesDict["LAGID"][0]] == "":


            pass

        # with open("./" + outputPath + "/debugText.txt", 'a') as debugTextFile:
        #     debugTextFile.write("\t".join(str(item) for item in InterfacesDict))
        #     debugTextFile.write("\n")
        #     for interfaceLine in InterfacesParseAll:
        #         debugTextFile.write("\t".join(str(item) for item in interfaceLine))
        #         debugTextFile.write("\n")

        ################################################### Calculate neighbors from P-t-P (/30,/31) IP subnets ###################################################

        PeeringParseAll = []

        for interfaceLine in InterfacesParseAll:

            # print(interfaceLine[InterfacesDict["IPV4Addr"][0]])
            # Calculating peer IPv4 address for IPv4 subnet on interface
            for address in interfaceLine[InterfacesDict["IPV4Addr"][0]].split("|"):
                if address == "": continue
                rawInput = address
                ipadd = ipaddress.ip_interface(str(rawInput))
                # Filtering only /30 and /31 networks
                if ( len(list(ipadd.network.hosts())) == 2 ):
                    tempNetworkList = list(ipadd.network.hosts())
                    tempNetworkMask = ipadd.network.prefixlen
                    tempPeerIPV4AddrList = []
                    for address in tempNetworkList:
                        tempPeerIPV4AddrList.append(str(address) + "/" + str(ipadd.network.prefixlen))
                    # Removing own adress from list
                    if str(ipadd) in tempPeerIPV4AddrList:
                        tempPeerIPV4AddrList.pop(tempPeerIPV4AddrList.index(str(ipadd)))

                    # Creating a peer record for all adresses in IPv4 subnet on interface
                    for tempPeerIPV4Addr in tempPeerIPV4AddrList:
                        PeeringParse = [""] * len(PeeringDict)

                        if len(tempPeerIPV4AddrList) == 1:
                            PeeringParse[PeeringDict["PeeringType"][0]] = "P2P IPv4"
                        else:
                            PeeringParse[PeeringDict["PeeringType"][0]] = "IPv4 subnet"

                        PeeringParse[PeeringDict["Hostname"][0]] = Hostname
                        PeeringParse[PeeringDict["SysAddr"][0]] = SysAddr
                        PeeringParse[PeeringDict["CLISyntax"][0]] = CLISyntax
                        PeeringParse[PeeringDict["IfName"][0]] = interfaceLine[InterfacesDict["IfName"][0]]
                        PeeringParse[PeeringDict["IfDescr"][0]] = interfaceLine[InterfacesDict["IfDescr"][0]]
                        PeeringParse[PeeringDict["PortBinding"][0]] = interfaceLine[InterfacesDict["PortBinding"][0]]
                        PeeringParse[PeeringDict["IPV4Addr"][0]] = interfaceLine[InterfacesDict["IPV4Addr"][0]]
                        PeeringParse[PeeringDict["IPV4Subnet"][0]] = interfaceLine[InterfacesDict["IPV4Subnet"][0]]
                        PeeringParse[PeeringDict["IPV6Addr"][0]] = interfaceLine[InterfacesDict["IPV6Addr"][0]]
                        PeeringParse[PeeringDict["IPV6Subnet"][0]] = interfaceLine[InterfacesDict["IPV6Subnet"][0]]
                        PeeringParse[PeeringDict["IPV4AddrRemote"][0]] = str(tempPeerIPV4Addr)
                        PeeringParse[PeeringDict["IPV4SubnetRemote"][0]] = interfaceLine[InterfacesDict["IPV4Subnet"][0]]

                        for tempPortName in interfaceLine[InterfacesDict["PortName"][0]].split("|"):
                            tempPeeringParse = PeeringParse.copy()
                            tempPeeringParse[PeeringDict["PortName"][0]] = tempPortName

                            PeeringParseAll.append(tempPeeringParse)

        ################################################### Parse BGP peering from config ###################################################

        # PeeringParseAll.clear()
        BGPPeeringParseAll = []

        # Syntax: Cisco IOS-XR
        if (CLISyntax == "IOS-XR"):
            for obj1 in cfg.find_objects(r"^router bgp"):
                tempAS = obj1.text.split("router bgp")[1].split()[0]
                # Looking for neighbor-groups first
                tempNBGroupList = []
                for obj2 in obj1.re_search_children("neighbor-group "):
                    tempNBGroupLine = [""] * 4   # for storing Group name, remote AS and source interface
                    tempNBGroupLine[0] = obj2.text.split("neighbor-group ")[1].split()[0]
                    for obj3 in obj2.re_search_children("description "):
                        tempNBGroupLine[1] = obj3.text.split("description ")[1].replace("\"","")
                        break
                    for obj3 in obj2.re_search_children("remote-as "):
                        tempNBGroupLine[2] = obj3.text.split("remote-as ")[1].split()[0]
                        break
                    for obj3 in obj2.re_search_children("update-source "):
                        tempNBGroupLine[3] = obj3.text.split("update-source ")[1].split()[0]
                        break
                    if tempNBGroupLine not in tempNBGroupList:
                        tempNBGroupList.append(tempNBGroupLine)
                for obj2 in obj1.re_search_children("neighbor "):
                    BGPPeeringParse = [""] * len(PeeringDict)

                    # Set local System Address & hostname
                    BGPPeeringParse[PeeringDict["SysAddr"][0]] = SysAddr
                    BGPPeeringParse[PeeringDict["Hostname"][0]] = Hostname
                    BGPPeeringParse[PeeringDict["CLISyntax"][0]] = CLISyntax

                    # Set peer address as SysAddrRemote
                    BGPPeeringParse[PeeringDict["IPV4AddrRemote"][0]] = obj2.text.split("neighbor ")[1].split()[0]
                    # Set local AS
                    BGPPeeringParse[PeeringDict["LocalAS"][0]] = tempAS

                    # Get peer group
                    tempGroupName = ""
                    for obj3 in obj2.re_search_children("use neighbor-group "):
                        tempGroupName = obj3.text.split("use neighbor-group ")[1].split()[0]
                        break

                    # Define peer description
                    for obj3 in obj2.re_search_children("description "):
                        BGPPeeringParse[PeeringDict["PeerDescr"][0]] = obj3.text.split("description ")[1].replace("\"","")
                        break
                    if (( BGPPeeringParse[PeeringDict["PeerDescr"][0]] == "" ) and ( tempGroupName != "" )):
                        for line in tempNBGroupList:
                            if line[0] == tempGroupName:
                                if line[1] != "":
                                    BGPPeeringParse[PeeringDict["PeerDescr"][0]] = line[1]
                                else:
                                    BGPPeeringParse[PeeringDict["PeerDescr"][0]] = "Group: " + tempGroupName

                    # Define peer remote AS
                    for obj3 in obj2.re_search_children("remote-as "):
                        BGPPeeringParse[PeeringDict["ASRemote"][0]] = obj3.text.split("remote-as ")[1].split()[0]
                        break
                    if (( BGPPeeringParse[PeeringDict["ASRemote"][0]] == "" ) and ( tempGroupName != "" )):
                        for line in tempNBGroupList:
                            if line[0] == tempGroupName:
                                BGPPeeringParse[PeeringDict["ASRemote"][0]] = line[2]

                    if BGPPeeringParse[PeeringDict["LocalAS"][0]] == BGPPeeringParse[PeeringDict["ASRemote"][0]]:
                        BGPPeeringParse[PeeringDict["PeeringType"][0]] = "iBGP"
                    else:
                        BGPPeeringParse[PeeringDict["PeeringType"][0]] = "eBGP"

                    # Define peer source interface
                    for obj3 in obj2.re_search_children("update-source "):
                        BGPPeeringParse[PeeringDict["IfName"][0]] = obj3.text.split("update-source ")[1].split()[0]
                        break
                    if (( BGPPeeringParse[PeeringDict["IfName"][0]] == "" ) and ( tempGroupName != "" )):
                        for line in tempNBGroupList:
                            if line[0] == tempGroupName:
                                BGPPeeringParse[PeeringDict["IfName"][0]] = line[3]

                    BGPPeeringParseAll.append(BGPPeeringParse)

        # Syntax: Cisco IOS
        if (CLISyntax == "IOS"):
            for obj1 in cfg.find_objects(r"^router bgp"):
                tempAS = obj1.text.split("router bgp")[1].split()[0]
                # Looking for neighbor-groups first
                tempNBGroupList = []
                for obj2 in obj1.re_search_children(r"neighbor .* peer-group *$"):

                    # Check if group was already added to the list
                    match = 0
                    for line in tempNBGroupList:
                        if obj2.text.split("neighbor ")[1].split(" peer-group")[0] == line[0]:
                            match = 1
                            break
                    if match == 1:
                        continue

                    tempNBGroupLine = [""] * 4   # for storing Group name, remote AS and source interface
                    tempNBGroupLine[0] = obj2.text.split("neighbor ")[1].split(" peer-group")[0]

                    searchExpression = r"neighbor " + tempNBGroupLine[0]
                    for obj3 in obj1.re_search_children(searchExpression):
                        if re.search(r"description",obj3.text):
                            tempNBGroupLine[1] = obj3.text.split("description ")[1].replace("\"","")
                            continue
                        if re.search(r"remote-as",obj3.text):
                            tempNBGroupLine[2] = obj3.text.split("remote-as ")[1].split()[0]
                            continue
                        if re.search(r"update-source",obj3.text):
                            tempNBGroupLine[3] = obj3.text.split("update-source ")[1].split()[0]
                            continue

                    if tempNBGroupLine not in tempNBGroupList:
                        tempNBGroupList.append(tempNBGroupLine)


                for obj2 in obj1.re_search_children(r"neighbor \d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}"):

                    # Check if group was already added to the list
                    match = 0
                    for line in BGPPeeringParseAll:
                        if obj2.text.split("neighbor ")[1].split()[0] == line[PeeringDict["IPV4AddrRemote"][0]]:
                            match = 1
                            break
                    if match == 1:
                        continue

                    BGPPeeringParse = [""] * len(PeeringDict)

                    # Set local System Address & hostname
                    BGPPeeringParse[PeeringDict["SysAddr"][0]] = SysAddr
                    BGPPeeringParse[PeeringDict["Hostname"][0]] = Hostname
                    BGPPeeringParse[PeeringDict["CLISyntax"][0]] = CLISyntax

                    # Set peer address as SysAddrRemote
                    BGPPeeringParse[PeeringDict["IPV4AddrRemote"][0]] = obj2.text.split("neighbor ")[1].split()[0]
                    # Set local AS
                    BGPPeeringParse[PeeringDict["LocalAS"][0]] = tempAS

                    # Get peer group
                    tempGroupName = ""
                    searchExpression = r"neighbor " + BGPPeeringParse[PeeringDict["IPV4AddrRemote"][0]] + r" peer-group"
                    for obj3 in obj1.re_search_children(searchExpression):
                        tempGroupName = obj3.text.split("peer-group ")[1].split()[0]
                        break

                    # Get peer parameters
                    searchExpression = r"neighbor " + BGPPeeringParse[PeeringDict["IPV4AddrRemote"][0]]
                    for obj3 in obj1.re_search_children(searchExpression):
                        if re.search(r"description",obj3.text):
                            BGPPeeringParse[PeeringDict["PeerDescr"][0]] = obj3.text.split("description ")[1].replace("\"","")
                            continue
                        if re.search(r"remote-as",obj3.text):
                            BGPPeeringParse[PeeringDict["ASRemote"][0]] = obj3.text.split("remote-as ")[1].split()[0]
                            continue
                        if re.search(r"update-source",obj3.text):
                            BGPPeeringParse[PeeringDict["IfName"][0]] = obj3.text.split("update-source ")[1].split()[0]
                            continue

                    # Get parameters from group if they are missing
                    if (( BGPPeeringParse[PeeringDict["PeerDescr"][0]] == "" ) and ( tempGroupName != "" )):
                        for line in tempNBGroupList:
                            if line[0] == tempGroupName:
                                if line[1] != "":
                                    BGPPeeringParse[PeeringDict["PeerDescr"][0]] = line[1]
                                else:
                                    BGPPeeringParse[PeeringDict["PeerDescr"][0]] = "Group: " + tempGroupName

                    if (( BGPPeeringParse[PeeringDict["ASRemote"][0]] == "" ) and ( tempGroupName != "" )):
                        for line in tempNBGroupList:
                            if line[0] == tempGroupName:
                                BGPPeeringParse[PeeringDict["ASRemote"][0]] = line[2]

                    if BGPPeeringParse[PeeringDict["LocalAS"][0]] == BGPPeeringParse[PeeringDict["ASRemote"][0]]:
                        BGPPeeringParse[PeeringDict["PeeringType"][0]] = "iBGP"
                    else:
                        BGPPeeringParse[PeeringDict["PeeringType"][0]] = "eBGP"

                    if (( BGPPeeringParse[PeeringDict["IfName"][0]] == "" ) and ( tempGroupName != "" )):
                        for line in tempNBGroupList:
                            if line[0] == tempGroupName:
                                BGPPeeringParse[PeeringDict["IfName"][0]] = line[3]

                    BGPPeeringParseAll.append(BGPPeeringParse)

        # Syntax: Huawei VRP
        if (CLISyntax == "VRP"):
            # TBD
            pass

        # Syntax: Nokia/ALU SR-OS
        if (CLISyntax == "SR-OS"):
            for obj1 in cfg.find_objects(r"^configure"):
                tempAS = ""
                for obj2 in obj1.re_search_children(r"router Base"):
                    # Get local AS number
                    for obj3 in obj2.re_search_children(r"autonomous-system"):
                        tempAS = obj3.text.split("autonomous-system ")[1].split()[0]
                        break

                    for obj3 in obj2.re_search_children(r"^ *bgp"):
                        # Looking for neighbor-groups first
                        for obj4 in obj3.re_search_children(r"^ *group"):

                            tempNBGroupLine = [""] * 5   # for storing Group name, remote AS and source interface
                            tempNBGroupLine[0] = obj4.text.split("group")[1].replace("\"","")

                            for obj5 in obj4.re_search_children(r"description"):
                                tempNBGroupLine[1] = obj5.text.split("description ")[1].replace("\"","")
                                break
                            for obj5 in obj4.re_search_children(r"peer-as"):
                                tempNBGroupLine[2] = obj5.text.split("peer-as ")[1].split()[0]
                                break
                            for obj5 in obj4.re_search_children(r"local-address"):
                                tempNBGroupLine[3] = obj5.text.split("local-address ")[1].split()[0]
                                break
                            for obj5 in obj4.re_search_children(r"type"):
                                if obj5.text.split("type ")[1].split()[0].lstrip().rstrip() == "external":
                                    tempNBGroupLine[4] = "eBGP"
                                else:
                                    if obj5.text.split("type ")[1].split()[0].lstrip().rstrip() == "internal":
                                        tempNBGroupLine[4] = "iBGP"
                                break

                            # Looking for neighbors in current group
                            for obj5 in obj4.re_search_children(r"neighbor \d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}"):

                                BGPPeeringParse = [""] * len(PeeringDict)

                                # Set local System Address & hostname
                                BGPPeeringParse[PeeringDict["SysAddr"][0]] = SysAddr
                                BGPPeeringParse[PeeringDict["Hostname"][0]] = Hostname
                                BGPPeeringParse[PeeringDict["CLISyntax"][0]] = CLISyntax

                                # Set peer address as SysAddrRemote
                                BGPPeeringParse[PeeringDict["IPV4AddrRemote"][0]] = obj5.text.split("neighbor ")[1].split()[0]
                                # Set local AS
                                BGPPeeringParse[PeeringDict["LocalAS"][0]] = tempAS

                                for obj6 in obj5.re_search_children(r"description"):
                                    tempNBGroupLine[1] = obj6.text.split("description ")[1].replace("\"","")
                                    break
                                for obj6 in obj5.re_search_children(r"peer-as"):
                                    tempNBGroupLine[2] = obj6.text.split("peer-as ")[1].split()[0]
                                    break
                                for obj6 in obj5.re_search_children(r"local-address "):
                                    tempNBGroupLine[3] = obj6.text.split("local-address ")[1].split()[0]
                                    break
                                for obj6 in obj5.re_search_children(r"type"):
                                    if obj6.text.split("type ")[1].split()[0].lstrip().rstrip() == "external":
                                        tempNBGroupLine[4] = "eBGP"
                                    else:
                                        if obj6.text.split("type ")[1].split()[0].lstrip().rstrip() == "internal":
                                            tempNBGroupLine[4] = "iBGP"
                                    break

                                # Get parameters from group if they are missing
                                if BGPPeeringParse[PeeringDict["PeerDescr"][0]] == "":
                                    if tempNBGroupLine[1] != "":
                                        BGPPeeringParse[PeeringDict["PeerDescr"][0]] = tempNBGroupLine[1]
                                    else:
                                        BGPPeeringParse[PeeringDict["PeerDescr"][0]] = "Group: " + tempNBGroupLine[0]

                                if BGPPeeringParse[PeeringDict["ASRemote"][0]] == "":
                                    BGPPeeringParse[PeeringDict["ASRemote"][0]] = tempNBGroupLine[2]

                                if BGPPeeringParse[PeeringDict["IfName"][0]] == "":
                                    BGPPeeringParse[PeeringDict["IfName"][0]] = tempNBGroupLine[3]

                                if BGPPeeringParse[PeeringDict["PeeringType"][0]] == "":
                                    BGPPeeringParse[PeeringDict["PeeringType"][0]] = tempNBGroupLine[4]

                                if BGPPeeringParse[PeeringDict["PeeringType"][0]] == "":
                                    if BGPPeeringParse[PeeringDict["LocalAS"][0]] == BGPPeeringParse[PeeringDict["ASRemote"][0]]:
                                        BGPPeeringParse[PeeringDict["PeeringType"][0]] = "iBGP"
                                    else:
                                        BGPPeeringParse[PeeringDict["PeeringType"][0]] = "eBGP"

                                if (( BGPPeeringParse[PeeringDict["IfName"][0]] == "" ) and ( BGPPeeringParse[PeeringDict["PeeringType"][0]] == "iBGP" )):
                                    BGPPeeringParse[PeeringDict["IfName"][0]] = "system"

                                if (( BGPPeeringParse[PeeringDict["ASRemote"][0]] == "" ) and ( BGPPeeringParse[PeeringDict["PeeringType"][0]] == "iBGP" )):
                                    BGPPeeringParse[PeeringDict["ASRemote"][0]] = tempAS

                                BGPPeeringParseAll.append(BGPPeeringParse)

                        # Looking for neighbors outside of groups
                        for obj5 in obj3.re_search_children(r"neighbor \d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}"):

                            BGPPeeringParse = [""] * len(PeeringDict)

                            # Set local System Address & hostname
                            BGPPeeringParse[PeeringDict["SysAddr"][0]] = SysAddr
                            BGPPeeringParse[PeeringDict["Hostname"][0]] = Hostname
                            BGPPeeringParse[PeeringDict["CLISyntax"][0]] = CLISyntax

                            # Set peer address as SysAddrRemote
                            BGPPeeringParse[PeeringDict["IPV4AddrRemote"][0]] = obj5.text.split("neighbor ")[1].split()[0]
                            # Set local AS
                            BGPPeeringParse[PeeringDict["LocalAS"][0]] = tempAS

                            for obj6 in obj5.re_search_children(r"description"):
                                tempNBGroupLine[1] = obj6.text.split("description ")[1].replace("\"","")
                                break
                            for obj6 in obj5.re_search_children(r"peer-as"):
                                tempNBGroupLine[2] = obj6.text.split("peer-as ")[1].split()[0]
                                break
                            for obj6 in obj5.re_search_children(r"local-address "):
                                tempNBGroupLine[3] = obj6.text.split("local-address ")[1].split()[0]
                                break
                            for obj6 in obj5.re_search_children(r"type"):
                                if obj6.text.split("type ")[1].split()[0].lstrip().rstrip() == "external":
                                    tempNBGroupLine[4] = "eBGP"
                                else:
                                    if obj6.text.split("type ")[1].split()[0].lstrip().rstrip() == "internal":
                                        tempNBGroupLine[4] = "iBGP"
                                break

                            # Get parameters from group if they are missing
                            if BGPPeeringParse[PeeringDict["PeerDescr"][0]] == "":
                                if tempNBGroupLine[1] != "":
                                    BGPPeeringParse[PeeringDict["PeerDescr"][0]] = tempNBGroupLine[1]
                                else:
                                    BGPPeeringParse[PeeringDict["PeerDescr"][0]] = "Group: " + tempNBGroupLine[0]

                            if BGPPeeringParse[PeeringDict["ASRemote"][0]] == "":
                                BGPPeeringParse[PeeringDict["ASRemote"][0]] = tempNBGroupLine[2]

                            if BGPPeeringParse[PeeringDict["IfName"][0]] == "":
                                BGPPeeringParse[PeeringDict["IfName"][0]] = tempNBGroupLine[3]

                            if BGPPeeringParse[PeeringDict["PeeringType"][0]] == "":
                                BGPPeeringParse[PeeringDict["PeeringType"][0]] = tempNBGroupLine[4]

                            if BGPPeeringParse[PeeringDict["PeeringType"][0]] == "":
                                if BGPPeeringParse[PeeringDict["LocalAS"][0]] == BGPPeeringParse[PeeringDict["ASRemote"][0]]:
                                    BGPPeeringParse[PeeringDict["PeeringType"][0]] = "iBGP"
                                else:
                                    BGPPeeringParse[PeeringDict["PeeringType"][0]] = "eBGP"

                            if (( BGPPeeringParse[PeeringDict["IfName"][0]] == "" ) and ( BGPPeeringParse[PeeringDict["PeeringType"][0]] == "iBGP" )):
                                BGPPeeringParse[PeeringDict["IfName"][0]] = "system"

                            if (( BGPPeeringParse[PeeringDict["ASRemote"][0]] == "" ) and ( BGPPeeringParse[PeeringDict["PeeringType"][0]] == "iBGP" )):
                                BGPPeeringParse[PeeringDict["ASRemote"][0]] = tempAS

                            BGPPeeringParseAll.append(BGPPeeringParse)


        # with open("./" + outputPath + "/debugText.txt", 'a') as debugTextFile:
        #     debugTextFile.write("\t".join(str(item) for item in PeeringDict))
        #     debugTextFile.write("\n")
        # for peeringLine in BGPPeeringParseAll:
        #     with open("./" + outputPath + "/debugText.txt", 'a') as debugTextFile:
        #         debugTextFile.write("\t".join(str(item) for item in peeringLine))
        #         debugTextFile.write("\n")

        ################################################### Define variables for show commands to execute ###################################################
        # Syntax: Cisco IOS-XR
        if CLISyntax == "IOS-XR":
            VRFNameList = []
            for obj1 in cfg.find_objects(r"^ *vrf "):       # Find node's VRF names from config
                # if debug: print("debug: obj1: "+str(obj1))
                if obj1.text.split("vrf ")[1].split()[0] not in VRFNameList:
                    VRFNameList.append(obj1.text.split("vrf ")[1].split()[0])
            # if debug:
                # if len(VRFNameList) > 0:
                #     print("debug: following VRF names found in configuration file: " + str(" ".join(str(item) for item in VRFNameList)))
            pass
        # Syntax: Cisco IOS/IOS-XE
        if CLISyntax == "IOS":
            VRFNameList = []
            for obj1 in cfg.find_objects(r"^ *vrf definition "):        # Find node's VRF names from config
                # if debug: print("debug: obj1: "+str(obj1))
                if obj1.text.split("vrf definition ")[1].split()[0] not in VRFNameList:
                    VRFNameList.append(obj1.text.split("vrf definition ")[1].split()[0])
            # if debug:
                # if len(VRFNameList) > 0:
                #     print("debug: following VRF names found in configuration file: " + str(" ".join(str(item) for item in VRFNameList)))
            pass
        # Syntax: Huawei VRP
        # vpn-name
        if CLISyntax == "VRP":
            VPNNameList = []
            for obj1 in cfg.find_objects(r"^ *ip vpn-instance "):        # Find node's VRF names from config
                # if debug: print("debug: obj1: "+str(obj1))
                if obj1.text.split("ip vpn-instance ")[1].split()[0] not in VPNNameList:
                    VPNNameList.append(obj1.text.split("ip vpn-instance ")[1].split()[0])
            # if debug:
            #     if len(VPNNameList) > 0:
            #         print("debug: following VRF names found in configuration file: " + str(" ".join(str(item) for item in VPNNameList)))
            pass
        # Syntax: ALU/Nokia SR-OS
        if CLISyntax == "SR-OS":
            cardList = []
            portList = []
            routerList = []
            serviceList = []
            for obj1 in cfg.find_objects(r"^configure"):
                # Find card numbers
                for obj2 in obj1.re_search_children(r" +card +"):
                    # if debug: print("debug: obj2: "+str(obj2))
                    if obj2.text.split("card ")[1].split()[0] not in cardList:
                        cardList.append(obj2.text.split("card ")[1].split()[0])
                # Find port numbers
                for obj2 in obj1.re_search_children(r" +port +"):
                    # if debug: print("debug: obj2: "+str(obj2))
                    if obj2.text.split("port ")[1].split()[0] not in portList:
                        portList.append(obj2.text.split("port ")[1].split()[0])
                for obj2 in obj1.re_search_children(r" +router +"):
                    if obj2.text.split("router ")[1].split()[0].replace("\"","") not in routerList:
                        # if debug: print("debug: obj2: "+str(obj2))
                        routerList.append(obj2.text.split("router ")[1].split()[0].replace("\"",""))
                for obj2 in obj1.re_search_children(r"service"):
                    # Find service IDs
                    match = 0
                    for obj3 in obj2.re_search_children(r"vprn"):
                        for line in serviceList:
                            if obj3.text.split("vprn ")[1].split(" name")[0] == line[0]: match = 1
                        if match == 0:
                            # if debug: print("debug: obj3: "+str(obj3))
                            serviceList.append([obj3.text.split("vprn ")[1].split(" name")[0], "VPRN" ])
                    match = 0
                    for obj3 in obj2.re_search_children(r"ies"):
                        for line in serviceList:
                            if obj3.text.split("ies ")[1].split(" name")[0] == line[0]: match = 1
                        if match == 0:
                            # if debug: print("debug: obj3: "+str(obj3))
                            serviceList.append([obj3.text.split("ies ")[1].split(" name")[0], "IES" ])
                    match = 0
                    for obj3 in obj2.re_search_children(r"vpls"):
                        for line in serviceList:
                            if obj3.text.split("vpls ")[1].split(" name")[0] == line[0]: match = 1
                        if match == 0:
                            # if debug: print("debug: obj3: "+str(obj3))
                            serviceList.append([obj3.text.split("vpls ")[1].split(" name")[0], "VPLS" ])
                    match = 0
                    for obj3 in obj2.re_search_children(r"pipe"):
                        for line in serviceList:
                            if obj3.text.split("pipe ")[1].split(" name")[0] == line[0]: match = 1
                        if match == 0:
                            # if debug: print("debug: obj3: "+str(obj3))
                            serviceList.append([obj3.text.split("pipe ")[1].split(" name")[0], "xPipe" ])
                    # Find SDP IDs
                    for obj3 in obj2.re_search_children(r"pipe"):
                        for line in serviceList:
                            if obj3.text.split("pipe ")[1].split(" name")[0] == line[0]: match = 1
                        if match == 0:
                            # if debug: print("debug: obj3: "+str(obj3))
                            serviceList.append([obj3.text.split("pipe ")[1].split(" name")[0], "xPipe" ])

            # if debug:
            #     if len(cardList) > 0:
            #         print("debug: following cards found in configuration file: " + str(" ".join(str(item) for item in cardList)))
            #     if len(portList) > 0:
            #         print("debug: following ports found in configuration file: " + str(" ".join(str(item) for item in portList)))
            #     if len(serviceList) > 0:
            #         print("debug: following services found in configuration file: " + str(" ".join(str(item) for item in serviceList)))
            pass

        ################################################### Create show commands to execute ###################################################

        tempCommandList = []
        iteration = 0
        tempCommandList.append([])
        for commandNumber in range(3,len(CommandsDict[CLISyntax])):
            tempCommandList[iteration].append(CommandsDict[CLISyntax][commandNumber])
        stop = 0
        while stop == 0:
            # print(iteration)
            iteration = iteration + 1
            tempCommandList.append([])
            stop = 1
            for command in tempCommandList[iteration-1]:
                # time.sleep(0.1)
                # print("Command: " + str(command[0]))
                if re.search(r"\{.*\}",command[0]):
                    stop = 0
                    if re.search(r"\{router-name\}",command[0]):
                        for routerName in routerList:
                            tempCommandList[iteration].append([ command[0].replace("{router-name}",routerName), command[1] ])
                        continue
                    if re.search(r"\{vrf-name\}",command[0]):
                        for VRFName in VRFNameList:
                            tempCommandList[iteration].append([ command[0].replace("{vrf-name}",VRFName), command[1] ])
                        continue
                    if re.search(r"\{vpn-name\}",command[0]):
                        for VPNName in VPNNameList:
                            tempCommandList[iteration].append([ command[0].replace("{vpn-name}",VPNName), command[1] ])
                        continue
                    if re.search(r"\{service-id\}",command[0]):
                        for service in serviceList:
                            tempCommandList[iteration].append([ command[0].replace("{service-id}",service[0]), command[1] ])
                        continue
                    if re.search(r"\{vprn-id\}",command[0]):
                        for service in serviceList:
                            if service[1] == "VPRN":
                                tempCommandList[iteration].append([ command[0].replace("{vprn-id}",service[0]), command[1] ])
                        continue
                    if re.search(r"\{ies-id\}",command[0]):
                        for service in serviceList:
                            if service[1] == "IES":
                                tempCommandList[iteration].append([ command[0].replace("{ies-id}",service[0]), command[1] ])
                        continue
                    if re.search(r"\{vpls-id\}",command[0]):
                        for service in serviceList:
                            if service[1] == "VPLS":
                                tempCommandList[iteration].append([ command[0].replace("{vpls-id}",service[0]), command[1] ])
                        continue
                    if re.search(r"\{xpipe-id\}",command[0]):
                        for service in serviceList:
                            if service[1] == "xPipe":
                                tempCommandList[iteration].append([ command[0].replace("{xpipe-id}",service[0]), command[1] ])
                        continue
                    if re.search(r"\{card-id\}",command[0]):
                        for card in cardList:
                            tempCommandList[iteration].append([ command[0].replace("{card-id}",card), command[1] ])
                        continue
                    if re.search(r"\{port-id\}",command[0]):
                        for port in portList:
                            tempCommandList[iteration].append([ command[0].replace("{port-id}",port), command[1] ])
                        continue
                    if re.search(r"\{.*\}",command[0]):
                        value = re.search(r"\{.*\}",command[0])
                        print("Unknown variable: " + value.group())
                        continue
                else:
                    tempCommandList[iteration].append([ command[0], command[1] ])

        commadList = []
        for command in tempCommandList[iteration]:
            if not re.search(r"\{.*\}",command[0]):
                commadList.append(command)

        ################################################### Execute show commands ###################################################

        execOutput = []

        for command in commadList:
            for attempt in range(0,3):
                try: 
                    commandExecLines = []
                    commandExecLines.append("#####\tExecuting \"" + str(command[0]) + "\" over " + protocol + " with " + str(command[1]) + " second(s) timeout\t#####\n")
                    print("Executing command \"" + str(command[0]) + "\".")
                    output = execCLICommand(connectionCursor, protocol, command[0], command[1])
                    # print("Collected "+ str(len(output[1])) + " lines of output")
                    commandExecLines.extend(output[1])
                    commandExecLines.append("\n#####\tExecuted with code " + str(output[0]) + " in " + str(round(output[2],2)) + " second(s)\t#####\n\n")
                    if output[0] == 0: break
                except (KeyboardInterrupt):
                    print("Command execution aborted by user")
                    break

            execOutput.extend(commandExecLines)

            with open(outputFilePath, 'a') as outputFile:
                outputFile.write("\n".join(str(item) for item in commandExecLines))

            # if debug:
            #     with open("./" + outputPath + "/debugText.txt", 'a') as debugTextFile:
            #         debugTextFile.write("\n".join(str(item) for item in commandExecLines))

        print("Show commands executed, adding data to the output file.")
        execTime = time.time() - startTime
        with open(outputFilePath, 'a') as outputFile:
            outputFile.write("#####\tData collection finished in " + str(round(execTime,2)) + " second(s)\t#####\n\n")

        startTime = time.time()

        ################################################### Define what values to print from all peering information ###################################################

        printPeeringValueList = []
        for value in PeeringDict:
            # Exclude cells that are not required to print
            if ((value != "PeeringID") and (value != "PeeringAdmState") and (value != "PeeringState") and (value != "NodeID") and (value != "IfID")
                    and (value != "IPV6Addr") and (value != "IPV6Subnet") and (value != "NodeIDRemote") and (value != "IfIDRemote") and (value != "IPV6AddrRemote") and(value != "IPV6SubnetRemote")
                    and (value != "LastUpdatedTime") and (value != "LastUpdatedBy")):
                printPeeringValueList.append(value)
 
       ################################################### Print peering information for P2P subnets ###################################################

        # Write P2P subnet data to a file (for diagnostic purposes)
        with open(outputFilePath, 'a') as outputFile:
            outputFile.write("#####\tNeihgboring data section\t#####\n\n")
            if len(PeeringParseAll) > 0:
                outputFile.write("Found following neighbors from attached P2P IP subnets (/30,/31) config:\n")
                # Print header
                valueNumber = 0
                for value in printPeeringValueList:
                    if valueNumber == 0:
                        outputFile.write(str(value))
                    else:
                        outputFile.write("\t" + str(value))
                    valueNumber = valueNumber + 1
                outputFile.write("\n")
                # Print data
                for peeringLine in PeeringParseAll:
                    valueNumber = 0
                    for value in printPeeringValueList:
                        if valueNumber == 0:
                            outputFile.write(str(peeringLine[PeeringDict[value][0]]))
                        else:
                            outputFile.write("\t" + str(peeringLine[PeeringDict[value][0]]))
                        valueNumber = valueNumber + 1
                    outputFile.write("\n")
                outputFile.write("\n")

        # # Write BGP data to a file (for diagnostic purposes)
        # with open(outputFilePath, 'a') as outputFile:
        #     if len(BGPPeeringParseAll) > 0:
        #         outputFile.write("Found following neighbors from BGP config:\n\n")
        #         outputFile.write("\t".join(str(item) for item in PeeringDict))
        #         outputFile.write("\n")
        #         for peeringLine in BGPPeeringParseAll:
        #             outputFile.write("\t".join(str(item) for item in peeringLine))
        #             outputFile.write("\n")
        #     outputFile.write("\n")

       ################################################### organize output of show commands into a separate lists ###################################################

        redirectOutputTo = "default"
        CDPNeighborsLines = []
        LLDPNeighborsLines = []
        OSPFv2NeighborsLines = []
        ISISNeighborsLines = []
        LDPNeighborsLines = []
        BGPNeighborsLines = []

        lineNumber = 0
        for line in execOutput:
            lineNumber = lineNumber + 1
            # Match CDP neighbors output
            # Syntax: Cisco IOS/IOS-XE/IOS-XR
            searchExpression = re.escape(shellPrompt)+r"[ ]*sh(o(w)?)? +c(d(p)?)? +ne(i(g(h(b(o(r(s)?)?)?)?)?)?)? +de(t(a(i(l)?)?)?)?"
            if re.search(re.compile(searchExpression),line):
                # if redirectOutputTo != "CDPNeighborsLines":
                #     if debug: print("debug: "+ redirectOutputTo +" output ends at line "+str(lineNumber)+": "+line)
                # if debug: print("debug: Found CDP neighbors beginning at line "+str(lineNumber)+": "+line)
                redirectOutputTo = "CDPNeighborsLines"
                CDPNeighborsLines.append(line)
                continue
            # Match LLDP neighbors output
            # Syntax: Cisco IOS/IOS-XE/IOS-XR
            searchExpression = re.escape(shellPrompt)+r"[ ]*sh(o(w)?)? +ll(d(p)?)? +ne(i(g(h(b(o(r(s)?)?)?)?)?)?)? +de(t(a(i(l)?)?)?)?"
            if re.search(re.compile(searchExpression),line):
                # if redirectOutputTo != "LLDPNeighborsLines":
                #     if debug: print("debug: "+ redirectOutputTo +" output ends at line "+str(lineNumber)+": "+line)
                # if debug: print("debug: Found LLDP neighbors beginning at line "+str(lineNumber)+": "+line)
                redirectOutputTo = "LLDPNeighborsLines"
                LLDPNeighborsLines.append(line)
                continue
            # Syntax: Huawei VRP
            searchExpression = re.escape(shellPrompt)+r"[ ]*dis(p(l(a(y)?)?)?)? +ll(d(p)?)? +ne(i(g(h(b(o(r(s)?)?)?)?)?)?)?"
            if re.search(re.compile(searchExpression),line):
                # if redirectOutputTo != "LLDPNeighborsLines":
                #     if debug: print("debug: "+ redirectOutputTo +" output ends at line "+str(lineNumber)+": "+line)
                # if debug: print("debug: Found LLDP neighbors beginning at line "+str(lineNumber)+": "+line)
                redirectOutputTo = "LLDPNeighborsLines"
                LLDPNeighborsLines.append(line)
                continue
            # Syntax: ALU/Nokia SR-OS
            searchExpression = re.escape(shellPrompt)+r"[ ]*sh(o(w)?)? +p(o(r(t)?)?)? .* et(h(e(r(n(e(t)?)?)?)?)?)? +ll(d(p)?)? +re(m(o(t(e(-(i(n(f(o)?)?)?)?)?)?)?)?)? +de(t(a(i(l)?)?)?)?"
            if re.search(re.compile(searchExpression),line):
                # if redirectOutputTo != "LLDPNeighborsLines":
                #     if debug: print("debug: "+ redirectOutputTo +" output ends at line "+str(lineNumber)+": "+line)
                # if debug: print("debug: Found LLDP neighbors beginning at line "+str(lineNumber)+": "+line)
                redirectOutputTo = "LLDPNeighborsLines"
                LLDPNeighborsLines.append(line)
                continue
            # Match OSPFv2 neighbors output
            # Syntax: Cisco IOS/IOS-XE/IOS-XR
            searchExpression = re.escape(shellPrompt)+r"[ ]*sh(o(w)?)? +(ip +)?os(p(f)?)? +ne(i(g(h(b(o(r(s)?)?)?)?)?)?)? +de(t(a(i(l)?)?)?)?"
            if re.search(re.compile(searchExpression),line):
                # if redirectOutputTo != "OSPFv2NeighborsLines":
                #     if debug: print("debug: "+ redirectOutputTo +" output ends at line "+str(lineNumber)+": "+line)
                # if debug: print("debug: Found OSPFv2 neighbors beginning at line "+str(lineNumber)+": "+line)
                redirectOutputTo = "OSPFv2NeighborsLines"
                OSPFv2NeighborsLines.append(line)
                continue
            # Syntax: Huawei VRP
            searchExpression = re.escape(shellPrompt)+r"[ ]*dis(p(l(a(y)?)?)?)? +os(p(f)?)? +pe(e(r)?)?"
            if re.search(re.compile(searchExpression),line):
                # if redirectOutputTo != "OSPFv2NeighborsLines":
                #     if debug: print("debug: "+ redirectOutputTo +" output ends at line "+str(lineNumber)+": "+line)
                # if debug: print("debug: Found OSPFv2 neighbors beginning at line "+str(lineNumber)+": "+line)
                redirectOutputTo = "OSPFv2NeighborsLines"
                OSPFv2NeighborsLines.append(line)
                continue
            # Syntax: ALU/Nokia SR-OS
            searchExpression = re.escape(shellPrompt)+r"[ ]*sh(o(w)?)? +ro(u(t(e(r)?)?)?)? +os(p(f)?)? +al(l)? +ne(i(g(h(b(o(r(s)?)?)?)?)?)?)? +de(t(a(i(l)?)?)?)?"
            if re.search(re.compile(searchExpression),line):
                # if redirectOutputTo != "OSPFv2NeighborsLines":
                #     if debug: print("debug: "+ redirectOutputTo +" output ends at line "+str(lineNumber)+": "+line)
                # if debug: print("debug: Found OSPFv2 neighbors beginning at line "+str(lineNumber)+": "+line)
                redirectOutputTo = "OSPFv2NeighborsLines"
                OSPFv2NeighborsLines.append(line)
                continue
            # Match ISIS neighbors output
            # Syntax: Cisco IOS/IOS-XE/IOS-XR
            searchExpression = re.escape(shellPrompt)+r"[ ]*sh(o(w)?)? +is(i(s)?)? +(ne(i(g(h(b(o(r(s)?)?)?)?)?)?)?|ad(j(a(c(e(n(c(y)?)?)?)?)?)?)?) +de(t(a(i(l)?)?)?)?"
            if re.search(re.compile(searchExpression),line):
                # if redirectOutputTo != "ISISNeighborsLines":
                #     if debug: print("debug: "+ redirectOutputTo +" output ends at line "+str(lineNumber)+": "+line)
                # if debug: print("debug: Found ISIS neighbors beginning at line "+str(lineNumber)+": "+line)
                redirectOutputTo = "ISISNeighborsLines"
                ISISNeighborsLines.append(line)
                continue
            # Syntax: Huawei VRP
            searchExpression = re.escape(shellPrompt)+r"[ ]*dis(p(l(a(y)?)?)?)? +is(i(s)?)? +pe(e(r)?)? +ve(r(b(o(s(e)?)?)?)?)?"
            if re.search(re.compile(searchExpression),line):
                # if redirectOutputTo != "ISISNeighborsLines":
                #     if debug: print("debug: "+ redirectOutputTo +" output ends at line "+str(lineNumber)+": "+line)
                # if debug: print("debug: Found ISIS neighbors beginning at line "+str(lineNumber)+": "+line)
                redirectOutputTo = "ISISNeighborsLines"
                ISISNeighborsLines.append(line)
            # Syntax: ALU/Nokia SR-OS
            searchExpression = re.escape(shellPrompt)+r"[ ]*sh(o(w)?)? +ro(u(t(e(r)?)?)?)? +is(i(s)?)? +al(l)? +ad(j(a(c(e(n(c(y)?)?)?)?)?)?)? +de(t(a(i(l)?)?)?)?"
            if re.search(re.compile(searchExpression),line):
                # if redirectOutputTo != "ISISNeighborsLines":
                #     if debug: print("debug: "+ redirectOutputTo +" output ends at line "+str(lineNumber)+": "+line)
                # if debug: print("debug: Found ISIS neighbors beginning at line "+str(lineNumber)+": "+line)
                redirectOutputTo = "ISISNeighborsLines"
                ISISNeighborsLines.append(line)
                continue
            # Match LDP neighbors output
            # Syntax: Cisco IOS/IOS-XE/IOS-XR
            searchExpression = re.escape(shellPrompt)+r"[ ]*sh(o(w)?)? +mp(l(s)?)? +l(d(p)?)? +ne(i(g(h(b(o(r(s)?)?)?)?)?)?)? +de(t(a(i(l)?)?)?)?"
            if re.search(re.compile(searchExpression),line):
                # if redirectOutputTo != "LDPNeighborsLines":
                #     if debug: print("debug: "+ redirectOutputTo +" output ends at line "+str(lineNumber)+": "+line)
                # if debug: print("debug: Found LDP neighbors beginning at line "+str(lineNumber)+": "+line)
                redirectOutputTo = "LDPNeighborsLines"
                LDPNeighborsLines.append(line)
                continue
            # Syntax: Huawei VRP
            searchExpression = re.escape(shellPrompt)+r"[ ]*dis(p(l(a(y)?)?)?)? +mp(l(s)?)? +l(d(p)?)? +pe(e(r)?)? +ve(r(b(o(s(e)?)?)?)?)?"
            if re.search(re.compile(searchExpression),line):
                # if redirectOutputTo != "LDPNeighborsLines":
                #     if debug: print("debug: "+ redirectOutputTo +" output ends at line "+str(lineNumber)+": "+line)
                # if debug: print("debug: Found LDP neighbors beginning at line "+str(lineNumber)+": "+line)
                redirectOutputTo = "LDPNeighborsLines"
                LDPNeighborsLines.append(line)
                continue
            # Syntax: ALU/Nokia SR-OS
            searchExpression = re.escape(shellPrompt)+r"[ ]*sh(o(w)?)? +ro(u(t(e(r)?)?)?)? +l(d(p)?)? +se(s(s(i(o(n)?)?)?)?)? +de(t(a(i(l)?)?)?)?"
            if re.search(re.compile(searchExpression),line):
                # if redirectOutputTo != "LDPNeighborsLines":
                #     if debug: print("debug: "+ redirectOutputTo +" output ends at line "+str(lineNumber)+": "+line)
                # if debug: print("debug: Found LDP neighbors beginning at line "+str(lineNumber)+": "+line)
                redirectOutputTo = "LDPNeighborsLines"
                LDPNeighborsLines.append(line)
                continue
            # Match BGP neighbors output
            # Syntax: Cisco IOS/IOS-XE/IOS-XR
            searchExpression = re.escape(shellPrompt)+r"[ ]*sh(o(w)?)? +(ip +)?bg(p)? +ne(i(g(h(b(o(r(s)?)?)?)?)?)?)?"
            if re.search(re.compile(searchExpression),line):
                # if redirectOutputTo != "BGPNeighborsLines":
                #     if debug: print("debug: "+ redirectOutputTo +" output ends at line "+str(lineNumber)+": "+line)
                # if debug: print("debug: Found BGP neighbors beginning at line "+str(lineNumber)+": "+line)
                redirectOutputTo = "BGPNeighborsLines"
                BGPNeighborsLines.append(line)
                continue
            # Syntax: Huawei VRP
            searchExpression = re.escape(shellPrompt)+r"[ ]*dis(p(l(a(y)?)?)?)? +bg(p)? +pe(e(r)?)? +ve(r(b(o(s(e)?)?)?)?)?"
            if re.search(re.compile(searchExpression),line):
                # if redirectOutputTo != "BGPNeighborsLines":
                #     if debug: print("debug: "+ redirectOutputTo +" output ends at line "+str(lineNumber)+": "+line)
                # if debug: print("debug: Found BGP neighbors beginning at line "+str(lineNumber)+": "+line)
                redirectOutputTo = "BGPNeighborsLines"
                BGPNeighborsLines.append(line)
                continue
            # Syntax: ALU/Nokia SR-OS
            searchExpression = re.escape(shellPrompt)+r"[ ]*sh(o(w)?)? +ro(u(t(e(r)?)?)?)? +bg(p)? +ne(i(g(h(b(o(r(s)?)?)?)?)?)?)?"
            if re.search(re.compile(searchExpression),line):
                # if redirectOutputTo != "BGPNeighborsLines":
                #     if debug: print("debug: "+ redirectOutputTo +" output ends at line "+str(lineNumber)+": "+line)
                # if debug: print("debug: Found BGP neighbors beginning at line "+str(lineNumber)+": "+line)
                redirectOutputTo = "BGPNeighborsLines"
                BGPNeighborsLines.append(line)
                continue

            # Match unknown command output
            # Syntax: all
            searchExpression = r"^"+re.escape(shellPrompt)
            if re.search(re.compile(searchExpression),line):
                # if debug: print("debug: Found unknown output beginning at line "+str(lineNumber)+": "+line)
                # if redirectOutputTo != "default":
                    # if debug: print("debug: "+ redirectOutputTo +" output ends at line "+str(lineNumber)+": "+line)
                redirectOutputTo = "default"
                continue

            # Redirect already classified output to appropriate list
            if redirectOutputTo == "CDPNeighborsLines":
                CDPNeighborsLines.append(line)
                continue
            if redirectOutputTo == "LLDPNeighborsLines":
                LLDPNeighborsLines.append(line)
                continue
            if redirectOutputTo == "OSPFv2NeighborsLines":
                OSPFv2NeighborsLines.append(line)
                continue
            if redirectOutputTo == "ISISNeighborsLines":
                ISISNeighborsLines.append(line)
                continue
            if redirectOutputTo == "LDPNeighborsLines":
                LDPNeighborsLines.append(line)
                continue
            if redirectOutputTo == "BGPNeighborsLines":
                BGPNeighborsLines.append(line)
                continue

        ################################################### Update/enrich peering info from output of show commands ###################################################

        ################################################### CDP output ###################################################

        # PeeringParseAll.clear()
        tempPeeringParseAll = []

        CDPNeighborsText = "\n".join(CDPNeighborsLines)
        CDPNeighborsText = CDPNeighborsText + "\n"

        # Syntax: Cisco IOS-XR
        if (CLISyntax == "IOS-XR"):
            # Look for CDP entries to find neighbor information
            neighborDelimiter = "-------------------------"
            for neighborText in CDPNeighborsText.split(neighborDelimiter):
                # print(neighborText)
                tempPeeringParse = [""] * len(PeeringDict)

                tempPeeringParse[PeeringDict["PeeringType"][0]] = "CDP"

                # Collecting data for current neighbor
                for line in neighborText.split("\n"):

                    # Check for local interface name in CDP output
                    if re.search(r"Interface *:",line):
                        tempPeeringParse[PeeringDict["PortName"][0]] = line.split(":")[1].lstrip().rstrip().split(" ")[0]
                    # Check for remote interface name in CDP output
                    if re.search(r"\(outgoing port\) *:",line):
                        tempPeeringParse[PeeringDict["PortNameRemote"][0]] = line.split(":")[1].lstrip().rstrip().split(" ")[0]
                        continue

                    # Check for remote system name in CDP output
                    if re.search(r"SysName *:",line):
                        tempHostname = line.split(":")[1].lstrip().rstrip().split(".")[0]
                        if tempHostname != "":
                            tempPeeringParse[PeeringDict["HostnameRemote"][0]] = tempHostname
                        continue
                    # Check for remote system ID in CDP output
                    if tempPeeringParse[PeeringDict["HostnameRemote"][0]] == "":
                        if re.search(r"Device ID *:",line):
                            tempHostname = line.split(":")[1].lstrip().rstrip().split(".")[0]
                            if tempHostname != "":
                                tempPeeringParse[PeeringDict["HostnameRemote"][0]] = tempHostname
                        continue

                    # Check for remote IP adresses in CDP output
                    if re.search(r"IPv4 address *:",line):
                        rawInput = line.split(":")[1].lstrip().rstrip().split(" ")[0]
                        ipadd = ipaddress.ip_address(str(rawInput))

                        if ( str(ipadd) not in tempPeeringParse[PeeringDict["SysAddrRemote"][0]].split("|") ):
                            if (( tempPeeringParse[PeeringDict["SysAddrRemote"][0]] != "" )):
                                tempPeeringParse[PeeringDict["SysAddrRemote"][0]] = tempPeeringParse[PeeringDict["SysAddrRemote"][0]] + "|"
                            tempPeeringParse[PeeringDict["SysAddrRemote"][0]] = tempPeeringParse[PeeringDict["SysAddrRemote"][0]] + str(ipadd)
                        continue

                    # Check for remote CLI syntax in CDP output
                    if tempPeeringParse[PeeringDict["CLISyntaxRemote"][0]] == "":
                        if re.search(r'.*Cisco IOS XR',line):
                            tempPeeringParse[PeeringDict["CLISyntaxRemote"][0]] = "IOS-XR"
                            continue
                    if tempPeeringParse[PeeringDict["CLISyntaxRemote"][0]] == "":
                        if re.search(r'.*Cisco IOS((-| )XE)? ',line):
                            tempPeeringParse[PeeringDict["CLISyntaxRemote"][0]] = "IOS"
                            continue
                    if tempPeeringParse[PeeringDict["CLISyntaxRemote"][0]] == "":
                        if re.search(r'.*TiMOS-',line):
                            tempPeeringParse[PeeringDict["CLISyntaxRemote"][0]] = "SR-OS"
                            continue
                    if tempPeeringParse[PeeringDict["CLISyntaxRemote"][0]] == "":
                        if re.search(r'.*VRP \(R\) software',line):
                            tempPeeringParse[PeeringDict["CLISyntaxRemote"][0]] = "VRP"
                            continue

                if tempPeeringParse[PeeringDict["PortName"][0]] == "":
                    continue
                else:
                    tempPeeringParseAll.append(tempPeeringParse)


        # Syntax: Cisco IOS/IOS-XE
        if (CLISyntax == "IOS"):
            # Look for CDP entries to find neighbor information
            neighborDelimiter = "-------------------------"
            for neighborText in CDPNeighborsText.split(neighborDelimiter):
                # print(neighborText)
                tempPeeringParse = [""] * len(PeeringDict)

                tempPeeringParse[PeeringDict["PeeringType"][0]] = "CDP"

                # Collecting data for current neighbor
                for line in neighborText.split("\n"):

                    # Check for local interface name in CDP output
                    if re.search(r"Interface *:",line):
                        tempPeeringParse[PeeringDict["PortName"][0]] = line.split(":")[1].split(",")[0].lstrip().rstrip()
                    # Check for remote interface name in CDP output
                    if re.search(r"\(outgoing port\) *:",line):
                        tempPeeringParse[PeeringDict["PortNameRemote"][0]] = line.split("):")[1].lstrip().rstrip().split(" ")[0]
                        continue

                    # Check for remote system name in CDP output
                    if re.search(r"SysName *:",line):
                        tempHostname = line.split(":")[1].lstrip().rstrip().split(".")[0]
                        if tempHostname != "":
                            tempPeeringParse[PeeringDict["HostnameRemote"][0]] = tempHostname
                        continue
                    # Check for remote system ID in CDP output
                    if tempPeeringParse[PeeringDict["HostnameRemote"][0]] == "":
                        if re.search(r"Device ID *:",line):
                            tempHostname = line.split(":")[1].lstrip().rstrip().split(".")[0]
                            if tempHostname != "":
                                tempPeeringParse[PeeringDict["HostnameRemote"][0]] = tempHostname
                        continue

                    # Check for remote IP adresses in CDP output
                    if re.search(r"IP address *:",line):
                        rawInput = line.split(":")[1].lstrip().rstrip().split(" ")[0]
                        ipadd = ipaddress.ip_address(str(rawInput))

                        if ( str(ipadd) not in tempPeeringParse[PeeringDict["SysAddrRemote"][0]].split("|") ):
                            if (( tempPeeringParse[PeeringDict["SysAddrRemote"][0]] != "" )):
                                tempPeeringParse[PeeringDict["SysAddrRemote"][0]] = tempPeeringParse[PeeringDict["SysAddrRemote"][0]] + "|"
                            tempPeeringParse[PeeringDict["SysAddrRemote"][0]] = tempPeeringParse[PeeringDict["SysAddrRemote"][0]] + str(ipadd)
                        continue

                    # Check for remote CLI syntax in CDP output
                    if tempPeeringParse[PeeringDict["CLISyntaxRemote"][0]] == "":
                        if re.search(r'.*Cisco IOS XR',line):
                            tempPeeringParse[PeeringDict["CLISyntaxRemote"][0]] = "IOS-XR"
                            continue
                    if tempPeeringParse[PeeringDict["CLISyntaxRemote"][0]] == "":
                        if re.search(r'.*Cisco IOS((-| )XE)? ',line):
                            tempPeeringParse[PeeringDict["CLISyntaxRemote"][0]] = "IOS"
                            continue
                    if tempPeeringParse[PeeringDict["CLISyntaxRemote"][0]] == "":
                        if re.search(r'.*TiMOS-',line):
                            tempPeeringParse[PeeringDict["CLISyntaxRemote"][0]] = "SR-OS"
                            continue
                    if tempPeeringParse[PeeringDict["CLISyntaxRemote"][0]] == "":
                        if re.search(r'.*VRP \(R\) software',line):
                            tempPeeringParse[PeeringDict["CLISyntaxRemote"][0]] = "VRP"
                            continue

                if tempPeeringParse[PeeringDict["PortName"][0]] == "":
                    continue
                else:
                    tempPeeringParseAll.append(tempPeeringParse)

        # if debug:
        #     # Write summary neighbors data to a file for debug purposes
        #     with open(outputFilePath, 'a') as outputFile:
        #         if len(PeeringParseAll) > 0:
        #             outputFile.write("DEBUG: Summary neighbor information from all sources is shown below:\n\n")
        #             outputFile.write("\t".join(str(item) for item in PeeringDict))
        #             outputFile.write("\n")
        #             for peeringLine in PeeringParseAll:
        #                 outputFile.write("\t".join(str(item) for item in peeringLine))
        #                 outputFile.write("\n")
        #         outputFile.write("\n")

        # Enrich peering table with parsed data from CDP
        for tempPeeringParse in tempPeeringParseAll:
            # Updating data for existing neighbors
            lineIndex = 0
            match1 = 0
            for peeringLine in PeeringParseAll:
                if tempPeeringParse[PeeringDict["PortName"][0]] == peeringLine[PeeringDict["PortName"][0]]:
                    match1 = 1
                    if tempPeeringParse[PeeringDict["PeeringType"][0]] not in peeringLine[PeeringDict["PeeringType"][0]].split("|"):
                        if PeeringParseAll[lineIndex][PeeringDict["PeeringType"][0]] != "":
                            PeeringParseAll[lineIndex][PeeringDict["PeeringType"][0]] = PeeringParseAll[lineIndex][PeeringDict["PeeringType"][0]] + "|"
                        PeeringParseAll[lineIndex][PeeringDict["PeeringType"][0]] = PeeringParseAll[lineIndex][PeeringDict["PeeringType"][0]] + tempPeeringParse[PeeringDict["PeeringType"][0]]

                    if tempPeeringParse[PeeringDict["PortNameRemote"][0]] not in peeringLine[PeeringDict["PortNameRemote"][0]].split("|"):
                        if PeeringParseAll[lineIndex][PeeringDict["PortNameRemote"][0]] != "":
                            PeeringParseAll[lineIndex][PeeringDict["PortNameRemote"][0]] = PeeringParseAll[lineIndex][PeeringDict["PortNameRemote"][0]] + "|"
                        PeeringParseAll[lineIndex][PeeringDict["PortNameRemote"][0]] = PeeringParseAll[lineIndex][PeeringDict["PortNameRemote"][0]] + tempPeeringParse[PeeringDict["PortNameRemote"][0]]

                    if tempPeeringParse[PeeringDict["HostnameRemote"][0]] not in peeringLine[PeeringDict["HostnameRemote"][0]].split("|"):
                        if PeeringParseAll[lineIndex][PeeringDict["HostnameRemote"][0]] != "":
                            PeeringParseAll[lineIndex][PeeringDict["HostnameRemote"][0]] = PeeringParseAll[lineIndex][PeeringDict["HostnameRemote"][0]] + "|"
                        PeeringParseAll[lineIndex][PeeringDict["HostnameRemote"][0]] = PeeringParseAll[lineIndex][PeeringDict["HostnameRemote"][0]] + tempPeeringParse[PeeringDict["HostnameRemote"][0]]

                    if tempPeeringParse[PeeringDict["HostnameRemote"][0]] not in peeringLine[PeeringDict["HostnameRemote"][0]].split("|"):
                        if PeeringParseAll[lineIndex][PeeringDict["HostnameRemote"][0]] != "":
                            PeeringParseAll[lineIndex][PeeringDict["HostnameRemote"][0]] = PeeringParseAll[lineIndex][PeeringDict["HostnameRemote"][0]] + "|"
                        PeeringParseAll[lineIndex][PeeringDict["HostnameRemote"][0]] = PeeringParseAll[lineIndex][PeeringDict["HostnameRemote"][0]] + tempPeeringParse[PeeringDict["HostnameRemote"][0]]

                    if tempPeeringParse[PeeringDict["SysAddrRemote"][0]] != "" and tempPeeringParse[PeeringDict["SysAddrRemote"][0]] != peeringLine[PeeringDict["SysAddrRemote"][0]]:
                        PeeringParseAll[lineIndex][PeeringDict["SysAddrRemote"][0]] = tempPeeringParse[PeeringDict["SysAddrRemote"][0]]
                        PeeringParseAll[lineIndex][PeeringDict["Comments"][0]] = "Remote system IP updated from CDP"
                    elif tempPeeringParse[PeeringDict["SysAddrRemote"][0]] != "":
                        if "CDP" not in PeeringParseAll[lineIndex][PeeringDict["Comments"][0]]:
                            PeeringParseAll[lineIndex][PeeringDict["Comments"][0]] = PeeringParseAll[lineIndex][PeeringDict["Comments"][0]] + "|CDP"


                    if tempPeeringParse[PeeringDict["CLISyntaxRemote"][0]] not in peeringLine[PeeringDict["CLISyntaxRemote"][0]].split("|"):
                        if PeeringParseAll[lineIndex][PeeringDict["CLISyntaxRemote"][0]] != "":
                            PeeringParseAll[lineIndex][PeeringDict["CLISyntaxRemote"][0]] = PeeringParseAll[lineIndex][PeeringDict["CLISyntaxRemote"][0]] + "|"
                        PeeringParseAll[lineIndex][PeeringDict["CLISyntaxRemote"][0]] = PeeringParseAll[lineIndex][PeeringDict["CLISyntaxRemote"][0]] + tempPeeringParse[PeeringDict["CLISyntaxRemote"][0]]

                lineIndex = lineIndex + 1

            # Look for other interfaces that were not included in peering table earlier if there are matching ports
            for interfaceLine in InterfacesParseAll:
                match2 = 0
                # Checking if this interface is already in peering table
                for peeringLine in PeeringParseAll:
                    if peeringLine[PeeringDict["IfName"][0]] == interfaceLine[InterfacesDict["IfName"][0]]:
                        match2 = 1
                        break
                if match2 == 1:
                    continue

                if tempPeeringParse[PeeringDict["PortName"][0]] in interfaceLine[InterfacesDict["PortName"][0]].split("|"):
                    match1 = 1
                    PeeringParse = [""] * len(PeeringDict)

                    PeeringParse[PeeringDict["PeeringType"][0]] = "CDP"
                    PeeringParse[PeeringDict["Hostname"][0]] = Hostname
                    PeeringParse[PeeringDict["SysAddr"][0]] = SysAddr
                    PeeringParse[PeeringDict["CLISyntax"][0]] = CLISyntax
                    PeeringParse[PeeringDict["IfName"][0]] = interfaceLine[InterfacesDict["IfName"][0]]
                    PeeringParse[PeeringDict["IfDescr"][0]] = interfaceLine[InterfacesDict["IfDescr"][0]]
                    PeeringParse[PeeringDict["PortBinding"][0]] = interfaceLine[InterfacesDict["PortBinding"][0]]
                    PeeringParse[PeeringDict["IPV4Addr"][0]] = interfaceLine[InterfacesDict["IPV4Addr"][0]]
                    PeeringParse[PeeringDict["IPV4Subnet"][0]] = interfaceLine[InterfacesDict["IPV4Subnet"][0]]
                    PeeringParse[PeeringDict["IPV6Addr"][0]] = interfaceLine[InterfacesDict["IPV6Addr"][0]]
                    PeeringParse[PeeringDict["IPV6Subnet"][0]] = interfaceLine[InterfacesDict["IPV6Subnet"][0]]


                    for tempPortName in interfaceLine[InterfacesDict["PortName"][0]].split("|"):
                        tempPeeringParse2 = PeeringParse.copy()

                        if tempPeeringParse[PeeringDict["PortName"][0]] == tempPortName:
                            tempPeeringParse2[PeeringDict["PortName"][0]] = tempPortName
                            tempPeeringParse2[PeeringDict["PortNameRemote"][0]] = tempPeeringParse[PeeringDict["PortNameRemote"][0]]
                            tempPeeringParse2[PeeringDict["HostnameRemote"][0]] = tempPeeringParse[PeeringDict["HostnameRemote"][0]]
                            if tempPeeringParse[PeeringDict["SysAddrRemote"][0]] != "":
                                tempPeeringParse2[PeeringDict["SysAddrRemote"][0]] = tempPeeringParse[PeeringDict["SysAddrRemote"][0]]
                                tempPeeringParse2[PeeringDict["Comments"][0]] = "Remote system IP updated from CDP"
                            tempPeeringParse2[PeeringDict["CLISyntaxRemote"][0]] = tempPeeringParse[PeeringDict["CLISyntaxRemote"][0]]

                        PeeringParseAll.append(tempPeeringParse2)

            if match1 == 0:
                print("Error: CDP peer " + tempPeeringParse[PeeringDict["PortName"][0]] + " is not found in peering and interface tables")

       ################################################### Print peering information from CDP ###################################################

        # Write CDP data to a file (for diagnostic purposes)
        with open(outputFilePath, 'a') as outputFile:
            if len(tempPeeringParseAll) > 0:
                outputFile.write("Found following neighbors from CDP:\n")
                # Print header
                valueNumber = 0
                for value in printPeeringValueList:
                    if valueNumber == 0:
                        outputFile.write(str(value))
                    else:
                        outputFile.write("\t" + str(value))
                    valueNumber = valueNumber + 1
                outputFile.write("\n")
                # Print data
                for peeringLine in tempPeeringParseAll:
                    valueNumber = 0
                    for value in printPeeringValueList:
                        if valueNumber == 0:
                            outputFile.write(str(peeringLine[PeeringDict[value][0]]))
                        else:
                            outputFile.write("\t" + str(peeringLine[PeeringDict[value][0]]))
                        valueNumber = valueNumber + 1
                    outputFile.write("\n")
                outputFile.write("\n")

       ################################################### Print summary peering information from all sources to debug file ###################################################

        # Write summary neighbors data to a file
        with open("./" + outputPath + "/debugText.txt", 'a') as debugTextFile:
            if len(PeeringParseAll) > 0:
                debugTextFile.write("Summary neighbor information from all sources (after CDP enrichment) is shown below:\n")
                # Print header
                valueNumber = 0
                for value in printPeeringValueList:
                    if valueNumber == 0:
                        debugTextFile.write(str(value))
                    else:
                        debugTextFile.write("\t" + str(value))
                    valueNumber = valueNumber + 1
                debugTextFile.write("\n")
                # Print data
                for peeringLine in PeeringParseAll:
                    valueNumber = 0
                    for value in printPeeringValueList:
                        if valueNumber == 0:
                            debugTextFile.write(str(peeringLine[PeeringDict[value][0]]))
                        else:
                            debugTextFile.write("\t" + str(peeringLine[PeeringDict[value][0]]))
                        valueNumber = valueNumber + 1
                    debugTextFile.write("\n")
                debugTextFile.write("\n")


        ################################################### LLDP output ###################################################

        # PeeringParseAll.clear()
        tempPeeringParseAll = []

        LLDPNeighborsText = "\n".join(LLDPNeighborsLines)
        LLDPNeighborsText = LLDPNeighborsText + "\n"

        # Syntax: Cisco IOS-XR
        if (CLISyntax == "IOS-XR"):
            # Look for LLDP entries to find neighbor information
            neighborDelimiter = "------------------------------------------------"
            for neighborText in LLDPNeighborsText.split(neighborDelimiter):
                # print(neighborText)
                tempPeeringParse = [""] * len(PeeringDict)

                tempPeeringParse[PeeringDict["PeeringType"][0]] = "LLDP"

                # Collecting data for current neighbor
                for line in re.split(r"\r*\n",neighborText):

                    # Check for local interface name in LLDP output
                    if re.search(r"Local Interface *:",line):
                        tempPeeringParse[PeeringDict["PortName"][0]] = line.split(":")[1].lstrip().rstrip().split(" ")[0]
                    # Check for remote interface name in LLDP output
                    if re.search(r"Port id *:",line):
                        tempPeeringParse[PeeringDict["PortNameRemote"][0]] = line.split(":")[1].lstrip().rstrip().split(" ")[0]
                        continue

                    if re.search(r"Port Description *:",line):
                        tempPeeringParse[PeeringDict["PortDescrRemote"][0]] = line.split(": ")[1]
                        continue

                    # Check for remote system name in LLDP output
                    if re.search(r"System Name *:",line):
                        tempHostname = line.split(":")[1].lstrip().rstrip().split(".")[0]
                        if tempHostname != "":
                            tempPeeringParse[PeeringDict["HostnameRemote"][0]] = tempHostname
                        continue

                    # Check for remote IP adresses in LLDP output
                    if re.search(r"IPv4 address *:",line):
                        rawInput = line.split(":")[1].lstrip().rstrip().split(" ")[0]
                        ipadd = ipaddress.ip_address(str(rawInput))

                        if ( str(ipadd) not in tempPeeringParse[PeeringDict["SysAddrRemote"][0]].split("|") ):
                            if (( tempPeeringParse[PeeringDict["SysAddrRemote"][0]] != "" )):
                                tempPeeringParse[PeeringDict["SysAddrRemote"][0]] = tempPeeringParse[PeeringDict["SysAddrRemote"][0]] + "|"
                            tempPeeringParse[PeeringDict["SysAddrRemote"][0]] = tempPeeringParse[PeeringDict["SysAddrRemote"][0]] + str(ipadd)
                        continue

                    # Check for remote CLI syntax in LLDP output
                    if tempPeeringParse[PeeringDict["CLISyntaxRemote"][0]] == "":
                        if re.search(r'.*Cisco IOS XR',line):
                            tempPeeringParse[PeeringDict["CLISyntaxRemote"][0]] = "IOS-XR"
                            continue
                    if tempPeeringParse[PeeringDict["CLISyntaxRemote"][0]] == "":
                        if re.search(r'.*Cisco IOS((-| )XE)? ',line):
                            tempPeeringParse[PeeringDict["CLISyntaxRemote"][0]] = "IOS"
                            continue
                    if tempPeeringParse[PeeringDict["CLISyntaxRemote"][0]] == "":
                        if re.search(r'.*TiMOS-',line):
                            tempPeeringParse[PeeringDict["CLISyntaxRemote"][0]] = "SR-OS"
                            continue
                    if tempPeeringParse[PeeringDict["CLISyntaxRemote"][0]] == "":
                        if re.search(r'.*VRP \(R\) software',line):
                            tempPeeringParse[PeeringDict["CLISyntaxRemote"][0]] = "VRP"
                            continue

                if tempPeeringParse[PeeringDict["PortName"][0]] == "":
                    continue
                else:
                    tempPeeringParseAll.append(tempPeeringParse)


        # Syntax: Cisco IOS/IOS-XE
        if (CLISyntax == "IOS"):
            # Look for LLDP entries to find neighbor information
            neighborDelimiter = "------------------------------------------------"
            for neighborText in LLDPNeighborsText.split(neighborDelimiter):
                # print(neighborText)
                tempPeeringParse = [""] * len(PeeringDict)

                tempPeeringParse[PeeringDict["PeeringType"][0]] = "LLDP"

                # Collecting data for current neighbor
                for line in re.split(r"\r*\n",neighborText):

                    # Check for local interface name in LLDP output
                    if re.search(r"Local Interface *:",line):
                        tempPeeringParse[PeeringDict["PortName"][0]] = line.split(":")[1].lstrip().rstrip().split(" ")[0]
                    # Check for remote interface name in LLDP output
                    if re.search(r"Port id *:",line):
                        tempPeeringParse[PeeringDict["PortNameRemote"][0]] = line.split(": ")[1].lstrip().rstrip().split(" ")[0]
                        continue

                    if re.search(r"Port Description *:",line):
                        tempPeeringParse[PeeringDict["PortDescrRemote"][0]] = line.split(": ")[1]
                        continue

                    # Check for remote system name in LLDP output
                    if re.search(r"System Name *:",line):
                        tempHostname = line.split(": ")[1].lstrip().rstrip().split(".")[0]
                        if tempHostname != "":
                            tempPeeringParse[PeeringDict["HostnameRemote"][0]] = tempHostname
                        continue
                    # Check for remote system ID in LLDP output
                    if tempPeeringParse[PeeringDict["HostnameRemote"][0]] == "":
                        if re.search(r"Device ID *:",line):
                            tempHostname = line.split(":")[1].lstrip().rstrip().split(".")[0]
                            if tempHostname != "":
                                tempPeeringParse[PeeringDict["HostnameRemote"][0]] = tempHostname
                        continue

                    # Check for remote IP adresses in LLDP output
                    if re.search(r"IPv4 address *:",line):
                        rawInput = line.split(":")[1].lstrip().rstrip().split(" ")[0]
                        ipadd = ipaddress.ip_address(str(rawInput))

                        if ( str(ipadd) not in tempPeeringParse[PeeringDict["SysAddrRemote"][0]].split("|") ):
                            if (( tempPeeringParse[PeeringDict["SysAddrRemote"][0]] != "" )):
                                tempPeeringParse[PeeringDict["SysAddrRemote"][0]] = tempPeeringParse[PeeringDict["SysAddrRemote"][0]] + "|"
                            tempPeeringParse[PeeringDict["SysAddrRemote"][0]] = tempPeeringParse[PeeringDict["SysAddrRemote"][0]] + str(ipadd)
                        continue

                    # Check for remote CLI syntax in LLDP output
                    if tempPeeringParse[PeeringDict["CLISyntaxRemote"][0]] == "":
                        if re.search(r'.*Cisco IOS XR',line):
                            tempPeeringParse[PeeringDict["CLISyntaxRemote"][0]] = "IOS-XR"
                            continue
                    if tempPeeringParse[PeeringDict["CLISyntaxRemote"][0]] == "":
                        if re.search(r'.*Cisco IOS((-| )XE)? ',line):
                            tempPeeringParse[PeeringDict["CLISyntaxRemote"][0]] = "IOS"
                            continue
                    if tempPeeringParse[PeeringDict["CLISyntaxRemote"][0]] == "":
                        if re.search(r'.*TiMOS-',line):
                            tempPeeringParse[PeeringDict["CLISyntaxRemote"][0]] = "SR-OS"
                            continue
                    if tempPeeringParse[PeeringDict["CLISyntaxRemote"][0]] == "":
                        if re.search(r'.*VRP \(R\) software',line):
                            tempPeeringParse[PeeringDict["CLISyntaxRemote"][0]] = "VRP"
                            continue

                if tempPeeringParse[PeeringDict["PortName"][0]] == "":
                    continue
                else:
                    tempPeeringParseAll.append(tempPeeringParse)

        # Syntax: Huawei VRP
        if (CLISyntax == "VRP"):
            # Look for LLDP entries to find neighbor information
            interfaceDelimiter = r"\r*\n\r*\n\r*\n"
            for interfaceText in re.split(interfaceDelimiter,LLDPNeighborsText):
                # Check for local interface name in LLDP output
                tempPortName = ""
                for line in interfaceText.split("\n"):
                    if re.search(r"has \d+ neighbor(s)? *:",line):
                        tempPortName = line.split(" ")[0]
                        break
                # Check for neighbor parameters if local interface was found
                if tempPortName != "":
                    neighborDelimiter = r"Neighbor \d+ *: *"
                    # Check if interface has neighbors
                    if len(re.split(neighborDelimiter,interfaceText)) == 1:
                        continue

                    for neighborText in re.split(neighborDelimiter,interfaceText):
                        # Skip text if it has no remote port id
                        if not re.search(r"PortId",neighborText):
                            continue

                        tempPeeringParse = [""] * len(PeeringDict)
                        tempPeeringParse[PeeringDict["PeeringType"][0]] = "LLDP"

                        # Collecting data for current neighbor
                        for line in re.split(r"\r*\n",neighborText):
                            tempPeeringParse[PeeringDict["PortName"][0]] = tempPortName

                            # Check for remote interface name in LLDP output
                            if re.search(r"PortId *:",line):
                                tempPeeringParse[PeeringDict["PortNameRemote"][0]] = line.split(":")[1].lstrip().rstrip().split(",")[0]
                                continue
                            # Check for remote interface name in LLDP output
                            if re.search(r"PortDesc *:",line):
                                tempPeeringParse[PeeringDict["PortDescrRemote"][0]] = line.split(":")[1].lstrip().rstrip()
                                continue

                            # Check for remote system name in LLDP output
                            if re.search(r"SysName *:",line):
                                tempHostname = line.split(":")[1].lstrip().rstrip().split(".")[0]
                                if tempHostname != "":
                                    tempPeeringParse[PeeringDict["HostnameRemote"][0]] = tempHostname
                                    continue

                            # Check for remote IP adresses in LLDP output
                            if re.search(r"ipV4 *:",line):
                                rawInput = line.split("ipV4:")[1].lstrip().rstrip().split(" ")[0]
                                ipadd = ipaddress.ip_address(str(rawInput))

                                if ( str(ipadd) not in tempPeeringParse[PeeringDict["SysAddrRemote"][0]].split("|") ):
                                    if (( tempPeeringParse[PeeringDict["SysAddrRemote"][0]] != "" )):
                                        tempPeeringParse[PeeringDict["SysAddrRemote"][0]] = tempPeeringParse[PeeringDict["SysAddrRemote"][0]] + "|"
                                    tempPeeringParse[PeeringDict["SysAddrRemote"][0]] = tempPeeringParse[PeeringDict["SysAddrRemote"][0]] + str(ipadd)
                                continue

                            # Check for remote CLI syntax in LLDP output
                            if tempPeeringParse[PeeringDict["CLISyntaxRemote"][0]] == "":
                                if re.search(r'.*Cisco IOS XR',line):
                                    tempPeeringParse[PeeringDict["CLISyntaxRemote"][0]] = "IOS-XR"
                                    continue
                            if tempPeeringParse[PeeringDict["CLISyntaxRemote"][0]] == "":
                                if re.search(r'.*Cisco IOS((-| )XE)? ',line):
                                    tempPeeringParse[PeeringDict["CLISyntaxRemote"][0]] = "IOS"
                                    continue
                            if tempPeeringParse[PeeringDict["CLISyntaxRemote"][0]] == "":
                                if re.search(r'.*TiMOS-',line):
                                    tempPeeringParse[PeeringDict["CLISyntaxRemote"][0]] = "SR-OS"
                                    continue
                            if tempPeeringParse[PeeringDict["CLISyntaxRemote"][0]] == "":
                                if re.search(r'.*VRP \(R\) software',line):
                                    tempPeeringParse[PeeringDict["CLISyntaxRemote"][0]] = "VRP"
                                    continue

                        tempPeeringParseAll.append(tempPeeringParse)

        # Syntax: ALU/Nokia SR-OS
        if (CLISyntax == "SR-OS"):
            # Look for LLDP entries to find neighbor information
            interfaceDelimiter = r"=+"
            # for interfaceText in LLDPNeighborsText.split(interfaceDelimiter):
            for interfaceText in re.split(interfaceDelimiter,LLDPNeighborsText):
                # Check for local interface name in LLDP output
                tempPortName = ""
                for line in interfaceText.split("\n"):
                    if re.search(r"Port .* Remote Peer Information",line):
                        tempPortName = line.split(" ")[1]
                        break
                # Check for neighbor parameters if local interface was found
                if tempPortName != "":
                    neighborDelimiter = r"Remote Peer Index "
                    # Check if interface has neighbors
                    if len(re.split(neighborDelimiter,interfaceText)) == 1:
                        continue

                    for neighborText in re.split(neighborDelimiter,interfaceText):
                        # Skip text if it has no remote port id
                        if not re.search(r"Port Id",neighborText):
                            continue

                        # Get peer number
                        tempPeerNumber = neighborText.split(" ")[0]

                        tempPeeringParse = [""] * len(PeeringDict)
                        tempPeeringParse[PeeringDict["PeeringType"][0]] = "LLDP"
                        tempPeeringParse[PeeringDict["PortName"][0]] = tempPortName

                        tempSysDecr = ""
                        CurrentValue = ""
                        # Collecting data for current neighbor
                        for line in re.split(r"\r*\n",neighborText):
                            if re.search(r" *:",line):
                                CurrentValue = ""
                                # Check for remote interface name in LLDP output
                                if re.search(r"Port Id *:",line):
                                    tempPeeringParse[PeeringDict["PortNameRemote"][0]] = line.split(": ")[1].lstrip().rstrip().split(",")[0]
                                    continue
                                # Check for remote interface name in LLDP output
                                if re.search(r"Port Description *:",line):
                                    tempPeeringParse[PeeringDict["PortDescrRemote"][0]] = line.split(": ")[1]
                                    CurrentValue = "PortDescrRemote"
                                    continue

                                # Check for remote system name in LLDP output
                                if re.search(r"System Name *:",line):
                                    tempHostname = line.split(": ")[1].lstrip().rstrip().split(".")[0]
                                    if tempHostname != "":
                                        tempPeeringParse[PeeringDict["HostnameRemote"][0]] = tempHostname
                                    continue
                                # Check for remote system description in LLDP output
                                if re.search(r"System Description *:",line):
                                    tempSysDecr = line.split(": ")[1].lstrip().rstrip().split(".")[0]
                                    CurrentValue = "tempSysDecr"
                                    continue
                            else:
                                if CurrentValue == "PortDescrRemote":
                                    tempPeeringParse[PeeringDict[CurrentValue][0]] = tempPeeringParse[PeeringDict[CurrentValue][0]] + line.split("                        ")[1]
                                if CurrentValue == "tempSysDecr":
                                    tempSysDecr = tempSysDecr + line.split("                        ")[1]

                        # Check for remote CLI syntax in LLDP output
                        if tempPeeringParse[PeeringDict["CLISyntaxRemote"][0]] == "":
                            if re.search(r'.*Cisco IOS XR',tempSysDecr):
                                tempPeeringParse[PeeringDict["CLISyntaxRemote"][0]] = "IOS-XR"
                        if tempPeeringParse[PeeringDict["CLISyntaxRemote"][0]] == "":
                            if re.search(r'.*Cisco IOS((-| )XE)? ',tempSysDecr):
                                tempPeeringParse[PeeringDict["CLISyntaxRemote"][0]] = "IOS"
                        if tempPeeringParse[PeeringDict["CLISyntaxRemote"][0]] == "":
                            if re.search(r'.*TiMOS-',tempSysDecr):
                                tempPeeringParse[PeeringDict["CLISyntaxRemote"][0]] = "SR-OS"
                        if tempPeeringParse[PeeringDict["CLISyntaxRemote"][0]] == "":
                            if re.search(r'.*VRP \(R\) software',tempSysDecr):
                                tempPeeringParse[PeeringDict["CLISyntaxRemote"][0]] = "VRP"

                        for neighborText2 in re.split(neighborDelimiter,interfaceText):
                            # Check if peer numbers match
                            if neighborText2.split(" ")[0] == tempPeerNumber:

                                # Check for remote IP adresses in LLDP output
                                match = 0
                                for line in re.split(r"\r*\n",neighborText2):
                                    if re.search(r"Address SubType *:.*IPv4",line):
                                        match = 1
                                        continue
                                    if (( match == 1 ) and ( re.search(r"Address *:",line) )):
                                        match = 0
                                        rawInput = line.split(":")[1].lstrip().rstrip().split(" ")[0]
                                        ipadd = ipaddress.ip_address(str(rawInput))

                                        if ( str(ipadd) not in tempPeeringParse[PeeringDict["SysAddrRemote"][0]].split("|") ):
                                            if (( tempPeeringParse[PeeringDict["SysAddrRemote"][0]] != "" )):
                                                tempPeeringParse[PeeringDict["SysAddrRemote"][0]] = tempPeeringParse[PeeringDict["SysAddrRemote"][0]] + "|"
                                            tempPeeringParse[PeeringDict["SysAddrRemote"][0]] = tempPeeringParse[PeeringDict["SysAddrRemote"][0]] + str(ipadd)

                        tempPeeringParseAll.append(tempPeeringParse)

        # if debug:
        #     # Write summary neighbors data to a file for debug purposes
        #     with open(outputFilePath, 'a') as outputFile:
        #         if len(PeeringParseAll) > 0:
        #             outputFile.write("DEBUG: Summary neighbor information from all sources is shown below:\n\n")
        #             outputFile.write("\t".join(str(item) for item in PeeringDict))
        #             outputFile.write("\n")
        #             for peeringLine in PeeringParseAll:
        #                 outputFile.write("\t".join(str(item) for item in peeringLine))
        #                 outputFile.write("\n")
        #         outputFile.write("\n")

        # Enrich peering table with parsed data from LLDP
        for tempPeeringParse in tempPeeringParseAll:
            # Updating data for existing neighbors
            lineIndex = 0
            match1 = 0
            for peeringLine in PeeringParseAll:
                if tempPeeringParse[PeeringDict["PortName"][0]] == peeringLine[PeeringDict["PortName"][0]]:
                    match1 = 1
                    if tempPeeringParse[PeeringDict["PeeringType"][0]] not in peeringLine[PeeringDict["PeeringType"][0]].split("|"):
                        if PeeringParseAll[lineIndex][PeeringDict["PeeringType"][0]] != "":
                            PeeringParseAll[lineIndex][PeeringDict["PeeringType"][0]] = PeeringParseAll[lineIndex][PeeringDict["PeeringType"][0]] + "|"
                        PeeringParseAll[lineIndex][PeeringDict["PeeringType"][0]] = PeeringParseAll[lineIndex][PeeringDict["PeeringType"][0]] + tempPeeringParse[PeeringDict["PeeringType"][0]]

                    if tempPeeringParse[PeeringDict["PortNameRemote"][0]] not in peeringLine[PeeringDict["PortNameRemote"][0]].split("|"):
                        if PeeringParseAll[lineIndex][PeeringDict["PortNameRemote"][0]] != "":
                            PeeringParseAll[lineIndex][PeeringDict["PortNameRemote"][0]] = PeeringParseAll[lineIndex][PeeringDict["PortNameRemote"][0]] + "|"
                        PeeringParseAll[lineIndex][PeeringDict["PortNameRemote"][0]] = PeeringParseAll[lineIndex][PeeringDict["PortNameRemote"][0]] + tempPeeringParse[PeeringDict["PortNameRemote"][0]]

                    if tempPeeringParse[PeeringDict["PortDescrRemote"][0]] not in peeringLine[PeeringDict["PortDescrRemote"][0]].split("|#|"):
                        if PeeringParseAll[lineIndex][PeeringDict["PortDescrRemote"][0]] != "":
                            PeeringParseAll[lineIndex][PeeringDict["PortDescrRemote"][0]] = PeeringParseAll[lineIndex][PeeringDict["PortDescrRemote"][0]] + "|#|"
                        PeeringParseAll[lineIndex][PeeringDict["PortDescrRemote"][0]] = PeeringParseAll[lineIndex][PeeringDict["PortDescrRemote"][0]] + tempPeeringParse[PeeringDict["PortDescrRemote"][0]]

                    if tempPeeringParse[PeeringDict["HostnameRemote"][0]] not in peeringLine[PeeringDict["HostnameRemote"][0]].split("|"):
                        if PeeringParseAll[lineIndex][PeeringDict["HostnameRemote"][0]] != "":
                            PeeringParseAll[lineIndex][PeeringDict["HostnameRemote"][0]] = PeeringParseAll[lineIndex][PeeringDict["HostnameRemote"][0]] + "|"
                        PeeringParseAll[lineIndex][PeeringDict["HostnameRemote"][0]] = PeeringParseAll[lineIndex][PeeringDict["HostnameRemote"][0]] + tempPeeringParse[PeeringDict["HostnameRemote"][0]]

                    if tempPeeringParse[PeeringDict["HostnameRemote"][0]] not in peeringLine[PeeringDict["HostnameRemote"][0]].split("|"):
                        if PeeringParseAll[lineIndex][PeeringDict["HostnameRemote"][0]] != "":
                            PeeringParseAll[lineIndex][PeeringDict["HostnameRemote"][0]] = PeeringParseAll[lineIndex][PeeringDict["HostnameRemote"][0]] + "|"
                        PeeringParseAll[lineIndex][PeeringDict["HostnameRemote"][0]] = PeeringParseAll[lineIndex][PeeringDict["HostnameRemote"][0]] + tempPeeringParse[PeeringDict["HostnameRemote"][0]]

                    if tempPeeringParse[PeeringDict["SysAddrRemote"][0]] != "" and tempPeeringParse[PeeringDict["SysAddrRemote"][0]] != peeringLine[PeeringDict["SysAddrRemote"][0]]:
                        PeeringParseAll[lineIndex][PeeringDict["SysAddrRemote"][0]] = tempPeeringParse[PeeringDict["SysAddrRemote"][0]]
                        PeeringParseAll[lineIndex][PeeringDict["Comments"][0]] = "Remote system IP updated from LLDP"
                    elif tempPeeringParse[PeeringDict["SysAddrRemote"][0]] != "":
                        if "LLDP" not in PeeringParseAll[lineIndex][PeeringDict["Comments"][0]]:
                            PeeringParseAll[lineIndex][PeeringDict["Comments"][0]] = PeeringParseAll[lineIndex][PeeringDict["Comments"][0]] + "|LLDP"

                    if tempPeeringParse[PeeringDict["CLISyntaxRemote"][0]] not in peeringLine[PeeringDict["CLISyntaxRemote"][0]].split("|"):
                        if PeeringParseAll[lineIndex][PeeringDict["CLISyntaxRemote"][0]] != "":
                            PeeringParseAll[lineIndex][PeeringDict["CLISyntaxRemote"][0]] = PeeringParseAll[lineIndex][PeeringDict["CLISyntaxRemote"][0]] + "|"
                        PeeringParseAll[lineIndex][PeeringDict["CLISyntaxRemote"][0]] = PeeringParseAll[lineIndex][PeeringDict["CLISyntaxRemote"][0]] + tempPeeringParse[PeeringDict["CLISyntaxRemote"][0]]

                lineIndex = lineIndex + 1

            # Look for other interfaces that were not included in peering table earlier if there are matching ports
            for interfaceLine in InterfacesParseAll:
                match2 = 0
                # Checking if this interface is already in peering table
                for peeringLine in PeeringParseAll:
                    if peeringLine[PeeringDict["IfName"][0]] == interfaceLine[InterfacesDict["IfName"][0]]:
                        match2 = 1
                        break
                if match2 == 1:
                    continue

                if tempPeeringParse[PeeringDict["PortName"][0]] in interfaceLine[InterfacesDict["PortName"][0]].split("|"):
                    match1 = 1
                    PeeringParse = [""] * len(PeeringDict)

                    PeeringParse[PeeringDict["PeeringType"][0]] = "LLDP"
                    PeeringParse[PeeringDict["Hostname"][0]] = Hostname
                    PeeringParse[PeeringDict["SysAddr"][0]] = SysAddr
                    PeeringParse[PeeringDict["CLISyntax"][0]] = CLISyntax
                    PeeringParse[PeeringDict["IfName"][0]] = interfaceLine[InterfacesDict["IfName"][0]]
                    PeeringParse[PeeringDict["IfDescr"][0]] = interfaceLine[InterfacesDict["IfDescr"][0]]
                    PeeringParse[PeeringDict["PortBinding"][0]] = interfaceLine[InterfacesDict["PortBinding"][0]]
                    PeeringParse[PeeringDict["IPV4Addr"][0]] = interfaceLine[InterfacesDict["IPV4Addr"][0]]
                    PeeringParse[PeeringDict["IPV4Subnet"][0]] = interfaceLine[InterfacesDict["IPV4Subnet"][0]]
                    PeeringParse[PeeringDict["IPV6Addr"][0]] = interfaceLine[InterfacesDict["IPV6Addr"][0]]
                    PeeringParse[PeeringDict["IPV6Subnet"][0]] = interfaceLine[InterfacesDict["IPV6Subnet"][0]]


                    for tempPortName in interfaceLine[InterfacesDict["PortName"][0]].split("|"):
                        tempPeeringParse2 = PeeringParse.copy()

                        if tempPeeringParse[PeeringDict["PortName"][0]] == tempPortName:
                            tempPeeringParse2[PeeringDict["PortName"][0]] = tempPortName
                            tempPeeringParse2[PeeringDict["PortNameRemote"][0]] = tempPeeringParse[PeeringDict["PortNameRemote"][0]]
                            tempPeeringParse2[PeeringDict["PortDescrRemote"][0]] = tempPeeringParse[PeeringDict["PortDescrRemote"][0]]
                            tempPeeringParse2[PeeringDict["HostnameRemote"][0]] = tempPeeringParse[PeeringDict["HostnameRemote"][0]]
                            if tempPeeringParse[PeeringDict["SysAddrRemote"][0]] != "":
                                tempPeeringParse2[PeeringDict["SysAddrRemote"][0]] = tempPeeringParse[PeeringDict["SysAddrRemote"][0]]
                                tempPeeringParse2[PeeringDict["Comments"][0]] = "Remote system IP updated from LLDP"
                            tempPeeringParse2[PeeringDict["SysAddrRemote"][0]] = tempPeeringParse[PeeringDict["SysAddrRemote"][0]]
                            tempPeeringParse2[PeeringDict["CLISyntaxRemote"][0]] = tempPeeringParse[PeeringDict["CLISyntaxRemote"][0]]

                        PeeringParseAll.append(tempPeeringParse2)

            if match1 == 0:
                print("Error: LLPD peer " + tempPeeringParse[PeeringDict["PortName"][0]] + " is not found in peering and interface tables")

       ################################################### Print peering information from LLDP ###################################################

        # Write LLDP data to a file (for diagnostic purposes)
        with open(outputFilePath, 'a') as outputFile:
            if len(tempPeeringParseAll) > 0:
                outputFile.write("Found following neighbors from LLDP:\n")
                # Print header
                valueNumber = 0
                for value in printPeeringValueList:
                    if valueNumber == 0:
                        outputFile.write(str(value))
                    else:
                        outputFile.write("\t" + str(value))
                    valueNumber = valueNumber + 1
                outputFile.write("\n")
                # Print data
                for peeringLine in tempPeeringParseAll:
                    valueNumber = 0
                    for value in printPeeringValueList:
                        if valueNumber == 0:
                            outputFile.write(str(peeringLine[PeeringDict[value][0]]))
                        else:
                            outputFile.write("\t" + str(peeringLine[PeeringDict[value][0]]))
                        valueNumber = valueNumber + 1
                    outputFile.write("\n")
                outputFile.write("\n")

       ################################################### Print summary peering information from all sources to debug file ###################################################

        # Write summary neighbors data to a file
        with open("./" + outputPath + "/debugText.txt", 'a') as debugTextFile:
            if len(PeeringParseAll) > 0:
                debugTextFile.write("Summary neighbor information from all sources (after LLDP enrichment) is shown below:\n")
                # Print header
                valueNumber = 0
                for value in printPeeringValueList:
                    if valueNumber == 0:
                        debugTextFile.write(str(value))
                    else:
                        debugTextFile.write("\t" + str(value))
                    valueNumber = valueNumber + 1
                debugTextFile.write("\n")
                # Print data
                for peeringLine in PeeringParseAll:
                    valueNumber = 0
                    for value in printPeeringValueList:
                        if valueNumber == 0:
                            debugTextFile.write(str(peeringLine[PeeringDict[value][0]]))
                        else:
                            debugTextFile.write("\t" + str(peeringLine[PeeringDict[value][0]]))
                        valueNumber = valueNumber + 1
                    debugTextFile.write("\n")
                debugTextFile.write("\n")


        ################################################### OSPFv2 output ###################################################

        # PeeringParseAll.clear()
        tempPeeringParseAll = []

        OSPFv2NeighborsText = "\n".join(OSPFv2NeighborsLines)
        OSPFv2NeighborsText = OSPFv2NeighborsText + "\n"

        # Syntax: Cisco IOS-XR
        if (CLISyntax == "IOS-XR"):
            # Look for OSPFv2 entries to find neighbor information
            neighborDelimiter = r"\r*\n\r*\n Neighbor "
            for neighborText in re.split(neighborDelimiter,OSPFv2NeighborsText):
                # Skip text if it has no neighbor specified
                if not re.search(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}",neighborText):
                    continue

                tempPeeringParse = [""] * len(PeeringDict)
                tempPeeringParse[PeeringDict["PeeringType"][0]] = "OSPFv2"

                # Collecting data for current neighbor
                for line in re.split(r"\r*\n",neighborText):

                    # Get local interface name in OSPFv2 output
                    if re.search(r"via interface ",line):
                        tempPeeringParse[PeeringDict["IfName"][0]] = line.split("via interface ")[1].split(" ")[0].lstrip().rstrip()
                        continue

                    # Get remote IPv4 address OSPFv2 output
                    if re.search(r"interface address",line):
                        tempPeeringParse[PeeringDict["IPV4AddrRemote"][0]] = line.split("interface address ")[1].split(" ")[0].lstrip().rstrip()
                    # Get remote system address OSPFv2 output
                        tempPeeringParse[PeeringDict["SysAddrRemote"][0]] = line.split(",")[0].lstrip().rstrip()
                        continue

                match = 0
                for line in tempPeeringParseAll:
                    if tempPeeringParse[PeeringDict["IPV4AddrRemote"][0]] == line[PeeringDict["IPV4AddrRemote"][0]]:
                        match = 1
                if match == 0:
                    # print(tempPeeringParse)
                    tempPeeringParseAll.append(tempPeeringParse)


        # Syntax: Cisco IOS/IOS-XE
        if (CLISyntax == "IOS"):
            # Look for OSPFv2 entries to find neighbor information
            neighborDelimiter = r"\r*\n Neighbor "
            for neighborText in re.split(neighborDelimiter,OSPFv2NeighborsText):
                # Skip text if it has no neighbor specified
                if not re.search(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}",neighborText):
                    continue

                tempPeeringParse = [""] * len(PeeringDict)
                tempPeeringParse[PeeringDict["PeeringType"][0]] = "OSPFv2"

                # Collecting data for current neighbor
                for line in re.split(r"\r*\n",neighborText):

                    # Get local interface name in OSPFv2 output
                    if re.search(r"via interface ",line):
                        tempPeeringParse[PeeringDict["IfName"][0]] = line.split("via interface ")[1].split(" ")[0].lstrip().rstrip()
                        continue

                    # Get remote IPv4 address OSPFv2 output
                    if re.search(r"interface address",line):
                        tempPeeringParse[PeeringDict["IPV4AddrRemote"][0]] = line.split("interface address ")[1].split(",")[0].lstrip().rstrip()
                    # Get remote system address OSPFv2 output
                        tempPeeringParse[PeeringDict["SysAddrRemote"][0]] = line.split(",")[0].lstrip().rstrip()
                        continue

                match = 0
                for line in tempPeeringParseAll:
                    if tempPeeringParse[PeeringDict["IPV4AddrRemote"][0]] == line[PeeringDict["IPV4AddrRemote"][0]]:
                        match = 1
                if match == 0:
                    # print(tempPeeringParse)
                    tempPeeringParseAll.append(tempPeeringParse)

        # Syntax: Huawei VRP
        if (CLISyntax == "VRP"):
            # Look for OSPFv2 entries to find neighbor information
            interfaceDelimiter = r"Area .* interface "
            for interfaceText in re.split(interfaceDelimiter,OSPFv2NeighborsText):

                tempIfName = ""
                tempIPV4Addr = ""
                for line in interfaceText.split("\n"):
                    if re.search(r".*'s neighbors",line):
                        # Get local interface name in OSPFv2 output
                        tempIfName = line.split("(")[1].split(")")[0]
                        # Get local IPv4 address OSPFv2 output
                        tempIPV4Addr = line.split("(")[0]
                        break

                if tempIfName != "":
                    neighborDelimiter = r"Router ID: "
                    for neighborText in re.split(neighborDelimiter,interfaceText):
                        # Skip text if it has no neighbor specified
                        if not re.search(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3} *Address:",neighborText):
                            continue

                        tempPeeringParse = [""] * len(PeeringDict)
                        tempPeeringParse[PeeringDict["PeeringType"][0]] = "OSPFv2"
                        tempPeeringParse[PeeringDict["IfName"][0]] = tempIfName

                        # Collecting data for current neighbor
                        for line in re.split(r"\r*\n",neighborText):
                            # Get remote system address OSPFv2 output
                            if re.search(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3} *Address:",line):
                                tempPeeringParse[PeeringDict["SysAddrRemote"][0]] = line.split(" ")[0].lstrip().rstrip()
                                # Get remote IPv4 address OSPFv2 output
                                tempPeeringParse[PeeringDict["IPV4AddrRemote"][0]] = line.split("Address: ")[1].split(" ")[0].lstrip().rstrip()
                                continue

                        match = 0
                        for line in tempPeeringParseAll:
                            if tempPeeringParse[PeeringDict["IPV4AddrRemote"][0]] == line[PeeringDict["IPV4AddrRemote"][0]]:
                                match = 1
                        if match == 0:
                            # print(tempPeeringParse)
                            tempPeeringParseAll.append(tempPeeringParse)

        # Syntax: ALU/Nokia SR-OS
        if (CLISyntax == "SR-OS"):
            # Look for OSPFv2 entries to find neighbor information
            neighborDelimiter = r"Neighbor Rtr Id : "
            for neighborText in re.split(neighborDelimiter,OSPFv2NeighborsText):
                # Skip text if it has no neighbor specified
                if not re.search(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}",neighborText):
                    continue

                tempPeeringParse = [""] * len(PeeringDict)
                tempPeeringParse[PeeringDict["PeeringType"][0]] = "OSPFv2"

                # Collecting data for current neighbor
                for line in re.split(r"\r*\n",neighborText):

                    # Get local interface name in OSPFv2 output
                    if re.search(r"  Interface: ",line):
                        tempPeeringParse[PeeringDict["IfName"][0]] = line.split("  Interface: ")[1].split(" ")[0].lstrip().rstrip()
                        # Get remote system address OSPFv2 output
                        tempPeeringParse[PeeringDict["SysAddrRemote"][0]] = line.split("  Interface: ")[0].lstrip().rstrip()
                        continue

                    # Get local IPv4 address OSPFv2 output
                    if re.search(r"Local IF IP Addr *:",line):
                        tempPeeringParse[PeeringDict["IPV4Addr"][0]] = line.split(": ")[1].split(" ")[0].lstrip().rstrip()
                        continue
                    # Get remote IPv4 address OSPFv2 output
                    if re.search(r"Neighbor IP Addr *:",line):
                        tempPeeringParse[PeeringDict["IPV4AddrRemote"][0]] = line.split(": ")[1].split(" ")[0].lstrip().rstrip()
                        continue

                match = 0
                for line in tempPeeringParseAll:
                    if tempPeeringParse[PeeringDict["IPV4AddrRemote"][0]] == line[PeeringDict["IPV4AddrRemote"][0]]:
                        match = 1
                if match == 0:
                    # print(tempPeeringParse)
                    tempPeeringParseAll.append(tempPeeringParse)

        # if debug:
        #     # Write summary neighbors data to a file for debug purposes
        #     with open(outputFilePath, 'a') as outputFile:
        #         if len(PeeringParseAll) > 0:
        #             outputFile.write("DEBUG: Summary neighbor information from all sources is shown below:\n\n")
        #             outputFile.write("\t".join(str(item) for item in PeeringDict))
        #             outputFile.write("\n")
        #             for peeringLine in PeeringParseAll:
        #                 outputFile.write("\t".join(str(item) for item in peeringLine))
        #                 outputFile.write("\n")
        #         outputFile.write("\n")

        # Enrich peering table with parsed data from OSPFv2
        for tempPeeringParse in tempPeeringParseAll:
            # Updating data for existing neighbors
            lineIndex = 0
            match1 = 0
            for peeringLine in PeeringParseAll:

                # Getting adresses for local subnet
                tempIPV4SubnetList = []
                if str(peeringLine[PeeringDict["IPV4Subnet"][0]]) != "":
                    for prefix in peeringLine[PeeringDict["IPV4Subnet"][0]].split("|"):
                        tempIPV4Subnet = ipaddress.ip_interface(str(prefix))
                        for address in tempIPV4Subnet.network.hosts():
                            tempIPV4SubnetList.append(str(address))

                # Check if remote addresses match
                # if (( tempPeeringParse[PeeringDict["IPV4AddrRemote"][0]] == peeringLine[PeeringDict["IPV4AddrRemote"][0]].split("/")[0] ) or ( tempPeeringParse[PeeringDict["SysAddrRemote"][0]] == peeringLine[PeeringDict["SysAddrRemote"][0]] )):
                if (( tempPeeringParse[PeeringDict["IPV4AddrRemote"][0]] == peeringLine[PeeringDict["IPV4AddrRemote"][0]].split("/")[0] )):
                    match1 = 1
                    if tempPeeringParse[PeeringDict["PeeringType"][0]] not in peeringLine[PeeringDict["PeeringType"][0]].split("|"):
                        if PeeringParseAll[lineIndex][PeeringDict["PeeringType"][0]] != "":
                            PeeringParseAll[lineIndex][PeeringDict["PeeringType"][0]] = PeeringParseAll[lineIndex][PeeringDict["PeeringType"][0]] + "|"
                        PeeringParseAll[lineIndex][PeeringDict["PeeringType"][0]] = PeeringParseAll[lineIndex][PeeringDict["PeeringType"][0]] + tempPeeringParse[PeeringDict["PeeringType"][0]]

                        if tempPeeringParse[PeeringDict["SysAddrRemote"][0]] != "" and tempPeeringParse[PeeringDict["SysAddrRemote"][0]] != peeringLine[PeeringDict["SysAddrRemote"][0]]:
                            PeeringParseAll[lineIndex][PeeringDict["SysAddrRemote"][0]] = tempPeeringParse[PeeringDict["SysAddrRemote"][0]]
                            PeeringParseAll[lineIndex][PeeringDict["Comments"][0]] = "Remote system IP updated from OSPF"
                        elif tempPeeringParse[PeeringDict["SysAddrRemote"][0]] != "":
                            if "OSPF" not in PeeringParseAll[lineIndex][PeeringDict["Comments"][0]]:
                                PeeringParseAll[lineIndex][PeeringDict["Comments"][0]] = PeeringParseAll[lineIndex][PeeringDict["Comments"][0]] + "|OSPF"
                else:
                    # Check if local interfaces match or remote address belongs to local interface's subnet
                    if (( tempPeeringParse[PeeringDict["IPV4AddrRemote"][0]] in tempIPV4SubnetList ) and ( tempPeeringParse[PeeringDict["IfName"][0]] == peeringLine[PeeringDict["IfName"][0]] )):
                        match1 = 1
                        # Check if peer address is empty
                        if peeringLine[PeeringDict["IPV4AddrRemote"][0]] == "":
                            peeringLine[PeeringDict["IPV4AddrRemote"][0]] = tempPeeringParse[PeeringDict["IPV4AddrRemote"][0]]
                            if tempPeeringParse[PeeringDict["PeeringType"][0]] not in peeringLine[PeeringDict["PeeringType"][0]].split("|"):
                                if PeeringParseAll[lineIndex][PeeringDict["PeeringType"][0]] != "":
                                    PeeringParseAll[lineIndex][PeeringDict["PeeringType"][0]] = PeeringParseAll[lineIndex][PeeringDict["PeeringType"][0]] + "|"
                                PeeringParseAll[lineIndex][PeeringDict["PeeringType"][0]] = PeeringParseAll[lineIndex][PeeringDict["PeeringType"][0]] + tempPeeringParse[PeeringDict["PeeringType"][0]]

                            if tempPeeringParse[PeeringDict["SysAddrRemote"][0]] != "" and tempPeeringParse[PeeringDict["SysAddrRemote"][0]] != peeringLine[PeeringDict["SysAddrRemote"][0]]:
                                PeeringParseAll[lineIndex][PeeringDict["SysAddrRemote"][0]] = tempPeeringParse[PeeringDict["SysAddrRemote"][0]]
                                PeeringParseAll[lineIndex][PeeringDict["Comments"][0]] = "Remote system IP updated from OSPF"
                            elif tempPeeringParse[PeeringDict["SysAddrRemote"][0]] != "":
                                if "OSPF" not in PeeringParseAll[lineIndex][PeeringDict["Comments"][0]]:
                                    PeeringParseAll[lineIndex][PeeringDict["Comments"][0]] = PeeringParseAll[lineIndex][PeeringDict["Comments"][0]] + "|OSPF"
                        else:
                            # Create duplicate line with another peer address
                            tempPeeringLine = peeringLine.copy()
                            tempPeeringLine[PeeringDict["IPV4AddrRemote"][0]] = tempPeeringParse[PeeringDict["IPV4AddrRemote"][0]]
                            if tempPeeringParse[PeeringDict["PeeringType"][0]] not in tempPeeringLine[PeeringDict["PeeringType"][0]].split("|"):
                                if tempPeeringLine[PeeringDict["PeeringType"][0]] != "":
                                    tempPeeringLine[PeeringDict["PeeringType"][0]] = tempPeeringLine[PeeringDict["PeeringType"][0]] + "|"
                                tempPeeringLine[PeeringDict["PeeringType"][0]] = tempPeeringLine[PeeringDict["PeeringType"][0]] + tempPeeringParse[PeeringDict["PeeringType"][0]]

                            if tempPeeringParse[PeeringDict["SysAddrRemote"][0]] != "" and tempPeeringParse[PeeringDict["SysAddrRemote"][0]] != peeringLine[PeeringDict["SysAddrRemote"][0]]:
                                tempPeeringLine[lineIndex][PeeringDict["SysAddrRemote"][0]] = tempPeeringParse[PeeringDict["SysAddrRemote"][0]]
                                tempPeeringLine[lineIndex][PeeringDict["Comments"][0]] = "Remote system IP updated from OSPF"
                            elif tempPeeringParse[PeeringDict["SysAddrRemote"][0]] != "":
                                if "OSPF" not in tempPeeringLine[lineIndex][PeeringDict["Comments"][0]]:
                                    tempPeeringLine[lineIndex][PeeringDict["Comments"][0]] = PeeringParseAll[lineIndex][PeeringDict["Comments"][0]] + "|OSPF"

                            PeeringParseAll.insert(lineIndex,tempPeeringLine)

                lineIndex = lineIndex + 1

            if match1 == 0:
                # Look for other interfaces that were not included in peering table earlier if there are matching ports
                for interfaceLine in InterfacesParseAll:

                    # Getting adresses for local subnet
                    tempIPV4SubnetList = []
                    if str(interfaceLine[InterfacesDict["IPV4Subnet"][0]]) != "":
                        for prefix in interfaceLine[InterfacesDict["IPV4Subnet"][0]].split("|"):
                            tempIPV4Subnet = ipaddress.ip_interface(str(prefix))
                            for address in tempIPV4Subnet.network.hosts():
                                tempIPV4SubnetList.append(str(address))

                    # if tempPeeringParse[PeeringDict["PortName"][0]] in interfaceLine[InterfacesDict["PortName"][0]].split("|"):
                    if tempPeeringParse[PeeringDict["IPV4AddrRemote"][0]] in tempIPV4SubnetList:

                        match1 = 1
                        PeeringParse = [""] * len(PeeringDict)

                        PeeringParse[PeeringDict["PeeringType"][0]] = "OSPFv2"
                        PeeringParse[PeeringDict["Hostname"][0]] = Hostname
                        PeeringParse[PeeringDict["SysAddr"][0]] = SysAddr
                        PeeringParse[PeeringDict["CLISyntax"][0]] = CLISyntax
                        PeeringParse[PeeringDict["IfName"][0]] = interfaceLine[InterfacesDict["IfName"][0]]
                        PeeringParse[PeeringDict["IfDescr"][0]] = interfaceLine[InterfacesDict["IfDescr"][0]]
                        PeeringParse[PeeringDict["PortBinding"][0]] = interfaceLine[InterfacesDict["PortBinding"][0]]
                        PeeringParse[PeeringDict["IPV4Addr"][0]] = interfaceLine[InterfacesDict["IPV4Addr"][0]]
                        PeeringParse[PeeringDict["IPV4Subnet"][0]] = interfaceLine[InterfacesDict["IPV4Subnet"][0]]
                        PeeringParse[PeeringDict["IPV6Addr"][0]] = interfaceLine[InterfacesDict["IPV6Addr"][0]]
                        PeeringParse[PeeringDict["IPV6Subnet"][0]] = interfaceLine[InterfacesDict["IPV6Subnet"][0]]
                        if tempPeeringParse[PeeringDict["SysAddrRemote"][0]] != "":
                            PeeringParse[PeeringDict["SysAddrRemote"][0]] = tempPeeringParse[PeeringDict["SysAddrRemote"][0]]
                            PeeringParse[PeeringDict["Comments"][0]] = "Remote system IP updated from OSPF"
                        PeeringParse[PeeringDict["IPV4AddrRemote"][0]] = tempPeeringParse[PeeringDict["IPV4AddrRemote"][0]]
                        PeeringParse[PeeringDict["IPV4SubnetRemote"][0]] = interfaceLine[InterfacesDict["IPV4Subnet"][0]]


                        for tempPortName in interfaceLine[InterfacesDict["PortName"][0]].split("|"):
                            tempPeeringParse2 = PeeringParse.copy()

                            tempPeeringParse2[PeeringDict["PortName"][0]] = tempPortName
                            PeeringParseAll.append(tempPeeringParse2)

            if match1 == 0:
                print("Error: OSPFv2 peer " + tempPeeringParse[PeeringDict["IPV4AddrRemote"][0]] + " is not found in peering and interface tables")


       ################################################### Print peering information from OSPF ###################################################

        # Write OSPFv2 data to a file (for diagnostic purposes)
        with open(outputFilePath, 'a') as outputFile:
            if len(tempPeeringParseAll) > 0:
                outputFile.write("Found following neighbors from OSPFv2:\n")
                # Print header
                valueNumber = 0
                for value in printPeeringValueList:
                    if valueNumber == 0:
                        outputFile.write(str(value))
                    else:
                        outputFile.write("\t" + str(value))
                    valueNumber = valueNumber + 1
                outputFile.write("\n")
                # Print data
                for peeringLine in tempPeeringParseAll:
                    valueNumber = 0
                    for value in printPeeringValueList:
                        if valueNumber == 0:
                            outputFile.write(str(peeringLine[PeeringDict[value][0]]))
                        else:
                            outputFile.write("\t" + str(peeringLine[PeeringDict[value][0]]))
                        valueNumber = valueNumber + 1
                    outputFile.write("\n")
                outputFile.write("\n")

       ################################################### Print summary peering information from all sources to debug file ###################################################

        # Write summary neighbors data to a file
        with open("./" + outputPath + "/debugText.txt", 'a') as debugTextFile:
            if len(PeeringParseAll) > 0:
                debugTextFile.write("Summary neighbor information from all sources (after OSPF enrichment) is shown below:\n")
                # Print header
                valueNumber = 0
                for value in printPeeringValueList:
                    if valueNumber == 0:
                        debugTextFile.write(str(value))
                    else:
                        debugTextFile.write("\t" + str(value))
                    valueNumber = valueNumber + 1
                debugTextFile.write("\n")
                # Print data
                for peeringLine in PeeringParseAll:
                    valueNumber = 0
                    for value in printPeeringValueList:
                        if valueNumber == 0:
                            debugTextFile.write(str(peeringLine[PeeringDict[value][0]]))
                        else:
                            debugTextFile.write("\t" + str(peeringLine[PeeringDict[value][0]]))
                        valueNumber = valueNumber + 1
                    debugTextFile.write("\n")
                debugTextFile.write("\n")


        ################################################### BGP output ###################################################

        # PeeringParseAll.clear()
        tempPeeringParseAll = []

        BGPNeighborsText = "\n".join(BGPNeighborsLines)
        BGPNeighborsText = BGPNeighborsText + "\n"

        # Syntax: Cisco IOS-XR
        if (CLISyntax == "IOS-XR"):
            # Look for BGP entries to find neighbor information
            neighborDelimiter = r"\r*\n\r*\nBGP neighbor is "
            for neighborText in re.split(neighborDelimiter,BGPNeighborsText):
                # Skip text if it has no neighbor specified
                if not re.search(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}",neighborText):
                    continue

                tempPeeringParse = [""] * len(PeeringDict)

                tempPeeringParse[PeeringDict["IPV4AddrRemote"][0]] = re.split(r"\r*\n",neighborText)[0]

                # Collecting data for current neighbor
                for line in re.split(r"\r*\n",neighborText):

                    if re.search(r"Remote AS ",line):
                        tempPeeringParse[PeeringDict["ASRemote"][0]] = line.split("Remote AS ")[1].split(",")[0].lstrip().rstrip()
                        tempPeeringParse[PeeringDict["LocalAS"][0]] = line.split("local AS ")[1].split(",")[0].lstrip().rstrip()
                        if len(line.split(", ")) >= 3:
                            if line.split(", ")[2].split(" link")[0].lstrip().rstrip() == "external":
                                tempPeeringParse[PeeringDict["PeeringType"][0]] = "eBGP"
                            elif line.split(", ")[2].split(" link")[0].lstrip().rstrip() == "internal":
                                tempPeeringParse[PeeringDict["PeeringType"][0]] = "iBGP"
                        continue

                    if re.search(r"Description: ",line):
                        tempPeeringParse[PeeringDict["PeerDescr"][0]] = line.split(": ")[1].replace("\"","")
                        continue

                    if re.search(r"Remote router ID ",line):
                        tempPeeringParse[PeeringDict["SysAddrRemote"][0]] = line.split("Remote router ID ")[1].split()[0].lstrip().rstrip()
                        continue

                match = 0
                for line in tempPeeringParseAll:
                    if tempPeeringParse[PeeringDict["IPV4AddrRemote"][0]] == line[PeeringDict["IPV4AddrRemote"][0]]:
                        match = 1
                if match == 0:
                    # print(tempPeeringParse)
                    tempPeeringParseAll.append(tempPeeringParse)

        # Syntax: Cisco IOS
        if (CLISyntax == "IOS"):
            # Look for BGP entries to find neighbor information
            neighborDelimiter = r"\r*\nBGP neighbor is "
            for neighborText in re.split(neighborDelimiter,BGPNeighborsText):
                # Skip text if it has no neighbor specified
                if not re.search(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}",neighborText):
                    continue

                tempPeeringParse = [""] * len(PeeringDict)

                # Collecting data for current neighbor
                for line in re.split(r"\r*\n",neighborText):

                    if re.search(r"remote AS ",line):
                        tempPeeringParse[PeeringDict["IPV4AddrRemote"][0]] = line.split(",")[0].lstrip().rstrip()
                        tempPeeringParse[PeeringDict["ASRemote"][0]] = line.split("remote AS ")[1].split(",")[0].lstrip().rstrip()
                        if len(line.split(", ")) >= 3:
                            if line.split(", ")[2].split(" link")[0].lstrip().rstrip() == "external":
                                tempPeeringParse[PeeringDict["PeeringType"][0]] = "eBGP"
                            elif line.split(", ")[2].split(" link")[0].lstrip().rstrip() == "internal":
                                tempPeeringParse[PeeringDict["PeeringType"][0]] = "iBGP"
                        continue

                    if re.search(r"remote router ID ",line):
                        tempPeeringParse[PeeringDict["SysAddrRemote"][0]] = line.split("remote router ID ")[1].split()[0].lstrip().rstrip()
                        continue

                match = 0
                for line in tempPeeringParseAll:
                    if tempPeeringParse[PeeringDict["IPV4AddrRemote"][0]] == line[PeeringDict["IPV4AddrRemote"][0]]:
                        match = 1
                if match == 0:
                    # print(tempPeeringParse)
                    tempPeeringParseAll.append(tempPeeringParse)


        # Syntax: Huawei VRP
        if (CLISyntax == "VRP"):
            # TBD
            pass

        # Syntax: ALU/Nokia SR-OS
        if (CLISyntax == "SR-OS"):
            # Look for BGP entries to find neighbor information
            neighborDelimiter = r"---+\r*\nPeer *: "
            for neighborText in re.split(neighborDelimiter,BGPNeighborsText):
                # Skip text if it has no neighbor specified
                if not re.search(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}",neighborText):
                    continue

                tempPeeringParse = [""] * len(PeeringDict)

                tempPeeringParse[PeeringDict["IPV4AddrRemote"][0]] = re.split(r"\r*\n",neighborText)[0]

                # Collecting data for current neighbor
                for line in re.split(r"\r*\n",neighborText):

                    if re.search(r"Description *: ",line):
                        tempPeeringParse[PeeringDict["PeerDescr"][0]] = line.split(": ")[1]
                        continue
                    if re.search(r"Peer AS *: ",line):
                        tempPeeringParse[PeeringDict["ASRemote"][0]] = line.split(": ")[1].split()[0]
                        continue
                    if re.search(r"Local AS *: ",line):
                        tempPeeringParse[PeeringDict["LocalAS"][0]] = line.split(": ")[1].split()[0]
                        continue
                    if re.search(r"Peer Address *: ",line):
                        tempPeeringParse[PeeringDict["SysAddrRemote"][0]] = line.split(": ")[1].split()[0]
                        continue
                    if re.search(r"Local Address *: ",line):
                        tempPeeringParse[PeeringDict["IPV4Addr"][0]] = line.split(": ")[1].split()[0]
                        continue
                    if re.search(r"Peer Type *: ",line):
                        if line.split(": ")[2].split()[0].lstrip().rstrip() == "External":
                            tempPeeringParse[PeeringDict["PeeringType"][0]] = "eBGP"
                        elif line.split(": ")[2].split()[0].lstrip().rstrip() == "Internal":
                            tempPeeringParse[PeeringDict["PeeringType"][0]] = "iBGP"
                        continue

                match = 0
                for line in tempPeeringParseAll:
                    if tempPeeringParse[PeeringDict["IPV4AddrRemote"][0]] == line[PeeringDict["IPV4AddrRemote"][0]]:
                        match = 1
                if match == 0:
                    # print(tempPeeringParse)
                    tempPeeringParseAll.append(tempPeeringParse)


        # if debug:
        #     # Write summary neighbors data to a file for debug purposes
        #     with open(outputFilePath, 'a') as outputFile:
        #         if len(PeeringParseAll) > 0:
        #             outputFile.write("DEBUG: Summary neighbor information from all sources is shown below:\n\n")
        #             outputFile.write("\t".join(str(item) for item in PeeringDict))
        #             outputFile.write("\n")
        #             for peeringLine in PeeringParseAll:
        #                 outputFile.write("\t".join(str(item) for item in peeringLine))
        #                 outputFile.write("\n")
        #         outputFile.write("\n")


        # # Write BGP data to a file (for diagnostic purposes)
        # with open(outputFilePath, 'a') as outputFile:
        #     if len(tempPeeringParseAll) > 0:
        #         outputFile.write("Found following neighbors from BGP:\n\n")
        #         outputFile.write("\t".join(str(item) for item in PeeringDict))
        #         outputFile.write("\n")
        #         for peeringLine in tempPeeringParseAll:
        #             outputFile.write("\t".join(str(item) for item in peeringLine))
        #             outputFile.write("\n")
        #     outputFile.write("\n")

        # Enrich BGP peering table with parsed data from BGP neighbors
        for tempPeeringParse in tempPeeringParseAll:
            # Updating data for existing neighbors
            lineIndex = 0
            for peeringLine in BGPPeeringParseAll:

                # Check if remote addresses match
                if (( tempPeeringParse[PeeringDict["IPV4AddrRemote"][0]] == peeringLine[PeeringDict["IPV4AddrRemote"][0]].split("/")[0] )):
                    if ( tempPeeringParse[PeeringDict["PeeringType"][0]] != "" ) and ( tempPeeringParse[PeeringDict["PeeringType"][0]] != peeringLine[PeeringDict["PeeringType"][0]] ):
                        BGPPeeringParseAll[lineIndex][PeeringDict["PeeringType"][0]] = tempPeeringParse[PeeringDict["PeeringType"][0]]
                    if ( tempPeeringParse[PeeringDict["PeerDescr"][0]] != "" ) and ( tempPeeringParse[PeeringDict["PeerDescr"][0]] != peeringLine[PeeringDict["PeerDescr"][0]] ):
                        BGPPeeringParseAll[lineIndex][PeeringDict["PeerDescr"][0]] = tempPeeringParse[PeeringDict["PeerDescr"][0]]
                    if ( tempPeeringParse[PeeringDict["LocalAS"][0]] != "" ) and ( tempPeeringParse[PeeringDict["LocalAS"][0]] != peeringLine[PeeringDict["LocalAS"][0]] ):
                        BGPPeeringParseAll[lineIndex][PeeringDict["LocalAS"][0]] = tempPeeringParse[PeeringDict["LocalAS"][0]]
                    if ( tempPeeringParse[PeeringDict["ASRemote"][0]] != "" ) and ( tempPeeringParse[PeeringDict["ASRemote"][0]] != peeringLine[PeeringDict["ASRemote"][0]] ):
                        BGPPeeringParseAll[lineIndex][PeeringDict["ASRemote"][0]] = tempPeeringParse[PeeringDict["ASRemote"][0]]
                    if ( tempPeeringParse[PeeringDict["SysAddrRemote"][0]] != "" ) and ( tempPeeringParse[PeeringDict["SysAddrRemote"][0]] != peeringLine[PeeringDict["SysAddrRemote"][0]] ):
                        BGPPeeringParseAll[lineIndex][PeeringDict["SysAddrRemote"][0]] = tempPeeringParse[PeeringDict["SysAddrRemote"][0]]
                    if ( tempPeeringParse[PeeringDict["IPV4Addr"][0]] != "" ) and ( tempPeeringParse[PeeringDict["IPV4Addr"][0]] != peeringLine[PeeringDict["IPV4Addr"][0]] ):
                        BGPPeeringParseAll[lineIndex][PeeringDict["IPV4Addr"][0]] = tempPeeringParse[PeeringDict["IPV4Addr"][0]]

                lineIndex = lineIndex + 1

       ################################################### Print peering information from BGP ###################################################

        # Write BGP subnet data to a file (for diagnostic purposes)
        with open(outputFilePath, 'a') as outputFile:
            if len(BGPPeeringParseAll) > 0:
                outputFile.write("Found following neighbors from BGP:\n")
                # Print header
                valueNumber = 0
                for value in printPeeringValueList:
                    if valueNumber == 0:
                        outputFile.write(str(value))
                    else:
                        outputFile.write("\t" + str(value))
                    valueNumber = valueNumber + 1
                outputFile.write("\n")
                # Print data
                for peeringLine in BGPPeeringParseAll:
                    valueNumber = 0
                    for value in printPeeringValueList:
                        if valueNumber == 0:
                            outputFile.write(str(peeringLine[PeeringDict[value][0]]))
                        else:
                            outputFile.write("\t" + str(peeringLine[PeeringDict[value][0]]))
                        valueNumber = valueNumber + 1
                    outputFile.write("\n")
                outputFile.write("\n")

        # # Write BGP data to a file (for diagnostic purposes)
        # with open(outputFilePath, 'a') as outputFile:
        #     if len(BGPPeeringParseAll) > 0:
        #         outputFile.write("Found following neighbors from BGP:\n\n")
        #         outputFile.write("\t".join(str(item) for item in PeeringDict))
        #         outputFile.write("\n")
        #         for peeringLine in BGPPeeringParseAll:
        #             outputFile.write("\t".join(str(item) for item in peeringLine))
        #             outputFile.write("\n")
        #     outputFile.write("\n")


        # Enrich peering table with parsed data from BGP
        for tempPeeringParse in BGPPeeringParseAll:
            # Updating data for existing neighbors
            lineIndex = 0
            match1 = 0
            for peeringLine in PeeringParseAll:

                # Getting adresses for local subnet
                tempIPV4SubnetList = []
                if str(peeringLine[PeeringDict["IPV4Subnet"][0]]) != "":
                    for prefix in peeringLine[PeeringDict["IPV4Subnet"][0]].split("|"):
                        tempIPV4Subnet = ipaddress.ip_interface(str(prefix))
                        for address in tempIPV4Subnet.network.hosts():
                            tempIPV4SubnetList.append(str(address))

                # Check if remote addresses match
                if ( tempPeeringParse[PeeringDict["IPV4AddrRemote"][0]] == peeringLine[PeeringDict["IPV4AddrRemote"][0]].split("/")[0] ):
                    match1 = 1
                    if tempPeeringParse[PeeringDict["PeeringType"][0]] not in peeringLine[PeeringDict["PeeringType"][0]].split("|"):
                        if PeeringParseAll[lineIndex][PeeringDict["PeeringType"][0]] != "":
                            PeeringParseAll[lineIndex][PeeringDict["PeeringType"][0]] = PeeringParseAll[lineIndex][PeeringDict["PeeringType"][0]] + "|"
                        PeeringParseAll[lineIndex][PeeringDict["PeeringType"][0]] = PeeringParseAll[lineIndex][PeeringDict["PeeringType"][0]] + tempPeeringParse[PeeringDict["PeeringType"][0]]

                    if tempPeeringParse[PeeringDict["LocalAS"][0]] not in peeringLine[PeeringDict["LocalAS"][0]].split("|"):
                        if PeeringParseAll[lineIndex][PeeringDict["LocalAS"][0]] != "":
                            PeeringParseAll[lineIndex][PeeringDict["LocalAS"][0]] = PeeringParseAll[lineIndex][PeeringDict["LocalAS"][0]] + "|"
                        PeeringParseAll[lineIndex][PeeringDict["LocalAS"][0]] = PeeringParseAll[lineIndex][PeeringDict["LocalAS"][0]] + tempPeeringParse[PeeringDict["LocalAS"][0]]

                    if tempPeeringParse[PeeringDict["PeerDescr"][0]] not in peeringLine[PeeringDict["PeerDescr"][0]].split("|"):
                        if PeeringParseAll[lineIndex][PeeringDict["PeerDescr"][0]] != "":
                            PeeringParseAll[lineIndex][PeeringDict["PeerDescr"][0]] = PeeringParseAll[lineIndex][PeeringDict["PeerDescr"][0]] + "|"
                        PeeringParseAll[lineIndex][PeeringDict["PeerDescr"][0]] = PeeringParseAll[lineIndex][PeeringDict["PeerDescr"][0]] + tempPeeringParse[PeeringDict["PeerDescr"][0]]

                    if tempPeeringParse[PeeringDict["ASRemote"][0]] not in peeringLine[PeeringDict["ASRemote"][0]].split("|"):
                        if PeeringParseAll[lineIndex][PeeringDict["ASRemote"][0]] != "":
                            PeeringParseAll[lineIndex][PeeringDict["ASRemote"][0]] = PeeringParseAll[lineIndex][PeeringDict["LocalAS"][0]] + "|"
                        PeeringParseAll[lineIndex][PeeringDict["ASRemote"][0]] = PeeringParseAll[lineIndex][PeeringDict["ASRemote"][0]] + tempPeeringParse[PeeringDict["ASRemote"][0]]

                    if tempPeeringParse[PeeringDict["SysAddrRemote"][0]] != "" and tempPeeringParse[PeeringDict["SysAddrRemote"][0]] != peeringLine[PeeringDict["SysAddrRemote"][0]]:
                        PeeringParseAll[lineIndex][PeeringDict["SysAddrRemote"][0]] = tempPeeringParse[PeeringDict["SysAddrRemote"][0]]
                        PeeringParseAll[lineIndex][PeeringDict["Comments"][0]] = "Remote system IP updated from BGP"
                    elif tempPeeringParse[PeeringDict["SysAddrRemote"][0]] != "":
                        if "BGP" not in PeeringParseAll[lineIndex][PeeringDict["Comments"][0]]:
                            PeeringParseAll[lineIndex][PeeringDict["Comments"][0]] = PeeringParseAll[lineIndex][PeeringDict["Comments"][0]] + "|BGP"
                else:
                    # Check if remote address belongs to local interface's subnet
                    if (( tempPeeringParse[PeeringDict["IPV4AddrRemote"][0]] in tempIPV4SubnetList )):
                        match1 = 1
                        # Check if peer address is empty
                        if peeringLine[PeeringDict["IPV4AddrRemote"][0]] == "":
                            peeringLine[PeeringDict["IPV4AddrRemote"][0]] = tempPeeringParse[PeeringDict["IPV4AddrRemote"][0]]
                            if tempPeeringParse[PeeringDict["PeeringType"][0]] not in peeringLine[PeeringDict["PeeringType"][0]].split("|"):
                                if PeeringParseAll[lineIndex][PeeringDict["PeeringType"][0]] != "":
                                    PeeringParseAll[lineIndex][PeeringDict["PeeringType"][0]] = PeeringParseAll[lineIndex][PeeringDict["PeeringType"][0]] + "|"
                                PeeringParseAll[lineIndex][PeeringDict["PeeringType"][0]] = PeeringParseAll[lineIndex][PeeringDict["PeeringType"][0]] + tempPeeringParse[PeeringDict["PeeringType"][0]]

                            if tempPeeringParse[PeeringDict["LocalAS"][0]] not in peeringLine[PeeringDict["LocalAS"][0]].split("|"):
                                if PeeringParseAll[lineIndex][PeeringDict["LocalAS"][0]] != "":
                                    PeeringParseAll[lineIndex][PeeringDict["LocalAS"][0]] = PeeringParseAll[lineIndex][PeeringDict["LocalAS"][0]] + "|"
                                PeeringParseAll[lineIndex][PeeringDict["LocalAS"][0]] = PeeringParseAll[lineIndex][PeeringDict["LocalAS"][0]] + tempPeeringParse[PeeringDict["LocalAS"][0]]

                            if tempPeeringParse[PeeringDict["PeerDescr"][0]] not in peeringLine[PeeringDict["PeerDescr"][0]].split("|"):
                                if PeeringParseAll[lineIndex][PeeringDict["PeerDescr"][0]] != "":
                                    PeeringParseAll[lineIndex][PeeringDict["PeerDescr"][0]] = PeeringParseAll[lineIndex][PeeringDict["PeerDescr"][0]] + "|"
                                PeeringParseAll[lineIndex][PeeringDict["PeerDescr"][0]] = PeeringParseAll[lineIndex][PeeringDict["PeerDescr"][0]] + tempPeeringParse[PeeringDict["PeerDescr"][0]]

                            if tempPeeringParse[PeeringDict["ASRemote"][0]] not in peeringLine[PeeringDict["ASRemote"][0]].split("|"):
                                if PeeringParseAll[lineIndex][PeeringDict["ASRemote"][0]] != "":
                                    PeeringParseAll[lineIndex][PeeringDict["ASRemote"][0]] = PeeringParseAll[lineIndex][PeeringDict["LocalAS"][0]] + "|"
                                PeeringParseAll[lineIndex][PeeringDict["ASRemote"][0]] = PeeringParseAll[lineIndex][PeeringDict["ASRemote"][0]] + tempPeeringParse[PeeringDict["ASRemote"][0]]

                            if tempPeeringParse[PeeringDict["SysAddrRemote"][0]] != "" and tempPeeringParse[PeeringDict["SysAddrRemote"][0]] != peeringLine[PeeringDict["SysAddrRemote"][0]]:
                                PeeringParseAll[lineIndex][PeeringDict["SysAddrRemote"][0]] = tempPeeringParse[PeeringDict["SysAddrRemote"][0]]
                                PeeringParseAll[lineIndex][PeeringDict["Comments"][0]] = "Remote system IP updated from BGP"
                            elif tempPeeringParse[PeeringDict["SysAddrRemote"][0]] != "":
                                if "BGP" not in PeeringParseAll[lineIndex][PeeringDict["Comments"][0]]:
                                    PeeringParseAll[lineIndex][PeeringDict["Comments"][0]] = PeeringParseAll[lineIndex][PeeringDict["Comments"][0]] + "|BGP"

                        else:
                            # Create duplicate line with another peer address
                            tempPeeringLine = peeringLine.copy()
                            tempPeeringLine[PeeringDict["IPV4AddrRemote"][0]] = tempPeeringLine[PeeringDict["IPV4AddrRemote"][0]]
                            if tempPeeringParse[PeeringDict["PeeringType"][0]] not in tempPeeringLine[PeeringDict["PeeringType"][0]].split("|"):
                                if tempPeeringLine[PeeringDict["PeeringType"][0]] != "":
                                    tempPeeringLine[PeeringDict["PeeringType"][0]] = tempPeeringLine[PeeringDict["PeeringType"][0]] + "|"
                                tempPeeringLine[PeeringDict["PeeringType"][0]] = tempPeeringLine[PeeringDict["PeeringType"][0]] + tempPeeringParse[PeeringDict["PeeringType"][0]]

                            if tempPeeringParse[PeeringDict["LocalAS"][0]] not in tempPeeringLine[PeeringDict["LocalAS"][0]].split("|"):
                                if tempPeeringLine[lineIndex][PeeringDict["LocalAS"][0]] != "":
                                    tempPeeringLine[lineIndex][PeeringDict["LocalAS"][0]] = tempPeeringLine[lineIndex][PeeringDict["LocalAS"][0]] + "|"
                                tempPeeringLine[lineIndex][PeeringDict["LocalAS"][0]] = tempPeeringLine[lineIndex][PeeringDict["LocalAS"][0]] + tempPeeringParse[PeeringDict["LocalAS"][0]]

                            if tempPeeringParse[PeeringDict["PeerDescr"][0]] not in tempPeeringLine[PeeringDict["PeerDescr"][0]].split("|"):
                                if tempPeeringLine[lineIndex][PeeringDict["PeerDescr"][0]] != "":
                                    tempPeeringLine[lineIndex][PeeringDict["PeerDescr"][0]] = tempPeeringLine[lineIndex][PeeringDict["PeerDescr"][0]] + "|"
                                tempPeeringLine[lineIndex][PeeringDict["PeerDescr"][0]] = tempPeeringLine[lineIndex][PeeringDict["PeerDescr"][0]] + tempPeeringParse[PeeringDict["PeerDescr"][0]]

                            if tempPeeringParse[PeeringDict["ASRemote"][0]] not in tempPeeringLine[PeeringDict["ASRemote"][0]].split("|"):
                                if tempPeeringLine[lineIndex][PeeringDict["ASRemote"][0]] != "":
                                    tempPeeringLine[lineIndex][PeeringDict["ASRemote"][0]] = tempPeeringLine[lineIndex][PeeringDict["LocalAS"][0]] + "|"
                                tempPeeringLine[lineIndex][PeeringDict["ASRemote"][0]] = tempPeeringLine[lineIndex][PeeringDict["ASRemote"][0]] + tempPeeringParse[PeeringDict["ASRemote"][0]]

                            if tempPeeringParse[PeeringDict["SysAddrRemote"][0]] != "" and tempPeeringLine[PeeringDict["SysAddrRemote"][0]] != peeringLine[PeeringDict["SysAddrRemote"][0]]:
                                tempPeeringLine[lineIndex][PeeringDict["SysAddrRemote"][0]] = tempPeeringParse[PeeringDict["SysAddrRemote"][0]]
                                tempPeeringLine[lineIndex][PeeringDict["Comments"][0]] = "Remote system IP updated from BGP"
                            elif tempPeeringParse[PeeringDict["SysAddrRemote"][0]] != "":
                                if "BGP" not in tempPeeringLine[lineIndex][PeeringDict["Comments"][0]]:
                                    tempPeeringLine[lineIndex][PeeringDict["Comments"][0]] = tempPeeringLine[lineIndex][PeeringDict["Comments"][0]] + "|BGP"

                            PeeringParseAll.insert(lineIndex,tempPeeringLine)

                lineIndex = lineIndex + 1

            if match1 == 0:
                # Look for other interfaces that were not included in peering table earlier if there are matching ports
                for interfaceLine in InterfacesParseAll:

                    # Getting adresses for local subnet
                    tempIPV4SubnetList = []
                    if str(interfaceLine[InterfacesDict["IPV4Subnet"][0]]) != "":
                        for prefix in interfaceLine[InterfacesDict["IPV4Subnet"][0]].split("|"):
                            tempIPV4Subnet = ipaddress.ip_interface(str(prefix))
                            for address in tempIPV4Subnet.network.hosts():
                                tempIPV4SubnetList.append(str(address))

                    if  (
                            ( "eBGP" in tempPeeringParse[PeeringDict["PeeringType"][0]].split("|") and tempPeeringParse[PeeringDict["IPV4AddrRemote"][0]] in tempIPV4SubnetList )
                            or
                            (( tempPeeringParse[PeeringDict["IfName"][0]] == interfaceLine[InterfacesDict["IfName"][0]] ) or (( tempPeeringParse[PeeringDict["IPV4Addr"][0]] != "" ) and (tempPeeringParse[PeeringDict["IPV4Addr"][0]] == interfaceLine[InterfacesDict["IPV4Addr"][0]].split("/")[0] )))
                        ):

                        match1 = 1
                        PeeringParse = [""] * len(PeeringDict)

                        PeeringParse[PeeringDict["PeeringType"][0]] = tempPeeringParse[PeeringDict["PeeringType"][0]]
                        PeeringParse[PeeringDict["Hostname"][0]] = Hostname
                        PeeringParse[PeeringDict["SysAddr"][0]] = SysAddr
                        PeeringParse[PeeringDict["CLISyntax"][0]] = CLISyntax
                        PeeringParse[PeeringDict["IfName"][0]] = interfaceLine[InterfacesDict["IfName"][0]]
                        PeeringParse[PeeringDict["IfDescr"][0]] = interfaceLine[InterfacesDict["IfDescr"][0]]
                        PeeringParse[PeeringDict["PortBinding"][0]] = interfaceLine[InterfacesDict["PortBinding"][0]]
                        PeeringParse[PeeringDict["IPV4Addr"][0]] = interfaceLine[InterfacesDict["IPV4Addr"][0]]
                        PeeringParse[PeeringDict["IPV4Subnet"][0]] = interfaceLine[InterfacesDict["IPV4Subnet"][0]]
                        PeeringParse[PeeringDict["IPV6Addr"][0]] = interfaceLine[InterfacesDict["IPV6Addr"][0]]
                        PeeringParse[PeeringDict["IPV6Subnet"][0]] = interfaceLine[InterfacesDict["IPV6Subnet"][0]]
                        PeeringParse[PeeringDict["LocalAS"][0]] = tempPeeringParse[PeeringDict["LocalAS"][0]]
                        PeeringParse[PeeringDict["ASRemote"][0]] = tempPeeringParse[PeeringDict["ASRemote"][0]]
                        PeeringParse[PeeringDict["PeerDescr"][0]] = tempPeeringParse[PeeringDict["PeerDescr"][0]]
                        if tempPeeringParse[PeeringDict["SysAddrRemote"][0]] != "":
                            PeeringParse[PeeringDict["SysAddrRemote"][0]] = tempPeeringParse[PeeringDict["SysAddrRemote"][0]]
                            PeeringParse[PeeringDict["Comments"][0]] = "Remote system IP updated from BGP"
                        PeeringParse[PeeringDict["IPV4AddrRemote"][0]] = tempPeeringParse[PeeringDict["IPV4AddrRemote"][0]]

                        for tempPortName in interfaceLine[InterfacesDict["PortName"][0]].split("|"):
                            tempPeeringParse2 = PeeringParse.copy()

                            tempPeeringParse2[PeeringDict["PortName"][0]] = tempPortName
                            PeeringParseAll.append(tempPeeringParse2)

            if match1 == 0:
                print("Error: BGP peer " + tempPeeringParse[PeeringDict["IPV4AddrRemote"][0]] + " is not found in peering and interface tables")

       ################################################### Print summary peering information from all sources to debug file ###################################################

        # Write summary neighbors data to a file
        with open("./" + outputPath + "/debugText.txt", 'a') as debugTextFile:
            if len(PeeringParseAll) > 0:
                debugTextFile.write("Summary neighbor information from all sources (after BGP enrichment) is shown below:\n")
                # Print header
                valueNumber = 0
                for value in printPeeringValueList:
                    if valueNumber == 0:
                        debugTextFile.write(str(value))
                    else:
                        debugTextFile.write("\t" + str(value))
                    valueNumber = valueNumber + 1
                debugTextFile.write("\n")
                # Print data
                for peeringLine in PeeringParseAll:
                    valueNumber = 0
                    for value in printPeeringValueList:
                        if valueNumber == 0:
                            debugTextFile.write(str(peeringLine[PeeringDict[value][0]]))
                        else:
                            debugTextFile.write("\t" + str(peeringLine[PeeringDict[value][0]]))
                        valueNumber = valueNumber + 1
                    debugTextFile.write("\n")
                debugTextFile.write("\n")

        ################################################### Create a list of addresses to connect for polling ###################################################

        pollPeerList = []
        for peeringParseLine in PeeringParseAll:

            # Skip peer with empty remote adresses
            if peeringParseLine[PeeringDict["IPV4AddrRemote"][0]] == "":
                continue

            match = 0
            # Check if values are already in list
            for pollPeerLine in pollPeerList:
                if peeringParseLine[PeeringDict["IPV4AddrRemote"][0]].split("|")[0].split("/")[0] == pollPeerLine[0]:
                    match = 1
            if match == 0:
                pollPeerLine = [ "" ] * 2
                pollPeerLine[0] = peeringParseLine[PeeringDict["IPV4AddrRemote"][0]].split("|")[0].split("/")[0]
                pollPeerLine[1] = peeringParseLine[PeeringDict["IfName"][0]]
                # print(pollPeerLine)
                pollPeerList.append(pollPeerLine)

        # if debug:
        #     with open("./" + outputPath + "/debugText.txt", 'a') as debugTextFile:
        #         debugTextFile.write("\n".join(str(item) for item in pollPeerList))

        ################################################### Connect and poll all neighbors over SSH/Telnet ###################################################

        tempPeeringParseAll = []
        # output = pollNeighbor(connectionCursor,protocol,login,password1,password2,remoteAddr,srcIfName,CLISyntax,execTimeout):
        for pollPeerLine in pollPeerList:
            if CLISyntax != "VRP":
                print("Polling neighbor " + pollPeerLine[0] + " from source interface " + pollPeerLine[1])
                output = pollNeighbor(connectionCursor,protocol,login,password1,password2,pollPeerLine[0],pollPeerLine[1],CLISyntax,60)

                if output[0] == 0:
                    print("Neighbor " + pollPeerLine[0] + " is accessible via " + output[1] + ", has remoteHostname=" + output[2] + ", remoteSysAddr=" + output[3] + ", remoteCLISyntax=" + output[4])

                    tempPeeringParse = [""] * len(PeeringDict)
                    tempPeeringParse[PeeringDict["PeeringType"][0]] = output[1]
                    tempPeeringParse[PeeringDict["IfName"][0]] = pollPeerLine[1]
                    tempPeeringParse[PeeringDict["IPV4AddrRemote"][0]] = pollPeerLine[0]
                    tempPeeringParse[PeeringDict["HostnameRemote"][0]] = output[2]
                    tempPeeringParse[PeeringDict["SysAddrRemote"][0]] = output[3]
                    tempPeeringParse[PeeringDict["CLISyntaxRemote"][0]] = output[4]

                    tempPeeringParseAll.append(tempPeeringParse)

                if debug:
                    with open("./" + outputPath + "/debugText.txt", 'a') as debugTextFile:
                        debugTextFile.write("\n\n\n#####\tPolling neighbor " + pollPeerLine[0] + " from source interface " + pollPeerLine[1] + " on " + str(datetime.datetime.today()) + "\t#####\n")
                        debugTextFile.write("\n".join(str(item) for item in output[5]))

        # Write SSH/Telnet to a file (for diagnostic purposes)
        with open(outputFilePath, 'a') as outputFile:
            if len(tempPeeringParseAll) > 0:
                outputFile.write("Found following neighbors from SSH/Telnet:\n")
                # Print header
                valueNumber = 0
                for value in printPeeringValueList:
                    if valueNumber == 0:
                        outputFile.write(str(value))
                    else:
                        outputFile.write("\t" + str(value))
                    valueNumber = valueNumber + 1
                outputFile.write("\n")
                # Print data
                for peeringLine in tempPeeringParseAll:
                    valueNumber = 0
                    for value in printPeeringValueList:
                        if valueNumber == 0:
                            outputFile.write(str(peeringLine[PeeringDict[value][0]]))
                        else:
                            outputFile.write("\t" + str(peeringLine[PeeringDict[value][0]]))
                        valueNumber = valueNumber + 1
                    outputFile.write("\n")
                outputFile.write("\n")

        # Enrich peering table with parsed data from SSH/Telnet
        for tempPeeringParse in tempPeeringParseAll:
            # Updating data for existing neighbors
            lineIndex = 0
            for peeringLine in PeeringParseAll:

                # Check if remote addresses match
                if ( tempPeeringParse[PeeringDict["IPV4AddrRemote"][0]].split("/")[0] == peeringLine[PeeringDict["IPV4AddrRemote"][0]].split("/")[0] ):
                    match1 = 1
                    if tempPeeringParse[PeeringDict["PeeringType"][0]] not in peeringLine[PeeringDict["PeeringType"][0]].split("|"):
                        if PeeringParseAll[lineIndex][PeeringDict["PeeringType"][0]] != "":
                            PeeringParseAll[lineIndex][PeeringDict["PeeringType"][0]] = PeeringParseAll[lineIndex][PeeringDict["PeeringType"][0]] + "|"
                        PeeringParseAll[lineIndex][PeeringDict["PeeringType"][0]] = PeeringParseAll[lineIndex][PeeringDict["PeeringType"][0]] + tempPeeringParse[PeeringDict["PeeringType"][0]]

                    if tempPeeringParse[PeeringDict["SysAddrRemote"][0]] != "" and tempPeeringParse[PeeringDict["SysAddrRemote"][0]] != peeringLine[PeeringDict["SysAddrRemote"][0]]:
                        PeeringParseAll[lineIndex][PeeringDict["SysAddrRemote"][0]] = tempPeeringParse[PeeringDict["SysAddrRemote"][0]]
                        PeeringParseAll[lineIndex][PeeringDict["Comments"][0]] = "Remote system IP updated from " + tempPeeringParse[PeeringDict["PeeringType"][0]]
                    elif tempPeeringParse[PeeringDict["SysAddrRemote"][0]] != "":
                        if tempPeeringParse[PeeringDict["PeeringType"][0]] not in PeeringParseAll[lineIndex][PeeringDict["Comments"][0]]:
                            PeeringParseAll[lineIndex][PeeringDict["Comments"][0]] = PeeringParseAll[lineIndex][PeeringDict["Comments"][0]] + "|" + tempPeeringParse[PeeringDict["PeeringType"][0]]

                    if tempPeeringParse[PeeringDict["HostnameRemote"][0]] != "" and tempPeeringParse[PeeringDict["HostnameRemote"][0]] != peeringLine[PeeringDict["HostnameRemote"][0]]:
                        PeeringParseAll[lineIndex][PeeringDict["HostnameRemote"][0]] = tempPeeringParse[PeeringDict["HostnameRemote"][0]]

                    if tempPeeringParse[PeeringDict["CLISyntaxRemote"][0]] != "" and tempPeeringParse[PeeringDict["CLISyntaxRemote"][0]] != peeringLine[PeeringDict["CLISyntaxRemote"][0]]:
                        PeeringParseAll[lineIndex][PeeringDict["CLISyntaxRemote"][0]] = tempPeeringParse[PeeringDict["CLISyntaxRemote"][0]]

                # Check if system IP match
                elif ( tempPeeringParse[PeeringDict["SysAddrRemote"][0]].split("/")[0] == peeringLine[PeeringDict["SysAddrRemote"][0]].split("/")[0] ):
                    if tempPeeringParse[PeeringDict["HostnameRemote"][0]] != "" and tempPeeringParse[PeeringDict["HostnameRemote"][0]] != peeringLine[PeeringDict["HostnameRemote"][0]]:
                        PeeringParseAll[lineIndex][PeeringDict["HostnameRemote"][0]] = tempPeeringParse[PeeringDict["HostnameRemote"][0]]

                lineIndex = lineIndex + 1

       ################################################### Print summary peering information from all sources ###################################################

        # Write summary neighbors data to a file
        with open(outputFilePath, 'a') as outputFile:
            if len(PeeringParseAll) > 0:
                outputFile.write("Summary neighbor information from all sources is shown below:\n")
                # Print header
                valueNumber = 0
                for value in printPeeringValueList:
                    if valueNumber == 0:
                        outputFile.write(str(value))
                    else:
                        outputFile.write("\t" + str(value))
                    valueNumber = valueNumber + 1
                outputFile.write("\n")
                # Print data
                for peeringLine in PeeringParseAll:
                    valueNumber = 0
                    for value in printPeeringValueList:
                        if valueNumber == 0:
                            outputFile.write(str(peeringLine[PeeringDict[value][0]]))
                        else:
                            outputFile.write("\t" + str(peeringLine[PeeringDict[value][0]]))
                        valueNumber = valueNumber + 1
                    outputFile.write("\n")
                outputFile.write("\n")


        ################################################### Calculate and print execution time ###################################################

        execTime = time.time() - startTime
        with open(outputFilePath, 'a') as outputFile:
            outputFile.write("#####\tNeighbors collection finished in " + str(round(execTime,2)) + " second(s)\t#####")

        if connectionCursor != "":
            connectionCursor.close()
            if protocol == "ssh":
                client.close()

#####################################################################################################################################################
#####################################################################################################################################################
#####################################################################################################################################################



#####################################################################################################################################################
###########################################################       Script body         ###############################################################
#####################################################################################################################################################

# if debug: print("debug: "+str(sys.argv))

argList = []
for argument in sys.argv:
    # if len(argument.split(":")) > 1:
    #     argument = argument.split(":")[0] + ":******"
    argList.append(argument)

print("Issued command: "+" ".join(str(k) for k in argList))

if len(sys.argv) <= 1:
    printHelpFunc()
    sys.exit()
if ((sys.argv[1] == "help") or (sys.argv[1] == "?") or (sys.argv[1] == "h") or (sys.argv[1] == "--help") or (sys.argv[1] == "-h")):
    printHelpFunc()
    sys.exit()
else:

#####################################################################################################################################################
###########################################################       Parse option         ##############################################################
#####################################################################################################################################################
    if (sys.argv[1] == "-p") or (sys.argv[1] == "--parse"):
        if (len(sys.argv) < 4):     # Initial arguments check
            print("Missig arguents, print -h for help.\r\n")
            sys.exit()
        inputPath = sys.argv[2]
        if debug: print("debug: "+"Input path: "+str(inputPath))
        outputPath = sys.argv[3]
        if debug: print("debug: "+"Output path: "+str(outputPath))

        genClean = 0
        defaultCLISyntax = ""

        if len(sys.argv) >= 4:
            for argument in sys.argv:
                if sys.argv.index(argument) >= 4:
                    if argument == "clean":
                        genClean = 1
                    for value in SyntaxDict:
                        if argument == value:
                            if value != "Hist":
                                defaultCLISyntax = value

        if debug: print("debug: "+"clean input: "+str(genClean))
        if debug: print("debug: "+"default CLI syntax set to: "+str(defaultCLISyntax))

        if debug: print("debug: "+"Input file: "+str(os.path.isfile(inputPath)))
        if debug: print("debug: "+"Input dir: "+str(os.path.isdir(inputPath)))

        inputFiles = []

        if os.path.isfile(inputPath):
            if (inputPath.endswith(".cfg") or inputPath.endswith(".txt") or inputPath.endswith(".log")):
                print("Parsing specified file...\r\n")
                inputFiles.append(inputPath)                  # Parse single file
            else:
                print("Specified file is not recognized text file, please specify another file. Supported extensions are cfg/txt/log.\r\n")
                sys.exit()
        else:
            if os.path.isdir(inputPath):
                if inputPath[-1] != "\\" and inputPath[-1] != "/":
                    inputPath = inputPath + "\\"
                i = 0
                for f in os.listdir(inputPath):
                    if os.path.isfile(inputPath+f):
                        if (f.endswith(".cfg") or f.endswith(".txt") or f.endswith(".log")):
                            if debug: print("debug: "+"Input file "+f+" is valid")
                            inputFiles.append(inputPath+f)      # Parse all files whithin a directory
                            i = i + 1
                        else:
                            if debug: print("debug: "+"Input file "+f+" has invalid extension")
                if i == 0:
                    print("Specified directory has no recognized text files, please specify another directory. Supported file extensions are cfg/txt/log.\r\n")
                    sys.exit()
                else:
                    print("Found",i,"suitable file(s) in specified directory.")
            else:
                print("Specified path is not a recognized directory or file, please specify another path. Supported file extensions are cfg/txt/log.\r\n")
                sys.exit()

        if ((os.path.isfile(outputPath) == False) & (os.path.isdir(outputPath) == False)):
            outputPath2 = os.path.split(outputPath)
            if outputPath2[0]:
                if os.path.isdir(outputPath2[0]) == False:
                    os.makedirs(outputPath2[0])

            outputDB = sqlite3.connect(outputPath)
            if ((outputDB == False) or (os.path.isfile(outputPath) == False)):
                print("Could not create SQLite database, check destination directory permissions.\r\n")
                sys.exit()
            else:
                outputCursor = outputDB.cursor()

                DBQuery="""CREATE TABLE sysInfo (
                            DBFormatVersion,
                            CreationDate,
                            LastUpdatedTime,
                            LastUpdatedBy
                            )"""
                if debugSQL: print("debug: "+str(DBQuery))
                outputCursor.execute(DBQuery)

                DBQuery="""INSERT INTO sysInfo
                            VALUES (
                            '"""+str(DBFormatVersion)+"""',
                            '"""+str(datetime.datetime.today())+"""',
                            '"""+str(datetime.datetime.today())+"""',
                            '"""+str(getpass.getuser())+"""'
                            )"""
                if debugSQL: print("debug: "+str(DBQuery))
                outputCursor.execute(DBQuery)

                outputDB.commit()

                DBQuery="""SELECT name
                            FROM sqlite_master where type='table'
                            """
                if debugSQL: print("debug: "+str(DBQuery))
                outputCursor.execute(DBQuery)

                tables = [description[0] for description in outputCursor.fetchall()]
                if debug: print("debug: "+str(tables))

                match = 0
                for t in tables:
                    if (t == "sysInfo"): match = 1
                if match == 0:
                    print("DB creation error, could not create sysInfo table correctly.\r\n")
                    outputDB.close()
                    os.remove(outputPath)
                    sys.exit()

                DBQuery="""SELECT *
                            FROM sysInfo"""
                if debugSQL: print("debug: "+str(DBQuery))
                outputCursor.execute(DBQuery)

                sysInfoColumns = [description[0] for description in outputCursor.description]
                if debug: print("debug: "+str(sysInfoColumns))

                if ((sysInfoColumns[0] != "DBFormatVersion") or (sysInfoColumns[1] != "CreationDate") or (sysInfoColumns[2] !="LastUpdatedTime") or (sysInfoColumns[3] !="LastUpdatedBy")):
                    print("DB creation error, could not create sysInfo table correctly.\r\n")
                    outputDB.close()
                    os.remove(outputPath)
                    sys.exit()

            print("Successfully created database at \""+outputPath+"\".")

        else:
            if (os.path.isdir(outputPath) == True):
                print("Specified output path matches existing directory, can not proceed.\r\n")
                sys.exit()
            else:
                outputDB = sqlite3.connect(outputPath)
                if debug: print("debug: "+"DB file: "+str(outputDB))
                outputCursor = outputDB.cursor()

                DBQuery="""SELECT name
                            FROM sqlite_master
                            WHERE type='table'
                            """
                if debugSQL: print("debug: "+str(DBQuery))
                outputCursor.execute(DBQuery)

                tables = [description[0] for description in outputCursor.fetchall()]
                if debug: print("debug: "+str(tables))

                match = 0
                for t in tables:
                    if (t == "sysInfo"): match = 1
                if match == 0:
                    print("DB opening error, could not find sysInfo table.\r\n")
                    outputDB.close()
                    sys.exit()

                DBQuery="""SELECT *
                            FROM sysInfo
                            """
                if debugSQL: print("debug: "+str(DBQuery))
                outputCursor.execute(DBQuery)

                sysInfoColumns = [description[0] for description in outputCursor.description]
                if debug: print("debug: "+str(sysInfoColumns))

                if ((sysInfoColumns[0] != "DBFormatVersion") or (sysInfoColumns[1] != "CreationDate") or (sysInfoColumns[2] !="LastUpdatedTime") or (sysInfoColumns[3] !="LastUpdatedBy")):
                    print("DB opening error, sysInfo table has missing columns.\r\n")
                    outputDB.close()
                    sys.exit()
                else:
                    DBQuery="""SELECT DBFormatVersion
                                FROM sysInfo
                                """
                    if debugSQL: print("debug: "+str(DBQuery))
                    outputCursor.execute(DBQuery)

                    DBFormatVersionCheck = 0
                    DBFormatVersionCheck = outputCursor.fetchone()[0]
                    if debug: print("debug: File DBFormatVersion = "+str(DBFormatVersionCheck[0]))
                    if debug: print("debug: Current DBFormatVersion = "+str(DBFormatVersion))

                    if str(DBFormatVersionCheck[0]) != str(DBFormatVersion):
                        print("DB opening error, DB format version mismatch. Please specify another output file.\r\n")
                        outputDB.close()
                        sys.exit()

                    outputDB.close()
                    shutil.copy(outputPath,outputPath+"."+time.strftime("%Y%m%d_%H%M%S")+".bak")
                    outputDB = sqlite3.connect(outputPath)
                    outputCursor = outputDB.cursor()

                    DBQuery="""SELECT *
                                FROM sysInfo
                                """
                    if debugSQL: print("debug: "+str(DBQuery))
                    outputCursor.execute(DBQuery)
                    if debug: print(outputCursor.fetchall())
                    DBQuery= """UPDATE sysInfo
                                SET LastUpdatedTime = '"""+str(datetime.datetime.today())+"""'
                                WHERE DBFormatVersion = '"""+str(DBFormatVersion)+"""'
                                """
                    if debugSQL: print("debug: "+str(DBQuery))
                    outputCursor.execute(DBQuery)
                    if debug: print(outputCursor.fetchall())
                    outputDB.commit()

                print("Successfully opened database at \""+outputPath+"\".")

        parseFunc(inputFiles,outputDB,defaultCLISyntax,genClean)
    else:
#####################################################################################################################################################
#########################################################         Output option         #############################################################
#####################################################################################################################################################
        if (sys.argv[1] == "-o") or (sys.argv[1] == "--output"):
            if (len(sys.argv) < 4):     # Initial arguments check
                print("Missig arguents, print -h for help.\r\n")
                sys.exit()
            inputPath = sys.argv[2]
            if debug: print("debug: "+"Input path: "+str(inputPath))
            outputPath = sys.argv[3]
            if debug: print("debug: "+"Output path: "+str(outputPath))

            targSyntax = ""

            if len(sys.argv) == 5:
                for argument in sys.argv:
                    if sys.argv.index(argument) == 4:
                        for value in SyntaxDict:
                            if argument == value:
                                if value != "Hist":
                                    targSyntax = value

            if debug: print("debug: "+"Input file: "+str(os.path.isfile(inputPath)))
            if debug: print("debug: "+"Input dir: "+str(os.path.isdir(inputPath)))

            if os.path.isfile(inputPath):
                print("Opening specified database...\r\n")
            else:
                print("Specified path is not a recognized database file, please specify another path.\r\n")
                sys.exit()

            inputDB = sqlite3.connect(inputPath)
            if debug: print("debug: "+"DB file: "+str(inputDB))
            inputCursor = inputDB.cursor()

            DBQuery="""SELECT name
                        FROM sqlite_master
                        WHERE type='table'
                        """
            if debugSQL: print("debug: "+str(DBQuery))
            inputCursor.execute(DBQuery)

            tables = [description[0] for description in inputCursor.fetchall()]
            if debug: print("debug: "+str(tables))

            match = 0
            for t in tables:
                if (t == "sysInfo"): match = 1
            if match == 0:
                print("DB opening error, could not find sysInfo table.\r\n")
                inputDB.close()
                sys.exit()

            DBQuery="""SELECT *
                        FROM sysInfo
                        """
            if debugSQL: print("debug: "+str(DBQuery))
            inputCursor.execute(DBQuery)

            sysInfoColumns = [description[0] for description in inputCursor.description]
            if debug: print("debug: "+str(sysInfoColumns))

            if ((sysInfoColumns[0] != "DBFormatVersion") or (sysInfoColumns[1] != "CreationDate") or (sysInfoColumns[2] !="LastUpdatedTime") or (sysInfoColumns[3] !="LastUpdatedBy")):
                print("DB opening error, sysInfo table has missing columns.\r\n")
                inputDB.close()
                sys.exit()
            else:
                DBQuery="""SELECT DBFormatVersion
                            FROM sysInfo
                            """
                if debugSQL: print("debug: "+str(DBQuery))
                inputCursor.execute(DBQuery)

                DBFormatVersionCheck = ""
                DBFormatVersionCheck = inputCursor.fetchone()[0]
                if debug: print("debug: File DBFormatVersionCheck = "+str(DBFormatVersionCheck[0]))
                if debug: print("debug: Current DBFormatVersion = "+str(DBFormatVersion))

                if str(DBFormatVersionCheck[0]) != str(DBFormatVersion):
                    print("DB opening error, DB format version mismatch. Please specify another output file.\r\n")
                    inputDB.close()
                    sys.exit()

            print("Successfully opened database at \""+inputPath+"\".")

            if ((os.path.isfile(outputPath) == False) & (os.path.isdir(outputPath) == False)):
                outputPath2 = os.path.split(outputPath)
                if outputPath2[1] is None:
                    print("Please specify path with non-empty filename\r\n")
                    inputDB.close()
                    sys.exit()
                else:
                    if outputPath2[0]:
                        if os.path.isdir(outputPath2[0]) == False:
                            os.makedirs(outputPath2[0])
                            print("Creating a new output file "+ outputPath2[1] +" at "+outputPath2[0])
                    else:
                        print("Creating a new output file "+outputPath2[1]+"\".")
            else:
                if (os.path.isdir(outputPath) == True):
                    print("Specified output file matches existing directory name. Please specify another output path.\r\n")
                    inputDB.close()
                    sys.exit()
                else:
                    print("Specified output file matches existing file. Existing file will backed up to another file and overwritten.\r\n")
                    shutil.copy(outputPath,outputPath+"."+time.strftime("%Y%m%d_%H%M%S")+".bak")
                    os.remove(outputPath)


            if len(outputPath.split(".")) > 1:
                # print(outputPath2[1].split(".")[1])
                if re.match(r"^[Cc][Ss][Vv]$",outputPath.split(".")[-1]):
                    print("Using CSV output file format.")
                    fileFormat = "csv"
                else:
                    if re.match(r"^[Xx][Ll][Ss][Xx]$",outputPath.split(".")[-1]):
                        print("Using XLSX output file format.")
                        fileFormat = "xlsx"
                    else:
                        print("Could not identify output file extension to set up file format. Please specify either \".csv\" or \".xlsx\" file extension.\r\n")
                        inputDB.close()
                        sys.exit()

            outputFunc(inputDB,outputPath,fileFormat,targSyntax)
        else:
#####################################################################################################################################################
###########################################################        Collect option         ###########################################################
#####################################################################################################################################################
            if (sys.argv[1] == "-c") or (sys.argv[1] == "--collect"):

    # -c|--collect    {login} {IPv4 addresses list/file} {output directory name} [recursive] [number of streams]
                # Initial arguments check
                if (len(sys.argv) < 5):
                    print("Missig arguents, print -h for help.\r\n")
                    sys.exit()

                # # Checking login password
                # if len(sys.argv[2].split(":")) < 2:
                #     print("Please specify login.\r\n")
                #     sys.exit()

                # login = sys.argv[2].split(":")[0]
                login = sys.argv[2]
                # password = sys.argv[2].split(":")[1]
                if debug: print("debug: "+"Using login: "+str(login))

                # Checking output directory
                outputPath = sys.argv[4]
                if ( os.path.isfile(outputPath) == True ):
                    print("Specified output directory path matches existing file, please specify another one.\r\n")
                    sys.exit()

                if ( os.path.isdir(outputPath) == False ):
                    if debug: print("debug: "+"Creating directory: "+str(outputPath))
                    os.makedirs(outputPath)

                # outputPath = outputPath + "/" + datetime.datetime.today().strftime("%Y-%m-%d_%H-%M") + "/"
                # if ( os.path.isdir(outputPath) == False ):
                #     os.makedirs(outputPath)

                # Checking management adresses and creating a list
                mgmtAddrList = []
                rawAddrList = []
                fileBool = False
                # print(sys.argv[3])
                # Checking if list of IPv4 addresses specified in a file
                if re.match(r"^[\d\,\.\-\/]+$",sys.argv[3]):
                    # print("Address list specified: " + str(sys.argv[3]))

                    if len(sys.argv[3].split(",")) > 1:
                        rawAddrList = sys.argv[3].split(",")
                    else:
                        rawAddrList.append(sys.argv[3])
                else:
                    # Check if specified string matches existing directory
                    if ( os.path.isdir(sys.argv[3]) == True ):
                        print("Specifed IPv4 addresses filename is not a file, exiting")
                        sys.exit()

                    # Check if specified string not matches existing filename
                    if ( os.path.isfile(sys.argv[3]) == False ):
                        print("Could not find specifed IPv4 addresses filename, exiting")
                        sys.exit()

                    fileBool = True
                    print("Filename specified: " + str(sys.argv[3]))

                    # Open file
                    addressFileContent = open(sys.argv[3],"r",newline ='\r')
                    rawAddrList = addressFileContent.readlines()

                # print(rawAddrList)

                for value in rawAddrList:
                    # print(value)
                    escapes = ''.join([chr(char) for char in range(1, 32)])
                    translator = str.maketrans('', '', escapes)
                    value = value.translate(translator)
                    value = value.lstrip().rstrip()
                    # print(value)

                    # Searching for individual IPv4 adresses in provided input
                    if re.match(r"^([1-9][0-9]?|1[0-9][0-9]|(2[0-1][0-9]|22[0-3]))(\.([1-9]?[0-9]|1[0-9][0-9]|(2[0-4][0-9]|25[0-5]))){3}$", value):
                        if fileBool:
                            print("Found address in file: " + str(value))
                        if int(ipaddress.ip_address(str(value))) not in mgmtAddrList:
                            mgmtAddrList.append(int(ipaddress.ip_address(str(value))))

                    else:
                    # Searching for IPv4 ranges in provided input
                        if re.match(r"^([1-9][0-9]?|1[0-9][0-9]|(2[0-1][0-9]|22[0-3]))(\.([1-9]?[0-9]|1[0-9][0-9]|(2[0-4][0-9]|25[0-5]))){3}-([1-9][0-9]?|1[0-9][0-9]|(2[0-1][0-9]|22[0-3]))(\.([1-9]?[0-9]|1[0-9][0-9]|(2[0-4][0-9]|25[0-5]))){3}$", value):
                            if fileBool:
                                print("Found address range in file: " + str(value))

                            ipaddStart = ipaddress.ip_address(str(value.split("-")[0]))
                            ipaddStop = ipaddress.ip_address(str(value.split("-")[1]))

                            # print(int(ipaddStop)-int(ipaddStart)+1)
                            if (int(ipaddStop)-int(ipaddStart)+1) > 1024:
                                print("Ranges containing more than 1024 adresses are not allowed.")
                                sys.exit()
                            else:
                                if (int(ipaddStop)-int(ipaddStart)+1) < 0:
                                    print("Starting address in range can not be lower than ending address.")
                                    sys.exit()
                            for i in range(int(ipaddStart),int(ipaddStop)+1):
                                if int(ipaddress.ip_address(i)) not in mgmtAddrList:
                                    mgmtAddrList.append(int(ipaddress.ip_address(i)))
                        else:
                    # Searching for IPv4 subnets in provided input
                            if re.match(r"^([1-9][0-9]?|1[0-9][0-9]|(2[0-1][0-9]|22[0-3]))(\.([1-9]?[0-9]|1[0-9][0-9]|(2[0-4][0-9]|25[0-5]))){3}\/([1-9]|[1-2][0-9]|3[0-2])$", value):
                                if fileBool:
                                    print("Found address subnet in file: " + str(value))
                                ipadd = ipaddress.ip_interface(str(value))
                                if len(list(ipadd.network)) > 1024:
                                    print("Subnets larger than /22 are not allowed.")
                                    sys.exit()
                                for host in list(ipadd.network):
                                    if int(host) not in mgmtAddrList:
                                        mgmtAddrList.append(int(host))
                            else:
                    # Searching for IPv4 BGP peers in provided input
                                if re.match(r"^(neighbor|peer) +([1-9][0-9]?|1[0-9][0-9]|(2[0-1][0-9]|22[0-3]))(\.([1-9]?[0-9]|1[0-9][0-9]|(2[0-4][0-9]|25[0-5]))){3}.*$", value):
                                    if fileBool:
                                        print("Found address of BGP peer in file: " + str(value.split()[1]))
                                    if int(ipaddress.ip_address(str(value.split()[1]))) not in mgmtAddrList:
                                        mgmtAddrList.append(int(ipaddress.ip_address(str(value.split()[1]))))

                if len(mgmtAddrList) == 0:
                    print("No valid IPv4 management address specified. IPv4 addresses must be in range 1.0.0.0 ~ 223.255.255.255 and subnet masks in range /22 ~ /32.\r\n")
                    sys.exit()

                # mgmtAddrList.sort()

                if len(mgmtAddrList) > 1024:
                    print("Working on more than 1024 adresses is not allowed.")
                    sys.exit()
                else:
                    # for address in mgmtAddrList:
                        # print(str(address))
                    if len(mgmtAddrList) > 10:
                        if not re.match(r'^ *(Y|y)(E|e)(S|s) *$',input("You have specified "+str(len(mgmtAddrList))+" addresses. Type \"yes\" if you sure you want to proceed? ")):
                            print("Aborting action.")
                            sys.exit()

                if len(mgmtAddrList) > 1:
                    print("Working on "+str(len(mgmtAddrList))+" addresses in range between "+str(ipaddress.ip_address(min(mgmtAddrList)))+" and "+str(ipaddress.ip_address(max(mgmtAddrList))) + ".")

                else:
                    print("Working on single specified address: " + str(ipaddress.ip_address(mgmtAddrList[0])))

# -c|--collect    {login} {IPv4 addresses list/file} {output directory name} [recursive] [number of streams]


                # Checking optional arguments
                recursive = False
                parallel = False

                argNumber = 0
                for argument in sys.argv:
                    if argNumber == 5:
                        if argument == "recursive":
                            recursive = True
                            if debug: print("debug: "+"Working recursively.")
                        else:
                            if (( argument.isnumeric() ) and ( streams == 1 )):
                                streams = int(argument)
                                if debug: print("debug: "+"number of streams set to " + str(streams) + ".")

                password1 = password2 = ""
                password1 = getpass.getpass("Please enter a password for authentication: ")
                password2 = getpass.getpass("Please enter a secondary (enable) password: ")

                if password2 == "":
                    password2 = password1

                print("Collecting data...\r\n")

                for host in mgmtAddrList:
                    hostAddr = ipaddress.ip_address(host)
                    collectFunc(login,password1,password2,hostAddr,outputPath,recursive)
                # print("Function under construction")
            else:
                print("Unknown argument \""+sys.argv[1]+"\"")
                sys.exit()

####################################################################################################