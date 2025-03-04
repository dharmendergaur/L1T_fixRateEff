#!/usr/bin/env python
# coding: utf-8

import glob
import pandas as pd
import numpy as np
import awkward as ak
from itertools import cycle

import utils.tools as tools
import utils.plotting as plotting

import mplhep as cms
import matplotlib.pyplot as plt
cms.style.use("CMS")
plt.rcParams["figure.figsize"] = (10,7)


# input data definition
# put "default" objects first
# i.e. those that should be used to obtain fixed rate

#nComp = 3

#l1Labels = ['L1', 'L1_noJEC', 'L1_noJECnoPUSnoPUM']
#branchTypes = ['unp', 'emu', 'emu'] # unp or emu

#sigPaths  = ["zmu24I_noJEC/", "zmu24I_noJEC/", "zmu24I_noJEC_noPUS_noPUM/"]
#bkgPaths  = ["zb24I_noJEC/", "zb24I_noJEC/", "zb24I_noJEC_noPUS_noPUM/"]

nComp = 4

l1Labels = ['Default', 'Default_noPUM', 'BaselineZS', 'ConservativeZS']
branchTypes = ['unp', 'emu', 'emu', 'emu'] # unp or emu

rootDir = "/eos/home-d/ddharmen/JEC/CMSSW_14_1_4_patch1/src/JETMET/perf_job1/code/L1T_fixRateEff"

sigPaths  = ["zmu_base/", "zmu_pumOff/", "zmu_base/", "zmu_con/"]
bkgPaths  = ["zb_base/", "zb_pumOff/", "zb_base/", "zb_con/"]


inputFormat = 'nano'     # nanoAOD
#inputFormat = 'hdf5'     # pandas dataframes

sigName = "zmu"
bkgName = "zb"

writeDir = "./data/"

# fileName = "/eos/home-d/ddharmen/JEC/CMSSW_14_1_4_patch1/src/JETMET/zerobias_perf_raw_test/default/nano*.root"
fileName = "nano_991.root"

sigFiles = [glob.glob(rootDir + path + fileName) for path in sigPaths]
bkgFiles = [glob.glob(rootDir + path + fileName) for path in bkgPaths]

if len(l1Labels) != nComp or len(branchTypes) != nComp or len(sigFiles) != nComp or len(bkgFiles) != nComp:
       raise TypeError("Number of inputs datasets is not consistent")

sig_hdf5s = [writeDir + "/" + sigName + label + ".hdf5" for label in l1Labels]
bkg_hdf5s = [writeDir + "/" + bkgName + label + ".hdf5" for label in l1Labels]

# L1 thresholds (GeV)
l1JetThresholds = [30, 120, 180]
l1METThresholds = [50, 90]

# arrays containing our signal and background data
# for the different sets of input files
sigs = []
bkgs = []

sig_dfs = []
bkg_dfs = []


# In[4]:


if inputFormat == 'nano':
    
    for sigFile, branchType in  zip(sigFiles, branchTypes):
        sigs.append(tools.getArrays(sigFile, tools.getBranches(['Jet'], branchType=='emu', False), len(sigFile)))
                       
    for bkgFile, branchType in zip(bkgFiles, branchTypes):
        bkgs.append(tools.getArrays(bkgFile, tools.getBranches(['Jet'], branchType=='emu', False), len(bkgFile)))


if inputFormat == 'nano':

    for sig, sig_hdf5, l1Label in zip(sigs, sig_hdf5s, l1Labels):
        # get the puppiMETs
        puppiMET, puppiMETNoMu = tools.getPUPPIMET(sig)
        # get the l1METs
        l1MET_df = pd.DataFrame(ak.to_list(ak.flatten(tools.getSum(sig, 'methf')['EtSum_pt'])), columns=[l1Label])
        puppiMET_df = pd.DataFrame(ak.to_list(puppiMET['PuppiMET_pt']), columns=['PuppiMET'])
        puppiMETNoMu_df = pd.DataFrame(ak.to_list(puppiMETNoMu['PuppiMET_pt']), columns=['PuppiMETNoMu'])
        # save to dataframe
        pd.concat([l1MET_df, puppiMET_df, puppiMETNoMu_df], axis=1).to_hdf(sig_hdf5, l1Label, mode='w')



for bkg, bkg_hdf5, l1Label in zip(bkgs, bkg_hdf5s, l1Labels):
        
        l1MET_df = pd.DataFrame(ak.to_list(ak.flatten(tools.getSum(bkg, 'methf')['EtSum_pt'])), columns=[l1Label])
        l1MET_df.to_hdf(bkg_hdf5, l1Label, mode='w')



