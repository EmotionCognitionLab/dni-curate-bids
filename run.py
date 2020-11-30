import json
import flywheel
from flywheel_bids.curate_bids import main_with_args, curate_bids_dir
import re

if __name__ == '__main__':

    # Grab Config
    CONFIG_FILE_PATH = '/flywheel/v0/config.json'
    with open(CONFIG_FILE_PATH) as config_file:
        config = json.load(config_file)

    #Dump config file for debugging
    #print(json.dumps(config,indent=4)) 

    api_key = config['inputs']['api_key']['key']
    session_id = config['destination']['id']
    #print("session id: %s" % session_id)
    reset = config['config']['reset']
    subject_only = not config['config']['entire_project']
    #template_file = config['config']['template_file']
    template_file = "bids-dni-v1.json"

    fw = flywheel.Client(api_key)
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

    # set the echotimes for any fieldmap acquisitions
    mag1_pattern = re.compile("^.*_e1\\.nii\\.gz")
    mag2_pattern = re.compile("^.*_e2\\.nii\\.gz")
    phase_pattern = re.compile("^.*_e2_ph\\.nii\\.gz")

    def set_echo_times(sess_id):
        session = fw.get_session(sess_id)
        acquisitions = session.acquisitions()
        for acquisition in acquisitions:
            # this may give incorrect results if an acquisition somehow has >1 mag1, mag2 or phase files
            for f in acquisition.files:
                if mag1_pattern.match(f.name):
                    mag1 = f
                elif mag2_pattern.match(f.name):
                    mag2 = f
                elif phase_pattern.match(f.name):
                    phase = f

        mag1_meta = fw.get_acquisition_file_info(mag1.parent.id,mag1.name)
        mag2_meta = fw.get_acquisition_file_info(mag2.parent.id,mag2.name)
        echotime1 = mag1_meta.info['EchoTime']
        echotime2 = mag2_meta.info['EchoTime']
        print(f"For {session.subject.label}/{session.label}, setting EchoTime1={echotime1:.5f}, EchoTime2={echotime2:.5f} in file {phase.name}.")
        phase.update_info({"EchoTime1":echotime1,"EchoTime2":echotime2})

    if session_only:
        all_sessions = [session_id]
    else:
        project = fw.get_project(project_id)
        search_result = fw.search({'return_type': 'session', 'structured_query': f"file.classification.Intent = 'Fieldmap' AND file.type = 'nifti' AND project.label = '{project.label}'"}, size=5000)
        all_sessions = list(map(lambda item: item['session']['_id'], search_result))

    for s_id in all_sessions:
        set_echo_times(s_id)
       