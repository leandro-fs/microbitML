#
# **Snake**
# derivado de [Tomate Ruso](xxx@gmail), 2do 13
# https://github.com/INFOCNBA/snake
#
# historial de versiones:
# v250821 - original de Tomate Ruso
# v250827 - comezamos a colaborar en el curso (solucionamos bug de puntaje)
# v251126 - movemos la manzana
#
#
#
# Licencia: [GPL v2](https://www.gnu.org/licenses/old-licenses/gpl-2.0.html)
# (C) Tomate Ruso
# (C) [Robótica - AITEC - CNBA](https://www.cnba.uba.ar/novedades/inscripcion-al-curso-de-robotica)
# (C) 2025 - [Fundación Sadosky](https://fundacionsadosky.org.ar/)
#


from microbit import *
import random
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
    global apple_pos #"global" no es estructurado... :(
    apple_pos_tmp=snake_tail[-1]
    while apple_pos_tmp in snake_tail:
        elemento1=random.randint(0,4)
        elemento2=random.randint(0,4)
        apple_pos_tmp = [elemento1,elemento2]
    apple_pos = apple_pos_tmp
    return apple_pos


for i in snake_tail:
    if snake_tail.index(i) == len(snake_tail) - 1:
        display.set_pixel(i[0],i[1],9)
    else:
        display.set_pixel(i[0],i[1],SNAKE_COLOR)
sleep(frametime * (2/3))
while True:
    
    if tuple(apple_pos) in snake_tail:
        display.clear()
        score += 1 
        snake_length += 1
        if score < 10:
            display.show(score)
        else:
            display.scroll(str(score))
        apple_pos = [random.randint(0,4),random.randint(0,4)]
        while tuple(apple_pos) in snake_tail:
            apple_pos = [random.randint(0,4),random.randint(0,4)]
            
            
        
        sleep(1000)
    
    if pin_logo.is_touched():
        mover_manzana()     # para pruebas
        
    if button_a.was_pressed():
        if direction == "up":
            direction = "left"
        elif direction == "left":
            direction = "down"
        elif direction == "down":
            direction = "right"
        elif direction == "right":
            direction = "up"
            
    if button_b.was_pressed():
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
        display.clear
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
    sleep(frametime)