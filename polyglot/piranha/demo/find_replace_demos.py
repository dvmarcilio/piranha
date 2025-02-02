from collections import Counter
from os.path import join, dirname
from polyglot_piranha import run_piranha_cli
import logging
from logging import info

find_Replace_dir = join(dirname(__file__), 'find_replace')

def swift_demo():
    """
    This shows how we can use Piranha to execute structural find/replace that hook on the the 
    pre-built rules.
    """    
    info("Running the Find/Replace demo for Swift")
    _ = run_piranha_cli(join(find_Replace_dir, "swift"), join(find_Replace_dir, "swift/configurations"), True)

def strings_demo():
    """
    This shows how we can use Piranha to execute structural find/replace without hooking up anything.
    """    
    info("Running the Find/Replace demo for Strings")
    _ = run_piranha_cli(join(find_Replace_dir, "strings"), join(find_Replace_dir, "strings/configurations"), True)

def java_demo():
    """
    This shows how we can use Piranha to execute structural find/replace that hook on the the 
    pre-built rules.
    Note how it deletes the enum declaration and consequently the file. 
    Deletion of the file can be disabled by setting the `delete_file_if_empty` flag to False.
    """    
    info("Running the Find/Replace demo for Java")
    _ = run_piranha_cli(join(find_Replace_dir, "java"), join(find_Replace_dir, "java/configurations"), True)


FORMAT = '%(levelname)s %(name)s %(asctime)-15s %(filename)s:%(lineno)d %(message)s'
logging.basicConfig(format=FORMAT)
logging.getLogger().setLevel(logging.INFO)
swift_demo()
strings_demo()
java_demo()
print("Completed running the Find/Replace demos")
