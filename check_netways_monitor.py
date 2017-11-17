#!/usr/bin/env python

# ------------------------------------------------------------------------------
# check_netways_monitor.py - A check plugin for the NETWAYS Monitor.
# Copyright (C) 2017  NETWAYS GmbH, www.netways.de
# Authors: Noah Hilverling <noah.hilverling@netways.de>
#
# Version: 1.0
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
# ------------------------------------------------------------------------------

import argparse
import sys
from pysnmp.entity.rfc3413.oneliner import cmdgen
from enum import Enum, IntEnum


# Translate the OID indexes to keywords
class DataTypes(IntEnum):
    PHYSICAL_INDEX = 1
    TYPE = 2
    SCALE = 3
    PRECISION = 4
    VALUE = 5
    SENSOR_STATUS = 6
    UNITS_DISPLAY = 7
    TIME_STAMP = 8
    UPDATE_RATE = 9
    NAME = 10
    WARNING_MIN = 11
    WARNING_MAX = 12
    CRITICAL_MIN = 13
    CRITICAL_MAX = 14
    STATE = 15
    SHOULD_BE_CHECKED = 16


# Translate the Nagios state IDs to keywords
class NagiosState(Enum):
    OK = 0
    WARNING = 1
    CRITICAL = 2
    UNKNOWN = 3


# Display a one line status message with:
#   - most important Nagios state and short message
#   - number and name of the sensors in any state but OK
#   - thresholds of the sensors
def print_status_message(sensor_states, perf_data):
    warning_name_string = ""
    for name in sensor_states[NagiosState.WARNING]:
        if warning_name_string:
            warning_name_string += ", "
        warning_name_string += name

    critical_name_string = ""
    for name in sensor_states[NagiosState.CRITICAL]:
        if critical_name_string:
            critical_name_string += ", "
        critical_name_string += name

    result_message = ""
    if len(sensor_states[NagiosState.WARNING]) > 0 and len(sensor_states[NagiosState.CRITICAL]) > 0:
        result_message = "CRITICAL NETWAYS Monitor: Sensor reports state CRITICAL for %d sensor%s (%s) " \
                "and state WARNING for %d sensor%s (%s)" % (
                    len(sensor_states[NagiosState.CRITICAL]),
                    "s" if len(sensor_states[NagiosState.CRITICAL]) > 1 else "",
                    critical_name_string,
                    len(sensor_states[NagiosState.WARNING]),
                    "s" if len(sensor_states[NagiosState.WARNING]) > 1 else "",
                    warning_name_string
                )
    elif len(sensor_states[NagiosState.WARNING]) > 0:
        result_message = "WARNING NETWAYS Monitor: Sensor reports state WARNING for %d sensor%s (%s)" % (
            len(sensor_states[NagiosState.WARNING]), "s" if len(sensor_states[NagiosState.WARNING]) > 1 else "", warning_name_string)
    elif len(sensor_states[NagiosState.CRITICAL]) > 0:
        result_message = "CRITICAL NETWAYS Monitor: Sensor reports state CRITICAL for %d sensor%s (%s)" % (
            len(sensor_states[NagiosState.CRITICAL]), "s" if len(sensor_states[NagiosState.CRITICAL]) > 1 else "", critical_name_string)
    else:
        result_message = "OK NETWAYS Monitor: Sensor reports that everything is fine"

    # Add the performance data to the end of the first output line
    result_message += "|"
    for singlePerfData in perf_data:
        result_message += singlePerfData + " "

    # Print summary and performance data
    print result_message


# Version number
version = 1.0

# Initialise variables
verbose = 0
hostname = ""
community = ""
timeout = 10
port = 161
physicalPort = 0

# Arguments for the CLI command
parser = argparse.ArgumentParser(description='Check plugin for the NETWAYS Monitor')
parser.add_argument("-V", "--version", action="store_true")
parser.add_argument("-v", "--verbose", action="count", default=0, help="increase output verbosity (-v or -vv)")
parser.add_argument("-t", "--timeout", help="seconds before connection times out (defaults to 10)", type=float, default=10)
parser.add_argument("-p", "--port", help="SNMP port of the NETWAYS Monitor (defaults to 161)", type=int, default=161)
parser.add_argument("-P", "--physical-port", help="physical port of the NETWAYS Monitor to check (shows all if not set)", type=int, default=0)
required = parser.add_argument_group('required arguments')
required.add_argument("-H", "--hostname", help="host of the NETWAYS Monitor", required=True)
required.add_argument("-C", "--community", help="read community of the sensor probe", required=True)

args = parser.parse_args()

# Print version if version argument is given
if args.version:
    print "Check NETWAYS Monitor Version %s" % version
    sys.exit()
else:
    # Assert arguments to their variables
    verbose = args.verbose if args.verbose <= 2 else 2
    hostname = args.hostname
    community = args.community
    timeout = args.timeout
    port = args.port
    physicalPort = args.physical_port

# The state with the highest importance (CRITICAL -> WARNING -> OK)
mostImportantState = NagiosState.OK

# Array of messages to print after first line if verbose
stateMessages = []

