__all__ = ["fun1", "pkt"]

def fun1():
    print("test")

class pkt():
    def encode(self,payload):
        # Note: versionToken, messageBus, and currentRole need to be passed or imported
        from main import versionToken, messageBus, currentRole
        result=versionToken+","
        result+="{},".format(messageBus)
        result+="{},".format(currentRole) #from
        result+=str(payload).replace(",","_coma_")
        return result

    def decode(self,OTAtext,validOriginRoles):
        # Note: versionToken, messageBus, currentRole, and errorHandler need to be passed or imported
        from main import versionToken, messageBus, currentRole, errorHandler
        resultValid=False
        resultDesc=""
        resultFrom=""
        resultPayload=""
        parts=OTAtext.split(",")
        try:
            if parts[0]!=versionToken:
                resultDesc="parts[versionToken]={}, expected:{}".format(parts[0],versionToken)
                errorHandler(halt=False,errorCode=9,desc=resultDesc)
                raise ValueError
            if parts[1]!=str(messageBus):
                resultDesc="parts[messageBus]:{}, expected:{}".format(parts[1],str(messageBus))
                #errorHandler(halt=False,errorCode=9,desc=resultDesc) #too chatty
                raise ValueError
            if parts[2] in validOriginRoles:
                resultFrom=parts[2]
            else:
                resultDesc="parts[originRoles]: {} not in '{}'".format(parts[2],str(validOriginRoles))
                if parts[2] == currentRole:
                    errorHandler(halt=True,errorCode=1,desc="Role cloning: {}".format(currentRole))
                raise ValueError
            resultPayload=parts[3].replace("_coma_",",")
            resultValid=True
            resultDesc="OK"
        except Exception as e:
            print("DEBUG:pkt.decode:e;{},desc:{},OTAtext:'{}'".format(e,resultDesc,OTAtext))
        return resultValid,resultDesc,resultFrom,resultPayload


