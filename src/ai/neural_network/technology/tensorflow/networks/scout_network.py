import os
from typing import Dict, List

import numpy as np
import tensorflow as tf
from tensorflow import Variable as TfVariable, TensorShape
from tensorflow import constant as TfConstant
from tensorflow import keras
from tensorflow.python.keras.callbacks import History, ModelCheckpoint
from tensorflow.python.keras.losses import Loss
from tensorflow.python.keras.optimizer_v2.optimizer_v2 import OptimizerV2
from tensorflow.python.keras.optimizers import Optimizer, Adam
from tensorflow.python.layers.base import Layer

from src.ai.ai_command_generator import CommandName
from src.ai.game_components.convert_self_to_json import Json
from src.ai.game_components.game_state import GameState
from src.ai.game_components.move_direction import DIRECTIONS, length_variant
from src.ai.game_components.unit_observation import UnitObservation
from src.ai.neural_network.technology.tensorflow.input_network_data_generator import InputNetworkDataGenerator
from src.ai.neural_network.technology.tensorflow.networks.network_adapter import NetworkAdapter, CommandDefinerLevel, \
    LengthDistanceTensorPrefix, CommandCostDefinerTensorNames, LENGTH
from src.ai.neural_network.technology.tensorflow.scout_network_loss_function import ScoutNetworkLossFunction, \
    clip_gradients
from src.ai.neural_network.technology_adapter.ai_command import AiCommand
from src.ai.neural_network.technology_adapter.error_function import ErrorFunction as MyErrorFunction
from src.ai.neural_network.technology_adapter.optimizer import Optimizer as MyOptimizer
from src.ai.neural_network.technology_adapter.tensorflow.tensorflow_error_function import TensorflowErrorFunction


