# Copyright (C) 2016 Antoine Carme <Antoine.Carme@Laposte.net>
# All rights reserved.

# This file is part of the Python Automatic Forecasting (PyAF) library and is made available under
# the terms of the 3 Clause BSD license

import pandas as pd
import numpy as np

# from memory_profiler import profile

from . import Time as tsti
from . import Perf as tsperf
from . import Plots as tsplot
from . import Utils as tsutil


# for timing
import time

class cAbstractAR:
    def __init__(self , cycle_residue_name, iExogenousInfo = None):
        self.mTimeInfo = tsti.cTimeInfo()
        self.mCycleFrame = pd.DataFrame()
        self.mARFrame = pd.DataFrame()        
        self.mCycleResidueName = cycle_residue_name
        self.mCycle = None
        self.mTrend = None
        self.mComplexity = None;
        self.mFormula = None;
        self.mTargetName = self.mCycleResidueName;
        self.mInputNames = [];
        self.mExogenousInfo = iExogenousInfo;
        self.mLagsForSeries = {}

    def compute_ar_residue(self, df):
        target = df[self.mCycleResidueName].values
        lSignal = df[self.mSignal].values
        lTrend = df[self.mTrend.mOutName].values
        lCycle = df[self.mCycle.mOutName].values
        lAR = df[self.mOutName].values
        if(self.mDecompositionType in ['T+S+R']):
            df[self.mOutName + '_residue'] = lSignal - lTrend - lCycle - lAR
        if(self.mDecompositionType in ['TS+R']):
            df[self.mOutName + '_residue'] = lSignal - lTrend * lCycle - lAR
        else:
            df[self.mOutName + '_residue'] = lSignal - (lTrend * lCycle * lAR)
        # df_detail = df[[self.mSignal, self.mTrend.mOutName, self.mCycle.mOutName, self.mOutName, self.mOutName + '_residue']]
        # print("compute_ar_residue_detail ", (self.mOutName, self.mDecompositionType, df_detail.describe(include='all').to_dict()))
        df[self.mOutName + '_residue'] = df[self.mOutName + '_residue'].astype(target.dtype)
        
    def plot(self):
        tsplot.decomp_plot(self.mARFrame, self.mTimeInfo.mNormalizedTimeColumn,
                           self.mCycleResidueName, self.mOutName , self.mOutName + '_residue', horizon = self.mTimeInfo.mHorizon);


    def register_lag(self, series, p):
        name = series+'_Lag' + str(p);
        # print("register_lag", (series , p , name))
        self.mInputNames.append(name);
        self.mLagsForSeries[series] = self.mLagsForSeries.get(series , [])
        self.mLagsForSeries[series].append(p)
        
    def dumpCoefficients(self):
        pass
    
    def computePerf(self):
        self.mARFitPerf= tsperf.cPerf();
        self.mARForecastPerf= tsperf.cPerf();
        (lFrameFit, lFrameForecast, lFrameTest) = self.mSplit.cutFrame(self.mARFrame);
        self.mARFitPerf.compute(
            lFrameFit[self.mCycleResidueName], lFrameFit[self.mOutName], self.mOutName)
        self.mARForecastPerf.compute(
            lFrameForecast[self.mCycleResidueName], lFrameForecast[self.mOutName], self.mOutName)

    def shift_series(self, series, p, idefault):
        N = series.shape[0];
        lType = series.dtype
        first_values = np.full((p), idefault, dtype=lType)
        new_values = np.hstack((first_values, series.values[0:N-p]));
        new_values = new_values.astype(lType)
        return new_values;

    def getDefaultValue(self, series):
        return self.mDefaultValues[series];

    def is_used(self, name):
        return True
    
    def addLagForForecast(self, df, lag_df, series, p):
        name = series+'_Lag' + str(p);
        if(not self.is_used(name)):
            return
        assert(p in self.mLagsForSeries[series])
        lSeries = df[series];
        lShiftedSeries = self.shift_series(lSeries, p , self.mDefaultValues[series]); 
        lag_df[name] = lShiftedSeries;
        
    def generateLagsForForecast(self, df):
        lag_df = pd.DataFrame()
        lag_df[self.mCycleResidueName] = df[self.mCycleResidueName].reset_index(drop=True)
        for p in self.mLagsForSeries[self.mCycleResidueName]:
            # signal lags ... plain old AR model
            self.addLagForForecast(df, lag_df, self.mCycleResidueName, p);
        # Exogenous variables lags
        if(self.mExogenousInfo is not None):
            # print(self.mExogenousInfo.mEncodedExogenous);
            # print(df.columns);
            for ex in self.mExogenousInfo.mEncodedExogenous:
                if(self.mLagsForSeries.get(ex)):
                    for p in self.mLagsForSeries[ex]:
                        self.addLagForForecast(df, lag_df, ex, p);
        return lag_df;


