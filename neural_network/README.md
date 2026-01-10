# Neural Network Integration Interface

**Status:** Placeholder for Next Sprint  
**Owner:** Race Strategy Team  
**Integration Target:** Sprint 2 (Post 8-week foundation)

---

## Overview

This module provides the interface for integrating the Race Strategy team's neural network model into the SC2 Driver IO system. The NN will analyze real-time telemetry data and provide driving strategy recommendations.

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│             Neural Network Data Flow                    │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  CAN Bus → Coordinator → NNDataBuffer                   │
│                              │                          │
│                              ├─ Accumulates N minutes   │
│                              ├─ Filters/averages        │
│                              └─ Triggers inference      │
│                                     │                   │
│                                     ▼                   │
│                          NN Model (PyTorch)             │
│                                     │                   │
│                                     ▼                   │
│                          Strategy Decisions             │
│                                     │                   │
│                                     ▼                   │
│                          CAN Bus (published)            │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

## Interface Specification

### Input Data Structure

```python
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
    # Extend as needed for your model
```

### Output Data Structure

```python
@dataclass  
class NNOutput:
    """Neural network decision output"""
    target_speed: float      # Recommended speed in mph
    confidence: float        # Model confidence (0-1)
    reasoning_code: int      # Enum for UI display
```

### Model Integration

Your model should implement this interface:

```python
def infer(samples: List[NNInput]) -> NNOutput:
    """
    Run inference on accumulated data samples.
    
    Args:
        samples: List of NNInput samples covering the time window
        
    Returns:
        NNOutput with strategy recommendation
    """
    # Your PyTorch model here
    pass
```

## CAN Message Specification

Reserved CAN IDs for NN outputs:

| Signal Name | CAN ID | Offset | Type | Description |
|-------------|--------|--------|------|-------------|
| `nn_target_speed` | 0x500 | 0 | float | Recommended speed (mph) |
| `nn_confidence` | 0x500 | 4 | float | Model confidence (%) |
| `nn_reasoning_code` | 0x501 | 0 | uint8 | Strategy reasoning enum |
| `nn_last_inference_time` | 0x501 | 1 | uint32 | Unix timestamp (seconds) |

## Configuration Parameters

Tunable parameters for your model integration:

- **`window_minutes`**: How many minutes of data to accumulate (default: 5)
- **`sample_hz`**: Sampling rate for data collection (default: 1Hz)
- **`min_samples`**: Minimum samples before inference runs (default: 10)

## Example Integration

```python
from neural_network.interface import NNDataBuffer, NNInput, NNOutput
from your_model import YourPyTorchModel

# Load your trained model
model = YourPyTorchModel.load("path/to/model.pt")

def my_inference(samples: List[NNInput]) -> NNOutput:
    # Preprocess data
    features = preprocess(samples)
    
    # Run model
    with torch.no_grad():
        prediction = model(features)
    
    # Convert to output format
    return NNOutput(
        target_speed=prediction.speed,
        confidence=prediction.confidence,
        reasoning_code=prediction.strategy_type
    )

# Register with coordinator
buffer = NNDataBuffer(window_minutes=5, sample_hz=1)
buffer.set_inference_callback(my_inference)
buffer.start()
```

## Testing

Before integrating with the live system:

1. **Simulate data**: Use `interface.py` with mock data
2. **Validate timing**: Ensure inference completes within acceptable latency
3. **Error handling**: Test failure modes (insufficient data, model errors)

## Requirements for Race Strategy Team

### Technical Requirements

- [ ] PyTorch model trained on Simulink data
- [ ] Model inference time < 5 seconds
- [ ] Model file size < 100MB
- [ ] Python 3.10+ compatible
- [ ] Dependencies listed in `requirements.txt`

### Documentation Requirements

- [ ] Model architecture description
- [ ] Training data specifications
- [ ] Inference performance benchmarks
- [ ] Known limitations and edge cases

### Integration Checklist

- [ ] Implement `infer()` function following interface
- [ ] Test with historical race data
- [ ] Profile memory and CPU usage
- [ ] Document reasoning_code enum values
- [ ] Provide example usage

## Contact

For questions about this interface:
- **Integration Lead**: [Your Name]
- **Race Strategy Team Lead**: [Team Lead Name]
- **Repository**: SC2 Driver IO

## Next Steps (Sprint 2)

1. Review this interface specification
2. Confirm CAN IDs don't conflict with existing messages
3. Define additional input features if needed
4. Schedule integration testing session
5. Plan fallback behavior if NN fails

---

**Last Updated:** January 9, 2026  
**Sprint:** Foundation (Week 1)
