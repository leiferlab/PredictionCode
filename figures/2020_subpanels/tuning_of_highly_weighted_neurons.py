import matplotlib.pyplot as plt
import numpy as np
import pickle
from matplotlib import gridspec
import matplotlib.backends.backend_pdf
from prediction import userTracker
from prediction import dataHandler as dh
import os
from scipy.ndimage import gaussian_filter
import prediction.provenance as prov

#behavior = 'curvature'
behavior = 'velocity'
pickled_data = '/projects/LEIFER/PanNeuronal/decoding_analysis/analysis/comparison_results_' + behavior + '_l10.dat'
with open(pickled_data, 'rb') as handle:
    data = pickle.load(handle)

excludeSets = ['BrainScanner20200309_154704', 'BrainScanner20181129_120339', 'BrainScanner20200130_103008']
excludeInterval = {'BrainScanner20200309_145927': [[50, 60], [215, 225]], 
                   'BrainScanner20200309_151024': [[125, 135], [30, 40]], 
                   'BrainScanner20200309_153839': [[35, 45], [160, 170]], 
                   'BrainScanner20200309_162140': [[300, 310], [0, 10]],
                   'BrainScanner20200130_105254': [[65, 75]],
                   'BrainScanner20200310_141211': [[200, 210], [240, 250]]}

def take_deriv(neurons):
    from prediction.Classifier import rectified_derivative
    _, _, nderiv = rectified_derivative(neurons)
    return nderiv

neuron_data = {}
deriv_neuron_data = {}
time_data = {}
beh_data = {}
for typ_cond in ['AML310_moving']:
    path = userTracker.dataPath()
    folder = os.path.join(path, '%s/' % typ_cond)
    dataLog = os.path.join(path,'{0}/{0}_datasets.txt'.format(typ_cond))

    # data parameters
    dataPars = {'medianWindow': 0,  # smooth eigenworms with gauss filter of that size, must be odd
            'gaussWindow': 50,  # gaussianfilter1D is uesed to calculate theta dot from theta in transformEigenworms
            'rotate': False,  # rotate Eigenworms using previously calculated rotation matrix
            'windowGCamp': 5,  # gauss window for red and green channel
            'interpolateNans': 6,  # interpolate gaps smaller than this of nan values in calcium data
            'volumeAcquisitionRate': 6.,  # rate at which volumes are acquired
            }
    dataSets = dh.loadMultipleDatasets(dataLog, pathTemplate = folder, dataPars = dataPars)
    keyList = np.sort(dataSets.keys())

    for key in keyList:
        if key in excludeSets:
            continue
        time = dataSets[key]['Neurons']['I_Time_crop_noncontig']
        neurons = dataSets[key]['Neurons']['I_smooth_interp_crop_noncontig']
        if behavior == 'velocity':
            beh = dataSets[key]['Behavior_crop_noncontig']['AngleVelocity']
        elif behavior == "curvature":
            beh = dataSets[key]['Behavior_crop_noncontig']['Eigenworm3']
        else:
            assert False


        if key in excludeInterval.keys():
            for interval in excludeInterval[key]:
                idxs = np.where(np.logical_or(time < interval[0], time > interval[1]))[0]
                time = time[idxs]
                neurons = neurons[:,idxs]
                beh = beh[idxs]

        neuron_data[key] = neurons
        deriv_neuron_data[key] = take_deriv(neurons)
        time_data[key] = time
        beh_data[key] = beh




key='BrainScanner20200130_110803'

import os
outfilename = key + '_highweight_tuning_' + behavior + '.pdf'
pdf = matplotlib.backends.backend_pdf.PdfPages(os.path.join(userTracker.codePath(),'figures','2020_subpanels','generatedFigs', outfilename))

#Sort neurons by abs value weight
slm_weights_raw = data[key]['slm_with_derivs']['weights'][:data[key]['slm_with_derivs']['weights'].size / 2]
slm_weights_raw_deriv = data[key]['slm_with_derivs']['weights'][data[key]['slm_with_derivs']['weights'].size / 2:]
highly_weighted_neurons = np.flipud(np.argsort(np.abs(slm_weights_raw)))
highly_weighted_neurons_deriv = np.flipud(np.argsort(np.abs(slm_weights_raw_deriv)))
num_neurons = len(highly_weighted_neurons)

