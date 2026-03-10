#
# Actividad de demo de la biblioteca MicrobitML de actividades grupales
#
# --- ¿Qué hace esta actividad? ---
#
# Este programa convierte varios micro:bits en un contador distribuído BASE4.
#
# Normalmente contamos en base 10: cuando un dígito llega a 10, se reinicia
# en 0 y le "avisa" al dígito de la izquierda que sume 1. Por eso después
# del 9 viene el 10, después del 19 viene el 20, y así.
#
# En cualquier base es lo mismo, pero acá en Base4 cada dígito puede valer de 0,o 3.
# Cuando un dígito llega a 4, se reinicia en 0 y le avisa al siguiente.
# Entonces se cuenta así: 0, 1, 2, 3, 10, 11, 12, 13, 20, 21... (en base 4).
# El número que en base 10 es 4, en base 4 se escribe "10". El 8 se escribe
# "20". El 15 se escribe "33".
#
# Cada micro:bit representa un dígito:
#   Rol A → dígito de las unidades      (el que recibe los botones)
#   Rol B → dígito de los "cuatros"
#   Rol C → dígito de los "dieciséis"
#   Rol D → dígito de los "sesenta y cuatro"
#   ... y así sucesivamente.
#
# Cuando apretás el botón en el micro:bit A, su dígito sube en 1.
# Si llega a 4, vuelve a 0 y manda un mensaje de radio ("CARRY") al micro:bit
# B para que él también sume 1. Si B también llega a 4, le avisa a C, y así.
#
# Juntando las pantallas de todos los micro:bits de derecha a izquierda
# (A, B, C...) podés leer el número completo en base 4.
# ---

import microbit as mb
import microbitml as mbml

ACTIVITY = "cnt"
base = 5
numberLength = 3  # lenght of the distributed counter
roles = ('A', 'B', 'C', 'D', 'E', 'F', 'G',
         'H', 'I', 'J', 'K', 'L', 'M', 'N',
         'O', 'P', 'Q', 'R', 'S', 'T', 'U',
         'V', 'W', 'X', 'Y', 'Z')[:numberLength]  # roles of the distributed counter, i.e 'A', 'B', 'C' for three digits


class MbContador:
    def __init__(self, base=3):
        """
        Initializes the class instance with a configurable base value and
        sets up communication and state management for the system.

        Args:
            base (int, optional): The base/system for the counter. Defaults to 3.
        """

        self.config = mbml.ConfigManager(
            roles=roles,
            grupos_max=9,
            grupos_min=1
        )
        self.config.load()

        self.grupo = self.config.get('grupo')
        self.role = self.config.get('role')
        self.role_next = self.get_next_role()

        # Setup radio communication
        self.radio = mbml.Radio(activity=ACTIVITY, channel=0)
        self.radio.configure(group=self.grupo, role=self.role)

        # Counter state
        self.base = base
        self.count = 0  # Current digit value (0-3 for base 4)

        self.show_count()

    def show_count(self):
        """Show the count value on display"""
        mb.display.show(str(self.count))
        mb.sleep(500)

    def show_config(self):
        """Show current role and group configuration"""
        mb.display.show(str(self.config.get('role')))
        mb.sleep(500)
        mb.display.show(str(self.config.get('grupo')))
        mb.sleep(500)
        mb.display.clear()

    def increment_count(self):
        """Increment the count and handle carry if needed"""
        self.count += 1

        if self.count < self.base:  # Base X overflow
            pass
        else:
            self.count = 0  # Reset to 0
            self.send_carry()  # Send carry to next digit

        self.display_count()

    def send_carry(self):
        """Send carry message to the next digit in sequence"""
        if self.role_next:  # ... is not None
            self.radio.send("CARRY", self.role_next)
            print("TX:CARRY to role {}".format(self.role_next))

    def get_next_role(self):
        """Get the next role in the sequence (A->B->C->D->...)"""
        current_role = self.config.get('role')
        roles = self.config.roles

        try:
            current_idx = roles.index(current_role)
            if current_idx < len(roles) - 1:
                return roles[current_idx + 1]
        except ValueError:
            pass

        return None  # No next role or role not found. Hit the total number's length

    def display_count(self):
        """Display the current count value"""
        mb.display.show(str(self.count))

    def handle_radio_messages(self):
        """Handle incoming radio messages"""
        message = self.radio.receive()
        if not message.valid:
            return

        if message.name == 'CARRY':
            # Check if this carry is meant for our role
            if message.valores and len(message.valores) > 0:
                target_role = message.valores[0]
                if target_role == self.config.get('role'):
                    print("RX:CARRY for role {}".format(target_role))
                    self.increment_count()

    def handle_buttons(self):
        """Handle button presses - only units digit (role A) responds to buttons"""
        if self.config.get('role') == 'A':  # Only units digit responds to buttons
            if mb.button_a.was_pressed():
                print("BTN:A pressed - incrementing count")
                self.increment_count()
                while mb.button_a.is_pressed():
                    mb.sleep(50)

            if mb.button_b.was_pressed():
                print("BTN:B pressed - incrementing count")
                self.increment_count()
                while mb.button_b.is_pressed():
                    mb.sleep(50)

    def change_config(self):
        """Handle configuration changes using pin1 + buttons"""
        if self.config.config_rg(mb.pin1, mb.button_a, mb.button_b, self.show_config):
            # Configuration changed, update radio
            nuevo_grupo = self.config.get('grupo')
            nuevo_role = self.config.get('role')
            self.radio.configure(group=nuevo_grupo, role=nuevo_role)
            self.role = nuevo_role
            print("Config updated: Group={}, Role={}".format(nuevo_grupo, nuevo_role))

    def run(self):
        """Main program loop"""
        self.config.save()
        print("mbContador started - Role: {}, Group: {}".format(
            self.config.get('role'), self.config.get('grupo')))

        while True:
            # Handle configuration changes
            self.change_config()

            # Show config when logo is touched
            if mb.pin_logo.is_touched():
                self.show_config()

            # Handle radio messages (carry commands)
            self.handle_radio_messages()

            # Handle button presses (only for units digit)
            self.handle_buttons()

            mb.sleep(20)


# Start the counter
mb.display.scroll(ACTIVITY)
MbContador(base=base).run()
