import numpy as np
import pandas as pd
import awkward as ak
import utils.branches as branches
import uproot


def deltaR(eta1, phi1, eta2, phi2):
    dphi = np.abs(phi1 - phi2)
    dphi = ak.where(dphi > np.pi, 2*np.pi - dphi, dphi)  
    deta = eta1 - eta2
    return np.sqrt(deta**2 + dphi**2)

def getArrays(inputFiles, branches, nFiles=1, fname="data.parquet"):

    files = [{file: 'Events'} for file in inputFiles][:nFiles]

    # get the data
    data = ak.concatenate([batch for batch in uproot.iterate(files, filter_name=branches)])
        
    data = formatBranches(data)

    return data


def getL1Types(useEmu=False, useMP=False):
    
    l1Type = 'L1Emul' if useEmu else 'L1' 
    l1SumType = l1Type + 'MP' if useMP else l1Type
    
    return l1Type, l1SumType


def getBranches(inputs=[], useEmu=False, useMP=False):
    
    l1Type, l1SumType = getL1Types(useEmu, useMP)
    
    sumBranches = [l1SumType + var for var in branches.sumBranches]
    all_branches = sumBranches + branches.puppiMETBranches + branches.muonBranches + branches.puppiJetBranches
    
    for input in inputs:
        all_branches += [l1Type + input + "_" + var for var in branches.objectBranches]

    return all_branches

def formatBranches(data):
    
    # remove the prefixes to the branch names for tidyness
    for branch in ak.fields(data):
        if branch.startswith("Jet_"):
            data[branch.replace("Jet_", "recoJet_")] = data[branch]
            del data[branch]

    for branch in ak.fields(data):
        if "L1" in branch:
            data[branch.replace("L1", "").replace("MP", "").replace("Emul", "")] = data[branch]
            del data[branch]
            
    return data


def getL1EmulHT(data):
    
    JET = data[branches.puppiJetBranches]
    etSum = ak.sum(JET['Jet_pt'], axis=1)
    
    return etSum

def getL1EmulJet1(data):
    
    JET = data[branches.puppiJetBranches]
    JET['leadingPt'] = ak.max(JET['Jet_pt'], axis=1)

    return JET['leadingPt']
    
def getPUPPIJET(data):
    DR_MAX = 0.4  # Maximum delta R between L1T and offline jets for matching
    minpT = 20.0

    l1jet = data[branches.puppiJetBranches]
    reco_puppiJetBranches = ['reco' + var for var in branches.puppiJetBranches]
    puppiJET = data[reco_puppiJetBranches]
    
    puppiJET = ak.with_field(puppiJET, puppiJET['recoJet_pt'] * np.cos(puppiJET['recoJet_phi']), "recoJet_ptx")
    puppiJET = ak.with_field(puppiJET, puppiJET['recoJet_pt'] * np.sin(puppiJET['recoJet_phi']), "recoJet_pty")
    puppiJET['recoJet_ht'] = ak.sum(puppiJET['recoJet_pt'], axis=1)
    puppiJET['leadingPt'] = ak.max(puppiJET['recoJet_pt'], axis=1)

    leading_puppi_idx = ak.argmax(puppiJET["recoJet_pt"], axis=1)
    leading_jet_eta = puppiJET['recoJet_eta'][leading_puppi_idx]
    leading_jet_phi = puppiJET['recoJet_phi'][leading_puppi_idx]
    leading_jet_pt = puppiJET['recoJet_pt'][leading_puppi_idx]

    matched_l1_jet = []
    for i in range(len(leading_jet_eta)):
        matched_jet = None
        for j in range(len(l1jet['Jet_pt'][i])):
            dR = deltaR(leading_jet_eta[i], leading_jet_phi[i], l1jet['Jet_eta'][i][j], l1jet['Jet_phi'][i][j])
            if ak.any(dR < DR_MAX) and ak.any(leading_jet_pt[i] > minpT):
                matched_jet = l1jet['Jet_pt'][i][j]
                break
        matched_l1_jet.append(matched_jet)

    puppiJET = ak.with_field(puppiJET, matched_l1_jet, "matched_l1_jet")
    return puppiJET



