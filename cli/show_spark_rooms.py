import os
import sys
script_dir = os.path.dirname(os.path.realpath(__file__))
sys.path.append(script_dir + '/../')

from ciscosparkapi import CiscoSparkAPI

from zpark import app as zpark_app

spark_api = CiscoSparkAPI(access_token=zpark_app.config['SPARK_ACCESS_TOKEN'])
rooms = spark_api.rooms.list(type='group')

print('Zpark has been invited to the following Spark rooms:\n')
for room in rooms:
    print('"{title}"\nroomId: {roomid}\n\n'.format(title=room.title, roomid=room.id))

