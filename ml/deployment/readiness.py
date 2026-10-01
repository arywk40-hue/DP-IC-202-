"""Publish evidence gaps for every saved event head; never promote rule accuracy to hazard accuracy."""
import argparse
import json
from pathlib import Path

from ml.event_classifier.predict import EventPredictor
from ml.event_classifier.features import EVENT_ACTIVE_CHANNELS, EVENT_NAMES


def audit(model):
    predictor = EventPredictor(model)  # Verify the model artifacts first.
    events = {}
    for name in EVENT_NAMES:
        entry = predictor.report['models'][name]
        flags = []
        positives = entry.get('train_positives', 0)
        if entry.get('skipped'):
            flags.append('UNTRAINED')
        if positives < 100:
            flags.append('FEWER_THAN_100_TRAINING_RULE_MATCHES')
        counts = {split: entry.get('metrics', {}).get(split, {}).get('positives_in_split', 0)
                  for split in ['validation', 'future_test', 'geographic_test']}
        if any(count == 0 for count in counts.values()):
            flags.append('NO_POSITIVE_RULE_MATCHES_IN_AT_LEAST_ONE_EVALUATION_SPLIT')
        events[name] = {'trained': not entry.get('skipped', False),
                        'physical_channels': EVENT_ACTIVE_CHANNELS[name],
                        'channel_availability_fraction_with_complete_six_sensor_history': 1.0,
                        'train_rule_matches': positives, 'evaluation_rule_matches': counts,
                        'flags': flags, 'independent_hazard_validation': False,
                        'public_alerts_enabled': False}
    return {'status': 'BENCH_PROTOTYPE_ONLY', 'events': events,
            'screening_note': '100 positives is a descriptive sparsity flag, not a statistical certification threshold.',
            'unmet_deployment_gates': ['Colocated six-channel local observations with verified timestamps and pressure',
                'Independent observed event labels and untouched temporal/geographic evaluation',
                'Future-event labels and separate lead-time evaluation before advance hazard warnings',
                'Calibration evaluated on independent held-out observations',
                'Independent withheld-node spatial validation',
                'Physical ESP32 serial replay and measured latency',
                'LoRa delivery/loss/latency tests when radio integration resumes']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model', type=Path, default=Path('ml/models/uci_beijing_event_rules_6sensor'))
    parser.add_argument('--output', type=Path, default=Path('reports/deployment/readiness.json'))
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(audit(args.model), indent=2)+'\n')
    print(args.output)


if __name__ == '__main__':
    main()
