"""print and time things"""
import time
import sys

progress_ready = False
toolbar_width = 40
start_time = 0

if not progress_ready:
        # setup toolbar
        sys.stdout.write("Booting [%s]" % (" " * toolbar_width))
        sys.stdout.flush()
        sys.stdout.write("\b" * (toolbar_width+1)) # return to start of line, after '['
        progress_ready = True
        start_time = time.time()

def progress(step, end = False):
    """print info"""
    global toolbar_width, start_time

    
    for i in range(step):
        sys.stdout.write("-")
        sys.stdout.flush()
    
    #sys.stdout.write(str(step))
    #print("--- %s seconds ---" % (time.time() - start_time))


    if end:
        sys.stdout.write("]\n") # this ends the progress bar
        sys.stdout.flush()
        #print("--- %s seconds ---" % (time.time() - start_time))