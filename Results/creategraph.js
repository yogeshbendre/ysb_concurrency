var data = [];
var vmarray = [];
var nicarray = [];
var dsarray = [];

function load() {

    //console.log(testdata)

    vmresult = testdata.vm ;

    for (var vmname in vmresult) {   
        vmarray.push(vmname)     
        vmDatas = vmresult[vmname]
        vmDatas.forEach(element => {
            data.push({ date: new Date(element["Time"]), [vmname]: element["Progress"] });
        });

    }

    nicresult = testdata.nic ;
    //console.log(nicresult)
    for (var hostname in nicresult){
        nicarray.push(hostname)
        nicDatas = nicresult[hostname]
        nicDatas.forEach(element => {            
            data.push({ date: new Date(element["Time"]), [hostname]: element["Bandwidth"] });
        });

    }

    dsresult = testdata.datastore
    for (var ds in dsresult){
        var readKey = ds + "Read"
        var writeKey = ds + "Write"
        dsarray.push(ds)
        dsDatas = dsresult[ds]
        dsDatas.forEach(element => {            
            data.push({ date: new Date(element["Time"]), [readKey]: element["Read"] , [writeKey] : element["Write"]});
        });

    }



}

