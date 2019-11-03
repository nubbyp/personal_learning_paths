import _thread
import threading
import time
import random
import os
import json
import logging

import ai

LAZINESS = 0.3

class Stats(object):
    def __init__(self, path, events_receiver):
        self._lock = threading.Lock()
        self._receiver = events_receiver
        self.path = path
        self.born_at = time.time()
        self.epochs_lived = 0
        self.epochs_trained = 0
        self.worst_reward = 0.0
        self.best_reward = 0.0
        self._obs = None
        
        self.load()

    def on_epoch(self, data, training):
        best_r = False
        worst_r = False
        with self._lock:
            reward = data['reward']
            if reward < self.worst_reward:
                self.worst_reward = reward
                worst_r = True

            elif reward > self.best_reward:
                best_r = True
                self.best_reward = reward

            self.epochs_lived += 1
            if training:
                self.epochs_trained += 1

        self.save()

        if best_r:
            self._receiver.on_ai_best_reward(reward)
        elif worst_r:
            self._receiver.on_ai_worst_reward(reward)

    def load(self):
        with self._lock:
            if os.path.exists(self.path) and os.path.getsize(self.path) > 0:
                logging.info("[ai] loading %s" % self.path)
                with open(self.path, 'rt') as fp:
                    obj = json.load(fp)

                self.born_at = obj['born_at']
                self.epochs_lived, self.epochs_trained = obj['epochs_lived'], obj['epochs_trained']
                self.best_reward, self.worst_reward = obj['rewards']['best'], obj['rewards']['worst']

    def save(self):
        with self._lock:
            logging.info("[ai] saving %s" % self.path)

            data = json.dumps({
                'born_at': self.born_at,
                'epochs_lived': self.epochs_lived,
                'epochs_trained': self.epochs_trained,
                'rewards': {
                    'best': self.best_reward,
                    'worst': self.worst_reward
                }
            })

            temp = "%s.tmp" % self.path
            with open(temp, 'wt') as fp:
                fp.write(data)

            os.replace(temp, self.path)


class AsyncTrainer(object):
    def __init__(self):
        self._model = None
        self._is_training = False
        self._training_epochs = 0
        self._nn_path = "/Users/geva/src/dvhacks/"
        self._stats = Stats("%s.json" % os.path.splitext(self._nn_path)[0], self)
        self.weights = {
    	    'param_'+str(x):1
    	    for x in range(20)
        }
         
    def set_training(self, training, for_epochs=0):
        self._is_training = training
        self._training_epochs = for_epochs

    def is_training(self):
        return self._is_training

    def training_epochs(self):
        return self._training_epochs

    def start_ai(self):
        self._model = ai.load(self)
        if self._model:
            self.on_ai_ready()
            self._obs = None
            

    def _save_ai(self):
        logging.info("[ai] saving model to %s ..." % self._nn_path)
        temp = "%s.tmp" % self._nn_path
        self._model.save(temp)
        os.replace(temp, self._nn_path)

    def on_ai_step(self):
        self._model.env.render()
        
        if self._is_training:
            self._save_ai()

        #self._stats.on_epoch(self._epoch.data(), self._is_training)

    def on_ai_training_step(self, _locals, _globals):
        pass

    def on_ai_policy(self, new_params):
        for name, value in new_params.items():
            curr_value = self.weights[name]
            if curr_value != value:
                logging.info("[ai] ! %s: %s -> %s" % (name, curr_value, value))
                self.weights[name] = value
        
    def on_ai_ready(self):
        pass
       
    def on_ai_best_reward(self, r):
        logging.info("[ai] best reward so far: %s" % r)

    def on_ai_worst_reward(self, r):
        logging.info("[ai] worst reward so far: %s" % r)

    def ai_step(self, state):
        if self._obs is None:
            self._obs = self._model.env.reset()
        self._model.env.env_method('set_state', state)
        self._model.learn(total_timesteps=1)
        action, _ = self._model.predict(self._obs)
        self._obs, _, _, _ = self._model.env.step(action)
        