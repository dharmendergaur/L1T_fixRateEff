sumBranches = ['EtSum_' + var for var in ['pt', 'etSumType', 'bx']]
objectBranches = ['pt', 'eta', 'phi', 'bx']
puppiMETBranches = ['PuppiMET_pt', 'PuppiMET_phi']
muonBranches = ['Muon_' + var for var in ['pt', 'phi', 'isPFcand']]
puppiJetBranches = ['Jet_' + var for var in ['pt', 'eta','phi']]
# L1EmulJetBranches = ['L1EmulJet_' + var for var in ['pt', 'eta','phi']]

# github.com/cms-sw/cmssw/blob/master/DataFormats/L1Trigger/interface/EtSum.h
sums = {'methf': 8}