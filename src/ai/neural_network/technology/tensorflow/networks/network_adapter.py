from typing import List, Dict

from tensorflow import constant
from tensorflow.python.layers.base import Layer

from src.ai.neural_network.technology_adapter.ai_command import AiCommand
from tensorflow.python.keras.models import Model

from src.ai.neural_network.technology_adapter.network_layer import NetworkLayer
from src.ai.neural_network.technology_adapter.tensorflow.network_layer import TensorflowNetworkLayer


class NetworkAdapter:
    _input_layer: Dict[str, Layer] = None
    _output_layer: Dict[str, Layer] = None
    _final_model: Model = None

    def __init__(self):
        pass

    def train(self,
              unit_observation: constant,
              current_game_state: constant) -> AiCommand:
        pass

    def test(self,
             unit_observation: constant,
             current_game_state: constant,) -> AiCommand:
        pass

    def set_input_layers(self, input_layer: Dict[str, Layer]):
        self._input_layer = input_layer

    def set_output_layer(self, output_layer: Dict[str, Layer]):
        self._output_layer = output_layer
