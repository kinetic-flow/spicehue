# spicehue

Allows games to control Philips Hue RGB LED lamps over SpiceAPI.

## Instructions

Modify default.ini file and fill in the values.

Ensure SpiceAPI server has been started.

Press the large button on the Hue Bridge (to ensure script has access) - only need to do this once.

Launch spicehue.py.

## Disclaimers

Please use caution if you are sensitive to flashing lights.

I will provide no support for this software, and I am not responsible for any possible damage to your hardware (networking equipment, Hue Bridge, Hue lamps).

Hue API isn't really designed for low latency or rapidly changing colors / brightness. Not every transition will look good; you'll have to experiment.

## Advanced usage

Instead of default.ini, you can specify a different INI file with --config flag.

## Build Dependencies

Depends on [phue, a Python library for Philips Hue](https://github.com/studioimaginaire/phue).

Requires SpiceAPI Python files in the path (not provided).

## License

MIT License; see LICENSE file.

"Hue Personal Wireless Lighting" is a trademark owned by Koninklijke Philips Electronics N.V., see www.meethue.com for more information. This project is in no way affiliated with  Philips.