from skimage.util.shape import view_as_windows as viewW
def strided_indexing_roll(a, r):
    # Concatenate with sliced to cover all rolls
    # This function will roll each row of a matrix a, a an amount specified by r.
    # I got it here: https://stackoverflow.com/a/51613442/200688
    a_ext = np.concatenate((a,a[:,:-1]),axis = 1)

    # Get sliding windows; use advanced-indexing to select appropriate ones
    n = a.shape[1]
    return viewW(a_ext,(1,n))[np.arange(len(r)), (n-r)%n,0]
import numpy.ma as ma
def nancorrcoef(A, B):
    a = ma.masked_invalid(A)
    b = ma.masked_invalid(B)

    msk = (~a.mask & ~b.mask)

    return ma.corrcoef(a[msk], b[msk])

def vcorrcoef(X,y):
    ''' vectorized corrcoef, from a https://waterprogramming.wordpress.com/2014/06/13/numpy-vectorized-correlation-coefficient/'''
    Xm = np.reshape(np.mean(X,axis = 1),(X.shape[0],1))
    ym = np.mean(y)
    r_num = np.sum((X-Xm)*(y-ym),axis = 1)
    r_den = np.sqrt(np.sum((X-Xm)**2,axis = 1)*np.sum((y-ym)**2))
    r = r_num/r_den
    return r

def get_pval_from_cdf(x,  rhos, cum_prob):
    np.all(np.diff(rhos) > 0)
    if x > 0:
        p = 1 - np.interp(x, rhos, cum_prob)
    if x <= 0:
        p = np.interp(x, rhos, cum_prob)
    return p

def shuffled_cdf_rho(activity, behavior, pdf, nShuffles = 5000):
    '''Take recording of F and dF/dt for a set of N neurons, and shuffle
    each neuron nShuffles times. Calculate the Pearsons Correlation coefficient
    rho and get a distrubtion out.
    The distrubtion is the cumulative distribution of the rhos from the N x nShuffle
    '''
    assert(activity.shape[1] > 360), "The recording is less than 1 minute long, or the array is not in the expected format"
    import numpy.matlib
    print("Shuffling %d times has begun." % nShuffles*activity.shape[0])
    print("Time reversing and duplicating data...")
    shuff_activity = np.matlib.repmat(np.fliplr(activity), nShuffles, 1)
    assert (np.all(shuff_activity[4,:] == shuff_activity[4+activity.shape[0],:])), "Somehow repmat failed"
    print("Generating Random Numbers...")
    roll = np.random.randint(activity.shape[1], size = nShuffles*activity.shape[0])
    assert (roll.shape[0] == shuff_activity.shape[0]), "The number of time lags does not match the number of rows of activity to shuffle"
    print("Permuting neural activity...")
    shuff_activity = strided_indexing_roll(shuff_activity, roll)
    assert (np.logical_not(np.all(np.all(shuff_activity[4,:] == shuff_activity[4+activity.shape[0],:])))), "By chance, two preselected rows were shuffled the same amount, or not at all. Should only happen p = 1/(Number of samples in recording)"
    print("Calculating pearson's correlation coefficients...")
#    rhos = np.array([nancorrcoef(row, behavior)[0,1] for row in shuff_activity])
    rhos = vcorrcoef(shuff_activity, behavior)
    assert(rhos.shape[0]==shuff_activity.shape[0]), "Got the wrong number of corrcoefs rho"
    print("Finding CDF...")
    rhos = np.sort(rhos)
    cum_prob = np.linspace(0, 1, len(rhos), endpoint = False)
    print("Shuffled distribution found.")
    fig_cdf = plt.figure()
    plt.plot(rhos, cum_prob)
    plt.xlabel('rho')
    plt.ylabel('p')
    plt.title('CDF , N=%d, max(rho)=%.2f, min(rho)=%.2f' % (nShuffles*activity.shape[0], np.max(rhos), np.min(rhos)))
    pdf.savefig(fig_cdf)
    return rhos, cum_prob

