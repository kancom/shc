# -*- coding: utf-8 -*-


import os

__author__    = "Andrey Kashrin <kas@sysqual.net>"
__copyright__ = "Copyright (C) 2018 by SysQual, LLC"
__license__   = "proprietary"

#~ Generic
DEBUG_MODE = False
PROD_PATH = '/opt'
PROD_USER = 'support'
PROD_BRAND = 'discovery'
SYS_PASS = 'ygxahpms'
DBCONFIG = 'dbconfig'
CHECK_INTERVAL = 60*5 # sec

#~ REST
API_VERSION = 'v1.0'
REST_PORT = 9873 #  tcp
ROUTE = "/health/api/" + API_VERSION + '/'

HTTP_200_OK = 200
HTTP_503_SERVICE_UNAVAILABLE = 503


ROLE_DBDATA = "dbdata"
ROLE_PROBE = "probe"
ROLE_BRKR = "broker"
ROLE_PRSR = "parser"
ROLE_XPI = "xpi"
ROLE_DPI = "dpi"
#~ ROLE_STSK = "statistics"
ROLE_GUI = "gui"

BIN_PATH = os.path.join(PROD_PATH, PROD_BRAND, 'bin')

LVL_CRT = "CRITICAL"
LVL_MJR = "MAJOR"
LVL_MNR = "MINOR"

PATH2CHECK = dict(
        #~ name=('abs/path', [LEVEL, [mode=xxxx, [owner, group]]]
        bin=(BIN_PATH,),
        lib=('/opt/discovery/lib/',),
        data=('/var/discovery/data/',),
        pdu=('/var/discovery/data/pdus',),
        chr1=('/var/discovery/data/chrs/arch',),
        chr2=('/var/discovery/data/chrs/cache',),
        chdata=('/var/discovery/data/dbfiles/clickhouse',
                    LVL_CRT, 755,
                    'clickhouse', 'clickhouse')
)

SERVICE2CHECH = dict(
        #~ name=('service-name', [LEVEL, [state=running, [enabled=active]]]
        mysql=('mysql.service',),
        nginx=('nginx.service',),
        phpfpm=('php7.2-fpm.service',),
        snmpd=('snmpd.service', LVL_MJR),
        ntp=('ntp.service', LVL_MJR),
        clickhouse=('clickhouse-server.service',),
        rsyslog=('rsyslog.service', LVL_MNR, 'running', 'active'),
        corosync=('corosync.service',),
        pacemaker=('pacemaker.service',),
        diplatform=('di-platform.target', LVL_MNR, 'active', 'active'),
        dicore=('di-core.target', LVL_MNR, 'active', 'active'),
)


SQL_LOCAL_PROCS = """
    SELECT name, count(*) cnt
    FROM config.vw_sys_procs2args
    WHERE address = '%s'
    GROUP BY name
"""
PROCS2CHECK = dict(
        #~ name='process' name', [LEVEL, [max number of threads]]
        #~ examples below
        #~ shc=('di-shc',),
        #~ dbproxy=('di-dbproxy', LVL_CRT, 5),
        #~ dbreplication=('di-dbreplication', LVL_MJR),
)

RAWCMD2CHECK = dict(
    #~ name=("cmd returning 0, if not - alarm", LEVEL, "alarm message")
    spaceroot=("""/bin/df / | awk '/^\// {usg=substr($5,1,length($5)-1); if (usg<95){print "ok"}}' | grep ok""",
                LVL_CRT, "/ usage more than 95%"),
    spacedata=("""/usr/bin/test -d /var/discovery/data && /bin/df /var/discovery/data | /usr/bin/awk '/^\// {usg=substr($5,1,length($5)-1); if (usg<95){print "ok"}}' | /bin/grep ok""",
                LVL_CRT, "/var/discovery/data usage more than 95%"),
    timezone=("date +%Z | grep UTC", LVL_CRT, "Node's timezone is not UTC0"),
    ntpsync=('ntpq -np | grep "*"', LVL_MJR, "ntp is not in sync"),
)

KPI2CHECK = dict(
    #~ name=("kpi full name", rate, "alarm mesage if more than rate", [LEVEL, [minvalue])
    notimplemented="notimplemented",
)

ROLE_CLAUSES = ['path', 'service', 'proc', 'cmd', 'kpi']

ROLE_CHECK_MAP = {
    "common": dict(
        path=['bin', 'lib', ],
        service=['snmpd', 'ntp', 'rsyslog', 'diplatform',],
        proc=[],
        cmd=['spaceroot', 'timezone', 'ntpsync', ],
        kpi=[],
    ),
    ROLE_DBDATA: dict(
        path=['chdata',],
        service=['clickhouse',],
        proc=[],
        cmd=['spacedata', ],
        kpi=[],
    ),
    ROLE_PROBE: dict(
        path=['pdu',],
        service=['dicore', ],
        proc=[],
        cmd=[],
        kpi=[],
    ),
    ROLE_GUI: dict(
        path=[],
        service=['mysql', 'nginx', 'phpfpm', 'clickhouse', 'corosync', 'pacemaker',],
        proc=[],
        cmd=[],
        kpi=[],
    )
}
