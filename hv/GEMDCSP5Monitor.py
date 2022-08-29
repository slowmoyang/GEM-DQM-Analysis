#!/usr/bin/env python

import cx_Oracle
import ROOT
import os
import time
from datetime import datetime
from datetime import timedelta
from operator import itemgetter
from array import array
import argparse
from argparse import RawTextHelpFormatter
from sys import exit
import getpass


"""
``GEMDCSP5Monitor.py`` --- Retrieve data for GEM detectors in P5 from database
============================================================================
Synopsis
--------
**GEMDCSP5Monitor.py** sta_period end_period monitorFlag sliceTestFlag

Twiki
-------------
TO BE DONE

Environment
--------------
This code runs on the 904DAQ machine

First of all you have to enter in your lxplus area and then connect to the 904DAQ machine

Now you have to ensure that in your area you have set two variables for access
GEM_P5_DB_NAME_OFFLINE_MONITOR and GEM_P5_DB_ACCOUNT_OFFLINE_MONITOR which contain the credentials to access to CMS P5 database

Description
-----------
This code retrieves Vmon, Imon, Status, Ison and Temperature informations for HV or LV for GEM detectors in P5
Data are taken from CMS database

To execute this code you have first to put in the one file the alias of chambers you want to look:
File to modify:
   In case you want data for the present situation in P5
      HV data --> file to modifiy: P5GEMChosenChambers_HV.txt
      LV data --> file to modifiy: P5GEMChosenChambers_LV.txt
   In case you want data for the slice test period
      HV data --> file to modifiy: P5GEMChosenChambers_sliceTest_HV.txt
      LV data --> file to modifiy: P5GEMChosenChambers_sliceTest_LV.txt

Mandatory arguments
-------------------
The following list shows the mandatory inputs that must be supplied to execute
the script.
.. program:: GEMDCSP5Monitor.py
.. option:: [*sta_period*]
.. option:: [*end_period*]
.. option:: [*monitorFlag*]
.. option:: [*sliceTestFlag*]

   sta_period, end_period, monitorFlag and sliceTestFlag must always be passed
   sta_period is the UTC Start Date of the monitor: has to be inserted in format YYYY-MM-DD HH24:mm:ss (e.g. 2018-04-01_15:22:31)
   end_period is the UTC  End  Date of the monitor: has to be inserted in format YYYY-MM-DD HH24:mm:ss (e.g. 2018-04-02_15:22:31)
   monitorFlag tell if data must be read for HV or LV (monitorFlag accepts only 'HV' or 'LV' string) (e.g. HV)
   sliceTestFlag tells if data must be taken from slice test period or not
   (sliceTestFlag = 0 : I use data for current situation in P5, sliceTestFlag = 1 : I use data collected during the slice test) (e.g. 0)

Example
------------------
python GEMDCSP5Monitor.py 2018-04-01_15:22:31 2018-04-02_15:22:31 HV 1

"""
descrString = "Twiki\n------------------------\nTO BE DONE"
descrString = descrString + "\n\nEnvironment\n------------------------\nThis code runs on the 904DAQ machine\n"
descrString = descrString + "\nFirst of all you have to enter in your lxplus area and then connect to the 904DAQ machine"
descrString = descrString + "\nNow you have to ensure that in your area you have set two variables for access"
descrString = descrString + "\nGEM_P5_DB_NAME_OFFLINE_MONITOR and GEM_P5_DB_ACCOUNT_OFFLINE_MONITOR which contain the credentials to access to CMS P5 database"
descrString = descrString + "\n\nDescription\n------------------------\nRetrieve from the database the vmon, imon, status, isON and temperature informations\n"
descrString = descrString + "To run this code you first have to put in one file the alias of chambers you want"
descrString = descrString + "\n   In case you want data for the present situation in P5"
descrString = descrString + "\n      HV data --> file to modifiy: P5GEMChosenChambers_HV.txt"
descrString = descrString + "\n      LV data --> file to modifiy: P5GEMChosenChambers_LV.txt"
descrString = descrString + "\n   In case you want data for the slice test period"
descrString = descrString + "\n      HV data --> file to modifiy: P5GEMChosenChambers_sliceTest_HV.txt"
descrString = descrString + "\n      LV data --> file to modifiy: P5GEMChosenChambers_sliceTest_LV.txt"
descrString = descrString + "\n\nExample\n------------------------"
descrString = descrString + "\npython GEMDCSP5Monitor.py sta_period end_period monitorFlag sliceTestFlag"
descrString = descrString + "\npython GEMDCSP5Monitor.py 2018-04-01_15:22:31 2018-04-02_15:22:31 HV 1"

#argparse
parser = argparse.ArgumentParser(description=descrString, formatter_class=RawTextHelpFormatter)

parser.add_argument("sta_period", type=str,
       help="UTC Start Date of the monitor, has to be inserted in format YYYY-MM-DD HH24:mm:ss (e.g. 2018-04-01_15:22:31)",
       metavar="sta_period")
parser.add_argument("end_period", type=str,
       help="UTC End Date of the monitor, has to be inserted in format YYYY-MM-DD HH24:mm:ss (e.g. 2018-04-02_15:22:31)",
       metavar="end_period")
parser.add_argument("monitorFlag", type=str,
       help="monitorFlag tell if data must be read for HV or LV (monitorFlag accepts only 'HV' or 'LV' string)",
       metavar="monitorFlag")
parser.add_argument("sliceTestFlag", type=int,
       help="sliceTestFlag tells if data must be taken from slice test period or not \n(sliceTestFlag = 0 : I use data for current situation in P5, sliceTestFlag = 1 : I use data collected during the slice test)",
       metavar="sliceTestFlag")
parser.add_argument("--chamberList", "-c", type=str,
       help="custom list of Chosen Chambers. If not set, default files will be used. If set to 'all', all existing chambers will be used.)",
       metavar="chamberList")
parser.add_argument("--verbose", "--v", help="Enables print outputs.")
parser.add_argument("--save", "--s", help="Save .png plots.")

args = parser.parse_args()

ROOT.gROOT.SetBatch(True)

#set verbosity settings
if args.verbose:
    def verboseprint(*args):
        # Print each argument separately so caller doesn't need to
        # stuff everything to be printed into a single string
        for arg in args:
           print(arg, end=' ')
        print()
else:
    verboseprint = lambda *a: None      # do-nothing function

dbName = os.getenv("GEM_P5_DB_NAME_OFFLINE_MONITOR") or getpass.getpass(prompt='GEM P5 DB Name: ')
dbAccount = os.getenv("GEM_P5_DB_ACCOUNT_OFFLINE_MONITOR") or getpass.getpass(prompt='GEM P5 DB Account')


