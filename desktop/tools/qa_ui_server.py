"""Local UI fixture server: no model loading, probes, updates or user profile."""
import os
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
os.environ['LINDA_HOME']=str(ROOT/'qa_ui_profile')
import uvicorn
from linda_desktop.app import Core,create_app
uvicorn.run(create_app(Core(),token='ui-test-token'),host='127.0.0.1',port=18764,log_level='warning')
