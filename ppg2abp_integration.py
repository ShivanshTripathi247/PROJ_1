import numpy as np
from scipy import signal
import time
from collections import deque

import sys
sys.path.append('/home/raspberry/PPG2ABP')
from PPG2ABP.model import PPG2ABPModel

class PPG2ABPIntegration:
    def __init__(self):
        self.model = PPG2ABPModel()
        self.model.load_weights('/home/raspberry/PPG2ABP/trained_model.h5')
        
    def estimate_bp(self, ppg_signal):
        # Preprocess PPG signal for PPG2ABP model
        processed_signal = self.preprocess_ppg(ppg_signal)
        
        # Get BP estimation
        bp_prediction = self.model.predict(processed_signal)
        
        return bp_prediction['systolic'], bp_prediction['diastolic']