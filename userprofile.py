from myclass import *
import os
import csv
import math
import logging
logging.basicConfig(level = logging.CRITICAL,format = '%(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
PMDcommand = r'D:\pmd-bin-6.4.0\bin\pmd '
REPDIR = r'D:\CodeRepertory\PJCY'
RESDIR = r'D:\科研\CodeQualityAnalysis\CodeAnalysis\PMD'
RULEDIR = r'D:\pmd-bin-6.4.0\bin\myRuleSet.xml'
CACHEDIR = r'D:\科研\CodeQualityAnalysis\CodeAnalysis\PMD\cache'

projidlist1 = [2981995, 17302594, 3048542,12277769,29292799,10425739,4876188,11474326] #[2981995, 17302594, 3048542,12277769,29292799,10425739,4876188,11474326]    name=["butterknife", "elasticsearch"]
projstarList = [21375, 31978, 133,163,135,9500,19900,31700] # [21375, 31978, 133,163,135,9500,19900,31700]
c0List1 = [407225743, 407436642,269793621,318742615,402811447,407322377,407250374,406815380] # [407225743, 407436642,269793621,318742615,402811447,407322377,407250374,406815380]   sha=[]
devIds = [49049, 165882, 2632242, 4589144, 75625, 4307816, 10844712, 64600, 114374, 199939, 1891264, 896, 4998106, 7924529, 436017]
# [49049, 165882, 2632242, 4589144, 75625, 4307816, 10844712, 64600, 114374, 199939, 1891264, 896, 4998106, 7924529, 436017]
# login=[]
COMMITWINDOW = 30

def getProjList():
    projList = []
    for id in projidlist1:
        projList.append(Project(id))
        projList[-1].setProjDir(REPDIR)
        projList[-1].setProjStar(projstarList.pop(0))
    return projList

def getDevList(source='local'):
    devList = []
    if source == 'local':
        for id in devIds:
            devList.append(Developer(id))
    elif source == 'mysql':
        devList = Developer.getAllIdFromMysql()
    return devList

def pmdAnalysis(proj, ci):
    # let git reset to ci, use PMD to analysis and gen <ci.com_id>.csv file.
    # popen has sync problem -- use .read() to sync
    os.popen('cd /d ' + proj.proj_dir + '&& git reset %s && git checkout -- "*.java"' % ci.sha).read()
    # ./run.sh pmd -d /home/act/elasticsearch -f csv -R ./myRuleSet.xml -language java -r /home/act/pmdresults/elasticsearch.csv -cache /home/act/pmdresults/cache
    os.popen('cd /d ' + proj.proj_dir + '&& git reset %s && git checkout -- "*.java"' % ci.sha).read()
    os.popen(PMDcommand + '-d ' + proj.proj_dir + ' -f csv -R ' + RULEDIR + ' -language java -r ' + RESDIR + '/' + str(ci.com_id) + '.csv -cache ' + CACHEDIR + str(proj.proj_id), 'r').read()

def pmdAnalysisDiff(proj, ci, cj):
    # get Commit changing file by git diff --name-only cj ci // cj = ci.parent()
    # let git reset to cj, use PMD to analysis and gen <cj.com_id>.csv file.
    os.popen('cd /d ' + proj.proj_dir + '&& git reset %s && git checkout -- "*.java"' % cj.sha).read()
    diffres = os.popen('cd /d ' + proj.proj_dir + '&& git diff --name-only %s %s' % (cj.sha, ci.sha)).read()
    with open(os.path.join(RESDIR, str(cj.com_id)+"ChangedFile.txt"), 'w') as f:
        if diffres:
            diffFiles = diffres.strip().split('\n')
            if diffFiles[0].endswith(".java"):
                f.write(os.path.join(proj.proj_dir, diffFiles[0]))
            else:
                return 'No diff'
            for i in range(1,len(diffFiles)):
                if diffFiles[i].endswith(".java"):
                    f.write(',' + os.path.join(proj.proj_dir, diffFiles[i]))
        else: # return no diff to help comList not append cj
            return 'No diff'
    # pmd -filelist
    # ./run.sh pmd -filelist /xxx/xxx -f csv -R ./myRuleSet.xml -language java -r /home/act/pmdresults/elasticsearch.csv -cache /home/act/pmdresults/cache
    # pmd -filelist D:\CodeRepertory\PJCY\butterknife\testfilelist.txt -f csv -R ./myRuleSet.xml -language java -r D:\科研\CodeQualityAnalysis\CodeAnalysis\PMD\butterknife.csv -cache D:\科研\CodeQualityAnalysis\CodeAnalysis\PMD\cache2981995
    os.popen(PMDcommand + '-filelist ' + os.path.join(RESDIR, str(cj.com_id)+"ChangedFile.txt") + ' -f csv -R ' + RULEDIR + ' -language java -r ' + RESDIR + '/' + str(cj.com_id) + '.csv -cache ' + CACHEDIR + str(proj.proj_id), 'r').read()
    return 'Well Done'

def analysisCommit(proj, ci, viopreDict):
    # analysis ci with PMD result file.
    # get ci.vioFileList
    with open(os.path.join(RESDIR, str(ci.com_id) + '.csv'), 'r') as f:
        res = csv.DictReader(f)
        filetmp = Myfile('', [], 0,1)
        for row in res:
            # "Problem","Package","File","Priority","Line","Description","Rule set","Rule"
            # one row one vio, build viotmp and update file
            if row['File'] != filetmp.fileFullName:
                ci.vioFileList.append(filetmp)
                # can't get LOC safely(gbk codec) and efficiently(file read)
                # can't get level
                # should do understand first to get import times(level) and LOC, store in a res.csv and load when proj analysis begin.
                filetmp = Myfile(row['File'], [], 100,1)
                # get LOC
                try:
                    with open(os.path.join(os.path.join(proj.proj_dir, filetmp.fileFullName)), 'r') as f:
                        LOC = len(f.readline())
                        filetmp.LOC = LOC
                except Exception as e:
                    # gbk  error
                    filetmp.LOC = 0
            viotmp = Violation(row['Rule'], row['Rule set'], int(row['Priority']))
            # update viopreDict
            if viotmp.vioName not in viopreDict:
                viopretmp = Viopresent(viotmp.vioName)
                viopretmp.preList = [[ci.com_id, 1]]
                viopreDict[viotmp.vioName] = viopretmp
            else:
                preListtmp = viopreDict[viotmp.vioName].preList
                if preListtmp[-1][0] == ci.com_id:
                    viopreDict[viotmp.vioName].preList[-1][1] += 1
                else:
                    viopreDict[viotmp.vioName].preList.append([ci.com_id, 1])
            filetmp.vioList.append(viotmp)
        ci.vioFileList.append(filetmp)
        ci.vioFileList.pop(0) # first empty filetmp

def getImpVios(viopreDict):
    # for each vio kind, get importance, compare and select import vios
    importantVios = []
    impVioName = []
    for vioName in viopreDict.keys():
        viopre = viopreDict[vioName]
        prelist = viopre.preList
        distime = 0
        pretime = prelist[-1][1]
        for i in range(len(prelist)-1):
            # prelist[i+1] is prelist[i].parent
            if prelist[i][1] < prelist[i+1][1]:
                distime += prelist[i+1][1] - prelist[i][1]
                # for debug
                logger.info("find one-shot vio[commit:%d, vio:%s, dispre:%d]" %(prelist[i][0],vioName,prelist[i+1][1] - prelist[i][1]))
            elif prelist[i][1] > prelist[i+1][1]:
                pretime += prelist[i][1] - prelist[i+1][1]
        viopre.distime = distime
        viopre.pretime = pretime
        importantVios.append(viopre)
    importantVios.sort(key=lambda viopre: viopre.distime / viopre.pretime,reverse=True)
    importantVios = importantVios[:int(len(importantVios) * 0.3) + 1]
    for i in range(len(importantVios)):
        if importantVios[i].distime == 0:
            importantVios = importantVios[:i]
            break
        else:
            impVioName.append(importantVios[i].vioName)
    # for debug
    # for viopre in importantVios:
    #    if viopre.distime != 0:
    #        logger.info(viopre.vioName, viopre.distime, viopre.pretime)
    # logger.info("importantVios len: ", len(importantVios), "; first impVio: ", importantVios[0].vioName)
    # return importantVios
    return impVioName

def getAvgScore(c0, importantVios, proj):
    for file in c0.vioFileList:
        if file.LOC == 0:
            continue
        for vio in file.vioList:
            if vio.vioName in importantVios:
                file.score[vio.vioClass] += 1
        for key in file.score:
            file.score[key] /= file.LOC
            c0.score[key] += file.score[key]
    for key in c0.score:
        c0.score[key] /= len(c0.vioFileList)
    return c0.score.copy()

def getDevScore(comList, importantVios, proj, devList, v0=Violation.EmptyVioClassDict):
    # loop comList to accumulate dev.score
    for com in comList:
        # get dev of the commit
        dev = None
        for d in devList:
            if d.dev_id == com.dev_id:
                dev = d
                break
        if not dev:
            continue
        logger.info(str(com.com_id) + " -- " + dev.name)
        for file in com.vioFileList:
            if file.LOC == 0:
                continue
            # count every important vio to file score
            for vio in file.vioList:
                # for viopre in importantVios:
                    # if vio.vioName == viopre.vioName:
                if vio.vioName in importantVios:
                    # score formula
                    file.score[vio.vioClass] += 1
                    # com.score[vio.vioClass] += 1
                    # break
            # count every file score to dev score
            for key in file.score:
                file.score[key] /= file.LOC # V
                file.score[key] = 150 / (file.score[key] + 1.5 * v0[key] + 1) # S = 150 / (V+1.5V0)
                dev.score[key] = (dev.score[key] * dev.fileNumber + file.score[key] * file.level * math.log10(proj.star + 10) / file.LOC) / (dev.fileNumber + 1)
            dev.fileNumber += 1

def main():
    devList = getDevList()
    projList =  getProjList()
    for proj in projList:
        logger.critical("begin analysis project %s" %proj.name)

        # viopreList = [] # list of Viopresent
        viopreDict = {} # dict of Viopresent
        comList = [] # list of Commit

        # get the last commit ci, PMD analysis, initial comList
        c0 = Commit(c0List1.pop(0))
        pmdAnalysis(proj, c0)
        ci = c0
        # analysisCommit(proj, ci, viopreDict)
        # comList.append(ci)
        # above is the way see c0 and the others the same; belong is the way use c0 to calculate S0
        # loop to get father commit, analysis, update comList
        looptime = 0
        while ci.hasParent() and looptime < COMMITWINDOW:
            cj = ci.getParent()
            # pmdAnalysis(proj, cj)
            diffSig = pmdAnalysisDiff(proj, ci, cj)
            if diffSig == 'Well Done':
                analysisCommit(proj, cj, viopreDict)
                comList.append(cj)
            ci = cj
            looptime += 1  # end of cij loop

        # get important vios(according to one-shot theory)
        importantVios = getImpVios(viopreDict)
        # get v0
        analysisCommit(proj, c0, {})
        v0 = getAvgScore(c0, importantVios, proj)
        # get dev score
        getDevScore(comList, importantVios, proj, devList, v0=v0)
        # for debug
        logger.info(proj.name + ", loop: " + str(looptime))
    # print dev profile
    for dev in devList:
        print(dev.dev_id, dev.name, dev.score)

main()