#  Copyright 2008-2015 Nokia Networks
#  Copyright 2016-     Robot Framework Foundation
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

"""Module that adds directories needed by Robot to sys.path when imported."""

import sys
import fnmatch
from os.path import abspath, dirname

ROBOTDIR = dirname(abspath(__file__))

# sys.path是一个列表list,他里面包含了已经添加到系统的环境变量路径
def add_path(path, end=False):
    if not end:
        remove_path(path)
        sys.path.insert(0, path)
        # 以最高优先级将path插入到sys.path中
    elif not any(fnmatch.fnmatch(p, path) for p in sys.path):
        # 如果sys.path列表中没有任何元素和函数变量path匹配，则将path加入到sys.path列表中
        sys.path.append(path)

def remove_path(path):
    sys.path = [p for p in sys.path if not fnmatch.fnmatch(p, path)]
    # 将sys.path中与变量path不匹配的元素赋值给sys.path.即删除sys.path中path,并且保留其余部分


# When, for example, robot/run.py is executed as a script, the directory
# containing the robot module is not added to sys.path automatically but
# the robot directory itself is. Former is added to allow importing
# the module and the latter removed to prevent accidentally importing
# internal modules directly.
add_path(dirname(ROBOTDIR))
remove_path(ROBOTDIR)
