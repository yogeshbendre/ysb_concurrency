__author__ = 'Smruti P Mohanty'
"""
Company : VMWare Inc.
                                Apache License
                           Version 2.0, January 2004
                        http://www.apache.org/licenses/

"""

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship,sessionmaker
from sqlalchemy import create_engine,Table, Column, Integer, String, MetaData
import time
from dateutil.parser import parse
from pyVmomi import vim, vmodl

Base = declarative_base()

class VMStats(Base):
    __tablename__ = 'vmstatus'
    id = Column(Integer, primary_key=True)
    time = Column(Integer)
    vmname = Column(String(40))
    progress = Column(Integer)
    legend = Column(String(100))


def Analyze(logger,si,vm_name,task):
    vmsession = None
    complete_time = None
    try:

        engine = create_engine('sqlite:///framework/db/%s.db' % vm_name)
        # remove_db(engine, db_name)

        Base.metadata.create_all(engine)
        time.sleep(1)

        Base.metadata.bind = engine
        vmDbSession = sessionmaker(bind=engine)
        vmsession = vmDbSession()


        tzinfos = {"UTC": 0}

        queue_time = None

        # Record The Queue Time

        queue_time = parse(str(task.info.queueTime),tzinfos=tzinfos).strftime('%s')
        vmStatQ = VMStats(time=queue_time, vmname=vm_name, legend="Queued",progress = 0)
        vmsession.add(vmStatQ)
        vmsession.commit()
        logger.info("VM %s Migration Queue Time %s" % (vm_name, queue_time))

        start_time = None

        run_loop = True
        # Record Progress
        startRecorded = False
        while run_loop:

            progress_time =  parse(str(si.CurrentTime()), tzinfos=tzinfos).strftime('%s')
            #migrationProgress = task.info.progress if task.info.progress else 0

            if task.info.state == vim.TaskInfo.State.running:
                if not startRecorded:
                    # Record The Start Time

                    start_time = parse(str(task.info.startTime), tzinfos=tzinfos).strftime('%s')
                    vmStatS = VMStats(time=start_time, vmname=vm_name, legend="Started", progress=task.info.progress)
                    vmsession.add(vmStatS)
                    vmsession.commit()

                    # clone_stamp["StartTime"] = str(start_time)
                    logger.info("VM %s Migration Start Time %s" % (vm_name, start_time))
                    startRecorded = True
                #logger.info("VM %s Migration Start Time %s" % (vm_name, start_time))
                else:
                    vmStatS = VMStats(time=progress_time, vmname=vm_name, legend="Running", progress=task.info.progress)
                    vmsession.add(vmStatS)
                    vmsession.commit()
                    time.sleep(5)

            if task.info.state == vim.TaskInfo.State.success:
                if task.info.result is not None:
                    out = '%s migration completed successfully, result: %s' % (vm_name, task.info.result)
                    logger.info(out)
                    complete_time = parse(str(task.info.completeTime),tzinfos=tzinfos).strftime('%s')
                    #clone_stamp["CompleteTime"] = str(complete_time)
                    vmStatC = VMStats(time=str(complete_time), vmname=vm_name, legend="Completed", progress=100 if not task.info.progress else task.info.progress)
                    vmsession.add(vmStatC)
                    vmsession.commit()
                    time.sleep(5)
                    run_loop = False
                else:
                    out = '%s migration completed successfully.' % vm_name
                    logger.info(out)
                    complete_time = parse(str(task.info.completeTime),tzinfos=tzinfos).strftime('%s')
                    #clone_stamp["CompleteTime"] = str(complete_time)
                    vmStatE = VMStats(time=complete_time, vmname=vm_name, legend="Completed", progress=100 if not task.info.progress else task.info.progress)
                    vmsession.add(vmStatE)
                    vmsession.commit()
                    time.sleep(5)
                    run_loop = False
            elif task.info.error is not None:
                out = '%s migration did not complete successfully: %s' % (vm_name, task.info.error)
                logger.error(out)
                complete_time = parse(str(task.info.completeTime),tzinfos=tzinfos).strftime('%s')
                #clone_stamp["CompleteTime"] = str(complete_time)
                vmStatE = VMStats(time=complete_time, vmname=vm_name, legend=str(task.info.error), progress=0)
                vmsession.add(vmStatE)
                vmsession.commit()
                run_loop = False
            else:
                logger.info('%s migration status: %s' % (vm_name, task.info.state))



    except Exception as e:
        logger.error("%s -  Error while entring data to Task DB %s"%(vm_name,e))
    finally:
        vmsession.close()


    logger.info("VM %s Migration Complete Time %s" % (vm_name, complete_time))
    #cloning_time_stamp[vm_name] = clone_stamp
