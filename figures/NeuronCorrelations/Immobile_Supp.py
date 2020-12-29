
import os
import numpy as np
import matplotlib.pyplot as plt
from prediction import userTracker
import prediction.dataHandler as dh
from seaborn import clustermap

# For data set 110803 (moving only)- frames 1-1465, AVA 33 and 16
#Goal is to plot neural trajectories projected into first three PCs

def plot_a_trajectory(ax, pc_traj, tscale, theta=0, phi=0, color='#1f77b4', gradient = True):
    ax.view_init(theta, phi)
    if gradient:
        lns = pc_traj.shape[0]-1
        print(tscale)
        for i in range(lns):
            ax.plot(pc_traj[i:i+2, 0], pc_traj[i:i+2, 1], pc_traj[i:i+2, 2], color=plt.cm.Wistia(tscale[i]))
    else:
        ax.plot(pc_traj[:,0], pc_traj[:,1], pc_traj[:,2], color=color)
    c=1.3
    ax.axes.set_xlim3d(c*np.min(pc_traj[:, 0]), c*np.max(pc_traj[:, 0]))
    ax.axes.set_ylim3d(c*np.min(pc_traj[:, 1]), c*np.max(pc_traj[:, 1]))
    ax.axes.set_zlim3d(c*np.min(pc_traj[:, 2]), c*np.max(pc_traj[:, 2]))
    ax.set_xlabel('PC1')
    ax.set_ylabel('PC2')
    ax.set_zlabel('PC3')

def sync3d_limits(ax1, ax2):
    ax2.axes.set_xlim3d(ax1.axes.get_xlim3d())
    ax2.axes.set_ylim3d(ax1.axes.get_ylim3d())
    ax2.axes.set_zlim3d(ax1.axes.get_zlim3d())





def plot_trajectories(pc_traj, drug_app_index, imm_start_index, end_index, title='Neural State Space Trajectories', color='#1f77b4', theta=None, phi =None):
    fig = plt.figure(figsize=(12, 8))
    plt.suptitle(title)
    row=1
    col=2
    #How do we choose the orientation of the 3d plot?
    if theta is None or phi is None:
        RAND = True #randomize theta or phi
    else:
        RAND = False # show the plot orientated around the specified value
        theta_spec, phi_spec = theta, phi
        jit = 1.5 #magnitude of jitter in degrees

    tscale = (time-time[0]+.0)/(time[-1]-time[0])
    for nplot in np.arange(col) + 1:
        if RAND: #Generate a random angle to view the 3D plot
            theta, phi = np.random.randint(360), np.random.randint(360)
        else: #Generate a random centered around the view
            theta, phi = theta_spec + jit*np.random.randn(), phi_spec + jit*np.random.randn()
        ax1 = plt.subplot(row, col, nplot, projection='3d', title='immobile (%d, %d)' % (theta, phi) )
        plot_a_trajectory(ax1, pc_traj[imm_start_index:end_index,:], tscale[imm_start_index:end_index], theta, phi, color)


    cfig = plt.figure()
    cax = plt.subplot(1, 1)
    cax.set_axis_off()
    cax.imshow(np.vstack(tscale, tscale), aspect='auto', cmap=plt.cm.Wistia)
    cfig.savefig(os.path.join(codePath,'figures/subpanels_revision/generatedFigs/')+'colorbar_Immobile_Supp.pdf')


    import prediction.provenance as prov
    #prov.stamp(plt.gca(), .55, .15, __file__)
    return


