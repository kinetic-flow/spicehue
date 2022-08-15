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

def config_lamps(config):
    for hue_lamp in config.options('mapping'):
        lights_raw = config.get('mapping', hue_lamp)
        lights = lights_raw.split(',')
        for light in lights:
            add_lamp_mapping(hue_lamp, light)
    pass

class LampConfig(NamedTuple):
    r: str
    g: str
    b: str

class LampColor(NamedTuple):
    name: str
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

def get_hue_lamps(bridge):
    hue_lamps = {}
    for lamp_name in lamps_in_use.keys():
        hue_lamp = bridge.get_light(lamp_name)
        if 'name' not in hue_lamp or hue_lamp['name'] != lamp_name:
             raise Exception(f'hue lamp with name {lamp_name} not found')
        hue_lamps[lamp_name] = bridge.get_light(lamp_name)

    return hue_lamps

def lamps_on_off(bridge, hue_lamps, on=True):
    for lamp_name in hue_lamps.keys():
        bridge.set_light(lamp_name, 'on', on)

lamps_in_use = {}
light_mapping = {}

def add_lamp_mapping(lamp_name, light):
    print(f'    {light} [R/G/B] => {lamp_name}')
    lamps_in_use[lamp_name] = LampStatus()
    add_to_light_mapping(light + " R", LampColor(lamp_name, 'r'))
    add_to_light_mapping(light + " G", LampColor(lamp_name, 'g'))
    add_to_light_mapping(light + " B", LampColor(lamp_name, 'b'))

def add_to_light_mapping(light, lamp_color):
    if light not in light_mapping:
        light_mapping[light] = []
    light_mapping[light].append(lamp_color)

def connect_spice(host, port, password):
    return spiceapi.Connection(host, port, password)

def update_hue_lamps(hue_bridge, overall_brightness, transition_time):
    for lamp_name, lamp in lamps_in_use.items():
        # print(f'{lamp_name} {lamp}')

        # turn off the lamp for (0, 0, 0)
        if (lamp.r == 0 and lamp.g == 0 and lamp.b == 0):
            # note: transitiontime is in deciseconds (0.1s)
            command = {
                'on': False,
                'transitiontime': transition_time
            }

            hue_bridge.set_light(lamp_name, command)
            continue

        # convert RGB to HSV
        hue, sat, val = colorsys.rgb_to_hsv(lamp.r, lamp.g, lamp.b)

        # note: transitiontime is in deciseconds (0.1s)
        command = {
            'on': True,
            'transitiontime': transition_time,
            'hue': int(round(hue * 65535)),
            'sat': int(round(sat * 255)),
            'bri': int(round(val * 255 * (overall_brightness / 100.0)))
        }

        # print(f'{hue} {sat} {val}')
        hue_bridge.set_light(lamp_name, command)
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
    config_lamps(config)
    hue_lamps = get_hue_lamps(hue_bridge)
    if len(hue_lamps) == 0:
        print('ERROR: no mappings are specified, update the INI file and try again')
        exit()

    if config.getboolean('hue', 'LightsOn', fallback='True'):
        print('Turning lights on...')
        lamps_on_off(hue_bridge, hue_lamps)

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
                        lamp_name = lamp_color.name
                        if rgb == 'r':
                            lamps_in_use[lamp_name].r = light[1]
                        elif rgb == 'g':
                            lamps_in_use[lamp_name].g = light[1]
                        else:
                            lamps_in_use[lamp_name].b = light[1]
                        pass

            if len(lights) > 0:
                update_hue_lamps(hue_bridge, overall_brightness, transition_time)

            sleep(sleep_interval / 1000)
            pass
    
    except KeyboardInterrupt:
        pass

    finally:
        if config.getboolean('hue', 'LightsOff', fallback='True'):
            print('Turning lights off...')
            lamps_on_off(hue_bridge, hue_lamps, False)
        print('Exiting...')

if __name__ == "__main__":
    main()
