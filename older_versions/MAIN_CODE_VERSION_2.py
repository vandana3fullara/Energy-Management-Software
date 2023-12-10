import tkinter as tk
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
def create_mysql_table_and_insert_data(parameters, db_table_name, row_data):
    try:
        connection = mysql.connector.connect(
            host="193.203.184.2",
            user="u295327377_madical_user",
            password="5G27zBkBOZ6w",
            database="u295327377_madical_db",
            port=3306
        )
        cursor = connection.cursor()
        create_table_query = f"CREATE TABLE IF NOT EXISTS `{db_table_name}` (Date DATETIME, {', '.join(parameters)})"
        cursor.execute(create_table_query)

        placeholders = ', '.join(['%s'] * (len(parameters) + 1))
        insert_query = f"INSERT INTO `{db_table_name}` VALUES ({placeholders})"
        cursor.execute(insert_query, row_data)

        connection.commit()
        cursor.close()
        connection.close()
    except mysql.connector.Error as e:
        print(f"MYSQL ERROR: {e}")

# Function to ask for the number of meters
def get_number_of_meters():
    global num_meters, root, meter_details, parameters
    num_meters = int(entry4.get())
    meter_details = []
    parameters = []
    for i in range(num_meters):
        meter_details.append({})
        parameters.append([])
    root.title("User Input for Meters")
    create_meter_input_window(0)

# Function to create the meter input window
def create_meter_input_window(meter_index):
    global entry0, entry1, entry2, entry3, root, meter_details, parameters
    if meter_index < num_meters:
        label0 = tk.Label(root, text=f"Enter Meter Model Number for Meter {meter_index + 1}")
        label0.pack()
        entry0 = tk.Entry(root, width=30)
        entry0.pack()

        label1 = tk.Label(root, text=f"Enter Slave ID for Meter {meter_index + 1}")
        label1.pack()
        entry1 = tk.Entry(root, width=30)
        entry1.pack()

        label2 = tk.Label(root, text=f"Enter Baud Rate for Meter {meter_index + 1}")
        label2.pack()
        entry2 = tk.Entry(root, width=30)
        entry2.pack()

        label3 = tk.Label(root, text=f"Enter Parity for Meter {meter_index + 1}")
        label3.pack()
        entry3 = tk.Entry(root, width=30)
        entry3.pack()

        submit_button = tk.Button(root, text="Connect", command=lambda i=meter_index: process_meter_details(i))
        submit_button.pack()
    else:
        root.destroy()
        collect_data_for_all_meters(num_meters, meter_details, parameters)

# Function to process meter details
def process_meter_details(meter_index):
    global entry0, entry1, entry2, entry3, meter_details, root

    meter_details[meter_index]['model_number'] = entry0.get()
    meter_details[meter_index]['slave_address'] = int(entry1.get())
    meter_details[meter_index]['baud_rate'] = int(entry2.get())
    meter_details[meter_index]['Parity'] = entry3.get()

    # Dynamically import the module based on user input
    if meter_details[meter_index]['model_number']:
        try:
            meter_model_module = importlib.import_module(f"meter_models.{meter_details[meter_index]['model_number']}")
            parameters[meter_index] = meter_model_module.parameters
            meter_details[meter_index]['address'] = meter_model_module.address
        except ImportError:
            print(f"Module For {meter_details[meter_index]['model_number']} Not Found")

    create_meter_input_window(meter_index + 1)

# Function to collect data for all meters
def collect_data_for_all_meters(num_meters, meter_details, parameters):
    while True:
        for meter_index in range(num_meters):
            collect_data_for_meter(meter_index, meter_details[meter_index], parameters[meter_index])
        time.sleep(1)

# Function to collect data for a single meter
def collect_data_for_meter(meter_index, meter_details, parameters):
    print(f"Meter {meter_index + 1} of {num_meters}")

    model_number = meter_details['model_number']
    file_name = f'{model_number}_Meter{meter_index + 1}.csv'
    db_table_name = f'{model_number}_Meter{meter_index + 1}'
    initialize_csv_file(file_name, parameters)  # Initialize the file with headers

    try:
        instrument = minimalmodbus.Instrument(serial_port, meter_details['slave_address'])
        instrument.serial.baudrate = meter_details['baud_rate']
        instrument.serial.bytesize = byte_size

        if meter_details['Parity'] == 'Even':
            instrument.serial.parity = serial.PARITY_EVEN
            instrument.serial.stopbits = 1
        elif meter_details['Parity'] == 'ODD':
            instrument.serial.parity = serial.PARITY_ODD
            instrument.serial.stopbits = 1
        else:
            instrument.serial.parity = serial.PARITY_NONE
            instrument.serial.stopbits = 2

        row_data = [get_current_datetime()]

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

        create_mysql_table_and_insert_data(parameters, db_table_name, row_data)
        print(f"Data Inserted Into Database Table {db_table_name} Successfully")

        print('*' * 50)
    except Exception as e:
        print(f"Connection to Meter {meter_index + 1} Failed: {str(e)}")

if __name__ == "__main__":
    root = tk.Tk()
    root.title("User Input Box")

    # Create Entry Widgets For User Input
    label4 = tk.Label(root, text="Enter the number of meters connected in series")
    label4.pack()
    entry4 = tk.Entry(root, width=30)
    entry4.pack()
    submit_button = tk.Button(root, text="Next", command=get_number_of_meters)
    submit_button.pack()
    root.mainloop()
 
