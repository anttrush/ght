import pymysql
import os
db = pymysql.connect("192.168.3.123", "ght", "ght", "github")
cursor = db.cursor()
cursor.execute("SELECT VERSION()")
data = cursor.fetchone()
print ("Database version : %s " % data)

class Project(object):
    def __init__(self, id):
        self.proj_id = id
        # get name from mysql, don't know how to get star
        sql = 'select name from projects where id=' + str(self.proj_id)
        cursor.execute(sql)
        res = cursor.fetchall()
        self.name = res[0][0]

    def setProjStar(self, star):
        self.star = star

    def setProjDir(self, repdir):
        self.proj_dir = os.path.join(repdir, self.name)

    def setAvgVio(self, avgVio): # use this to replace v0 param
        self.AvgVio = avgVio

class Developer(object):
    @staticmethod
    def getAllIdFromMysql():
        dbSO_GH = pymysql.connect("192.168.3.123", "root", "123456", "SO_GH")
        cursorSO_GH = dbSO_GH.cursor()
        sql = 'select github_user_id from stackoverflow_github_users'
        cursorSO_GH.execute(sql)
        res = cursorSO_GH.fetchall()
        devList = []
        for idres in res:
            devList.append(int(idres[0]))
        # for debug
        print(len(devList), devList[:5])
        return devList

    def __init__(self, id):
        self.dev_id = id
        sql = 'select login from users where id=' + str(self.dev_id)
        cursor.execute(sql)
        res = cursor.fetchall()
        self.name = res[0][0]
        self.score = Violation.EmptyVioClassDict.copy()
        self.fileNumber = 0

    def isMemberOf(self, proj_id):
        sql = 'select * from project_members where repo_id=' + str(proj_id) + ' and user_id=' + str(self.dev_id)
        cursor.execute(sql)
        res = cursor.fetchall()
        if res:
            return True
        else:
            return False

class Commit(object):
    def __init__(self, id):
        self.com_id = id
        self.vioFileList = []
        self.score = Violation.EmptyVioClassDict.copy()
        sql = 'select author_id, sha from commits where id=' + str(self.com_id)
        cursor.execute(sql)
        res = cursor.fetchall()
        if res:
            self.dev_id = int(res[0][0])
            self.sha = res[0][1]
        else:
            print("CommitNotFoundException")

    def hasParent(self):
        # go into mysql and find self.parent
        sql = 'select parent_id from commit_parents where commit_id=' + str(self.com_id)
        cursor.execute(sql)
        res = cursor.fetchall()
        if not res:
            self.parent = None
            return False
        elif len(res) == 1:
            # new a commit and set self.parent
            self.parent = Commit(int(res[0][0]))
            return True
        else:
            # select real parent of a PR commit
            self.parent = Commit(int(res[1][0]))
            return True

    def getParent(self):
        if self.parent == None:
            self.hasParent()
        return self.parent

class Myfile(object):
    def __init__(self, filefullname, violist, loc, level):
        self.fileFullName = filefullname
        self.vioList = violist
        self.LOC = loc
        self.score = Violation.EmptyVioClassDict.copy()
        self.level = level

class Violation(object):
    EmptyVioClassDict = {'Best Practices':0, 'Code Style':0,'Design':0, 'Documentation':0,'Error Prone':0, 'Multithreading':0,'Performance':0, 'Security':0}
    def __init__(self, vioname, vioclass, priority):
        self.vioName = vioname
        self.vioClass = vioclass
        self.priority = priority

class Viopresent(object):
    def __init__(self, vioname):
        self.vioName = vioname
        self.preList = [] # [[com_id, times], ...]
        # for counting importance according to "one-shot" theory
        self.distime = 0 # disapear times
        self.pretime = 0 # present times
