range = (-.7, 1.02)
not_zero = 1e-20


class RewardFunction(object):
    def __call__(self, state):
        if state['sel'] == 0:
        	# positive reward for top item
        	return 1
        else:
        	# negative reward for other items
        	return 0.3 * (1-state['sel'])
