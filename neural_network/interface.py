#!/usr/bin/env python3
"""
Neural Network Interface - Data accumulation and inference coordination
Placeholder for Race Strategy team integration (Next Sprint)
"""

from dataclasses import dataclass
from typing import List, Callable, Optional
from collections import deque
import threading
import time
import logging

logger = logging.getLogger(__name__)


@dataclass
class NNInput:
    """Data packet for neural network inference"""
    timestamp: float
    speed: float
    soc: float
    pack_current: float
    pack_voltage: float
    motor_temp: float
    solar_power: float
    # Add more fields as needed by NN model
    

@dataclass  
class NNOutput:
    """Neural network decision output"""
    target_speed: float
    confidence: float
    reasoning_code: int  # Enum for UI display
    

class NNDataBuffer:
    """
    Accumulates CAN data for periodic NN inference.
    
    Usage by Race Strategy team:
        buffer = NNDataBuffer(window_minutes=5, sample_hz=1)
        buffer.set_inference_callback(my_nn_model.infer)
        buffer.start()
        
    Buffer automatically calls inference every `window_minutes`
    and publishes results to CAN via callback
    """
    
    def __init__(
        self,
        window_minutes: int = 5,
        sample_hz: float = 1.0,
        output_callback: Optional[Callable[[NNOutput], None]] = None
    ):
        self.window_minutes = window_minutes
        self.sample_hz = sample_hz
        self.output_callback = output_callback
        
        max_samples = int(window_minutes * 60 * sample_hz)
        self.buffer: deque[NNInput] = deque(maxlen=max_samples)
        
        self._inference_fn: Optional[Callable[[List[NNInput]], NNOutput]] = None
        self._running = False
        self._thread: Optional[threading.Thread] = None
        
        logger.info(f"NN buffer initialized: {window_minutes}min window, {sample_hz}Hz sampling")
        
    def set_inference_callback(self, fn: Callable[[List[NNInput]], NNOutput]) -> None:
        """Set the neural network inference function"""
        self._inference_fn = fn
        logger.info("NN inference callback registered")
        
    def add_sample(self, sample: NNInput) -> None:
        """Called by coordinator to add new data point"""
        self.buffer.append(sample)
        
    def start(self) -> None:
        """Start periodic inference"""
        if self._running:
            logger.warning("NN buffer already running")
            return
            
        self._running = True
        self._thread = threading.Thread(target=self._inference_loop, daemon=True)
        self._thread.start()
        logger.info("NN inference loop started")
    
    def stop(self) -> None:
        """Stop inference loop"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5.0)
        logger.info("NN inference loop stopped")
        
    def _inference_loop(self) -> None:
        """Periodic inference execution"""
        while self._running:
            time.sleep(self.window_minutes * 60)
            
            if len(self.buffer) < 10:  # Minimum samples required
                logger.warning(f"Insufficient samples for inference: {len(self.buffer)}")
                continue
                
            if self._inference_fn:
                try:
                    logger.info(f"Running inference on {len(self.buffer)} samples")
                    result = self._inference_fn(list(self.buffer))
                    
                    if self.output_callback:
                        self.output_callback(result)
                        logger.info(f"NN output: speed={result.target_speed:.1f}, confidence={result.confidence:.2f}")
                        
                except Exception as e:
                    logger.error(f"NN inference failed: {e}")
            else:
                logger.warning("No inference function registered")
    
    def get_buffer_size(self) -> int:
        """Get current number of samples in buffer"""
        return len(self.buffer)


if __name__ == "__main__":
    # Test the NN interface
    logging.basicConfig(level=logging.INFO)
    
    def mock_inference(samples: List[NNInput]) -> NNOutput:
        """Mock NN inference for testing"""
        avg_speed = sum(s.speed for s in samples) / len(samples)
        return NNOutput(
            target_speed=avg_speed + 5.0,
            confidence=0.85,
            reasoning_code=1
        )
    
    def mock_output_callback(output: NNOutput):
        """Mock callback for NN output"""
        print(f"NN recommends: {output.target_speed:.1f} mph (confidence: {output.confidence:.2f})")
    
    buffer = NNDataBuffer(window_minutes=0.05, sample_hz=10, output_callback=mock_output_callback)  # 3 seconds for testing
    buffer.set_inference_callback(mock_inference)
    
    # Add some sample data
    for i in range(20):
        sample = NNInput(
            timestamp=time.time(),
            speed=45.0 + i,
            soc=85.0,
            pack_current=10.0,
            pack_voltage=100.0,
            motor_temp=50.0,
            solar_power=500.0
        )
        buffer.add_sample(sample)
        time.sleep(0.1)
    
    buffer.start()
    
    # Let it run for a bit
    time.sleep(5)
    
    buffer.stop()