def getPUPPIMET(data):
    
    # get the offline puppi MET
    puppiMET = data[branches.puppiMETBranches]
    puppiMET = ak.with_field(puppiMET, puppiMET['PuppiMET_pt']*np.cos(puppiMET['PuppiMET_phi']), "PuppiMET_ptx")
    puppiMET = ak.with_field(puppiMET, puppiMET['PuppiMET_pt']*np.sin(puppiMET['PuppiMET_phi']), "PuppiMET_pty")

    # get the offline muons
    muons = data[branches.muonBranches]
    muons = muons[muons["Muon_isPFcand"] == 1]
    del muons["Muon_isPFcand"]
    muons = ak.with_field(muons, muons['Muon_pt']*np.cos(muons['Muon_phi']), "Muon_ptx")
    muons = ak.with_field(muons, muons['Muon_pt']*np.sin(muons['Muon_phi']), "Muon_pty")

    # make the offline puppi MET no mu
    puppiMET_noMu = ak.copy(puppiMET)
    puppiMET_noMu['PuppiMET_ptx'] = puppiMET['PuppiMET_ptx'] + np.sum(muons['Muon_ptx'], axis=1)
    puppiMET_noMu['PuppiMET_pty'] = puppiMET['PuppiMET_pty'] + np.sum(muons['Muon_pty'], axis=1)
    puppiMET_noMu['PuppiMET_pt'] = np.sqrt(puppiMET_noMu['PuppiMET_ptx']**2 + puppiMET_noMu['PuppiMET_pty']**2)
    
    del puppiMET['PuppiMET_phi'], puppiMET['PuppiMET_ptx'], puppiMET['PuppiMET_pty']
    del puppiMET_noMu['PuppiMET_phi'], puppiMET_noMu['PuppiMET_ptx'], puppiMET_noMu['PuppiMET_pty']
    
    return puppiMET, puppiMET_noMu

def apply_pt_cut(data, puppiMET_noMu, cut_value = -1):
    return data[puppiMET_noMu['PuppiMET_pt'] > cut_value], puppiMET_noMu[puppiMET_noMu['PuppiMET_pt'] > cut_value]

def remove_saturated(data, puppiMET_noMu):
    for col in data.columns:
        if "pt" in col:
            data = data[data[col] < 1000]
            puppiMET_noMu = puppiMET_noMu[data[col] < 1000]
    return data, puppiMET_noMu

def flatten(data, puppiMET_noMu, types=[]):
    
    cutoff = 800
    a = 0.88
    b = 0.06
    c = 0.01

    if 'puppi' in types:
        rand_arr = np.random.rand(len(puppiMET_noMu))
        data = data[rand_arr[puppiMET_noMu['PuppiMET_pt'] > 0]*(a-puppiMET_noMu['PuppiMET_pt']**b/cutoff**b) < c]
        puppiMET_noMu = puppiMET_noMu[rand_arr[puppiMET_noMu['PuppiMET_pt'] > 0]*(a-puppiMET_noMu['PuppiMET_pt']**b/cutoff**b) < c]
    
    if 'l1' in types:
        l1MET = ak.flatten(getSum(data, 'methf')['EtSum_pt'])
        rand_arr = np.random.rand(len(l1MET))
        data = data[rand_arr[l1MET > 0]*(a-l1MET**b/cutoff**b) < c]
        puppiMET_noMu = puppiMET_noMu[rand_arr[l1MET > 0]*(a-l1MET**b/cutoff**b) < c]

    return data, puppiMET_noMu
    

def getCollections(data, inputSums, inputs=[]):

    collections = {}

    # get the sums
    l1Sums = data[branches.sumBranches]
    l1Sums = l1Sums[l1Sums['EtSum_bx'] == 0]
    del l1Sums['EtSum_bx']

    # make the sum collections
    for esum in inputSums:
        sumCol = l1Sums[l1Sums['EtSum_etSumType'] == branches.sums[esum]]
        del sumCol['EtSum_etSumType']
        collections[esum] = sumCol
        
    # make the object collecions
    for input in inputs:
        collection = data[[input + "_" + var for var in branches.objectBranches]]
        collection = collection[collection[input+"_bx"] == 0]
        del collection[input + '_bx']
        collections[input] = collection
        
    return collections

def getSum(data, sumType):
    
    # get the sums
    l1Sums = data[branches.sumBranches]
    l1Sums = l1Sums[l1Sums['EtSum_bx'] == 0]
    del l1Sums['EtSum_bx']

    etSum = l1Sums[l1Sums['EtSum_etSumType'] == branches.sums[sumType]]
    del etSum['EtSum_etSumType']
    
    return etSum


def makeDataframe(collections, fileName=None, nObj=0, keepStruct=False):
    
    object_dfs = []
    for coll in collections:
        if coll in ['Jet', 'EG', 'Tau']:
            objects = pd.DataFrame(ak.to_list(ak.fill_none(ak.pad_none(ak.sort(collections[coll], ascending=False), nObj, clip=True), 0)))
        else:
            objects = pd.DataFrame(ak.to_list(collections[coll]))
        object_labels= ["{}_{}".format(coll, i) for i in range(len(objects.values.tolist()[0][0]))]
        for column in objects.columns:
            object = pd.DataFrame(objects.pop(column).values.tolist())
            object.columns = pd.MultiIndex.from_product([object_labels, [column.split("_")[1]]])
            object_dfs.append(object)

    df = pd.concat(object_dfs, axis=1)

    new_cols = pd.MultiIndex.from_tuples(sorted(list(df.columns)))
    for col in new_cols:
        df[col] = df.pop(col)

    if keepStruct:
        df
    else:
        df.columns = ["{}_{}".format(col[0], col[1]) for col in df.columns]

    if fileName:
        df.to_hdf(fileName, 'online', mode='w')

    return df


def arrayToDataframe(array, label, fileName):

    df = pd.DataFrame(ak.to_list(array))
    if fileName:
        df.to_hdf(fileName, label, mode='a')
    
    return df
