import sys
import json
import ROOT
import numpy as np
from array import array

args = sys.argv

min_duration = args[1]

file_path = 'out.json'
station = 1
gem_labels = [f'GE{station}1-{region}-L{layer}' for region in ['M', 'P'] for layer in [1, 2]]
data = {'run': []}

for gem_label in gem_labels:
    data[gem_label] = {'muonSTA': {}, 'muonGLB': {}}
    for i in range(1, 37):
        data[gem_label]['muonSTA'][f'{i}'] = []
        data[gem_label]['muonGLB'][f'{i}'] = []

with open(f'good_runs/good_runs_{min_duration}.json', 'r') as json_file:
    json_runs = json.load(json_file)
    good_runs = json_runs['run']

with open('hv_by_run.json', 'r') as json_file:
    hv_by_run = json.load(json_file)

with open(file_path, 'r') as json_file:
    runs = json.load(json_file)
    # runs = json_data[args[1]]

    for run in runs.keys():
        data['run'].append(run)
        for gem_label in gem_labels:
            glb_muon = runs[run][gem_label]['GLB']
            glb_muon = [glb_muon[key] for key in glb_muon.keys()]

            for chamber, glb in enumerate(zip(*glb_muon)):
                data[gem_label]['muonGLB'][f'{chamber+1}'].append(list(glb))

    for gem_label in gem_labels:
        region = 1 if gem_label.split('-')[1] != 'P' else -1
        for i in range(1, 37):
            cvs = ROOT.TCanvas('', '', 2400, 800)
            glb_denom, glb_numer, glb_eff, glb_inactive = [], [], [], []
            for glb in data[gem_label]['muonGLB'][f'{i}']:
                glb_denom.append(glb[0])
                glb_numer.append(glb[1])
                glb_eff.append(glb[2])
                glb_inactive.append(glb[3])

            run_ls = [int(run) for run in data['run']]
            tmp_ls = [[r, g_d, g_n, g_e, g_i] for r, g_d, g_n, g_e, g_i in zip(run_ls, glb_denom, glb_numer, glb_eff, glb_inactive)]
            tmp_ls.sort(key=lambda x: x[0])

            run_arr, glb_arr = array('d'), array('d')
            glb_lower, glb_upper = array('d'), array('d')
            hv_run_arr, hv_arr = array('d'), array('d')
            xerr_arr = array('d')
            inactive_run_arr, inactive_arr = array('d'), array('d')
            xarr = array('d')

            start_run = 357300
            end_run = 357800

            xarr_idx = 1
            for tmp in tmp_ls:
                if tmp[0] < start_run: continue
                if tmp[0] > end_run: continue
                if tmp[0] not in good_runs: continue
                try:
                    hv = hv_by_run[f'{tmp[0]}'][f'{region}'][i-1]
                    if hv != -1:
                        hv_run_arr.append(tmp[0])
                        hv_arr.append(round(hv/1000, 4))
                except Exception as Err:
                    pass
                if tmp[3] == 0: continue

                if tmp[4] != -1:
                    inactive_run_arr.append(tmp[0])
                    inactive_arr.append(round(tmp[4], 4))
                xarr.append(xarr_idx)
                xarr_idx += 1
                run_arr.append(tmp[0])
                glb_lower.append(tmp[3] - ROOT.TEfficiency.ClopperPearson(tmp[1], tmp[2], 0.683, False))
                glb_upper.append(-tmp[3] + ROOT.TEfficiency.ClopperPearson(tmp[2], tmp[2], 0.683, True))
                glb_arr.append(tmp[3])
                xerr_arr.append(0)

            if len(run_arr) == 0:
                for tmp in tmp_ls:
                    run_arr.append(tmp[0])
                    # sta_arr.append(tmp[1])
                    glb_arr.append(tmp[2])
                    glb_lower.append(0)
                    glb_upper.append(0)
                    xerr_arr.append(0)
                    hv_run_arr.append(0)
                    hv_arr.append(0)
                    inactive_run_arr.append(0)
                    inactive_arr.append(0)

            if len(hv_run_arr) == 0:
                for tmp in tmp_ls:
                    hv_run_arr.append(0)
                    hv_arr.append(0)

            # g_sta = ROOT.TGraph(len(run_arr), run_arr, sta_arr)
            # g_glb = ROOT.TGraph(len(run_arr), run_arr, glb_arr)
            g_glb = ROOT.TGraphAsymmErrors(len(xarr), xarr, glb_arr, xerr_arr, xerr_arr, glb_lower, glb_upper)
            # g_glb = ROOT.TGraphAsymmErrors(len(run_arr), hv_arr, glb_arr, xerr_arr, xerr_arr, glb_lower, glb_upper)
            g_hv = ROOT.TGraph(len(hv_run_arr), hv_run_arr, hv_arr)
            g_inactive = ROOT.TGraph(len(inactive_run_arr), xarr, inactive_arr)

            g_inactive.SetMarkerColor(4)
            g_glb.SetMarkerColor(3)
            # g_sta.SetMarkerStyle(8)
            g_glb.SetMarkerStyle(8)
            # g_sta.SetMarkerSize(1.6)
            g_glb.SetMarkerSize(1.2)
            g_glb.SetTitle(f'{gem_label}-chamber-{i}')
            g_glb.GetXaxis().SetTitle('Run')
            g_glb.GetYaxis().SetTitle('Efficiency')
            # g_glb.GetXaxis().SetLimits(run_ls[0], run_ls[-1])
            g_glb.GetYaxis().SetRange(0, 1)
            g_glb.SetMinimum(0.)
            g_glb.SetMaximum(1.05)
            # g_glb.GetXaxis().SetLimits(357700, 357800)
            print(len(run_arr))
            g_glb.GetXaxis().SetNdivisions(len(run_arr))
            for bin_idx, run_num in enumerate(run_arr):
                g_glb.GetXaxis().SetBinLabel(g_glb.GetXaxis().FindBin(bin_idx+1), f'{int(run_num)}')
            # g_glb.GetXaxis().SetLimits(650, 800)
            g_glb.GetXaxis().LabelsOption('v')
            g_glb.Draw('AP')
            g_hv.SetLineColor(2)
            g_hv.SetLineWidth(2)
            g_hv.Draw('L')
            g_inactive.Draw('*')
            # g_sta.Draw('*l')
            # g_hv.Draw('LY+')
            leg = ROOT.TLegend(0.12, 0.15, 0.3, 0.35)
            # leg.AddEntry(g_sta, 'STA muon')
            leg.AddEntry(g_glb, 'GLB muon')
            leg.AddEntry(g_inactive, 'Inactive fraction', 'P')
            # leg.AddEntry(g_hv, 'HV / 1000')
            leg.SetFillStyle(0)
            leg.SetBorderSize(0)
            leg.Draw()
            cvs.SetGrid()
            cvs.SaveAs(f'new_imgs/{gem_label}_chamber_{i}.png')



