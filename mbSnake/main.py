#
# **Snake**
# derivado de [Tomate Ruso](xxx@gmail), 2do 13
# https://github.com/INFOCNBA/snake
#
# historial de versiones:
# v250821 - original de Tomate Ruso
# v250827 - comezamos a colaborar en el curso (solucionamos bug de puntaje)
# v251126 - movemos la manzana
# v251210 - importamos framework MicrobitML - practicamos APIs !! :)
# v251211 - otras microbit con rol "A"(manzana) , llama a mover_manzana(). ahora somos MULTIJUGADOR!!
#
#
#
# Licencia: [GPL v2](https://www.gnu.org/licenses/old-licenses/gpl-2.0.html)
# (C) Tomate Ruso
# (C) [Robótica - AITEC - CNBA](https://www.cnba.uba.ar/novedades/inscripcion-al-curso-de-robotica)
# (C) 2025 - [Fundación Sadosky](https://fundacionsadosky.org.ar/)
#


from microbit import *
import radio
import random
from microbitml import RadioPacket


version_token = "snk"
CONFIG_FILE = 'config.cfg'
group_max = 9

role_descriptions = {
    "S": "Snake, lurks and eats (A)pples", #role_descriptions[0] is the default
    "A": "Apple, avoids been eaten by (S)nakes",

}

role_list = list(role_descriptions.keys())

valid_origin_roles_per_destination = {
    "A": ["S"], #not other apples
    "S": ["A"], #possibly many "A"pples
}

current_role = role_list[0] # default role is Snake :)
group = 0
message_bus = group #as expected by microbitml
pin_config=pin1 
pin_config.set_touch_mode(pin_config.RESISTIVE)


packet_input = None
packet_output = None
if pin_logo.is_touched():
            pass #flash spureous events

def error_handler(*args, **kwargs): #para microbitml
    print("WARN: error_handler no implementado, recibe {},{}".format(str(args),str(kwargs)))
    

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


def button_a_was_pressed(config_adjust):
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
        return True  # Indica que se cambio config
    return False  # No se cambio config


def button_b_was_pressed(config_adjust):
    if config_adjust:
        global message_bus
        message_bus += 1
        if message_bus > group_max:
            message_bus = 0
        pin_logo_is_touched()
        save_config()
        print("INFO:button_b_was_pressed({}),newbus:{}".format(config_adjust, message_bus))
        return True  # Indica que se cambio config
    return False  # No se cambio config




#
# begins students's code :D
#

#pin_logo.set_touch_mode(pin_logo.RESISTIVE)
SNAKE_COLOR = 5
snake_length = 2
score = 0
snake_x = 2
snake_y = 2
direction = "up"
apple_pos = [random.randint(0,4),random.randint(0,4)]
frametime = 750
#para crear la serpiente:
snake_tail = [(snake_x,snake_y + 2),(snake_x,snake_y + 1),(snake_x,snake_y)]



def mover_manzana():
    # nota docente: explicar violaciones a la programacion estructurada, frecuentes en Python
    # "global" no es estructurado... :(
    global apple_pos 
    apple_pos_tmp=snake_tail[-1]
    while apple_pos_tmp in snake_tail:
        elemento1=random.randint(0,4)
        elemento2=random.randint(0,4)
        apple_pos_tmp = [elemento1,elemento2]
    apple_pos = apple_pos_tmp
    print("DEBUG: mover_manzana() -> {},{}".format(apple_pos[0],apple_pos[1]))
    return apple_pos



# Main execution
#if __name__ == "__main__": #TODO: main vs main
display.scroll(version_token)
pin_logo_is_touched()  # Mostrar configuracion actual
load_config()
packet_input = None
packet_output = None
radio.on()
radio.config(group=153)
pin1.set_pull(pin1.PULL_UP)


