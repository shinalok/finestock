import sys
import unittest
from unittest.mock import MagicMock
import queue

# Create verification script
class TestRefactoring(unittest.TestCase):
    def test_lazy_loading(self):
        # We need to ensure we start fresh
        if 'finestock' in sys.modules:
            del sys.modules['finestock']
        if 'finestock.ls' in sys.modules:
            del sys.modules['finestock.ls']
            
        import finestock
        # Check if ls is imported in sys.modules
        # Note: submodule might be imported but not bound to finestock.ls if lazy
        # But here we check sys.modules
        # Actually, if we just import finestock, it should NOT likely import finestock.ls unless __init__ does it
        
        # However, due to previous run_command usage or environment, it might strictly be tricky to un-import.
        # But let's try.
        # Ideally, we check that accessing finestock.ls raises AttributeError until we create it or import it.
        
        with self.assertRaises(AttributeError):
            _ = finestock.ls
            
        print("PASS: Lazy loading check (finestock.ls not accessible)")

    def test_interfaces_and_queue(self):
        import finestock
        from finestock.api_factory import APIProvider
        from finestock.comm.api_interface import MarketDataProvider, RealtimeProvider
        
        # Create API
        ls_api = finestock.create_api(APIProvider.LS)
        
        self.assertIsInstance(ls_api, MarketDataProvider, "LS should implement MarketDataProvider")
        self.assertIsInstance(ls_api, RealtimeProvider, "LS should implement RealtimeProvider")
        print("PASS: Interface implementation check")
        
        # Test Queue
        q = queue.Queue()
        ls_api.set_data_queue(q)
        
        test_data = {"price": 100}
        ls_api.add_data(test_data)
        
        received = q.get(timeout=1)
        self.assertEqual(received, test_data)
        print("PASS: Queue injection check")
        
        # Test absence of make_queue
        self.assertFalse(hasattr(ls_api, 'make_queue'), "make_queue should be removed")
        print("PASS: make_queue removal check")

if __name__ == '__main__':
    unittest.main()
