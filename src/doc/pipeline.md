python preprocess.py --config configs\ucsd_ped2.yaml
python train.py --config configs\ucsd_ped2.yaml
python rules.py --config configs\ucsd_ped2.yaml
python test.py --config configs\ucsd_ped2.yaml
python evaluate.py --config configs\ucsd_ped2.yaml

python visualize.py --config configs\ucsd_ped2.yaml --top-frames 30 --alerts
python explain.py --config configs\ucsd_ped2.yaml --output-dir outputs\analysis\ucsd_ped2