for sig_hdf5, l1Label in zip(sig_hdf5s, l1Labels):
    sig_dfs.append(pd.read_hdf(sig_hdf5, l1Label))
    
for bkg_hdf5, l1Label in zip(bkg_hdf5s, l1Labels):
    bkg_dfs.append(pd.read_hdf(bkg_hdf5, l1Label))



# plot the MET distributions
plt.hist(sig_dfs[0]['PuppiMET'], bins = 100, range = [0,200], histtype = 'step', log = True, label = "PUPPI MET")
plt.hist(sig_dfs[0]['PuppiMETNoMu'], bins = 100, range = [0,200], histtype = 'step',  label = "PUPPI MET NoMu")

for sig_df, l1Label in zip(sig_dfs, l1Labels):
    plt.hist(sig_df[l1Label], bins = 100, range = [0,200], histtype = 'step', label = l1Label)

plt.legend(fontsize=14)
plt.xlabel('L1 MET [GeV]')
plt.ylabel('Events')
plt.tight_layout()
plt.savefig("plots/MET.pdf", format="pdf")
plt.clf()


# plot the MET resolution
for sig_df, l1Label in zip(sig_dfs, l1Labels):
    plt.hist((sig_df[l1Label] - sig_df['PuppiMETNoMu']), bins = 80, range = [-100,100], label = l1Label + " Diff")

plt.legend(fontsize=14)
plt.xlabel('L1 MET - Puppi MET [GeV]')
plt.ylabel('Events')
plt.tight_layout()
plt.savefig("plots/MET_res.pdf", format="pdf")
plt.clf()

# plot the jet distributions
#plt.hist(sig_dfs[0]['Jet_pt_0'], bins = 100, range = [0,200], histtype = 'step', log = True, label = "PUPPI MET")
#plt.hist(sig_dfs[0]['Jet_pt'], bins = 100, range = [0,200], histtype = 'step',  label = "PUPPI MET NoMu")


# make fixed rate MET efficiencies

# rate plots must be in bins of GeV
ptRange = [0,200]
bins = ptRange[1]

l1METRates = []
l1METThresholdsArr = [l1METThresholds]

# get rate hist for "default" objects
rateScale = 40000000*(2452/3564)/len(bkg_dfs[0])
rateHist = plt.hist(bkg_dfs[0], bins=bins, range=ptRange, histtype = 'step', label=l1Labels[0], cumulative=-1, log=True, weights=np.full(len(bkg_dfs[0]), rateScale))

for l1METThreshold in l1METThresholds:
    # get rates for the default thresholds
    l1METRate = rateHist[0][l1METThreshold]
    l1METRates.append(l1METRate)

for i in range(1, nComp):
    # get thresholds for the fixed rates
    rateScale = 40000000*(2452/3564)/len(bkg_dfs[i])
    rateHist = plt.hist(bkg_dfs[i], bins=bins, range=ptRange, histtype = 'step', label=l1Labels[i], cumulative=-1, log=True, weights=np.full(len(bkg_dfs[i]), rateScale))
    thresholds = []
    for l1METThreshold in l1METThresholds:
        # get threshold for this rate
        thresholds.append(plotting.getThreshForRate(rateHist[0], bins, l1METRates[l1METThresholds.index(l1METThreshold)]))
    l1METThresholdsArr.append(thresholds)

plt.legend(fontsize=14)
plt.xlabel('L1 MET [GeV]')
plt.ylabel('Rate [Hz]')
plt.tight_layout()
plt.savefig("plots/MET_rates.pdf", format="pdf")
plt.clf()


# plot the MET efficiency
marks = cycle(('o', 's', '^', 'v', 'D', '*', '+', 'x'))
cols = cycle(('tab:blue','tab:orange','tab:green','tab:red','tab:purple', 'tab:pink', 'tab:cyan', 'tab:brown', 'tab:olive'))
m=0
for sig_df, l1Label, l1METThresholds in zip(sig_dfs, l1Labels, l1METThresholdsArr):
       for l1METThreshold in l1METThresholds:
              eff_data, xvals,err = plotting.efficiency(sig_df[l1Label], sig_df['PuppiMETNoMu'], l1METThreshold, 10, 400)
              plt.scatter(xvals, eff_data, label=l1Label + " > " + str(l1METThreshold), marker=next(marks), color=next(cols))
              m+=1

plt.axhline(0.95, linestyle='--', color='black')
plt.legend(fontsize=14)
plt.xlabel('PuppiMETnoMu [GeV]')
plt.ylabel('Efficiency')
plt.tight_layout()
plt.savefig("plots/MET_eff.pdf", format="pdf")
plt.clf()
