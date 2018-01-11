import json
from termcolor import colored
from datetime import date, datetime

def get_status(status):
   if status == "Success":
       return colored(status, "green")
   else:
       return colored(status, "red")



def json_serial(obj):
    """JSON serializer for objects not serializable by default json code"""

    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    raise TypeError ("Type %s not serializable" % type(obj))


def format_json(s):
    json.dumps(s, indent=2, default=json_serial)