# Performance data for each sensor as string
perfData = []

# Root for sensor dictionary tree
sensors = {}

# Root for sensor OIDs
sensorsOID = (1, 3, 6, 1, 4, 1, 26840, 254, 1, 1, 1, 1)

generator = cmdgen.CommandGenerator()
communityData = cmdgen.CommunityData(community)
transport = cmdgen.UdpTransportTarget((hostname, port), timeout=timeout, retries=0)
command = getattr(generator, 'nextCmd')

errorIndication, errorStatus, errorIndex, result = command(communityData, transport, sensorsOID)

# Check if an exception occurred
if errorIndication:
    print "%s NETWAYS Monitor: %s" % (NagiosState.UNKNOWN.name, errorIndication)
    mostImportantState = NagiosState.UNKNOWN
elif errorStatus:
    print('%s NETWAYS Monitor: %s at %s' % (NagiosState.CRITICAL.name,
                                             errorStatus.prettyPrint(),
                                             errorIndex and result[int(errorIndex)-1] or '?'))
    mostImportantState = NagiosState.CRITICAL
else:
    # Sort results
    for data in result:
        dataType = int(data[0][0][12])
        sensor = int(data[0][0][13])
        value = data[0][1]

        # Add needed dictionaries if not yet existing
        if sensor not in sensors:
            sensors[sensor] = {}

        # Cast to float and cut decimals
        if dataType > 10:
            value = float(str(value).strip("\x00"))

        # Translate virtual ports (1-8) to physical ports (1-4)
        if dataType == DataTypes.PHYSICAL_INDEX and value > 4:
            value -= 4

        # Store data in dictionary tree
        sensors[sensor][dataType] = value

    sensorCount = 0

    # Check which sensors should be checked and count them
    for sensor, data in sensors.iteritems():
        data[DataTypes.SHOULD_BE_CHECKED] = 0
        if data[DataTypes.SENSOR_STATUS] == 1:
            if physicalPort == 0 or data[DataTypes.PHYSICAL_INDEX] == physicalPort:
                sensorCount += 1
                data[DataTypes.SHOULD_BE_CHECKED] = 1

    # Check if there is no sensor on the given port
    if sensorCount < 1:
        print "%s NETWAYS Monitor: There is no sensor on the given port" % NagiosState.UNKNOWN.name
        sys.exit(NagiosState.UNKNOWN.value)

    # Sensor names sorted by state
    states = {NagiosState.OK: [], NagiosState.WARNING: [], NagiosState.CRITICAL: []}

    # Calculate state
    for sensor, data in sensors.iteritems():
        if not data[DataTypes.SHOULD_BE_CHECKED]:
            continue

        # Convert VALUE according to SCALE
        data[DataTypes.VALUE] = float(data[DataTypes.VALUE]) * 1000 ** (float(data[DataTypes.SCALE])-9)

        data[DataTypes.STATE] = NagiosState.OK

        # State WARNING
        if data[DataTypes.VALUE] < data[DataTypes.WARNING_MIN] or data[DataTypes.VALUE] > data[DataTypes.WARNING_MAX]:
            data[DataTypes.STATE] = NagiosState.WARNING

        # State CRITICAL
        if data[DataTypes.VALUE] < data[DataTypes.CRITICAL_MIN] or data[DataTypes.VALUE] > data[DataTypes.CRITICAL_MAX]:
            data[DataTypes.STATE] = NagiosState.CRITICAL

        # Override most important state
        if data[DataTypes.STATE].value > mostImportantState.value:
            mostImportantState = data[DataTypes.STATE]

        # Add sensor name to its state dictionary
        states[data[DataTypes.STATE]].append(data[DataTypes.NAME])

        # Status message for sensor
        stateMessage = '%s sensor "%s": %s %s' % (data[DataTypes.STATE].name,
                                                    data[DataTypes.NAME],
                                                    data[DataTypes.VALUE],
                                                    data[DataTypes.UNITS_DISPLAY])

        # Add thresholds to verbose sensor messages
        if verbose > 1:
            stateMessage += " (%s:%s/%s:%s)" % (data[DataTypes.WARNING_MIN],
                                                data[DataTypes.WARNING_MAX],
                                                data[DataTypes.CRITICAL_MIN],
                                                data[DataTypes.CRITICAL_MAX])

        stateMessages.append(stateMessage)

        # Add performance data to performance data array
        perfData.append("'%s_%s'=%s;%s:%s;%s:%s" % (str(data[DataTypes.NAME]).replace(" ", "_"),
                                                   data[DataTypes.UNITS_DISPLAY],
                                                   data[DataTypes.VALUE],
                                                   data[DataTypes.WARNING_MIN],
                                                   data[DataTypes.WARNING_MAX],
                                                   data[DataTypes.CRITICAL_MIN],
                                                   data[DataTypes.CRITICAL_MAX]))

    # Print first line of output
    print_status_message(states, perfData)

    # Add additional information for each sensor to the output if verbose
    if verbose > 0:
        for message in stateMessages:
            print message

# Exit with most important state
sys.exit(mostImportantState.value)
