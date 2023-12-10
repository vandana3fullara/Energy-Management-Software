import minimalmodbus
import serial
import datetime
import time
import csv
import mysql.connector
import importlib
import math
import struct
import os
import requests

# Define Your Serial Port
serial_port = '/dev/ttyUSB0'
byte_size = 8

# Function To Replace NaN With 0
def replace_nan_with_zero(value):
    return 0.0 if math.isnan(value) else value

# Function To Get The Current Date And Time In The Specified Format
def get_current_datetime():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# Function To Initialize The File With Headers
def initialize_csv_file(file_name, headers):
    if not os.path.isfile(file_name):
        with open(file_name, 'w', newline='') as csvfile:
            csvwriter = csv.writer(csvfile)
            csvwriter.writerow(['Date'] + headers)  # Write Date And Headers

# Function To Write Data To The File
def write_data_to_csv(file_name, data):
    with open(file_name, 'a', newline='') as csvfile:
        csvwriter = csv.writer(csvfile)
        csvwriter.writerow(data)

# Function To Create The Database Table And Insert Data
def create_mysql_table_and_insert_data(parameters, db_table_name, row_data, section_id, raspberrypi_id, meter_id):
    try:
        connection = mysql.connector.connect(
            host="193.203.184.2",
            user="u295327377_madical_user",
            password="5G27zBkBOZ6w",
            database="u295327377_madical_db",
            port=3306
        )
        cursor = connection.cursor()

        # Modify the create table query to include section_id, raspberrypi_id, and meter_id
        create_table_query = f"CREATE TABLE IF NOT EXISTS `{db_table_name}` (Date DATETIME, section_id INT, raspberrypi_id INT, meter_id INT, {', '.join(parameters)})"
        cursor.execute(create_table_query)

        # Add section_id, raspberrypi_id, and meter_id to the row data
        row_data = [get_current_datetime(), section_id, raspberrypi_id, meter_id] + row_data

        placeholders = ', '.join(['%s'] * (len(parameters) + 4))
        insert_query = f"INSERT INTO `{db_table_name}` VALUES ({placeholders})"
        cursor.execute(insert_query, row_data)

        connection.commit()
        cursor.close()
        connection.close()
    except mysql.connector.Error as e:
        print(f"MYSQL ERROR: {e}")

# Function to get the meter details from the API endpoint
def get_meter_details():
    api_url = "http://192.168.0.158:5000/api/meters"
    try:
        response = requests.get(api_url)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"API Error: {e}")
        return None

# Function to collect data for all meters
def collect_data_for_all_meters(num_meters, meter_details, parameters, section_id, raspberrypi_id):
    while True:
        for meter_index in range(num_meters):
            collect_data_for_meter(meter_index, meter_details[meter_index], parameters[meter_index], section_id, raspberrypi_id)
        time.sleep(60)

# Function to collect data for a single meter
def collect_data_for_meter(meter_index, meter_details, parameters, section_id, raspberrypi_id):
    print(f"Meter {meter_index + 1} of {num_meters}")

    model_number = meter_details['meter_model']
    file_name = f'Section{section_id}_RaspberryPi{raspberrypi_id}.csv'
    db_table_name = f'Section{section_id}_RaspberryPi{raspberrypi_id}'
    initialize_csv_file(file_name, parameters)  # Initialize the file with headers

    try:
        instrument = minimalmodbus.Instrument(serial_port, int(meter_details['slave_address']))
        instrument.serial.baudrate = meter_details['baud_rate']
        instrument.serial.bytesize = byte_size

        if meter_details['parity'] == 'Even':
            instrument.serial.parity = serial.PARITY_EVEN
            instrument.serial.stopbits = 1
        elif meter_details['parity'] == 'ODD':
            instrument.serial.parity = serial.PARITY_ODD
            instrument.serial.stopbits = 1
        else:
            instrument.serial.parity = serial.PARITY_NONE
            instrument.serial.stopbits = 2

        row_data = []

        for i in meter_details['address']:
            if model_number in ['em1220h', 'em1000h']:
                register_value = instrument.read_float(int(i), functioncode=3)
                row_data.append(replace_nan_with_zero(register_value))
            elif model_number in ['em6433', 'em6436']:
                raw_data_big_endian = instrument.read_registers(int(i), 2, functioncode=3)
                little_endian_bytes = bytes([raw_data_big_endian[1] & 0xFF, raw_data_big_endian[1] >> 8, raw_data_big_endian[1] & 0xFF, raw_data_big_endian[1] >> 8])
                register_value = struct.unpack('<f', little_endian_bytes)[0]
                row_data.append(replace_nan_with_zero(register_value))

        write_data_to_csv(file_name, row_data)  # Append data to the file
        print(f"Data Inserted Into File {file_name} Successfully")

        create_mysql_table_and_insert_data(parameters, db_table_name, row_data, section_id, raspberrypi_id, meter_index + 1)
        print(f"Data Inserted Into Database Table {db_table_name} Successfully")

        print('*' * 50)
    except Exception as e:
        print(f"Connection to Meter {meter_index + 1} Failed: {str(e)}")

if __name__ == "__main__":
    # Get meter details from the API
    api_data = get_meter_details()

    if api_data and 'num_meters_connected' in api_data and 'meters_details' in api_data:
        num_meters = api_data['num_meters_connected']
        meter_details = api_data['meters_details']
        parameters = []
        section_id = api_data.get('section_id', 1)
        raspberrypi_id = api_data.get('raspberrypi_id', 1)

        for meter_index in range(num_meters):
            meter_model = meter_details[meter_index]['meter_model']
            try:
                meter_model_module = importlib.import_module(f"meter_models.{meter_model}")
                parameters.append(meter_model_module.parameters)
                meter_details[meter_index]['address'] = meter_model_module.address
            except ImportError:
                print(f"Module For {meter_model} Not Found")

        collect_data_for_all_meters(num_meters, meter_details, parameters, section_id, raspberrypi_id)
    else:
        print("Invalid API response. Check the API endpoint.")

