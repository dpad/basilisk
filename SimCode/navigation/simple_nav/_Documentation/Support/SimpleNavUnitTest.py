''' '''
'''
 ISC License

 Copyright (c) 2016-2017, Autonomous Vehicle Systems Lab, University of Colorado at Boulder

 Permission to use, copy, modify, and/or distribute this software for any
 purpose with or without fee is hereby granted, provided that the above
 copyright notice and this permission notice appear in all copies.

 THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
 WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
 MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
 ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
 WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
 ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
 OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

'''
#Very simple simulation.  Just sets up and calls the SPICE interface.  Could 
#be the basis for a unit test of SPICE

import pytest
import sys, os, inspect


filename = inspect.getframeinfo(inspect.currentframe()).filename
path = os.path.dirname(os.path.abspath(filename))
splitPath = path.split('SimCode')
sys.path.append(splitPath[0] + '/modules')
sys.path.append(splitPath[0] + '/PythonModules')

import matplotlib.pyplot as plt
import numpy
import ctypes
import math

#sys.path.append(os.environ['SIMULATION_BASE']+'/modules')
#sys.path.append(os.environ['SIMULATION_BASE']+'/PythonModules/')

#Import all of the modules that we are going to call in this simulation
import simple_nav
import spice_interface
import six_dof_eom
import MessagingAccess
import SimulationBaseClass
import sim_model


def listNorm(inputList):
   normValue = 0.0
   for elem in inputList:
      normValue += elem*elem
   normValue = math.sqrt(normValue)
   i=0
   while i<len(inputList):
      inputList[i] = inputList[i]/normValue
      i += 1

      

TestResults = {}

#Create a sim module as an empty container
TotalSim = SimulationBaseClass.SimBaseClass() 
TotalSim.CreateNewTask("sNavTestTask", int(1E8))

#Now initialize the modules that we are using.  I got a little better as I went along
sNavObject = simple_nav.SimpleNav()
TotalSim.AddModelToTask("sNavTestTask", sNavObject)

TotalSim.TotalSim.CreateNewMessage("inertial_state_output", 25*8, 2)
TotalSim.TotalSim.CreateNewMessage("sun_planet_data", 7*8+64, 2)

SpiceMessage = spice_interface.SpicePlanetState()
StateMessage = six_dof_eom.OutputStateData()

vehPosition = [10000.0, 0.0, 0.0]
sunPosition = [10000.0, 1000.0, 0.0]

SimulationBaseClass.SetCArray(vehPosition, 'double', StateMessage.r_N)
SimulationBaseClass.SetCArray(sunPosition, 'double', 
   SpiceMessage.PositionVector)
SpiceMessage.PlanetName = "sun"

TotalSim.TotalSim.WriteMessageData("inertial_state_output", 25*8, 0, 
   StateMessage);
TotalSim.TotalSim.WriteMessageData("sun_planet_data", 7*8+64, 0, SpiceMessage);
sNavObject.ModelTag = "SimpleNavigation"
posBound = [1000.0]*3
velBound = [1.0]*3
attBound = [5E-3]*3
rateBound = [0.02]*3
sunBound = [5.0*math.pi/180.0]*3
dvBound = [0.053]*3

posSigma = 5.0
velSigma = 0.05
attSigma = 5.0/3600.0*math.pi/180.0
rateSigma = 0.05*math.pi/180.0
sunSigma = 0.1*math.pi/180.0
dvSigma = 0.1*math.pi/180.0

PMatrix = [0.0]*18*18
PMatrix[0*18+0] = PMatrix[1*18+1] = PMatrix[2*18+2] = posSigma
PMatrix[3*18+3] = PMatrix[4*18+4] = PMatrix[5*18+5] = velSigma
PMatrix[6*18+6] = PMatrix[7*18+7] = PMatrix[8*18+8] = attSigma
PMatrix[9*18+9] = PMatrix[10*18+10] = PMatrix[11*18+11] = rateSigma
PMatrix[12*18+12] = PMatrix[13*18+13] = PMatrix[14*18+14] = sunSigma
PMatrix[15*18+15] = PMatrix[16*18+16] = PMatrix[17*18+17] = dvSigma
errorBounds = []
errorBounds.extend(posBound)
errorBounds.extend(velBound)
errorBounds.extend(attBound)
errorBounds.extend(rateBound)
errorBounds.extend(sunBound)
errorBounds.extend(dvBound)

sNavObject.walkBounds = sim_model.DoubleVector(errorBounds)
sNavObject.PMatrix = sim_model.DoubleVector(PMatrix)
sNavObject.crossTrans = True
sNavObject.crossAtt = False

