from PySide2.QtWidgets import QApplication,QWidget,QGridLayout,QCheckBox
from PySide2 import QtGui
from PySide2.QtCore import Qt
from appconfig.appConfigStack import appConfigStack as confStack
from appconfig.appConfigN4d import appConfigN4d
import os
import yaml
import json

import gettext
_ = gettext.gettext

class main(confStack):
	def __init_stack__(self):
		self.dbg=False
		self._debug("Main Stack loaded")
		self.description="Redirect Mirror"
		self.visible=False
		self.enabled=True
		self.level='n4d'
		self.n4d_master=appConfigN4d()
		self.mirror_dir="/net/mirror/llx21"
	#def __init__
	
	def _load_screen(self):
		self._set_server_data()
		box=QGridLayout()
		self.setLayout(box)
		self.chkEnabled=QCheckBox(_("Enable mirror redirection"))
		box.addWidget(self.chkEnabled,0,0,1,1)
		self.updateScreen()
		return(self)
	#def _load_screen

	def updateScreen(self):
		self._set_server_data()
		if self.is_enabled():
			self.chkEnabled.setChecked(True)
	#def _udpate_screen

	def is_enabled(self):
		sw_enabled=False
		self.slave_ip=self._get_replication_ip()
		self._debug("Slave IP: {}".format(self.slave_ip))
		try:
			resp=self.n4dQuery("NfsManager","is_mirror_shared",self.mirror_dir,self.slave_ip,ip=self.master_ip)
			if isinstance(resp,dict):
				if resp.get('status',-1)==0:
					sw_enabled=True
			elif isinstance(resp,str):
				if resp=="Shared is configured":
					sw_enabled=True
		except Exception as e:
			self._debug(e)
			sw_enabled=False
		self._debug("Redirect enabled: {}".format(sw_enabled))
		return(sw_enabled)
	#def is_enabled
	
	def _get_replication_ip(self):
		path="/etc/netplan/30-replication-lliurex.yaml"
		try:
			if os.path.exists(path):
				with open(path,"r") as stream:
					data=yaml.safe_load(stream)
				eth=list(data["network"]["ethernets"].keys())[0]
				return data["network"]["ethernets"][eth]["addresses"][0].split("/")[0]
		except Exception as e:
			print("Failed getting replication IP")
			print(e)
			raise e		
	#def _get_replication_ip
	
	def _set_server_data(self):
		master_ip=self.n4dGetVar(var="MASTER_SERVER_IP")
		self._debug("Get master_ip: {}".format(master_ip))
		self.master_ip=''
		if isinstance(master_ip,dict):
			self.master_ip=master_ip.get('ip','')
		if (self.master_ip):
			self.sw_slave=True
		else:
			master_ip=self.n4dGetVar(var="SRV_IP")
			if isinstance(master_ip,dict):
				self.master_ip=master_ip.get('ip','')
		if self.n4d_master.server=='server' or self.n4d_master.server=='localhost':
			self.n4d_master.server=self.master_ip
	#def _set_server_data
	
	def enable_redirect(self):
		sw_add=False
		status=self.n4d_master.n4dGetVar(client=None,var="LLIUREXMIRROR")
		try:
			status_orig=self.n4dGetVar(var="LLIUREXMIRROR")
		except:
			status_orig={}

		if isinstance(status,dict):
			if status.get("llx21",None):
				if status["llx21"].get('last_mirror_date',None)==None:
					self.showMsg(_("No mirror at master server"))
				else:
					self.n4dQuery("NfsManager","add_mirror",self.mirror_dir,self.slave_ip,ip=self.master_ip)
					try:
						mount_stat=self.n4dQuery("NfsManager","is_mount_configured","{}".format(self.mirror_dir))
						if isinstance(mount_stat,dict):
							if mount_stat.get('status',0)==-1:
								self._debug("Mounting on boot")
								self.n4dQuery("NfsManager","configure_mount_on_boot","{}:{}".format(self.master_ip,self.mirror_dir),"{}".format(self.mirror_dir))
								sw_add=True
						self.n4dSetVar(var="LLIUREXMIRROR",val=status)
						self.n4dSetVar(var="LLIUREXMIRROR_ORIG",val=status_orig)

					except Exception as e:
						print("Add mirror err: {}".format(e))
						self.showMsg(_("Error adding mirror {}".format(e)))
						sw_add=False
			else:
				self.showMsg(_("No mirror at master server"))
		return sw_add
	#def enable_redirect
	
	def disable_redirect(self):
		sw_rm=True
		self.n4dQuery("NfsManager","remove_ip_from_mirror",self.mirror_dir,self.slave_ip,ip=self.master_ip)
		try:
			self.n4dQuery("NfsManager","remove_mount_on_boot",self.mirror_dir)
		except:
			sw_rm=False
		try:
			status_orig=self.n4dGetVar(var="LLIUREXMIRROR_ORIG")
		except:
			status_orig={}
		self.n4dSetVar(var="LLIUREXMIRROR",val=status_orig)
		try:
			self.n4dDelVar(var="LLIUREXMIRROR_ORIG")
		except:
			pass
		return sw_rm
	#def disable_redirect
	
	def writeConfig(self):
		state=self.chkEnabled.isChecked()
		self._debug("State changed to {}".format(state))
		if state:
			self._debug("Redirecting mirror...")
			if not self.enable_redirect():
				self.chkEnabled.setChecked(False)
		else:
			self._debug(_("Disabling mirror redirect..."))
			if not self.disable_redirect():
				self.chkEnabled.setChecked(False)
		self._debug("Done")
	#def writeConfig

