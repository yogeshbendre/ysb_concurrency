__author__ = 'Smruti P Mohanty'
"""
Company : VMWare Inc.
                                Apache License
                           Version 2.0, January 2004
                        http://www.apache.org/licenses/
"""
from framework.common import TestConstants as tc
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine
from sqlalchemy.orm import relationship, sessionmaker
import plotly
from plotly.tools import make_subplots
from framework.common.TaskAnalyzer import VMStats
from framework.common.EsxStats import NetworkData, DSData
import datetime
import plotly.graph_objs as go
from collections import defaultdict, namedtuple
import traceback
import json
import os
import webbrowser as wb
import time

Base = declarative_base()

final_data = {}
vm_data = defaultdict(list)
host_ds = defaultdict(list)
host_nic = defaultdict(list)

html_data="""
<!doctype html>
<html lang="en">



<head>

    <style>
        #chartdiv {
            width: 100%%;
            height: 1800px;
        }
    </style>

    <script src="https://www.amcharts.com/lib/4/core.js"></script>
    <script src="https://www.amcharts.com/lib/4/charts.js"></script>
    <script src="https://www.amcharts.com/lib/4/themes/animated.js"></script>

    <script type="text/javascript" src="%(datafile)s"></script>
    <script type="text/javascript" src="creategraph.js"></script>
    <script type="text/javascript">
        function draw() {
            //console.log(data)
            am4core.ready(function () {
                // Themes begin
                var titlearray = []
                var indx = 1
                am4core.useTheme(am4themes_animated);
                // Themes end



                var chart = am4core.create("chartdiv", am4charts.XYChart);

                chart.colors.list = [
                am4core.color("#CD5C5C"),am4core.color("#FF9900"),am4core.color("#0066CC"),am4core.color("#CCCC00"),
                am4core.color("#669933"),am4core.color("#CCCCFF"),am4core.color("#CC9900"),am4core.color("#999966"),
                am4core.color("#CC99CC"),am4core.color("#FF9999"),am4core.color("#CC6600"),am4core.color("#CC66CC"),
                am4core.color("#0066FF"),am4core.color("#FF6699"),am4core.color("#CC3300"),am4core.color("#CC33CC"),
                am4core.color("#99CC66"),am4core.color("#FF3399"),am4core.color("#66CCCC"),am4core.color("#669999"),
                am4core.color("#CC0000"),am4core.color("#660000"),am4core.color("#3366CC"),am4core.color("#6600CC"),
                am4core.color("#663300"),am4core.color("#993300"),am4core.color("#666600"),am4core.color("#666699"),
                am4core.color("#6666FF"),am4core.color("#669900"),am4core.color("#003333")
                ];
                colorindx = 0

                var scrollbarX = new am4charts.XYChartScrollbar();
                var interfaceColors = new am4core.InterfaceColorSet();

                chart.data = data;
                // the following line makes value axes to be arranged vertically.
                chart.leftAxesContainer.layout = "vertical";

                var dateAxis = chart.xAxes.push(new am4charts.DateAxis());
                dateAxis.renderer.grid.template.location = 0;
                dateAxis.renderer.ticks.template.length = 8;
                dateAxis.renderer.ticks.template.strokeOpacity = 0.1;
                dateAxis.renderer.grid.template.disabled = true;
                dateAxis.renderer.ticks.template.disabled = false;
                dateAxis.renderer.ticks.template.strokeOpacity = 0.2;

                var valueAxis = chart.yAxes.push(new am4charts.ValueAxis());
                valueAxis.tooltip.disabled = false;
                valueAxis.title.text = "Progress %%";
                valueAxis.zIndex = 1;
                valueAxis.renderer.baseGrid.disabled = true;

                // Set up axis
                valueAxis.renderer.inside = true;
                valueAxis.height = am4core.percent(60);
                valueAxis.renderer.labels.template.verticalCenter = "bottom";
                valueAxis.renderer.labels.template.padding(2, 2, 2, 2);
                //valueAxis.renderer.maxLabelPosition = 0.95;
                valueAxis.renderer.fontSize = "0.8em"

                // uncomment these lines to fill plot area of this axis with some color
                valueAxis.renderer.gridContainer.background.fill = interfaceColors.getFor("alternativeBackground");
                valueAxis.renderer.gridContainer.background.fillOpacity = 0.05;




                //Iterate on all VMs and Plot
                vmarray.forEach(element => {

                    var series0 = chart.series.push(new am4charts.LineSeries());
                    series0.dataFields.dateX = "date";
                    series0.dataFields.valueY = [element];
                    series0.fill = chart.colors.getIndex(colorindx);
                    colorindx = colorindx +1 ;
                    //series.tooltipText = "{valueY.value}";
                    var bullet = series0.bullets.push(new am4charts.CircleBullet());

                    bullet.tooltipText = "{valueY.value}"
                    series0.name = [element];


                    scrollbarX.series.push(series0);


                });

                titlearray.push({ "Axes": valueAxis, "Name": "VM-Data" })



                nicarray.forEach(element => {
                    var axisName = 'valueAxis' + indx
                    indx = indx + 1;

                    //console.log(axisName)

                    window[axisName] = chart.yAxes.push(new am4charts.ValueAxis());
                    window[axisName].tooltip.disabled = true;

                    // this makes gap between panels
                    window[axisName].marginTop = 30;
                    window[axisName].renderer.baseGrid.disabled = true;
                    window[axisName].renderer.inside = true;
                    window[axisName].height = am4core.percent(30);
                    window[axisName].zIndex = 10
                    window[axisName].renderer.labels.template.verticalCenter = "bottom";
                    window[axisName].renderer.labels.template.padding(2, 2, 2, 2);
                    //valueAxis2.renderer.maxLabelPosition = 0.95;
                    window[axisName].renderer.fontSize = "0.8em"
                    window[axisName].title.text = "KBps";

                    // uncomment these lines to fill plot area of this axis with some color
                    window[axisName].renderer.gridContainer.background.fill = interfaceColors.getFor("alternativeBackground");
                    window[axisName].renderer.gridContainer.background.fillOpacity = 0.05;

                    /*

                    var series1 = chart.series.push(new am4charts.ColumnSeries());

                    series1.columns.template.width = am4core.percent(50);
                    series1.dataFields.dateX = "date";
                    series1.dataFields.valueY = [element];

                    series1.yAxis = window[axisName];
                    series1.columns.template.tooltipText = "{valueY.value}";
                    series1.name = [element] + "-" + testdata.nic[element][0].vnic;
                    */

                    var series1 = chart.series.push(new am4charts.LineSeries());
                    series1.dataFields.dateX = "date";
                    series1.dataFields.valueY = [element];
                    series1.yAxis = window[axisName];

                    series1.fill = chart.colors.getIndex(colorindx);
                    colorindx = colorindx +1 ;
                    //series.tooltipText = "{valueY.value}";
                    var bullet = series1.bullets.push(new am4charts.CircleBullet());

                    bullet.tooltipText = "{valueY.value}"
                    series1.name = [element] + "-" + testdata.nic[element][0].vnic;;

                    series1.fill = chart.colors.getIndex(colorindx);
                    colorindx = colorindx +1 ;



                    scrollbarX.series.push(series1);


                    titlearray.push({ "Axes": window[axisName], "Name": [element] + " : " + testdata.nic[element][0].vnic })




                });






                //Render Datastore



                dsarray.forEach(element => {
                    //console.log(element)
                    var axisName = 'valueAxis' + indx
                    indx = indx + 1;

                    window[axisName] = chart.yAxes.push(new am4charts.ValueAxis());
                    window[axisName].tooltip.disabled = true;

                    // this makes gap between panels
                    window[axisName].marginTop = 30;
                    window[axisName].renderer.baseGrid.disabled = true;
                    window[axisName].renderer.inside = true;
                    window[axisName].height = am4core.percent(30);
                    window[axisName].zIndex = 10
                    window[axisName].renderer.labels.template.verticalCenter = "bottom";
                    window[axisName].renderer.labels.template.padding(2, 2, 2, 2);
                    //valueAxis2.renderer.maxLabelPosition = 0.95;
                    window[axisName].renderer.fontSize = "0.8em"
                    window[axisName].title.text = "ms";

                    // uncomment these lines to fill plot area of this axis with some color
                    window[axisName].renderer.gridContainer.background.fill = interfaceColors.getFor("alternativeBackground");
                    window[axisName].renderer.gridContainer.background.fillOpacity = 0.05;


                    var rKey = element + "Read"
                    var wKey = element + "Write"



                    var series2 = chart.series.push(new am4charts.LineSeries());
                    series2.yAxis = window[axisName];
                    series2.dataFields.dateX = "date";
                    series2.dataFields.valueY = [rKey];
                    series2.fill = chart.colors.getIndex(colorindx);
                    colorindx = colorindx +1 ;

                    var bullet = series2.bullets.push(new am4charts.CircleBullet());
                    bullet.tooltipText = "{valueY.value}"
                    series2.name = [element] + "ReadLatency";                  

                    scrollbarX.series.push(series2);



                    var series3 = chart.series.push(new am4charts.LineSeries());
                    series3.yAxis = window[axisName];
                    series3.dataFields.dateX = "date";
                    series3.dataFields.valueY = [rKey];
                    series3.fill = chart.colors.getIndex(colorindx);
                    colorindx = colorindx +1 ;

                    var bullet = series3.bullets.push(new am4charts.CircleBullet());
                    bullet.tooltipText = "{valueY.value}"
                    series3.name = [element] + "WriteLatency";

                    scrollbarX.series.push(series3);

                    titlearray.push({ "Axes": window[axisName], "Name": [element] + " : " + "DataStore Latency" })




                });




                chart.legend = new am4charts.Legend();

                // Set Title for Subplots


                title_indx = 1
                titlearray.forEach(element => {
                    //var title_axis = element["Axes"];
                    var title_name = element["Name"];
                    console.log(element["Axes"].title.text)
                    var title2 = "title" + title_indx
                    title_indx = title_indx + 1;
                    window[title2] = element["Axes"].renderer.gridContainer.createChild(am4core.Label);
                    window[title2].text = "[bold]" + title_name;
                    //window[title2].fill = series.fill;
                    window[title2].isMeasured = false;
                    window[title2].y = 15;
                    window[title2].x = am4core.percent(50);
                    window[title2].align = "center";
                    window[title2].textAlign = "middle";

                }
                );



                chart.cursor = new am4charts.XYCursor();
                chart.cursor.xAxis = dateAxis;
                scrollbarX.marginBottom = 20;
                chart.scrollbarX = scrollbarX;


                // Enable export
                chart.exporting.menu = new am4core.ExportMenu();
                chart.exporting.menu.align = "left";
                chart.exporting.menu.verticalAlign = "top";


            }); // end am4core.ready()

        }

    </script>

</head>


<body onload="load();draw();">
    <div id="chartdiv"> </div>
</body>

</html>
"""

