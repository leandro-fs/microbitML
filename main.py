# main.py - MicrobitML Perceptron - Ramiro Alarcon Lasagno
from microbit import *
import radio
import music
from microbitml import RadioPacket

version_token = "pct"
CONFIG_FILE = 'config.cfg'
message_bus_max = 9

role_weights = {"A": 1, "B": 2}
role_counter_max = {"A": 3, "B": 6}
role_descriptions = {
    "A": "perceptron input, weight:{}".format(role_weights["A"]),
    "B": "perceptron input, weight:{}".format(role_weights["B"]),
    "Z": "perceptron output, activation function: a+b>4",
}

role_list = list(role_descriptions.keys())

valid_origin_roles_per_destination = {
    "A": list(),
    "B": list(),
    "Z": ("A", "B")
}

current_role = role_list[0]
message_bus = 0


def error_handler(halt=False, error_code=0, description="desc"):
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


def load_config():
    global current_role, message_bus
    try:
        with open(CONFIG_FILE, 'r') as f:
            config = eval(f.read())
        current_role = config['current_role']
        message_bus = config['message_bus']
        print("Loaded config:", config)
    except:
        current_role = role_list[0]
        message_bus = 0
        print("Using default config")


def save_config():
    try:
        config = {
            'current_role': current_role,
            'message_bus': message_bus
        }
        with open(CONFIG_FILE, 'w') as f:
            f.write(repr(config))
        print("Saved config:", config)
    except Exception as e:
        print("Save error:", e)


class PerceptronModel():
    
    def __init__(self, role, packet_input, packet_output):
        if role in role_list:
            self.role = role
            self.counter = {"A": 0, "B": 0}
            self.output = 0
            self.packet_input = packet_input
            self.packet_output = packet_output
            self.output_threshold = 7
            # CORRECCION: Fijar el rol en el packet para evitar usar current_role global
            self.packet_output.fixed_role = role
        else:
            error_handler(halt=True, error_code=1, description="FATAL:unexisting role {}".format(role))
            
    def event_handler(self, event, param_dict):
        if event == "message":
            self.handle_message(param_dict)
        elif event == "button":
            self.handle_button(param_dict)
        else:
            error_handler(halt=True, error_code=1, description="FATAL:unexisting event {}".format(event))        

            
    def update_output(self):
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
        if self.role in ("A", "B"):
            increment = 1
            increment *= role_weights[self.role]
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
                increment = 0
            if increment == 0:                
                pass
            display.show(self.counter[self.role])
            encoded_packet = self.packet_output.encode(self.counter[self.role])
            radio.send(encoded_packet)    
        else:
            print("DEBUG:{}:model.button():unimplemented button handler".format(self.role))


def message_send(role_destination, message):
    print("DEBUG:{}:messageSend({},{})".format(current_role, role_destination, message))


def message_attend(message):
    print("DEBUG:{}:messageAttend({})".format(current_role, message))


def indicator_led_off():
    display.set_pixel(4, 0, 0)


def indicator_led_on():
    display.set_pixel(4, 0, 9)


def button_a_was_pressed(config_adjust):
    global model
    if config_adjust:
        global current_role
        previous_role = current_role
        role_index = role_list.index(current_role)
        if role_index < len(role_list) - 1:
            current_role = role_list[role_index + 1]
        else:
            current_role = role_list[0]
        pin_logo_is_touched()
        save_config()
        print("INFO:button_a_was_pressed({}),prevRole:{},newRole:{}".format(config_adjust, previous_role, current_role))
    else:
        model.event_handler(event="button", param_dict={"button": "a"})


def button_b_was_pressed(config_adjust):
    if config_adjust:
        global message_bus
        message_bus += 1
        if message_bus > message_bus_max:
            message_bus = 0
        pin_logo_is_touched()
        save_config()
        print("INFO:button_b_was_pressed({}),newbus:{}".format(config_adjust, message_bus))
    else:
        model.event_handler(event="button", param_dict={"button": "b"})


def on_message_received(message):
    # CORRECCION: Filtrar mensajes del propio rol ANTES de decodificar
    try:
        parts = message.split(",")
        sender_role = parts[2] if len(parts) > 2 else ""
        
        # Ignorar mensajes propios (no es clonacion, es radio broadcast)
        if sender_role == current_role:
            print("DEBUG:on_message():mensaje propio ignorado de '{}'".format(sender_role))
            return
    except:
        pass  # Si falla el split, continuar con decodificacion normal
    
    # Decodificacion normal para mensajes de otros roles
    valid_origin_roles = valid_origin_roles_per_destination[current_role]
    decode_valid, decode_description, from_role, decoded_payload = packet_input.decode(message, valid_origin_roles)
    print("DEBUG:on_message(packet_input.decode({})):{},'{}','{}'".format(message, decode_valid, decode_description, decoded_payload))
    if decode_valid:
        print("INFO:on_message():in from '{}': '{}'".format(from_role, decoded_payload))
        model.handle_message(param_dict={"origin": from_role, "payload": decoded_payload})
    else:
        print("DEBUG:on_message():pass".format(message, decode_valid))


def pin_logo_is_touched():
    keep_going = True
    while keep_going:
        display.show(current_role)
        sleep(500)
        display.show(message_bus)
        sleep(200)
        keep_going = pin_logo.is_touched()
        if keep_going:
            print("DEBUG:pin_logo_is_touched(),Role:{},message_bus:{}".format(current_role, message_bus))
    display.clear()


# Main execution
if __name__ == "__main__":
    display.scroll(version_token)
    load_config()
    packet_input = RadioPacket()
    packet_output = RadioPacket()
    radio.on()
    radio.config(group=153)
    model = PerceptronModel(current_role, packet_input, packet_output)
    pin_logo_is_touched()
    model.update_output()
    
    # Main loop
    while True:
        if button_a.was_pressed():
            config_adjust = pin1.is_touched()
            button_a_was_pressed(config_adjust)
        if button_b.was_pressed():
            config_adjust = pin1.is_touched()
            button_b_was_pressed(config_adjust)
        if pin_logo.is_touched():
            pin_logo_is_touched()
        message = radio.receive()
        if message:
            on_message_received(message)