class cZeroAR(cAbstractAR):
    def __init__(self , cycle_residue_name):
        super().__init__(cycle_residue_name, None)
        self.mOutName = self.mCycleResidueName +  '_NoAR'
        self.mNbLags = 0;
        self.mFormula = "NoAR";
        self.mComplexity = 0;
        self.mConstantValue = 0.0
        
    def fit(self):
        series = self.mCycleResidueName; 
        self.mTime = self.mTimeInfo.mTime;
        self.mSignal = self.mTimeInfo.mSignal;
        self.mConstantValue = 0.0
        if(self.mDecompositionType in ['TSR']):
            # multiplicative models
            self.mConstantValue = 1.0
        
        # self.mTimeInfo.addVars(self.mARFrame);
        # self.mARFrame[series] = self.mCycleFrame[series]
        self.mARFrame[self.mOutName] = self.mConstantValue;
        self.mARFrame[self.mCycle.mOutName] = self.mConstantValue;
        self.mARFrame[self.mTrend.mOutName] = self.mConstantValue;
        self.compute_ar_residue(self.mARFrame)
        assert(self.mARFrame.shape[0] > 0)
                

    def transformDataset(self, df, horizon_index = 1):
        df[self.mOutName] = self.mConstantValue;
        self.compute_ar_residue(df)
        assert(df.shape[0] > 0)
        return df;



