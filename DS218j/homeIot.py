import paho.mqtt.client as mqtt
from mysql.connector import MySQLConnection, Error, connect
import json
import time
import threading
import datetime
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from ftplib import FTP
import os
import fileinput
import credentials as cr
import config as cf
from configparser import ConfigParser

current_heating_setpoint_celsius = 20


def add_log(function_name, exception_name):
    with open(cf.log_file_path, "a") as fileObj:
        now = datetime.datetime.now()
        now_string = now.strftime("%m/%d/%Y, %H:%M:%S")
        fileObj.write(now_string + ": Exception in " + function_name + ":\n")
        fileObj.write(exception_name + '\n')
        print(now_string + ": Exception in " + function_name + ":\n")
        print(exception_name + '\n')


def sql_read_config(filename='DS218j/config.ini', section='mysql'):
    parser = ConfigParser()
    parser.read(filename)
    db = {}
    if parser.has_section(section):
        items = parser.items(section)
        for item in items:
            db[item[0]] = item[1]
    else:
        raise Exception('{0} not found in the {1} file'
                        .format(section, filename))
    return db


def sql_insert_data(location, data, topic):
    '''insert string to topic and location'''
    query = "INSERT INTO iot(location,data,topic) " \
            "VALUES(%s,%s,%s)"
    args = (location, data, topic)
    try:
        db_config = sql_read_config()
        conn = MySQLConnection(**db_config)
        cursor = conn.cursor()
        cursor.execute(query, args)
        conn.commit()
    except Exception as e:
        add_log("sql_insert_data", str(e))
    finally:
        cursor.close()
        conn.close()


def sql_read_data():
    try:
        db_config = sql_read_config()
        conn = MySQLConnection(**db_config)
        cursor = conn.cursor()
        query = ("SELECT ts, location, data FROM iot WHERE ts BETWEEN"
                 " %s AND %s AND topic = 'climate'")
        query_start = datetime.datetime.now()
        query_end = query_start - datetime.timedelta(hours=cf.plot_hours)
        cursor.execute(query, (query_end, query_start))
        fetched = cursor.fetchall()
        cursor.close()
        conn.close()
        return fetched
    except Exception as e:
        add_log("sql_read_data", str(e))


def sql_get_last_temp(location):
    db_config = sql_read_config()
    conn = MySQLConnection(**db_config)
    cursor = conn.cursor()
    query = ("SELECT data FROM iot WHERE location = '" + location + "'"
             "ORDER BY ts DESC LIMIT 1")
    cursor.execute(query)
    fetched = cursor.fetchall()
    cursor.close()
    conn.close()
    fetched = json.loads(fetched[0][0].decode("utf-8"))
    return fetched['tempCelsius']


def parse_for_plot(fetched):
    try:
        c = 0
        data_dict = json.loads(fetched[0][2].decode("utf-8"))
        le = len(fetched)
        col_dict = {'ts': [None]*le,
                    'location': [None]*le}
        for i in data_dict:
            col_dict.update({i: [None]*le})
        for i in fetched:
            col_dict['ts'][c] = i[0]
            col_dict['location'][c] = i[1]
            data_dict = json.loads(i[2].decode("utf-8"))
            for u in data_dict:
                col_dict[u][c] = data_dict[u]
            c += 1
        return col_dict
    except Exception as e:
        add_log("parse_for_plot", str(e))


def plot(parsed):
    fig = make_subplots(rows=2, cols=1)
    for location in set(parsed['location']):
        time_vec = [parsed['ts'][i]
                    for i in range(len(parsed['ts']))
                    if parsed['location'][i] == location]
        humidity_vec = [parsed['humidityPerCent'][i]
                        for i in range(len(parsed['ts']))
                        if ((parsed['location'][i] == location) 
                        and (type(parsed['humidityPerCent'][i]) == float))]
        temp_vec = [parsed['tempCelsius'][i]
                    for i in range(len(parsed['ts']))
                    if parsed['location'][i] == location]
        fig.add_trace(go.Scatter(
                            x=time_vec,
                            y=humidity_vec,
                            mode='lines',
                            name='humidity ' + location),
                      row=1,
                      col=1)
        fig.add_trace(go.Scatter(
                            x=time_vec,
                            y=temp_vec,
                            mode='lines',
                            name='temperature ' + location),
                      row=2,
                      col=1)
    fig['layout']['yaxis1']['title'] = 'Humidity in percent'
    fig['layout']['yaxis2']['title'] = 'Temperature in °C'
    fig.write_html(cf.plot_file_path, auto_open=False)


