from multiprocessing import Pool
import sys
import time

def f(name):
    print 'hello', name
    #sys.stdout.flush()

if __name__ == '__main__':
    p = Pool(3)
    p.map_async(f, ('bob', 'china', 'mina'))
    time.sleep(10)
