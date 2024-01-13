import unittest
from extension.coordination.coordination_manager import CoordinationManager  

class CoordinationManagerTest(unittest.TestCase):
    def setUp(self):
        self._cm = CoordinationManager.getInstance()
        
    def tearDown(self):
        self._cm.remove_all_observables()

    def test_observer_is_called_no_condition(self):
        n = 5  # Number of expected callback invocations
        callback_counter = [0]
        def action(state):
            callback_counter[0] = state['test']
        self._cm.add_observable('single_test', {'test': 0})
        self._cm.observe(observable_name='single_test', action=action)

        for i in range(1, n+1):
            self._cm.update_observable_state(observable_name='single_test', new_state={'test': i})
        self.assertEqual(callback_counter[0], n, f"Observer should be called {n} times")
    
    def test_observer_is_not_called_when_late(self):
        callback_counter = [0]
        def action(state):
            callback_counter[0] = state['test']
        self._cm.add_observable('single_test', {'test': 0})
        self._cm.update_observable_state(observable_name='single_test', new_state={'test': 1})
        self._cm.observe(observable_name='single_test', action=action)
        self.assertEqual(callback_counter[0], 0, f"Late Observer should not be called")

    def test_observer_is_called_with_condition(self):
        n = 5  # Number of expected callback invocations
        callback_counter = [0]
        def action(state):
            callback_counter[0] = state['test']
        def condition(state):
            return state['test'] <= n
        self._cm.add_observable('single_test', {'test': 0})
        self._cm.observe(observable_name='single_test', action=action, condition=condition)

        for i in range(1, n+10):
            self._cm.update_observable_state(observable_name='single_test', new_state={'test': i})

        self.assertEqual(callback_counter[0], n, f"Observer should be called max {n} times due to the condition")


    def test_multi_observer_is_called(self):
        n = 5  # Number of expected callback invocations for each observable
        global_callback_counter = [0]
        observable_1_value= [0]
        observable_2_value= [0]
        def action(state):
            global_callback_counter[0] += 1
            observable_1_value[0] = state[0]['test_1']
            observable_2_value[0] = state[1]['test_2']
        self._cm.add_observable('multi_test_1', {'test_1': 0})
        self._cm.add_observable('multi_test_2', {'test_2': 0})
        self._cm.multi_observe(observable_names=['multi_test_1', 'multi_test_2'], action=action)

        for i in range(1, n+1):
            self._cm.update_observable_state(observable_name='multi_test_1', new_state={'test_1': i})
            self._cm.update_observable_state(observable_name='multi_test_2', new_state={'test_2': i})
        
        #some other updates for # 2
        self._cm.update_observable_state(observable_name='multi_test_2', new_state={'test_2': 10})

        self.assertEqual(global_callback_counter[0], 11, f"Observer should be called 11 times")
        self.assertEqual(observable_1_value[0], n, f"Observer should be called max {n} times")
        self.assertEqual(observable_2_value[0], 10, f"Observer should be called max 10 times")

    def test_multi_observer_is_called_with_conditon(self):
        n = 5  # Number of expected callback invocations for each observable
        global_callback_counter = [0]
        observable_1_value= [0]
        observable_2_value= [0]
        def action(state):
            global_callback_counter[0] += 1
            observable_1_value[0] = state[0]['test_1']
            observable_2_value[0] = state[1]['test_2']
        
        def condition(state):
            return state[0]['test_1'] <= n and state[1]['test_2'] <= 8
        
        self._cm.add_observable('multi_test_1', {'test_1': 0})
        self._cm.add_observable('multi_test_2', {'test_2': 0})
        self._cm.multi_observe(observable_names=['multi_test_1', 'multi_test_2'], action=action , condition=condition)

        for i in range(1, n+10):
            self._cm.update_observable_state(observable_name='multi_test_1', new_state={'test_1': i}) # call 5
            self._cm.update_observable_state(observable_name='multi_test_2', new_state={'test_2': i}) # call 5

        #some other updates
        self._cm.update_observable_state(observable_name='multi_test_1', new_state={'test_1': n}) # not call
        self._cm.update_observable_state(observable_name='multi_test_2', new_state={'test_2': 6}) # call
        self._cm.update_observable_state(observable_name='multi_test_2', new_state={'test_2': 7}) # call
        self._cm.update_observable_state(observable_name='multi_test_2', new_state={'test_2': 8}) # call
        self._cm.update_observable_state(observable_name='multi_test_2', new_state={'test_2': 100}) # not call
        self._cm.update_observable_state(observable_name='multi_test_2', new_state={'test_2': 101}) # not call
        self._cm.update_observable_state(observable_name='multi_test_2', new_state={'test_2': 102}) # not call
        

        self.assertEqual(observable_1_value[0], n, f"Observer should have max {n} value due to the condition")
        self.assertEqual(observable_2_value[0], 8, f"Observer should have max 8 times due to the condition")
        self.assertEqual(global_callback_counter[0], 13, f"Observer should be called 13 times due to the condition")

if __name__ == '__main__':
    unittest.main()