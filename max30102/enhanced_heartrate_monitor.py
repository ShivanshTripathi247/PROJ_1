from .max30102 import MAX30102
from . import hrcalc
import threading
import time
import numpy as np
from collections import deque

class EnhancedHeartRateMonitor(object):
    """Enhanced HeartRateMonitor with raw PPG access for blood pressure estimation"""
    
    LOOP_TIME = 0.01
    
    def __init__(self, print_raw=False, print_result=False):
        self.bpm = 0
        self.spo2 = None
        self.print_raw = print_raw
        self.print_result = print_result
        
        # Raw PPG data for blood pressure estimation
        self.raw_ir_buffer = deque(maxlen=2500)  # 50 seconds at 50Hz
        self.raw_red_buffer = deque(maxlen=2500)
        self.ppg_timestamps = deque(maxlen=2500)
        
    def run_sensor(self):
        sensor = MAX30102()
        ir_data = []
        red_data = []
        bpms = []
        
        while not self._thread.stopped:
            num_bytes = sensor.get_data_present()
            
            if num_bytes > 0:
                while num_bytes > 0:
                    red, ir = sensor.read_fifo()
                    num_bytes -= 1
                    
                    # Store for HR/SpO2 calculation
                    ir_data.append(ir)
                    red_data.append(red)
                    
                    # NEW: Store raw PPG data with timestamps for BP estimation
                    current_time = time.time()
                    self.raw_ir_buffer.append(ir)
                    self.raw_red_buffer.append(red)
                    self.ppg_timestamps.append(current_time)
                    
                    if self.print_raw:
                        print("{0}, {1}".format(ir, red))
                
                # Keep last 100 samples for HR/SpO2 calculation
                while len(ir_data) > 100:
                    ir_data.pop(0)
                    red_data.pop(0)
                
                if len(ir_data) == 100:
                    bpm, valid_bpm, spo2, valid_spo2 = hrcalc.calc_hr_and_spo2(ir_data, red_data)
                    
                    if valid_bpm:
                        bpms.append(bpm)
                        while len(bpms) > 4:
                            bpms.pop(0)
                        self.bpm = np.mean(bpms)
                        
                        if valid_spo2 and spo2 > 0:
                            self.spo2 = spo2
                    
                    # Check finger detection
                    if (np.mean(ir_data) < 50000 and np.mean(red_data) < 50000):
                        self.bpm = 0
                        self.spo2 = None
                        if self.print_result:
                            print("Finger not detected")
                    else:
                        if self.print_result:
                            print("BPM: {0}, SpO2: {1}".format(self.bpm, self.spo2))
            
            time.sleep(self.LOOP_TIME)
        
        sensor.shutdown()
    
    def get_raw_ppg_data(self, duration_seconds=50):
        """Get raw PPG data for blood pressure estimation"""
        if len(self.raw_ir_buffer) < duration_seconds * 50:  # 50Hz sampling
            return None, None, None
        
        # Return last N seconds of data
        num_samples = duration_seconds * 50
        ir_data = list(self.raw_ir_buffer)[-num_samples:]
        red_data = list(self.raw_red_buffer)[-num_samples:]
        timestamps = list(self.ppg_timestamps)[-num_samples:]
        
        return ir_data, red_data, timestamps
    
    def start_sensor(self):
        self._thread = threading.Thread(target=self.run_sensor)
        self._thread.stopped = False
        self._thread.start()
    
    def stop_sensor(self, timeout=2.0):
        self._thread.stopped = True
        self.bmp = 0
        self.spo2 = None
        self._thread.join(timeout)
