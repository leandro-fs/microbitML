# main.py - MicrobitML Perceptron Implementation - Modificado por Ramiro Alarcón Lasagno
# Imports go at the top
from microbit import *
import radio
import music
from microbitml import pkt

# Version identifier displayed at startup
version_token = "pct"

# Maximum message bus number (single digit to avoid scrolling)
message_bus_max = 9  # min is 0, one digit avoids scrolling

# Weight multipliers for each input role
role_weights = {"A": 1, "B": 2}

# Maximum counter value for each input role
role_counter_max = {"A": 3, "B": 6}

# Human-readable descriptions of each role's function
role_descriptions = {
    "A": "perceptron input, weight:{}".format(role_weights["A"]),
    "B": "perceptron input, weight:{}".format(role_weights["B"]),
    "Z": "perceptron output, activation function: a+b>4",
}

role_list = list(role_descriptions.keys())

# Define which roles can send messages to which destination roles
valid_origin_roles_per_destination = {
    "A": list(),
    "B": list(),
    "Z": ("A", "B")
}

#
# this node's default config
#
current_role = role_list[0]
message_bus = 0


def error_handler(halt=False, error_code=0, description="desc"):
    """
    Display error on screen and optionally halt execution
    """
    if halt:
        severity = "FATAL"
    else:
        severity = "WARN"
    print("{}:{}:{}".format(severity, error_code, description))
    while True:
        display.show(error_code)
        sleep(200)
        display.show(Image.SAD)
        sleep(2000)
        if not halt:
            break


class PerceptronModel():
    """
    perceptron. two inputs, possibly n-fold input some day
    
    """
    def __init__(self, role, packet_input, packet_output):
        if role in role_list:
            self.role = role
            self.counter = {"A": 0, "B": 0}
            self.output = 0
            self.packet_input = packet_input
            self.packet_output = packet_output
            self.output_threshold = 7
        else:
            error_handler(halt=True, error_code=1, description="FATAL:unexisting role {}".format(role))
            
    def event_handler(self, event, param_dict):
        """
        Route incoming events to appropriate handler
        """
        if event == "message":
            # todo: validation
            self.handle_message(param_dict)
        elif event == "button":
            # todo: validation
            self.handle_button(param_dict)
            pass
        else:
            error_handler(halt=True, error_code=1, description="FATAL:unexisting event {}".format(event))        

            
    def update_output(self):
        """
        Calculate perceptron output and display result with audio feedback
        """
        previous_output = self.output
        counters_sum = self.counter["A"] + self.counter["B"]
        if counters_sum >= self.output_threshold:
            self.output = 1
            if self.output != previous_output:
                music.pitch(frequency=500, duration=250, wait=False)
        else:
            self.output = 0
            if self.output != previous_output:            
                music.pitch(frequency=7000, duration=500, wait=False)
        display.show(counters_sum)
        for pixel_row in range(5):
            display.set_pixel(4, pixel_row, 9 * self.output)

    
    def handle_message(self, param_dict):
        """
        Process received radio message and update counters
        """
        if self.role == "Z":
            if param_dict["origin"] in self.counter.keys():
                try:
                    self.counter[param_dict["origin"]] = int(param_dict["payload"])
                    self.update_output()
                except Exception as e:
                    print("DEBUG:{}:model.message():{}".format(self.role, e))        
            else:
                print("WARN:{}:model.message():paramDict[origin] '{}' not in self.counter.keys".format(self.role, param_dict["origin"]))
        
        else:
            print("DEBUG:{}:model.message():unimplemented message handler".format(self.role))
    
    def handle_button(self, param_dict):
        """
        Process button press event and broadcast new value
        """
        if self.role in ("A", "B"):
            increment = 1
            increment *= role_weights[self.role]  # apply perceptron input's weight parameter
            if param_dict["button"] == "a":
                if self.counter[self.role] + increment > role_counter_max[self.role]:
                    increment = 0
                else:
                    self.counter[self.role] += increment
            elif param_dict["button"] == "b":
                if self.counter[self.role] - increment < 0:
                    increment = 0
                else:
                    self.counter[self.role] -= increment          
            else:
                print("WARN:{}:model.button():paramDict[button] '{}' not implmented".format(self.role, param_dict["button"]))                
                increment = 0  # just to trigger the beep
            if increment == 0:                
                #music.pitch(frequency=500, duration=150, wait=False) # no beep, pls!!
                pass
            # if increment!=0 #send even if nothing changed, just to recover lost sync with Z
            display.show(self.counter[self.role])
            encoded_packet = self.packet_output.encode(self.counter[self.role])
            radio.send(encoded_packet)    
        else:
            print("DEBUG:{}:model.button():unimplemented button handler".format(self.role))