def main():
   #Reminder: in the DB the DeltaV between pins are saved, not the V from ground
   #-------------KIND OF MONITOR FLAG----------------------------------------
   #monitorFlag = "HV"
   #monitorFlag = "LV"
   monitorFlag = args.monitorFlag

   #-------------DEVELOPER SLICE TEST FLAG------------------------------------
   #sliceTestFlag = 1 #1 uses the slice test mapping properties
   #sliceTestFlag = 0 #0 for real P5 conditions
   sliceTestFlag = args.sliceTestFlag

   #-------------FILE WITH CHOSEN CHAMBERS------------------------------------
   dir_path = os.path.dirname(os.path.realpath(__file__))
   if (args.chamberList is not None) and (args.chamberList != "all"):
       chambersFileName == args.chamberList
   elif args.chamberList == "all":
       if sliceTestFlag == 0:
          chambersFileName = "P5GEMExistingChambers.txt"
       if sliceTestFlag == 1:
          if monitorFlag == "HV":
             chambersFileName = "P5GEMExistingChambers_sliceTest_HV.txt"
          if monitorFlag == "LV":
             chambersFileName = "P5GEMExistingChambers_sliceTest_LV.txt"
   elif monitorFlag == "HV":
      if sliceTestFlag == 0:
         chambersFileName = "P5GEMChosenChambers_HV.txt"
      if sliceTestFlag == 1:
         chambersFileName = "P5GEMChosenChambers_sliceTest_HV.txt"

   elif monitorFlag == "LV":
      if sliceTestFlag == 0:
         chambersFileName = "P5GEMChosenChambers_LV.txt"
      if sliceTestFlag == 1:
         chambersFileName = "P5GEMChosenChambers_sliceTest_LV.txt"
   chambersFileName=dir_path+"/"+chambersFileName
   #-------------FILE WITH EXISTING CHAMBERS-----------------------------------
   if sliceTestFlag == 0:
      existingChambersFileName = "P5GEMExistingChambers.txt"
   if sliceTestFlag == 1:
      if monitorFlag == "HV":
         existingChambersFileName = "P5GEMExistingChambers_sliceTest_HV.txt"
      if monitorFlag == "LV":
         existingChambersFileName = "P5GEMExistingChambers_sliceTest_LV.txt"
   existingChambersFileName=dir_path+"/"+existingChambersFileName

   #-------------FILE WITH MAPPING---------------------------------------------
   if monitorFlag == "HV":
      if sliceTestFlag == 0:
         mappingFileName = "GEMP5MappingHV.txt"
      if sliceTestFlag == 1:
         mappingFileName = "GEMP5MappingHV_sliceTest.txt"

   if monitorFlag == "LV":
      if sliceTestFlag == 0:
         mappingFileName = "GEMP5MappingLV.txt"
      if sliceTestFlag == 1:
         mappingFileName = "GEMP5MappingLV_sliceTest.txt"
   mappingFileName=dir_path+"/"+mappingFileName

   #-------------PREPARE START AND END DATE------------------------------------
   #sta_period = raw_input("Insert UTC start time in format YYYY-MM-DD HH:mm:ss\n")
   #type(sta_period)
   #end_period = raw_input("Insert UTC end time in format YYYY-MM-DD HH:mm:ss\n")
   #type(end_period)

   sta_period = args.sta_period
   end_period = args.end_period

   sta_period.replace("_", " ")
   end_period.replace("_", " ")

   start=sta_period.replace(" ", "_")
   end=end_period.replace(" ", "_")
   start=start.replace(":", "-")
   end=end.replace(":", "-")

   #add ' at beginning and end to have the date in the format for the query
   sta_period = "'" + sta_period + "'"
   end_period = "'" + end_period + "'"

   startDate = datetime(int(start[:4]), int(start[5:7]), int(start[8:10]), int(start[11:13]), int(start[14:16]), int(start[17:]) )
   endDate   = datetime(int(end[:4]), int(end[5:7]), int(end[8:10]), int(end[11:13]), int(end[14:16]), int(end[17:]) )

   #-------------OUTPUT ROOT FILE------------------------------------------------
   if not os.path.exists(dir_path+"/OutputFiles"):
       os.makedirs(dir_path+"/OutputFiles")
   dirStringSave = dir_path+"/OutputFiles/P5_GEM_"+monitorFlag+"_monitor_UTC_start_"+start+"_end_"+end+"/"

   fileName = dir_path+"/OutputFiles/P5_GEM_"+monitorFlag+"_monitor_UTC_start_"+start+"_end_"+end+".root"
   f1=ROOT.TFile(fileName,"RECREATE")

   #-------------DATES OF MAPPING CHANGE-----------------------------------------
   mappingChangeDate = []
   if sliceTestFlag == 1:
      if monitorFlag == "HV":
         firstMappingChange = datetime( 2017, 0o3, 18, 11, 54, 0o1 ) #trial date for SliceTestMapping
         secondMappingChange = datetime( 2018, 0o3, 0o5, 0o4, 0o7, 16 ) #trial date for SliceTestMapping

         mappingChangeDate.append( firstMappingChange )
         mappingChangeDate.append( secondMappingChange )
      if monitorFlag == "LV":
         firstMappingChange = datetime( 2017, 0o2, 15, 00, 00, 0o1 ) #trial date for SliceTestMapping
         secondMappingChange = datetime( 2017, 0o6, 9, 16, 17, 0o4 ) #trial date for SliceTestMapping

         mappingChangeDate.append( firstMappingChange )
         mappingChangeDate.append( secondMappingChange )

   if sliceTestFlag == 0:
      if monitorFlag == "HV":
         firstMappingChange = datetime( 2019, 10, 0o1, 00, 00, 0o1 )
         #secondMappingChange = datetime( 2020, 01, 27, 11, 30, 01 )#time always in UTC

         mappingChangeDate.append(firstMappingChange)
         #mappingChangeDate.append(secondMappingChange)
      if monitorFlag == "LV":
         firstMappingChange = datetime( 2019, 10, 0o1, 00, 00, 0o1 )

         mappingChangeDate.append(firstMappingChange)

   lastDate = datetime( 2050, 0o1, 0o1, 00, 00, 0o1)
   mappingChangeDate.append( lastDate )

   #divide the monitor period in a number of periods equal to the number of mappings used
   periodBool = []
   numberOfMaps = len(mappingChangeDate)-1

   #fill periodBool with 0 to say that the map is not used, chnage than to one if used
   for mapIdx in range(numberOfMaps):
      periodBool.append(0)

   startIdx = -1
   endIdx   = -1

   #errors declaration
   if (startDate < mappingChangeDate[0] or endDate < mappingChangeDate[0]) :
      LowDateError = "ERROR: Date too early!! Dates must be greater than "+ str(mappingChangeDate[0])
      exit( LowDateError )
   if (startDate > endDate):
      SwapDateError = "ERROR: Start date greater than end date!!"
      exit( SwapDateError )

   #find the index for mapping start and end
   startIdx = -1
   endIdx = -1
   for dateIdx in range(len(mappingChangeDate)-1):
      if ( startDate > mappingChangeDate[dateIdx] and startDate <= mappingChangeDate[dateIdx+1] ):
         periodBool[dateIdx] = 1
         startIdx = dateIdx
      if ( endDate > mappingChangeDate[dateIdx] and endDate <= mappingChangeDate[dateIdx+1] ):
         periodBool[dateIdx] = 1
         endIdx = dateIdx

   #fill with one all the periods between start and end date
   if ( startIdx != endIdx and (endIdx-startIdx)>1 ):
      for fillPeriodIdx in range(endIdx-startIdx-1):
         periodBool[startIdx+1+fillPeriodIdx] = 1

   verboseprint ( periodBool )

   #----------MAPPING LENGTH---------------------------------------------------
   #if mapping is HV is 504 lies long, if LV is 144 lines long
   findMap = 0
   if (mappingFileName.find("HV") != -1):
      verboseprint("You are using a HV map")
      findMap=1
      mappingLength = 504
      if sliceTestFlag == 1:
         mappingLength = 14
   if (mappingFileName.find("LV") != -1):
      verboseprint("You are using a LV map")
      findMap=-1
      mappingLength = 144
      if sliceTestFlag == 1:
         mappingLength = 12

   #-----------READ THE FILE WITH EXISTING CHAMBERS NAMES-----------------------
   #in the string in ExistingChambers file are contained all the names that a chmaber can have in different mappings
   #example: if a chamber is called in first map with alias SC27 and then as GEMINI27, in file existsing chmabers
   # is indicated with SC27:GEMINI27
   ExistingChambers = []
   nExistingChambers = sum(1 for line in open(existingChambersFileName))
   verboseprint ("In "+ existingChambersFileName + " you have "+str(nExistingChambers)+" chambers")

   fileExChambers = open(existingChambersFileName, "r")
   fileExChambersLine = fileExChambers.readlines()

   for exChamber in range(int(nExistingChambers)):
      exChamberName = str(fileExChambersLine[exChamber])[:-1]
      ShortAliasOneChamber = exChamberName.split(":")
      ExistingChambers.append( ShortAliasOneChamber )

   verboseprint( "ExistingChambers:", ExistingChambers )

   #------------READ THE FILE WITH CHOSEN CHAMBERS-------------------------------
   #name of chambers are take in input from the chambersFileName
   #count the number of chambers in the chambersFileName
   howManyChambers = sum(1 for line in open(chambersFileName))
   verboseprint ("In "+ chambersFileName + " you have "+str(howManyChambers)+" chambers")

   fileChambers = open(chambersFileName, "r")
   fileChambersLine = fileChambers.readlines()

   chamberList = []
   #in chamberList I can use only one name for one chamber
   #I have to check that the name exists in existing chambers file

   for chIdx in range(int(howManyChambers)):
      chamberName = str(fileChambersLine[chIdx])[:-1]
      #print chamberName
      #check that the name of the chamber is one of the existing
      ExistBool = False
      for existIdx in range(len(ExistingChambers)):
         for existSplitIdx in range(len(ExistingChambers[existIdx])):
            alterName = ExistingChambers[existIdx][existSplitIdx]
            if chamberName == alterName:
               ExistBool = True
      if ExistBool == False:
         print(("ERROR: WRONG NAME OF THE CHAMBER: the accepted names are in File: " + existingChambersFileName))
         return 1
      chamberList.append( chamberName )

   verboseprint ( chamberList )

   #------------READ THE MAPPING FILE--------------------------------------------
   fileMapping = open(mappingFileName, "r")
   fileMappingLine = fileMapping.readlines()

   #lines with start of mapping
   startMappingLines=[]

   #mapping booleans with same lenght as periodBool
   boolMapping = []

   for i in range(len(periodBool)):
     boolMapping.append(False)

   lineCounter = 0
   for x in fileMappingLine:
      #find the : index
      columnIdx = x.index(":")
      #make a loop on every mapping
      for mapIdx in range(len(boolMapping)):
         if str(x)[:columnIdx] == ("Mapping"+str(mapIdx+1)): #the first map is Mapping1, notMapping0
            boolMapping[mapIdx] = True
            startMappingLines.append( int(fileMappingLine.index(x)) )
      lineCounter = lineCounter + 1

   #if the boolMapping is full of True means that all the maps have been inserted in the map file
   allCorrectMapFlag = True
   for mapIdx in range(len(boolMapping)):
      if boolMapping[mapIdx] == False:
         allCorrectMapFlag = False
         print(( "ERROR: Map "+str(mapIdx+1)+" not charged correctely" ))
         return 1

   if allCorrectMapFlag == True:
      for mapIdx in range(len(boolMapping)):
         boolMapping[mapIdx] = bool(periodBool[mapIdx])

   #check that the periodBool is the same of boolMapping
   if boolMapping != periodBool:
      print("ERROR: boolMapping != periodBool")
      return 1

   #----------FRONT MAPPING STRING----------------------------------------------
   column1 = fileMappingLine[0].index(":")
   subString1 = fileMappingLine[0][column1+1:]
   column2 = subString1.index(":")
   stringFrontDP = subString1[column2+2:-2]

   #------------CHARGE THE MAPPING-----------------------------------------------
   #store the mapping each in a dedicated vector
   allMappingList=[]
   for idxMap in range(len(boolMapping)):
      #recognise where a map starts
      oneMap = []
      for lineIdx in range(startMappingLines[idxMap]+1, startMappingLines[idxMap]+1+mappingLength):
         oneMap.append( stringFrontDP + fileMappingLine[lineIdx][:-1] )
      allMappingList.append(oneMap)

   #verboseprint ( "allMappingList", allMappingList )

   #------------DATABASE CONNECT------------------------------------------------
   db = cx_Oracle.connect( dbAccount+dbName )
   cur = db.cursor()

   #-------------CHOOSE THE NEEDED MAPPING LINES FOR EACH REQUESTED CHAMBER----
   AllChosenChamberAllDPsWanted = []
   #charge a DP only if the mapBoolean corresponding is True
   for chIdx in range(len(chamberList)): #loop on chosen chambers (name of chamber as that in the ChosenChambers file)
      OneChamberAllDPs = []
      for allMapIdx in range(len(allMappingList)): #loop on all maps
         OneMapAllDPs = []
         for oneMapIdx in range(len(allMappingList[allMapIdx])): #loop on One Map
            #take one line of the mapping
            oneMapLine = allMappingList[allMapIdx][oneMapIdx]
            #now I have to look for a specific channel
            if monitorFlag == "HV":
               if sliceTestFlag == 0:
                  channelNameAsInMap = ["G3Bot", "G3Top", "G2Bot", "G2Top", "G1Bot", "G1Top", "Drift"] #part of alias in map that can be used to identify the channel
               if sliceTestFlag == 1:
                  channelNameAsInMap = ["G3bot", "G3top", "G2bot", "G2top", "G1bot", "G1top", "Drift"]
            if monitorFlag == "LV":
               if sliceTestFlag == 0:
                  channelNameAsInMap = ["L1", "L2"]
               if sliceTestFlag == 1:
                  if allMapIdx == 0:
                     channelNameAsInMap = ["TOP_VFAT", "TOP_OH2V", "TOP_OH4V", "BOT_VFAT", "BOT_OH2V", "BOT_OH4V"]
                  if allMapIdx == 1:
                     channelNameAsInMap = ["L1_VFAT", "L1_OH2V", "L1_OH4V", "L2_VFAT", "L2_OH2V", "L2_OH4V"]

            #now that there are channelName I look for a specific channel
            for channelNameIdx in range(len(channelNameAsInMap)):
               if (oneMapLine.find(channelNameAsInMap[channelNameIdx]) != -1):
                  #the order of chambers in Existing chambers can be different from that in chamberList
                  chamberMatch = False
                  for existChamberIdx in range(len(ExistingChambers)):
                     listAlterNamesOneChamber = ExistingChambers[existChamberIdx]
                     for alterNamesIdx in range(len(listAlterNamesOneChamber)):
                        if chamberList[chIdx] == listAlterNamesOneChamber[alterNamesIdx]:
                           chamberMatch = True
                           indexInExistingChambers = existChamberIdx
                  #now I know that the chamber I am looking to is the right one
                  #I look for a match between names of the chamber I am looking to and the line of the mapping
                  for alterNameThisChamberIdx in range(len(ExistingChambers[indexInExistingChambers])):
                     alterName = ExistingChambers[indexInExistingChambers][alterNameThisChamberIdx]
                     if (oneMapLine.find( alterName ) != -1 ):
                        #save this DP (for this map) for this channel
                        column2Idx = oneMapLine.index(":",15)
                        OneChannelOneDP = oneMapLine[:column2Idx]
                        OneChannelMapAlias = oneMapLine[column2Idx+1:]
                        OneChannelOneShortAlias = alterName
                        verboseprint( "PairDPAlias", OneChannelOneDP, OneChannelOneShortAlias )

                        #I have to look in the DB which is the SINCE associated to this ALIAS and DPE_NAME in table CMS_GEM_PVSS_COND.ALIASES
                        #REMEMBER: there is a dot at the end of DPE_NAME in ALIASES table
                        query = "select SINCE, DPE_NAME, ALIAS from CMS_GEM_PVSS_COND.ALIASES where DPE_NAME='"+str(OneChannelOneDP)+".' and ALIAS='"+str(OneChannelMapAlias)+"'"
                        cur.execute(query)
                        curALIAS = cur
                        boolNoSinceSeen = True
                        for result in curALIAS:
                           boolNoSinceSeen = False
                           OneChannelOneSince = result[0]
                        #in case there is nothing in curAlias
                        if boolNoSinceSeen:
                           OneChannelOneSince = datetime( 1970, 0o1, 0o1, 00, 00, 0o1 ) #date used for since if there is nothing
                           #if I have more than one map I add one second to the dummyDate
                           #if ( allMapIdx > 0 ):
                           #   secondsToAdd = allMapIdx + 1
                           #   OneChannelOneSince = datetime( 1970, 01, 01, 00, 00, secondsToAdd ) #date used for since if there is nothing

                        DPAliasSinceOneChannel = []
                        DPAliasSinceOneChannel.append(OneChannelOneDP)
                        DPAliasSinceOneChannel.append(OneChannelOneShortAlias)
                        DPAliasSinceOneChannel.append(OneChannelOneSince)

                        OneMapAllDPs.append(DPAliasSinceOneChannel)
                        #verboseprint("OneMapAllDPs", OneMapAllDPs)
         OneChamberAllDPs.append(OneMapAllDPs)
         #verboseprint("OneChamberAllDPs", OneChamberAllDPs)
      #now OneChamberAllDPs is ready. I have to reorder the elements since I need a product given by a channel loop and then a map loop
      #instead I have a map loop and then a channel loop
      #I'd need this
      #[chamber]
      #[[channel1][channel2]]
      #[[[map1],[map2]][[map1],[map2]]]
      #[[[DP, SHORTALIAS, SINCE],[DP, SHORTALIAS, SINCE]][[DP, SHORTALIAS, SINCE],[DP, SHORTALIAS, SINCE]]]
      #[[[1],[2]][[3],[4]]]

      #INSTEAD I HAVE
      #[[[1],[3]][[2],[4]]]

      #verboseprint("OneChamberAllDPs", OneChamberAllDPs)

      #REORDER
      #verboseprint ("OneChamberAllDPs[0]", OneChamberAllDPs[0])
      #verboseprint ("OneChamberAllDPs[0]", type(OneChamberAllDPs[0]))
      #verboseprint ("OneChamberAllDPs[0]", len(OneChamberAllDPs[0]))
      howManyChannelsInAMap = len(OneChamberAllDPs[0]) #number of channels seen in a map for this chamber
      OneChamberAllDPsWanted = []
      for channelIdx in range(howManyChannelsInAMap):
         fixedChannelList = []
         for mapIdx in range(len(OneChamberAllDPs)):
            takenTriplet = OneChamberAllDPs[mapIdx][channelIdx]
            fixedChannelList.append(takenTriplet)
         OneChamberAllDPsWanted.append(fixedChannelList)

      #verboseprint("OneChamberAllDPsWanted", OneChamberAllDPsWanted)

      #sort in case SINCE are stored not in the cronological order
      for channelIdx in range(len(OneChamberAllDPsWanted)):
         OneChannelAllMapsList = OneChamberAllDPsWanted[channelIdx]
         OneChannelAllMapsListSorted = sorted(OneChannelAllMapsList, key=lambda element: element[2]) #element[2] is SINCE
         OneChamberAllDPsWanted[channelIdx] = OneChannelAllMapsListSorted
      #verboseprint("OneChamberAllDPsWanted", OneChamberAllDPsWanted)

   #------------SEE WHICH SINCE ARE TO USE-----------------------------------------------------------------------------
   #table CMS_GEM_PVSS_COND.ALIASES contains SINCE, DPE_NAME, ALIAS
   #table CMS_GEM_PVSS_COND.DP_NAME2ID contains DPNAME and ID
   #for a data point there could be different IDs associated, depending on their
   #validity period

   #select only the necessary IDs depending on sta_period and end_period
   #add a true or a False to OneChamberAllDPsWanted triplet to say if this since has to be used or not
   #[[[DP, ALIASSHORT, SINCE],[DP, ALIASSHORT, SINCE]],[[DP, ALIASSHORT, SINCE],[DP, ALIASSHORT, SINCE]]]
   #[[    MAP 1              ,     MAP2              ],[    MAP1               ,      MAP2             ]]
   #[                CHANNEL 1                        ,                 CHANNEL 2                       ]
   #                                              CHAMBER

      for channelIdx in range(len(OneChamberAllDPsWanted)):
         listOfDates = []
         for mapIdx in range(len(OneChamberAllDPsWanted[channelIdx])):
            usedMap = False
            sinceMap = OneChamberAllDPsWanted[channelIdx][mapIdx][2]
            verboseprint ( "sinceMap", sinceMap )
            pairDateFalse = []
            pairDateFalse.append(sinceMap)
            pairDateFalse.append(False)
            listOfDates.append( pairDateFalse )
         #appendAlso the start and end date
         startPair = [startDate, True]
         endPair = [endDate, True]
         listOfDates.append( startPair )
         listOfDates.append( endPair   )

         sortDates = sorted(listOfDates, key=lambda element: element[0]) #sortDate is made by lists [SINCE, trueorfalse]
         #mark the since to use
         startIdx = sortDates.index( startPair )
         endIdx   = sortDates.index( endPair   )
         if startIdx == 0:
            verboseprint( "start is before the first since")
         if (startIdx == 0 and endIdx == 1):
            verboseprint("both start and end are before the first since: no data expected")

         #mark since to use
         #first since if start is before start
         if startIdx != 0:
            sortDates[startIdx-1][1] = True
         for sortIdx in range(len(sortDates)):
            if (sortIdx > startIdx and sortIdx < endIdx):
               sortDates[sortIdx][1] = True

         verboseprint("sortDates", sortDates)
         verboseprint("OneChamberAllDPsWanted", OneChamberAllDPsWanted[channelIdx][mapIdx])

         #add the true or false to the OneChamberAllDPsWanted list
         for mapIdx in range(len(OneChamberAllDPsWanted[channelIdx])):
            sinceDate = OneChamberAllDPsWanted[channelIdx][mapIdx][2]
            threeElements = OneChamberAllDPsWanted[channelIdx][mapIdx]
            for sortIdx in range(len(sortDates)):
               #if the dates in two lists are the same I add the boolean
               if sortDates[sortIdx][0] == OneChamberAllDPsWanted[channelIdx][mapIdx][2]:
                  verboseprint ( "sortDate: ", sortDates[sortIdx][1] )
                  threeElements.append(sortDates[sortIdx][1]) #the boolean is in position 1
                  OneChamberAllDPsWanted[channelIdx][mapIdx] = threeElements

      verboseprint("OneChamberAllDPsWanted with true or false", OneChamberAllDPsWanted)

      #--------------------------FIND IDs------------------------------------------------------------------------
      #DPE_NAME has a dot at the end of channellXXX, DPNAME has not a dot

      verboseprint("-------------------------------------------------------------------------------------------------------------------------")
      verboseprint("                    "+chamberList[chIdx]+" :CALLED DPs AND THEIR IDs")
      for channelIdx in range(len(OneChamberAllDPsWanted)):
         oneChannelIDs=[]
         for mapIdx in range(len(OneChamberAllDPsWanted[channelIdx])):
            thisMapDP = OneChamberAllDPsWanted[channelIdx][mapIdx][0]
            thisMapAlias = OneChamberAllDPsWanted[channelIdx][mapIdx][1]
            query = "select ID, DPNAME from CMS_GEM_PVSS_COND.DP_NAME2ID where DPNAME='"+thisMapDP+"'"
            cur.execute(query)
            curID = cur
            for result in curID:
               dpID   = result[0]
               dpNAME = result[1]

            verboseprint( "chamber:", chamberList[chIdx], "channel", channelNameAsInMap[channelIdx], "ID", dpID, "DPNAME", dpNAME, "ALIAS", thisMapAlias )
            #add to the four elements of OneChamberAllDPsWanted[channelIdx][mapIdx] also the ID
            fourElements = OneChamberAllDPsWanted[channelIdx][mapIdx]
            fourElements.append( dpID )
            OneChamberAllDPsWanted[channelIdx][mapIdx] = fourElements
            #now OneChamberAllDPsWanted[channelIdx][mapIdx] is made by a list
            #[DP, ALIASSHORT, SINCE, BOOL for the since to use, DPID]

      verboseprint("OneChamberAllDPsWanted with also IDs", OneChamberAllDPsWanted)

      AllChosenChamberAllDPsWanted.append(OneChamberAllDPsWanted)

   #OUT OF CHAMBER LOOP
   #verboseprint("AllChosenChamberAllDPsWanted", AllChosenChamberAllDPsWanted)

   #--------------RETRIEVE DATA FOR HV--------------------------------------------
   #table CMS_GEM_PVSS_COND.FWCAENCHANNELA1515 for HV
   #table CMS_GEM_PVSS_COND.FWCAENCHANNEL for LV

   #for each chamber I retrive data and then if one is NULL I don't save it
   #HV TABLE
   #describe CMS_GEM_PVSS_COND.FWCAENCHANNELA1515;
   # Name					   Null?    Type
   # ----------------------------------------- -------- ----------------------------
   #UPDATEID				   NOT NULL NUMBER(38)
   #DPID					    NUMBER
   #CHANGE_DATE					    TIMESTAMP(9)
   #DPE_STATUS					    NUMBER
   #DPE_POSITION				    NUMBER
   #ACTUAL_IMONREAL				    NUMBER
   #ACTUAL_IMON					    NUMBER
   #ACTUAL_VMON					    NUMBER
   #ACTUAL_STATUS				    NUMBER
   #ACTUAL_ISON					    NUMBER
   #ACTUAL_TEMP					    NUMBER
   #ACTUAL_IMONDET 				    NUMBER
   #SETTINGS_OFFORDER				    NUMBER
   #SETTINGS_ONORDER				    NUMBER

   #LV TABLE
   #SQL> describe CMS_GEM_PVSS_COND.FWCAENCHANNEL;
   #Name					   Null?    Type
   #----------------------------------------- -------- ----------------------------
   #UPDATEID				   NOT NULL NUMBER(38)
   #DPID					    NUMBER
   #CHANGE_DATE					    TIMESTAMP(9)
   #DPE_STATUS					    NUMBER
   #DPE_POSITION				    NUMBER
   #ACTUAL_VMON					    NUMBER
   #ACTUAL_ISON					    NUMBER
   #ACTUAL_IMON					    NUMBER
   #ACTUAL_OVC					    NUMBER
   #ACTUAL_TRIP					    NUMBER
   #ACTUAL_STATUS				    NUMBER
   #ACTUAL_TEMP					    NUMBER
   #ACTUAL_VCON					    NUMBER
   #ACTUAL_TEMPERATUREERROR			    NUMBER
   #ACTUAL_POWERFAIL				    NUMBER

   if monitorFlag == "HV":
      tableData = "CMS_GEM_PVSS_COND.FWCAENCHANNELA1515"
   if monitorFlag == "LV":
      tableData = "CMS_GEM_PVSS_COND.FWCAENCHANNEL"

   stringWhatRetriveList     = ["imon", "vmon", "smon", "ison", "temp"]
   for chIdx in range(len(chamberList)):
      #create the first level of directories: one for each chamber
      chamberNameRootFile = chamberList[chIdx].replace("-", "_M")
      chamberNameRootFile = chamberNameRootFile.replace("+", "_P")
      chamberNameRootFile = chamberNameRootFile.replace("/", "_")
      firstDir = f1.mkdir(chamberNameRootFile)
      firstDir.cd()

      #put a counter to identify which channel I am looking to
      #IF I CALL A CHAMBER I AM OBLIGED TO LOOK ALL THE SEVEN CHANNELS
      if monitorFlag == "HV":
         if sliceTestFlag == 0:
            channelName = ["G3Bot", "G3Top", "G2Bot", "G2Top", "G1Bot", "G1Top", "Drift"]
         if sliceTestFlag == 1:
            channelName = ["G3Bot", "G3Top", "G2Bot", "G2Top", "G1Bot", "G1Top", "Drift"]
      if monitorFlag == "LV":
         if sliceTestFlag == 0:
            channelName = ["L1", "L2"]
         if sliceTestFlag == 1:
            channelName = ["L1_VFAT", "L1_OH2V", "L1_OH4V", "L2_VFAT", "L2_OH2V", "L2_OH4V"]

      #declare one multigraph with all channel
      Imontmultig1 = ROOT.TMultiGraph()
      titleMultig1 = chamberList[chIdx] + "; ;Imon (#mu A)"
      if monitorFlag == "LV":
         titleMultig1 = chamberList[chIdx] + "; ;Imon (A)"
      Imontmultig1.SetName( chamberList[chIdx]+"_Imon_AllChannels" )
      Imontmultig1.SetTitle( titleMultig1 )
      minDateImonMultig = 9999999
      maxDateImonMultig = 1
      minValImonMultig = 999999
      maxValImonMultig = -999999

      Vmontmultig1 = ROOT.TMultiGraph()
      titleMultig1 = chamberList[chIdx] + "; ;#Delta Vmon (V)"
      Vmontmultig1.SetName( chamberList[chIdx]+"_Vmon_AllChannels" )
      Vmontmultig1.SetTitle( titleMultig1 )
      minDateVmonMultig = 999999
      maxDateVmonMultig = 1
      minValVmonMultig = 999999
      maxValVmonMultig = -999999

      Smontmultig1 = ROOT.TMultiGraph()
      titleMultig1 = chamberList[chIdx] + "; ;Status code"
      Smontmultig1.SetName( chamberList[chIdx]+"_Smon_AllChannels" )
      Smontmultig1.SetTitle( titleMultig1 )
      minDateSmonMultig = 999999
      maxDateSmonMultig = 1
      minValSmonMultig = 999999
      maxValSmonMultig = -999999

      Isontmultig1 = ROOT.TMultiGraph()
      titleMultig1 = chamberList[chIdx] + "; ;IsOn code (0=OFF, 1=ON)"
      Isontmultig1.SetName( chamberList[chIdx]+"_Ison_AllChannels" )
      Isontmultig1.SetTitle( titleMultig1 )
      minDateIsonMultig = 999999
      maxDateIsonMultig = 1
      minValIsonMultig = 999999
      maxValIsonMultig = -999999

      Temptmultig1 = ROOT.TMultiGraph()
      titleMultig1 = chamberList[chIdx] + "; ;Temperature (Celsius degrees)"
      Temptmultig1.SetName( chamberList[chIdx]+"_Temp_AllChannels" )
      Temptmultig1.SetTitle( titleMultig1 )
      minDateTempMultig = 999999
      maxDateTempMultig = 1
      minValTempMultig = 999999
      maxValTempMultig = -999999

      #Declare one Legend for the multigraphs
      legendMultiImon = ROOT.TLegend(0.55,0.20,0.88,0.382)
      legendMultiImon.SetTextSize(0.025);
      legendMultiImon.SetTextFont(42);

      legendMultiVmon = ROOT.TLegend(0.55,0.665,0.88,0.88)
      legendMultiVmon.SetTextSize(0.025);
      legendMultiVmon.SetTextFont(42);

      for channelIdx in range(len(AllChosenChamberAllDPsWanted[chIdx])):
         OneChannelInfo = AllChosenChamberAllDPsWanted[chIdx][channelIdx]
         imonData = [] #store two Dates and Imon in pair (0th Date in millisecond from the first element stored, 1st Date as wanted by root, 2nd Imon)
         vmonData = [] #store two Dates and Vmon in pair
         smonData = [] #store two Dates and Status in pair
         isonData = [] #store two Dates and Ison in pair
         tempData = [] #store two Dates and Temp in pair

         #look how many SINCE I have in this channel
         howManySince = len(OneChannelInfo)

         contData = 0
         #for each chnnel of a chamber there are more than one ID
         for mapIdx in range(len( OneChannelInfo )):
            sinceThisMap = OneChannelInfo[mapIdx][2]
            aliasThisMap = OneChannelInfo[mapIdx][1]
            #look which is the first date to call and which is the last date to call, not to call two times a selection on date
            firstDateToCall = startDate
            if sinceThisMap > startDate:
               if OneChannelInfo[mapIdx][3]: #check that the SINCE is marked with True to use it
                  firstDateToCall = str(sinceThisMap)
                  #if I have taken a date from the SINCE, this is not in format YYYY-MM-DD HH24:MI:SS
                  #remove from the date string the part of milliseconds
                  #find the last column :
                  firstDateToCall_lastColumnIdx = firstDateToCall.rfind(":")
                  firstDateToCall = firstDateToCall[:firstDateToCall_lastColumnIdx+3]

            lastDateToCall = endDate
            if mapIdx != (len( OneChannelInfo )-1): #the since has also to be used to stop retrieving data for an ID, but only if the SINCE is not the last one
               sinceNextMap = OneChannelInfo[mapIdx+1][2]
               if sinceNextMap < endDate:
                  if OneChannelInfo[mapIdx+1][3]: #check that the SINCE is marked with True to use it
                     lastDateToCall = str(sinceNextMap)
                     #if I have taken a date from the SINCE, this is not in format YYYY-MM-DD HH24:MI:SS
                     #remove from the date string the part of milliseconds
                     #find the last column :
                     lastDateToCall_lastColumnIdx = lastDateToCall.rfind(":")
                     lastDateToCall = lastDateToCall[:lastDateToCall_lastColumnIdx+3]

            if monitorFlag == "HV":
               queryAll = "select CHANGE_DATE, ACTUAL_IMON, ACTUAL_VMON, ACTUAL_STATUS, ACTUAL_ISON, ACTUAL_TEMP, ACTUAL_IMONREAL from " + tableData + " where DPID = " + str(OneChannelInfo[mapIdx][4]) + " and CHANGE_DATE > to_date( '" + str(firstDateToCall) + "', 'YYYY-MM-DD HH24:MI:SS') and CHANGE_DATE < to_date( '" + str(lastDateToCall) + "', 'YYYY-MM-DD HH24:MI:SS')"
            if monitorFlag == "LV":
               queryAll = "select CHANGE_DATE, ACTUAL_IMON, ACTUAL_VMON, ACTUAL_STATUS, ACTUAL_ISON, ACTUAL_TEMP from " + tableData + " where DPID = " + str(OneChannelInfo[mapIdx][4]) + " and CHANGE_DATE > to_date( '" + str(firstDateToCall) + "', 'YYYY-MM-DD HH24:MI:SS') and CHANGE_DATE < to_date( '" + str(lastDateToCall) + "', 'YYYY-MM-DD HH24:MI:SS')"

            verboseprint ( "OneChannelInfo", OneChannelInfo )
            verboseprint( "query", queryAll )

