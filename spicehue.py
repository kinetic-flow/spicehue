#!/usr/bin/env python3

from dataclasses import dataclass
import sys
from typing import NamedTuple
import spiceapi
from time import sleep
from phue import Bridge
import colorsys
from configparser import RawConfigParser
import argparse
import time

def config_lamps(hue_bridge, config):
    for hue_lamp in config.options('mapping'):
        lights_raw = config.get('mapping', hue_lamp)
        lights = lights_raw.split(',')
        for light in lights:
            add_lamp_mapping(hue_bridge, hue_lamp, light)
    pass

class LampConfig(NamedTuple):
    r: str
    g: str
    b: str

class LampColor(NamedTuple):
    lamp_id: str
    # 'r', 'g', or 'b'
    rgb: str

@dataclass
class LampStatus():
    r: float = 0.0
    g: float = 0.0
    b: float = 0.0

def connect_hue(bridge_ip):
    b = Bridge(bridge_ip)

    # If the app is not registered and the button is not pressed, press the
    # button and call connect() (this only needs to be run a single time)
    b.connect()

    # Print all hue lamps for convenience
    print('Listing all hue lamps:', end=' ')
    lamps = [lamp.name for lamp in b.lights]
    print(", ".join(lamps))

    return b

def lamps_on_off(bridge, on=True):
    for lamp_id in lamps_in_use.keys():
        bridge.set_light(lamp_id, 'on', on)

lamps_in_use = {}
light_mapping = {}

def add_lamp_mapping(hue_bridge, lamp_name, light):
    print(f'    {light} [R/G/B] => {lamp_name}')

    id = (int)(hue_bridge.get_light_id_by_name(lamp_name))
    if not id:
        return

    lamps_in_use[id] = LampStatus()
    add_to_light_mapping(light + " R", LampColor(id, 'r'))
    add_to_light_mapping(light + " G", LampColor(id, 'g'))
    add_to_light_mapping(light + " B", LampColor(id, 'b'))

def add_to_light_mapping(light, lamp_color):
    if light not in light_mapping:
        light_mapping[light] = []
    light_mapping[light].append(lamp_color)

def connect_spice(host, port, password):
    return spiceapi.Connection(host, port, password)

def update_hue_lamps(hue_bridge, overall_brightness, transition_time):
    for lamp_id, lamp in lamps_in_use.items():
        # print(f'{lamp_id} {lamp}')

        # turn off the lamp for (0, 0, 0)
        if (lamp.r == 0 and lamp.g == 0 and lamp.b == 0):
            # note: transitiontime is in deciseconds (0.1s)
            command = {
                'on': False,
                'transitiontime': transition_time
            }

            hue_bridge.set_light(lamp_id, command)
            continue

        # convert RGB to HSV
        hue, sat, val = colorsys.rgb_to_hsv(lamp.r, lamp.g, lamp.b)

        now = time.time()

        # note: transitiontime is in deciseconds (0.1s)
        command = {
            'on': True,
            'transitiontime': transition_time,
            'hue': int(round(hue * 65535)),
            'sat': int(round(sat * 255)),
            'bri': int(round(val * 255 * (overall_brightness / 100.0)))
        }

        # print(f'{hue} {sat} {val}')
        hue_bridge.set_light(lamp_id, command)

        print(time.time() - now)

    pass

def main():
    print('\nStarting spicehue...')

    parser = argparse.ArgumentParser(description='spicehue')
    parser.add_argument("--config", type=str, default='default.ini')
    args = parser.parse_args()

    print(f'Reading config file {args.config} ...')

    # "Raw" version is used to override optionxform as a workaround to make keys
    # case sensitive
    config = RawConfigParser()
    config.optionxform = lambda option: option

    # read config file
    config.read(args.config)
    spice_host = config.get('spice', 'Host')
    spice_port = config.getint('spice', 'Port')
    spice_pass = config.get('spice', 'Password', fallback='')
    sleep_interval = config.getfloat('misc', 'SleepInterval', fallback=20.0)
    overall_brightness = config.getint('hue', 'Brightness', fallback=100)
    transition_time = config.getint('hue', 'TransitionTime', fallback=1)

    print('Connect to Philips Hue bridge...')
    bridge_ip = config.get('hue', 'BridgeIp')
    hue_bridge = connect_hue(bridge_ip)

    print('Mappings:')
    config_lamps(hue_bridge, config)

    con = None
    print('Start listening over SpiceAPI...')
    try:
        while True:
            lights = []
            try:
                if con is None:
                    print(f'Connect to SpiceAPI... host: {spice_host}, port: {spice_port}')
                    con = connect_spice(spice_host, spice_port, spice_pass)
                    print('Running, press Ctrl+C to stop...')
                if con is not None:
                    lights = spiceapi.lights_read(con)

            except Exception:
                if con is not None:
                    print('Connection error')
                    if config.getboolean('hue', 'LightsOffOnError', fallback='True'):
                        print('Turning lights off...')
                        lamps_on_off(hue_bridge, False)
                    con = None
            finally:
                if con is None:
                    print('Connection failed, retrying in a bit')
                    sleep(5)

            for light in lights:
                light_name = light[0]
                if light_name in light_mapping:
                    lamp_list = light_mapping[light_name]
                    for lamp_color in lamp_list:
                        rgb = lamp_color.rgb
                        lamp_id = lamp_color.lamp_id
                        if rgb == 'r':
                            lamps_in_use[lamp_id].r = light[1]
                        elif rgb == 'g':
                            lamps_in_use[lamp_id].g = light[1]
                        else:
                            lamps_in_use[lamp_id].b = light[1]
                        pass

            if len(lights) > 0:
                update_hue_lamps(hue_bridge, overall_brightness, transition_time)

            sleep(sleep_interval / 1000)
            pass
    
    except KeyboardInterrupt:
        pass

    finally:
        if config.getboolean('hue', 'LightsOffOnExit', fallback='True'):
            print('Turning lights off...')
            lamps_on_off(hue_bridge, False)
        print('Exiting...')

if __name__ == "__main__":
    main()
