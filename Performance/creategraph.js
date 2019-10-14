var data = [];
var vmarray = [];
var nicarray = [];
var dsarray = [];
var memarray = [];
var diskarray = [];

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
        var sent = hostname + "sent";
        var got = hostname + "got" ;
        nicarray.push(hostname)
        nicDatas = nicresult[hostname]
        nicDatas.forEach(element => {
            data.push({ date: new Date(element["Time"]), [hostname]: element["Bandwidth"] ,[sent]: element["Transmitted"], [got]: element["Received"]});
        });

    }

    dsresult = testdata.datastore
    for (var ds in dsresult){
        var readLatencyKey = ds + "ReadLatency"
        var writeLatencyKey = ds + "WriteLatency"
        var readKey = ds + "Read"
        var writeKey = ds + "Write"
        dsarray.push(ds)
        dsDatas = dsresult[ds]
        dsDatas.forEach(element => {
            data.push({ date: new Date(element["Time"]), [readLatencyKey]: element["ReadLatency"] ,
            [writeLatencyKey] : element["WriteLatency"], [readKey]:element["Read"],[writeKey]:element["Write"]});
        });

    }

    diskresult = testdata.disk
    for (var ds in diskresult){
        var totalLatencyKey = ds + "Latency"

        var readKey = ds + "Read"
        var writeKey = ds + "Write"
        diskarray.push(ds)
        diskDatas = diskresult[ds]
        diskDatas.forEach(element => {
            data.push({ date: new Date(element["Time"]), [totalLatencyKey]: element["TotalLatency"] ,
             [readKey]:element["Read"],[writeKey]:element["Write"]});
        });

    }

    memresults = testdata.mem
    for (var hsname in memresults) {
        var memoryusage = hsname + "memusage"
        memarray.push(hsname)
        memDatas = memresults[hsname]
        //console.log(memresults[hsname])
        memDatas.forEach(element => {
            data.push({ date: new Date(element["Time"]), [memoryusage]: element["Usage"] });
        });

    }




}

