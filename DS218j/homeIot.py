import paho.mqtt.client as mqtt
import credentials as cr
from configparser import ConfigParser
from mysql.connector import MySQLConnection, Error, connect
import json
import time,threading
import datetime
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from ftplib import FTP
import os
import fileinput

plotFile = 'index.html'
visuIntervalSecs = int(15)

def sql_read_config(filename='DS218j/config.ini', section='mysql'):
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

def sql_read_data(hoursBack,topicStr):
    try:
        db_config = sql_read_config()
        conn      = MySQLConnection(**db_config)
        cursor    = conn.cursor()

        query = ("SELECT ts, location, data FROM iot WHERE ts BETWEEN"
                " %s AND %s AND topic = '" + topicStr + "'")

        queryStart = datetime.datetime.now()
        queryEnd   = queryStart - datetime.timedelta(hours=hoursBack)
        cursor.execute(query, (queryEnd, queryStart))
        fetched = cursor.fetchall()
        cursor.close()
        conn.close()
        return fetched
    except Error as error:
        print(error)

def parse_for_plot(fetched):
    try:
        c = 0
        dataDict = json.loads(fetched[0][2].decode("utf-8")) 
        le       = len(fetched)
        colDict  = {'ts':[None]*le,
                     'location':[None]*le}
        for i in dataDict:
            colDict.update({i:[None]*le})
        for i in fetched:
            colDict['ts'][c]       = i[0]
            colDict['location'][c] = i[1]
            dataDict = json.loads(i[2].decode("utf-8"))
            for u in dataDict:
                colDict[u][c] = dataDict[u]
            c += 1
        return colDict
    except Error as error:
        print(error)

def sql_insert_data(locationStr,dataStr,topicStr):
    query = "INSERT INTO iot(location,data,topic) " \
            "VALUES(%s,%s,%s)"
    args = (locationStr,dataStr,topicStr)
    try:
        db_config = sql_read_config()
        conn      = MySQLConnection(**db_config)
        cursor    = conn.cursor()
        cursor.execute(query, args)
        conn.commit()
    except Error as error:
        print(error)
    finally:
        cursor.close()
        conn.close()

def plot(parsed):
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    for location in set(parsed['location']):
        fig.add_trace(go.Scatter(
                            x=[parsed['ts'][i] for i in range(len(parsed['ts'])) if parsed['location'][i] == location],
                            y=[parsed['humidityPerCent'][i] for i in range(len(parsed['ts'])) if parsed['location'][i] == location],
                            mode='lines',
                            name='humidity ' + location))
        fig.add_trace(go.Scatter(
                            x=[parsed['ts'][i] for i in range(len(parsed['ts'])) if parsed['location'][i] == location],
                            y=[parsed['tempCelsius'][i] for i in range(len(parsed['ts'])) if parsed['location'][i] == location],
                            mode='lines',
                            name='temperature ' + location),
                            secondary_y=True)
    fig.write_html(plotFile, auto_open=False)

def on_connect(client, userdata, flags, rc):
    '''The mqtt callback for when the client receives a CONNACK response from the server.'''
    print("Connected with result code "+str(rc))

    client.subscribe("climate")

def on_message(client, userdata, msg):
    ''' The callback for when a PUBLISH message is received from the server.'''
    print(msg.topic+" "+str(msg.payload))
    try:
        payload  = json.loads(msg.payload.decode("utf-8"))
        sql_insert_data(payload['location'],json.dumps(payload['data']),msg.topic)
    except Exception as e:
        print(e)

class Visualize(threading.Thread):
    def run(self):
        while True:
            time.sleep(visuIntervalSecs)
            try:
                fetched = sql_read_data(24,'climate')
                parsed  = parse_for_plot(fetched)
                plot(parsed)
                uploadToServer()
            except Exception as e:
                print(e)

def uploadToServer():
    try:
        ftpClient = FTP(host=cr.ftpHost
                    , user=cr.ftpUser
                    , passwd=cr.ftpPwd)
        ftpClient.set_debuglevel(2)
        ftpClient.connect() 
        ftpClient.login(cr.ftpUser,cr.ftpPwd)
        ftpClient.cwd('/public_html/sc')
        fp = open(plotFile, 'rb')
        ftpClient.storbinary('STOR %s' % os.path.basename(plotFile), fp, 1024)
        fp.close()
        ftpClient.quit()
    except Exception as e:
        print(e)

# construct a mqtt client and start a thread to process the connection and the messages
client            = mqtt.Client()
client.username_pw_set(cr.username, password=cr.password)
client.on_connect = on_connect
client.on_message = on_message
client.connect("192.168.1.200", 1883, 60)
client.loop_start()

# the visualization thread
Visualize(name = "visualize").start()

#The main thread
while threading.activeCount() > 1:
  time.sleep(1)