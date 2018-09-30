#!/usr/bin/python3
# why the shebang here, when it's imported?  Can't really be used stand alone, right?  And fermat.py didn't have one...
# this is 4-5 seconds slower on 1000000 points than Ryan's desktop...  Why?


from which_pyqt import PYQT_VER
if PYQT_VER == 'PYQT5':
    from PyQt5.QtCore import QLineF, QPointF, QThread, pyqtSignal
elif PYQT_VER == 'PYQT4':
    from PyQt4.QtCore import QLineF, QPointF, QThread, pyqtSignal
else:
    raise Exception('Unsupported Version of PyQt: {}'.format(PYQT_VER))


import time
import math


class ConvexHullSolverThread(QThread):
    def __init__(self, unsorted_points, demo):
        self.points = unsorted_points
        self.pause = demo
        QThread.__init__(self)

    def __del__(self):
        self.wait()

    show_hull = pyqtSignal(list, tuple)
    display_text = pyqtSignal(str)

    # some additional thread signals you can implement and use for debugging, if you like
    show_tangent = pyqtSignal(list, tuple)
    erase_hull = pyqtSignal(list)
    erase_tangent = pyqtSignal(list)

    def run(self):
        assert(type(self.points) == list and type(self.points[0]) == QPointF)

        n = len(self.points)
        print('Computing Hull for set of {} points'.format(n))

        t1 = time.time()
        self.points.sort(key=lambda point: point.x())

        t2 = time.time()
        print('Time Elapsed (Sorting): {:3.3f} sec'.format(t2-t1))

        t3 = time.time()
        finalHull = self.solve(self.points)

        t4 = time.time()

        USE_DUMMY = False
        if USE_DUMMY:
            # this is a dummy polygon of the first 3 unsorted points
            polygon = [QLineF(self.points[i], self.points[(i+1) % 3])
                       for i in range(3)]

            # when passing lines to the display, pass a list of QLineF objects.  Each QLineF
            # object can be created with two QPointF objects corresponding to the endpoints
            assert(type(polygon) == list and type(polygon[0]) == QLineF)
            # send a signal to the GUI thread with the hull and its color
            self.show_hull.emit(polygon, (255, 0, 0))

        else:
            # TODO: PASS THE CONVEX HULL LINES BACK TO THE GUI FOR DISPLAY
            polygon = [QLineF(finalHull.points[i], finalHull.points[(i+1) % 3])
                       for i in range(3)]
            self.show_hull.emit(polygon, (0, 255, 0))

        # send a signal to the GUI thread with the time used to compute the hull
        self.display_text.emit(
            'Time Elapsed (Convex Hull): {:3.3f} sec'.format(t4-t3))
        print('Time Elapsed (Convex Hull): {:3.3f} sec'.format(t4-t3))

    def solve(self, sortedPoints):
        splitIndex = math.ceil(len(sortedPoints) / 2)

        leftHull = self.makeHull(sortedPoints[:splitIndex])
        rightHull = self.makeHull(sortedPoints[splitIndex:])

        # return mergeHulls(leftHull, rightHull)
        return ConvexHull(sortedPoints)

    def makeHull(self, points):
        if (len(points) < 4):
            # Make connections between points here
            return ConvexHull(points)
        else:
            splitIndex = math.ceil(len(points) / 2)

            leftHull = self.makeHull(points[:splitIndex])
            rightHull = self.makeHull(points[splitIndex:])

    def mergeHulls(self, left, right):
        pass

    def findUpperTangent(self):
        pass

    def findLowerTangent(self):
        pass

    def computeSlope(self, firstPoint, secondPoint):
        pass


class ConvexHull:
    def __init__(self, sortedPoints):
        self.points = sortedPoints
        self.numPoints = len(sortedPoints)

    def findRightMostPoint(self):
        # TODO: change this bad boy
        return self.points[self.numPoints - 1]

    def findLeftMostPoint(self):
        return self.points[0]
