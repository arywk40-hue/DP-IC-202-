"""Recorded/simulated driver adapters; physical buses/pins/calibration unvalidated."""
import math
from datetime import datetime,timezone


def pms7003(frame):
    if not isinstance(frame,bytes) or len(frame)!=32 or frame[:2]!=b'BM' or int.from_bytes(frame[2:4],'big')!=28:
        raise ValueError('PMS7003 frame header/length')
    if sum(frame[:30])!=int.from_bytes(frame[30:32],'big'):raise ValueError('PMS7003 checksum')
    return dict(pm25_ug_m3=int.from_bytes(frame[12:14],'big'),pm10_ug_m3=int.from_bytes(frame[14:16],'big'),
                measurement_kind='atmospheric_optical_equivalent_not_reference_AQI',reserved_bytes=frame[28:30].hex())


def bme280_compensated(values):
    expected=['temperature_c','humidity_pct','pressure_pa']
    if not all(k in values and math.isfinite(float(values[k])) for k in expected):raise ValueError('Compensated BME280 values required')
    return dict(temperature_c=float(values['temperature_c']),relative_humidity_pct=float(values['humidity_pct']),pressure_hpa=float(values['pressure_pa'])/100,
                pressure_reference='station',factory_compensation_required=True,field_calibration_verified=False)


def encoder(previous,current,elapsed_seconds,pulses_per_revolution=600,wind_calibration=None):
    if type(previous) is not int or type(current) is not int or not 0<=previous<2**32 or not 0<=current<2**32 or not math.isfinite(elapsed_seconds) or elapsed_seconds<=0 or type(pulses_per_revolution) is not int or pulses_per_revolution<=0:
        raise ValueError('Valid counter/time/PPR required')
    count=(current-previous)%(2**32);rps=count/(elapsed_seconds*pulses_per_revolution)
    wind=None
    if wind_calibration is not None:
        slope,intercept=wind_calibration
        if not all(math.isfinite(v) for v in [slope,intercept]) or slope<=0:raise ValueError('Independent measured wind transfer function required')
        wind=slope*rps+intercept
        if not 0<=wind<=100:wind=None
    return dict(pulse_count=count,rotations_per_second=rps,rpm=rps*60,wind_speed_mps=wind,wind_direction_deg=None,
                calibration_status='provided_transfer_function_not_hardware_verified' if wind_calibration is not None else 'UNAVAILABLE_NO_ROTOR_CALIBRATION',
                ppr_convention='caller must specify counted edges including quadrature multiplier')


def nmea(sentence):
    if not isinstance(sentence,str) or len(sentence)>180 or not sentence.startswith('$') or '*' not in sentence:raise ValueError('NMEA framing')
    body,checksum=sentence.strip()[1:].split('*',1);value=0
    for c in body:value^=ord(c)
    if f'{value:02X}'!=checksum.upper():raise ValueError('NMEA checksum')
    f=body.split(',');kind=f[0][-3:]
    def coordinate(value,hemisphere,latitude):
        digits=2 if latitude else 3
        result=int(value[:digits])+float(value[digits:])/60
        if hemisphere in ['S','W']:result=-result
        if hemisphere not in (['N','S'] if latitude else ['E','W']):raise ValueError('Hemisphere')
        if abs(result)>(90 if latitude else 180):raise ValueError('Coordinate range')
        return result
    if kind=='RMC':
        if len(f)<10 or f[2]!='A':return {'fix_valid':False,'timestamp_utc':None}
        date,time=f[9],f[1]
        if len(date)!=6 or len(time)<6:raise ValueError('RMC UTC date/time unavailable')
        second=float(time[4:]);year=2000+int(date[4:])
        stamp=datetime(year,int(date[2:4]),int(date[:2]),int(time[:2]),int(time[2:4]),int(second),int((second%1)*1e6),tzinfo=timezone.utc)
        return dict(fix_valid=True,timestamp_utc=stamp.isoformat(),latitude=coordinate(f[3],f[4],True),longitude=coordinate(f[5],f[6],False),
                    elevation_m=None,elevation_datum='UNVERIFIED_GNSS_HEIGHT',wind_speed_mps=None)
    if kind=='GGA':
        if len(f)<13 or not f[6] or int(f[6])==0:return {'fix_valid':False}
        return dict(fix_valid=True,latitude=coordinate(f[2],f[3],True),longitude=coordinate(f[4],f[5],False),
                    reported_msl_altitude_m=float(f[9]) if f[9] and f[10]=='M' else None,
                    reported_geoid_separation_m=float(f[11]) if f[11] and f[12]=='M' else None,
                    elevation_m=None,elevation_datum='receiver_MSL_model_not_verified_EGM96')
    return {'unsupported_sentence':kind}


def ds3231(registers,oscillator_stopped=False,configured_utc=False):
    if len(registers)!=7 or oscillator_stopped or not configured_utc:return {'timestamp_utc':None,'status':'UNVERIFIED_RTC_CLOCK'}
    def bcd(n):
        if n&15>9 or (n>>4)>9:raise ValueError('Invalid BCD')
        return (n>>4)*10+(n&15)
    sec,minute=bcd(registers[0]&127),bcd(registers[1]&127);hour=registers[2]
    if hour&64:
        h=bcd(hour&31)
        if not 1<=h<=12:raise ValueError('Invalid 12-hour clock')
        hour=h%12+(12 if hour&32 else 0)
    else:hour=bcd(hour&63)
    year=2000+bcd(registers[6])+(100 if registers[5]&128 else 0)
    stamp=datetime(year,bcd(registers[5]&31),bcd(registers[4]&63),hour,minute,sec,tzinfo=timezone.utc)
    return {'timestamp_utc':stamp.isoformat(),'status':'CONFIGURED_UTC_NOT_DRIFT_VALIDATED'}


def ina219(values,shunt_calibrated=False):
    if not all(math.isfinite(float(values[k])) for k in ['bus_voltage_v','current_ma','power_mw']):raise ValueError('Power diagnostic values')
    return {**values,'measurement_kind':'power_health_not_weather','calibration_verified':shunt_calibrated is True,'physical_meter_validation':False}


class RetryDriver:
    """Bounded host polling; no IO backend or hardware accuracy assumed."""
    def __init__(self,reader,attempts=3):
        if not 1<=attempts<=5:raise ValueError('Retry budget')
        self.reader=reader;self.attempts=attempts;self.last_success=None;self.last_error=None
    def poll(self,timestamp):
        for attempt in range(self.attempts):
            try:
                value=self.reader();self.last_success=timestamp;self.last_error=None
                return {'status':'READ_SUCCESS_NOT_CALIBRATION_PROOF','value':value,'attempts':attempt+1}
            except (TimeoutError,OSError,ValueError) as exc:self.last_error=type(exc).__name__
        return {'status':'DRIVER_UNAVAILABLE','value':None,'attempts':self.attempts,'last_error':self.last_error}
