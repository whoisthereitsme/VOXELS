from utils import *
from world import *
from bundle import *
from tests import *



def tests(tests:list=None) -> None:
    if tests is None:
        tests = [test1, test2, test3, test4, test5, test6]

    
    with Bundle():
        try:
            for i, test in enumerate(tests):
                
                print(f"\n=== RUNNING TEST {i+1}/{len(tests)}: {test.__name__} ===")
                timer.lap()
                test()
                print(f"=== TEST {i+1}/{len(tests)}: {test.__name__} PASSED in {timer.lap():.3f} seconds ===\n")

        except Exception:
            traceback.print_exc()
        finally:
            pass