def message_send(role_destination, message):
    """
    Send message to specific role destination (currently debug only)
    """
    print("DEBUG:{}:messageSend({},{})".format(current_role, role_destination, message))
    

def message_attend(message):
    """
    Attend to incoming message (currently debug only)
    """
    print("DEBUG:{}:messageAttend({})".format(current_role, message))
    

def indicator_led_off():
    """
    Turn off indicator LED at position (4,0)
    """
    display.set_pixel(4, 0, 0)


def indicator_led_on():
    """
    Turn on indicator LED at position (4,0)
    """
    display.set_pixel(4, 0, 9)


def button_a_was_pressed(config_adjust):
    """
    Handle button A press event
    config_adjust: if True, change role; if False, normal operation
    """
    global model
    if config_adjust:
        # config change: role in role_list
        global current_role
        previous_role = current_role
        role_index = role_list.index(current_role)
        if role_index < len(role_list) - 1:
            current_role = role_list[role_index + 1]
        else:
            current_role = role_list[0]
        pin_logo_is_touched()
        print("INFO:button_a_was_pressed({}),prevRole:{},newRole:{}".format(config_adjust, previous_role, current_role))
    else:
        #display.show("a")
        #encoded_packet = packet_output.encode("a")
        #radio.send(encoded_packet)        
        #indicator_led_off()
        model.event_handler(event="button", param_dict={"button": "a"})
        #print("INFO:button_a_was_pressed({}),Role:{}".format(config_adjust, current_role))
    

def button_b_was_pressed(config_adjust):
    """
    Handle button B press event
    config_adjust: if True, change message_bus; if False, normal operation
    """
    if config_adjust:
        # config change: message_bus in message_buses_list
        global message_bus
        message_bus += 1
        if message_bus > message_bus_max:
            message_bus = 0
        pin_logo_is_touched()
        print("INFO:button_b_was_pressed({}),newbus:{}".format(config_adjust, message_bus))
    else:
        #display.show("b")
        #encoded_packet = packet_output.encode("b")
        #radio.send(encoded_packet)        
        #indicator_led_off()
        model.event_handler(event="button", param_dict={"button": "b"})
        #print("INFO:button_a_was_pressed({}),Role:{}".format(config_adjust, current_role))


def on_message_received(message):
    """
    Process incoming radio message
    Validates origin role and forwards to model if valid
    """
    valid_origin_roles = valid_origin_roles_per_destination[current_role]
    decode_valid, decode_description, from_role, decoded_payload = packet_input.decode(message, valid_origin_roles)
    print("DEBUG:on_message(packet_input.decode({})):{},'{}','{}'".format(message, decode_valid, decode_description, decoded_payload))
    if decode_valid:
        print("INFO:on_message():in from '{}': '{}'".format(from_role, decoded_payload))
        #display.show(decoded_payload)
        #indicator_led_on()
        model.handle_message(param_dict={"origin": from_role, "payload": decoded_payload})
    else:
        print("DEBUG:on_message():pass".format(message, decode_valid))         


def pin_logo_is_touched():
    """
    Display current configuration (role and message_bus) while logo is touched
    """
    keep_going = True  # show Role and message_bus at least once
    while keep_going:
        display.show(current_role)
        sleep(500)
        display.show(message_bus)
        sleep(200)
        keep_going = pin_logo.is_touched()
        if keep_going:
            print("DEBUG:pin_logo_is_touched(),Role:{},message_bus:{}".format(current_role, message_bus))
    display.clear()
        
    

# Main program execution
if __name__ == "__main__":
    display.scroll(version_token)
    packet_input = pkt()
    packet_output = pkt()
    radio.on()
    radio.config(group=153)  # ,power=6)
    model = PerceptronModel(current_role, packet_input, packet_output)
    pin_logo_is_touched()
    model.update_output()
    
    # Main event loop
    while True:
        if button_a.was_pressed():
            config_adjust = pin1.is_touched()  # pin1 asserted, config adjustment is in order
            button_a_was_pressed(config_adjust)
        if button_b.was_pressed():
            config_adjust = pin1.is_touched()  # pin1 asserted, config adjustment is in order
            button_b_was_pressed(config_adjust)
        if pin_logo.is_touched():
            pin_logo_is_touched()
        message = radio.receive()
        if message:
            on_message_received(message)