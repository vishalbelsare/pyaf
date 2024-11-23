import numpy as np
import pandas as pd
from . import SignalDecomposition_AR as tsar
from . import Utils as tsutil
from . import Complexity as tscomplex

class cAbstract_Scikit_Model(tsar.cAbstractAR):
    def __init__(self , cycle_residue_name, P , iExogenousInfo = None):
        super().__init__(cycle_residue_name, iExogenousInfo)
        self.mNbLags = P;
        self.mNbExogenousLags = P;
        self.mScikitModel = None;
        self.mFeatureSelector = None
        self.mComplexity = tscomplex.eModelComplexity.High;
        self.set_name();

    def dumpCoefficients(self, iMax=10):
        # tsutil.print_pyaf_detailed_info(self.mScikitModel.__dict__);
        pass

    def build_Scikit_Model(self):
        assert(0);

    def set_name(self):
        assert(0);

    def get_used_variables(self):
        lUsed = []
        for (series, lList_p) in self.mLagsForSeries.items():
            used = [p for p in lList_p if (series+'_Lag' + str(p) in self.mInputNamesAfterSelection)]
            if(len(used) > 0):
                lUsed = lUsed + [series]
        return lUsed

    def fit(self):
        # tsutil.print_pyaf_detailed_info("ESTIMATE_SCIKIT_MODEL_START" , self.mCycleResidueName);

        self.build_Scikit_Model();
        
        series = self.mCycleResidueName; 
        self.mTime = self.mTimeInfo.mTime;
        self.mSignal = self.mTimeInfo.mSignal;
        lAREstimFrame = self.mSplit.getEstimPart(self.mARFrame)

        lARInputs = lAREstimFrame[self.mInputNames].values

        lARTarget = lAREstimFrame[series].values
        # tsutil.print_pyaf_detailed_info(len(self.mInputNames), lARInputs.shape , lARTarget.shape)
        assert(lARInputs.shape[1] > 0);
        assert(lARTarget.shape[0] > 0);
        assert(lARInputs.shape[1] == len(self.mInputNames))

        from sklearn.feature_selection import SelectKBest
        from sklearn.feature_selection import f_regression
        lMaxFeatures = self.mOptions.mMaxFeatureForAutoreg;
        if(lMaxFeatures >= lARInputs.shape[1]):
            lMaxFeatures = lARInputs.shape[1];
        if(lMaxFeatures >= (lARInputs.shape[0] // 4)):
            lMaxFeatures = lARInputs.shape[0] // 4;
        self.mFeatureSelector =  SelectKBest(f_regression, k= lMaxFeatures);
        try:
            self.mFeatureSelector.fit(lARInputs, lARTarget);
        except Exception as e:
            tsutil.print_pyaf_detailed_info("SCIKIT_MODEL_FEATURE_SELECTION_FAILURE" , self.mOutName, lARInputs.shape, e);
            if(self.mOptions.mDebug):
                df1 = pd.DataFrame(lARInputs);
                df1.columns = self.mInputNames
                df1['TGT'] = lARTarget;
                # df1.to_csv("SCIKIT_MODEL_FEATURE_SELECTION_FAILURE.csv.gz" , compression='gzip');
            # issue  #72 : ignore feature selection in case of failure.
            self.mFeatureSelector = None

        if(self.mFeatureSelector):
            lARInputsAfterSelection =  self.mFeatureSelector.transform(lARInputs);
            lSupport = self.mFeatureSelector.get_support(indices=True);
            self.mInputNamesAfterSelection = [self.mInputNames[k] for k in lSupport];
                
        else:
            lARInputsAfterSelection = lARInputs;
            self.mInputNamesAfterSelection = self.mInputNames;

        assert(len(self.mInputNamesAfterSelection) == lARInputsAfterSelection.shape[1]);
        # tsutil.print_pyaf_detailed_info("FEATURE_SELECTION" , self.mOutName, lARInputs.shape[1] , lARInputsAfterSelection.shape[1]);
        del lARInputs;

        try:
            self.mScikitModel.fit(lARInputsAfterSelection, lARTarget)
        except Exception as e:
            tsutil.print_pyaf_detailed_info("SCIKIT_MODEL_FIT_FAILURE" , self.mOutName, lARInputsAfterSelection.shape, e);
            if(self.mOptions.mDebug):
                df1 = pd.DataFrame(lARInputsAfterSelection);
                df1.columns = self.mInputNamesAfterSelection
                df1['TGT'] = lARTarget;
                # df1.to_csv("SCIKIT_MODEL_FIT_FAILURE.csv.gz" , compression='gzip');
            del self.mScikitModel
            self.mScikitModel = None;
            
        del lARInputsAfterSelection;
        del lARTarget;
        del lAREstimFrame;     

        if(self.mScikitModel is not None):
            lFullARInputs = self.mARFrame[self.mInputNames].values;
            lFullARInputsAfterSelection =  self.mFeatureSelector.transform(lFullARInputs) if self.mFeatureSelector else lFullARInputs;
            lPredicted = self.mScikitModel.predict(lFullARInputsAfterSelection);
            self.mARFrame[self.mOutName] = lPredicted
        else:
            # issue_34 failure SVD does not converge
            self.mARFrame[self.mOutName] = 0.0
            if(self.mDecompositionType in ['TSR']):
                self.mARFrame[self.mOutName] = 1.0
                

        self.compute_ar_residue(self.mARFrame)

        # tsutil.print_pyaf_detailed_info("ESTIMATE_SCIKIT_MODEL_END" , self.mOutName);


    def transformDataset(self, df, horizon_index = 1):
        series = self.mCycleResidueName; 
        if(self.mExogenousInfo is not None):
            df = self.mExogenousInfo.transformDataset(df);
        lag_df = self.generateLagsForForecast(df, selection = self.mInputNamesAfterSelection);
        inputs_after_feat_selection = lag_df[self.mInputNamesAfterSelection].values
        # inputs_after_feat_selection = self.mFeatureSelector.transform(inputs) if self.mFeatureSelector else inputs;
        if(self.mScikitModel is not None):
            pred = self.mScikitModel.predict(inputs_after_feat_selection)
            df[self.mOutName] = pred;
        else:
            df[self.mOutName] = 0.0
            if(self.mDecompositionType in ['TSR']):
                df[self.mOutName] = 1.0

            
        self.compute_ar_residue(df)
        return df;



class cAutoRegressiveModel(cAbstract_Scikit_Model):
    def __init__(self , cycle_residue_name, P , iExogenousInfo = None):
        super().__init__(cycle_residue_name, P, iExogenousInfo)
        self.mComplexity = tscomplex.eModelComplexity.High;

    def dumpCoefficients(self, iMax=10):
        logger = tsutil.get_pyaf_logger();
        lDict = dict(zip(self.mInputNamesAfterSelection , self.mScikitModel.coef_.round(6)));
        lDict1 = dict(zip(self.mInputNamesAfterSelection , abs(self.mScikitModel.coef_.round(6))));
        i = 1;
        lOrderedVariables = sorted(lDict1.keys(), key=lDict1.get, reverse=True);
        for k in lOrderedVariables[0:iMax]:
            logger.info("AR_MODEL_COEFF " + str(i) + " " + str(k) + " " + str(lDict[k]));
            i = i + 1;


    def build_Scikit_Model(self):
        import sklearn.linear_model as linear_model
        # issue_22 : warning about singular matrix => change the solver by default. 
        self.mScikitModel = linear_model.Ridge(solver='svd', alpha = 0.0)

    def set_name(self):
        self.mOutName = self.mCycleResidueName +  '_AR(' + str(self.mNbLags) + ")";
        self.mFormula = "AR" # (" + str(self.mNbLags) + ")";
        if(self.mExogenousInfo is not None):
            self.mOutName = self.mCycleResidueName +  '_ARX(' + str(self.mNbLags) + ")";
            self.mFormula = "ARX" # (" + str(self.mNbExogenousLags) + ")";
        
        

class cSVR_Model(cAbstract_Scikit_Model):
    def __init__(self , cycle_residue_name, P , iExogenousInfo = None):
        super().__init__(cycle_residue_name, P, iExogenousInfo)
        self.mComplexity = tscomplex.eModelComplexity.High;

    def dumpCoefficients(self, iMax=10):
        pass


    def build_Scikit_Model(self):
        import sklearn.svm as svm
        self.mScikitModel = svm.SVR(kernel='rbf', gamma='scale')

    def set_name(self):
        self.mOutName = self.mCycleResidueName +  '_SVR(' + str(self.mNbLags) + ")";
        self.mFormula = "SVR" # (" + str(self.mNbLags) + ")";
        if(self.mExogenousInfo is not None):
            self.mOutName = self.mCycleResidueName +  '_SVRX(' + str(self.mNbLags) + ")";
            self.mFormula = "SVRX" # (" + str(self.mNbExogenousLags) + ")";


class cXGBoost_Model(cAbstract_Scikit_Model):
    def __init__(self , cycle_residue_name, P , iExogenousInfo = None):
        super().__init__(cycle_residue_name, P, iExogenousInfo)
        self.mComplexity = tscomplex.eModelComplexity.High;

    def dumpCoefficients(self, iMax=10):
        pass

    def get_default_xgb_options(self):
        lXGBOptions = dict(n_estimators=10,
                           nthread=1,
                           min_child_weight=10,
                           max_depth=3,
                           seed=self.mOptions.mSeed)
        return lXGBOptions

        
    def build_Scikit_Model(self):
        import xgboost as xgb

        lXGBOptions = self.mOptions.mXGBOptions;
        if(lXGBOptions is None):
            lXGBOptions = self.get_default_xgb_options()
            
        self.mScikitModel = xgb.XGBRegressor(**lXGBOptions)

    def set_name(self):
        self.mOutName = self.mCycleResidueName +  '_XGB(' + str(self.mNbLags) + ")";
        self.mFormula = "XGB" #  + str(self.mNbLags) + ")";
        if(self.mExogenousInfo is not None):
            self.mOutName = self.mCycleResidueName +  '_XGBX(' + str(self.mNbLags) + ")";
            self.mFormula = "XGBX" # (" + str(self.mNbExogenousLags) + ")";



class cLightGBM_Model(cAbstract_Scikit_Model):
    def __init__(self , cycle_residue_name, P , iExogenousInfo = None):
        super().__init__(cycle_residue_name, P, iExogenousInfo)
        self.mComplexity = tscomplex.eModelComplexity.High;

    def dumpCoefficients(self, iMax=10):
        pass

    def get_default_lgbm_options(self):
        lLGBMOptions = dict(objective='regression',
                            n_estimators=32,
                            random_state=self.mOptions.mSeed)
        return lLGBMOptions
        
    def build_Scikit_Model(self):
        import lightgbm as lgb

        lLGBMOptions = self.mOptions.mLGBMOptions;
        if(lLGBMOptions is None):
            lLGBMOptions = self.get_default_lgbm_options()
            
        self.mScikitModel = lgb.LGBMRegressor(**lLGBMOptions)

    def set_name(self):
        self.mOutName = self.mCycleResidueName +  '_LGB(' + str(self.mNbLags) + ")";
        self.mFormula = "LGB" #  + str(self.mNbLags) + ")";
        if(self.mExogenousInfo is not None):
            self.mOutName = self.mCycleResidueName +  '_LGBX(' + str(self.mNbLags) + ")";
            self.mFormula = "LGBX" # (" + str(self.mNbExogenousLags) + ")";