for typ_cond in ['AKS297.51_immobile']: #, 'AKS297.51_moving']:
    path = userTracker.dataPath()
    folder = os.path.join(path, '%s/' % typ_cond)
    dataLog = os.path.join(path,'{0}/{0}_datasets.txt'.format(typ_cond))

    # Hard coding in folder for old dataset:
    #folder = '/projects/LEIFER/PanNeuronal/decoding_analysis/old_worm_data/Special_transition/'
    #dataLog = '/projects/LEIFER/PanNeuronal/decoding_analysis/old_worm_data/Special_transition/Special_transition_datasets.txt'

    # data parameters
    dataPars = {'medianWindow': 0,  # smooth eigenworms with gauss filter of that size, must be odd
            'gaussWindow': 50,  # gaussianfilter1D is uesed to calculate theta dot from theta in transformEigenworms
            'rotate': False,  # rotate Eigenworms using previously calculated rotation matrix
            'windowGCamp': 5,  # gauss window for red and green channel
            'interpolateNans': 6,  # interpolate gaps smaller than this of nan values in calcium data
            'volumeAcquisitionRate': 6.,  # rate at which volumes are acquired
            }
    dataSets = dh.loadMultipleDatasets(dataLog, pathTemplate=folder, dataPars = dataPars)
    keyList = np.sort(dataSets.keys())
    theDataset = '125716'
    drug_application = None
    transition = im_start = 11
    im_end = 5765


    for key in filter(lambda x: theDataset in x, keyList):
        print("Running "+key)
        time = dataSets[key]['Neurons']['I_Time_crop_noncontig']
        time_contig = dataSets[key]['Neurons']['I_Time']
        neurons = dataSets[key]['Neurons']['I_smooth_interp_crop_noncontig']
        neurons_withNaN = dataSets[key]['Neurons']['I_smooth'] # use this to find the untracked neurons after transition
        neurons_ZScore = dataSets[key]['Neurons']['ActivityFull'] # Z scored neurons to use to look at calcium traces
        velocity = dataSets[key]['Behavior_crop_noncontig']['AngleVelocity']

        # Only consider neurons that have timepoints present for at least 70% of the time during immobilization
        frac_nan_during_imm = np.true_divide(np.sum(np.isnan(neurons_withNaN[:, im_start:]), axis=1),
                                             neurons_withNaN[:, transition:].shape[1])
        valid_imm = np.argwhere(frac_nan_during_imm < 0.3)[:, 0]

        dset = dataSets[key]
        Iz = neurons_ZScore
        # Cluster on Z-scored interpolated data to get indices
        # Cluster only on the immobile portion; and only consider neurons prsent for both moving and immobile
        from scipy.cluster.hierarchy import linkage, dendrogram
        Z = linkage(dataSets[key]['Neurons']['Activity'][valid_imm,transition:])
        d = dendrogram(Z, no_plot=True)
        idx_clust = np.array(d['leaves'])

        if drug_application is not None:
            drug_app_time = time_contig[drug_application]
            drug_app_index = np.abs(time - drug_app_time).argmin()
        else:
            drug_app_time = None
            drug_app_index = None

        imm_start_time = time_contig[im_start]
        imm_start_index = np.abs(time - imm_start_time).argmin() #Index is for Noncontig
        end_time = time_contig[im_end]
        end_index = np.abs(time - end_time).argmin() # INdex is for noncontig





    #### Plot heatmap and behavior for whoel recording
    fig = plt.figure(figsize=(10, 12), constrained_layout=False)
    import matplotlib.gridspec as gridspec
    gs = gridspec.GridSpec(ncols=1, nrows=6, figure=fig, height_ratios=[2, .6, .6, .8, 1.1, 1.3], width_ratios=[5])
    ax = fig.add_subplot(gs[0, :])

    prcntile = 99.7
    num_Neurons=neurons_withNaN[valid_imm, :].shape[0]
    vmin = np.nanpercentile(neurons_withNaN[valid_imm, :], 0.1)
    vmax = np.nanpercentile(neurons_withNaN[valid_imm, :].flatten(), prcntile)
    pos = ax.imshow(neurons_withNaN[valid_imm[idx_clust], :], aspect='auto',
                    interpolation='none', vmin=vmin, vmax=vmax,
                    extent=[time_contig[0], time_contig[-1], -.5, num_Neurons - .5], origin='lower')
    ax.set_ylim(-.5, num_Neurons + .5)
    ax.set_yticks(np.arange(0, num_Neurons, 25))
    ax.set_xticks(np.arange(0, time_contig[-1], 60))
    # ax.set_title('I_smooth_interp_crop_noncontig_wnans  (smooth,  interpolated, common noise rejected, w/ large NaNs, mean- and var-preserved, outlier removed, photobleach corrected)')
    ax.set_xlabel('Time (s)')
    ax.set_ylabel('Neuron')
    ax.set_xlim(0, end_time)
    from matplotlib import ticker

    cb = fig.colorbar(pos, ax=ax)
    tick_locator = ticker.MaxNLocator(nbins=5)
    cb.locator = tick_locator
    cb.update_ticks()

    AVA1 = AVAR = 72#36
    AVA2 = AVAL = 63 #126#23
    AVAR_ci = np.squeeze(np.argwhere(valid_imm[idx_clust] == AVAR))
    AVAL_ci = np.squeeze(np.argwhere(valid_imm[idx_clust] == AVAL))

    yt = ax.get_yticks()
    yt = np.append(yt, [AVAR_ci, AVAL_ci])
    ytl = yt.tolist()
    ytl[-2:-1] = ["AVAR", "AVAL"]
    ax.set_yticks(yt)
    ax.set_yticklabels(ytl)



    axbeh = fig.add_subplot(gs[1, :], sharex=ax)
    axbeh.plot(dset['Neurons']['TimeFull'], dset['BehaviorFull']['AngleVelocity'], linewidth=1.5, color='k')
    fig.colorbar(pos, ax=axbeh)
    axbeh.axhline(linewidth=0.5, color='k')
    axbeh.set_xticks(np.arange(0, time_contig[-1], 60))
    axbeh.set_xlim(0, end_time)
    axbeh.set_ylim(-2, 2)
    axbeh.set_ylabel('Velocity')
    axbeh.axes.get_xaxis().set_visible(False)

    curv = dset['BehaviorFull']['Eigenworm3']
    axbeh = fig.add_subplot(gs[2, :], sharex=ax)
    axbeh.plot(dset['Neurons']['TimeFull'], curv, linewidth=1.5, color='brown')
    axbeh.set_ylabel('Curvature')
    fig.colorbar(pos, ax=axbeh)
    axbeh.axhline(linewidth=.5, color='k')
    axbeh.set_xticks(np.arange(0, time_contig[-1], 60))
    axbeh.set_xlim(0, end_time)
    axbeh.set_ylim(-20, 20)
    axbeh.axes.get_xaxis().set_visible(False)

    axava1 = fig.add_subplot(gs[3, :], sharex=ax)
    #axava1.plot(time_contig, dataSets[key]['Neurons']['gRaw'][AVAL,:])
    axava1.plot(time_contig, neurons_withNaN[AVAL,:], color='#1f77b4', label='AVAL')
    axava1.plot(time_contig, neurons_withNaN[AVAR, :], color='blue', label='AVAR')
    axava1.legend()
    axava1.set_xticks(np.arange(0, time_contig[-1], 60))
    axava1.set_ylabel('AVA')
    fig.colorbar(pos, ax=axava1)
    axava1.set_xlim(0, end_time)
    axava1.axes.get_xaxis().set_visible(False)





    #Repeat on the derivatives a la Kato et al
    def take_deriv(neurons):
        from prediction.Classifier import rectified_derivative
        _, _, nderiv = rectified_derivative(neurons)
        return nderiv
    Neuro_dFdt = take_deriv(neurons[valid_imm[idx_clust], :]).T
    Neuro = np.copy(neurons[valid_imm[idx_clust], ]).T  # I_smooth_interp_nonctoig



    def center_and_scale_around_immmobile_portion(recording, imm_start_index, end_index, with_std=False):
        # subtract and rescale the whole recording  so that the mean during hte immobile portion is zero
        # and, optionally, so that the variance during immobile portion is 1
        from sklearn.preprocessing import StandardScaler
        mean_scale = StandardScaler(copy=True, with_mean=True, with_std=with_std)
        mean_scale.fit(recording[imm_start_index:end_index, :]) #calcluate mean and or variance based on immobile
        return mean_scale.transform(recording) #rescale based on whole recording

    Neuro_mean_sub = center_and_scale_around_immmobile_portion(Neuro, imm_start_index, end_index, with_std=False)
    Neuro_z = center_and_scale_around_immmobile_portion(Neuro, imm_start_index, end_index, with_std=True)
    Neuro_dFdt_mean_sub = center_and_scale_around_immmobile_portion(Neuro_dFdt, imm_start_index, end_index, with_std=False)
    Neuro_dFdt_z = center_and_scale_around_immmobile_portion(Neuro_dFdt, imm_start_index, end_index, with_std=True)

    def print_AVAs_weights_in_pcs(AVAL_ci, AVAR_ci, pca, label=''):
        from sklearn.decomposition import PCA
        print(label)
        print("AVAL weights:", pca.components_[:, AVAL_ci])
        print("AVAR weights:", pca.components_[:, AVAR_ci])
        print("AVAL ranks:", np.where(np.argsort(np.abs(pca.components_)) == AVAL_ci))
        print("AVAR ranks:", np.where(np.argsort(np.abs(pca.components_)) == AVAR_ci))
        return

    def project_into_immobile_pcs(recording, imm_start_index, end_index, AVAL_ci=None, AVAR_ci=None, label=''):
        # Plot neural state space trajectories in first 3 PCs
        # also reduce dimensionality of the neural dynamics.
        from sklearn.decomposition import PCA
        nComp = 3  # pars['nCompPCA']
        pca = PCA(n_components=nComp, copy=True)
        pcs = pca.fit(recording[imm_start_index:end_index, :]).transform(recording)
        if AVAL_ci is not None and AVAR_ci is not None:
            print_AVAs_weights_in_pcs(AVAL_ci, AVAR_ci, pca, label=label)
        del pca
        return np.copy(pcs)


    pcs = project_into_immobile_pcs(Neuro_mean_sub, imm_start_index, end_index, AVAL_ci, AVAR_ci, label='activity')
    pcs_z = project_into_immobile_pcs(Neuro_z, imm_start_index, end_index, AVAL_ci, AVAR_ci, label='z-score')
    pcs_dFdt = project_into_immobile_pcs(Neuro_dFdt_mean_sub, imm_start_index, end_index, AVAL_ci, AVAR_ci, label='deriv')
    pcs_dFdt_z = project_into_immobile_pcs(Neuro_dFdt_z, imm_start_index, end_index, AVAL_ci, AVAR_ci, label='deriv Z-scored')
    

    #theta, phi =None, None
    theta, phi = 325, 267
    plot_trajectories(pcs, drug_app_index, imm_start_index, im_end, key + '\n F  PCA (minimally processed)', theta=theta, phi=phi)
    plot_trajectories(pcs_z, drug_app_index, imm_start_index, im_end, key + '\n F  PCA (z-scored)', theta=theta, phi=phi)
    plot_trajectories(pcs_dFdt, drug_app_index, imm_start_index, im_end, key + '\n F  dF/dt PCA (minimally processed)', color="#ff7f0e", theta=theta, phi=phi)
    plot_trajectories(pcs_dFdt_z, drug_app_index, imm_start_index, im_end, key + '\n F  dF/dt PCA (z-scored)', color="#ff7f0e", theta=theta, phi=phi)

    offset = 20
    axpc = fig.add_subplot(gs[4, :], sharex=ax)
    axpc.plot(time, pcs_z[:, 0], label='PC1', color='#6339F6')
    axpc.plot(time, offset + pcs_z[:, 1], label='PC2', color='#426BEB')
    axpc.plot(time, 2 * offset + pcs_z[:, 2], label='PC3', color='#3DC1F6')
    axpc.set_xticks(np.arange(0, time_contig[-1], 60))
    axpc.legend()
    fig.colorbar(pos, ax=axpc)
    axpc.set_xlim(0, end_time)
    axpc.axes.get_xaxis().set_visible(False)

    offset = 24
    axpcdf = fig.add_subplot(gs[5, :], sharex=ax)
    axpcdf.plot(time, pcs_dFdt_z[:, 0], label='PC1 dF/dt', color='#F6C802')
    axpcdf.plot(time, offset + pcs_dFdt_z[:, 1], label='PC2 dF/dt', color='#EB9B0F')
    axpcdf.plot(time, 2 * offset + pcs_dFdt_z[:, 2], label='PC3 dF/dt', color='#F66607')
    axpcdf.set_xticks(np.arange(0, time_contig[-1], 60))
    axpcdf.legend()
    fig.colorbar(pos, ax=axpcdf)
    axpc.set_xlim(0, end_time)

    codePath = userTracker.codePath()
    outputFolder = os.path.join(codePath,'figures/subpanels_revision/generatedFigs')
    import matplotlib.backends.backend_pdf
    pdf = matplotlib.backends.backend_pdf.PdfPages(os.path.join(outputFolder, key + "transition.pdf"))
    pdf.savefig(fig)
    pdf.close()








    print("Plotting.")





    plt.show()




print("Done")