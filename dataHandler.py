# -*- coding: utf-8 -*-
"""
Created on Fri Nov 10 15:41:10 2017
load and compare multiple data sets for behavior prediction.
@author: monika scholz
"""
import scipy.io
import os
import numpy as np
import matplotlib.pylab as plt
import scipy.interpolate
from scipy.signal import medfilt, deconvolve
from skimage.transform import resize
from sklearn import preprocessing
import makePlots as mp
from scipy.ndimage.filters import gaussian_filter1d
import h5py
from scipy.special import erf

def calcFFT(data, time_step=1/6.):
    """plot frequency of data"""
    fft = []
    if len(data.shape)>1:
        for line in data:
            ps = np.abs(np.fft.fft(line))**2
            freqs = np.fft.fftfreq(line.size, time_step)
            idx = np.argsort(freqs)
            fft.append(ps[idx])
    else:
        ps = np.abs(np.fft.fft(data))**2
        freqs = np.fft.fftfreq(data.size, time_step)
        idx = np.argsort(freqs)
        fft = ps[idx]
    return freqs[idx], fft

def makeEthogram(anglevelocity, pc3):
    """use rotated Eigenworms to create a new Ethogram."""
    etho = np.zeros((len(anglevelocity),1))
    # set forward and backward
    etho[np.where(anglevelocity>0.05)] = 1
    etho[np.where(anglevelocity<=-0.05)] = -1
    # overwrite this in case of turns
    etho[np.abs(pc3)>10] = 2
    return etho

def loadPoints(folder, straight = True):
    """get tracked points from Pointfile."""
    points = np.squeeze(scipy.io.loadmat(folder+'pointStatsNew.mat')['pointStatsNew'])
    if straight:
        return [p[0] for p in points]
    else:
        return [p[1] for p in points]
    
def loadEigenBasis(filename):
    """load the specific worm basis set."""
    eigenworms = scipy.io.loadmat(filename)['eigbasis']
    return eigenworms

def deconvolveCalcium(Y, show=False):
    """deconvolve with GCamp6s response digitized from Nature volume 499, pages 295–300 (18 July 2013)
        doi:10.1038/nature12354"""
    # fit function -- fitted with least squares from digitized data
    pars =  [ 0.38036106 , 0.00565365 , 1.00621729 , 0.31627363 ]
    def fitfunc(x,A,m, tau1, s):
        return A*erf((x-m)/s)*np.exp(-x/tau1)
    gcampXN = np.linspace(0,Y.shape[1]/6., Y.shape[1])
    gcampYN = fitfunc(gcampXN, *pars)
    Ydec = np.real(np.fft.ifft(np.fft.fft(Y, axis = 1)/np.fft.fft(gcampYN)))*np.sum(gcampYN)
    if show:
        plt.subplot(221)
        plt.plot(gcampX, gcampY)
        plt.plot(gcampXN[:18], gcampYN[:18])
        ax = plt.subplot(222)
        frq, psGC = calcFFT(gcampYN, time_step=1/6.)
        plt.plot(frq, psGC)
        ax.set_yscale('log',nonposy='clip')
        ax.set_xlabel('Frequency (Hz)')
        ax.set_ylabel("Power spectrum")

        Ydec = []
             line by line fft of neural signal
        frq, fft = calcFFT(Y, time_step=1/6.)
        for line in fft:
            plt.plot(frq, line, 'r', alpha=0.1)

        ax.set_yscale('log',nonposy='clip')
        ax.set_xlabel('Frequency (Hz)')
        ax.set_ylabel("Power spectrum")
        plt.show()
        vmax, vmin=1,0
        ax = plt.subplot(223)
        cax1 = ax.imshow(Y, aspect='auto', interpolation='none', origin='lower',vmax=vmax, vmin=vmin)
        ax = plt.subplot(224)
        pcax1 = ax.imshow(Ydec, aspect='auto', interpolation='none', origin='lower',vmax=vmax, vmin=vmin)
        plt.show()
    return Ydec
    

def estimateEigenwormError(clFull, eigenworms, volTime):
    """use the high resolution behavior to get a variance estimate.
    This will be wrong or meaningless if the centerlines were copied between frames."""
    loadCenterlines(folder, full = True)
    pcsNew, meanAngle, lengths, refPoint = calculateEigenwormsFromCL(cl, eigenworms)
    # reshape by indices of volume. First and last entry will be wonky
    clIndices = np.rint(np.interp(volTime, clTime, np.arange(len(clTime))))
    # split array by indices into blocks corresponding to volumes
    pcs = np.split(pcsNew, clIndices)
    print pcs.shape
    # calculate standard deviation
    pcsErr = np.std(pcs, axis=0)
    print pcsErr.shape
    #
    plt.plot(pcsNew[0])
    plt.plot(pcsNew[0])
    