#
# comienza Role S ("Snake")
#
if current_role == "S":
    packet_input = RadioPacket()
    #packet_output = RadioPacket() no se usa
    if pin_logo.is_touched():
        pass #prevent spurious events

    # Dibujar serpiente inicial
    sleep(frametime * (2/3))
    for i in snake_tail:
        if snake_tail.index(i) == len(snake_tail) - 1:
            display.set_pixel(i[0],i[1],9)
        else:
            display.set_pixel(i[0],i[1],SNAKE_COLOR)
    
    def on_message_received(message):
        if pin_logo.is_touched():
            pass #prevent spurious events
        decode_valid=None
        decode_description=None
        from_role=None
        decoded_payload=None
        try:
            valid_origin_roles = valid_origin_roles_per_destination[current_role]
            decode_valid, decode_description, from_role, decoded_payload = packet_input.decode(message, valid_origin_roles)
        except Exception as e:
            print("ERR: on_message_received: problema '{}' procesando '{}'".format(e,message))
            pass  # Si falla el split, continuar con decodificacion normal
        
        print("DEBUG:on_message(packet_input.decode({})):{},'{}','{}'".format(message, decode_valid, decode_description, decoded_payload))
        if decode_valid:
            if decoded_payload == "mover":
                _=mover_manzana()
                print("DEBUG: mover_manzana:{}".format(_))
            else:
                print("INFO:on_message():in from '{}': '{}' payload desconocido".format(from_role, decoded_payload))

        else:
            print("DEBUG:on_message():pass msg='{}', valid={}".format(message, decode_valid))

    while True: #loop
        if tuple(apple_pos) in snake_tail:
            display.clear()
            score += 1 
            snake_length += 1
            if score < 10:
                display.show(score)
            else:
                display.scroll(str(score))
            mover_manzana()
            sleep(1000)
        
            
        if button_a.was_pressed():
            config_adjust = pin_config.is_touched()
            if config_adjust:
                config_changed = button_a_was_pressed(config_adjust)
            else:
                # Logica normal de juego
                if direction == "up":
                    direction = "left"
                elif direction == "left":
                    direction = "down"
                elif direction == "down":
                    direction = "right"
                elif direction == "right":
                    direction = "up"

        if button_b.was_pressed():
            config_adjust = pin_config.is_touched()
            if config_adjust:
                config_changed = button_b_was_pressed(config_adjust)
            else:
                # Logica normal de juego
                if direction == "up":
                    direction = "right"
                elif direction == "left":
                    direction = "up"
                elif direction == "down":
                    direction = "left"
                elif direction == "right":
                    direction = "down"
        

        
        
        if direction == "up":
            snake_y -= 1
        elif direction == "down":
            snake_y += 1
        elif direction == "left":
            snake_x -= 1
        elif direction == "right":
            snake_x += 1
        s_pos = (snake_x, snake_y)
            
        snake_tail.append((snake_x,snake_y))
        if len(snake_tail) > snake_length :
            snake_tail.remove(snake_tail[0])
        used_display = []
        for i in snake_tail:
            if snake_tail.index(i) != len(snake_tail) - 1:
                used_display.append(i)

        if snake_x < 0 or snake_x > 4 or snake_y < 0 or snake_y > 4 or s_pos in used_display:
            sleep(500)
            display.clear()
            display.show(Image.SKULL)
            sleep(1000)
            display.scroll("YOU LOSE.",50)
            while True:
                display.scroll("PRESS A TO RESTART",50)
                if button_a.was_pressed():
                    score = 0
                    break
                sleep(10)
            SNAKE_COLOR = 5
            snake_length = 2
            snake_x = 2
            snake_y = 2
            snake_tail = [(snake_x,snake_y + 2),(snake_x,snake_y + 1),(snake_x,snake_y)]
            direction = "up"
        
        display.clear()
        display.set_pixel(apple_pos[0],apple_pos[1],9)
        for i in snake_tail:
            if snake_tail.index(i) == len(snake_tail) - 1:
                display.set_pixel(i[0],i[1],6)
            else:
                display.set_pixel(i[0],i[1],SNAKE_COLOR)
        message = radio.receive()
        if message:
            on_message_received(message)
        sleep(frametime)
    #
    # terminal rol "S"
    #        
#
# comienza Rol A ("Apple")
#
if current_role == "A":
    #packet_input = RadioPacket() #no se usa
    packet_output = RadioPacket()
    print("INFO: soy manzana")
    def enviar_mover():
            encoded = packet_output.encode("mover")
            radio.send(encoded)  # Envía "snk,0,A,mover"
            print("DEBUG: manzana envió '{}'".format(encoded))
            display.show(Image.ARROW_N)
            sleep(frametime*2)
            display.clear()

    if pin_logo.is_touched():
        pass #flash spureous events

    while True: #loop
        sleep(100) #microbit.sleep(microsegundos)
        if accelerometer.was_gesture("shake"):
            enviar_mover()
            
        if button_a.was_pressed():
            config_adjust = pin1.is_touched()
            if config_adjust:
                button_a_was_pressed(config_adjust)
            else:
                enviar_mover()

        if button_b.was_pressed():
            config_adjust = pin1.is_touched()
            if config_adjust:
                button_b_was_pressed(config_adjust)
            else:
                enviar_mover()
                
        if pin_logo.is_touched():
            pin_logo_is_touched()

    #
    # termina Rol A ("Apple")
    #
#
#   Rol desconocido
#
msg=("rol "+current_role+"_"+current_role+"_"+current_role+" no existe")
raise NotImplementedError(msg)