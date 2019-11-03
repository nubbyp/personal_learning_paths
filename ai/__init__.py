import os
import time
import warnings
import logging
from stable_baselines import A2C
from stable_baselines.common.policies import MlpLstmPolicy
from stable_baselines.common.vec_env import DummyVecEnv
import ai.gym as wrappers

def load(agent, from_disk=True):
    try:
        env = wrappers.Environment(agent)
        env = DummyVecEnv([lambda: env])
        a2c = A2C(MlpLstmPolicy, env) 
        return a2c
    except Exception as e:
        logging.exception("error while starting AI")
    return False
