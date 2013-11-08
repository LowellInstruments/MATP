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

# License

See LICNESE file (Simplified BSD)


# Windows installation instructions

1. Install git
2. Clone this repo somewhere
3. Install python
4. Modify your path so that python is runnable from the command prompt (probably)
5. dir into the repo you cloned in step 2
6. run `bin\lid.py path/to/data/file.lid 1`
7. Check output of out.csv and tmp.csv

Note: that extra 1 indicates you want to use default host storage. I haven't built in a flag parser yet
so I'm using 1 to represent "use default host storage".

We have to use default host storage because a lot of the data files have mis-calibrated MXS/MYS/MZS values.