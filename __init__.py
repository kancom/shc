# -*- coding: utf-8 -*-


"""snmp agent with AgentX protocol for KPI."""


__author__    = "Andrey Kashirin <support@sysqual.net>"
__date__      = "2016-10-22 15:11:01 MSK"
__copyright__ = "Copyright (C) 2018 by SysQual, LLC"
__license__   = "proprietary"
__version__   = "2.5"


import os
import re
import grp
import pwd
import sys
import time
import argparse
import subprocess

from sqlalchemy.sql import text
from threading import Thread, Event
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from flask import json, Response, request

from riva_platform import utils
from riva_platform.shc import settings
from riva_platform.shc.model import CfgNode
from riva_platform.utils import EndpointAction, FlaskAppWrapper, shutdown_flask


#~ TODO
#~ add logger
def print_debug(mgs):
    if settings.DEBUG_MODE:
        print(mgs)

def shell_cmd_output(cmd_fmt, args=None):
    if args:
        cmd = cmd_fmt % args
    else:
        cmd = cmd_fmt
    result = ""
    print_debug("shell_cmd_output: cmd=%s" % cmd)
    try:
        result = subprocess.check_output(cmd, shell=True)
    finally:
        return result

def shell_cmd(cmd):
    result = subprocess.call(cmd, shell=True)
    return True if result==0 else False


def format_alarm_msg(msg, lvl=settings.LVL_CRT):
    return (lvl, msg)


def get_service_list():
    cmd = "systemctl list-units"
    result = shell_cmd_output(cmd)
    return result

def check_cmd(cmd2check):
    cmd = cmd2check[0]
    clevel = cmd2check[1]
    cmsg = cmd2check[2]
    if not shell_cmd(cmd):
        return format_alarm_msg(cmsg, clevel)

def check_proc(proc2check):
    proc = proc2check[0]
    clevel = proc2check[1] if len(proc2check)>1 else settings.LVL_CRT
    cprocesses = proc2check[2] if len(proc2check)>2 else None
    cmd = "pgrep -c -P 1 -f '%s$' || printf ''"
    output = int(shell_cmd_output(cmd, proc))
    if not output:
        return format_alarm_msg("%s is not running" % proc, clevel)
    elif cprocesses and cprocesses<output:
        return format_alarm_msg("%s has more processes than expected" % proc, clevel)
    elif cprocesses and cprocesses>output:
        return format_alarm_msg("%s has less processes than expected" % proc, clevel)
    return False


def check_service(service2test, service_list):
    service = service2test[0]
    clevel = service2test[1] if len(service2test)>1 else settings.LVL_CRT
    csub = service2test[2] if len(service2test)>2 else "running"
    cenabled = service2test[3] if len(service2test)>3 else "active"
    #~ sys-devices-pci0000:00-0000:00:1c.6-0000:02:00.0-net-wlp2s0.device                        loaded active plugged   Wireless 8260
    mo = re.search(service+' +([^ ]+) +([^ ]+) +([^ ]+)',
                    service_list,
                    re.MULTILINE)
    result = False
    if mo:
        loaded = mo.group(1)
        enabled = mo.group(2)
        sub = mo.group(3)
        result = (csub==sub) and (cenabled==enabled)
    if not result:
        return format_alarm_msg("%s is not at expected state" % service, clevel)
    return False

def check_path(path2test):
    path = path2test[0]
    clevel = path2test[1] if len(path2test)>1 else settings.LVL_CRT
    mode = str(path2test[2]) if len(path2test)>2 else None
    owner = path2test[3] if len(path2test)>3 else None
    group = path2test[4] if len(path2test)>4 else None
    if not os.path.exists(path):
        return format_alarm_msg("%s doesn't exist" % path, clevel)
    result = True
    stat_info = os.stat(path)
    uid = stat_info.st_uid
    gid = stat_info.st_gid
    fmode = str(oct(stat_info.st_mode))[3:]
    fuser = pwd.getpwuid(uid)[0]
    fgroup = grp.getgrgid(gid)[0]
    if mode:
        result = result and fmode==mode
    if owner:
        result = result and fuser==owner
    if group:
        result = result and fgroup==group
    if result:
        return False
    return format_alarm_msg("%s permissions are not correct" % path, clevel)

def extend_procs(ip, dbsession):
    sql = settings.SQL_LOCAL_PROCS % ip
    result = dbsession.execute(text(sql))
    for line in result:
        name, cnt = line
        if name not in settings.PROCS2CHECK:
            settings.PROCS2CHECK[name] = (name, settings.LVL_CRT, cnt)
            settings.ROLE_CHECK_MAP['common']['proc'].append(
                name
            )


