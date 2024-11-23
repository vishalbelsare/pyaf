mkdir logs
# this file is a utility that is used to run the benchamrks .... takes too much time to run. 
# The output of the benchmarks will be in logs directory.
# This script is used for bernchmarks , not for tests.
# tests are located in the 'tests' directory. There is a tests/Makefile.
python3 benches/run_benchmark_artificial.py
python3 benches/run_benchmark_M1Comp.py
python3 benches/run_benchmark_M2Comp.py
python3 benches/run_benchmark_M3Comp.py
python3 benches/run_benchmark_M4Comp.py
python3 benches/run_benchmark_FPP2.py
python3 benches/run_benchmark_MWH.py
python3 benches/run_benchmark_NN3.py
python3 benches/run_benchmark_NN5.py
python3 benches/run_benchmark_Yahoo.py
