import json
import flywheel
from flywheel_bids.curate_bids import main_with_args, curate_bids_dir

if __name__ == '__main__':

    # Grab Config
    CONFIG_FILE_PATH = '/flywheel/v0/config.json'
    with open(CONFIG_FILE_PATH) as config_file:
        config = json.load(config_file)

    #Dump config file for debugging
    #print(json.dumps(config,indent=4)) 

    api_key = config['inputs']['api_key']['key']
    session_id = config['destination']['id']
    reset = config['config']['reset']
    subject_only = not config['config']['entire_project']
    #template_file = config['config']['template_file']
    template_file = "bids-dni-v1.json"

    fw = flywheel.Flywheel(api_key)
    session = fw.get_session(session_id)
    #print(session)
    project_id = session['project']

    #Dump config file for debugging
    #print(config)
    #print("Template file: %s" % template_file)
    #print("Session id: %s" % session_id)

    if (subject_only):
    	session_only = True
    else:
    	session_only = False

    curate_bids_dir(fw, project_id, session_id, reset=reset, session_only=session_only,template_file=template_file)
