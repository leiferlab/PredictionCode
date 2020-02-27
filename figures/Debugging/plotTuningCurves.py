
################################################
#
# grab all the data we will need
#
################################################
import os
import numpy as np

from prediction import userTracker
import prediction.dataHandler as dh

print("Loading data..")

codePath = userTracker.codePath()
outputFolder = os.path.join(codePath,'figures/Debugging')

data = {}
for typ in ['AKS297.51', 'AML32', 'AML18']:
    for condition in ['moving', 'chip', 'immobilized']:  # ['moving', 'immobilized', 'chip']:
        path = userTracker.dataPath()
        folder = os.path.join(path, '{}_{}/'.format(typ, condition))
        dataLog = os.path.join(path, '{0}_{1}/{0}_{1}_datasets.txt'.format(typ, condition))
        outLoc = os.path.join(path, 'Analysis/{}_{}_results.hdf5'.format(typ, condition))
        outLocData = os.path.join(path, 'Analysis/{}_{}.hdf5'.format(typ, condition))

        print("Loading " + folder + "...")
        try:
            # load multiple datasets
            dataSets = dh.loadDictFromHDF(outLocData)
            keyList = np.sort(dataSets.keys())
            results = dh.loadDictFromHDF(outLoc)
            # store in dictionary by typ and condition
            key = '{}_{}'.format(typ, condition)
            data[key] = {}
            data[key]['dsets'] = keyList
            data[key]['input'] = dataSets
            data[key]['analysis'] = results
        except IOError:
            print typ, condition, 'not found.'
            pass
print('Done reading data.')



### CHOOSE DATASET TO PLOT
key = 'AKS297.51_moving'
idn = 'BrainScanner20200130_110803'

### Get the relevant data.
dset = data[key]['input'][idn]
activity = dset['Neurons']['I_smooth']
time = dset['Neurons']['I_Time']
gRaw = dset['Neurons']['gRaw']
numNeurons = activity.shape[0]
vel = dset['BehaviorFull']['AngleVelocity']
curv = dset['BehaviorFull']['Eigenworm3']




import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec


#Loop through each neuron
for neuron in np.arange(numNeurons):
    fig = plt.figure(constrained_layout=True, figsize=[22, 16])
    gs = gridspec.GridSpec(ncols=7, nrows=5, figure=fig)
    ax1 = fig.add_subplot(gs[0, 1])
    ax2 = fig.add_subplot(gs[0, 4])
    ax3 = fig.add_subplot(gs[1, :])
    ax4 = fig.add_subplot(gs[2, :], sharex=ax3)
    ax5 = fig.add_subplot(gs[3, :], sharex=ax3)
    ax6 = fig.add_subplot(gs[4, :], sharex=ax3)

    ax = [ax1, ax2, ax3, ax4, ax5]

    fig.suptitle(key + ' ' + idn + ' Neuron: #' + str(neuron))

    #Randomize the axes order withour replacement
    #Actually Plot
    ax[0].plot(vel, activity[neuron, :],'o', markersize=0.7)

    # Randomize the axes order withour replacement
    ax[1].plot(curv, activity[neuron, :],'o', markersize=0.7)

    ax[0].set_title(key + ' ' + idn + ' Neuron: #' + str(neuron),
                    fontsize=10)
    ax[1].set_title(key + ' ' + idn + ' Neuron: #' + str(neuron),
                    fontsize=10)

    #Add line for behavior = 0
    ax[0].axvline(linewidth=0.5, color='k')
    ax[1].axvline(linewidth=0.5, color='k')


    ax[0].set_xlabel('Velocity')
    ax[1].set_xlabel('Curvature')


    ax[0].set_ylabel('Fluorescence (common-noise rejected)')
    ax[1].set_ylabel('Fluorescence (common-noise rejected)')


    ax[2].plot(time, activity[neuron, :])
    ax[2].set_ylabel('Activity')
    ax[2].set_xlabel('Volumes')


    ax[3].plot(vel)
    ax[3].set_ylabel('Velocity')
    ax[3].set_xlabel('Volumes')
    ax[3].axhline(linewidth=0.5, color='k')


    ax[4].plot(curv)
    ax[4].set_ylabel('Curvature')
    ax[4].set_xlabel('Volumes')
    ax[4].axhline(linewidth=0.5, color='k')

    ax[5].plot(gRaw)
    ax[5].set_ylabel('gRaw')
    ax[5].set_xlabel('Volumes')




#Later should sort by COM of the distribution.. but for now just plot


print("Saving tuning curve plots to PDF...")

import matplotlib.backends.backend_pdf
pdf = matplotlib.backends.backend_pdf.PdfPages(key + "_" + idn + "_tuning.pdf")
numFigs = plt.gcf().number + 1
for fig in xrange(1, numFigs): ## will open an empty extra figure :(
    print("Saving Figure %d of %d" % (fig, numFigs))
    pdf.savefig(fig)
    plt.close(fig)
pdf.close()
print("Saved.")