#Calculate distribution of corrcoeff's on shuffled data for getting p-values
activity_all = np.concatenate((neuron_data[key], deriv_neuron_data[key]), axis = 0)
rhos, cum_prob = shuffled_cdf_rho(activity_all, beh_data[key], pdf)

for type in ['F', 'dF/dt']:
    for rank in np.arange(num_neurons):
        if type == 'F':
            neuron = highly_weighted_neurons[rank]
            weight = slm_weights_raw[neuron]
            activity = neuron_data[key][neuron]
            color = u'#1f77b4'
        elif type == 'dF/dt':
            neuron = highly_weighted_neurons_deriv[rank]
            weight = slm_weights_raw_deriv[neuron]
            activity = deriv_neuron_data[key][neuron]
            color = u'#ff7f0e'
        else:
            assert False



        #Calculate bins for box plot and split data up into subarrays based on bin
        nbins = 10
        plus_epsilon = 1.00001
        bin_edges = np.linspace(np.nanmin(beh_data[key]) * plus_epsilon, np.nanmax(beh_data[key]) * plus_epsilon, nbins)
        binwidth = np.diff(bin_edges)
        assigned_bin = np.digitize(beh_data[key], bin_edges)
        activity_bin = [None] * (len(bin_edges) - 1)  # note the activity has to be lists, and there should be 1 less because the bins are edges
        for k, each in enumerate(np.unique(assigned_bin)):
            activity_bin[k] = activity[np.argwhere(assigned_bin == each)[:, 0]]

        rho = nancorrcoef(beh_data[key], activity)[0,1]
        pval = get_pval_from_cdf(rho, rhos, cum_prob)
        fig1 = plt.figure(constrained_layout = True, figsize=[10, 5.3])
        gs = gridspec.GridSpec(ncols = 4, nrows = 2, figure = fig1)
        plt.rc('xtick', labelsize = 17)
        plt.rc('ytick', labelsize = 17)

        ax_blank = fig1.add_subplot(gs[1,0], title = key + '  ' + type + '\n Neuron: %d,\n Weight Rank: %d, Weight = %.4f\n rho= %.2f, p=%.2E' % (neuron, rank, weight, rho, pval))

        #Generate scatter plot and then box plot
        f1_ax1 = fig1.add_subplot(gs[0, 0], xlabel = behavior, ylabel='Activity (' + type + ')')
        f1_ax1.plot(beh_data[key], activity, 'o', alpha=.05, color = color)
        boxprops = dict(linewidth=.5)
        capprops = dict(linewidth=.5)
        whiskerprops = dict(linewidth=.5)
        flierprops = dict(linewidth=.2, markersize = 1, marker='+')
        medianprops = dict(linewidth = 2, color='#67eb34')
        labels = [''] * len(activity_bin)
        f1_ax1.boxplot(activity_bin, positions = bin_edges[:-1] + binwidth / 2, widths = binwidth * .9, boxprops = boxprops,
                    medianprops = medianprops, labels = labels, manage_xticks = False,
                    capprops = capprops, whiskerprops = whiskerprops, flierprops = flierprops)
        plt.locator_params(nbins = 4)

        f1_ax2 = fig1.add_subplot(gs[0,1:], xlabel='time (s)', ylabel='Activity')
        f1_ax2.plot(time_data[key], activity, color = color)
        f1_ax2.set_xlim(left = 0)

        f1_ax3 = fig1.add_subplot(gs[1,1:], xlabel='time (s)', ylabel = behavior)
        f1_ax3.plot(time_data[key], beh_data[key], color='black')
        f1_ax3.axhline(color='black')
        f1_ax3.set_xlim(left = 0)
        prov.stamp(f1_ax3, .55, .35, __file__ + '\n' + pickled_data)
        pdf.savefig(fig1)

pdf.close()
print("wrote " + outfilename)

