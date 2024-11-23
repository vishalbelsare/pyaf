
import pyaf.ForecastEngine as autof
import pyaf.Bench.TS_datasets as tsds




b1 = tsds.generate_random_TS(N = 4000 , FREQ = 'D', seed = 0, trendtype = "constant", cycle_length = 24, transform = "None", sigma = 0.1, exog_count = 0);

df = b1.mPastData.copy()
df[b1.mSignalVar] = df[b1.mName]

lEngine = autof.cForecastEngine()
lEngine

H = 12;
lEngine.mOptions.mFilterSeasonals = False;
lEngine.mOptions.mParallelMode = True;
lEngine.mOptions.mDebugPerformance = True;
lEngine.train(df , b1.mTimeVar , b1.mSignalVar, H);
lEngine.getModelInfo();


lEngine.standardPlots("outputs/artificial_ds_keep_all_seasonals_day")
