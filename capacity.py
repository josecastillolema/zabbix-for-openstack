#!/usr/bin/python

import os
import time
import re
import subprocess
from pprint import pprint
import json

import requests
import xml.etree.ElementTree

plataform = 'OS_VCP_AUREK'
ip = '10.10.10.10'
url_cap = 'http://x.y.z.w/capacity'
url_perf = 'http://x.y.z.w:5123/performance'
computes = ['srv1','srv2','srv3','srv4','srv5','srv6','srv7','srv9','srv11','srv13','srv14','srv15','hrv2','hrv3','hrv4']

def collect_data():

  namespaces = [ int(subprocess.check_output("ssh ctr%s 'sudo ip netns ls|wc -l'"%i, shell=True).strip()) for i in range(1, 4)]
  s = subprocess.check_output("openstack hypervisor stats show", shell=True).strip()
  r = re.findall(r'\w+', s)
  ips_used = int(subprocess.check_output("openstack floating ip list | wc -l", shell=True).strip())-4
  os_routers = int(subprocess.check_output("openstack router list | wc -l", shell=True).strip())-4
  os_volumes_inuse = int(subprocess.check_output("openstack volume list --all-projects | grep in-use | wc -l", shell=True).strip())
  os_volumes_maintenance = int(subprocess.check_output("openstack volume list --all-projects | grep maintenance | wc -l", shell=True).strip())
  os_volumes_available = int(subprocess.check_output("openstack volume list --all-projects | grep available | wc -l", shell=True).strip())
  os_snapshots = int(subprocess.check_output("openstack volume snapshot list --all-projects | wc -l", shell=True).strip())-4
  ceph_stats = json.loads(subprocess.check_output("ssh ctr1 'sudo ceph -s --format json'", shell=True))

  ips_total = X
  response = requests.get(url_cap)
  cap = response.json()
  response = requests.get(url_perf)
  perf = True
  try:
    perf = response.json()
    for k in perf.keys():
      if k.find('KbPerSecond') > 0:
          perf[k.replace('KbPerSecond', 'Bandwidth')] = int(perf[k])*1000
  except:
    print 'sem performance'
    perf = False

  hosts_total = int(r[3])
  vms_total = int(r[21])
  mem_total = int(r[17])*1024*1024
  mem_allocated = int(r[19])*1024*1024
  mem_used = 0 
  for compute in computes:
    ma = subprocess.check_output("ssh " + compute + " free -h", shell=True).split()[8][:-1]
    try:
       mem_used += int(ma)
    except:
       mem_used += int(float(ma.replace(',','.')))
  mem_used = mem_used*1024*1024*1024
  mem_available = int(r[11])*1024*1024
  cores_total = int(r[23])*10
  cores_used = int(r[25])
  cores_available = cores_total-cores_used

  disk_available = int(cap['freeSpace'][:-6])/1024
  disk_used = int(cap['usedSpace'][:-6])/1024
  disk_allocated = int(cap['allocatedSpace'][:-6])/1024
  disk_total = int(cap['availableSpace'][:-6])/1024

  hypervisors = subprocess.check_output("openstack compute service list | grep nova-compute | grep -v disabled | awk {' print $6 '}", shell=True).split()
  #hypervisors = re.findall(r'\w+', hypervisors)
  l = []
  #print hypervisors
  for hypervisor in hypervisors:
    #print hypervisor
    try:
      s = subprocess.check_output("openstack hypervisor show %s | grep load_average" % hypervisor, shell=True).strip()
      r = re.findall(r'\w+', s)
      #print 'load.max:', s
      #print r
      f = float(r[1]+'.'+r[2])
      l.append(f)
    except:
      print 'hypervisor %s nao responde' % hypervisor

  print l
  l_min = min(l)
  l_max = max(l)
  l_avg = sum(l) / len(l)

  print 'load.min:', l_min
  print 'load.max:', l_max
  print 'load.avg:', l_avg

  print 'hosts.total:', hosts_total
  print 'vms.total:', vms_total
  print 'mem.total:', mem_total
  print 'mem.used:', mem_used
  print 'mem.available:', mem_available
  print 'mem.allocated:', mem_allocated
  print 'disk.total:', disk_total
  print 'disk.used:', disk_used
  print 'disk.available: ', disk_available
  print 'disk.allocated:', disk_allocated
  print 'cores.avalilable:', cores_available
  print 'cores.total:', cores_total
  print 'cores.useid:', cores_used

  print 'ips.used:', ips_used
  print 'ips.total:', ips_total
  print 'os.routers:', os_routers
  print 'os.volumes_inuse:', os_volumes_inuse
  print 'os.volumes.maintenance:', os_volumes_maintenance
  print 'os.volume.available:', os_volumes_available
  print 'os.snapshots', os_snapshots

  os.popen("zabbix_sender -vv -z %s -p 10051 -s '%s' -k 'capacity.openstack.hosts[total]' -o %s" %  (ip,plataform,hosts_total))
  os.popen("zabbix_sender -vv -z %s -p 10051 -s '%s' -k 'capacity.openstack.vms[total]' -o %s" %  (ip,plataform,vms_total))

  os.popen("zabbix_sender -vv -z %s -p 10051 -s '%s' -k 'capacity.openstack.mem[total]' -o %s" %  (ip,plataform,mem_total))
  os.popen("zabbix_sender -vv -z %s -p 10051 -s '%s' -k 'capacity.openstack.mem[allocated]' -o %s" %  (ip,plataform,mem_allocated))
  os.popen("zabbix_sender -vv -z %s -p 10051 -s '%s' -k 'capacity.openstack.mem[available]' -o %s" %  (ip,plataform,mem_available))
  os.popen("zabbix_sender -vv -z %s -p 10051 -s '%s' -k 'capacity.openstack.mem[used]' -o %s" %  (ip,plataform,mem_used))

  os.popen("zabbix_sender -vv -z %s -p 10051 -s '%s' -k 'capacity.openstack.disk[total]' -o %s" %  (ip,plataform,disk_total))
  os.popen("zabbix_sender -vv -z %s -p 10051 -s '%s' -k 'capacity.openstack.disk[used]' -o %s" %  (ip,plataform,disk_used))
  os.popen("zabbix_sender -vv -z %s -p 10051 -s '%s' -k 'capacity.openstack.disk[available]' -o %s" %  (ip,plataform,disk_available))
  os.popen("zabbix_sender -vv -z %s -p 10051 -s '%s' -k 'capacity.openstack.disk[allocated]' -o %s" %  (ip,plataform,disk_allocated))

  os.popen("zabbix_sender -vv -z %s -p 10051 -s '%s' -k 'capacity.openstack.cpucores[total]' -o %s" %  (ip,plataform,cores_total))
  os.popen("zabbix_sender -vv -z %s -p 10051 -s '%s' -k 'capacity.openstack.cpucores[used]' -o %s" %  (ip,plataform,cores_used))
  os.popen("zabbix_sender -vv -z %s -p 10051 -s '%s' -k 'capacity.openstack.cpucores[available]' -o %s" %  (ip,plataform,cores_available))

  os.popen("zabbix_sender -vv -z %s -p 10051 -s '%s' -k 'capacity.openstack.floatingips[total]' -o %s" %  (ip,plataform,ips_total))
  os.popen("zabbix_sender -vv -z %s -p 10051 -s '%s' -k 'capacity.openstack.floatingips[used]' -o %s" %  (ip,plataform,ips_used))

  os.popen("zabbix_sender -vv -z %s -p 10051 -s '%s' -k 'capacity.openstack.virtualrouters' -o %s" %  (ip,plataform,os_routers))
  os.popen("zabbix_sender -vv -z %s -p 10051 -s '%s' -k 'capacity.openstack.volumes[inuse]' -o %s" %  (ip,plataform,os_volumes_inuse))
  os.popen("zabbix_sender -vv -z %s -p 10051 -s '%s' -k 'capacity.openstack.volumes[maintenance]' -o %s" %  (ip,plataform,os_volumes_maintenance))
  os.popen("zabbix_sender -vv -z %s -p 10051 -s '%s' -k 'capacity.openstack.volumes[available]' -o %s" %  (ip,plataform,os_volumes_available))
  os.popen("zabbix_sender -vv -z %s -p 10051 -s '%s' -k 'capacity.openstack.snapshots' -o %s" %  (ip,plataform,os_snapshots))

  os.popen("zabbix_sender -vv -z %s -p 10051 -s '%s' -k 'capacity.openstack.pcpu[avg]' -o %.2f" %  (ip,plataform,l_avg))
  os.popen("zabbix_sender -vv -z %s -p 10051 -s '%s' -k 'capacity.openstack.pcpu[min]' -o %s" %  (ip,plataform,l_min))
  os.popen("zabbix_sender -vv -z %s -p 10051 -s '%s' -k 'capacity.openstack.pcpu[max]' -o %s" %  (ip,plataform,l_max))

  os.popen("zabbix_sender -vv -z %s -p 10051 -s '%s' -k 'capacity.openstack.namespaces[1]' -o %.2f" %  (ip,plataform,namespaces[0]))
  os.popen("zabbix_sender -vv -z %s -p 10051 -s '%s' -k 'capacity.openstack.namespaces[2]' -o %.2f" %  (ip,plataform,namespaces[1]))
  os.popen("zabbix_sender -vv -z %s -p 10051 -s '%s' -k 'capacity.openstack.namespaces[3]' -o %.2f" %  (ip,plataform,namespaces[2]))

  if perf:
   for e in ['front','back']:
    for d in ['Read','Write']:
      for m in ['Iops','Bandwidth','LatencyAvg','LatencyMax']:
        try:
           if m in ['LatencyAvg', 'LatencyMax']:
              v = float(perf['{e}End{d}{m}'.format(e = e, d = d, m = m)])/100.
           else:
              v = perf['{e}End{d}{m}'.format(e = e, d = d, m = m)]
           os.popen("zabbix_sender -vv -z {i} -p 10051 -s '{p}' -k 'capacity.openstack.disk[{e}End{d}{m}]' -o {v}".format(
                   i = ip, p = plataform, e = e, d = d, m = m, v=v))
           print e, d, m, v
        except:
           print 'Error sending {e}End{d}{m}'.format(e = e, d = d, m = m)

  os.popen("zabbix_sender -vv -z %s -p 10051 -s '%s' -k 'capacity.openstack.ceph[total]' -o %s" %  (ip,plataform,ceph_stats['pgmap']['bytes_total']))
  os.popen("zabbix_sender -vv -z %s -p 10051 -s '%s' -k 'capacity.openstack.ceph[used]' -o %s" %  (ip,plataform,ceph_stats['pgmap']['bytes_used']))
  if ceph_stats['pgmap'].has_key('read_bytes_sec'):
    os.popen("zabbix_sender -vv -z %s -p 10051 -s '%s' -k 'capacity.openstack.ceph[readBandwidth]' -o %s" %  (ip,plataform,ceph_stats['pgmap']['read_bytes_sec']))
  else:
    os.popen("zabbix_sender -vv -z %s -p 10051 -s '%s' -k 'capacity.openstack.ceph[readBandwidth]' -o %s" %  (ip,plataform,0))
  if ceph_stats['pgmap'].has_key('write_bytes_sec'):
    os.popen("zabbix_sender -vv -z %s -p 10051 -s '%s' -k 'capacity.openstack.ceph[writeBandwidth]' -o %s" %  (ip,plataform,ceph_stats['pgmap']['write_bytes_sec']))
  else:
    os.popen("zabbix_sender -vv -z %s -p 10051 -s '%s' -k 'capacity.openstack.ceph[writeBandwidth]' -o %s" %  (ip,plataform,0))
  if ceph_stats['pgmap'].has_key('op_per_sec'):
    os.popen("zabbix_sender -vv -z %s -p 10051 -s '%s' -k 'capacity.openstack.ceph[iops]' -o %s" %  (ip,plataform,ceph_stats['pgmap']['op_per_sec']))
  else:
    os.popen("zabbix_sender -vv -z %s -p 10051 -s '%s' -k 'capacity.openstack.ceph[iops]' -o %s" %  (ip,plataform,0))

def main():
  collect_data()

if __name__ == '__main__':
  main()
