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
        finalHull = self.makeHull(self.points)

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
            polygon = [QLineF(finalHull.points[i], finalHull.points[i+1])
                       for i in range(finalHull.numPoints - 1)]
            polygon.append(
                QLineF(finalHull.points[finalHull.numPoints - 1], finalHull.points[0]))
            self.show_hull.emit(polygon, (255, 0, 0))

        # send a signal to the GUI thread with the time used to compute the hull
        self.display_text.emit(
            'Time Elapsed (Convex Hull): {:3.3f} sec'.format(t4-t3))
        print('Time Elapsed (Convex Hull): {:3.3f} sec'.format(t4-t3))

    def makeHull(self, points):
        '''
        This is the start and end point of the algorithm.

        Recursively breaks the size of the list of points in half
        until there is only one point in the list then merges the two
        halves back together. This will create a tree-like structure of height log(n)
        the "putting back together" of each leaf is of order O(n).

        Time: O(nlog(n))
        '''
        if (len(points) < 2):
            # Make connections between points here
            return ConvexHull(points)
        else:
            splitIndex = math.ceil(len(points) / 2)

            leftHull = self.makeHull(points[:splitIndex])
            rightHull = self.makeHull(points[splitIndex:])

            newHull = self.mergeHulls(leftHull, rightHull)

            return newHull

    def mergeHulls(self, left, right):
        '''
        Merges to hulls together while maintaining the correct order and discarding
        any points that are not on the outer edge

        Time: O(n + n + n) or O(n) - 'n' being the number of points the two hulls have combined
                because this function calls the upper/lower tangent functions which are O(n)
                plus in the worst case of ordering the points it will have to cover all of
                the points in the two hulls
        '''
        # Find upper and lower tangents
        upperTan = self.findUpperTangent(left, right)
        lowerTan = self.findLowerTangent(left, right)

        # Maintain correct order and return the new hull with that list of points
        indexUpperLeftVertex = left.points.index(upperTan.leftPoint)
        indexUpperRightVertex = right.points.index(upperTan.rightPoint)
        indexLowerLeftVertex = left.points.index(lowerTan.leftPoint)
        indexLowerRightVertex = right.points.index(lowerTan.rightPoint)

        mergedPoints = list()
        numTotalPoints = left.numPoints + right.numPoints
        if (numTotalPoints < 4):
            # Just merge the points together, they are in order
            # This is constant time
            mergedPoints = left.points + right.points
            # If there are 3 points then figure out what their order should be
            # and overwrite the mergedPoints
            if(numTotalPoints == 3):
                leftStart = left.points[0]
                leftEnd = left.points[1]
                rightPoint = right.points[0]
                if (self.computeSlope(leftStart, rightPoint) > self.computeSlope(leftStart, leftEnd)):
                    mergedPoints = list()
                    mergedPoints.append(leftStart)
                    mergedPoints.append(rightPoint)
                    mergedPoints.append(leftEnd)
        else:
            # Get points starting from left most point on left hull to upper-left vertex
            for i in range(left.numPoints):
                if (i == indexUpperLeftVertex):
                    mergedPoints.append(left.points[indexUpperLeftVertex])
                    break
                else:
                    mergedPoints.append(left.points[i])

            # Get points from upper-right vertex to end of right hull
            i = indexUpperRightVertex
            while(True):
                i = i % right.numPoints
                if (i == indexLowerRightVertex):
                    mergedPoints.append(right.points[indexLowerRightVertex])
                    break
                mergedPoints.append(right.points[i])
                i += 1

            # Get the rest of the points on the left hull
            if (indexLowerLeftVertex != 0):
                i = indexLowerLeftVertex
                for i in range(indexLowerLeftVertex, left.numPoints):
                    mergedPoints.append(left.points[i])

        mergedHull = ConvexHull(mergedPoints)
        return mergedHull

    def findUpperTangent(self, leftHull, rightHull):
        '''
        Finds the upper tangent between two hulls by:
            1. Choosing the left-most point of the right hull &
                the right-most point of the left hull to start
            2. While maintaining the current right point,
                rotate around the left hull in a counter-clockwise direction
                (in the case of an ordered list, decrement the index)
                until the slope no longer increases
            3. While maintaining the current left point,
                rotate around the right hull in a clockwise direction
                (increment the index) until the slope no longer decreases
            4. Keep doing 2 & 3 until you don't move points any longer

        Time: O(n) - 'n' being the number of points in both the hulls
                    worst case it will need to check all the points of the two hulls
        '''
        isUpperTangentToBoth = False
        isUpperTangentToLeft = False
        isUpperTangentToRight = False
        didIterateLeft = False
        didIterateRight = False

        leftMostOnRH = rightHull.findLeftMostPoint()
        rightMostOnLH = leftHull.findRightMostPoint()
        upperRightPt = leftMostOnRH
        upperLeftPt = rightMostOnLH

        while (isUpperTangentToBoth == False):
            # Setup the inital state of each iteration
            indexLeftHullPt = leftHull.points.index(upperLeftPt)
            indexRightHullPt = rightHull.points.index(upperRightPt)
            didIterateLeft = False
            didIterateRight = False
            isUpperTangentToLeft = False
            isUpperTangentToRight = False

            # Move counter clock wise around left hull
            oldSlope = self.computeSlope(upperLeftPt, upperRightPt)
            while (isUpperTangentToLeft == False):
                indexLeftHullPt -= 1
                # Avoid out of range
                indexLeftHullPt = indexLeftHullPt % leftHull.numPoints

                newSlope = self.computeSlope(
                    leftHull.points[indexLeftHullPt], upperRightPt)
                # Slope is decreasing
                if (newSlope < oldSlope):
                    didIterateLeft = True
                    # Move to the new point
                    upperLeftPt = leftHull.points[indexLeftHullPt]
                    oldSlope = newSlope
                # Found the top point on left hull
                else:
                    break

            # Found upper left point... for now
            isUpperTangentToLeft = True

            # Move clockwise around right hull
            oldSlope = self.computeSlope(upperLeftPt, upperRightPt)
            while (isUpperTangentToRight == False):
                indexRightHullPt += 1
                # Avoid out of range
                indexRightHullPt = indexRightHullPt % rightHull.numPoints

                newSlope = self.computeSlope(
                    upperLeftPt, rightHull.points[indexRightHullPt])
                # Slope is increasing
                if (newSlope > oldSlope):
                    didIterateRight = True
                    # Move to the new point
                    upperRightPt = rightHull.points[indexRightHullPt]
                    oldSlope = newSlope
                # Found the top point on right hull
                else:
                    break

            # Found upper right point... for now
            isUpperTangentToRight = True

            # Break when both tangents are found
            if (isUpperTangentToLeft and isUpperTangentToRight and not didIterateLeft and not didIterateRight):
                # We have found the upper tangent
                isUpperTangentToBoth = True

        return Tangent(upperLeftPt, upperRightPt)

    def findLowerTangent(self, leftHull, rightHull):
        '''
        Finds the lower tangent between two hulls by:
            1. Choosing the left-most point of the right hull &
                the right-most point of the left hull to start
            2. While maintaining the current right point,
                rotate around the left hull in a clockwise direction
                (in the case of an ordered list, increment the index)
                until the slope no longer increases
            3. While maintaining the current left point,
                rotate around the right hull in a counter-clockwise direction
                (decrement the index) until the slope no longer decreases
            4. Keep doing 2 & 3 until you don't move points any longer

        Time: O(n) - 'n' being the number of points in both the hulls
                    worst case it will need to check all the points of the two hulls
        '''
        isLowerTangentToBoth = False
        isLowerTangentToLeft = False
        isLowerTangentToRight = False
        didIterateLeft = False
        didIterateRight = False

        leftMostOnRH = rightHull.findLeftMostPoint()
        rightMostOnLH = leftHull.findRightMostPoint()
        lowerRightPt = leftMostOnRH
        lowerLeftPt = rightMostOnLH

        while (isLowerTangentToBoth == False):
            # Setup the inital state of each iteration
            indexLeftHullPt = leftHull.points.index(lowerLeftPt)
            indexRightHullPt = rightHull.points.index(lowerRightPt)
            didIterateLeft = False
            didIterateRight = False
            isLowerTangentToLeft = False
            isLowerTangentToRight = False

            # Move clock wise around left hull
            oldSlope = self.computeSlope(lowerLeftPt, lowerRightPt)
            while (isLowerTangentToLeft == False):
                indexLeftHullPt += 1
                # Avoid out of range
                indexLeftHullPt = indexLeftHullPt % leftHull.numPoints

                newSlope = self.computeSlope(
                    leftHull.points[indexLeftHullPt], lowerRightPt)
                # Slope is increasing
                if (newSlope > oldSlope):
                    didIterateLeft = True

                    # Move the iterator to the new point
                    lowerLeftPt = leftHull.points[indexLeftHullPt]
                    oldSlope = newSlope
                # Found the lowest point on left hull
                else:
                    break

            # Found upper left point for now
            isLowerTangentToLeft = True

            # Move clockwise around right hull
            oldSlope = self.computeSlope(lowerLeftPt, lowerRightPt)
            while (isLowerTangentToRight == False):
                indexRightHullPt -= 1
                # Avoid out of range
                indexRightHullPt = indexRightHullPt % rightHull.numPoints

                newSlope = self.computeSlope(lowerLeftPt,
                                             rightHull.points[indexRightHullPt])
                # Slope is decreasing
                if (newSlope < oldSlope):
                    didIterateRight = True
                    # Move to the new point
                    lowerRightPt = rightHull.points[indexRightHullPt]
                    oldSlope = newSlope
                # Found the lowest point on right hull
                else:
                    break

            # Set the status bit for the right hull lower tangent to true
            isLowerTangentToRight = True

            # Break when both tangents are found
            if (isLowerTangentToLeft and isLowerTangentToRight and not didIterateLeft and not didIterateRight):
                # We have found the lower tangent
                isLowerTangentToBoth = True

        return Tangent(lowerLeftPt, lowerRightPt)

    def computeSlope(self, firstPoint, secondPoint):
        '''
        Calculates the slope between two points
        i.e.
            y2 - y1
        -----------
            x2 - x1
        Time: O(1) this is just a constant time operation
        '''
        rise = secondPoint.y() - firstPoint.y()
        run = secondPoint.x() - firstPoint.x()
        return rise / run


class Tangent:
    '''
    A tangent is simply two points that, in the case
    of this lab, connect two hulls
    '''

    def __init__(self, leftHullPt, rightHullPt):
        self.leftPoint = leftHullPt
        self.rightPoint = rightHullPt


class ConvexHull:
    '''
    A convex hull is an ordered list of points
    The list always begins with the left-most point
    '''

    def __init__(self, sortedPoints):
        self.points = sortedPoints
        self.numPoints = len(sortedPoints)

    def findRightMostPoint(self):
        '''
        Finds the right-most point in the list
        Time: O(n) in the worst case it will traverse the
            entire list, but this is rare
        '''
        if (self.numPoints == 1):
            return self.points[0]

        rightMostVal = -100.0
        rightMostIndex = 0
        indexCounter = 0

        for point in self.points:
            if (float(point.x()) > rightMostVal):
                rightMostVal = point.x()
                rightMostIndex = indexCounter
            indexCounter += 1

        return self.points[rightMostIndex]

    def findLeftMostPoint(self):
        '''
        Finds the left-most point in the list
        Time: O(1) the left-most is always first
        '''
        return self.points[0]