def on_connect(client, userdata, flags, rc):
    '''The mqtt callback for when the client
    receives a CONNACK response from the server.'''
    print("Connected with result code "+str(rc))
    client.subscribe(cf.mqtt_topic)


def parse_heater_temp(payload):
    returnDict = {"tempCelsius": float(payload['local_temperature']),
                  "humidityPerCent": ""}
    return json.dumps(returnDict)


def on_message(client, userdata, msg):
    ''' The callback for when a PUBLISH message is received from the server.
    Inserts data from mqtt to the database'''
    print(msg.topic+" "+str(msg.payload))
    try:
        payload = json.loads(msg.payload.decode("utf-8"))
        if msg.topic == 'climate':
            sql_insert_data(payload['location'],
                            json.dumps(payload['data']),
                            msg.topic)
        else:
            sql_insert_data('armchair',
                            parse_heater_temp(payload),
                            'climate')
    except Exception as e:
        add_log("on_message", str(e))


def upload_to_server():
    try:
        ftpClient = FTP(host=cr.ftp_host,
                        user=cr.ftp_user,
                        passwd=cr.ftp_pwd)
        ftpClient.set_debuglevel(2)
        ftpClient.connect()
        ftpClient.login(cr.ftp_user, cr.ftp_pwd)
        # ftpClient.cwd('/public_html/' + cf.html_sub_domain)
        fp = open(cf.plot_file_path, 'rb')
        ftpClient.storbinary('STOR %s' % os.path.basename(cf.plot_file_path),
                             fp,
                             1024)
        fp.close()
        ftpClient.quit()
    except Exception as e:
        add_log("upload_to_server", str(e))


def determine_temp_diff():
    try:
        bedroom_temp_celsius = sql_get_last_temp('bedroom')
        armchair_temp_celsius = sql_get_last_temp('armchair')
        return round(bedroom_temp_celsius -
                     armchair_temp_celsius, 1)
    except Exception as e:
        add_log("determine_temp_diff", str(e))


def set_heating_setpoint(new_setpoint):
    client.publish('zigbee2mqtt/living_room_heater/set',
                   '{"preset": "manual"}')
    client.publish('zigbee2mqtt/living_room_heater/set',
                   '{"current_heating_setpoint": "' + str(new_setpoint) +
                   '"}')


def is_night():
    night_beg = datetime.time(hour=18)
    night_end = datetime.time(hour=6)
    now_hour = datetime.datetime.now().hour
    if((now_hour > night_beg.hour) or
       (now_hour) < night_end.hour):
        return True
    else:
        return False


def adjust_heating_setpoint():
    if (is_night()):
        current_heating_setpoint_celsius = 17
    else:
        current_heating_setpoint_celsius = 22
    temp_diff = determine_temp_diff()
    new_setp = current_heating_setpoint_celsius - temp_diff
    set_heating_setpoint(new_setp)


class Visualize(threading.Thread):
    def run(self):
        while True:
            time.sleep(180)
            try:
                adjust_heating_setpoint()
                fetched = sql_read_data()
                parsed = parse_for_plot(fetched)
                plot(parsed)
                upload_to_server()
            except Exception as e:
                add_log("upload_to_server", str(e))
            time.sleep(cf.plot_interval_seconds-180)


network_up = False
while not network_up:
    try:
        client = mqtt.Client()
        client.on_connect = on_connect
        client.on_message = on_message
        client.connect(cf.mqtt_server_ip, cf.mqtt_port, cf.mqtt_ping_seconds)
        client.loop_start()
        network_up = True
    except Exception as e:
        add_log("mqtt connect", str(e))
        time.sleep(5)

# The visualization thread
try:
    adjust_heating_setpoint()
    fetched = sql_read_data()
    parsed = parse_for_plot(fetched)
    plot(parsed)
    upload_to_server()
except Exception as e:
    add_log("upload_to_server", str(e))
Visualize(name="visualize").start()

# The main thread
while threading.activeCount() > 1:
    time.sleep(1)
