#!/usr/bin/python
# -*- coding: utf-8 -*-
# cups backend to switch on GEMBIRD SIS-PM outlet before printing and switch off after some time
# based on mailto beckend by Robert Sander <robert.sander@epigenomics.com>
# (C) 2015 Thomas Malcher
# Released under GPL
# NO WARRANTY AT ALL
#

import sys, os, syslog, subprocess
import time
import signal
import atexit

def error(message):
    #syslog.syslog(syslog.LOG_ERR, message)
    sys.stderr.write("ALERT: "+message+"\n")
def debug(message):
    #syslog.syslog(syslog.LOG_DEBUG, message)
    sys.stderr.write("DEBUG: "+message+"\n")

argc = len(sys.argv)
pidfile = "/run/sispmctl_turnoff.pid"
atexit.register(syslog.closelog)
syslog.openlog('sispmctl_printer', syslog.LOG_PID, syslog.LOG_LPR)

debug("sispmctl argv[%s] = '%s'" % (argc, "', '".join(sys.argv)))

if argc == 1:
    print "direct sispmctl \"Unknown\" \"SISPMCTL\""
    sys.exit(0)

if argc < 6 or argc > 7:
    error("ERROR: %s job-id user title copies options [file]" % sys.argv[0])
    sys.exit(1)

jobid = sys.argv[1]
user = sys.argv[2]
title = sys.argv[3]
copies = sys.argv[4]
opts = sys.argv[5]

deviceuri = os.environ['DEVICE_URI']
debug("INFO: Deviceuri:" + deviceuri)
try:
	if argc == 7:
		  infilename = sys.argv[6]
		  debug("INFO: file is "+infilename)
	else:
			infilename = os.tempnam()
			with open(infilename, "w") as infile:
				infile.write(sys.stdin.read())
			debug("INFO: copied stdin to tmp file " + infilename)
	#decode outlet number
	switchnr = None
	if type(deviceuri) == str and deviceuri.startswith("sispmctl://"):
		  nested_uri_idx = deviceuri.find("/", 11)
		  if nested_uri_idx < 0:
		    error("wrong URI format, could not find nested original URI "+deviceuri)
		    sys.exit(1)
		  switchnr = str(int(deviceuri[11:nested_uri_idx]))
		  deviceuri = deviceuri[nested_uri_idx+1:]
		  debug("decoded original deviceuri " + deviceuri)
	else:
		  debug("search for number of outlet in options")
		  for opt in opts.split(" "):
		    if opt[:9] == "switchnr=":
			  	switchnr = str(int(opt[9:]))
			  	debug("switch outlet number " + switchnr)
	if not switchnr:
		error("was not able to decode outlet number")
		sys.exit(1)
	#check if turnoff process is already running, if so stop it 
	if os.path.exists(pidfile):
		debug("turnoff process already running -> stop it")
		try:
			with open(pidfile,"r") as f:
				tpid = f.readline(10)
			os.kill(int(tpid), signal.SIGTERM)
		except Exception as e:
			os.remove(pidfile)
			error("ERROR was not able to kill turnoff process: "+str(e))
	#turn the outlet for the printer on
	subprocess.check_call(["/usr/bin/sispmctl","-o",str(switchnr)])
	debug("outlet number "+str(switchnr)+" switched on")
	time.sleep(10)
	#call the original backend
	i = deviceuri.find(":")
	backend = "/usr/lib/cups/backend/"+deviceuri[:i]
	debug("orig backend " + backend)
	os.environ['DEVICE_URI'] = deviceuri
	title = "\""+title+"\""
	options = "\""+opts+"\""
	orig_backend_command = [backend,jobid,user,title,copies,options,infilename]
	debug("execute backend %s" % " ".join(command))
	subprocess.check_call(command)
	debug("usb backend ist fertig")
	#start turnoff process
	subprocess.check_call(['/usr/lib/cups/backend/sispmctl_turnoff.py',str(switchnr)])
	debug("turnoff started")
	sys.exit(0)
except Exception as e:
	error(str(e))
	sys.exit(1)




