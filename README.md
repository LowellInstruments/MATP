# MATP

Log reader for Lowell Instrument's data logger.

# Usage

1. Install the necessary dependencies:
  1. `$ virtualenv ve`
  2. `$ source ve/bin/activate # may be different on windows`
  3. `$ pip install -r requirements.txt`
2. Add this directory to your PYTHONPATH environment variable
  *) Unix: `export PYTHONPATH=.`
  *) Windows: somewhere under Control Panel is an Environment Variable setting you can modify.
3. Add the bin directory to your PATH environment variable
  *) Same as above except replace PYTHONPATH with PATH
4. Run `$ lid.py <filename>` to convert the binary file to a csv

# Testing

To run the integration tests:

1. Follow the basic usage instructions above.
2. `$ cd matp/test`
3. run `$ python test_integration.py`

# License

See LICNESE file (Simplified BSD)

# Windows installation instructions

1. Install git
2. Clone this repo somewhere
3. Install python
4. Modify your path so that python is runnable from the command prompt (probably)
5. dir into the repo you cloned in step 2
6. run `bin\lid.py path/to/data/file.lid`
7. Check output of out.csv and tmp.csv
