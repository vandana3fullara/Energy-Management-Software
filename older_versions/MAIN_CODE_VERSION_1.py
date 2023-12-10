import tkinter as tk
import minimalmodbus
import serial
import datetime
import time
import os
import csv
import mysql.connector
import importlib
import math
import struct

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

# Function To Collect And Log Data
def data_collection(meter_model_number, db_table_name):
    file_name = f'{meter_model_number}.csv'
    initialize_csv_file(file_name, parameters)  # Initialize The File With Headers

    while True:
        try:
            instrument = minimalmodbus.Instrument(serial_port, slave_address)
            instrument.serial.baudrate = baud_rate
            instrument.serial.bytesize = byte_size

            if Parity == 'Even':
                instrument.serial.parity = serial.PARITY_EVEN
                instrument.serial.stopbits = 1
            elif Parity == 'ODD':
                instrument.serial.parity = serial.PARITY_ODD
                instrument.serial.stopbits = 1
            else:
                instrument.serial.parity = serial.PARITY_NONE
                instrument.serial.stopbits = 2

            row_data = [get_current_datetime()]

            if meter_model_number in ['em1220h', 'em1000h']:
                for i in address:
                    register_value = instrument.read_float(int(i), functioncode=3)
                    row_data.append(replace_nan_with_zero(register_value))
            elif meter_model_number in ['em6433', 'em6436']:
                for i in address:
                    raw_data_big_endian = instrument.read_registers(int(i), 2, functioncode=3)
                    little_endian_bytes = bytes([raw_data_big_endian[1] & 0xFF, raw_data_big_endian[1] >> 8, raw_data_big_endian[1] & 0xFF, raw_data_big_endian[1] >> 8])
                    register_value = struct.unpack('<f', little_endian_bytes)[0]
                    row_data.append(replace_nan_with_zero(register_value))
                    

            write_data_to_csv(file_name, row_data)  # Write Data To The File
            print("Data Inserted Into File Successfully")

            create_mysql_table_and_insert_data(parameters, db_table_name, row_data)
            print("Data Inserted Into Database Successfully")

            print('*' * 50)
            time.sleep(1)  # Sleep For 1 Seconds
        except Exception as e:
            print("Connection Failed", str(e))

# Function To Get User Input
def get_user_input():
    global slave_address, baud_rate, Parity, meter_model_number
    meter_model_number = entry0.get()
    slave_address = int(entry1.get())
    baud_rate = int(entry2.get())
    Parity = entry3.get()
    root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    root.title("User Input Box")

    # Create Entry Widgets For User Input
    label0 = tk.Label(root, text="Enter Meter Model Number")
    label0.pack()
    entry0 = tk.Entry(root, width=30)
    entry0.pack()  

    label1 = tk.Label(root, text="Enter Slave ID")
    label1.pack()
    entry1 = tk.Entry(root, width=30)
    entry1.pack()

    label2 = tk.Label(root, text="Enter Baud Rate")
    label2.pack()
    entry2 = tk.Entry(root, width=30)
    entry2.pack()

    label3 = tk.Label(root, text="Enter Parity")
    label3.pack()
    entry3 = tk.Entry(root, width=30)
    entry3.pack()

    # Create A Button To Submit The Input
    submit_button = tk.Button(root, text="Connect", command=get_user_input)
    submit_button.pack()

    root.mainloop()

    # Dynamically Import The Module Based On User Input
    if meter_model_number:
        try:
            meter_model_module = importlib.import_module(f"meter_models.{meter_model_number}")
            parameters = meter_model_module.parameters
            address = meter_model_module.address
            data_collection(meter_model_number, meter_model_number)  # Call The Data Collection Function With Dynamic Parameters
        except ImportError:
            print(f"Module For {meter_model_number} Not Found")
