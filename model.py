# -*- coding: utf-8 -*-


"""Database schema reflection"""
from sqlalchemy import Column, Integer, String, Enum
from sqlalchemy.ext.declarative import declarative_base

__author__ = "Andrey Kashrin <kas@sysqual.net>"
__copyright__ = "Copyright (C) 2018 by SysQual, LLC"
__license__ = "proprietary"


'''
   Configuration
'''

config = 'config'
sysdata = 'sys_data'
DBase = declarative_base()

print("Deprecate structure Cfg_Node" )
role_status = ("on", "off", "pending on", "pending off")


class CfgNode(DBase):
    """cfg_nodes table"""
    __tablename__ = 'cfg_nodes'
    __table_args__ = {'schema': config}
    id = Column(Integer, primary_key=True, autoincrement=True)
    address = Column(String(15), nullable=False)
    probe = Column(Enum(*role_status), default='off')
    gui = Column(Enum(*role_status), default='off')
    db_data = Column(Enum(*role_status), default='off')

    def __repr__(self):
        return "<Node('{}')>".format(self.address)

