# Copyright (c) 2024 Advanced Micro Devices, Inc. All Rights Reserved.

"""
Implementation of gym.vector.VectorEnv backed by a Schola Environment.
"""

from typing import Dict, List, Tuple, TypeVar, Union
from schola.core.unreal_connections import UnrealConnection
from schola.core.env import ScholaEnv
from schola.core.error_manager import EnvironmentException
import numpy as np
import gymnasium as gym
from schola.core.utils import nested_get, IdManager

import logging

T = TypeVar("T")

class GymVectorEnv(gym.vector.VectorEnv):
    """
    A Gym Vector Environment that wraps a Schola Environment.

    Parameters
    ----------
    unreal_connection : UnrealConnection
        The connection to the Unreal Engine.
    verbosity : int, default=0
        The verbosity level for the environment.

    Attributes
    ----------
    reset_infos : List[Dict[str,str]]
        The information returned from the last reset.
    """
    def __init__(
        self,
        unreal_connection : UnrealConnection,
        verbosity: int = 0
    ):
        self._env = ScholaEnv(
            unreal_connection,
            verbosity,
        )
        self.id_manager = IdManager(self._env.ids)
        # we just use the default UID to get the shared definition
        single_obs_space = self._env.get_obs_space(*self.id_manager[0])
        single_action_space = self._env.get_action_space(*self.id_manager[0])
        
        #test that everything is setup correctly
        try:
            for env_id, agent_id in self.id_manager.id_list:
                assert self._env.get_action_space(env_id,agent_id) == single_action_space, f"Action Space Mismatch on Agent:{agent_id} in Env {env_id}.\nGot: {self._env.get_action_space(env_id,agent_id)}\nExpected:{single_action_space}"
                assert self._env.get_obs_space(env_id,agent_id) == single_obs_space, f"Observation Space Mismatch on Agent:{agent_id} in Env {env_id}.\nGot: {self._env.get_obs_space(env_id,agent_id)}\nExpected:{single_obs_space}"
        except Exception as e:
            self._env.close()
            raise e
        
        logging.debug(single_action_space)
        logging.debug(single_obs_space)
        self.reset_infos : List[Dict[str,str]] = {}

        super().__init__(self._env.num_agents, single_obs_space, single_action_space)

    def close(self) -> None:
        super().close()
        return self._env.close()

    def get_attr(self, name:str) -> List[None]:
        """
        Get an attribute from the environment.

        Parameters
        ----------
        name: str
            The name of the attribute to get.
        
        Notes
        -----
        This method is not implemented and will always return a list of None values, as sub-environments are not individually accessible.
        """
        return [None for x in range(0, self._env.num_envs)]

    def reset_async(self,seed=None,options=None):
        pass # do nothing here for now

    def reset_wait(self, seed:Union[None, List[int], int]=None, options: Union[List[Dict[str,str]], Dict[str,str], None]=None ) -> Tuple[Dict[str,np.ndarray], Dict[int,Dict[str,str]]]:
        obs, nested_infos = self._env.hard_reset(seeds=seed,options=options)
        if isinstance(seed,int):
            self._np_random = self._env.np_random
        
        infos = {}
        for env_id in nested_infos:
            for agent_id in nested_infos[env_id]:
                uid = self.id_manager[env_id, agent_id]
                #safe because we are iterating over nested_infos
                infos[uid] = nested_infos[env_id][agent_id]

        # flatten the observations, converting from dict to list using key as indices
        obs = self.batch_obs(obs)
        return obs, infos

    def batch_obs(self, obs: Dict[int, Dict[int,Dict[str, np.ndarray]]]) -> Dict[str,np.ndarray]:
        batched_observations = gym.experimental.vector.utils.create_empty_array(self.single_observation_space, n=self.num_envs)
        flattened_observations = self.id_manager.flatten_id_dict(obs)
        gym.experimental.vector.utils.concatenate(self.single_observation_space, flattened_observations, batched_observations)
        return batched_observations
    
    def unbatch_actions(self, actions: Dict[int,np.ndarray]) -> Dict[int,Dict[int,Dict[str,np.ndarray]]]:
        """
        Unbatch actions from Dict[ObsID,Batched] to a nested Dict[EnvId,Dict[AgentId,Dict[ObsId,Value]]], effectively moving the env, and agent dimensions into Dictionaries.

        Parameters
        ----------
        actions : Dict[int,np.ndarray]
            The batched actions to unbatch.
        
        Returns
        -------
        Dict[int,Dict[int,Dict[str,np.ndarray]]]
            The unbatched actions.
        """
        #To prevent issues with non-iterable spaces we use the regular action space if num_envs ==1
        it = gym.experimental.vector.utils.iterate(self.action_space, actions)
        return self.id_manager.nest_id_list([value for value in it])


    def step_async(self, actions: Dict[int,np.ndarray]) -> None:
        actions = self.unbatch_actions(actions)
        self._env.send_actions(actions)
    
    def step_wait(self) -> Tuple[Dict[str,np.ndarray], np.ndarray, np.ndarray, np.ndarray, Dict[int,Dict[str,str]]]:
        observations, rewards, terminateds, truncateds, nested_infos = self._env.poll()

        array_rewards = np.asarray(self.id_manager.flatten_id_dict(rewards))

        array_observations = self.batch_obs(observations)
        array_terminateds = np.asarray(self.id_manager.flatten_id_dict(terminateds))
        array_truncateds = np.asarray(self.id_manager.flatten_id_dict(truncateds))
        
        envs_to_reset = []
        infos = {}

        for env_id in nested_infos:
            for agent_id in nested_infos[env_id]:
                uid = self.id_manager[env_id, agent_id]
                #safe because we are iterating over nested_infos
                infos[uid] = nested_infos[env_id][agent_id]

        for env_id, agent_id_list in enumerate(self._env.ids):
            #We don't handle the case where 1 agent ends early currently.
            if(any(terminateds[env_id].values()) or any(truncateds[env_id].values())):
                if(all(terminateds[env_id].values()) or all(truncateds[env_id].values())):
                    envs_to_reset.append(env_id)
                else:
                    raise EnvironmentException(f"Gym with multi-agent environments does not support agents completing at different steps. Env {env_id} had agents in different completion states.")
        
        if len(envs_to_reset) > 0:
            resetted_obs, reset_infos = self._env.soft_reset(envs_to_reset)
            for env_id in envs_to_reset:
                for agent_id in self.id_manager.partial_get(env_id):
                    uid = self.id_manager[env_id, agent_id]
                    #update our info to have stuff from the last step
                    infos[uid] = {**nested_get(reset_infos,[env_id, agent_id],{}),
                                  "final_info":infos[uid],
                                  "final_observation":observations[env_id][agent_id]
                                }
                    array_observations[uid] =  resetted_obs[env_id][agent_id]
        return array_observations, array_rewards, array_terminateds, array_truncateds, infos
