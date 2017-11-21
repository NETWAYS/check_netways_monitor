## check_netways_monitor ##

### Description ###

This plugin serves the purpose of getting data from the NETWAYS Monitor and calculating its state.


### Dependencies ###

+ [PySNMP](https://github.com/etingof/pysnmp)
+ [enum34](https://pypi.python.org/pypi/enum34)

### Usage ###

```
check_netways_monitor.py -H -C [-p] [-V] [-v] [-h]
```

#### required arguments: ####

+ **HOSTNAME:** host of the NETWAYS Monitor  
  `` -H, --hostname  ``
+ **COMMUNITY:** read community of the NETWAYS Monitor  
  `` -C, --community ``

#### optional arguments: ####

+ **HELP** show the help message and exit  
  `` -h, --help ``
+ **VERSION** shows the current version of the check plugin  
  `` -V, --version ``
+ **VERBOSE** increases output verbosity (-v or -vv)  
  `` -v, --verbose ``
+ **TIMEOUT** seconds before connection times out (defaults to 10)  
  `` -t, --timeout ``
+ **PORT** SNMP port of the NETWAYS Monitor (defaults to 161)  
  `` -p, --port ``
+ **PHYSICAL-PORT** physical port of the NETWAYS Monitor to check (shows all if not set)  
  `` -P, --physical-port ``
