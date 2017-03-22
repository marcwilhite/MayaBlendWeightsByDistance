# MayaBlendSkinWeightsByDistance
### Distance blending of vertex weights in either 3d space or UV space.
It requires that more than 3 vertices are selected. The weight of the middle vertices will be blended
with either linear or quadratic interpolation with the vertex pair with the greatest distance as the
blend sources. Select vertices and run 'blendWeightsByDistance' command.

Parameters:  
 - uvspace [uv] (default is False) 
 - quadraticblend [qb] (default is False)

Example:
 ```
 import maya.cmds as mc
 mc.blendWeightsByDistance()   # blends in linear 3d space
 mc.blendWeightsByDistance(uv=True)  # blend in linear uv space
 mc.blendWeightsByDistance(qb=True)  # blends in quadratic 3d space
 mc.blendWeightsByDistance(uv=True, qb=True)  # blends in quadratic uv space
 ```
