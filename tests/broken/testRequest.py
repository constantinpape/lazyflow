###############################################################################
#   lazyflow: data flow based lazy parallel computation framework
#
#       Copyright (C) 2011-2014, the ilastik developers
#                                <team@ilastik.org>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the Lesser GNU General Public License
# as published by the Free Software Foundation; either version 2.1
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Lesser General Public License for more details.
#
# See the files LICENSE.lgpl2 and LICENSE.lgpl3 for full text of the
# GNU Lesser General Public License version 2.1 and 3 respectively.
# This information is also available on the ilastik web site at:
#		   http://ilastik.org/license/
###############################################################################
from lazyflow.request import Request, global_thread_pool
import os
import time
import random
import numpy
import h5py

import threading

class TestRequest(object):
    
    @classmethod
    def setupClass(cls):
        pass

    @classmethod
    def teardownClass(cls):
        pass
    
    def test_basic(self):
        def someWork():
            time.sleep(0.001)
            #print "producer finished"

        def callback(s):
            pass

        def test(s):
            req = Request(someWork)
            req.notify(callback)
            req.wait()
            time.sleep(0.001)
            print s
            return s

        req = Request( test, s = "hallo !")
        req.notify(callback)
        assert req.wait() == "hallo !"

        requests = []
        for i in range(10):
            req = Request( test, s = "hallo %d" %i)
            requests.append(req)

        for r in requests:
            r.wait()

    def test_withH5Py(self):
        """
        We have suspicions that greenlet and h5py don't interact well with eachother.
        This tests basic functionality.
        TODO: Expand it for better coverage.
        """
        maxDepth = 5
        maxBreadth = 10

        filename = 'requestTest.h5'
        h5File = h5py.File( filename, 'w' )
        dataset = h5File.create_dataset( 'test/data', data=numpy.zeros( (maxDepth, maxBreadth), dtype=int ))

        def writeToH5Py(result, index, req):
            dataset[index] += 1

        # This closure randomly chooses to either (a) return immediately or (b) fire off more work
        def someWork(depth, force=False, i=0):
            #print 'depth=', depth, 'i=', i
            if depth > 0 and (force or random.random() > 0.5):
                requests = []
                for i in range(maxBreadth):
                    req = Request(someWork, depth=depth-1, i=i)
                    req.notify(writeToH5Py, index=(depth-1, i), req=req)
                    requests.append(req)

                for r in requests:
                    r.wait()

        req = Request(someWork, depth=maxDepth, force=True)
        req.wait()
        h5File.close()

        print "finished testWithH5Py"
        os.remove(filename)

    def test_callWaitDuringCallback(self):
        """
        When using request.notify(...) to handle request completions, the handler should be allowed to call request.wait().
        Currently, this causes a hang somewhere in request.py.
        """
        def handler(result, req):
            return
            req.wait()
            
        def workFn():
            pass
        
        req = Request(workFn)
        req.notify( handler, req=req )
        req.wait()

    def test_lotsOfSmallRequests(self):
        handlerCounter = [0]
        handlerLock = threading.Lock()
        
        def completionHandler( result, req ):
            handlerLock.acquire()
            handlerCounter[0] += 1
            handlerLock.release()

        requestCounter = [0]
        requestLock = threading.Lock()            
        allRequests = []
        # This closure randomly chooses to either (a) return immediately or (b) fire off more work
        def someWork(depth, force=False, i=-1):
            #print 'depth=', depth, 'i=', i
            if depth > 0 and (force or random.random() > 0.5):
                requests = []
                for i in range(10):
                    req = Request(someWork, depth=depth-1, i=i)
                    req.notify(completionHandler, req=req)
                    requests.append(req)
                    allRequests.append(req)
                    
                    requestLock.acquire()
                    requestCounter[0] += 1
                    requestLock.release()
            

                for r in requests:
                    r.wait()

        req = Request(someWork, depth=6, force=True)

        def blubb(req):
          pass

        req.notify(blubb)
        print "pausing graph"
        global_thread_pool.pause()
        global_thread_pool.unpause()
        print "resumed graph"
        req.wait()
        print "request finished"

        
        # Handler should have been called once for each request we fired
        assert handlerCounter[0] == requestCounter[0]

        print "finished testLotsOfSmallRequests"
        
        for r in allRequests:
          assert r.finished

        print "waited for all subrequests"
    
    def test_pause_unpause(self):
        handlerCounter = [0]
        handlerLock = threading.Lock()
        
        def completionHandler( result, req ):
            handlerLock.acquire()
            handlerCounter[0] += 1
            handlerLock.release()

        requestCounter = [0]
        requestLock = threading.Lock()            
        allRequests = []
        # This closure randomly chooses to either (a) return immediately or (b) fire off more work
        def someWork(depth, force=False, i=-1):
            #print 'depth=', depth, 'i=', i
            if depth > 0 and (force or random.random() > 0.8):
                requests = []
                for i in range(10):
                    req = Request(someWork, depth=depth-1, i=i)
                    req.notify(completionHandler, req=req)
                    requests.append(req)
                    allRequests.append(req)
                    
                    requestLock.acquire()
                    requestCounter[0] += 1
                    requestLock.release()
            

                for r in requests:
                    r.wait()

        req = Request(someWork, depth=6, force=True)

        def blubb(req):
          pass

        req.notify(blubb)
        global_thread_pool.pause()
        req2 = Request(someWork, depth=6, force=True)
        req2.notify(blubb)
        global_thread_pool.unpause()
        assert req2.finished == False
        assert req.finished
        req.wait()

        
        # Handler should have been called once for each request we fired
        assert handlerCounter[0] == requestCounter[0]

        print "finished pause_unpause"
        
        for r in allRequests:
          assert r.finished

        print "waited for all subrequests"


        
if __name__ == "__main__":
    import sys
    import nose
    sys.argv.append("--nocapture")    # Don't steal stdout.  Show it on the console as usual.
    sys.argv.append("--nologcapture") # Don't set the logging level to DEBUG.  Leave it alone.
    ret = nose.run(defaultTest=__file__)
    if not ret: sys.exit(1)