def calculateEigenwormsFromCL(cl, eigenworms):
    """takes (x,y) pairs from centerlines and returns eigenworm coefficients."""
    # coordinate segments
    diffVec = np.diff(cl, axis=1)
    # calculate tangential vectors
    wcNew = np.unwrap(np.arctan2(-diffVec[:,:,1], diffVec[:,:,0]))
    #################these things are needed for reconstruction
    # get mean angle
    meanAngle = np.mean(wcNew, axis=1)
    # get segment lengths
    lengths = np.sqrt(diffVec[:,:,1]**2+diffVec[:,:,0]**2)
    # get overall alignment in space
    # reference point to start with
    refPoint = cl[:,0]
    # calculate mean subtracted tangent angles
    wcNew = wcNew-meanAngle[:, np.newaxis]
    # project onto Eigenworms
    pcsNew = np.dot(eigenworms,wcNew.T)
    return pcsNew, meanAngle, lengths, refPoint

def calculateCLfromEW(pcsNew, eigenworms, meanAngle, lengths, refPoint):
    """takes eigenworms and a few reference parameters to recreate centerline."""
    # now we recreate the worm
    wcR = np.dot(pcsNew.T, eigenworms) + meanAngle[:, np.newaxis] 
    # recreate tangent vectors with correct length
    tVecs = np.stack([lengths*np.cos(wcR), -lengths*np.sin(wcR)], axis=2)
    # start at same point as original CL
    clApprox = refPoint[:, np.newaxis] + np.cumsum(tVecs, axis=1)
    return clApprox       

def loadCenterlines(folder, full = False):
    """get centerlines from centerline.mat file"""
    tmp = scipy.io.loadmat(folder+'heatDataMS.mat')
    clTime = np.squeeze(tmp['clTime']) # 50Hz centerline times
    volTime =  np.squeeze(tmp['hasPointsTime'])# 6 vol/sec neuron times
    clIndices = np.rint(np.interp(volTime, clTime, np.arange(len(clTime))))
    #cl = scipy.io.loadmat(folder+'centerline.mat')['centerline']
    cl = np.rollaxis(scipy.io.loadmat(folder+'centerline.mat')['centerline'], 2,0)
    #if wormcentered:
    wc = np.rollaxis(scipy.io.loadmat(folder+'centerline.mat')['wormcentered'], 1,0)
    # eigenprojections
    ep = np.rollaxis(scipy.io.loadmat(folder+'centerline.mat')['eigenProj'],1,0)
    if full:
        # get all recorded centerlines during high-res movie
        clIndices = np.arange(int(np.min(clIndices), int(np.max(clIndices))))
    
    # reduce to volume time
    clNew = cl[clIndices.astype(int)]
    wcNew = wc[clIndices.astype(int)]
    epNew = ep[clIndices.astype(int)]
    
#    for cl in clNew[::10]:
#        plt.plot(cl[:,0], cl[:,1])
#    plt.show()
    return clNew, wcNew, epNew
    
def transformEigenworms(pc1, pc2, pc3, dataPars):
    """smooth Eigenworms and calculate associated metrics like velocity."""
    theta = np.unwrap(np.arctan2(pc2, pc1))
    #velo = savitzky_golay(theta, window_size=dataPars['savGolayWindow'], order=3, deriv=1, rate=1)
    velo = gaussian_filter1d(theta, dataPars['savGolayWindow'], order=1)
    # median filter the velocity and pca components 
    if dataPars['medianWindow'] < 3:
        return pc1, pc2, pc3, velo, theta
    #velo = scipy.signal.medfilt(velo, dataPars['medianWindow'])
    
#    pc1 = scipy.signal.medfilt(pc1, dataPars['medianWindow'])
#    pc2 = scipy.signal.medfilt(pc2, dataPars['medianWindow'])
#    pc3 = scipy.signal.medfilt(pc3, dataPars['medianWindow'])
    pc1 = gaussian_filter1d(pc1, dataPars['medianWindow'])
    pc2 = gaussian_filter1d(pc2, dataPars['medianWindow'])
    pc3 = gaussian_filter1d(pc3, dataPars['medianWindow'])
    
    return pc1, pc2, pc3, velo, theta


