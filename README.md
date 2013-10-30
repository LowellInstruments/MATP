# MATP

Log reader for Lowell Instrument's data logger

# Usage

1. Install the necessary dependencies:
  1. `$ virtualenv ve`
  2. `$ source ve/bin/activate # may be different on windows`
  3. `$ pip install -r requirements.txt`
2. Add this directory to your PYTHONPATH environment variable
  1. `export PYTHONPATH=.`
3. Run `$ bin/lid.py <filename>` to convert the binary file to a csv
