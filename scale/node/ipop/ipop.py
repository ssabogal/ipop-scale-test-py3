#!/usr/bin/env python

import os
import sys
import json
import shlex
import subprocess

def cmd(command):
    proc = subprocess.Popen(shlex.split(command), stdout=subprocess.PIPE)
    ret = proc.stdout.read()[:-1].decode("utf-8")
    print(ret)
    return ret

IPOP_TINCAN="./ipop-tincan"
IPOP_CONTROLLER="controller.Controller"
IPOP_GVPN_CONFIG="./controller/modules/sample-gvpn-config.json"
IPOP_SVPN_CONFIG="./controller/modules/sample-svpn-config.json"
IPOP_CONFIG="./gen-config.json"

LOG_TIN="./tin.log"
LOG_CTR="./ctr.log"

def main():

    ### change pwd to script location
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    ### handle/redirect commands
    args = sys.argv[1:]

    if (args[0] == "run"):

        #TODO check that not already running
        cmd("bash -c \"sudo chmod +x "+IPOP_TINCAN+"\"")

        # run IPOP tincan

        cmd("bash -c \"nohup sudo "+IPOP_TINCAN+" &> "+LOG_TIN+" 2>&1 &\"")
        cmd("bash -c \"nohup python -m "+IPOP_CONTROLLER+" -c "+IPOP_CONFIG+" &> "+LOG_CTR+" 2>&1 &\"")

    elif (args[0] == "stop"):
        cmd("bash -c \"ps aux | grep -v grep | grep "+IPOP_TINCAN+" | awk '{print $2}' | xargs sudo kill -9\"")
        cmd("bash -c \"ps aux | grep -v grep | grep "+IPOP_CONTROLLER+" | awk '{print $2}' | xargs sudo kill -9\"")

    elif (args[0] == "config"):

        ipop_id   = int(args[1])
        vpn_type  = args[2]
        serv_addr = args[3]
        fwdr_addr = args[4]
        fwdr_port = int(args[5])
        options   = args[6:]

        config = {}

        # generate an IPOP SVPN config file
        if (vpn_type == "svpn"):
            f = open(IPOP_SVPN_CONFIG, 'r')
            config = json.load(f)
            f.close()

            # TODO

        # generate an IPOP GVPN config file
        else:
            f = open(IPOP_GVPN_CONFIG, 'r')
            config = json.load(f)
            f.close()

            # options reserved by scale-test
            config["CFx"]["xmpp_username"] = "node"+str(ipop_id)+"@ejabberd"
            config["CFx"]["xmpp_password"] = "password"
            config["CFx"]["xmpp_host"] = serv_addr
            config["CFx"]["vpn_type"] = "SocialVPN" if (vpn_type == "svpn") else "GroupVPN"
            config["TincanSender"]["stun"] = [serv_addr+":3478"]
            config["TincanSender"]["turn"] = [{"server": serv_addr+":19302", "user": "node"+str(ipop_id), "pass": "password"}]
            config["BaseTopologyManager"]["ip4"] = '172.31.'+str(ipop_id//256)+'.'+str(ipop_id%256)
            config["CFx"]["ip4_mask"] = 16
            config["CentralVisualizer"]["central_visualizer_addr"] = fwdr_addr
            config["CentralVisualizer"]["central_visualizer_port"] = int(fwdr_port)

            config["CFx"]["tincan_logging"] = 2
            config["Logger"]["controller_logging"] = "INFO"
            config["CentralVisualizer"]["enabled"] = True
            config["BaseTopologyManager"]["use_central_visualizer"] = True

            # available options (args[6:])
            config["BaseTopologyManager"]["num_successors"]      = int(options[0])
            config["BaseTopologyManager"]["num_chords"]          = int(options[1])
            config["BaseTopologyManager"]["num_on_demand"]       = int(options[2])
            config["BaseTopologyManager"]["num_inbound"]         = int(options[3])
            config["BaseTopologyManager"]["ttl_link_initial"]    = int(options[4])
            config["BaseTopologyManager"]["ttl_link_pulse"]      = int(options[5])
            config["BaseTopologyManager"]["ttl_chord"]           = int(options[6])
            config["BaseTopologyManager"]["ttl_on_demand"]       = int(options[7])
            config["BaseTopologyManager"]["threshold_on_demand"] = int(options[8])

        # generate IPOP config file
        f = open(IPOP_CONFIG, 'w')
        json.dump(config, f, indent = 4)
        f.close()

    else:
        print("unrecognized command")

if __name__ == "__main__":
    main()