def collect_health():
    engine = create_engine("mysql://{}:{}@{}/config".format(
                                settings.PROD_BRAND,
                                settings.SYS_PASS,
                                settings.DBCONFIG,
                                ),
                        encoding='utf8',
                        echo=True if settings.DEBUG_MODE else False
                                        )
    smaker = sessionmaker(bind=engine)
    dbsession = smaker()
    my_ip = utils.get_used_ip_address(utils.get_net_df_gw())
    dbres = dbsession.query(CfgNode.gui, CfgNode.db_data, CfgNode.probe).\
                            filter(CfgNode.address==my_ip).\
                            one()
    gui, dbdata, probe = dbres
    #~ gui='off'
    #~ probe='off'
    #~ dbdata='off'
    roles = {}
    roles['common'] = True
    roles['gui'] = True if gui=='on' else False
    roles['probe'] = True if probe=='on' else False
    roles['dbdata'] = True if dbdata=='on' else False
    result = {}
    extend_procs(my_ip, dbsession)
    for role, armed in roles.iteritems():
        if armed:
            result[role] = {}
            tests = settings.ROLE_CHECK_MAP[role]['path']
            result[role]['path'] = []
            for test in tests:
                test = settings.PATH2CHECK[test]
                test_res = check_path(test)
                if test_res:
                    result[role]['path'].append(test_res)

            tests = settings.ROLE_CHECK_MAP[role]['service']
            result[role]['service'] = []
            service_list = get_service_list()
            for test in tests:
                test = settings.SERVICE2CHECH[test]
                test_res = check_service(test, service_list)
                if test_res:
                    result[role]['service'].append(test_res)

            tests = settings.ROLE_CHECK_MAP[role]['proc']
            result[role]['proc'] = []
            for test in tests:
                test = settings.PROCS2CHECK[test]
                test_res = check_proc(test)
                if test_res:
                    result[role]['proc'].append(test_res)

            tests = settings.ROLE_CHECK_MAP[role]['cmd']
            result[role]['cmd'] = []
            for test in tests:
                test = settings.RAWCMD2CHECK[test]
                test_res = check_cmd(test)
                if test_res:
                    result[role]['cmd'].append(test_res)
    return result

term_event = Event()

def periodic_func():
    cmd = "curl -d 'rescan=true' -X POST http://127.0.0.1:%s%sget 2>&1 /dev/null"
    args = (settings.REST_PORT, settings.ROUTE)
    while not term_event.isSet():
        shell_cmd_output(cmd, args)
        elapsed = 0
        while not term_event.isSet() and elapsed<settings.CHECK_INTERVAL:
            time.sleep(1)
            elapsed += 1


class RESTapi(object):
    HEALTH = {}
    def __init__(self, quenue = None):
        self.flask_app = FlaskAppWrapper(__name__)
        self.flask_app.add_endpoint(endpoint=settings.ROUTE+'get',
                                    endpoint_name='get',
                                    handler=self.rest_get_health,
                                    methods=['GET', 'POST']
                                    )
        self.quenue = quenue
        print_debug("http://127.0.0.1:" + str(settings.REST_PORT) + settings.ROUTE)
        self.flask_app.run(host='0.0.0.0', port=settings.REST_PORT,
                           debug=False, use_reloader=False)

    def stop(self):
        shutdown_flask()

    def rest_get_health(self):
        try:
            if not self.HEALTH or request.method=='POST':
                self.HEALTH.clear()
                self.HEALTH = collect_health()
            response = Response(json.dumps(self.HEALTH),
                            status=settings.HTTP_200_OK,
                            mimetype=u'application/json')
            return response
        except:
            print("rest_get_health: health fulfill failed")
            return Response(
                        json.dumps({'msg':'Failed'}),
                        status=settings.HTTP_503_SERVICE_UNAVAILABLE,
                        mimetype=u'application/json'
                        )

def main():
    print_debug("DEBUG MODE")
    parser = argparse.ArgumentParser(
        description=__doc__,
        epilog="Report bugs to %s" % __author__
    )
    parser.add_argument(
        "-v", "--version", action="store_true",
        help="Print version and exit"
    )
    args = parser.parse_args(sys.argv[1:])
    if args.version:
        print '%s' % __version__
        return 0

    try:
        restapi = None
        thread = Thread(target = periodic_func)
        thread.daemon = True
        thread.start()
        restapi = RESTapi()
    except Exception as e:
        print "Unhandled exception:", e
        term_event.set()
        if (restapi):
            restapi.stop()
    except KeyboardInterrupt:
        term_event.set()
        if (restapi):
            restapi.stop()

if __name__ == "__main__":
        main()
