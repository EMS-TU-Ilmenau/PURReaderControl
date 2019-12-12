# PUR Reader Control
Python interface to control PUR UHF RFID readers

## Description
Works with USB desktop readers like the [PUR-Dongle-100U](http://www.rf-embedded.eu/Reader/PUR-Dongle-100U-OEM-eng.html). 

**Note:** currently, not all features are implemented.

## Getting started
1. Install all necessary drivers from the reader manufacturer
2. Clone and `cd` into this repository and 
    - either run `python test.py` locally to test, 
    - or [install](https://packaging.python.org/tutorials/installing-packages/) this package via `pip install .` to use it globally

**Example**
```python
from purreader import PURReader

# connect to reader
reader = PURReader('COM7')

# set some settings temporarly (unplug from power to reset)
# these are actually default though
reader.freqKHz = [865700, 866900, 867500, 866300] # hop randomly on ETSI frequencies
reader.blfKHz = 160 # tag backscatter link frequency
reader.encoding = 'M2' # or FM0, M4, M8
reader.session = 1

# search for tags
tags = reader.singleInventory()
for tag in tags:
    print(tag) # tag EPC and RSSI values are reported
```
