# Market and Oil Tracker

The purpose of this is to be able to pull data from January 2024 forward for the US market 
to see how the oil market impacts the other US markets over time.  This tracker data from the 
python script actually creates the new report html.  The lastest one from the last set of 
changes has been saved in this project.  To execute the python script just run the following 
from the location of the script:

Anyone who clones this repo can now get up and running with just:

   uv sync 

And to run your script:

   uv run market_oil_tracker.py 

File 	Purpose
pyproject.toml	Defines your project and its dependencies(yfinance, pandas)
uv.lock 	Locks exact versions of all packages (inccluding sub-dependencies
.python-version	Pins Python version(3.9)
.gitignore	Keeps the .venv folder out of git