only_vm_html = """
<!doctype html>
<html lang="en">



<head>

    <style>
        #chartdiv {
            width: 100%%;
            height: 900px;
        }
    </style>

    <script src="https://www.amcharts.com/lib/4/core.js"></script>
    <script src="https://www.amcharts.com/lib/4/charts.js"></script>
    <script src="https://www.amcharts.com/lib/4/themes/animated.js"></script>

    <script type="text/javascript" src="%(datafile)s"></script>
    <script type="text/javascript" src="creategraph.js"></script>
    <script type="text/javascript">
        function draw() {
            //console.log(data)
            am4core.ready(function () {
                // Themes begin
                var titlearray = []
                var indx = 1
                am4core.useTheme(am4themes_animated);
                // Themes end



                var chart = am4core.create("chartdiv", am4charts.XYChart);

                chart.colors.list = [
                    am4core.color("#3498DB"),
                    am4core.color("#CD5C5C"), am4core.color("#FF9900"), am4core.color("#0066CC"), am4core.color("#CCCC00"),
                    am4core.color("#669933"), am4core.color("#CCCCFF"), am4core.color("#CC9900"), am4core.color("#999966"),
                    am4core.color("#CC99CC"), am4core.color("#FF9999"), am4core.color("#CC6600"), am4core.color("#CC66CC"),
                    am4core.color("#0066FF"), am4core.color("#FF6699"), am4core.color("#CC3300"), am4core.color("#CC33CC"),
                    am4core.color("#99CC66"), am4core.color("#FF3399"), am4core.color("#66CCCC"), am4core.color("#669999"),
                    am4core.color("#CC0000"), am4core.color("#660000"), am4core.color("#3366CC"), am4core.color("#6600CC"),
                    am4core.color("#663300"), am4core.color("#993300"), am4core.color("#666600"), am4core.color("#666699"),
                    am4core.color("#6666FF"), am4core.color("#669900"), am4core.color("#003333")
                ];
                colorindx = 0

                var scrollbarX = new am4charts.XYChartScrollbar();
                var scrollbarY = new am4charts.XYChartScrollbar();
                //var scrollbarY = new am4charts.ChartScrollbar();
                var interfaceColors = new am4core.InterfaceColorSet();

                chart.data = data;
                // the following line makes value axes to be arranged vertically.
                chart.leftAxesContainer.layout = "vertical";

                var dateAxis = chart.xAxes.push(new am4charts.DateAxis());
                dateAxis.renderer.grid.template.location = 0;
                dateAxis.renderer.ticks.template.length = 8;
                dateAxis.renderer.ticks.template.strokeOpacity = 0.1;
                dateAxis.renderer.grid.template.disabled = true;
                dateAxis.renderer.ticks.template.disabled = false;
                dateAxis.renderer.ticks.template.strokeOpacity = 0.2;

                var valueAxis = chart.yAxes.push(new am4charts.ValueAxis());
                valueAxis.tooltip.disabled = false;
                valueAxis.title.text = "Progress %%";
                valueAxis.zIndex = 1;
                valueAxis.renderer.baseGrid.disabled = true;

                // Set up axis
                valueAxis.renderer.inside = true;
                valueAxis.height = am4core.percent(60);
                valueAxis.renderer.labels.template.verticalCenter = "bottom";
                valueAxis.renderer.labels.template.padding(2, 2, 2, 2);
                //valueAxis.renderer.maxLabelPosition = 0.95;
                valueAxis.renderer.fontSize = "0.8em"

                // uncomment these lines to fill plot area of this axis with some color
                valueAxis.renderer.gridContainer.background.fill = interfaceColors.getFor("alternativeBackground");
                valueAxis.renderer.gridContainer.background.fillOpacity = 0.05;




                //Iterate on all VMs and Plot
                vmarray.forEach(element => {

                    var series0 = chart.series.push(new am4charts.LineSeries());
                    series0.dataFields.dateX = "date";
                    series0.dataFields.valueY = [element];
                    series0.fill = chart.colors.getIndex(colorindx);
                    colorindx = colorindx + 1;
                    //series.tooltipText = "{valueY.value}";
                    var bullet = series0.bullets.push(new am4charts.CircleBullet());

                    bullet.tooltipText = "{valueY.value} :" + element
                    series0.name = [element];


                    scrollbarX.series.push(series0);
                    scrollbarY.series.push(series0)



                });


                titlearray.push({ "Axes": valueAxis, "Name": "VMs Operation Data Progress/ Time" })




                chart.legend = new am4charts.Legend();

                // Set Title for Subplots


                title_indx = 1
                titlearray.forEach(element => {
                    //var title_axis = element["Axes"];
                    var title_name = element["Name"];
                    console.log(element["Axes"].title.text)
                    var title2 = "title" + title_indx
                    title_indx = title_indx + 1;
                    window[title2] = element["Axes"].renderer.gridContainer.createChild(am4core.Label);
                    window[title2].text = "[bold]" + title_name;
                    window[title2].fill = chart.colors.getIndex(0);
                    //window[title2].fill = series.fill;
                    window[title2].isMeasured = false;
                    window[title2].y = 15;
                    window[title2].x = am4core.percent(40);
                    window[title2].align = "center";
                    window[title2].textAlign = "middle";

                }
                );



                chart.cursor = new am4charts.XYCursor();

                chart.cursor.xAxis = dateAxis;
                scrollbarX.marginBottom = 20;
                chart.scrollbarX = scrollbarX;

                //chart.cursor.yAxis = valueAxis;

                //chart.scrollbarY = scrollbarY;
                //chart.cursor.behavior = "zoomY";

                chart.scrollbarY = new am4core.Scrollbar();


                //chart.scrollbarY = new am4core.Scrollbar();



                // Enable export
                chart.exporting.menu = new am4core.ExportMenu();
                chart.exporting.menu.align = "left";
                chart.exporting.menu.verticalAlign = "top";


            }); // end am4core.ready()

        }

    </script>

</head>


<body onload="load();draw();">
    <div id="chartdiv"> </div>
</body>

</html>

"""