def preprocessNeuralData(R, G, dataPars):
    """zscore etc for neural data."""
    # prep neural data by masking nans
    mask = np.isnan(R)
    R[mask] = np.interp(np.flatnonzero(mask), np.flatnonzero(~mask), R[~mask])
    mask = np.isnan(G)
    G[mask] = np.interp(np.flatnonzero(mask), np.flatnonzero(~mask), G[~mask])
    
    # smooth with GCamp6 halftime = 1s
    RS =np.array([gaussian_filter1d(line,dataPars['windowGCamp']) for line in R])       
    GS =np.array([gaussian_filter1d(line,dataPars['windowGCamp']) for line in G])       
    YR = GS/RS
    if meansubtract:
        # long-window size smoothing filter to subtract overall fluctuation in SNR
        wind = 90
        mean = np.mean(rolling_window(np.mean(YR,axis=0), window=2*wind), axis=1)
        #pad with normal mean in front to correctly center the mean values
        mean = np.pad(mean, (wind,0), mode='constant', constant_values=(np.mean(np.mean(YR,axis=0)[:wind])))[:-wind]
        # do the same in the end
        mean[-wind:] = np.repeat(np.mean(np.mean(YR,axis=0)[:-wind]), wind)
        YN = YR-mean
    else:
        YN = YR
    # zscore values 
    Y =  preprocessing.scale(YN.T).T
    return Y

def loadData(folder, dataPars):
    """load matlab data."""
    data = scipy.io.loadmat(folder+'heatDataMS.mat')
    ew= 1
    # unpack behavior variables
    ethoOrig, xPos, yPos, vel, pc12, pc3 = data['behavior'][0][0].T
#    # get eigenworm file
    if ew:
        ewfile = "eigenWorms.mat"
        # ncomponents controls how many we use
        nComp = 3
        eigenworms = loadEigenBasis(ewfile)[:nComp]
        eigenworms = resize(eigenworms, (nComp,99))
        # deal with eigenworms -- get them directly from centerlines
        cl, wc, ep = loadCenterlines(folder)
    #    # get prefactors from eigenworm projection
        pcs, meanAngle, lengths, refPoint = calculateEigenwormsFromCL(cl, eigenworms)
        print 'Done loading eigenworms '
    else:
        pcs = np.vstack([pc12[:,1],pc12[:,0], pc3[:,0]])
    
    # Rotate Eigenworms
    if dataPars['rotate']:
        # load rotation matrix
        R = np.loadtxt(folder+'../'+'Rotationmatrix.dat')
        pcs = np.array(np.dot(R, pcs))
    pc1, pc2, pc3 = pcs
    #mask nans in eigenworms by linear interpolation
    mask1 = np.isnan(pc1)
    mask2 = np.isnan(pc2)
    mask3 = np.isnan(pc3)
    if np.any(mask1):
        pc1[mask1] = np.interp(np.flatnonzero(mask1), np.flatnonzero(~mask1), pc1[~mask1])
    if np.any(mask2):
        pc2[mask2] = np.interp(np.flatnonzero(mask2), np.flatnonzero(~mask2), pc2[~mask2])
    if np.any(mask3):
        pc3[mask3] = np.interp(np.flatnonzero(mask3), np.flatnonzero(~mask3), pc3[~mask3])
    
    # do Eigenworm transformations and calculate velocity etc.
#    # median filter the Eigenworms
    pc1, pc2, pc3, velo, theta = transformEigenworms(pc1, pc2, pc3, dataPars)

    # ethogram redone
    etho = makeEthogram(velo, pc3)
    #etho = ethoOrig
    
    #load neural data
    R = np.array(data['rPhotoCorr'])
    G = np.array(data['gPhotoCorr'])
    Y = preprocessNeuralData(R, G, dataPars)
    
    # store relevant indices
    nonNan = np.arange(0, YR.shape[1])
    nonNan  = np.where(np.any(np.isfinite(data['rPhotoCorr']),axis=0))[0]
    
    # create a time axis in seconds
    T = np.arange(Y.shape[1])/6.
    # redo time axis in seconds for nan issues
    T = np.arange(Y[:,nonNan].shape[1])/6.
    
    # unpack neuron position (only one frame, randomly chosen)
    try:
        neuroPos = data['XYZcoord'][order].T
    except KeyError:
        neuroPos = []
        print 'No neuron positions:', folder
    YD = deconvolveCalcium(Y) 
    if 0:
        #### show what pipeline does
        titles= ['Bleaching corrected', 'Gaussian filter $\sigma=5$', 'Rolling mean (30 s) ', 'Z score']
        for i, hm in enumerate([G[order]/R[order],YR, YN, Y]):
            ax=plt.subplot(2,2,i+1)
            low, high = np.percentile(hm, [2.28, 97.72])#[ 15.87, 84.13])
            ax.set_title(titles[i])
            cax1 = ax.imshow( hm, aspect='auto', interpolation='none', origin='lower',extent=[0,T[-1],len(Y),0],vmax=high, vmin=low)
            ax.set_xlabel('Time (s)')
            ax.set_ylabel("Neuron")
        plt.tight_layout()
        plt.show()
        
        for i, hm in enumerate([G[order]/R[order],YR, YN, Y]):
            ax=plt.subplot(2,2,i+1)
            f, ps = calcFFT(hm, time_step=1/6.)
            ax.set_title(titles[i])
            m, s = np.mean(ps, axis=0), np.std(ps, axis=0)
            ax.plot(f, m, 'r')
            #ax.fill_between(f, m-s, m+s, alpha=0.2, color='r')
            ax.set_yscale('log',nonposy='clip')
            ax.set_xlabel('Frequency (Hz)')
            ax.set_ylabel("Power spectrum")
        plt.tight_layout()
        plt.show()
    # create a dictionary structure of these data
    dataDict = {}
    
    dataDict['CL'] = 
    dataDict['Behavior'] = {}

    tmpData = [vel[:,0], pc1, pc2, pc3, velo, theta, etho, xPos, yPos]
    for kindex, key in enumerate(['CMSVelocity', 'Eigenworm1', 'Eigenworm2', 'Eigenworm3',\
                'AngleVelocity','Theta', 'Ethogram', 'X', 'Y']):
        dataDict['Behavior'][key] = tmpData[kindex][nonNan]
    dataDict['Neurons'] = {}
    dataDict['Neurons']['Time'] =  np.arange(Y[:,nonNan].shape[1])/6.#T[nonNan]
    dataDict['Neurons']['Activity'] = Y[:,nonNan]
    dataDict['Neurons']['rankActivity'] = rankTransform(Y)[:,nonNan]
    dataDict['Neurons']['Positions'] = neuroPos
    return dataDict
    
    
