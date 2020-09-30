#!/bin/bash
#########################################################################
# File Name: pep8.sh
# Author: meetbill(wangbin34)
# mail: meetbill@163.com
# Created Time: 2020-09-30 10:17:57
# autopep8 会根据 PEP 8 样式文档来格式化 python 代码
#########################################################################

if [ $# != 1 ] ; then
    echo "USAGE: $0 filename"
    echo " e.g.: $0 w.py"
    exit 1;
fi

CUR_DIR=`S=$(readlink "$0"); [ -z "$S"  ] && S=$0; cd $(dirname $S);pwd`

python $CUR_DIR/autopep8.py --aggressive --in-place  $1
