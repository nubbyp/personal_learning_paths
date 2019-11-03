import logging
import gym
from gym import spaces
import numpy as np

import ai.featurizer as featurizer
import ai.reward as reward
from ai.parameter import Parameter

MAX_RESULTS = 20

class Environment(gym.Env):
    params = [
    	Parameter('param_'+str(x), min_value=-10, max_value=10)
    	for x in range(MAX_RESULTS)
    ]
    
    def __init__(self, agent):
        super(Environment, self).__init__()
        self._agent = agent
        self._epoch_num = 0
        self._last_render = None
        self._state = {}

        self.last = {
            'reward': 0.0,
            'observation': None,
            'policy': None,
            'params': {},
            'state': None,
            'state_v': None
        }

        self.action_space = spaces.MultiDiscrete([p.space_size() for p in Environment.params if p.trainable])
        self.observation_space = spaces.Box(low=0, high=1, shape=featurizer.shape, dtype=np.float32)
        self.reward_range = reward.range

    @staticmethod
    def policy_size():
        return len(list(p for p in Environment.params if p.trainable))

    @staticmethod
    def policy_to_params(policy):
        num = len(policy)
        params = {}

        assert len(Environment.params) == num

        for i in range(num):
            param = Environment.params[i]
            params[param.name] = param.to_param_value(policy[i])
        
        return params

    def _apply_policy(self, policy):
        new_params = Environment.policy_to_params(policy)
        self.last['policy'] = policy
        self.last['params'] = new_params
        self._agent.on_ai_policy(new_params)

    def set_state(self, state):
        self._state = state
        return self._state
        
    def get_state(self):
        return self._state
        
    def step(self, policy):
        self._apply_policy(policy)
        self._epoch_num += 1
        f = reward.RewardFunction()
        self.last['reward'] = f(self._state)
        self.last['state'] = self._state
        self.last['state_v'] = featurizer.featurize(self._state)
        self._agent.on_ai_step()
        return self.last['state_v'], self.last['reward'], not self._agent.is_training(), {}

    def reset(self):
        self._epoch_num = 0
        
    def render(self, mode='human', close=False, force=False):
        return
