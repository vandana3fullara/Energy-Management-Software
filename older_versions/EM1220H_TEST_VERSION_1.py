# This Code Will Pull The Data For A Specific Meter Model Number That User Will Input And Will Dynamically Set The Parameters And Register Address Into This Code And
# Display Those Data To The Console User Should Enter Slave ID 5 BaudRate 5 And Parity Even
# Along With That During Data Pulling If It's Getting NaN Value Then It Will Store That Value As 0 In The Local File

import tkinter as tk
from tkinter import messagebox
import minimalmodbus
import serial
import datetime
import time
import os
import math
import importlib

# Define Your Serial Port
serial_port = '/dev/ttyUSB0'

global connection
byte_size = 8

# Function To Replace NaN Value With 0 Value
def replace_nan_with_zero(value):
    return 0.0 if math.isnan(value) else value

# Function To Get The Current Date And Time In The Specified Format
def get_current_datetime():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def data_collection(parameters, address):
    while True:
        try:
            instrument = minimalmodbus.Instrument(serial_port, slave_address)
            instrument.serial.baudrate = baud_rate
            instrument.serial.bytesize = byte_size
            instrument.serial.parity = parity
            instrument.serial.stopbits = stop_bit

            row_data = [get_current_datetime()]

            for i in address:
                register_value = instrument.read_float(int(i), functioncode=3)
                # Replace NaN Values With 0 Before Adding To row_data
                row_data.append(replace_nan_with_zero(register_value))

            # Print Data To The Console
            print(row_data)

            print('*' * 50)
            time.sleep(1)  # Sleep For 1 Seconds
        except Exception as e:
            print("Connection Failed", str(e))

def get_user_input():
    global slave_address, baud_rate, Parity, stop_bit, parity, meter_model_number
    meter_model_number = entry0.get()
    slave_address = int(entry1.get())
    baud_rate = int(entry2.get())
    Parity = entry3.get()

    if Parity == 'Even':
        parity = serial.PARITY_EVEN
        stop_bit = 1
    elif Parity == 'ODD':
        parity = serial.PARITY_ODD
        stop_bit = 1
    else:
        parity = serial.PARITY_NONE
        stop_bit = 2

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
            data_collection(parameters, address)  # Call The Data Collection Function With Dynamic Parameters And Address
        except ImportError:
            print(f"Module For {meter_model_number} Not Found")
