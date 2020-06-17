%Goal of this script is to genreate a table to relate:
%   - Frame number of a low mag recording
%   - time in seconds shown on the low mag recording
%   - Volume number from high magnification recording 
%
% Note we will select the brightfield frame number as the common timeline upon
% which all other values are interpolated onto
%
% Instructions: you need to add 3dbrain from communcal code to your path so
% that you have access to the tripleFlashAlign Function/
% Then when you runt he GUI will promt you for the brainscanner folder to
% read in.


%Load the spreadsheet
%csvfile = '/home/leifer/workspace/PredictionCode/figures/Debugging/compareOmegaTurns/EscapeResponseTimePoints.csv';
%T = readtable(csvfile,'Format','%s%s%f%u%u%u%u%s','Delimiter',',')



vlc_bf_FrameRate = 30.00003; %frames / vlc second




%Prompt user to select a brainscanner folder and align flashes in brightfield and
%fluorescence
[bfAll, fluorAll, hiResData] =  tripleFlashAlign();

%We will select the time of each brightfield frame as the timeline to align
%to
commonTime = bfAll.frameTime; 
bf_frame_indx1 = 1:length(commonTime); %we will index the brightfield frame starting at 1
bf_vlc_time_mins =  floor( (bf_frame_indx1 /  vlc_bf_FrameRate)  /  60 );
bf_vlc_time_secs =  floor( mod(bf_frame_indx1 /  vlc_bf_FrameRate, 60)   );


%skip repeated time stamps for interpolation otherwise interpolation
%will error
ind = find(diff(hiResData.frameTime)~=0);
volume = round(interp1(hiResData.frameTime(ind), double(hiResData.stackIdx(ind)), commonTime,'linear')); 


T = array2table([commonTime, bf_frame_indx1', bf_vlc_time_mins', bf_vlc_time_secs', volume], 'VariableNames',{'LabTime_Secs', 'BF_Frame', 'VLC_BF_Mins', 'VLC_BF_Secs', 'volume' });

writetable(T,'realtiveTimingWithVolumes.txt','Delimiter',',') 





assert(0,'everything worked')



% These are the relevant timepoints on the VLC video of the brightfield
%vlc_bf = [T.StartMin*60 + T.StartSec, T.EndMin * 60 + T.EndSec ]; %in vlc seconds






for k=1:size(vlc_bf,1)
    bf(k,:) = vlc_bf(k,:).*vlc_bf_FrameRate(k); % brightfield frame number
    %Get the time alignment between brightfield and hi magnification images
    
    % by comparing flashes
    [bfAll, ~, hiResData] =  tripleFlashAlign(T.BrainScannerFolder{k});

    commonTime(k,:) = [bfAll.frameTime(round(bf(k, START))), bfAll.frameTime(round(bf(k,FINISH)))];
    
    %skip repeated time stamps for interpolation otherwise interpolation
    %will error
    ind = find(diff(hiResData.frameTime)~=0);
    volume(k,:) = round(interp1(hiResData.frameTime(ind),hiResData.stackIdx(ind),commonTime(k,:),'linear'));

end

U=[T,array2table(volume,'VariableNames',{'StartVolume','EndVolume'})];
writetable(U,'realtiveTimingWithVolumes.txt','Delimiter',',') 


