import paho.mqtt.client as mqtt
import credentials as cr
from configparser import ConfigParser
from mysql.connector import MySQLConnection, Error
import json


def read_db_config(filename='DS218j/config.ini', section='mysql'):
    # create parser and read ini configuration file
    parser = ConfigParser()
    parser.read(filename)
 
    # get section, default to mysql
    db = {}
    if parser.has_section(section):
        items = parser.items(section)
        for item in items:
            db[item[0]] = item[1]
    else:
        raise Exception('{0} not found in the {1} file'.format(section, filename))
 
    return db

def insert_data(locationStr,dataStr,topicStr):
    query = "INSERT INTO iot(location,data,topic) " \
            "VALUES(%s,%s,%s)"
    args = (locationStr,dataStr,topicStr)
 
    try:
        db_config = read_db_config()
        conn = MySQLConnection(**db_config)
 
        cursor = conn.cursor()
        cursor.execute(query, args)
  
        conn.commit()
    except Error as error:
        print(error)
 
    finally:
        cursor.close()
        conn.close()

# The mqtt callback for when the client receives a CONNACK response from the server.
def on_connect(client, userdata, flags, rc):
    print("Connected with result code "+str(rc))

    # Subscribing in on_connect() means that if we lose the connection and
    # reconnect then subscriptions will be renewed.
    client.subscribe("climate")

# The callback for when a PUBLISH message is received from the server.
def on_message(client, userdata, msg):
    print(msg.topic+" "+str(msg.payload))
    payload  = json.loads(msg.payload)
    insert_data(payload['location'],json.dumps(payload['data']),msg.topic)

client = mqtt.Client()
client.username_pw_set(cr.username, password=cr.password)
client.on_connect = on_connect
client.on_message = on_message

client.connect("192.168.1.200", 1883, 60)

# Blocking call that processes network traffic, dispatches callbacks and
# handles reconnecting.
# Other loop*() functions are available that give a threaded interface and a
# manual interface.
client.loop_forever()