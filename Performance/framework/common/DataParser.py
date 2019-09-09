__author__ = 'Smruti P Mohanty'
"""
Company : VMWare Inc.
                                Apache License
                           Version 2.0, January 2004
                        http://www.apache.org/licenses/
"""
import re

#pattern = "^(\w+)-(.)-(\w+)=(.*)$"
datamatch = re.compile("""^(\w+)    # Test Name
                        -(.+)-       #Instance
                        (\w+)       #Variable
                        =
                        (.*)$       #Actual Data """,re.X)




def DataGenerator(filename,testname):

    final_data = {}
    instance_dict = {}
    common_instance = {}
    instance_data = {}
    with open(filename,"r") as f:
        lines = f.readlines()
        for line in lines:
            if line.startswith(testname):
                result = datamatch.match(line)
                if result:
                    testname = result.group(1)
                    test_instance = result.group(2)
                    test_variable = result.group(3)
                    test_data = result.group(4)
                    #print "Test: %s  Instance: %s Variable: %s Data %s"%(testname,test_instance,test_variable,test_data)
                    if test_instance == "*":
                        common_instance[test_variable] = test_data
                    else:
                        instance_dict[test_instance] = instance_dict.get(test_instance,"") + "," + test_variable + ":" + test_data


        for instance in instance_dict:
            instance_data[instance] = dict((x,y) for x,y in (item.split(":") for item in instance_dict[instance].strip(",").split(",")))





        final_data[testname] = {"common":common_instance,"instance":instance_data}

    return final_data,len(instance_dict)





#data = DataGenerator("vmotion.txt","HLMMigration")


#print json.dumps(data)






