import os.path
import os
import numbers
import requests
import subprocess
from pathlib import Path

import psutil

from datetime import datetime

from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS

class Framboesa:
    def __init__(self, org, bucket, token):
        # You can generate a Token from the "Tokens Tab" in the UI
        self.token = token
        self.client = InfluxDBClient(url="http://framboesa:8086", token=token)
        self.org = org
        self.bucket = bucket
    
    def get_value(self, query):
        tables = self.client.query_api().query(query, org = self.org)
        # get first record
        for table in tables:
            for record in table.records:
                return record["_value"]

    def get_cpu_temperature(self):
        thermals = psutil.sensors_temperatures()
        if "coretemp" in thermals:
            val = psutil.sensors_temperatures()['coretemp'][0].current
        elif "cpu_thermal" in thermals:
            val = psutil.sensors_temperatures()['cpu_thermal'][0].current
        return '**CPU\'s temperature** is {}ºC'.format(round(val, 1))

    def query(self, measurement, field):
        return """from(bucket: "{}")
          |> range(start: -{})
          |> filter(fn: (r) => r["_measurement"] == "{}")
          |> filter(fn: (r) => r["_field"] == "{}")
          |> last()
          |> yield(name: "last")""".format(self.bucket, '6h', measurement, field)

    def query2(self, measurement, field):
        query = """from(bucket: "{}")
          |> range(start: {})
          |> filter(fn: (r) => r["_measurement"] == "{}")
          |> filter(fn: (r) => r["_field"] == "{}")
          |> increase()
          |> last()
          |> yield(name: "last")""".format(self.bucket, "6h", measurement, field)
    
    def get_query2(self, measurement, field, unit):
        query = self.query(measurement, field)
        val = self.get_value(query)
        return {'value': val, 'unit': unit}
    
    def get_blocked(self): return self.get_query2('pihole', 'ads_blocked_today', 'unit')
    def get_miss(self): return self.get_query2('unbound', 'total_num_cachemiss', 'unit')
    def get_unbound_cache(self): return self.get_query2('unbound', 'total_num_cachehits', 'unit')
    def get_pihole_cache(self): return self.get_query2('pihole', 'queries_cached', 'unit')
    
    def get_unbound(self):
        hits = 0
        miss = 0
        blocked = 0
        try:
            hits = self.get_unbound_cache()["value"] + self.get_pihole_cache()["value"]
        except:
            pass
        try:
            miss = self.get_miss()["value"]
        except:
            pass
        try:
            blocked = self.get_blocked()["value"]
        except:
            pass
        
        message = ["**DNS** *(last 6 hours)*", 
                   "- {0: .1f}%  -- {2: 5d} : Cache",
                   "- {5: .1f}%  -- {4: 5d} : Blocked",
                   "- {1: .1f}%  -- {3: 5d} : External requests"]
        
        hits_pct = 0
        miss_pct = 0
        blocked_pct = 0
        try:
            hits_pct = round(hits / (hits + miss + blocked) * 100, 1)
        except:
            pass
        try:
            miss_pct = round(hits / (hits + miss + blocked) * 100, 1)
        except:
            pass
        try:
            blocked_pct = round(blocked / (hits + miss + blocked) * 100, 1)
        except:
            pass

        return "\n".join(message).format(
            hits_pct,
            miss_pct,
            round(hits),
            round(miss),
            round(blocked) if blocked is not None else 0,
            blocked_pct
        )
    def get_temperature(self):
        query = self.query('sensors', 'temperature')
        val = self.get_value(query)
        return {'value': val, 'unit': 'ºC'}
    
    def get_humidity(self):
        query = self.query('sensors', 'humidity')
        val = self.get_value(query)
        return {'value': val, 'unit': 'Relative %'}
    
    def get_wifi(self):
        try:
            wifi = subprocess.run(['iwgetid', 'wlan1', '-r'], text = True, capture_output = True).stdout.strip()
            bitrate = ''
            with open('/proc/net/wireless', 'r') as f:
                for line in f.readlines():
                    if 'wlan1' in line:
                        bitrate = line.split()[2:4]
                        bitrate = 'quality: ' + bitrate[0] + ' signal: ' + bitrate[1] + 'dBm'

            ch = subprocess.run(['iwgetid', 'wlan1', '-c', '-r'], text = True, capture_output = True).stdout.strip()
            return "**Wifi** is connected to '{}' (channel: {} {})".format(wifi, ch, bitrate)
        except:
            return "**Wifi** is not supported"

    def get_load(self):
        load = os.getloadavg()
        return "**Load**\n- {0} _(1min)_\n- {1} _(5min)_\n- {2} _(15min)_".format(load[0], load[1], load[2])

    def get_info(self):
        t = self.get_temperature()
        h = self.get_humidity()
        return "\n".join(
            ["",
             "**Framboesa summary**",
             "",
             "**Sensors**:",
             "- Relative humidity: {}%",
             "- Temperature: {}ºC",
             "",
             "{}",
             "",
             "{}",
             "",
             "{}",
             "",
             "{}"]
        ).format(
            round(h['value'], 1), 
            round(t['value'], 1), 
            self.get_wifi(), 
            self.get_cpu_temperature(), 
            self.get_load(), 
            self.get_unbound()
        )

