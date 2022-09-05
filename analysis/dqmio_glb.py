from pathlib import Path
from dataclasses import dataclass
import json
import uproot
import sqlite3
import numpy as np


@dataclass
class DQMInfo:
    region: int
    station: int
    layer: int
    run: int
    eff: np.ndarray
    num: np.ndarray
    denom: np.ndarray
    status: np.ndarray


data_dir = Path('/store/user/jwheo/DQMGUI_data/Run2022/')

station = 1
regions = ['M', 'P']
layers = [1, 2]
data = {}
for path in data_dir.glob('**/*.root'):
    trigger = path.parts[-3]
    if trigger == 'DoubleMuon': continue
    run_number = int(path.stem.split('_')[2][1:])
    if run_number < 355681 and trigger == "Muon": continue
    if run_number in data.keys(): print('err')
    print(trigger, run_number)
    data[f'{run_number}'] = {}
    root_file = uproot.open(path)
    try:
        # sta_eff_dir = root_file[f'DQMData/Run {run_number}/GEM/Run summary/Efficiency/muonSTA']
        glb_eff_dir = root_file[f'DQMData/Run {run_number}/GEM/Run summary/Efficiency/muonSTA']

    except Exception as errs:
        try:
            # sta_eff_dir = root_file[f'DQMData/Run {run_number}/GEM/Run summary/Efficiency/type1']
            glb_eff_dir = root_file[f'DQMData/Run {run_number}/GEM/Run summary/Efficiency/type2']
            # report_summary_map = root_file[f'DQMData/Run {run_number}/GEM/Run summary/EventInfo/{var}']

        except Exception as err:
            print(err)
    try:
        report_summary_map = root_file[f'DQMData/Run {run_number}/GEM/Run summary/EventInfo/reportSummaryMap']
        event_info_dir = root_file[f'DQMData/Run {run_number}/GEM/Run summary/EventInfo']
    except Exception as errs:
        pass

    for region in regions:
        for layer in layers:
            gem_label = f'GE{station}1-{region}-L{layer}'
            try:
                data[f'{run_number}'][gem_label] = {
                    # 'STA': {
                    #     'denominator': sta_eff_dir[f'chamber_ieta_{gem_label}'].values().sum(axis=1).tolist(),
                    #     'numerator': sta_eff_dir[f'chamber_ieta_match_{gem_label}'].values().sum(axis=1).tolist(),
                    #     'efficiency': sta_eff_dir[f'eff_chamber_{gem_label}'].values().tolist(),
                    #  },
                    'GLB': {
                        'denominator': glb_eff_dir[f'chamber_ieta_{gem_label}'].values().sum(axis=1).tolist(),
                        'numerator': glb_eff_dir[f'chamber_ieta_match_{gem_label}'].values().sum(axis=1).tolist(),
                        'efficiency': glb_eff_dir[f'eff_chamber_{gem_label}'].values().tolist(),
                     }
                }

            except Exception as err:
                data[f'{run_number}'][gem_label] = {
                        # 'STA': {
                        #     'denominator': sta_eff_dir[f'Efficiency/detector_{gem_label}'].values().sum(axis=1).tolist(),
                        #     'numerator': sta_eff_dir[f'Efficiency/detector_{gem_label}_matched'].values().sum(axis=1).tolist(),
                        #     'efficiency': sta_eff_dir[f'Efficiency/eff_detector_{gem_label}'].values().sum(axis=1).tolist(),
                        # },
                        'GLB': {
                            'denominator': glb_eff_dir[f'Efficiency/detector_{gem_label}'].values().sum(axis=1).tolist(),
                            'numerator': glb_eff_dir[f'Efficiency/detector_{gem_label}_matched'].values().sum(axis=1).tolist(),
                            'efficiency': glb_eff_dir[f'Efficiency/eff_detector_{gem_label}'].values().sum(axis=1).tolist(),
                        }
                }

            try:
                data[f'{run_number}'][gem_label]['STA']['inactive'] = event_info_dir[f'inactive_frac_chamber_{gem_label}'].values().tolist()
                data[f'{run_number}'][gem_label]['GLB']['inactive'] = event_info_dir[f'inactive_frac_chamber_{gem_label}'].values().tolist()

            except Exception as err:
                data[f'{run_number}'][gem_label]['STA']['inactive'] = [-1 for _ in range(36)]
                data[f'{run_number}'][gem_label]['GLB']['inactive'] = [-1 for _ in range(36)]

file_path = 'out.json'
with open(file_path, 'w') as outfile:
    json.dump(data, outfile, indent=2)
