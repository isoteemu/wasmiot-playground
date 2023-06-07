import json
from pprint import pprint
from pyld import jsonld
from pathlib import Path
import pytest
from rich import print

from thingi.td import jsonld_compact, Thingi

TD_FILE = Path(Path(__file__).parent, "data/td_random.json")


def random_number():
    return 42


def test_model_loading():

    td = json.loads(TD_FILE.read_text())
    
    print(Thingi.producer(td))
    

    #json_ld = jsonld_compact(td)

    #print(json_ld)

    #print(jsonld.flatten(compact))

    #td = SupervisorDescription.parse_obj(json_ld)

    #print(td)

    #print(td.json(by_alias=True, indent=2))
    #pprint(td)
    #pprint(td.schema(by_alias=True))

if __name__ == "__main__":
    test_model_loading()
