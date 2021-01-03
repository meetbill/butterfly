#!/bin/bash

CUR_DIR=$(cd `dirname $0`; pwd)
cd ${CUR_DIR}
DISP_NAME="butterfly"

EXEC="python2.7"
MAIN_FILE="${CUR_DIR}/main.py"
STDOUT="${CUR_DIR}/__stdout"

PROC_SIG="954216e9"

# Consts
RED='\033[1;91m'
GREN='\033[1;92m'
WITE='\033[1;97m'
NC='\033[0m'

# Global vailables
PROC_COUNT="0"
function count_proc()
{
    PROC_COUNT=$(ps -ef | grep $MAIN_FILE | grep $PROC_SIG | grep -vc grep)
}
function list_proc()
{
    ps -ef | grep -v grep | grep $PROC_SIG | grep --color $MAIN_FILE
}
function list_proc_pids()
{
    ps -ef | grep $MAIN_FILE | grep $PROC_SIG | grep -v grep | awk '{print $2}'
}

function start_procs()
{
    printf "Starting $DISP_NAME processes"
    count_proc
    if [ $PROC_COUNT \> 0 ]; then
        echo
        list_proc
        echo -e ${RED}"\n[ERROR]" ${NC}"Start $DISP_NAME failed, processes already runing."
        exit -1
    fi
    date >> $STDOUT
    $EXEC $MAIN_FILE $PROC_SIG 1>>$STDOUT 2>&1 &

    sleep 1
    list_proc
    count_proc
    if [ $PROC_COUNT == 0 ]; then
        echo -e ${RED}"\n[ERROR]" ${NC}"Start $DISP_NAME failed."
        exit -1
    fi

    echo -e ${GREN}"\n[OK]" ${NC}"$DISP_NAME start succesfully."
}

function stop_procs()
{
    printf "Stoping $DISP_NAME"
    count_proc
    if [ ${PROC_COUNT} -eq 0 ]; then
        echo -e ${RED}"\n[ERROR]" ${NC}"$DISP_NAME process not found."
        exit -1
    fi

    kill -15 $(list_proc_pids)
    count_proc
    while [ ${PROC_COUNT} -ne 0 ]; do
        printf "."
        sleep 0.2
        count_proc
    done
    echo -e ${GREN}"\n[OK]" ${NC}"$DISP_NAME stop succesfully."
}

function status_procs()
{
    count_proc
    echo -e ${RED}${PROC_COUNT}${NC} "$DISP_NAME processes runing."
}

function docker_start_procs()
{
    printf "Starting $DISP_NAME processes"
    count_proc
    date >> $STDOUT
    $EXEC $MAIN_FILE $PROC_SIG
}

function set_env()
{
    echo "Please exe this command:"
    echo "------------------------"
    echo "export PYTHONPATH=\$(pwd):\$PYTHONPATH"
}

MODE=${1}
case ${MODE} in
    "start")
        start_procs
        ;;

    "docker_start")
        docker_start_procs
        ;;

    "stop")
        stop_procs
        ;;

    "restart")
        stop_procs
        start_procs
        ;;

    "status")
        status_procs
        ;;

    "env")
        set_env
        ;;

    *)
        # usage
        echo -e "\nUsage: $0 {start|stop|restart|status}"
        echo -e ${WITE}" start          "${NC}"Start $DISP_NAME processes."
        echo -e ${WITE}" docker_start   "${NC}"Start $DISP_NAME processes for docker."
        echo -e ${WITE}" stop           "${NC}"Kill all $DISP_NAME processes."
        echo -e ${WITE}" restart        "${NC}"Kill all $DISP_NAME processes and start again."
        echo -e ${WITE}" status         "${NC}"Show $DISP_NAME processes status."
        echo -e ${WITE}" env            "${NC}"env(Set PYTHONPATH tips).\n"
        exit 1
        ;;
esac