def DrawIt(**kwargs):
    opsname = tc.testname
    logger = tc.logger
    vmdb = kwargs["vms"]  # A list of all VMS
    datastoreinfo = kwargs["datastoreinfo"]  # A Default Dict


    try:
        # Plotting statts




        # This plots VM Stats

        for vm in vmdb:
            rowVMSession = None
            try:
                engine = create_engine('sqlite:///framework/db/%s.db' % vm)
                Base.metadata.bind = engine
                vdbSession = sessionmaker(bind=engine)
                rowVMSession = vdbSession()
                vmname = vm
                results = rowVMSession.query(VMStats.time, VMStats.progress)

                for result in results:
                    vm_data.setdefault(vm, []).append({"Time": result[0] * 1000, "Progress": result[1]})

            except Exception as e:
                logger.debug("THREAD -%s- Error while reading data from VM DB %s" % (vm, e))

            finally:
                rowVMSession.close()

        rowEsxSession = None

        for host, dsnames in datastoreinfo.items():
            rowEsxSession = None

            try:

                engine = create_engine('sqlite:///framework/db/%s.db' % host)
                Base.metadata.bind = engine
                esxDbSession = sessionmaker(bind=engine)
                rowEsxSession = esxDbSession()
                logger.debug("THREAD - %s - Plotting Network for host " % (host))

                vnic, = rowEsxSession.query(NetworkData.network).first()
                unit, = rowEsxSession.query(NetworkData.unit).first()
                nicresults = rowEsxSession.query(NetworkData.time, NetworkData.usage)

                for nicresult in nicresults:
                    time_val = int(nicresult[0]) * 1000
                    host_nic.setdefault(host, []).append({"Time": time_val, "Bandwidth": nicresult[1], "vnic": vnic})

                finalds = []

                for row in rowEsxSession.query(DSData.datastore).distinct():
                    finalds.append(row.datastore)

                logger.debug("THREAD - %s - Unique DS %s" % (host, finalds))

                for ds in finalds:
                    results = rowEsxSession.query(DSData.time, DSData.dsread, DSData.dswrite)
                    for result in results:
                        host_ds.setdefault(ds, []).append(
                            {"Time": int(result[0]) * 1000, "Read": result[1], "Write": result[2]})



            except Exception as e:
                logger.exception("THREAD -%s- Host Level Error while reading data from ESX DB %s" % (host, e))

            finally:
                rowEsxSession.close()

        try:
            final_data["vm"] = dict(vm_data)
            final_data["nic"] = dict(host_nic)
            final_data["datastore"] = dict(host_ds)

            x = json.dumps(final_data, indent=4)


            js_file = tc.testname + "_" + str(tc.test_start) + ".js"

            html_file = tc.testname + "_" + str(tc.test_start) + ".html"
            vm_file = "VM_Operation_" + tc.testname + "_" + str(tc.test_start) + ".html"

            print("THREAD - GraphPlotter - The Data file name %s" % js_file)

            with open(js_file, "w") as f:
                f.write("var testdata = %s" % x)

            print("THREAD - GraphPlotter - Plotting Operation Graph  %s" % html_file)

            html_new_Data = html_data % {"datafile": js_file}
            vm_new_data = only_vm_html % {"datafile": js_file}

            with open(html_file, "w") as f:
                f.write(html_new_Data)

            with open(vm_file, "w") as f:
                f.write(vm_new_data)

            print("THREAD - GraphPlotter - The result is plotted at %s" % html_file)

            wb.open('file://' + os.path.realpath(html_file))
            time.sleep(5)
            wb.open_new_tab('file://' + os.path.realpath(vm_file))

        except Exception as e:
            logger.exception("THREAD - GraphPlotter - Error while plotting data %s"%e)




    except Exception as e:
        logger.exception("THREAD -main- Error while reading data from ESX DB %s" % (e))









