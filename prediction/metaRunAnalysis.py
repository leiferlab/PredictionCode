#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
Created on Wed Jul 10 14:14:34 2019
This is a meta script to run runAnalysis over and over again.
@author: leifer
"""
print('yo')

import git
repo = git.Repo(search_parent_directories=True)
sha = repo.head.object.hexsha
repoPath=repo._working_tree_dir
repoURL=repo.remotes.origin.url

from datetime import datetime

datetime.today().strftime('%Y-%m-%d %H:%M')

print(sha)

####

import runAnalysis as analysis

analysis.actuallyRun('AML32','moving')
analysis.actuallyRun('AML18','moving')
analysis.actuallyRun('AML70','moving')
analysis.actuallyRun('AML175','moving')


analysis.actuallyRun('AML32','immobilized')
analysis.actuallyRun('AML18','immobilized')
analysis.actuallyRun('AML70','immobilized')

analysis.actuallyRun('AML32','chip')
analysis.actuallyRun('Special','transition') #Note these are identicail..
                                            # I copied and pasted the input files..

analysis.actuallyRun('AML70','chip')

execfile('../figures/supp/S4.py')
execfile('../figures/supp/S2.py')
execfile('../figures/main/fig1v3.py')
execfile('../figures/main/fig2_expVarslm.py')
execfile('../figures/main/fig2v3.py')