def loadMultipleDatasets(dataLog, pathTemplate, dataPars):
    """load matlab files containing brainscanner data. 
    string dataLog: file containing Brainscanner names with timestamps e.g. BrainScanner20160413_133747.
    path pathtemplate: relative or absoluet location of the dataset with a formatter replacing the folder name. e.g.
                        GoldStandardDatasets/{}_linkcopy

    return: dict of dictionaries with neuron and behavior data
    """
    datasets={}
    for lindex, line in enumerate(np.loadtxt(dataLog, dtype=str, ndmin = 2)):
        folder = pathTemplate.format(line[0])
        datasets[line[0]] = loadData(folder, dataPars)
    return datasets

def loadNeuronPositions(filename):
    x = scipy.io.loadmat(filename)['x']
    y = scipy.io.loadmat(filename)['y']
    z = scipy.io.loadmat(filename)['z']
    neuronID = scipy.io.loadmat(filename)['ID']
    # remove non-head neurons
    indices = np.where((y<-2.3)&(x<0.1))
    return np.stack((neuronID[indices],x[indices],y[indices],z[indices]))

def rankTransform(neuroMap):
    """takes a matrix and transforms values into rank within the colum. ie. neural dynamics: for each neuron
    calculate its rank at the current time."""
    temp = neuroMap.argsort(axis=0)
    rank = temp.argsort(axis=0)
    return rank


def rolling_window(a, window):
    a = np.pad(a, (0,window), mode="constant", constant_values=(np.nan,))
    shape = a.shape[:-1] + (a.shape[-1] - window, window)
    strides = a.strides + (a.strides[-1],)
    
    return np.lib.stride_tricks.as_strided(a, shape=shape, strides=strides)
    

def saveDictToHDF(filePath, d):
    f = h5py.File(filePath,'w')
    for fnKey in d.keys():
        for amKey in d[fnKey].keys():
            for attKey in d[fnKey][amKey].keys():
                if type(d[fnKey][amKey][attKey]) is not dict:
                    dataPath = '/%s/%s/%s'%(fnKey,amKey,attKey)
                    f.create_dataset(dataPath,data=d[fnKey][amKey][attKey])
                else:
                    for bKey in d[fnKey][amKey][attKey].keys():
                        
                        dataPath = '/%s/%s/%s/%s'%(fnKey,amKey,attKey,bKey)
                        f.create_dataset(dataPath,data=d[fnKey][amKey][attKey][bKey])
    f.close()
    return

def loadDictFromHDF(filePath):
    f = h5py.File(filePath,'r')
    d = {}
    for fnKey in f.keys():
        d[fnKey] = {}
        for amKey in f[fnKey].keys():
            d[fnKey][amKey] = {}
            for attKey in f[fnKey][amKey].keys():
                if isinstance(f[fnKey][amKey][attKey], h5py.Dataset):
                    d[fnKey][amKey][attKey] = f[fnKey][amKey][attKey][...]
                else:
                    d[fnKey][amKey][attKey] = {}
                    for bKey in f[fnKey][amKey][attKey].keys():
                        d[fnKey][amKey][attKey][bKey] = f[fnKey][amKey][attKey][bKey][...]
                        
    f.close()
    return d