TotalSim.TotalSim.logThisMessage("simple_nav_output", int(1E8))
TotalSim.InitializeSimulation()
TotalSim.ConfigureStopTime(int(60*144.0*1E9))
TotalSim.ExecuteSimulation()

posNav = MessagingAccess.obtainMessageVector("simple_nav_output", 'simple_nav',
   'NavStateOut', 60*144*10, TotalSim.TotalSim, 'vehPosition', 'double', 0, 2, sim_model.logBuffer)
velNav = MessagingAccess.obtainMessageVector("simple_nav_output", 'simple_nav',
   'NavStateOut', 60*144*10, TotalSim.TotalSim, 'vehVelocity', 'double', 0, 2, sim_model.logBuffer)
attNav = MessagingAccess.obtainMessageVector("simple_nav_output", 'simple_nav',
   'NavStateOut', 60*144*10, TotalSim.TotalSim, 'vehSigma', 'double', 0, 2, sim_model.logBuffer)
rateNav = MessagingAccess.obtainMessageVector("simple_nav_output", 'simple_nav',
   'NavStateOut', 60*144*10, TotalSim.TotalSim, 'vehBodyRate', 'double', 0, 2, sim_model.logBuffer)
dvNav = MessagingAccess.obtainMessageVector("simple_nav_output", 'simple_nav',
   'NavStateOut', 60*144*10, TotalSim.TotalSim, 'vehAccumDV', 'double', 0, 2, sim_model.logBuffer)
sunNav = MessagingAccess.obtainMessageVector("simple_nav_output", 'simple_nav',
   'NavStateOut', 60*144*10, TotalSim.TotalSim, 'vehSunPntBdy', 'double', 0, 2, sim_model.logBuffer)


sunHatPred = numpy.array(sunPosition)-numpy.array(vehPosition)
listNorm(sunHatPred)

countAllow = posNav.shape[0] * 0.3*100

sigmaThreshold = 0.0
posDiffCount = 0
velDiffCount = 0
attDiffCount = 0
rateDiffCount = 0
dvDiffCount = 0
sunDiffCount = 0
i=0
while i< posNav.shape[0]:
   posVecDiff = posNav[i,1:] - vehPosition
   velVecDiff = velNav[i,1:] 
   attVecDiff = attNav[i,1:] 
   rateVecDiff = rateNav[i,1:] 
   dvVecDiff = dvNav[i,1:] 
   sunVecDiff = math.acos(numpy.dot(sunNav[i, 1:], sunHatPred))
   j=0
   while j<3:
      if(abs(posVecDiff[j]) > posBound[j] + posSigma*sigmaThreshold):
         posDiffCount += 1
      if(abs(velVecDiff[j]) > velBound[j] + velSigma*sigmaThreshold):
         velDiffCount += 1
      if(abs(attVecDiff[j]) > attBound[j] + attSigma*sigmaThreshold):
         attDiffCount += 1
      if(abs(rateVecDiff[j]) > rateBound[j] + rateSigma*sigmaThreshold):
         rateDiffCount += 1
      if(abs(dvVecDiff[j]) > dvBound[j] + dvSigma*sigmaThreshold):
         dvDiffCount += 1
      j+=1
   if(abs(sunVecDiff) > 4.0*math.sqrt(3.0)*sunBound[0] + 4.0*sunSigma*sigmaThreshold):
      sunDiffCount += 1
   i+= 1

errorCounts = [posDiffCount, velDiffCount, attDiffCount, rateDiffCount, 
   dvDiffCount, sunDiffCount]
i=0
for count in errorCounts:
   if count > countAllow:
      print "Too many error counts for element: "
      print i

#plt.figure(1)
#plt.plot(posNav[:,0]*1.0E-9, posNav[:,1], label='x-position')
#plt.plot(posNav[:,0]*1.0E-9, posNav[:,2], label='y-position' )
#plt.plot(posNav[:,0]*1.0E-9, posNav[:,3], label='z-position' )
#plt.legend()
#plt.xlabel('Time (s)')
#plt.ylabel('Position (m)')
#
#
#plt.figure(2)
#plt.plot(attNav[:,0], attNav[:,1] )
#plt.plot(attNav[:,0], attNav[:,2] )
#plt.plot(attNav[:,0], attNav[:,3] )

#plt.show()

PMatrixBad = [0.0]*12*12
stateBoundsBad = [0.0]*14
sNavObject.walkBounds = sim_model.DoubleVector(stateBoundsBad)
sNavObject.PMatrix = sim_model.DoubleVector(PMatrixBad)
sNavObject.inputStateName = "random_name"
sNavObject.inputSunName = "weirdly_not_the_sun"
TotalSim.InitializeSimulation()
TotalSim.ConfigureStopTime(int(1E8))
TotalSim.ExecuteSimulation()
