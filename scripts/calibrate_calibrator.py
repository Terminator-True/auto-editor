import argparse
import yaml
from pathlib import Path


def compute_platt_params(labels):
    # Very naive: compute slope/intercept from one-point mapping (mean)
    # Expect labels: list of (raw_confidence, true_label_bool)
    # We'll compute a linear fit y = a*x + b where y is 1.0 for true, 0.0 for false
    if not labels:
        return {'a': 1.0, 'b': 0.0}
    xs = [x for x, y in labels]
    ys = [1.0 if y else 0.0 for x, y in labels]
    mean_x = sum(xs)/len(xs)
    mean_y = sum(ys)/len(ys)
    # slope = cov(x,y)/var(x)
    num = sum((x-mean_x)*(y-mean_y) for x,y in zip(xs, ys))
    den = sum((x-mean_x)**2 for x in xs)
    if den == 0:
        a = 1.0
    else:
        a = num/den
    b = mean_y - a*mean_x
    return {'a': float(a), 'b': float(b)}


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--input', help='YAML file with labeled confidences', required=True)
    p.add_argument('--output', help='Write calibration to', default='config/calibration.yml')
    args = p.parse_args()

    with open(args.input, 'r', encoding='utf-8') as f:
        payload = yaml.safe_load(f)

    # Expect payload: list of {raw: 0.9, label: true}
    labels = [(item['raw'], bool(item['label'])) for item in payload]
    params = compute_platt_params(labels)

    outp = Path(args.output)
    outp.parent.mkdir(parents=True, exist_ok=True)
    with outp.open('w', encoding='utf-8') as f:
        yaml.safe_dump(params, f)
    print('Wrote calibration to', outp)


if __name__ == '__main__':
    main()