#            if monitorFlag == "HV":
#               queryAll = "select CHANGE_DATE, ACTUAL_IMON, ACTUAL_VMON, ACTUAL_STATUS, ACTUAL_ISON, ACTUAL_TEMP, ACTUAL_IMONREAL from " + tableData + " where DPID = " + str(OneChannelInfo[mapIdx][4]) + " and CHANGE_DATE > to_date( " + sta_period + ", 'YYYY-MM-DD HH24:MI:SS') and CHANGE_DATE < to_date( " + end_period + ", 'YYYY-MM-DD HH24:MI:SS')"
#            if monitorFlag == "LV":
#               queryAll = "select CHANGE_DATE, ACTUAL_IMON, ACTUAL_VMON, ACTUAL_STATUS, ACTUAL_ISON, ACTUAL_TEMP from " + tableData + " where DPID = " + str(OneChannelInfo[mapIdx][4]) + " and CHANGE_DATE > to_date( " + sta_period + ", 'YYYY-MM-DD HH24:MI:SS') and CHANGE_DATE < to_date( " + end_period + ", 'YYYY-MM-DD HH24:MI:SS')"

            #queryAll = "select CHANGE_DATE, ACTUAL_IMON, ACTUAL_VMON, ACTUAL_STATUS, ACTUAL_ISON, ACTUAL_TEMP from CMS_GEM_PVSS_COND.FWCAENCHANNELA1515 where  DPID = 55 and CHANGE_DATE > to_date( '2018-04-01 00:00:00', 'YYYY-MM-DD HH24:MI:SS') and CHANGE_DATE < to_date ( '2018-05-01 00:00:00', 'YYYY-MM-DD HH24:MI:SS')"

            cur.execute(queryAll)
            curAllData = cur
            for result in curAllData:
               #verboseprint (result)
               dateElem = result[0]
               imonElem = result[1]
               vmonElem = result[2]
               smonElem = result[3]
               isonElem = result[4] #it can be only 0 or 1
               tempElem = result[5] #in celcius degrees
               if monitorFlag == "HV":
                  imonRealElem = result[6]

               #for the final Tree I need dates in a  string format
               dateElemString = str(dateElem)

               #take the first Date
               if contData == 0:
                  startTs = result[0]

               tot_secondsDate = (dateElem - startTs).total_seconds()
               #verboseprint("tot_secondsDate:", tot_secondsDate) #('tot_secondsDate:', 16512.532)

               #convert dateElem in a usable format
               dateElemStr = str(dateElem)  #2017-04-01 00:00:32.439000
               #verboseprint("dateElemStr", dateElemStr)
               if (dateElemStr.find(".") != -1): #if dot found
                  dotIdx = dateElemStr.index(".")
                  dateNoMicro = dateElemStr[:dotIdx]
                  micro = dateElemStr[dotIdx+1:]
               else:                             #if dot not found
                  dateNoMicro = dateElemStr
                  micro = "000000"

               da1 = ROOT.TDatime( dateNoMicro )
               convertedDate = da1.Convert()

               floatMicro = "0." + micro
               dateElemSQL = convertedDate + float(floatMicro)

               #ATTENTION: I use ACTUAL_IMONREAL only if I have no info from ACTUAL_IMON
               #ATTENTION2: for smonData I have 4 elements: the last is the date in string
               if imonElem is not None:       #imon
                  tripleList = [ tot_secondsDate, dateElemSQL, imonElem ]
                  imonData.append( tripleList )
               """else:
                  if monitorFlag == "HV":
                     if imonRealElem is not None:
                        tripleList = [ tot_secondsDate, dateElemSQL, imonRealElem ]
                        imonData.append( tripleList )"""
               if vmonElem is not None:       #vmon
                  tripleList = [ tot_secondsDate, dateElemSQL, vmonElem, mapIdx, dateElemStr ]
                  vmonData.append( tripleList )
               if smonElem is not None:       #smon
                  tripleList = [ tot_secondsDate, dateElemSQL, smonElem, dateElemString ]
                  if smonElem < 0:
                     continue
                  smonData.append( tripleList )
               if isonElem is not None:       #ison
                  tripleList = [ tot_secondsDate, dateElemSQL, isonElem ]
                  isonData.append( tripleList )
               if tempElem is not None:       #temp
                  tripleList = [ tot_secondsDate, dateElemSQL, tempElem ]
                  tempData.append( tripleList )

               contData = contData + 1

            #verboseprint("imonData", imonData)
            #verboseprint("vmonData", vmonData)
            #verboseprint("smonData", smonData)
            #verboseprint("isonData", isonData)
            #verboseprint("tempData", tempData)

            verboseprint( chamberList[chIdx]+" "+channelName[channelIdx] + " (Alias: " +aliasThisMap+"): Not sorted lists created: WAIT PLEASE!!")

            #----------------SORT DATA-------------------------------------------------------
            #after collecting all data (we are inside the loop over chambers)
            #reorder data by date, the may not be in the correct time order
            #sort data in each of the seven channels

            imonData = sorted(imonData, key=lambda element: element[0]) #reorder using the internal list of imonData( element[0] is tot_secondsDate )
            vmonData = sorted(vmonData, key=lambda element: element[0])
            smonData = sorted(smonData, key=lambda element: element[0])
            isonData = sorted(isonData, key=lambda element: element[0])
            tempData = sorted(tempData, key=lambda element: element[0])

            #verboseprint("imonData", imonData)
            #verboseprint("vmonData", vmonData)
            #verboseprint("smonData", smonData)
            #verboseprint("isonData", isonData)
            #verboseprint("tempData", tempData)

            verboseprint("   Lists sorted: WAIT PLEASE!!")

            #look for Vmon values greater than 1000V
            fileVolts = open("Over1000Volts.txt","a")
            chchBool = False

            for vIdx in range(len(vmonData)):
               if ( vmonData[vIdx][2] >= 1000 ):
                  stringChamberChannel = chamberList[chIdx]+"\t"+channelName[channelIdx]+"\t"+aliasThisMap+"\n"
                  stringValues = "Date:"+str(vmonData[vIdx][4])+"\t"+" Vmon:"+str(vmonData[vIdx][2])+"\n"
                  if ( not chchBool ): #write the stringChamberChannel only one time
                     fileVolts.write( stringChamberChannel )
                     chchBool = True
                  fileVolts.write( stringValues )
            fileVolts.close()

         #----------------DUMP THE FIRST ELEMENT----------------------------------------------

         #verboseprint("len imonSortList", len(imonSortList))
         for idxElem in range(len(imonData)):
            secondAndThird = []
            secondAndThird.append(imonData[idxElem][1])
            secondAndThird.append(imonData[idxElem][2])
            imonData[idxElem] = secondAndThird

         for idxElem in range(len(vmonData)):
            secondAndThird = []
            secondAndThird.append(vmonData[idxElem][1])
            secondAndThird.append(vmonData[idxElem][2])
            vmonData[idxElem] = secondAndThird

         #smon has: 1 = date for TGraphs, 2 = decaimal status, 3 = date in string format
         for idxElem in range(len(smonData)):
            secondAndThird = []
            secondAndThird.append(smonData[idxElem][1])
            secondAndThird.append(int(smonData[idxElem][2]))
            secondAndThird.append(smonData[idxElem][3])
            smonData[idxElem] = secondAndThird

         for idxElem in range(len(isonData)):
            secondAndThird = []
            secondAndThird.append(isonData[idxElem][1])
            secondAndThird.append(isonData[idxElem][2])
            isonData[idxElem] = secondAndThird

         for idxElem in range(len(tempData)):
            secondAndThird = []
            secondAndThird.append(tempData[idxElem][1])
            secondAndThird.append(tempData[idxElem][2])
            tempData[idxElem] = secondAndThird

         #END OF LOOP ON MAPS: still inside loop on channels
         verboseprint("   Sorted lists filled!")

         #----------------CREATE HISTOGRAMS----------------------------------------------
         if monitorFlag == "HV":
            IMin = -20   #uA
            IMax = 20    #uA
            NBinImon = int(IMax-IMin)
            IUnitMeasure = "I [uA]"

            VMin = -50   #V
            VMax = 800
            NBinVmon = int((VMax-VMin)/10)

            StatusMin = 0
            StatusMax = 4100
            NBinStatus = StatusMax

            IsonMin = -1
            IsonMax = 3
            NBinIson = int(IsonMax-IsonMin)

            TempMin = 0  #celsius
            TempMax = 100
            NBinTemp = TempMax

         if monitorFlag == "LV":
            IMin = -10  #A
            IMax = 10
            NBinImon = int(IMax-IMin)
            IUnitMeasure = "I [A]"

            VMin = -10  #V
            VMax = 10  #V
            NBinVmon = int((VMax-VMin)/10)

            StatusMin = 0
            StatusMax = 65536
            NBinStatus = StatusMax

            IsonMin = -1
            IsonMax = 3
            NBinIson = int(IsonMax-IsonMin)

            TempMin = 0 #celsius
            TempMax = 100
            NBinTemp = TempMax

         #declare histograms
         chamberNameRootFile = chamberList[chIdx].replace("-", "_M")
         chamberNameRootFile = chamberNameRootFile.replace("+", "_P")
         chamberNameRootFile = chamberNameRootFile.replace("/", "_")

         Imonh1 = ROOT.TH1F(monitorFlag+"_ImonChamber"+  chamberNameRootFile+"_"+channelName[channelIdx]+"_TH1", monitorFlag+"_ImonChamber"+  chamberNameRootFile+"_"+channelName[channelIdx]+"_TH1", NBinImon, IMin, IMax)
         Vmonh1 = ROOT.TH1F(monitorFlag+"_VmonChamber"+  chamberNameRootFile+"_"+channelName[channelIdx]+"_TH1", monitorFlag+"_VmonChamber"+  chamberNameRootFile+"_"+channelName[channelIdx]+"_TH1", NBinVmon, VMin, VMax)
         Smonh1 = ROOT.TH1F(monitorFlag+"_StatusChamber"+chamberNameRootFile+"_"+channelName[channelIdx]+"_TH1", monitorFlag+"_StatusChamber"+chamberNameRootFile+"_"+channelName[channelIdx]+"_TH1", NBinStatus, StatusMin, StatusMax)
         Isonh1 = ROOT.TH1F(monitorFlag+"_IsonChamber"+  chamberNameRootFile+"_"+channelName[channelIdx]+"_TH1", monitorFlag+"_IsonChamber"+  chamberNameRootFile+"_"+channelName[channelIdx]+"_TH1", NBinIson, IsonMin, IsonMax)
         Temph1 = ROOT.TH1F(monitorFlag+"_TempChamber"+  chamberNameRootFile+"_"+channelName[channelIdx]+"_TH1", monitorFlag+"_TempChamber"+  chamberNameRootFile+"_"+channelName[channelIdx]+"_TH1", NBinTemp, TempMin, TempMax)

         #axis titles
         Imonh1.GetXaxis().SetTitle(IUnitMeasure)
         Imonh1.GetYaxis().SetTitle("counts")
         Vmonh1.GetXaxis().SetTitle("V [V]")
         Vmonh1.GetYaxis().SetTitle("counts")
         Smonh1.GetXaxis().SetTitle("Status code")
         Smonh1.GetYaxis().SetTitle("counts")
         Isonh1.GetXaxis().SetTitle("Ison status (0=OFF, 1=ON)")
         Isonh1.GetYaxis().SetTitle("counts")
         Temph1.GetXaxis().SetTitle("Temperature [Celsius degrees]")
         Temph1.GetYaxis().SetTitle("counts")

         #fill histograms: remember thet each row of Data has (Date, Value)
         for idxPoint in range(len(imonData)):
            Imonh1.Fill(imonData[idxPoint][1])

         for idxPoint in range(len(vmonData)):
            Vmonh1.Fill(vmonData[idxPoint][1])

         for idxPoint in range(len(smonData)):
            Smonh1.Fill(smonData[idxPoint][1])

         for idxPoint in range(len(isonData)):
            Isonh1.Fill(isonData[idxPoint][1])

         for idxPoint in range(len(tempData)):
            Temph1.Fill(tempData[idxPoint][1])

         #write TH1
         Imonh1.Write()
         Vmonh1.Write()
         Smonh1.Write()
         Isonh1.Write()
         Temph1.Write()

         #--------------------CREATE TGRAPHS-------------------------------------------
         #to create the TGraph I have to pass two lists: one with times and the other with values
         imonData_dates = array ( 'd' )
         vmonData_dates = array ( 'd' )
         smonData_dates = array ( 'd' )
         isonData_dates = array ( 'd' )
         tempData_dates = array ( 'd' )

         imonData_values = array ( 'd' )
         vmonData_values = array ( 'd' )
         smonData_values = array ( 'd' )
         isonData_values = array ( 'd' )
         tempData_values = array ( 'd' )

         for imonIdx in range(len(imonData)):
            imonData_dates.append(imonData[imonIdx][0])
            imonData_values.append(imonData[imonIdx][1])

         for vmonIdx in range(len(vmonData)):
            vmonData_dates.append(vmonData[vmonIdx][0])
            vmonData_values.append(vmonData[vmonIdx][1])

         for smonIdx in range(len(smonData)):
            smonData_dates.append(smonData[smonIdx][0])
            smonData_values.append(smonData[smonIdx][1])

         for isonIdx in range(len(isonData)):
            isonData_dates.append(isonData[isonIdx][0])
            isonData_values.append(isonData[isonIdx][1])

         for tempIdx in range(len(tempData)):
            tempData_dates.append(tempData[tempIdx][0])
            tempData_values.append(tempData[tempIdx][1])






         #in case there is nothing the TGraph gives error: put a dummy value
         dummyNumber = -999999999
         if monitorFlag == "HV":
            dummyStatus = 4095 #all 1 for a binary status of 12 bit
         if monitorFlag == "LV":
            dummyStatus = 65535 #all 1 for a binary status of 16 bit
         dummyDate = str("1970-01-01 00:00:01.000001")
         dummyPair = [0, dummyNumber]
         dummyThree = [0, dummyStatus, dummyDate]
         #Last Value
         if ( len(vmonData)==0 and sliceTestFlag == 0 and monitorFlag == "HV"  ):
            #queryLastValue = "select VALUE_NUMBER from CMS_GEM_PVSS_COND.FWCAENCHANNELA1515_LV where DPID = " + str(OneChannelInfo[mapIdx][4]) + " and DPE_NAME = 'ACTUAL_VMON'"
            #Do a query back in time
            foundLast = False
            firstDateBackInTime = firstDateToCall
            lastDateBackInTime  = lastDateToCall
            refDate = firstDateToCall
            timeIntervalStep = lastDateToCall - firstDateToCall
            for queryIdx in range(5):
                #firstDateBackInTime = firstDateBackInTime - timeIntervalStep
                #lastDateBackInTime  = lastDateBackInTime  - timeIntervalStep
                firstDateBackInTime = refDate - timedelta(hours=12*(queryIdx+1))
                lastDateBackInTime  = refDate - timedelta(hours=12*(queryIdx))
                queryLastValue = "select CHANGE_DATE, ACTUAL_VMON from " + tableData + " where DPID = " + str(OneChannelInfo[mapIdx][4]) + " and CHANGE_DATE > to_date( '" + str(firstDateBackInTime) + "', 'YYYY-MM-DD HH24:MI:SS') and CHANGE_DATE < to_date( '" + str(lastDateBackInTime) + "', 'YYYY-MM-DD HH24:MI:SS')"
                verboseprint ( queryLastValue )
                cur.execute(queryLastValue)
                curLast = cur
                lastValueList = []
                for curLastElem in curLast:
                   lastValue_date  = curLastElem[0]
                   lastValue_value = curLastElem[1]
                   if lastValue_value is not None:
                      lastValueList.append( [lastValue_date, lastValue_value] )
                #Sort the list
                lastValueList = sorted(lastValueList, key=lambda element: element[0])
                if len(lastValueList) > 0:
                   lastSavedVoltage_value = lastValueList[-1][1]
                   foundLast = True
                   break
            #verboseprint ( "LAST", lastSavedVoltage_value )
            startLast = start.replace("_", "-")
            startLastSplitList = startLast.split("-")
            lastDateStr = startLastSplitList[0]+"-"+startLastSplitList[1]+"-"+startLastSplitList[2]+" "+startLastSplitList[3]+":" +startLastSplitList[4]+":"+startLastSplitList[5]
            verboseprint ( "lastDateStr", lastDateStr)
            last_date = ROOT.TDatime( lastDateStr )
            lastDateConverted = last_date.Convert()
            floatMicro_LAST = "0.000001"
            dateElemSQL_LAST = lastDateConverted + float(floatMicro_LAST)

         if len(imonData)==0:
            imonData_dates.append(0)
            imonData_values.append(dummyNumber)
            imonData.append( dummyPair )
         if len(vmonData)==0:
            if foundLast:
               vmonData_dates.append(dateElemSQL_LAST)
               vmonData_values.append(lastSavedVoltage_value)
               vmonData.append( [dateElemSQL_LAST, lastSavedVoltage_value] )
            else:
               vmonData_dates.append(0)
               vmonData_values.append(dummyNumber)
               vmonData.append( dummyPair )
         if len(smonData)==0:
            smonData_dates.append(0)
            smonData_values.append(dummyStatus)
            smonData.append( dummyThree )
         if len(isonData)==0:
            isonData_dates.append(0)
            isonData_values.append(dummyNumber)
            isonData.append( dummyPair )
         if len(tempData)==0:
            tempData_dates.append(0)
            tempData_values.append(dummyNumber)
            tempData.append( dummyPair )

         #find minimum and maximum date between all channels of one chamber
         if ( imonData_dates[0] < minDateImonMultig ):
            minDateImonMultig = imonData_dates[0]-1
         if ( imonData_dates[-1] > maxDateImonMultig  ):
            maxDateImonMultig = imonData_dates[-1]+1

         if ( vmonData_dates[0] < minDateVmonMultig ):
            minDateVmonMultig = vmonData_dates[0]-1
         if ( vmonData_dates[-1] > maxDateVmonMultig  ):
            maxDateVmonMultig = vmonData_dates[-1]+1

         if ( smonData_dates[0] < minDateSmonMultig ):
            minDateSmonMultig = smonData_dates[0]-1
         if ( smonData_dates[-1] > maxDateSmonMultig  ):
            maxDateSmonMultig = smonData_dates[-1]+1

         if ( isonData_dates[0] < minDateIsonMultig ):
            minDateIsonMultig = isonData_dates[0]-1
         if ( isonData_dates[-1] > maxDateIsonMultig  ):
            maxDateIsonMultig = isonData_dates[-1]+1

         if ( tempData_dates[0] < minDateTempMultig ):
            minDateTempMultig = tempData_dates[0]-1
         if ( tempData_dates[-1] > maxDateTempMultig  ):
            maxDateTempMultig = tempData_dates[-1]+1

         #find the maximum and minimum value
         if ( min( imonData_values ) < minValImonMultig ):
            minValImonMultig = min( imonData_values )
         if ( max( imonData_values ) > maxValImonMultig ):
            maxValImonMultig = max( imonData_values )

         if ( min( vmonData_values ) < minValVmonMultig ):
            minValVmonMultig = min( vmonData_values )
         if ( max( vmonData_values ) > maxValVmonMultig ):
            maxValVmonMultig = max( vmonData_values )

         if ( min( smonData_values ) < minValSmonMultig ):
            minValSmonMultig = min( smonData_values )
         if ( max( smonData_values ) > maxValSmonMultig ):
            maxValSmonMultig = max( smonData_values )

         if ( min( tempData_values ) < minValTempMultig ):
            minValTempMultig = min( tempData_values )
         if ( max( tempData_values ) > maxValTempMultig ):
            maxValTempMultig = max( tempData_values )

         #declare TGraphs
         Imontg1 = ROOT.TGraph(len(imonData),imonData_dates,imonData_values)
         Vmontg1 = ROOT.TGraph(len(vmonData),vmonData_dates,vmonData_values)
         Smontg1 = ROOT.TGraph(len(smonData),smonData_dates,smonData_values)
         Isontg1 = ROOT.TGraph(len(isonData),isonData_dates,isonData_values)
         Temptg1 = ROOT.TGraph(len(tempData),tempData_dates,tempData_values)

         #prepeare one color for each channel
         markColor = 4 #default
         markNum = 20 #default
         transWhite = ROOT.TColor.GetColorTransparent(0, 0)
         if monitorFlag == "HV":
            if ( channelName[channelIdx].find("G3Bot") != -1):
               markColor = 1 #black
               markNum = 20
            if ( channelName[channelIdx].find("G3Top") != -1):
               markColor = 2 #red
               markNum = 21
            if ( channelName[channelIdx].find("G2Bot") != -1):
               markColor = 3 #green
               markNum = 22
            if ( channelName[channelIdx].find("G2Top") != -1):
               markColor = 4 #blue
               markNum = 23
            if ( channelName[channelIdx].find("G1Bot") != -1):
               markColor = 6 #pink
               markNum = 29
            if ( channelName[channelIdx].find("G1Top") != -1):
               markColor = 7 #light blue
               markNum = 33
            if ( channelName[channelIdx].find("Drift") != -1):
               markColor = 401 #darkYellow
               markNum = 34
         if monitorFlag == "LV":
            if ( channelName[channelIdx].find("L1") != -1):
               markColor = 2 #red
               markNum = 20
            if ( channelName[channelIdx].find("L2") != -1):
               markColor = 4 #blue
               markNum = 21

         #setting for TGraphs
         #Imontg1.SetLineColor(transWhite)
         Imontg1.SetLineWidth(0)
         Imontg1.SetMarkerColor(markColor)
         Imontg1.SetMarkerStyle(markNum)
         Imontg1.SetMarkerSize(1)

         #Vmontg1.SetLineColor(transWhite)
         Vmontg1.SetLineWidth(0)
         Vmontg1.SetMarkerColor(markColor)
         Vmontg1.SetMarkerStyle(markNum)
         Vmontg1.SetMarkerSize(1)

         #Smontg1.SetLineColor(transWhite)
         Smontg1.SetLineWidth(0)
         Smontg1.SetMarkerColor(markColor)
         Smontg1.SetMarkerStyle(markNum)
         Smontg1.SetMarkerSize(1)

         #Isontg1.SetLineColor(transWhite)
         Isontg1.SetLineWidth(0)
         Isontg1.SetMarkerColor(markColor)
         Isontg1.SetMarkerStyle(markNum)
         Isontg1.SetMarkerSize(1)

         #Temptg1.SetLineColor(transWhite)
         Temptg1.SetLineWidth(0)
         Temptg1.SetMarkerColor(markColor)
         Temptg1.SetMarkerStyle(markNum)
         Temptg1.SetMarkerSize(1)

         #TGraph names
         Imontg1.SetName(monitorFlag+"_ImonChamber"+  chamberNameRootFile+"_"+channelName[channelIdx]+"_UTC_time")
         Vmontg1.SetName(monitorFlag+"_VmonChamber"+  chamberNameRootFile+"_"+channelName[channelIdx]+"_UTC_time")
         Smontg1.SetName(monitorFlag+"_StatusChamber"+chamberNameRootFile+"_"+channelName[channelIdx]+"_UTC_time")
         Isontg1.SetName(monitorFlag+"_IsonChamber"+  chamberNameRootFile+"_"+channelName[channelIdx]+"_UTC_time")
         Temptg1.SetName(monitorFlag+"_TempChamber"+  chamberNameRootFile+"_"+channelName[channelIdx]+"_UTC_time")

         #TGraph title
         Imontg1.SetTitle(monitorFlag+"_ImonChamber"+  chamberNameRootFile+"_"+channelName[channelIdx]+"_UTC_time")
         Vmontg1.SetTitle(monitorFlag+"_VmonChamber"+  chamberNameRootFile+"_"+channelName[channelIdx]+"_UTC_time")
         Smontg1.SetTitle(monitorFlag+"_StatusChamber"+chamberNameRootFile+"_"+channelName[channelIdx]+"_UTC_time")
         Isontg1.SetTitle(monitorFlag+"_IsonChamber"+  chamberNameRootFile+"_"+channelName[channelIdx]+"_UTC_time")
         Temptg1.SetTitle(monitorFlag+"_TempChamber"+  chamberNameRootFile+"_"+channelName[channelIdx]+"_UTC_time")

         #Y axis
         if monitorFlag == "HV":
            currentBrak = "[uA]"
         if monitorFlag == "LV":
            currentBrak = "[A]"
         Imontg1.GetYaxis().SetTitle("Imon "+chamberNameRootFile+" "+channelName[channelIdx]+" "+currentBrak)
         #Vmontg1.GetYaxis().SetTitle("Vmon "+chamberNameRootFile+" "+channelName[channelIdx]+" [V]")
         Vmontg1.GetYaxis().SetTitle("#Delta Vmon [V]")
         Smontg1.GetYaxis().SetTitle("Status code "+chamberNameRootFile+" "+channelName[channelIdx])
         Isontg1.GetYaxis().SetTitle("Ison code: 0=ON 1=OFF "+chamberNameRootFile+" "+channelName[channelIdx])
         Temptg1.GetYaxis().SetTitle("Temperature "+chamberNameRootFile+" "+channelName[channelIdx]+" [Celsius degrees]")

         #X axis
         Imontg1.GetXaxis().SetTimeDisplay(1)
         Vmontg1.GetXaxis().SetTimeDisplay(1)
         Smontg1.GetXaxis().SetTimeDisplay(1)
         Isontg1.GetXaxis().SetTimeDisplay(1)
         Temptg1.GetXaxis().SetTimeDisplay(1)

         Imontg1.GetXaxis().SetTimeFormat("#splitline{%y-%m-%d}{%H:%M:%S}%F1970-01-01 00:00:00")
         Vmontg1.GetXaxis().SetTimeFormat("#splitline{%y-%m-%d}{%H:%M:%S}%F1970-01-01 00:00:00")
         Smontg1.GetXaxis().SetTimeFormat("#splitline{%y-%m-%d}{%H:%M:%S}%F1970-01-01 00:00:00")
         Isontg1.GetXaxis().SetTimeFormat("#splitline{%y-%m-%d}{%H:%M:%S}%F1970-01-01 00:00:00")
         Temptg1.GetXaxis().SetTimeFormat("#splitline{%y-%m-%d}{%H:%M:%S}%F1970-01-01 00:00:00")

         Imontg1.GetXaxis().SetLabelOffset(0.025)
         Vmontg1.GetXaxis().SetLabelOffset(0.025)
         Smontg1.GetXaxis().SetLabelOffset(0.025)
         Isontg1.GetXaxis().SetLabelOffset(0.025)
         Temptg1.GetXaxis().SetLabelOffset(0.025)

         Imontg1.GetXaxis().SetLabelSize(0.018)
         Vmontg1.GetXaxis().SetLabelSize(0.018)
         Smontg1.GetXaxis().SetLabelSize(0.018)
         Isontg1.GetXaxis().SetLabelSize(0.018)
         Temptg1.GetXaxis().SetLabelSize(0.018)

         Imontg1.GetYaxis().SetLabelSize(0.018)
         Vmontg1.GetYaxis().SetLabelSize(0.018)
         Smontg1.GetYaxis().SetLabelSize(0.018)
         Isontg1.GetYaxis().SetLabelSize(0.018)
         Temptg1.GetYaxis().SetLabelSize(0.018)


         #Write TGraph
         Imontg1.Write()
         Vmontg1.Write()
         Smontg1.Write()
         Isontg1.Write()
         Temptg1.Write()

         #canvas dimensions
         canW = 800;
         canH = 800;
         canH_ref = 800;
         canW_ref = 800;

         #references for T, B, L, R
         TopMar = 0.12*canH_ref;
         BotMar = 0.17*canH_ref;
         LeftMar = 0.15*canW_ref;
         RightMar = 0.12*canW_ref;

         #declare a TPaveText for CMS Prelimiary
         cmsPrelOneGr = ROOT.TPaveText(0.13,0.88,0.355,0.96,"brNDC");
         cmsPrelOneGr.AddText("CMS Preliminary");
         cmsPrelOneGr.SetTextAlign(12);
         cmsPrelOneGr.SetShadowColor(transWhite);
         cmsPrelOneGr.SetFillColor(transWhite);
         cmsPrelOneGr.SetLineColor(transWhite);
         cmsPrelOneGr.SetLineColor(transWhite);

         #declare a TPaveText for CMS xAxis title
         xAxisLabOneGr = ROOT.TPaveText(0.6,0.88,0.9,0.92,"brNDC");
         xAxisLabOneGr.AddText("Date(YY-MM-DD) / UTC Time(hh:mm:ss)");
         xAxisLabOneGr.SetTextAlign(12);
         xAxisLabOneGr.SetShadowColor(transWhite);
         xAxisLabOneGr.SetFillColor(transWhite);
         xAxisLabOneGr.SetLineColor(transWhite);
         xAxisLabOneGr.SetLineColor(transWhite);

         #save TGraphSingleChannel

         #chStringSaveArr = ["Drift", "G1Bot", "G2Bot", "G3Bot"]

         #for saveIdx in range(len(chStringSaveArr)):
         #   if ( channelName[channelIdx] == chStringSaveArr[saveIdx] ):
         #      #declare two canvas
         #      chStringSave = chStringSaveArr[saveIdx]
         #      imonCanvasOneGr = ROOT.TCanvas("ImonCanvasOneGraph", chamberList[chIdx]+chStringSave, 50, 50, 800, 800 )
         #      imonCanvasOneGr.SetLeftMargin( LeftMar/canW )
         #      imonCanvasOneGr.SetRightMargin( RightMar/canW )
         #      imonCanvasOneGr.SetTopMargin( TopMar/canH )
         #      imonCanvasOneGr.SetBottomMargin( BotMar/canH )
         #      Imontg1.Draw("AP")
         #      cmsPrelOneGr.Draw("NB")
         #      xAxisLabOneGr.Draw("NB")
         #      chamberNameNoSlash = chamberList[chIdx].replace("/","_")
         #      if args.save: imonCanvasOneGr.SaveAs(dirStringSave+"/Imon_"+chamberNameNoSlash+"_"+chStringSave+".png")

         #      vmonCanvasOneGr = ROOT.TCanvas("VmonCanvasOneGraph", chamberList[chIdx]+chStringSave, 50, 50, 800, 800 )
         #      vmonCanvasOneGr.SetLeftMargin( LeftMar/canW )
         #      vmonCanvasOneGr.SetRightMargin( RightMar/canW )
         #      vmonCanvasOneGr.SetTopMargin( TopMar/canH )
         #      vmonCanvasOneGr.SetBottomMargin( BotMar/canH )
         #      Vmontg1.Draw("AP")
         #      cmsPrelOneGr.Draw("NB")
         #      xAxisLabOneGr.Draw("NB")
         #      if args.save: vmonCanvasOneGr.SaveAs(dirStringSave+"/Vmon_"+chamberNameNoSlash+"_"+chStringSave+".png")

         #      del( imonCanvasOneGr )
         #      del( vmonCanvasOneGr )




         #add graphs to multigraphs
         Imontmultig1.Add(Imontg1)
         Vmontmultig1.Add(Vmontg1)
         Smontmultig1.Add(Smontg1)
         Isontmultig1.Add(Isontg1)
         Temptmultig1.Add(Temptg1)

         if ( channelName[channelIdx] == "G3Bot" ):
            legendMultiImon.AddEntry( Imontg1, "GEM-3 bot electrode", "p" )
            legendMultiVmon.AddEntry( Imontg1, "#Delta V Induction gap", "p" )
         if ( channelName[channelIdx] == "G3Top" ):
            legendMultiImon.AddEntry( Imontg1, "GEM-3 top electrode", "p" )
            legendMultiVmon.AddEntry( Imontg1, "#Delta V GEM-3 foil", "p" )
         if ( channelName[channelIdx] == "G2Bot" ):
            legendMultiImon.AddEntry( Imontg1, "GEM-2 bot electrode", "p" )
            legendMultiVmon.AddEntry( Imontg1, "#Delta V Transfer-2 gap", "p" )
         if ( channelName[channelIdx] == "G2Top" ):
            legendMultiImon.AddEntry( Imontg1, "GEM-2 top electrode", "p" )
            legendMultiVmon.AddEntry( Imontg1, "#Delta V GEM-2 foil", "p" )
         if ( channelName[channelIdx] == "G1Bot" ):
            legendMultiImon.AddEntry( Imontg1, "GEM-1 bot electrode", "p" )
            legendMultiVmon.AddEntry( Imontg1, "#Delta V Transfer-1 gap", "p" )
         if ( channelName[channelIdx] == "G1Top" ):
            legendMultiImon.AddEntry( Imontg1, "GEM-1 top electrode", "p" )
            legendMultiVmon.AddEntry( Imontg1, "#Delta V GEM-1 foil", "p" )
         if ( channelName[channelIdx] == "Drift" ):
            legendMultiImon.AddEntry( Imontg1, "Drift electrode", "p" )
            legendMultiVmon.AddEntry( Imontg1, "#Delta V Drift gap", "p" )


         if ( channelName[channelIdx] == "L1" ):
            legendMultiImon.AddEntry( Imontg1, "Layer 1", "p" )
            legendMultiVmon.AddEntry( Imontg1, "Layer 1", "p" )
         if ( channelName[channelIdx] == "L2" ):
            legendMultiImon.AddEntry( Imontg1, "Layer 2", "p" )
            legendMultiVmon.AddEntry( Imontg1, "Layer 2", "p" )

         #----------------------TREE STATUS------------------------------------------------
         #translate the status in binary and meaning string
         smonData_binStatus     = []
         smonData_decimalStatus = []
         smonData_dateString    = []
         smonData_meaningString = []

         #---------------------STATUS MEANING FOR HV--------------------------------------
         if monitorFlag == "HV":
            #12 bit status for HV board A1515
            #Bit 0: ON/OFF
            #Bit 1: RUP
            #Bit 2: RDW
            #Bit 3: OVC
            #Bit 4: OVV
            #Bit 5: UVV
            #Bit 6: etx trip
            #Bit 7: MAX V
            #Bit 8: EXT disable
            #Bit 9: Internal Trip
            #Bit 10: calibration error
            #Bit 11: unplugged

            nBit = 12
            for smonIdx in range(len(smonData)):
               #binary status
               binStat = bin(int(smonData[smonIdx][1]))[2:] #to take away the 0b in front of the binary number
               #verboseprint ("binStat:", binStat)
               lenStat = len(binStat)
               binStat = str(0) * (nBit - lenStat) + binStat
               binStat = "0b"+binStat
               smonData_binStatus.append( binStat )

               #decimal status
               smonData_decimalStatus.append( smonData[smonIdx][1] )

               #date string
               smonData_dateString.append( smonData[smonIdx][2] )

               #meaning string
               extensibleStat = ""
               if binStat == "0b000000000000": #these are binary numbers
                  StatusMeaning = "OFF"
                  #verboseprint(StatusMeaning)

               if binStat == "0b000000000001": #these are binary numbers
                  StatusMeaning = "ON"
                  #verboseprint(StatusMeaning)

               cutBinStr = binStat[13:]
               if cutBinStr == "0": #if I have OFF
                  extensibleStat = extensibleStat + "OFF" + " "
               elif cutBinStr == "1": #if I have OFF
                  extensibleStat = extensibleStat + "ON" + " "

               #bin produces a string (so the operation >> can be only made only on int)
               #I observe the bin number with bin(shift2)
               #I shift of one bit to delete the bit 0 from the string
               shift2 = binStat[:-1]

               #verboseprint("binStat:", binStat, "shift2:", shift2 )
               if len(shift2) != 13:
                  print(("ERROR: "+monitorFlag+" error in len of shift2. Len="+str(len(shift2))+"/13"))
                  print(("binStat:", binStat, "shift2:", shift2))
                  return 1

               #for the second status cathegory I need the last two bins of shift2
               #print ( "shift2", shift2, "bin 1 and 2", shift2[11:])
               if int(shift2[11:]) > 0:
                  #print (shift2[11:])
                  cutBinStr = shift2[11:]
                  if cutBinStr[1] == "1": #if I have RUP
                     StatusMeaning = "RUP"
                     extensibleStat = extensibleStat + StatusMeaning + " "
                     #print(StatusMeaning)
                  if cutBinStr[0] == "1": #if I have RDW
                     StatusMeaning = "RDW"
                     extensibleStat = extensibleStat + StatusMeaning + " "
                     #print(StatusMeaning)

               #third status
               shift3 = binStat[:-3]
               if len(shift3) != 11:
                  print(("ERROR: "+monitorFlag+" error in len of shift3. Len="+str(len(shift3))+"/11"))
                  print(("shift3:", shift3))
                  return 1

               #print ( "shift3", shift3, "bin 3, 4, 5", shift3[8:])
               if int(shift3[8:]) > 0:
                  #print (shift3[8:])
                  cutBinStr = shift3[8:]
                  if cutBinStr[2] == "1": #if I have OVC
                     StatusMeaning = "OVC"
                     extensibleStat = extensibleStat + StatusMeaning + " "
                     #print(StatusMeaning)
                  if cutBinStr[1] == "1": #if I have OVV
                     StatusMeaning = "OVV"
                     extensibleStat = extensibleStat + StatusMeaning + " "
                     #print(StatusMeaning)
                  if cutBinStr[0] == "1": #if I have UVV
                     StatusMeaning = "UVV"
                     extensibleStat = extensibleStat + StatusMeaning + " "
                     #print(StatusMeaning)

               #fourth status
               shift4 = binStat[:-6]
               if len(shift4) != 8:
                  print(("ERROR: "+monitorFlag+" error in len of shift4. Len="+str(len(shift4))+"/8"))
                  print(("shift4:", shift4))
                  return 1

               #print ( "shift4", shift4, "bin 6, 7, 8, 9", shift4[4:])
               if int(shift4[4:]) > 0:
                  #print (shift4[4:])
                  cutBinStr = shift4[4:]
                  if cutBinStr[3] == "1": #if I have Ext Trip
                     StatusMeaning = "Ext Trip"
                     extensibleStat = extensibleStat + StatusMeaning + " "
                     #print(StatusMeaning)
                  if cutBinStr[2] == "1": #if I have Max V
                     StatusMeaning = "Max V"
                     extensibleStat = extensibleStat + StatusMeaning + " "
                     #print(StatusMeaning)
                  if cutBinStr[1] == "1": #if I have Ext Disable
                     StatusMeaning = "Ext Disable"
                     extensibleStat = extensibleStat + StatusMeaning + " "
                     #print(StatusMeaning)
                  if cutBinStr[0] == "1": #if I have Int Trip
                     StatusMeaning = "Int Trip"
                     extensibleStat = extensibleStat + StatusMeaning + " "
                     #print(StatusMeaning)

               #fifth status
               shift5 = binStat[:-10]
               if len(shift5) != 4:
                  print(("ERROR: "+monitorFlag+" error in len of shift5. Len="+str(len(shift5))+"/4"))
                  print(("shift5:", shift5))
                  return 1

               #print ( "shift5", shift5, "bin 10", shift5[3:])
               if int(shift5[3:]) > 0:
                  #print (shift5[3:])
                  cutBinStr = shift5[3:]
                  if cutBinStr[0] == "1": #if I have Calib Error
                     StatusMeaning = "Calib Error"
                     extensibleStat = extensibleStat + StatusMeaning + " "
                     #print(StatusMeaning)

               #sixth status
               shift6 = binStat[:-11]
               if len(shift6) != 3:
                  print(("ERROR: "+monitorFlag+" error in len of shift6. Len="+str(len(shift6))+"/3"))
                  print(("shift6:", shift6))
                  return 1

               #print ( "shift6", shift6, "bin 11", shift6[2:])
               if int(shift6[2:]) > 0:
                  #print (shift6[2:])
                  cutBinStr = shift6[2:]
                  if cutBinStr[0] == "1": #if I have Unplugged
                     StatusMeaning = "Unplugged"
                     extensibleStat = extensibleStat + StatusMeaning + " "
                     #print(StatusMeaning)

               smonData_meaningString.append( extensibleStat )

            #END OF LOOP OVER smonData

         #---------------------STATUS MEANING FOR LV--------------------------------------------
         if monitorFlag == "LV":
            #for LV boards A3016 or A3016HP we have a 16 bit status
            #LV boards (CAEN A3016 o A3016 HP)
            #Bit 0: ON/OFF
            #Bit 1: dont care
            #Bit 2: dont care
            #Bit 3: OverCurrent
            #Bit 4: OverVoltage
            #Bit 5: UnderVoltage
            #Bit 6: dont care
            #Bit 7: Over HVmax
            #Bit 8: dont care
            #Bit 9: Internal Trip
            #Bit 10: Calibration Error
            #Bit 11: Unplugged
            #Bit 12: dont care
            #Bit 13: OverVoltage Protection
            #Bit 14: Power Fail
            #Bit 15: Temperature Error

            nBit = 16
            for smonIdx in range(len(smonData)):
               #binary status
               binStat = bin(int(smonData[smonIdx][1]))[2:] #to take away the 0b in front of the binary number
               #print ("binStat:", binStat)
               lenStat = len(binStat)
               binStat = str(0) * (nBit - lenStat) + binStat
               binStat = "0b"+binStat
               smonData_binStatus.append( binStat )

               #decimal status
               smonData_decimalStatus.append( smonData[smonIdx][1] )

               #date string
               smonData_dateString.append( smonData[smonIdx][2] )

               #meaning string
               extensibleStat = ""
               if len(binStat) != (nBit + 2) :
                  print(("ERROR: "+monitorFlag+" error in len of binStat. Len="+len(binStat)+"/"+str(nBit + 2)))
                  return 1

               if binStat == "0b0000000000000000": #these are binary numbers
                  StatusMeaning = "OFF"
                  #print(StatusMeaning)

               if binStat == "0b0000000000000001": #these are binary numbers
                  StatusMeaning = "ON"
                  #print(StatusMeaning)

               cutBinStr = binStat[-1:]
               if cutBinStr == "0": #if I have OFF
                  extensibleStat = extensibleStat + "OFF" + " "
               elif cutBinStr == "1": #if I have OFF
                  extensibleStat = extensibleStat + "ON" + " "

               #bin produces a string (so the operation >> can be only made only on int)
               #I observe the bin number with bin(shift2)
               #I shift of one bit to delete the bit 0 from the string
               removedBits = 0 - 1 #negative number
               shift2 = binStat[:removedBits]

               #print("binStat:", binStat, "shift2:", shift2 )
               if len(shift2) != (nBit + 2) + removedBits:
                  print(("ERROR: "+monitorFlag+" error in len of shift2. Len="+len(shift2)+"/"+str(nBit + 2 + removedBits )))
                  return 1

               #I have to remove bit 1 and 2 because they are not interesting
               #len(shift2)-2    -2 because I want the last two bits
               #print ( "shift2", shift2, "bin 1 and 2", shift2[len(shift2)-2:])

               #remove bit 1 and 2 : second status cathegory even if it is written mismatch 3: I removed the bits
               removedBits = removedBits - 2 #negative number
               shift3 = binStat[:removedBits]

               if len(shift3) != (nBit + 2) + removedBits:
                  print(("ERROR: "+monitorFlag+" error in len of shift3. Len="+len(shift3)+"/"+str(nBit + 2 + removedBits )))
                  return 1

               #for the second status cathegory I need the last two bins of shift3
               #print ( "shift3", shift3, "bit 3 4 5", shift3[len(shift3)-3:])
               if int(shift3[len(shift3)-3:]) > 0:
                  #print (shift3[len(shift3)-3:])
                  cutBinStr = shift3[len(shift3)-3:]
                  if cutBinStr[2] == "1": #if I have OVC
                     StatusMeaning = "OVC"
                     extensibleStat = extensibleStat + StatusMeaning + " "
                     #print(StatusMeaning)
                  if cutBinStr[1] == "1": #if I have OVV
                     StatusMeaning = "OVV"
                     extensibleStat = extensibleStat + StatusMeaning + " "
                     #print(StatusMeaning)
                  if cutBinStr[0] == "1": #if I have UVV
                     StatusMeaning = "UVV"
                     extensibleStat = extensibleStat + StatusMeaning + " "
                     #print(StatusMeaning)

               #remove bit 3 4 5
               removedBits = removedBits - 3 #negative number
               shift4 = binStat[:removedBits]

               if len(shift4) != (nBit + 2) + removedBits:
                  print(("ERROR: "+monitorFlag+" error in len of shift4. Len="+len(shift4)+"/"+str(nBit + 2 + removedBits )))
                  return 1

               #print ( "shift4", shift4, "bit 6", shift4[len(shift4)-1:])

               #remove bit 6
               removedBits = removedBits - 1 #negative number
               shift5 = binStat[:removedBits]

               if len(shift5) != (nBit + 2) + removedBits:
                  print(("ERROR: "+monitorFlag+" error in len of shift5. Len="+len(shift5)+"/"+str(nBit + 2 + removedBits )))
                  return 1
               #for the third status cathegory I need the last four bins of shift5
               #I dont register the bit 8 beacuse not interesting
               #print ( "shift5", shift5, "bit 7, 8, 9", shift5[len(shift5)-3:])
               if int(shift5[len(shift5)-3:]) > 0:
                  #print (shift5[len(shift5)-3:])
                  cutBinStr = shift5[len(shift5)-3:]
                  if cutBinStr[2] == "1": #if I have OHVMax
                     StatusMeaning = "OHVMax"
                     extensibleStat = extensibleStat + StatusMeaning + " "
                     #print(StatusMeaning)
                  if cutBinStr[0] == "1": #if I have INTTRIP
                     StatusMeaning = "InTrip"
                     extensibleStat = extensibleStat + StatusMeaning + " "
                     #print(StatusMeaning)

               #remove bit 7 8 9 to do the fourth status cathegory
               removedBits = removedBits - 3 #negative number
               shift6 = binStat[:removedBits]

               if len(shift6) != (nBit + 2) + removedBits:
                  print(("ERROR: "+monitorFlag+" error in len of shift6. Len="+len(shift6)+"/"+str(nBit + 2 + removedBits )))
                  return 1

               #for the fourth status cathegory I need the last bit of shift6
               #print ( "shift6", shift6, "bit 10", shift6[len(shift6)-1:])
               if int(shift6[len(shift6)-1:]) > 0:
                  #print (shift6[len(shift6)-1:])
                  cutBinStr = shift6[len(shift6)-1:]
                  if cutBinStr[0] == "1": #if I have Calib Error
                     StatusMeaning = "CalibERR"
                     extensibleStat = extensibleStat + StatusMeaning + " "
                     #print(StatusMeaning)

               #remove bit 10
               removedBits = removedBits - 1 #negative number
               shift7 = binStat[:removedBits]

               if len(shift7) != (nBit + 2) + removedBits:
                  print(("ERROR: "+monitorFlag+" error in len of shift7. Len="+len(shift7)+"/"+str(nBit + 2 + removedBits )))
                  return 1

               #for the fifth status cathegory I need the last bit of shift7
               #print ( "shift7", shift7, "bit 11", shift7[len(shift7)-1:])
               if int(shift7[len(shift7)-1:]) > 0:
                  #print (shift7[len(shift7)-1:])
                  cutBinStr = shift7[len(shift7)-1:]
                  if cutBinStr[0] == "1": #if I have Unplugged
                     StatusMeaning = "Unplugged"
                     extensibleStat = extensibleStat + StatusMeaning + " "
                     #print(StatusMeaning)

               #remove bit 11
               removedBits = removedBits - 1 #negative number
               shift8 = binStat[:removedBits]

               if len(shift8) != (nBit + 2) + removedBits:
                  print(("ERROR: "+monitorFlag+" error in len of shift8. Len="+len(shift8)+"/"+str(nBit + 2 + removedBits )))
                  return 1

               #print ( "shift8", shift8, "bit 12", shift8[len(shift8)-1:])   #bit 12 not interesting

               #remove bit 12 to do the sixth status cathegory
               removedBits = removedBits - 1 #negative number
               shift9 = binStat[:removedBits]

               if len(shift9) != (nBit + 2) + removedBits:
                  print(("ERROR: "+monitorFlag+" error in len of shift9. Len="+len(shift9)+"/"+str(nBit + 2 + removedBits )))
                  return 1

               #for the sixth status cathegory I need the last bit of shift9
               #print ( "shift9", shift9, "bit 13", shift9[len(shift9)-1:])
               if int(shift9[len(shift9)-1:]) > 0:
                  #print (shift9[len(shift9)-1:])
                  cutBinStr = shift9[len(shift9)-1:]
                  if cutBinStr[0] == "1": #if I have OVVPROT
                     StatusMeaning = "OVVPROT"
                     extensibleStat = extensibleStat + StatusMeaning + " "
                     #print(StatusMeaning)

               #remove bit 13 to do the seventh status cathegory
               removedBits = removedBits - 1 #negative number
               shift10 = binStat[:removedBits]

               if len(shift10) != (nBit + 2) + removedBits:
                  print(("ERROR: "+monitorFlag+" error in len of shift10. Len="+len(shift10)+"/"+str(nBit + 2 + removedBits )))
                  return 1

               #for the seventh status cathegory I need the last bit of shift10
               #print ( "shift10", shift10, "bit 14", shift10[len(shift10)-1:])
               if int(shift10[len(shift10)-1:]) > 0:
                  #print (shift10[len(shift10)-1:])
                  cutBinStr = shift10[len(shift10)-1:]
                  if cutBinStr[0] == "1": #if I have POWFAIL
                     StatusMeaning = "POWFAIL"
                     extensibleStat = extensibleStat + StatusMeaning + " "
                     #print(StatusMeaning)

               #remove bit 14 to do the eight status cathegory
               removedBits = removedBits - 1 #negative number
               shift11 = binStat[:removedBits]

               if len(shift11) != (nBit + 2) + removedBits:
                  print(("ERROR: "+monitorFlag+" error in len of shift11. Len="+len(shift11)+"/"+str(nBit + 2 + removedBits )))
                  return 1

               #for the eight status cathegory I need the last bit of shift11
               #print ( "shift11", shift11, "bit 15", shift11[len(shift11)-1:])
               if int(shift11[len(shift11)-1:]) > 0:
                  #print (shift11[len(shift11)-1:])
                  cutBinStr = shift11[len(shift11)-1:]
                  if cutBinStr[0] == "1": #if I have TEMPERR
                     StatusMeaning = "TEMPERR"
                     extensibleStat = extensibleStat + StatusMeaning + " "
                     #print(StatusMeaning)

               smonData_meaningString.append( extensibleStat )

            #END OF LOOP OVER smonData


         #------------------CHECK SIZE OF VECTORS FOR TREE-------------------------------------
         #check lenght of vectors
         if len(smonData) != len(smonData_binStatus):
            print(("ERROR: "+monitorFlag+" len(smonData) different from len(smonData_binStatus)"))
            print(("len(smonData):", len(smonData), "len(smonData_binStatus):", len(smonData_binStatus)))
            return 1
         if len(smonData_binStatus) != len(smonData_decimalStatus):
            print(("ERROR: "+monitorFlag+" len(smonData_binStatus) different from len(smonData_binStatus)"))
            print(("len(smonData_binStatus):", len(smonData_binStatus), "len(smonData_decimalStatus):", len(smonData_decimalStatus)))
            return 1
         if len(smonData_decimalStatus) != len(smonData_dateString):
            print(("ERROR: "+monitorFlag+" len(smonData_decimalStatus) different from len(smonData_dateString)"))
            print(("len(smonData_decimalStatus):", len(smonData_decimalStatus), "len(smonData_dateString):", len(smonData_dateString)))
            return 1
         if len(smonData_dateString) != len(smonData_meaningString):
            print(("ERROR: "+monitorFlag+" len(smonData_dateString) different from len(smonData_meaningString)"))
            print(("len(smonData_dateString):", len(smonData_dateString), "len(smonData_meaningString):", len(smonData_meaningString)))
            return 1


         #---------------------TREE DECLARATION------------------------------------------------
         StatusTree = ROOT.TTree(monitorFlag+"_StatusTree"+chamberNameRootFile+"_"+channelName[channelIdx], monitorFlag+"_StatusTree"+chamberNameRootFile+"_"+channelName[channelIdx])

         smonRootTimesDate   = ROOT.vector('string')()
         smonRootDecimalStat = ROOT.vector('string')()
         smonRootBinStat     = ROOT.vector('string')()
         smonRootMeaningStat = ROOT.vector('string')()

         StatusTree.Branch( 'TS',          smonRootTimesDate   )
         StatusTree.Branch( 'DecimalStat', smonRootDecimalStat )
         StatusTree.Branch( 'BinaryStat',  smonRootBinStat     )
         StatusTree.Branch( 'MeaningStat', smonRootMeaningStat )

         for smonIdx in range(len( smonData )):
            smonRootTimesDate.push_back(   smonData_dateString[smonIdx]    )
            smonRootDecimalStat.push_back( str(smonData_decimalStatus[smonIdx]) )
            smonRootBinStat.push_back(     smonData_binStatus[smonIdx]     )
            smonRootMeaningStat.push_back( smonData_meaningString[smonIdx] )

         StatusTree.Fill()#fill done when vectors are ready and full

         StatusTree.Write()

      #end of loop over channels

      #calculate how much to adjust the range in Y for multigraphs
      rangeImon = maxValImonMultig - minValImonMultig
      rangeVmon = maxValVmonMultig - minValVmonMultig
      rangeSmon = maxValSmonMultig - minValSmonMultig
      rangeTemp = maxValTempMultig - minValTempMultig

      minValImonMultig = minValImonMultig - 0.05*rangeImon
      minValVmonMultig = minValVmonMultig - 0.05*rangeVmon
      minValSmonMultig = minValSmonMultig - 0.05*rangeSmon
      minValTempMultig = minValTempMultig - 0.05*rangeTemp

      maxValImonMultig = maxValImonMultig + 0.05*rangeImon
      maxValVmonMultig = maxValVmonMultig + 0.05*rangeVmon
      maxValSmonMultig = maxValSmonMultig + 0.05*rangeSmon
      maxValTempMultig = maxValTempMultig + 0.05*rangeTemp

      print(("chamber: ", chamberList[chIdx] ))

      fontSize = 0.018

      #set multigraphs
      Imontmultig1.GetXaxis().SetRangeUser( minDateImonMultig, maxDateImonMultig )
      Imontmultig1.GetYaxis().SetRangeUser( minValImonMultig-0.5*rangeImon, maxValImonMultig )
      Imontmultig1.GetYaxis().SetTitle("Monitored current (#muA)")
      Imontmultig1.GetXaxis().SetTimeDisplay(1)
      Imontmultig1.GetXaxis().SetTimeFormat("#splitline{%y-%m-%d}{%H:%M:%S}%F1970-01-01 00:00:00")
      Imontmultig1.GetXaxis().SetLabelOffset(0.025)
      Imontmultig1.GetXaxis().SetLabelSize(fontSize)
      Imontmultig1.GetYaxis().SetLabelSize(fontSize)

      Vmontmultig1.GetXaxis().SetRangeUser( minDateVmonMultig, maxDateVmonMultig )
      Vmontmultig1.GetYaxis().SetRangeUser( minValVmonMultig, maxValVmonMultig+0.6*rangeVmon )
      Vmontmultig1.GetYaxis().SetTitle("Monitored voltage (V)")
      Vmontmultig1.GetXaxis().SetTimeDisplay(1)
      Vmontmultig1.GetXaxis().SetTimeFormat("#splitline{%y-%m-%d}{%H:%M:%S}%F1970-01-01 00:00:00")
      Vmontmultig1.GetXaxis().SetLabelOffset(0.025)
      Vmontmultig1.GetXaxis().SetLabelSize(fontSize)
      Vmontmultig1.GetYaxis().SetLabelSize(fontSize)

      Smontmultig1.GetXaxis().SetRangeUser( minDateSmonMultig, maxDateSmonMultig )
      Smontmultig1.GetYaxis().SetRangeUser( minValSmonMultig, maxValSmonMultig )
      #Smontmultig1.GetYaxis().SetTitle("Date(YY-MM-DD) / UTC Time(hh:mm:ss)"); #used to produce the label with the same font easily
      Smontmultig1.GetXaxis().SetTimeDisplay(1)
      Smontmultig1.GetXaxis().SetTimeFormat("#splitline{%y-%m-%d}{%H:%M:%S}%F1970-01-01 00:00:00")
      Smontmultig1.GetXaxis().SetLabelOffset(0.025)
      Smontmultig1.GetXaxis().SetLabelSize(fontSize)
      Smontmultig1.GetYaxis().SetLabelSize(fontSize)

      Isontmultig1.GetXaxis().SetRangeUser( minDateIsonMultig, maxDateIsonMultig )
      Isontmultig1.GetYaxis().SetRangeUser( 0.05, 1.5 )
      Isontmultig1.GetXaxis().SetTimeDisplay(1)
      Isontmultig1.GetXaxis().SetTimeFormat("#splitline{%y-%m-%d}{%H:%M:%S}%F1970-01-01 00:00:00")
      Isontmultig1.GetXaxis().SetLabelOffset(0.025)
      Isontmultig1.GetXaxis().SetLabelSize(fontSize)
      Isontmultig1.GetYaxis().SetLabelSize(fontSize)

      Temptmultig1.GetXaxis().SetRangeUser( minDateTempMultig, maxDateTempMultig )
      Temptmultig1.GetXaxis().SetTimeDisplay(1)
      Temptmultig1.GetXaxis().SetTimeFormat("#splitline{%y-%m-%d}{%H:%M:%S}%F1970-01-01 00:00:00")
      Temptmultig1.GetXaxis().SetLabelOffset(0.025)
      Temptmultig1.GetXaxis().SetLabelSize(fontSize)
      Temptmultig1.GetYaxis().SetLabelSize(fontSize)

      Imontmultig1.Write()
      Vmontmultig1.Write()
      Smontmultig1.Write()
      Isontmultig1.Write()
      Temptmultig1.Write()

      #canvas dimensions
      canW = 800;
      canH = 800;
      canH_ref = 800;
      canW_ref = 800;

      #references for T, B, L, R
      TopMar = 0.12*canH_ref;
      BotMar = 0.17*canH_ref;
      LeftMar = 0.15*canW_ref;
      RightMar = 0.12*canW_ref;

      #declare a TPaveText for CMS Prelimiary
      cmsPrel = ROOT.TPaveText(0.13,0.88,0.355,0.96,"brNDC");
      cmsPrel.AddText("CMS Preliminary");
      cmsPrel.SetTextAlign(12);
      cmsPrel.SetShadowColor(transWhite);
      cmsPrel.SetFillColor(transWhite);
      cmsPrel.SetLineColor(transWhite);
      cmsPrel.SetLineColor(transWhite);

      #declare a TPaveText for CMS xAxis title
      xAxisLab = ROOT.TPaveText(0.6,0.88,0.9,0.92,"brNDC");
      xAxisLab.AddText("Date(YY-MM-DD) / Time(hh:mm:ss)");
      xAxisLab.SetTextAlign(12);
      xAxisLab.SetShadowColor(transWhite);
      xAxisLab.SetFillColor(transWhite);
      xAxisLab.SetLineColor(transWhite);
      xAxisLab.SetLineColor(transWhite);

      #declare three canvas for multigraphs: without canvas I cannot put the legend
      imonCanvas = ROOT.TCanvas("ImonCanvasAllChannels", chamberList[chIdx], 50, 50, 800, 800 )
      imonCanvas.SetLeftMargin( LeftMar/canW )
      imonCanvas.SetRightMargin( RightMar/canW )
      imonCanvas.SetTopMargin( TopMar/canH )
      imonCanvas.SetBottomMargin( BotMar/canH )
      Imontmultig1.Draw("AP")
      legendMultiImon.Draw("SAME")
      cmsPrel.Draw("NB")
      xAxisLab.Draw("NB")
      imonCanvas.Write()

      vmonCanvas = ROOT.TCanvas("VmonCanvasAllChannels", chamberList[chIdx], 50, 50, 800, 800 )
      vmonCanvas.SetLeftMargin( LeftMar/canW )
      vmonCanvas.SetRightMargin( RightMar/canW )
      vmonCanvas.SetTopMargin( TopMar/canH )
      vmonCanvas.SetBottomMargin( BotMar/canH )
      Vmontmultig1.Draw("AP")
      legendMultiVmon.Draw("SAME")
      cmsPrel.Draw("NB")
      xAxisLab.Draw("NB")
      vmonCanvas.Write()

      smonCanvas = ROOT.TCanvas("SmonCanvasAllChannels", chamberList[chIdx], 50, 50, 800, 800 )
      smonCanvas.SetLeftMargin( LeftMar/canW )
      smonCanvas.SetRightMargin( RightMar/canW )
      smonCanvas.SetTopMargin( TopMar/canH )
      smonCanvas.SetBottomMargin( BotMar/canH )
      Smontmultig1.Draw("AP")
      legendMultiImon.Draw("SAME")
      cmsPrel.Draw("NB")
      xAxisLab.Draw("NB")
      smonCanvas.Write()

      #SAVE MULTIGRAPHS
      chamberNameNoSlash = chamberList[chIdx].replace("/","_")

      if args.save: imonCanvas.SaveAs(dirStringSave+"/Imon_"+chamberNameNoSlash+"_AllElectrodes.png")
      if args.save: vmonCanvas.SaveAs(dirStringSave+"/Vmon_"+chamberNameNoSlash+"_AllElectrodes.png")


      del(Imontmultig1)
      del(Vmontmultig1)
      del(Smontmultig1)
      del(imonCanvas)
      del(vmonCanvas)
      del(smonCanvas)


   #end of loop over chambers
   #at column 3 we are inside the main
   f1.Close()

   print('\n-------------------------Output--------------------------------')
   print((fileName+ " has been created."))
   verboseprint("It is organised in directories: to change directory use DIRNAME->cd()")
   verboseprint('To draw a TH1 or a TGraph: OBJNAME->Draw()')
   verboseprint('To scan the TTree use for example:\nHV_StatusTree2_2_Top_G3Bot->Scan("","","colsize=26")')
   print("ALL MONITOR TIMES ARE IN UTC, DCS TIMES ARE IN CET")

if __name__ == '__main__':
   main()

