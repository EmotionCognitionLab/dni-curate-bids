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
    echo_pattern = re.compile("^(.*)_e([1-9])\\.nii\\.gz")

    if session_only:
        all_sessions = [fw.get_session(session_id)]
    else:
        project = fw.get_project(project_id)
        all_sessions = project.sessions.iter()

    for sess in all_sessions:
        set_echo_times(sess)
        set_echo_indices(sess)


    def set_echo_times(session):
        mag1 = {}
        mag2 = {}
        phase = {}
        acquisitions = session.acquisitions()
        for acquisition in acquisitions:
            fieldmap_files = list(filter(lambda f: 'Fieldmap' in f.classification.get('Intent', []) and f.type == 'nifti', acquisition.files))
            # this may give incorrect results if a session somehow has >1 mag1, mag2 or phase files
            for f in fieldmap_files:
                if mag1_pattern.match(f.name):
                    mag1 = f
                elif mag2_pattern.match(f.name):
                    mag2 = f
                elif phase_pattern.match(f.name):
                    phase = f

        if mag1 != {} and mag2 != {} and phase != {}:
            mag1_meta = fw.get_acquisition_file_info(mag1.parent.id,mag1.name)
            mag2_meta = fw.get_acquisition_file_info(mag2.parent.id,mag2.name)
            echotime1 = mag1_meta.info['EchoTime']
            echotime2 = mag2_meta.info['EchoTime']
            print(f"For {session.subject.label}/{session.label}, setting EchoTime1={echotime1:.5f}, EchoTime2={echotime2:.5f} in file {phase.name}.")
            phase.update_info({"EchoTime1":echotime1,"EchoTime2":echotime2})


    def set_echo_indices(session):
        """Identifies multi-echo sequences and sets the BIDS echo index for each file in them.
            Some multi-echo sequences start with *_e1.nii.gz, while others start with *.nii.gz 
            and then go to *_e2.nii.gz, *_e3.nii.gz, ... 
        """
        acquisitions = session.acquisitions()
        for a in acquisitions:
            func_files = list(filter(lambda f: 'Functional' in f.classification.get('Intent', []) and 'nifti' == f.type, a.files))
            updated_files = 0
            max_echo_index = 0
            base_file_name = ''

            for f in func_files:
                echo_match = echo_pattern.match(f.name)
                if echo_match:
                    if updated_files == 0:
                        base_file_name = echo_match.group(1)
                    echo_index = echo_match.group(2)
                    max_echo_index = max(max_echo_index, int(echo_index))
                    f.update_info({"BIDS": {"Echo": echo_index }})
                    updated_files += 1

            if updated_files > 0 and updated_files < max_echo_index:
                # then the sequence started with a <base_file_name>.nii.gz file that we 
                # haven't set the echo index on yet - find it and set it
                first_file_name = base_file_name + '.nii.gz'
                first_file = list(filter(lambda f: f.name == first_file_name, func_files))
                if len(first_file) != 1:
                    print(f"For {session.subject.label}/{session.label}, expected to find one file named {first_file_name} as part of a multi-echo sequence in acquisiton {a.label}, but found {len(first_file)} files with that name. The echo indexing may be incorrect for this sequence.")
                else:
                    first_file[0].update_info({"BIDS": {"Echo": 1 }})


        
       