class cAutoRegressiveEstimator:
    def __init__(self):
        self.mTimeInfo = tsti.cTimeInfo()
        self.mCycleFrame = pd.DataFrame()
        self.mARFrame = pd.DataFrame()
        self.mARList = {}
        self.mExogenousInfo = None;
        
    def plotAR(self):
        for trend in self.mTrendList:
            for cycle in self.mCycleList[trend]:
                cycle_residue = cycle.getCycleResidueName();
                for autoreg in self.mARList[cycle_residue]:
                    autoreg.plot(); 

    def is_not_constant(self, iSeries):
        lFirst = iSeries[0];
        for lValue in iSeries[1:]:
            if(lValue != lFirst):
                return True;
        return False;

    def shift_series(self, series, p):
        N = series.shape[0];
        lType = series.dtype
        first_values = np.full((p), series.values[0], dtype=lType)
        new_values = np.hstack((first_values, series.values[0:N-p]));
        new_values = new_values.astype(lType)
        return new_values;

    def addLagForTraining(self, df, lag_df, series, autoreg, p):
        name = series+'_Lag' + str(p);
        if(name in lag_df.columns):
            autoreg.register_lag(series, p);
            return lag_df;

        lSeries = df[series];
        lShiftedSeries = self.shift_series(lSeries, p);
        self.mDefaultValues[series] = lSeries.values[0];
        
        lShiftedEstim = self.mSplit.getEstimPart(lShiftedSeries);
        lAcceptable = self.is_not_constant(lShiftedEstim);
        if(lAcceptable):
            autoreg.register_lag(series, p);
            lag_df[name] = lShiftedSeries;
            self.mLagOrigins[name] = series;
        return lag_df;

    def addLagsForTraining(self, df, cycle_residue, iNeedExogenous = False):
        logger = tsutil.get_pyaf_logger();
        add_lag_start_time = time.time()
        for autoreg in self.mARList[cycle_residue]:
            P = autoreg.mNbLags;
            for p in range(1,P+1):
                # signal lags ... plain old AR model
                self.addLagForTraining(df, self.mARFrame, cycle_residue, autoreg, p);
            # Avoid dataframe fragemntation.
            self.mARFrame = self.mARFrame.copy()

            # Exogenous variables lags
            if(autoreg.mExogenousInfo is not None):
                P1 = P;
                lExogCount = len(autoreg.mExogenousInfo.mEncodedExogenous);
                lNbVars = P * lExogCount;
                if(lNbVars >= self.mOptions.mMaxFeatureForAutoreg):
                   P1 = self.mOptions.mMaxFeatureForAutoreg // lExogCount;
                autoreg.mNbExogenousLags = P1;
                for ex in autoreg.mExogenousInfo.mEncodedExogenous:
                    for p in range(1,P1+1):
                        # print(autoreg.mExogenousInfo.mEncodedExogenous);
                        # print(df.columns);
                        self.addLagForTraining(df, self.mARFrame, ex, autoreg, p);
                    # Avoid dataframe fragemntation.
                    self.mARFrame = self.mARFrame.copy()

            # print("AUTOREG_DETAIL" , P , len(autoreg.mInputNames));
            if(autoreg.mExogenousInfo is not None):
                assert((P + P*len(autoreg.mExogenousInfo.mEncodedExogenous)) >= len(autoreg.mInputNames));
            else:
                assert(P >= len(autoreg.mInputNames));
        if(self.mOptions.mDebugProfile):
            logger.info("LAG_TIME_IN_SECONDS " + self.mTimeInfo.mSignal + " " +
                  str(len(self.mARFrame.columns)) + " " +
                  str(time.time() - add_lag_start_time))


    # @profile
    def estimate_ar_models_for_cycle(self, cycle_residue):
        logger = tsutil.get_pyaf_logger();
        self.mARFrame = pd.DataFrame();
        self.mTimeInfo.addVars(self.mARFrame);
        self.mCycleFrame[cycle_residue] = self.mCycleFrame[cycle_residue]            
        self.mARFrame[cycle_residue] = self.mCycleFrame[cycle_residue]            

        self.mDefaultValues = {};
        self.mLagOrigins = {};

        if(self.mOptions.mDebugProfile):
            logger.info("AR_MODEL_ADD_LAGS_START '" +
                  cycle_residue + "' " + str(self.mCycleFrame.shape[0]) + " "
                  + str(self.mARFrame.shape[1]));

        self.addLagsForTraining(self.mCycleFrame, cycle_residue);

        if(self.mOptions.mDebugProfile):
            logger.info("AR_MODEL_ADD_LAGS_END '" +
                  cycle_residue + "' " + str(self.mCycleFrame.shape[0]) + " "
                  + str(self.mARFrame.shape[1]));

        # print(self.mARFrame.info());

        lCleanListOfArModels = [];
        for autoreg in self.mARList[cycle_residue]:
            self.mARFrame[autoreg.mTrend.mOutName] = autoreg.mCycle.mTrendFrame[autoreg.mTrend.mOutName]            
            self.mARFrame[autoreg.mCycle.mOutName] = self.mCycleFrame[autoreg.mCycle.mOutName]            
            if((autoreg.mFormula == "NoAR") or (len(autoreg.mInputNames) > 0)):
                lCleanListOfArModels.append(autoreg);
        self.mARList[cycle_residue] = lCleanListOfArModels;
        
        for autoreg in self.mARList[cycle_residue]:
            start_time = time.time()
            if(self.mOptions.mDebugProfile):
                logger.info("AR_MODEL_START_TRAINING_TIME '" +
                      cycle_residue + "' " + str(self.mCycleFrame.shape[0]) +
                      " " +  str(len(autoreg.mInputNames)) + " " + str(start_time));
            autoreg.mOptions = self.mOptions;
            autoreg.mCycleFrame = self.mCycleFrame;
            autoreg.mARFrame = self.mARFrame
            autoreg.mTimeInfo = self.mTimeInfo;
            autoreg.mSplit = self.mSplit;
            autoreg.mLagOrigins = self.mLagOrigins;
            autoreg.mDefaultValues = self.mDefaultValues;
            autoreg.mDecompositionType = self.mDecompositionType
            autoreg.fit();
            if(self.mOptions.mDebugPerformance):
                autoreg.computePerf();
            end_time = time.time()
            lTrainingTime = round(end_time - start_time , 2);
            if(self.mOptions.mDebugProfile):
                logger.info("AR_MODEL_TRAINING_TIME_IN_SECONDS '" +
                      autoreg.mOutName + "' " + str(self.mCycleFrame.shape[0]) +
                      " " +  str(len(autoreg.mInputNames)) + " " + str(lTrainingTime));

    def check_not_nan(self, sig , name):
        #print("check_not_nan");
        if(np.isnan(sig[:-1]).any()):
            logger = tsutil.get_pyaf_logger();
            logger.error("CYCLE_RESIDUE_WITH_NAN_IN_SIGNAL" + str(sig));
            raise tsutil.Internal_PyAF_Error("INVALID_COLUMN _FOR_CYCLE_RESIDUE ['"  + name + "'");
        pass


    
        
    # @profile
    def estimate(self):
        from . import Keras_Models as tskeras
        from . import Scikit_Models as tsscikit
        from . import Intermittent_Models as interm

        logger = tsutil.get_pyaf_logger();
        mARList = {}
        lNeedExogenous = False;
        for trend in self.mTrendList:
            for cycle in self.mCycleList[trend]:
                cycle_residue = cycle.getCycleResidueName();
                if(self.mOptions.mDebug):
                    self.check_not_nan(self.mCycleFrame[cycle_residue], cycle_residue)
                self.mARList[cycle_residue] = [];
                if(self.mOptions.mActiveAutoRegressions['NoAR']):
                    self.mARList[cycle_residue] = [ cZeroAR(cycle_residue)];
                lLags = self.mCycleFrame[cycle_residue].shape[0] // 4;
                if(lLags >= self.mOptions.mMaxAROrder):
                    lLags = self.mOptions.mMaxAROrder;
                lKeep = (self.mCycleFrame[cycle_residue].shape[0] > 12) and (self.mCycleFrame[cycle_residue].std() > 0.00001)
                if(not lKeep):
                    logger.info("SKIPPING_AR_MODELS_WITH_LOW_VARIANCE_CYCLE_RESIDUE '" + cycle_residue + "'");
                    
                if(lKeep):
                    if(self.mOptions.mActiveAutoRegressions['AR']):
                        lAR = tsscikit.cAutoRegressiveModel(cycle_residue, lLags);
                        self.mARList[cycle_residue] = self.mARList[cycle_residue] + [lAR];
                    if(self.mOptions.mActiveAutoRegressions['ARX'] and (self.mExogenousInfo is not None)):
                        lARX = tsscikit.cAutoRegressiveModel(cycle_residue, lLags,
                                                             self.mExogenousInfo);
                        self.mARList[cycle_residue] = self.mARList[cycle_residue] + [lARX];
                        lNeedExogenous = True;
                    if(self.mOptions.mActiveAutoRegressions['LSTM']):
                        if(self.mOptions.canBuildKerasModel('LSTM')):
                            lLSTM = tskeras.cLSTM_Model(cycle_residue, lLags,
                                                        self.mExogenousInfo);
                            self.mARList[cycle_residue] = self.mARList[cycle_residue] + [lLSTM];
                        else:
                            logger.debug("SKIPPING_MODEL_WITH_KERAS '" + 'LSTM');
                        
                    if(self.mOptions.mActiveAutoRegressions['MLP']):
                        if(self.mOptions.canBuildKerasModel('MLP')):
                            lMLP = tskeras.cMLP_Model(cycle_residue, lLags,
                                                      self.mExogenousInfo);
                            self.mARList[cycle_residue] = self.mARList[cycle_residue] + [lMLP];
                        else:
                            logger.debug("SKIPPING_MODEL_WITH_KERAS '" + 'MLP');
                        
                    if(self.mOptions.mActiveAutoRegressions['SVR']):
                        lSVR = tsscikit.cSVR_Model(cycle_residue, lLags);
                        self.mARList[cycle_residue] = self.mARList[cycle_residue] + [lSVR];
                    if(self.mOptions.mActiveAutoRegressions['SVRX'] and (self.mExogenousInfo is not None)):
                        lSVRX = tsscikit.cSVR_Model(cycle_residue, lLags,
                                                       self.mExogenousInfo);
                        self.mARList[cycle_residue] = self.mARList[cycle_residue] + [lSVRX];
                        lNeedExogenous = True;
                    if(self.mOptions.mActiveAutoRegressions['XGB']):
                        if(self.mOptions.canBuildXGBoostModel('XGB')):
                            lXGB = tsscikit.cXGBoost_Model(cycle_residue, lLags)
                            self.mARList[cycle_residue] = self.mARList[cycle_residue] + [lXGB];
                        else:
                            logger.debug("SKIPPING_MODEL_WITH_XGBOOST '" + 'XGB');
                    if(self.mOptions.mActiveAutoRegressions['XGBX'] and (self.mExogenousInfo is not None)):
                        if(self.mOptions.canBuildXGBoostModel('XGBX')):
                            lXGBX = tsscikit.cXGBoost_Model(cycle_residue, lLags,
                                                            self.mExogenousInfo);
                            self.mARList[cycle_residue] = self.mARList[cycle_residue] + [lXGBX];
                            lNeedExogenous = True;
                        else:
                            logger.debug("SKIPPING_MODEL_WITH_XGBOOST '" + 'XGBX');
                            
                    if(self.mOptions.mActiveAutoRegressions['LGB']):
                        if(self.mOptions.canBuildLightGBMModel('LGB')):
                            lLGB = tsscikit.cLightGBM_Model(cycle_residue, lLags)
                            self.mARList[cycle_residue] = self.mARList[cycle_residue] + [lLGB];
                        else:
                            logger.debug("SKIPPING_MODEL_WITH_LIGHTGBM '" + 'LGB');
                    if(self.mOptions.mActiveAutoRegressions['LGBX'] and (self.mExogenousInfo is not None)):
                        if(self.mOptions.canBuildLightGBMModel('LGBX')):
                            lLGBX = tsscikit.cLightGBM_Model(cycle_residue, lLags,
                                                             self.mExogenousInfo);
                            self.mARList[cycle_residue] = self.mARList[cycle_residue] + [lLGBX];
                            lNeedExogenous = True;
                        else:
                            logger.debug("SKIPPING_MODEL_WITH_LIGHTGBM '" + 'LGBX');
                    if(self.mOptions.mActiveAutoRegressions['CROSTON']):
                        lIsSignalIntermittent = interm.is_signal_intermittent(self.mCycleFrame[cycle_residue] , self.mOptions)
                        if(lIsSignalIntermittent):
                            lCroston = interm.cCroston_Model(cycle_residue, lLags)
                            self.mARList[cycle_residue] = self.mARList[cycle_residue] + [lCroston];
                if(len(self.mARList[cycle_residue]) == 0):
                    self.mARList[cycle_residue] = [ cZeroAR(cycle_residue)];
                for lAR in self.mARList[cycle_residue]:
                    lAR.mCycle = cycle
                    lAR.mTrend = cycle.mTrend

        if(lNeedExogenous):
            if(self.mOptions.mDebugProfile):
                logger.info("AR_MODEL_ADD_EXOGENOUS '" + str(self.mCycleFrame.shape[0]) +
                      " " + str(len(self.mExogenousInfo.mEncodedExogenous)));
            self.mCycleFrame = self.mExogenousInfo.transformDataset(self.mCycleFrame);
        
        for cycle_residue in self.mARList.keys():
            self.estimate_ar_models_for_cycle(cycle_residue);
            for autoreg in self.mARList[cycle_residue]:
                autoreg.mARFrame = pd.DataFrame();
            del self.mARFrame;
