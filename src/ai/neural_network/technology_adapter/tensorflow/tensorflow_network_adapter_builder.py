from typing import Dict, List

import tensorflow as tf
from tensorflow.keras import layers
from tensorflow.python.keras import Input
from tensorflow.python.layers.base import Layer
from tensorflow.python.layers.core import Dense

from src.ai.ai_command_generator import CommandName
from src.ai.ai_data_and_info.ai_awards.ai_awards_definer import AiAwardsDefiner
from src.ai.ai_data_and_info.ai_info import AiInfo
from src.ai.game_components.convert_self_to_json import Json
from src.ai.game_components.move_direction import MoveDirection, DIRECTIONS
from src.ai.game_components.person_unit_params import PersonUnitParams
from src.ai.game_components.sector_params import SectorParams
from src.ai.game_components.unit_observation import UnitObservation
from src.ai.neural_network.technology.tensorflow.networks.network_adapter import command_cost_definer_layer_names, \
    CommandDefinerLevel
from src.ai.neural_network.technology_adapter.ai_command import AiCommand
from src.ai.neural_network.technology_adapter.error_function import ErrorFunction
from src.ai.neural_network.technology_adapter.network_adapter import NetworkAdapter
from src.ai.neural_network.technology_adapter.network_layer import NetworkLayer, NetworkLayers
from src.ai.neural_network.technology_adapter.network_technology_adapter_builder import NetworkTechnologyAdapterBuilder
from src.ai.neural_network.technology_adapter.optimizer import Optimizer
from src.ai.neural_network.technology_adapter.tensorflow.builder.tensorflow_layer_builder import TensorflowLayerBuilder
from src.ai.neural_network.technology_adapter.tensorflow.tensorflow_error_function import TensorflowErrorFunction
from src.ai.neural_network.technology_adapter.tensorflow.network_layer import TensorflowNetworkLayer
from src.ai.neural_network.technology_adapter.tensorflow.tensorflow_optimizer import TensorflowOptimizer
from src.ai.neural_network.technology_adapter.tensorflow.scout_network_adapter import ScoutNetworkAdapter


class TensorflowNetworkAdapterBuilder(NetworkTechnologyAdapterBuilder):
    def __init__(self):
        super().__init__()

    @staticmethod
    def generate_scout_network_adapter(ai_info: AiInfo) -> ScoutNetworkAdapter:
        return ScoutNetworkAdapter()

    def generate_error_function(self, ai_awards_definer: AiAwardsDefiner) -> ErrorFunction:
        return TensorflowErrorFunction(ai_awards_definer)

    def generate_optimizer(self) -> Optimizer:
        return TensorflowOptimizer()

    def compile_model(self,
                      adapter: NetworkAdapter,
                      error_function: ErrorFunction, optimizer: Optimizer) -> NetworkAdapter:
        # TODO 7kia обновить ErrorFunction и Optimizer
        adapter.compile(optimizer=optimizer, loss=error_function)
        return adapter

    def generate_output_layer(self, command_cost_definer_layer: NetworkLayer) -> NetworkLayer:
        result: TensorflowNetworkLayer = TensorflowNetworkLayer()
        return result

    def generate_input_unit_observation_layer(self) -> NetworkLayers:
        unit_observation: UnitObservation = UnitObservation()
        result: Dict[str, TensorflowNetworkLayer] = self._generate_dict_input_layer_from_json(
            unit_observation.as_json(),
        )
        return result

    def _generate_dict_input_layer_from_json(self, json: Json) -> Dict[str, TensorflowNetworkLayer]:
        result: Dict[str, TensorflowNetworkLayer] = {}
        for key in json:
            value: any = json[key]
            new_layer: TensorflowNetworkLayer = TensorflowNetworkLayer()
            if isinstance(value, (float, int)):
                new_layer.value = Input(shape=(1,), name=key)
            elif isinstance(value, list):
                if self._is_position(value):
                    new_layer.value = Input(shape=(2,), name=key)
                elif self._is_matrix(value):
                    new_layer.value = Input(shape=(16, ), name=key)
            else:
                raise TypeError(f"_generate_dict_input_layer_from_json: {value} have incorrect type")
            result[key] = new_layer
        return result

    @staticmethod
    def _is_position(value: any) -> bool:
        return len(value) == 2

    @staticmethod
    def _is_matrix(value: any) -> bool:
        return len(value) == 4

    def generate_input_sector_params_layer(self) -> NetworkLayers:
        sector_params: SectorParams = SectorParams()
        result: Dict[str, TensorflowNetworkLayer] = self._generate_dict_input_layer_from_json(
            sector_params.generate_params_for_network()
        )
        return result

    def generate_input_person_unit_params_layer(self) -> NetworkLayers:
        person_unit_params: PersonUnitParams = PersonUnitParams()
        result: Dict[str, TensorflowNetworkLayer] = self._generate_dict_input_layer_from_json(
            person_unit_params.as_json()
        )
        return result

    def generate_command_definer_layer(self, input_layers: Dict[str, NetworkLayers]) -> NetworkLayer:
        result: TensorflowNetworkLayer = TensorflowNetworkLayer()

        input_for_new_layers: Dict[str, Layer] = {}
        for layer_name in command_cost_definer_layer_names:
            current_layer: NetworkLayers = input_layers[layer_name.value]
            input_for_new_layers[layer_name.value] = TensorflowLayerBuilder.convert_as_array(current_layer)

        result.value = layers.Dense(
            len(command_cost_definer_layer_names),
            activation='softmax',
            name=f"command_definer_layer"
        )(
            TensorflowLayerBuilder.convert_dict_to_array(input_for_new_layers)
        )
        return result

    def generate_output_layer(self, input_layer: NetworkLayer) -> NetworkLayers:
        result: Dict[str, TensorflowNetworkLayer] = {}

        input_tensor: TensorflowNetworkLayer = input_layer
        command_cost_summation_layer_name: str = CommandDefinerLevel.command_cost_summation_layer.value
        result[command_cost_summation_layer_name] = TensorflowNetworkLayer()
        result[command_cost_summation_layer_name].value = layers.Dense(
            1,
            activation='softmax',
            name=command_cost_summation_layer_name
        )(
            input_tensor.value
        )

        result_layer_name: str = CommandDefinerLevel.result.value
        result[result_layer_name] = TensorflowNetworkLayer()
        result[result_layer_name].value = layers.Dense(
            1,
            activation=self._get_ai_command,
            name=result_layer_name
        )(
            result[command_cost_summation_layer_name].value
        )
        return result

    # TODO 7kia выдаёт только для слоя разведки
    def _get_ai_command(self, tensor):
        return tf.argmax(tensor)