class ScoutNetwork(NetworkAdapter):
    # слой определения ценности параметров
    __input_param_cost_definer: Dict[str, Layer] = None
    # слой определения ценности конкретной команды
    __command_cost_definer: Dict[str, Layer] = None
    # слой объединения значений и определения выходной окманды
    __command_definer: Layer = None


    _model_weight_path: str = 'model/scout_network.weight'
    _model_path: str = 'model/scout_network.model'
    _callback_save_weight: ModelCheckpoint = None

    def __init__(self):
        super().__init__()
        checkpoint_dir = os.path.dirname(self._model_weight_path)
        self._callback_save_weight = tf.keras.callbacks.ModelCheckpoint(
            filepath=self._model_weight_path,
            save_weights_only=True,
            verbose=1
        )
        self.data_generator = InputNetworkDataGenerator()
        # if self.exist_model():
        #     self._final_model = keras.models.load_model(self._model_path)
        # https://github.com/maurock/snake-ga/blob/master/DQN.py

    def exist_model(self) -> bool:
        return os.path.isdir(self._model_path)

    def __del__(self):
        self._final_model.save(self._model_path)

    def train(self,
              unit_observation: UnitObservation,
              current_game_state: GameState) -> AiCommand:
        gradient = None
        with tf.GradientTape() as tape:
            tape.watch(self._final_model.variables)
            y = self._final_model.loss(None, None)
            y = tf.Variable([y])
            gradient = tape.gradient(
                self._final_model.loss(None, None),
                self._final_model.variables
            )
            for index in range(len(gradient)):
                if gradient[index] is None:
                    gradient[index] = tf.Variable([0.0])

        grads_and_vars = list(zip(gradient, self._final_model.variables))
        self._final_model.optimizer.apply_gradients(grads_and_vars)  # processed_grads

        history: History = self._final_model.fit(
            self.data_generator.generate_input_data(unit_observation, current_game_state),# np.asarray(input_data),
            # batch_size=1,
            # callbacks=[self._callback_save_weight]
            epochs=1
        )
        print('\nhistory dict:', history.history)
        return self.test(unit_observation, current_game_state)

    def test(self,
             unit_observation: UnitObservation,
             current_game_state: GameState) -> AiCommand:
        self._set_current_and_last_game_state(current_game_state)

        # 7kia Используемые входные значения. Оставлены в качестве напоминания
        # для разработчика. Не удалять

        # unit_observation_data.own_organization
        # unit_observation_data.own_composition
        # unit_observation_data.sector
        # unit_observation_data.own_sum_info
        # unit_observation_data.own_max_info
        # unit_observation_data.enemy_sum_info
        # unit_observation_data.enemy_max_info
        #
        # current_game_state.person_unit_params.troop_amount
        # current_game_state.person_unit_params.organization
        # current_game_state.person_unit_params.enemy_troop_amount
        # current_game_state.person_unit_params.enemy_organization
        # current_game_state.person_unit_params.experience
        # current_game_state.person_unit_params.overlap
        # current_game_state.person_unit_params.speed
        #
        # current_game_state.sector_params.own_sum_info
        # current_game_state.sector_params.own_max_info
        # current_game_state.sector_params.enemy_sum_info
        # current_game_state.sector_params.enemy_max_info

        result_tensor = self._final_model.predict(
            self.data_generator.generate_input_data(unit_observation, current_game_state),# np.asarray(input_data),
        )
        direction_index: int = result_tensor[0] % LENGTH[CommandCostDefinerTensorNames]
        distance_variant_index: int = int(result_tensor[0] / LENGTH[CommandCostDefinerTensorNames])

        return AiCommand(
            direction=DIRECTIONS[direction_index],
            distance=length_variant[distance_variant_index],
            command_name=CommandName.move_or_attack
        )

    def compile(self, optimizer: MyOptimizer, loss: MyErrorFunction):
        self._final_model = keras.Model(
            inputs=self._input_layer,
            outputs=self._output_layer[CommandDefinerLevel.result.value]
        )
        new_loss: Loss = self._create_loss(loss)
        new_optimizer: OptimizerV2 = self._create_optimizer(optimizer, new_loss)

        # TODO 7kia загрузка модели
        self._final_model.compile(
            optimizer=new_optimizer,
            loss=new_loss,
            # metrics=['accuracy'],
        )
        self._load_weight()
        # keras.utils.plot_model(self._final_model, "./scout_network_model.png", show_shapes=True)

    def _load_weight(self):
        if self._exist_file(self._model_weight_path):
            self._final_model.load_weights(self._model_weight_path)
        else:
            self._final_model.save_weights(self._model_weight_path)

    def _exist_file(self, path: str) -> bool:
        return os.path.isfile(path)

    def set_input_param_cost_definer(self, layer: Dict[str, Layer]):
        self.__input_param_cost_definer = layer

    def set_command_cost_definer(self, layer: Dict[str, Layer]):
        self.__command_cost_definer = layer

    def _set_current_and_last_game_state(self, current_game_state: TfConstant):
        if self._current_game_state is None:
            self._current_game_state = current_game_state
        self._last_game_state = self._current_game_state
        self._current_game_state = current_game_state

    def set_command_definer(self, layer: Layer):
        self.__command_definer = layer

    # TODO 7kia используется стандартный алгоритм обучения
    def _create_optimizer(self, optimizer: MyOptimizer, new_loss: Loss) -> OptimizerV2:
        # gradients = []
        # with tf.GradientTape() as tape:
        #     for var in self._final_model.variables:
        #         tape.watch(self._final_model.variables)
        #         gradients.append(
        #             tape.gradient(new_loss(None, None), clip_gradients(var))
        #         )

        #     current_loss = loss(outputs, model(inputs))
        # gradients = tf.gradients(new_loss, self._final_model.variables)
        # model.W.assign_sub(learning_rate * dW)
        # model.b.assign_sub(learning_rate * db)

        new_optimizer: OptimizerV2 = tf.keras.optimizers.SGD(learning_rate=1e-3)
        # Compute the gradients for a list of variables.
        # with tf.GradientTape() as tape:
        #     loss = new_loss.call()
        # vars = self._final_model.variables
        # grads = tape.gradient(loss, vars)

        # Process the gradients, for example cap them, etc.
        # capped_grads = [MyCapper(g) for g in grads]
        # processed_grads = [process_gradient(g) for g in grads]
        # Ask the optimizer to apply the processed gradients.
        # grads_and_vars = list(zip(np.copy(gradients), self._final_model.variables))
        # new_optimizer.apply_gradients(grads_and_vars)#processed_grads
        # new_optimizer.minimize(
        #         lambda x=None, y=None: new_loss.call(x, y),
        #         var_list=self._final_model.trainable_weights,
        #         grad_loss=zip(gradients, self._final_model.variables)
        #     )
        # new_optimizer.minimize(new_loss, var_list=self._final_model.trainable_weights)

        # new_optimizer.apply_gradients(zip(grads, self._final_model.trainable_weights))
        return new_optimizer

    def _create_loss(self, loss: MyErrorFunction) -> Loss:
        error_function: TensorflowErrorFunction = loss
        result = ScoutNetworkLossFunction(error_function)
        result.set_game_states(self.get_current_state, self.get_last_state)
        return result



