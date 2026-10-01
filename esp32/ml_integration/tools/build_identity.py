"""PlatformIO pre-build: identify the exact model and integration sources."""
import hashlib
from pathlib import Path


def identity(project, environment="esp32-s3-ml"):
    root = project.parents[1]
    files = {
        'forecast': root/'ml/models/uci_beijing_6h/esp32_student/export/indra_six_sensor_forecast.h',
        'events': root/'ml/models/uci_beijing_event_rules_6sensor/esp32_student/export/indra_event_classifier.h',
        'runtime': project/'include/indra_ml_runtime.h',
        'application': project/'src/main.cpp',
        'fixture': project/'include/self_test_fixture.h',
        'platform': project/'platformio.ini',
        'identity_script': project/'tools/build_identity.py',
    }
    hashes = {name: hashlib.sha256(path.read_bytes()).hexdigest() for name, path in files.items()}
    hashes['environment'] = hashlib.sha256(environment.encode()).hexdigest()
    hashes['build'] = hashlib.sha256(''.join(f'{k}:{v}\n' for k,v in sorted(hashes.items())).encode()).hexdigest()
    return hashes


# SCons injects Import while executing an extra_script.
if 'Import' in globals():
    globals()['Import']('env')
    project = Path(globals()['env']['PROJECT_DIR'])
    values = identity(project, globals()['env']['PIOENV'])
    header = '#pragma once\n' + ''.join(
        f'#define INDRA_{key.upper()}_SHA256 "{value}"\n' for key,value in values.items())
    path = project/'include/build_identity.h'
    if not path.exists() or path.read_text() != header:
        path.write_text(header)
