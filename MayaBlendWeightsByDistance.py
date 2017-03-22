import maya.cmds as mc
import maya.OpenMaya as OpenMaya
import maya.OpenMayaAnim as OpenMayaAnim
import maya.OpenMayaMPx as OpenMayaMPx
import math
import sys

kPluginCmdName = 'blendWeightsByDistance'
kUVSpaceFlag = "-uv"
kUVSpaceLongFlag = "-uvspace"
kQuadraticBlendFlag = "-qb"
kQuadraticBlendLongFlag = "-quadraticblend"


class BlendWeightsByDistanceCmd(OpenMayaMPx.MPxCommand):
    """
    Blends skinned vertices based on distance in either
    3d space or UV space. It requires that more than 3 vertices are
    selected. The weight of the middle vertices will be blended with
    either linear or quadratic interpolation.

    Parameters:  uvspace (default is False) quadraticblend (default is False)
    Comments:  select verts and run command 'blendWeightsByDistance' """

    def __init__(self):
        OpenMayaMPx.MPxCommand.__init__(self)

    def doIt(self, args):
        self.points = mc.ls(selection=True, fl=True, type='float3')
        self.sel = OpenMaya.MSelectionList()
        self.components = OpenMaya.MObject()
        self.dgPath = OpenMaya.MDagPath()
        self.sUtil = OpenMaya.MScriptUtil()
        self.aWeights = OpenMaya.MDoubleArray()
        self.aUndoWeights = OpenMaya.MDoubleArray()
        self.aInfluences = OpenMaya.MIntArray()

        argData = OpenMaya.MArgDatabase(self.syntax(), args)
        if argData.isFlagSet(kUVSpaceFlag):
            self.UVSpace = argData.flagArgumentBool(kUVSpaceFlag, 0)
        else:
            self.UVSpace = False
        if argData.isFlagSet(kQuadraticBlendFlag):
            self.quadraticBlend = argData.flagArgumentBool(kQuadraticBlendFlag, 0)
        else:
            self.quadraticBlend = False

        self.redoIt()

    def redoIt(self):
        if len(self.points) < 3:
            return

        if self.aWeights.length():
            self.fnSkin.setWeights(self.dgPath, self.components, self.aInfluences, self.aWeights, False, self.aUndoWeights)
            return

        for i in range(len(self.points)):
            self.sel.add(self.points[i])
        self.sel.getDagPath(0, self.dgPath, self.components)

        skin = mc.ls(mc.listHistory(self.dgPath.partialPathName()), type='skinCluster')
        if not skin:
            return
        else:
            self.skin = skin[0]

        self.sel.clear()
        self.sel.add(self.skin)
        oSkin = OpenMaya.MObject()
        self.sel.getDependNode(0, oSkin)
        self.fnSkin = OpenMayaAnim.MFnSkinCluster(oSkin)

        fComponents = OpenMaya.MFnSingleIndexedComponent(self.components)
        mc.setAttr(self.skin+'.envelope', 0.0)
        fnMesh = OpenMaya.MFnMesh(self.dgPath)
        fUV = self.sUtil.asFloat2Ptr()

        if self.UVSpace:
            dist = lambda a, b: math.sqrt((a[0] - b[0])**2 + (a[1] - b[1])**2)
        else:
            dist = lambda a, b: math.sqrt((a[0] - b[0])**2 + (a[1] - b[1])**2 + (a[2] - b[2])**2)

        maxDistance = 0
        for i in range(len(self.points)):
            for j in range(i + 1, len(self.points)):
                if self.UVSpace:
                    for k in range(2):
                        pntPos = mc.pointPosition(self.points[(j * k) + (i * abs(1-k))])
                        vPnt = OpenMaya.MFloatVector(pntPos[0], pntPos[1], pntPos[2])
                        pPnt = OpenMaya.MPoint(vPnt)
                        fnMesh.getUVAtPoint(pPnt, fUV)
                        if k:
                            lPntB = [self.sUtil.getFloat2ArrayItem(fUV, 0, 0)]
                            lPntB.append(self.sUtil.getFloat2ArrayItem(fUV, 0, 1))
                        else:
                            lPntA = [self.sUtil.getFloat2ArrayItem(fUV, 0, 0)]
                            lPntA.append(self.sUtil.getFloat2ArrayItem(fUV, 0, 1))
                else:
                    lPntA = OpenMaya.MPoint()
                    fnMesh.getPoint(fComponents.element(i), lPntA)
                    lPntB = OpenMaya.MPoint()
                    fnMesh.getPoint(fComponents.element(j), lPntB)
                d = dist(lPntA, lPntB)
                if d > maxDistance:
                    maxDistance = d
                    maxPoint = self.points[j]
                    minPoint = self.points[i]
                    minDist = list(lPntA)

        self.sel.clear()
        self.sel.add(minPoint)
        self.sel.add(maxPoint)
        baseComponents = OpenMaya.MObject()
        self.sel.getDagPath(0, self.dgPath, baseComponents)

        ptrInfCount = self.sUtil.asUintPtr()
        aBaseWeights = OpenMaya.MDoubleArray()
        self.fnSkin.getWeights(self.dgPath, baseComponents, aBaseWeights, ptrInfCount)
        iInfCount = self.sUtil.getUint(ptrInfCount)

        self.fnSkin.getWeights(self.dgPath, self.components, self.aWeights, ptrInfCount)
        self.aUndoWeights.copy(self.aWeights)
        dgInfluences = OpenMaya.MDagPathArray()
        self.fnSkin.influenceObjects(dgInfluences)

        for i in range(iInfCount):
            self.aInfluences.append(i)

        for i in range(0, self.aWeights.length(), iInfCount):
            index = fComponents.element(i / iInfCount)
            pPnt = OpenMaya.MPoint()
            fnMesh.getPoint(index, pPnt)
            if self.UVSpace:
                fnMesh.getUVAtPoint(pPnt, fUV)
                lPnt = [self.sUtil.getFloat2ArrayItem(fUV, 0, 0)]
                lPnt.append(self.sUtil.getFloat2ArrayItem(fUV, 0, 1))
                dMin = dist(minDist, lPnt) / maxDistance
            else:
                dMin = dist(minDist, pPnt) / maxDistance

            if self.quadraticBlend:
                blend = lambda x, y: (x * (1.0 - dMin)**2)/(maxDistance**2) + (y * (dMin)**2)/(maxDistance**2)

            else:
                blend = lambda x, y: (x * (1.0 - dMin)) + (y * dMin)

            for j in range(iInfCount):
                self.aWeights.set(blend(aBaseWeights[j], aBaseWeights[iInfCount + j]), i + j)

            sumTotal = sum(self.aWeights[i:i+iInfCount])
            self.aWeights[i:i+iInfCount] = [x/sumTotal for x in self.aWeights[i:i+iInfCount]]
        mc.setAttr(self.skin+'.envelope', 1.0)
        self.fnSkin.setWeights(self.dgPath, self.components, self.aInfluences, self.aWeights, False, self.aUndoWeights)

    def undoIt(self):
        self.fnSkin.setWeights(self.dgPath, self.components, self.aInfluences, self.aUndoWeights, False, self.aWeights)

    def isUndoable(self):
        return True


def cmdCreator():
    return OpenMayaMPx.asMPxPtr(BlendWeightsByDistanceCmd())


def syntaxCreator():
    syntax = OpenMaya.MSyntax()
    syntax.addFlag(kUVSpaceFlag, kUVSpaceLongFlag, OpenMaya.MSyntax.kBoolean)
    syntax.addFlag(kQuadraticBlendFlag, kQuadraticBlendLongFlag, OpenMaya.MSyntax.kBoolean)
    return syntax


def initializePlugin(mobject):
    mplugin = OpenMayaMPx.MFnPlugin(mobject)
    try:
        mplugin.registerCommand(kPluginCmdName, cmdCreator, syntaxCreator)
    except:
        sys.stderr.write('Failed to register command: ' + kPluginCmdName)
    print "done"


def uninitializePlugin(mobject):
    mplugin = OpenMayaMPx.MFnPlugin(mobject)
    try:
        mplugin.deregisterCommand(kPluginCmdName)
    except:
        sys.stderr.write('Failed to unrestier command: ' + kPluginCmdName)
